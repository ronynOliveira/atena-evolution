#!/usr/bin/env python3
"""
Backup automático do wiki do Projeto Atena.
Cria um repositório git local e faz commit/push periódico.
Se GITHUB_TOKEN estiver configurado, push para GitHub.
Se não, mantém backup local.

Autor: OWL (Batedor da Nuvem)
Data: 2026-05-20
"""

import subprocess
import sys
import os
import logging
from datetime import datetime

logging.basicConfig(level=logging.WARNING, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

WIKI_PATH = os.path.join(os.path.expanduser("~"), "wiki")
BACKUP_LOG = os.path.join(WIKI_PATH, "_meta", "backup-log.md")


def inicializar_git():
    """Inicializa repositório git no wiki se não existir."""
    git_dir = os.path.join(WIKI_PATH, ".git")
    if os.path.exists(git_dir):
        print("  Git já inicializado")
        return True

    print("  Inicializando git...")
    try:
        subprocess.run(
            ["git", "init"],
            cwd=WIKI_PATH, capture_output=True, text=True, timeout=30
        )
        # Configura usuário
        subprocess.run(
            ["git", "config", "user.email", "owl@projeto-atena.local"],
            cwd=WIKI_PATH, capture_output=True, text=True, timeout=10
        )
        subprocess.run(
            ["git", "config", "user.name", "OWL (Batedor da Nuvem)"],
            cwd=WIKI_PATH, capture_output=True, text=True, timeout=10
        )
        # Cria .gitignore
        gitignore = os.path.join(WIKI_PATH, ".gitignore")
        with open(gitignore, "w") as f:
            f.write("_archive/\n_meta/*.tmp\n")
        print("  Git inicializado com sucesso")
        return True
    except Exception as e:
        print(f"  Erro ao inicializar git: {e}")
        return False


def fazer_backup():
    """Faz commit de todas as mudanças no wiki."""
    print("  Verificando mudanças...")

    try:
        # Adiciona todas as mudanças
        subprocess.run(
            ["git", "add", "-A"],
            cwd=WIKI_PATH, capture_output=True, text=True, timeout=30
        )

        # Verifica se há mudanças para commitar
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=WIKI_PATH, capture_output=True, text=True, timeout=10
        )

        if not result.stdout.strip():
            print("  Nenhuma mudança detectada")
            return {"status": "sem_mudancas"}

        # Conta arquivos alterados
        files = result.stdout.strip().split("\n")
        print(f"  {len(files)} arquivo(s) alterado(s)")

        # Commit
        agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        commit_msg = f"backup automático — {agora} — {len(files)} arquivo(s)"

        subprocess.run(
            ["git", "commit", "-m", commit_msg],
            cwd=WIKI_PATH, capture_output=True, text=True, timeout=30
        )

        print(f"  Commit: {commit_msg}")

        # Tenta push se GITHUB_TOKEN estiver configurado
        github_token = os.environ.get("GITHUB_TOKEN", "")
        if not github_token:
            # Tenta ler do config do gh CLI
            try:
                result = subprocess.run(
                    ["/c/Program Files/GitHub CLI/gh.exe", "auth", "token"],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    github_token = result.stdout.strip()
            except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as e:
                logger.debug("gh CLI nao encontrado ou erro ao ler token: %s", e)

        if github_token:
            print("  Token encontrado, tentando push...")
            # Configura remote com token
            remote_url = f"https://x-access-token:{github_token}@github.com/projeto-atena/wiki.git"
            subprocess.run(
                ["git", "remote", "add", "origin", remote_url],
                cwd=WIKI_PATH, capture_output=True, text=True, timeout=10
            )
            push_result = subprocess.run(
                ["git", "push", "-u", "origin", "main"],
                cwd=WIKI_PATH, capture_output=True, text=True, timeout=60
            )
            if push_result.returncode == 0:
                print("  Push para GitHub: sucesso")
                return {"status": "ok", "files": len(files), "pushed": True}
            else:
                print(f"  Push falhou: {push_result.stderr[:200]}")
                return {"status": "ok_local", "files": len(files), "pushed": False}
        else:
            print("  GITHUB_TOKEN não configurado — backup local apenas")
            return {"status": "ok_local", "files": len(files), "pushed": False}

    except Exception as e:
        print(f"  Erro no backup: {e}")
        return {"status": "erro", "message": str(e)}


def registrar_log(resultado):
    """Registra o resultado do backup no log."""
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    entrada = f"\n## [{agora}] backup | "
    if resultado["status"] == "ok":
        entrada += f"✅ {resultado['files']} arquivo(s) — push OK"
    elif resultado["status"] == "ok_local":
        entrada += f"✅ {resultado['files']} arquivo(s) — local (sem GITHUB_TOKEN)"
    elif resultado["status"] == "sem_mudancas":
        entrada += "✅ Sem mudanças"
    else:
        entrada += f"❌ Erro: {resultado.get('message', 'desconhecido')}"

    os.makedirs(os.path.dirname(BACKUP_LOG), exist_ok=True)
    with open(BACKUP_LOG, "a", encoding="utf-8") as f:
        f.write(entrada + "\n")


def main():
    print("=" * 50)
    print("BACKUP AUTOMÁTICO DO WIKI — PROJETO ATENA")
    print("=" * 50)
    print(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Wiki: {WIKI_PATH}")
    print()

    if not os.path.exists(WIKI_PATH):
        print("❌ Wiki não encontrado!")
        return 1

    # Inicializa git se necessário
    if not inicializar_git():
        print("❌ Falha ao inicializar git")
        return 1

    # Faz backup
    resultado = fazer_backup()

    # Registra log
    registrar_log(resultado)

    print()
    print("=" * 50)
    if resultado["status"] in ("ok", "ok_local", "sem_mudancas"):
        print("✅ Backup concluído")
    else:
        print("❌ Backup falhou")
    print("=" * 50)

    return 0


if __name__ == "__main__":
    sys.exit(main())
