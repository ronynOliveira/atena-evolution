"""
hermes_auto_update.py — Atualização automática do Hermes Agent
Verifica atualizações, faz backup, aplica e reinicia.
"""
import subprocess
import json
import os
import sys
import shutil
import time
from pathlib import Path
from datetime import datetime

HERMES_DIR = Path(os.path.expanduser("~/.hermes"))
BACKUP_DIR = HERMES_DIR / "backups"
CONFIG_FILE = HERMES_DIR / "config.yaml"
UPDATE_LOG = HERMES_DIR / "update_log.json"


def run_cmd(cmd: str, cwd: str = None) -> tuple[int, str]:
    """Executa comando e retorna (exit_code, output)."""
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True,
        cwd=cwd, timeout=120
    )
    return result.returncode, result.stdout + result.stderr


def get_current_version() -> str:
    """Obtém versão atual do Hermes."""
    rc, output = run_cmd("hermes --version 2>&1")
    if rc == 0:
        return output.strip()
    return "unknown"


def check_updates() -> dict:
    """Verifica se há atualizações disponíveis."""
    print("Verificando atualizacoes...")

    # Verificar atualizações via pip
    rc, output = run_cmd("pip show hermes-agent 2>&1")
    current = ""
    if rc == 0:
        for line in output.split("\n"):
            if line.startswith("Version:"):
                current = line.split(":", 1)[1].strip()
                break

    # Verificar atualizações via pip index
    rc2, output2 = run_cmd("pip index versions hermes-agent 2>&1 || pip install hermes-agent==999 2>&1")
    latest = ""
    if rc2 != 0:
        # Parse "Available versions: 0.16.0, 0.15.9, ..."
        for line in output2.split("\n"):
            if "Available versions:" in line:
                versions = line.split(":", 1)[1].strip().split(",")
                latest = versions[0].strip()
                break

    return {
        "current": current,
        "latest": latest,
        "update_available": current != latest and latest != "",
    }


def create_backup() -> str:
    """Cria backup do diretório Hermes."""
    BACKUP_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"hermes_backup_{timestamp}"

    print(f"Criando backup em {backup_path}...")
    shutil.copytree(HERMES_DIR, backup_path, ignore=shutil.ignore_patterns(
        "backups", "__pycache__", "*.pyc", ".git"
    ))
    print(f"  Backup criado: {backup_path}")
    return str(backup_path)


def apply_update() -> bool:
    """Aplica atualização via pip."""
    print("Aplicando atualizacao...")
    rc, output = run_cmd("pip install --upgrade hermes-agent 2>&1")
    if rc == 0:
        print("  Atualização aplicada com sucesso!")
        return True
    else:
        print(f"  ERRO na atualização:\n{output}")
        return False


def restart_gateway() -> bool:
    """Reinicia o gateway do Hermes."""
    print("Reiniciando gateway...")
    rc, output = run_cmd("hermes gateway restart 2>&1")
    if rc == 0:
        print("  Gateway reiniciado!")
        return True
    else:
        print(f"  ERRO ao reiniciar: {output}")
        # Tentar método alternativo
        rc2, output2 = run_cmd("printf 'y\\ny\\n\\n' | hermes gateway install 2>&1")
        if rc2 == 0:
            print("  Gateway reiniciado via install!")
            return True
        print(f"  ERRO alternativo: {output2}")
        return False


def log_update(result: dict):
    """Registra resultado da atualização."""
    logs = []
    if UPDATE_LOG.exists():
        with open(UPDATE_LOG, "r") as f:
            logs = json.load(f)

    logs.append({
        "timestamp": datetime.now().isoformat(),
        **result
    })

    # Manter apenas últimos 50 logs
    logs = logs[-50:]

    with open(UPDATE_LOG, "w") as f:
        json.dump(logs, f, indent=2, ensure_ascii=False)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Hermes Auto-Update")
    parser.add_argument("--check-only", action="store_true", help="Apenas verificar")
    parser.add_argument("--force", action="store_true", help="Forçar atualização")
    parser.add_argument("--no-restart", action="store_true", help="Não reiniciar gateway")
    args = parser.parse_args()

    print("="*50)
    print("Hermes Auto-Update")
    print("="*50)

    # Versão atual
    version = get_current_version()
    print(f"Versão atual: {version}")

    # Verificar atualizações
    update_info = check_updates()
    print(f"Última versão: {update_info['latest']}")
    print(f"Atualização disponível: {update_info['update_available']}")

    if args.check_only:
        return

    if not update_info["update_available"] and not args.force:
        print("Nenhuma atualização necessária.")
        return

    # Criar backup
    backup_path = create_backup()

    # Aplicar atualização
    success = apply_update()

    result = {
        "version_before": version,
        "version_after": get_current_version(),
        "backup_path": backup_path,
        "update_success": success,
    }

    if success and not args.no_restart:
        restarted = restart_gateway()
        result["restart_success"] = restarted

    # Log
    log_update(result)

    print("\n" + "="*50)
    print(f"Resultado: {'SUCESSO' if success else 'FALHA'}")
    print(f"Backup: {backup_path}")
    print("="*50)


if __name__ == "__main__":
    main()
