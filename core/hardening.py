#!/usr/bin/env python3
"""
Koldi's Hardening — Script de Segurança do Sistema
Varredura + Correção + Monitoramento + Memória + Relatório

Uso:
  python hardening.py scan          — Apenas verificar
  python hardening.py fix           — Corrigir problemas encontrados
  python hardening.py monitor       — Modo monitor (executa e re-executa)
  python hardening.py report        — Relatório de segurança legível
  python hardening.py scan --report — Escaneia e gera relatório
"""

import json
import os
import shutil
import stat
import subprocess

# Windows: CREATE_NO_WINDOW to prevent CMD flash
WIN_FLAGS = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
import sys
import time
from datetime import datetime
from pathlib import Path

HERMES = Path.home() / "AppData/Local/hermes"
COFRE_DIR = HERMES / "cofre"
LOG_FILE = HERMES / "logs" / "hardening.log"
REPORT_FILE = HERMES / "logs" / "security_report.json"
LIB_DIR = HERMES / "lib"
AUTO_FETCH_STATE = HERMES / "auto-fetch" / "last_state.json"
AUTO_FETCH_SCRIPT = HERMES / "scripts" / "auto_fetch.py"

# ─── Memory Tree Integration ──────────────────────────────────────────────
_memory_scorer = None  # lazy import


def _get_memory_scorer():
    """Lazy-import memory_scorer to avoid dependency at module load time."""
    global _memory_scorer
    if _memory_scorer is None:
        sys.path.insert(0, str(LIB_DIR))
        import memory_scorer as ms
        _memory_scorer = ms
    return _memory_scorer


# Arquivos que devem ter permissão restrita (apenas dono)
RESTRICTED_FILES = [
    HERMES / ".env",
    HERMES / "config.yaml",
    Path.home() / ".composio" / "api_key",
    COFRE_DIR / "vault.enc",
    COFRE_DIR / "vault.salt",
]

# Pastas que devem ser restritas
RESTRICTED_DIRS = [
    COFRE_DIR,
]

# Severity → score mapping for memory tree entries
SEVERITY_SCORE = {
    "HIGH": 8.0,
    "MEDIUM": 5.0,
    "LOW": 3.0,
}


def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


# ─── Memory Tree Logging ──────────────────────────────────────────────────

def log_security_event(issue: dict):
    """Log a security issue as a memory tree entry."""
    try:
        ms = _get_memory_scorer()
        ms.ensure_dirs()
        severity = issue.get("severity", "LOW")
        score = SEVERITY_SCORE.get(severity, 3.0)
        content = (
            f"[{severity}] {issue['type']}: {issue.get('detail', '')} "
            f"| path: {issue.get('path', 'N/A')}"
        )
        ms.create_entry(
            content=content,
            category="security",
            tags=["hardening", severity.lower(), issue["type"]],
            source="hardening_script",
            score=score,
        )
    except Exception as e:
        log(f"⚠ Memory tree log falhou: {e}")


def log_disk_event(detail: str, severity: str = "MEDIUM"):
    """Log disk-space findings as memory tree entries."""
    try:
        ms = _get_memory_scorer()
        ms.ensure_dirs()
        score = SEVERITY_SCORE.get(severity, 5.0)
        ms.create_entry(
            content=f"[{severity}] disk_monitor: {detail}",
            category="system",
            tags=["hardening", "disk", severity.lower()],
            source="hardening_script",
            score=score,
        )
    except Exception:
        pass


# ─── Auto-Fetch Integration ───────────────────────────────────────────────

