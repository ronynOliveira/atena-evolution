#!/usr/bin/env python3
"""
Auto-Fetch System for Hermes Agent
Inspired by OpenHuman's 20-minute auto-fetch cron.

Collects data from connected sources and feeds into wiki/memory.
Runs every 60 minutes via cron job.

Sources:
  1. GitHub (projetoAtenacompleto) — recent issues, PRs, commits
  2. Wiki health — page count, recent changes
  3. System resources — RAM, disk, CPU
  4. OpenRouter API key status
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# ─── Paths ────────────────────────────────────────────────────────────────
HERMES_HOME = Path(os.environ.get("HERMES_HOME", "C:/Users/dell-/AppData/Local/hermes"))
WIKI_DIR = Path("C:/Users/dell-/wiki")
LOG_DIR = HERMES_HOME / "logs"
STATE_DIR = HERMES_HOME / "auto-fetch"
STATE_FILE = STATE_DIR / "last_state.json"

os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(STATE_DIR, exist_ok=True)

LOG_FILE = LOG_DIR / "auto-fetch.log"


def log(msg: str):
    """Log with timestamp."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def run(cmd: list[str], timeout: int = 30) -> str:
    """Run a command, return stdout."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0)
        if r.returncode == 0:
            return r.stdout.strip()
        return f"[exit {r.returncode}] {r.stderr.strip()[:200]}"
    except subprocess.TimeoutExpired:
        return "[timeout]"
    except FileNotFoundError as e:
        return f"[not found: {e.filename}]"


# ─── Source 1: GitHub ─────────────────────────────────────────────────────
def fetch_github() -> dict:
    """Fetch recent activity from projetoAtenacompleto."""
    result = {
        "recent_commits": [],
        "open_issues": 0,
        "recent_issues": [],
        "error": None,
    }

    # Check gh auth
    auth = run(["gh", "auth", "status", "--show-token"])
    if "[exit" in auth or "[not found" in auth:
        result["error"] = "gh CLI not authenticated"
        return result

    REPO = "ronynOliveira/projetoAtenacompleto"

    # Recent commits (last 5)
    commits_raw = run(["gh", "api", f"/repos/{REPO}/commits?per_page=5"])
    if commits_raw and not commits_raw.startswith("[exit") and not commits_raw.startswith("[not found"):
        try:
            commits = json.loads(commits_raw)
            for c in commits:
                sha = c.get("sha", "")[:7]
                msg = c.get("commit", {}).get("message", "").split("\n")[0][:80]
                date = c.get("commit", {}).get("committer", {}).get("date", "")[:10]
                author = c.get("commit", {}).get("author", {}).get("name", "?")
                result["recent_commits"].append({
                    "sha": sha,
                    "msg": msg,
                    "date": date,
                    "author": author,
                })
        except json.JSONDecodeError:
            pass

    # Open issues count
    issues_count = run(["gh", "api", f"/repos/{REPO}/issues?state=open&per_page=1"])
    if issues_count and not issues_count.startswith("[exit"):
        try:
            # The Link header has the total count, but easier: just count
            all_issues = run(["gh", "api", f"/repos/{REPO}/issues?state=open&per_page=100"])
            if all_issues and not all_issues.startswith("[exit"):
                issues = json.loads(all_issues)
                result["open_issues"] = len([i for i in issues if "pull_request" not in i])
        except (json.JSONDecodeError, TypeError):
            pass

    return result


# ─── Source 2: Wiki Health ────────────────────────────────────────────────
def fetch_wiki() -> dict:
    """Check wiki health and recent changes."""
    result = {
        "page_count": 0,
        "total_size_kb": 0,
        "recent_changes": [],
        "error": None,
    }

    if not WIKI_DIR.exists():
        result["error"] = f"Wiki dir not found: {WIKI_DIR}"
        return result

    # Count pages (.md files)
    md_files = list(WIKI_DIR.rglob("*.md"))
    result["page_count"] = len(md_files)

    # Total size of .md files
    total_bytes = sum(f.stat().st_size for f in md_files if f.is_file())
    result["total_size_kb"] = round(total_bytes / 1024, 1)

    # Get most recently modified .md files
    md_with_mtime = [(f, f.stat().st_mtime) for f in md_files if f.is_file()]
    md_with_mtime.sort(key=lambda x: x[1], reverse=True)

    for f, mtime in md_with_mtime[:5]:
        rel = f.relative_to(WIKI_DIR)
        dt = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
        result["recent_changes"].append(f"{rel} [{dt}]")

    return result


# ─── Source 3: System Resources ───────────────────────────────────────────
def fetch_system() -> dict:
    """Check system resources."""
    result = {
        "ram_pct": 0,
        "disk_free_gb": 0,
        "ollama_running": False,
        "ollama_models": [],
        "gateway_running": False,
    }

    # RAM via PowerShell
    ps_cmd = 'powershell -Command "Get-CimInstance Win32_OperatingSystem | Select @{N=\'Pct\';E={[math]::Round(($_.TotalVisibleMemorySize-$_.FreePhysicalMemory)/$_.TotalVisibleMemorySize*100,1)}} | Format-Table -HideTableHeaders"'
    ram = run(["powershell", "-Command", "Get-CimInstance Win32_OperatingSystem | Select @{N='P';E={[math]::Round(($_.TotalVisibleMemorySize-$_.FreePhysicalMemory)/$_.TotalVisibleMemorySize*100,1)}} | Format-Table -HideTableHeaders"], timeout=15)
    if ram and ram.strip() and ram.strip() != "[exit":
        try:
            result["ram_pct"] = float(ram.strip().split("\n")[0].strip())
        except (ValueError, IndexError):
            pass

    # Disk free
    disk = run(["powershell", "-Command", "Get-PSDrive C | Select-Object -ExpandProperty Free"], timeout=15)
    if disk and disk.strip() and disk.strip() != "[exit":
        try:
            free_bytes = int(disk.strip())
            result["disk_free_gb"] = round(free_bytes / (1024**3), 0)
        except (ValueError, IndexError):
            pass

    # Ollama health
    ollama_check = run(["curl", "-s", "http://localhost:11434/api/tags"], timeout=10)
    if ollama_check and "models" in ollama_check:
        result["ollama_running"] = True
        try:
            data = json.loads(ollama_check)
            models_list = data.get("models", data.get("data", []))
            result["ollama_models"] = [m["name"] for m in models_list]
        except (json.JSONDecodeError, KeyError):
            pass

    # Gateway health
    gw_check = run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "http://localhost:8642/health"], timeout=10)
    if gw_check and gw_check.strip() == "200":
        result["gateway_running"] = True

    return result


# ─── Source 4: Config Status ──────────────────────────────────────────────
def fetch_config() -> dict:
    """Check critical config values."""
    result = {
        "active_model": "unknown",
        "openrouter_configured": False,
    }

    config_path = HERMES_HOME / "config.yaml"
    if config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            content = f.read()
            # Extract model info
            for line in content.split("\n"):
                line = line.strip()
                if line.startswith("default:") and "model:" not in line:
                    result["active_model"] = line.split(":", 1)[1].strip()
                    break

    # Check if openrouter provider exists in config
    if config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            content = f.read()
            result["openrouter_configured"] = "openrouter" in content.lower()

    return result


# ─── Source 5: Composio ──────────────────────────────────────────────────
def fetch_composio() -> dict:
    """Check Composio connection status."""
    result = {"connected": False, "key_present": False, "error": None}

    key_file = Path.home() / ".composio" / "api_key"
    if key_file.exists():
        result["key_present"] = True

    try:
        from composio import Composio
        key = os.environ.get("COMPOSIO_API_KEY")
        if not key and key_file.exists():
            key = key_file.read_text().strip()
        if key:
            c = Composio(api_key=key)
            result["connected"] = True
    except Exception as e:
        result["error"] = str(e)[:80]

    return result


# ─── Main ─────────────────────────────────────────────────────────────────
def main():
    log("=== Auto-Fetch Cycle Start ===")

    results = {
        "timestamp": datetime.now().isoformat(),
        "github": fetch_github(),
        "wiki": fetch_wiki(),
        "system": fetch_system(),
        "config": fetch_config(),
        "composio": fetch_composio(),
    }

    # Save state for cross-cycle comparison
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # ─── Source 6: Memory Tree ─────────────────────────────────────────────
    try:
        sys.path.insert(0, str(HERMES_HOME / "lib"))
        from memory_scorer import get_stats as get_memory_stats
        mem_stats = get_memory_stats()
    except Exception:
        mem_stats = {"total_entries": 0}

    # Build summary
    gh = results["github"]
    wk = results["wiki"]
    sys_info = results["system"]

    log(f"GitHub: {len(gh['recent_commits'])} recent commits, {gh['open_issues']} open issues")
    log(f"Wiki: {wk['page_count']} pages, {wk['total_size_kb']}KB total")
    log(f"Sistema: RAM {sys_info['ram_pct']}% | Disco {sys_info['disk_free_gb']}GB livre")
    log(f"Ollama: {'✅ rodando' if sys_info['ollama_running'] else '❌ parado'} ({len(sys_info['ollama_models'])} modelos)")
    log(f"Gateway: {'✅ rodando' if sys_info['gateway_running'] else '❌ parado'}")

    comp = results.get("composio", {})
    if comp.get("key_present"):
        log(f"Composio: {'✅ conectado' if comp.get('connected') else '⚠️ API key ok mas backend offline'}")
    else:
        log("Composio: ❌ sem API key")
    
    log(f"Memory Tree: {mem_stats.get('total_entries', 0)} entries, score médio {mem_stats.get('avg_score', 0):.1f}")

    if gh["error"]:
        log(f"⚠ GitHub error: {gh['error']}")

    if sys_info["ram_pct"] > 85:
        log(f"⚠ ALERTA: RAM em {sys_info['ram_pct']}% — alto!")

    if not sys_info["gateway_running"]:
        log("⚠ ALERTA: Gateway Hermes está PARADO!")

    log("=== Auto-Fetch Cycle Complete ===")

    # Output JSON for cron job to capture
    summary = {
        "status": "ok",
        "timestamp": results["timestamp"],
        "github_commits": len(gh["recent_commits"]),
        "github_issues": gh["open_issues"],
        "wiki_pages": wk["page_count"],
        "ram_pct": sys_info["ram_pct"],
        "disk_free_gb": sys_info["disk_free_gb"],
        "ollama_models": len(sys_info["ollama_models"]),
        "gateway_running": sys_info["gateway_running"],
    }
    print(f"\n---AUTO-FETCH-SUMMARY---")
    print(json.dumps(summary))
    print("---END-SUMMARY---")


if __name__ == "__main__":
    main()