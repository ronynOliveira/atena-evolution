#!/usr/bin/env python3
"""Hermes auto-update with logging, version detection, and gateway control."""

import argparse
import logging
import os
import platform
import re
import shutil
import signal
import subprocess

# Windows: CREATE_NO_WINDOW to prevent CMD flash
WIN_FLAGS = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
import sys
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path

IS_WINDOWS = platform.system() == "Windows"
DEFAULT_REPO_ROOT = Path(
    os.environ.get(
        "HERMES_REPO_ROOT",
        r"C:\Users\dell-\AppData\Local\hermes\hermes-agent",
    )
)
DEFAULT_LOG_DIR = Path(
    os.environ.get(
        "HERMES_AUTO_UPDATE_LOG_DIR",
        str(DEFAULT_REPO_ROOT.parent / "logs"),
    )
)
HERMES_BIN = os.environ.get("HERMES_BIN", "hermes")
HERMES_GATEWAY_SCRIPT = DEFAULT_REPO_ROOT / "scripts" / "hermes-gateway"
PID_FILE = DEFAULT_REPO_ROOT.parent / "gateway.pid"
LOCK_FILE = DEFAULT_REPO_ROOT.parent / "gateway.lock"
LOG_FILE_NAME = "auto_update.log"
UPDATE_TIMEOUT = 600
GATEWAY_STOP_TIMEOUT = 30
GATEWAY_START_TIMEOUT = 60

VERSION_RE = re.compile(r"v?(\d+)\.(\d+)\.(\d+)")


def setup_logging(verbose: bool = False, log_dir: Path = DEFAULT_LOG_DIR) -> logging.Logger:
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("hermes.auto_update")
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    logger.handlers.clear()

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(
        log_dir / LOG_FILE_NAME,
        maxBytes=2 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(fmt)
    file_handler.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)

    console = logging.StreamHandler(sys.stderr)
    console.setFormatter(fmt)
    console.setLevel(logging.DEBUG if verbose else logging.INFO)
    logger.addHandler(console)

    return logger


def resolve_hermes() -> str:
    path = shutil.which(HERMES_BIN)
    if path:
        return path
    fallback = DEFAULT_REPO_ROOT / "venv" / "Scripts" / ("hermes.exe" if IS_WINDOWS else "hermes")
    if fallback.exists():
        return str(fallback)
    return HERMES_BIN


def run_cmd(
    cmd,
    *,
    cwd=None,
    check=True,
    capture=True,
    timeout=None,
    env=None,
    input_text=None,
    logger=None,
) -> subprocess.CompletedProcess:
    popen_kwargs = dict(
        cwd=str(cwd) if cwd else None,
        check=False,
        capture_output=capture,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        env=env,
    )
    if input_text is not None:
        popen_kwargs["input"] = input_text

    log = logger or logging.getLogger("hermes.auto_update")
    log.debug("RUN: %s (cwd=%s)", " ".join(str(c) for c in cmd), cwd or os.getcwd())
    try:
        result = subprocess.run(cmd, **popen_kwargs,
                       creationflags=WIN_FLAGS)
    except FileNotFoundError as exc:
        log.error("Command not found: %s (%s)", cmd[0], exc)
        if check:
            raise
        return subprocess.CompletedProcess(cmd, 127, "", str(exc))
    except subprocess.TimeoutExpired as exc:
        log.error("Command timed out after %ss: %s", timeout, " ".join(str(c) for c in cmd))
        if check:
            raise
        return subprocess.CompletedProcess(cmd, 124, exc.stdout or "", exc.stderr or "")

    if capture:
        stdout = (result.stdout or "").strip()
        stderr = (result.stderr or "").strip()
        if stdout:
            log.debug("STDOUT: %s", stdout[:2000])
        if stderr:
            log.debug("STDERR: %s", stderr[:2000])

    if check and result.returncode != 0:
        log.error(
            "Command failed (exit=%d): %s",
            result.returncode,
            " ".join(str(c) for c in cmd),
        )
        raise subprocess.CalledProcessError(
            result.returncode, cmd, result.stdout, result.stderr
        )
    return result