def notify_auto_fetch(security_data: dict):
    """Write hardening findings into auto-fetch's shared state for next cycle."""
    try:
        AUTO_FETCH_STATE.parent.mkdir(parents=True, exist_ok=True)
        state = {}
        if AUTO_FETCH_STATE.exists():
            try:
                state = json.loads(AUTO_FETCH_STATE.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, Exception):
                state = {}
        state["hardening"] = {
            "timestamp": datetime.now().isoformat(),
            "total_issues": security_data.get("total_issues", 0),
            "high": security_data.get("high", 0),
            "medium": security_data.get("medium", 0),
            "low": security_data.get("low", 0),
            "alerts": [
                i for i in security_data.get("issues", [])
                if i.get("severity") in ("HIGH", "MEDIUM")
            ],
        }
        AUTO_FETCH_STATE.write_text(
            json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        log(f"📡 Notificação enviada ao auto-fetch ({security_data.get('total_issues', 0)} issues)")
    except Exception as e:
        log(f"⚠ Falha ao notificar auto-fetch: {e}")


def trigger_auto_fetch(security_data: dict):
    """Trigger an auto-fetch cycle if critical issues found."""
    notify_auto_fetch(security_data)
    if security_data.get("high", 0) > 0 and AUTO_FETCH_SCRIPT.exists():
        try:
            subprocess.Popen(
                [sys.executable, str(AUTO_FETCH_SCRIPT)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=WIN_FLAGS,
            )
            log(f"🔄 Auto-fetch acionado para ciclo extra ({security_data['high']} alta(s))")
        except Exception as e:
            log(f"⚠ Falha ao acionar auto-fetch: {e}")


# ─── Disk Monitoring ──────────────────────────────────────────────────────

DISK_THRESHOLD_WARN_GB = 5.0
DISK_THRESHOLD_CRIT_GB = 1.0


def check_disk() -> dict:
    """Check disk space usage on C: drive."""
    result = {
        "total_gb": 0,
        "free_gb": 0,
        "used_pct": 0,
        "status": "OK",
        "detail": "",
    }
    try:
        usage = shutil.disk_usage("C:/")
        total_gb = usage.total / (1024 ** 3)
        free_gb = usage.free / (1024 ** 3)
        used_pct = 100 * (usage.used / usage.total) if usage.total > 0 else 0

        result["total_gb"] = round(total_gb, 2)
        result["free_gb"] = round(free_gb, 2)
        result["used_pct"] = round(used_pct, 1)

        if free_gb < DISK_THRESHOLD_CRIT_GB:
            result["status"] = "CRITICAL"
            result["detail"] = (
                f"Disco C: criticamente baixo — {free_gb:.2f} GB livre "
                f"({used_pct:.1f}% usado)"
            )
        elif free_gb < DISK_THRESHOLD_WARN_GB:
            result["status"] = "WARN"
            result["detail"] = (
                f"Disco C: {free_gb:.2f} GB livre ({used_pct:.1f}% usado) "
                f"— abaixo do limiar de alerta ({DISK_THRESHOLD_WARN_GB} GB)"
            )
        else:
            result["detail"] = (
                f"Disco C: {free_gb:.2f} GB livre ({used_pct:.1f}% usado) — OK"
            )
    except Exception as e:
        result["status"] = "ERROR"
        result["detail"] = f"Falha ao verificar disco: {e}"

    return result


# ─── SCAN ─────────────────────────────────────────────────────────────────

def scan() -> dict:
    """Varredura completa de segurança."""
    issues = []

    # 1. Permissões de arquivos
    for path in RESTRICTED_FILES:
        if path.exists():
            perms = oct(os.stat(path).st_mode)[-3:]
            is_open = perms in ["666", "777", "755", "644"]
            issues.append({
                "type": "permission",
                "path": str(path),
                "severity": "HIGH" if is_open else "OK",
                "current": perms,
                "target": "600",
                "detail": f"Permissão {perms} — mundo pode ler" if is_open else "OK",
            })

    # 2. KEYS hardcoded em scripts
    scripts_dir = HERMES / "scripts"
    sensitive_patterns = ["api_key", "api.secret", "password", "token=", "secret="]

    for f in sorted(scripts_dir.glob("*.py")):
        try:
            content = f.read_text(encoding="utf-8")
            for i, line in enumerate(content.split("\n"), 1):
                lowered = line.lower()
                for pat in sensitive_patterns:
                    if pat in lowered and "=" in line and len(line) > 40:
                        if "getpass" not in lowered and "os.environ" not in lowered:
                            issues.append({
                                "type": "hardcoded_key",
                                "path": f"{f.name}:{i}",
                                "severity": "MEDIUM",
                                "detail": line.strip()[:80],
                            })
        except:
            pass

    # 3. Serviços expostos — timeout curto
    listening_ports = []
    try:
        result = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True, text=True, timeout=8
        ,
                       creationflags=WIN_FLAGS)
        for line in result.stdout.split("\n"):
            if "LISTENING" in line and "0.0.0.0" in line:
                parts = line.strip().split()
                if len(parts) >= 2:
                    addr = parts[1]
                    port = addr.split(":")[-1] if ":" in addr else addr
                    listening_ports.append(port)
    except:
        pass

    # Portas não-sistema que estão expostas em 0.0.0.0
    system_ports = {"135", "445", "2179", "5040", "5357"}
    unknown_ports = [p for p in listening_ports if p not in system_ports]
    for p in unknown_ports:
        issues.append({
            "type": "exposed_port",
            "path": f"0.0.0.0:{p}",
            "severity": "LOW",
            "detail": f"Porta {p} exposta em todas as interfaces",
        })

    # 4. Disk monitoring integrado
    disk_info = check_disk()
    if disk_info["status"] in ("WARN", "CRITICAL"):
        issues.append({
            "type": "disk_space",
            "path": "C:",
            "severity": "HIGH" if disk_info["status"] == "CRITICAL" else "MEDIUM",
            "detail": disk_info["detail"],
        })

    report = {
        "timestamp": datetime.now().isoformat(),
        "total_issues": len(issues),
        "high": sum(1 for i in issues if i["severity"] == "HIGH"),
        "medium": sum(1 for i in issues if i["severity"] == "MEDIUM"),
        "low": sum(1 for i in issues if i["severity"] == "LOW"),
        "issues": issues,
        "disk": disk_info,
    }

    # Log security events to memory tree
    for issue in issues:
        if issue["severity"] in ("HIGH", "MEDIUM"):
            log_security_event(issue)

    return report


# ─── FIX ──────────────────────────────────────────────────────────────────

def fix(report: dict):
    """Corrigir problemas encontrados."""
    fixed = 0

    for issue in report["issues"]:
        if issue["type"] == "permission" and issue["severity"] == "HIGH":
            path = Path(issue["path"])
            try:
                # Tentar path.chmod (implementação Path)
                path.chmod(0o600)
                log(f"🔧 Corrigido: {issue['path']} ({issue['current']} → 600)")
                fixed += 1
            except PermissionError:
                # Fallback com os.chmod
                try:
                    os.chmod(str(path), stat.S_IRUSR | stat.S_IWUSR)
                    log(f"🔧 Corrigido (os.chmod): {issue['path']} → 600")
                    fixed += 1
                except PermissionError:
                    log(f"⚠ Não foi possível corrigir {issue['path']} — sem permissão de admin")
        elif issue["type"] == "disk_space":
            log(f"⚠ Disco baixo — {issue['detail']} — correção manual necessária")

    # Garantir que pastas restritas existam com permissão correta
    for d in RESTRICTED_DIRS:
        d.mkdir(parents=True, exist_ok=True)
        try:
            # Tentar path.chmod
            d.chmod(0o700)
            log(f"🔧 Diretório seguro: {d} (700)")
            fixed += 1
        except PermissionError:
            try:
                os.chmod(str(d), stat.S_IRWXU)
                log(f"🔧 Diretório seguro (os.chmod): {d} (700)")
                fixed += 1
            except PermissionError:
                pass

    # Remover scripts com keys hardcoded (do patch_composio_config)
    old_patch = HERMES / "scripts" / "patch_composio_config.py"
    if old_patch.exists():
        content = old_patch.read_text(encoding="utf-8")
        if "ak_iv6" in content:
            # Replace old hardcoded key
            content = content.replace("ak_iv6XhAezVQEcaZqU9b41", "***")
            old_patch.write_text(content, encoding="utf-8")
            log(f"🔧 Limpo: patch_composio_config.py (hardcoded key removida)")
            fixed += 1

    log(f"\n✅ Total: {fixed} problemas corrigidos")


# ─── REPORT ────────────────────────────────────────────────────────────────

def generate_report(report_data: dict) -> str:
    """Generate a human-readable security report."""
    lines = []
    lines.append("=" * 60)
    lines.append("  🔐 KOLDI'S HARDENING — RELATÓRIO DE SEGURANÇA")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"  Timestamp:    {report_data['timestamp']}")
    lines.append(f"  Total issues: {report_data['total_issues']}")
    lines.append(f"  🔴 Alta:      {report_data['high']}")
    lines.append(f"  🟡 Média:     {report_data['medium']}")
    lines.append(f"  🔵 Baixa:     {report_data['low']}")
    lines.append("")

    # Disk section
    disk = report_data.get("disk", {})
    lines.append("── Disco ───────────────────────────────────────────────")
    if disk:
        status_icon = {
            "OK": "✅", "WARN": "⚠️", "CRITICAL": "🚨", "ERROR": "❌"
        }.get(disk.get("status", "OK"), "❓")
        lines.append(f"  {status_icon} Status: {disk.get('status', 'N/A')}")
        lines.append(f"     Total: {disk.get('total_gb', '?')} GB")
        lines.append(f"     Livre: {disk.get('free_gb', '?')} GB")
        lines.append(f"     Uso:   {disk.get('used_pct', '?')}%")
        lines.append(f"     Detalhe: {disk.get('detail', 'N/A')}")
    else:
        lines.append("  ⚪ Não verificado")
    lines.append("")

    # Issues section
    lines.append("── Problemas Detectados ─────────────────────────────────")
    if not report_data["issues"]:
        lines.append("  ✅ Nenhum problema encontrado.")
    else:
        for i, issue in enumerate(report_data["issues"], 1):
            icon = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🔵", "OK": "✅"}
            ic = icon.get(issue.get("severity", ""), "⚪")
            lines.append(f"  {i:2d}. {ic} [{issue['severity']}] {issue['type']}")
            lines.append(f"      Path:   {issue.get('path', 'N/A')}")
            lines.append(f"      Detail: {issue.get('detail', 'N/A')}")
            if issue.get("current") and issue.get("target"):
                lines.append(f"      Perm:   {issue['current']} → {issue['target']}")
            lines.append("")

    # Memory Tree summary
    try:
        ms = _get_memory_scorer()
        stats = ms.get_stats()
        lines.append("── Memory Tree ─────────────────────────────────────────")
        lines.append(f"  Total entries:     {stats.get('total_entries', 0)}")
        lines.append(f"  Score médio:       {stats.get('avg_score', 0)}")
        lines.append(f"  Entries ativas:    {stats.get('active', 0)}")
        lines.append(f"  Consolidadas:      {stats.get('consolidated', 0)}")
        lines.append("")
    except Exception:
        pass

    lines.append("=" * 60)
    lines.append("  Fim do relatório")
    lines.append("=" * 60)

    return "\n".join(lines)


