"""check_hermes_update.py — Verificador/Atualizador do Hermes Agent.

Compara a versão local do Hermes Agent com a versão remota publicada no
GitHub (https://github.com/nousresearch/hermes-agent). Quando há
atualização, oferece a opção de atualizar via ``git pull`` + ``pip install
-e .`` após desligar o gateway (e religar no final).

Modos de uso:
    python check_hermes_update.py                 # interativo (pergunta)
    python check_hermes_update.py --auto          # atualiza sem perguntar
    python check_hermes_update.py --check-only    # só verifica, não atualiza

Códigos de saída:
    0  — versão local é a mais recente (ou update aplicado com sucesso)
    1  — atualização disponível (e não foi aplicada)
    2  — erro de execução

Compatível com Windows (PowerShell / Git-Bash) e Linux/macOS.
"""

from __future__ import annotations

import argparse
import logging
import os
import re
import subprocess

# Windows: CREATE_NO_WINDOW to prevent CMD flash
WIN_FLAGS = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

GITHUB_REPO = "nousresearch/hermes-agent"
GITHUB_URL = f"https://github.com/{GITHUB_REPO}"
VERSION_RE = re.compile(r"v?(\d{4})\.(\d+)\.(\d+)(?:\.(\d+))?")


def setup_logging() -> logging.Logger:
    """Configura logger com saída para arquivo + console."""
    log_dir = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "hermes" / "logs"
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        log_dir = Path.home() / ".hermes" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "hermes_update.log"

    logger = logging.getLogger("hermes_update")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    fmt = logging.Formatter(
        fmt="[%(asctime)s] %(levelname)-7s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    try:
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    except OSError as exc:
        sys.stderr.write(f"[warn] Não foi possível abrir log file: {exc}\n")

    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    logger.addHandler(sh)
    return logger


def run_cmd(cmd, *, cwd: Optional[str] = None, timeout: int = 60) -> Tuple[int, str, str]:
    """Executa comando e retorna (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=isinstance(cmd, str),
            creationflags=WIN_FLAGS,
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired as exc:
        return 124, "", f"Timeout após {timeout}s: {exc}"
    except FileNotFoundError as exc:
        return 127, "", f"Comando não encontrado: {exc}"
    except Exception as exc:
        return 1, "", f"Erro inesperado: {exc}"


def parse_version(tag: str) -> Optional[Tuple[int, int, int, int]]:
    """Converte 'v2026.5.29.2' -> (2026, 5, 29, 2). Sem patch -> 0."""
    if not tag:
        return None
    m = VERSION_RE.search(tag)
    if not m:
        return None
    y, mo, d, p = m.groups()
    return int(y), int(mo), int(d), int(p or 0)


def get_current_version(logger: logging.Logger) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Roda ``hermes --version`` e retorna (version_tag, project_path, raw_output).

    O output típico é ``Hermes Agent v0.15.1 (2026.5.29)`` — versão semver
    + data entre parênteses. As tags git são date-based (``v2026.5.29.2``),
    então priorizamos a data para que a comparação com as tags funcione.
    """
    code, out, err = run_cmd(["hermes", "--version"], timeout=30)
    if code != 0:
        logger.error("Falha ao executar 'hermes --version' (rc=%s): %s", code, err.strip())
        return None, None, out + err
    raw = out + err

    date_match = re.search(r"\((\d{4}\.\d+\.\d+(?:\.\d+)?)\)", raw)
    semver_match = re.search(r"v(\d+\.\d+\.\d+(?:\.\d+)?)", raw)

    version: Optional[str] = None
    if date_match:
        version = f"v{date_match.group(1)}"
    elif semver_match:
        version = f"v{semver_match.group(1)}"

    path_match = re.search(r"Project:\s*(\S+)", raw)
    project_path = path_match.group(1).strip() if path_match else None

    logger.info("Versão local detectada: %s", version or "<desconhecida>")
    if project_path:
        logger.info("Projeto: %s", project_path)
    return version, project_path, raw


def find_repo_dir(project_path: Optional[str], logger: logging.Logger) -> Optional[Path]:
    """Tenta descobrir o diretório do repositório hermes-agent."""
    candidates: list[Path] = []
    if project_path:
        candidates.append(Path(project_path))
    candidates.append(Path.home() / "AppData" / "Local" / "hermes" / "hermes-agent")
    candidates.append(Path("/usr/local/hermes-agent"))
    candidates.append(Path("/opt/hermes-agent"))

    for cand in candidates:
        try:
            if cand.is_dir() and (cand / ".git").exists():
                logger.info("Repositório encontrado: %s", cand)
                return cand
        except OSError:
            continue
    return None


def fetch_latest_tag(repo_dir: Path, logger: logging.Logger) -> Optional[str]:
    """Executa ``git fetch --tags`` e retorna a tag mais recente."""
    logger.info("Rodando 'git fetch --tags' em %s ...", repo_dir)
    code, _, err = run_cmd(["git", "fetch", "--tags", "--prune", "--force"], cwd=str(repo_dir), timeout=120)
    if code != 0:
        logger.warning("git fetch falhou (rc=%s): %s", code, err.strip())
    else:
        logger.info("git fetch --tags concluído.")

    code, out, err = run_cmd(
        ["git", "tag", "--sort=-version:refname"],
        cwd=str(repo_dir),
        timeout=30,
    )
    if code != 0 or not out.strip():
        logger.error("Não foi possível listar tags locais: %s", err.strip())
        return None

    tags = [t.strip() for t in out.splitlines() if t.strip()]
    for tag in tags:
        if parse_version(tag):
            logger.info("Tag mais recente (local): %s", tag)
            return tag
    logger.error("Nenhuma tag válida encontrada no repositório.")
    return None


def is_gateway_running(logger: logging.Logger) -> bool:
    """Detecta se o gateway está rodando (Windows e Unix)."""
    code, out, _ = run_cmd(["hermes", "gateway", "status"], timeout=20)
    if code == 0 and out:
        low = out.lower()
        if any(k in low for k in ("running", "active", "started", "online", "up")):
            if any(k in low for k in ("stopped", "inactive", "not running", "down")):
                return False
            return True
        if any(k in low for k in ("stopped", "inactive", "not running", "down")):
            return False
    if os.name == "nt":
        code, out, _ = run_cmd(["tasklist"], timeout=15)
        return "hermes.exe" in out.lower() or "gateway" in out.lower()
    code, out, _ = run_cmd(["pgrep", "-af", "hermes"], timeout=15)
    return bool(out.strip())


def stop_gateway(logger: logging.Logger) -> bool:
    """Tenta parar o gateway; retorna True se conseguiu ou se já estava parado."""
    logger.info("Parando gateway...")
    code, out, err = run_cmd(["hermes", "gateway", "stop"], timeout=60)
    if code == 0:
        logger.info("Gateway parado com sucesso.")
        return True
    logger.warning("'hermes gateway stop' falhou (rc=%s): %s%s", code, out.strip(), err.strip())

    if os.name == "nt":
        code, _, _ = run_cmd(["taskkill", "/F", "/IM", "hermes.exe"], timeout=30)
        if code == 0:
            logger.info("Processos hermes.exe finalizados via taskkill.")
            return True
    else:
        code, _, _ = run_cmd(["pkill", "-f", "hermes"], timeout=30)
        if code == 0:
            logger.info("Processos hermes finalizados via pkill.")
            return True
    return False


def start_gateway(logger: logging.Logger) -> bool:
    """Religa o gateway após o update."""
    logger.info("Reiniciando gateway...")
    code, out, err = run_cmd(["hermes", "gateway", "start"], timeout=60)
    if code == 0:
        logger.info("Gateway reiniciado.")
        return True
    logger.error("Falha ao reiniciar gateway (rc=%s): %s%s", code, out.strip(), err.strip())
    return False


def perform_update(repo_dir: Path, logger: logging.Logger) -> bool:
    """Executa git pull + pip install -e . no diretório do repo."""
    logger.info("Executando 'git pull --ff-only' em %s ...", repo_dir)
    code, out, err = run_cmd(["git", "pull", "--ff-only"], cwd=str(repo_dir), timeout=180)
    logger.info("git pull stdout: %s", out.strip() or "<vazio>")
    if err.strip():
        logger.warning("git pull stderr: %s", err.strip())
    if code != 0:
        logger.error("git pull falhou (rc=%s). Tentando 'git pull --rebase'...", code)
        code2, out2, err2 = run_cmd(["git", "pull", "--rebase"], cwd=str(repo_dir), timeout=180)
        if code2 != 0:
            logger.error("git pull --rebase também falhou (rc=%s): %s", code2, err2.strip())
            return False
        logger.info("git pull --rebase OK: %s", out2.strip())

    logger.info("Executando 'pip install -e .' (pode demorar)...")
    code, out, err = run_cmd(
        [sys.executable, "-m", "pip", "install", "-e", "."],
        cwd=str(repo_dir),
        timeout=900,
    )
    tail = "\n".join((out + err).splitlines()[-20:])
    logger.info("pip install tail:\n%s", tail)
    if code != 0:
        logger.error("pip install -e . falhou (rc=%s)", code)
        return False
    logger.info("Update aplicado com sucesso.")
    return True


def ask_for_confirmation(latest_tag: str, current: Optional[str], logger: logging.Logger) -> bool:
    """Pergunta ao usuário se deseja atualizar. Default: sim."""
    print()
    print(f"  Versão atual : {current or '<desconhecida>'}")
    print(f"  Versão nova  : {latest_tag}")
    print()
    try:
        ans = input(f"Aplicar update agora? [S/n]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        logger.info("Entrada cancelada pelo usuário.")
        return False
    if ans in ("", "s", "sim", "y", "yes"):
        return True
    logger.info("Usuário cancelou o update.")
    return False


def compare_versions(current: Optional[str], latest: str, logger: logging.Logger) -> int:
    """Compara duas tags. Retorna -1, 0, 1 (current vs latest)."""
    c = parse_version(current or "")
    l = parse_version(latest)
    if c is None or l is None:
        logger.warning("Não foi possível comparar versões (current=%s, latest=%s).", current, latest)
        return 0
    if c < l:
        return -1
    if c > l:
        return 1
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="check_hermes_update",
        description="Verifica e aplica atualizações do Hermes Agent.",
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Atualiza automaticamente sem perguntar ao usuário.",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Apenas verifica se há atualização; não modifica nada.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    logger = setup_logging()
    logger.info("=" * 60)
    logger.info("Iniciando verificação de update do Hermes Agent")
    logger.info("Args: auto=%s check_only=%s", args.auto, args.check_only)

    try:
        current, project_path, _ = get_current_version(logger)
    except Exception as exc:
        logger.exception("Erro ao obter versão atual: %s", exc)
        return 2

    repo_dir = find_repo_dir(project_path, logger)
    if not repo_dir:
        logger.error(
            "Não foi possível localizar o repositório hermes-agent. "
            "Defina a variável HERMES_REPO_DIR ou instale a partir de %s.",
            GITHUB_URL,
        )
        return 2

    try:
        latest = fetch_latest_tag(repo_dir, logger)
    except Exception as exc:
        logger.exception("Erro ao buscar tags remotas: %s", exc)
        return 2

    if not latest:
        logger.error("Falha ao determinar a tag mais recente.")
        return 2

    cmp = compare_versions(current, latest, logger)
    logger.info("Comparação: current=%s latest=%s -> %s", current, latest, cmp)

    if cmp >= 0:
        logger.info("Hermes Agent já está na versão mais recente (%s).", current or latest)
        return 0

    logger.warning("Atualização disponível: %s -> %s", current, latest)

    if args.check_only:
        print(f"Atualização disponível: {current} -> {latest}")
        return 1

    if not args.auto:
        if not ask_for_confirmation(latest, current, logger):
            print("Update cancelado pelo usuário.")
            return 1
    else:
        logger.info("Modo --auto: prosseguindo sem perguntar.")

    gateway_was_running = False
    try:
        try:
            gateway_was_running = is_gateway_running(logger)
        except Exception as exc:
            logger.warning("Não foi possível checar gateway: %s", exc)

        if gateway_was_running:
            stop_gateway(logger)
            time.sleep(2)

        ok = perform_update(repo_dir, logger)
        if not ok:
            logger.error("Update falhou.")
            if gateway_was_running:
                start_gateway(logger)
            return 2

        try:
            new_version, _, _ = get_current_version(logger)
            logger.info("Versão pós-update: %s", new_version)
        except Exception as exc:
            logger.warning("Não foi possível reler a versão após update: %s", exc)

    finally:
        if gateway_was_running:
            try:
                start_gateway(logger)
            except Exception as exc:
                logger.exception("Falha ao religar gateway: %s", exc)

    logger.info("Verificação concluída com sucesso.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.stderr.write("\n[abort] Interrompido pelo usuário.\n")
        sys.exit(2)
    except Exception as exc:
        sys.stderr.write(f"[fatal] {exc}\n")
        sys.exit(2)