def git_fetch_tags(repo_root: Path, logger: logging.Logger) -> None:
    logger.info("Fetching tags from origin (git fetch --tags)...")
    run_cmd(["git", "fetch", "--tags", "--prune", "--prune-tags"], cwd=repo_root, check=True, logger=logger)
    run_cmd(["git", "fetch", "origin"], cwd=repo_root, check=False, logger=logger)


def parse_version(tag: str):
    if not tag:
        return None
    m = VERSION_RE.search(tag)
    if not m:
        return None
    try:
        return tuple(int(x) for x in m.groups())
    except ValueError:
        return None


def get_current_version(repo_root: Path, logger: logging.Logger):
    logger.info("Resolving current version...")
    result = run_cmd(
        ["git", "describe", "--tags", "--abbrev=0"],
        cwd=repo_root,
        check=False,
        logger=logger,
    )
    if result.returncode == 0 and result.stdout:
        tag = result.stdout.strip()
        ver = parse_version(tag)
        if ver:
            logger.info("Current version (tag): %s -> %s", tag, ver)
            return tag, ver
    result = run_cmd(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=repo_root,
        check=False,
        logger=logger,
    )
    sha = result.stdout.strip() if result.returncode == 0 else "unknown"
    logger.warning("No version tag on HEAD; commit=%s", sha)
    return sha, None


def get_latest_version(repo_root: Path, logger: logging.Logger):
    logger.info("Resolving latest version from remote tags...")
    result = run_cmd(
        ["git", "tag", "--list", "--sort=-v:refname"],
        cwd=repo_root,
        check=False,
        logger=logger,
    )
    if result.returncode != 0 or not result.stdout:
        logger.warning("No tags found on disk after fetch.")
        return None, None
    for line in result.stdout.splitlines():
        tag = line.strip()
        if not tag:
            continue
        ver = parse_version(tag)
        if ver:
            logger.info("Latest version (tag): %s -> %s", tag, ver)
            return tag, ver
    logger.warning("Tags exist but none match semver pattern: %s", result.stdout[:500])
    return None, None


def has_update(current_ver, latest_ver, logger: logging.Logger) -> bool:
    if latest_ver is None:
        logger.info("Cannot determine latest version; assuming update available.")
        return True
    if current_ver is None:
        logger.info("Current version unknown; assuming update available.")
        return True
    if latest_ver > current_ver:
        logger.info("Update available: %s < %s", current_ver, latest_ver)
        return True
    logger.info("Already up to date: %s >= %s", current_ver, latest_ver)
    return False


def check_for_update(repo_root: Path, logger: logging.Logger):
    git_fetch_tags(repo_root, logger)
    current_tag, current_ver = get_current_version(repo_root, logger)
    latest_tag, latest_ver = get_latest_version(repo_root, logger)
    available = has_update(current_ver, latest_ver, logger)
    return {
        "current_tag": current_tag,
        "current_version": current_ver,
        "latest_tag": latest_tag,
        "latest_version": latest_ver,
        "update_available": available,
    }


def read_pid_file(path: Path, logger: logging.Logger):
    if not path.exists():
        return None
    try:
        raw = path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        logger.warning("Could not read PID file %s: %s", path, exc)
        return None
    if not raw:
        return None
    try:
        return int(raw.split()[0])
    except ValueError:
        logger.warning("PID file %s has non-integer content: %r", path, raw)
        return None


def pid_alive(pid: int) -> bool:
    if not IS_WINDOWS:
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False
    try:
        result = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
            creationflags=WIN_FLAGS,
        )
        return f"{pid}" in (result.stdout or "")
    except (subprocess.SubprocessError, OSError):
        return False


def kill_pid_powershell(pid: int, logger: logging.Logger) -> bool:
    if not pid_alive(pid):
        logger.info("PID %d not alive; nothing to kill.", pid)
        return True
    logger.info("Killing PID %d via PowerShell Stop-Process -Force...", pid)
    if IS_WINDOWS:
        ps_cmd = [
            "powershell",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            f"Stop-Process -Id {pid} -Force -ErrorAction SilentlyContinue; exit 0",
        ]
        try:
            run_cmd(ps_cmd, check=False, logger=logger)
        except Exception as exc:
            logger.warning("PowerShell Stop-Process failed for %d: %s", pid, exc)
    else:
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError as exc:
            logger.warning("SIGTERM to %d failed: %s", pid, exc)
    deadline = time.time() + 10
    while time.time() < deadline:
        if not pid_alive(pid):
            logger.info("PID %d terminated.", pid)
            return True
        time.sleep(0.5)
    logger.warning("PID %d still alive after 10s; falling back to taskkill.", pid)
    run_cmd(["taskkill", "/F", "/PID", str(pid)], check=False, logger=logger)
    time.sleep(1)
    return not pid_alive(pid)