# ─── CLI ──────────────────────────────────────────────────────────────────

def main():
    print("🔐 Koldi's Hardening — Segurança do Sistema\n")

    if len(sys.argv) < 2:
        print("Uso: hardening.py [scan|fix|monitor|report] [--report]")
        return

    cmd = sys.argv[1]
    extra_flags = sys.argv[2:]

    if cmd == "scan":
        report = scan()
        print(f"\n📊 Relatório: {report['total_issues']} problemas")
        print(f"   🔴 Alta: {report['high']}")
        print(f"   🟡 Média: {report['medium']}")
        print(f"   🔵 Baixa: {report['low']}\n")

        for issue in report["issues"]:
            icon = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🔵"}
            print(f"  {icon.get(issue['severity'], '⚪')} [{issue['severity']}] {issue['type']}")
            print(f"     {issue['detail']}")

        # Salvar relatório
        REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
        REPORT_FILE.write_text(json.dumps(report, indent=2, ensure_ascii=False))
        log(f"📄 Relatório salvo: {REPORT_FILE}")

        # Notificar auto-fetch
        notify_auto_fetch(report)
        if report["high"] > 0:
            trigger_auto_fetch(report)

        # Se --report, gerar relatório legível
        if "--report" in extra_flags:
            print("\n" + generate_report(report))

    elif cmd == "fix":
        report = scan()
        if report["total_issues"] == 0:
            print("✅ Nenhum problema encontrado.")
        else:
            fix(report)
            # Re-scan after fix
            post_report = scan()
            remaining = post_report["total_issues"]
            if remaining == 0:
                print("✅ Todos os problemas foram corrigidos.")
            else:
                print(f"⚠ {remaining} problemas restantes (podem precisar de admin).")
            # Notificar auto-fetch
            notify_auto_fetch(post_report)

    elif cmd == "report":
        # Generate report from last scan or run fresh scan
        if REPORT_FILE.exists():
            try:
                data = json.loads(REPORT_FILE.read_text(encoding="utf-8"))
                # Refresh disk info
                data["disk"] = check_disk()
            except Exception:
                data = scan()
        else:
            data = scan()
        print(generate_report(data))

    elif cmd == "monitor":
        import time
        print("👁️  Modo monitor — executando scan a cada 60s")
        print("   Pressione Ctrl+C para parar.\n")
        try:
            while True:
                report = scan()
                if report["high"] > 0 or report["medium"] > 0:
                    log(f"⚠ ALERTA: {report['high']} alta, {report['medium']} média")
                    trigger_auto_fetch(report)
                else:
                    log(f"✅ Scan OK — {report['total_issues']} issues menores")
                time.sleep(60)
        except KeyboardInterrupt:
            print("\n👋 Monitor encerrado.")

    else:
        print(f"Comando desconhecido: {cmd}")
        print("Uso: hardening.py [scan|fix|monitor|report] [--report]")


if __name__ == "__main__":
    main()