def kill_hermes_processes(logger: logging.Logger) -> int:
    logger.info("Killing any running hermes.exe processes (Windows file lock workaround)...")
    killed = 0
    if IS_WINDOWS:
        result = run_cmd(
            ["taskkill", "/F", "/IM", "hermes.exe", "/T"],
            check=False,
            logger=logger,
        )
        if "SUCCESS" in (result.stdout or "") or "ÊXITO" in (result.stdout or ""):
            killed += 1
        run_cmd(
            [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                "Get-Process hermes -ErrorAction SilentlyContinue | Stop-Process -Force; exit 0",
            ],
            check=False,
            logger=logger,
        )
    else:
        run_cmd(["pkill", "-9", "-f", "hermes"], check=False, logger=logger)
    time.sleep(2)
    return killed


def stop_gateway(repo_root: Path, logger: logging.Logger) -> bool:
    logger.info("Stopping gateway (hermes gateway stop)...")
    hermes = resolve_hermes()
    try:
        run_cmd(
            [hermes, "gateway", "stop"],
            cwd=repo_root,
            check=False,
            timeout=GATEWAY_STOP_TIMEOUT,
            logger=logger,
        )
    except Exception as exc:
        logger.warning("hermes gateway stop raised: %s", exc)

    pid = read_pid_file(PID_FILE, logger)
    if pid is not None:
        kill_pid_powershell(pid, logger)

    if LOCK_FILE.exists():
        try:
            LOCK_FILE.unlink()
            logger.info("Removed stale lock file: %s", LOCK_FILE)
        except OSError as exc:
            logger.warning("Could not remove lock %s: %s", LOCK_FILE, exc)

    deadline = time.time() + 10
    while time.time() < deadline:
        pid = read_pid_file(PID_FILE, logger)
        if pid is None or not pid_alive(pid):
            logger.info("Gateway is down.")
            return True
        time.sleep(1)
    logger.error("Gateway did not stop in time.")
    return False


def start_gateway(repo_root: Path, logger: logging.Logger) -> bool:
    logger.info("Starting gateway (hermes gateway start)...")
    hermes = resolve_hermes()
    try:
        result = run_cmd(
            [hermes, "gateway", "start"],
            cwd=repo_root,
            check=False,
            timeout=GATEWAY_START_TIMEOUT,
            logger=logger,
        )
        if result.returncode == 0:
            logger.info("Gateway start returned 0.")
            return True
        logger.warning("hermes gateway start exit=%d", result.returncode)
    except Exception as exc:
        logger.error("hermes gateway start raised: %s", exc)

    if HERMES_GATEWAY_SCRIPT.exists():
        logger.info("Falling back to direct gateway script invocation...")
        try:
            py = repo_root / "venv" / ("Scripts" if IS_WINDOWS else "bin") / (
                "python.exe" if IS_WINDOWS else "python"
            )
            py = str(py) if py.exists() else sys.executable
            subprocess.Popen(
                [py, str(HERMES_GATEWAY_SCRIPT)],
                cwd=str(repo_root),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                close_fds=not IS_WINDOWS,
                creationflags=WIN_FLAGS,
            )
            time.sleep(3)
            pid = read_pid_file(PID_FILE, logger)
            if pid and pid_alive(pid):
                logger.info("Gateway launched via script (pid=%d).", pid)
                return True
        except Exception as exc:
            logger.error("Direct gateway launch failed: %s", exc)
    return False


def run_hermes_update(repo_root: Path, auto: bool, logger: logging.Logger) -> int:
    hermes = resolve_hermes()
    args = [hermes, "update", "--yes"]
    if auto:
        args.append("--non-interactive")
    logger.info("Running: %s (cwd=%s)", " ".join(args), repo_root)
    try:
        result = run_cmd(
            args,
            cwd=repo_root,
            check=False,
            timeout=UPDATE_TIMEOUT,
            capture=True,
            logger=logger,
        )
    except subprocess.TimeoutExpired:
        logger.error("Update timed out after %ss.", UPDATE_TIMEOUT)
        return 124
    return result.returncode


def cmd_check_only(args, logger: logging.Logger) -> int:
    try:
        info = check_for_update(args.repo_root, logger)
    except Exception as exc:
        logger.error("Check failed: %s", exc)
        return 1
    print(f"current={info['current_tag']} latest={info['latest_tag']} update_available={info['update_available']}")
    return 0 if not info["update_available"] else 0


def cmd_apply(args, logger: logging.Logger) -> int:
    repo_root: Path = args.repo_root
    try:
        info = check_for_update(repo_root, logger)
        if not info["update_available"]:
            logger.info("No update needed; nothing to do.")
            return 0

        logger.info("Update path: %s -> %s", info["current_tag"], info["latest_tag"])

        gateway_was_running = False
        pid = read_pid_file(PID_FILE, logger)
        if pid is not None and pid_alive(pid):
            gateway_was_running = True
        elif HERMES_GATEWAY_SCRIPT.exists():
            gateway_was_running = True

        stopped = stop_gateway(repo_root, logger)
        if not stopped:
            logger.warning("Gateway may still be running; proceeding with caution.")

        kill_hermes_processes(logger)

        rc = run_hermes_update(repo_root, args.auto, logger)
        if rc != 0:
            logger.error("Update failed (exit=%d). Will attempt to restart gateway.", rc)
            if gateway_was_running:
                start_gateway(repo_root, logger)
            return rc

        if gateway_was_running:
            started = start_gateway(repo_root, logger)
            if not started:
                logger.error("Update succeeded but gateway did not start!")
                return 2
        else:
            logger.info("Gateway was not running; skipping start.")

        logger.info("Auto-update finished successfully.")
        return 0

    except subprocess.CalledProcessError as exc:
        logger.error("Subprocess failed: %s (exit=%d)", exc.cmd, exc.returncode)
        try:
            start_gateway(repo_root, logger)
        except Exception as restart_exc:
            logger.error("Could not restart gateway after failure: %s", restart_exc)
        return exc.returncode or 1
    except KeyboardInterrupt:
        logger.warning("Interrupted by user.")
        try:
            start_gateway(repo_root, logger)
        except Exception:
            pass
        return 130
    except Exception as exc:
        logger.exception("Unexpected error: %s", exc)
        try:
            start_gateway(repo_root, logger)
        except Exception:
            pass
        return 1


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="auto_update",
        description="Hermes auto-update: check tags, stop gateway, update, restart gateway.",
    )
    p.add_argument(
        "--check-only",
        action="store_true",
        help="Only check for updates (git fetch --tags + version compare). Do not modify anything.",
    )
    p.add_argument(
        "--auto",
        action="store_true",
        help="Run in non-interactive / auto mode. Passes --non-interactive to hermes update and assumes yes.",
    )
    p.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help=f"Path to hermes-agent repo root (default: {DEFAULT_REPO_ROOT})",
    )
    p.add_argument(
        "--log-dir",
        type=Path,
        default=DEFAULT_LOG_DIR,
        help=f"Directory for log file (default: {DEFAULT_LOG_DIR})",
    )
    p.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable DEBUG-level logging.",
    )
    return p


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()
    logger = setup_logging(verbose=args.verbose, log_dir=args.log_dir)
    logger.info("=" * 60)
    logger.info("Hermes auto-update starting (check_only=%s, auto=%s)", args.check_only, args.auto)
    logger.info("Repo root: %s", args.repo_root)
    logger.info("Log file: %s", args.log_dir / LOG_FILE_NAME)

    if not args.repo_root.exists():
        logger.error("Repo root does not exist: %s", args.repo_root)
        return 1

    if args.check_only:
        return cmd_check_only(args, logger)
    return cmd_apply(args, logger)


if __name__ == "__main__":
    sys.exit(main())
