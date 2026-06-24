#!/usr/bin/env python3
"""
security_watchdog.py — Real-time file integrity and credential leak monitor

Monitors sensitive files (.env, config.yaml, composio keys) for permission
and attribute changes every 5 minutes. Scans scripts/ for new files containing
API key / credential patterns. Logs all events to security_watchdog.log and
integrates with the Memory Tree scorer for persistent event tracking.

Usage:
    python security_watchdog.py               # Run single check (cron-friendly)
    python security_watchdog.py --watch        # Run continuously every 5 min
    python security_watchdog.py --check-only   # Run once, exit (same as default)
"""

import argparse
import datetime
import hashlib
import json
import logging
import os
import re
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ── Paths ─────────────────────────────────────────────────────────────
HERMES_HOME = Path(os.environ.get(
    "HERMES_HOME",
    os.path.join(str(Path.home()), "AppData/Local/hermes"),
))
SCRIPTS_DIR = HERMES_HOME / "scripts"
LOGS_DIR = HERMES_HOME / "logs"
LIB_DIR = HERMES_HOME / "lib"
LOG_FILE = LOGS_DIR / "security_watchdog.log"
STATE_FILE = LIB_DIR / "security_watchdog_state.json"

# Ensure lib dir is on sys.path so memory_scorer can be imported
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

# ── Configuration ─────────────────────────────────────────────────────
SENSITIVE_FILE_PATTERNS = [
    ".env",
    "config.yaml",
    "config.yml",
    "composio_key",
    "composio_credentials.json",
    ".composio_auth.json",
    "*.pem",
    "*.key",
    "id_rsa",
    "id_ed25519",
    ".netrc",
    ".git-credentials",
]

# API key / credential regexes
API_KEY_PATTERNS = [
    re.compile(r"(?i)(?:api[_-]?key|apikey|api[_-]secret|api_secret_key"
               r"|secret_key|access_key|auth_token|token|password|passwd"
               r"|credential)\s*[:=]\s*[\"']?[A-Za-z0-9_\-@#$%^&+=]{16,}[\"']?"),
    re.compile(r"(?i)sk-[A-Za-z0-9]{20,}"),            # OpenAI
    re.compile(r"(?i)ghp_[A-Za-z0-9]{36}"),            # GitHub PAT
    re.compile(r"(?i)gho_[A-Za-z0-9]{36}"),            # GitHub OAuth
    re.compile(r"(?i)AKIA[0-9A-Z]{16}"),               # AWS access key
    re.compile(r"(?i)eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\."
               r"[A-Za-z0-9_\-]{10,}"),                # JWT
    re.compile(r"(?i)xox[prba]-[A-Za-z0-9-]{10,}"),   # Slack tokens
    re.compile(r"(?:-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----)"),  # Private keys
]

# Directories to scan for sensitive files (targeted, no broad rglob)
SEARCH_ROOTS: List[Path] = [
    HERMES_HOME,
]

# Additional specific file locations to check (not recursively scanned)
ADDITIONAL_LOCATIONS: List[Path] = [
    Path.home(),                              # C:\Users\<user>
    Path.home() / ".ssh",
    HERMES_HOME / "config",
    HERMES_HOME.parent / ".env",
    HERMES_HOME.parent / "config.yaml",
    HERMES_HOME.parent / "config.yml",
]

# Directories to exclude from recursive traversal
EXCLUDED_DIRS = {"node_modules", ".git", "__pycache__", "venv", ".venv",
                 "env", ".env", ".git", "Lib", "site-packages", ".npm",
                 ".cache", "AppData/Local/Temp", "temp", "tmp", "build",
                 "dist", ".mypy_cache", ".pytest_cache", ".rpmbuild"}


# ── Helpers ───────────────────────────────────────────────────────────
def _mask_value(text: str, keep_front: int = 8, keep_back: int = 4) -> str:
    """Mask a credential value for safe logging."""
    if len(text) <= keep_front + keep_back + 3:
        return "***masked***"
    return text[:keep_front] + "..." + text[-keep_back:]


def _file_matches_pattern(filepath: Path, patterns: List[str]) -> bool:
    """Check if a filename matches any glob pattern."""
    name = filepath.name
    for pat in patterns:
        if pat.startswith("*."):
            if name.endswith(pat[1:]):
                return True
        elif pat == name:
            return True
    return False


def _walk_files(root: Path) -> List[Path]:
    """Walk files in a directory tree, excluding known junk dirs."""
    results = []
    try:
        for entry in root.iterdir():
            if entry.name in EXCLUDED_DIRS:
                continue
            try:
                if entry.is_file():
                    results.append(entry)
                elif entry.is_dir():
                    results.extend(_walk_files(entry))
            except PermissionError:
                continue
    except PermissionError:
        pass
    return results


# ── Security Watchdog ─────────────────────────────────────────────────
class SecurityWatchdog:
    """Real-time file integrity and credential leak monitor."""

    def __init__(self):
        self.events: List[Dict] = []
        self._setup_logging()
        self._load_state()
        self._memory_available = self._check_memory_scorer()

    # -- initialisation ------------------------------------------------

    def _setup_logging(self) -> None:
        """Configure file logger."""
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger("security_watchdog")
        self.logger.setLevel(logging.INFO)
        self.logger.handlers.clear()

        fh = logging.FileHandler(str(LOG_FILE), encoding="utf-8")
        fh.setLevel(logging.INFO)
        fh.setFormatter(logging.Formatter(
            "%(asctime)s|%(levelname)s|%(message)s",
        ))
        self.logger.addHandler(fh)

    def _load_state(self) -> None:
        """Load persisted file state from disk."""
        self.state: Dict = {}
        if STATE_FILE.exists():
            try:
                self.state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                self.state = {}

    def _save_state(self) -> None:
        """Persist file state to disk."""
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(self.state, indent=2, default=str),
                              encoding="utf-8")

    @staticmethod
    def _check_memory_scorer() -> bool:
        """Test whether memory_scorer can be imported."""
        try:
            import memory_scorer  # noqa: F401
            return True
        except ImportError:
            return False

    # -- event pipeline ------------------------------------------------

    def _log_memory_event(self, event_type: str, details: str,
                          severity: str = "info") -> None:
        """Persist security event as a Memory Tree entry."""
        if not self._memory_available:
            return
        try:
            from memory_scorer import create_entry
            score_map = {"critical": 9.0, "warning": 7.0, "info": 5.0}
            create_entry(
                content=f"[SecurityWatchdog] {event_type}: {details}",
                category="security",
                tags=["security", "watchdog", event_type, severity],
                source="security_watchdog",
                score=score_map.get(severity, 5.0),
            )
        except Exception as exc:
            self.logger.warning("Failed to write to memory scorer: %s", exc)

    def _add_event(self, event_type: str, details: str,
                   severity: str = "info") -> None:
        """Register and persist a security event."""
        timestamp = datetime.datetime.now().isoformat()
        event = {
            "timestamp": timestamp,
            "type": event_type,
            "details": details,
            "severity": severity,
        }
        self.events.append(event)

        # File log
        log_msg = f"{severity.upper()}|{event_type}|{details}"
        if severity == "critical":
            self.logger.critical(log_msg)
        elif severity == "warning":
            self.logger.warning(log_msg)
        else:
            self.logger.info(log_msg)

        # Memory Tree
        self._log_memory_event(event_type, details, severity)

    # -- file integrity checks -----------------------------------------

    def check_file_integrity(self) -> None:
        """Check sensitive files for permission / attribute changes."""
        checked: set = set()

        # Recursive scan of HERMES_HOME only
        if HERMES_HOME.is_dir():
            for f in _walk_files(HERMES_HOME):
                if not _file_matches_pattern(f, SENSITIVE_FILE_PATTERNS):
                    continue
                resolved = str(f.resolve())
                if resolved in checked:
                    continue
                checked.add(resolved)
                self._check_single_file(f)

        # Direct check of additional known locations
        for loc in ADDITIONAL_LOCATIONS:
            if not loc.exists():
                continue
            try:
                if loc.is_file():
                    if _file_matches_pattern(loc, SENSITIVE_FILE_PATTERNS):
                        resolved = str(loc.resolve())
                        if resolved not in checked:
                            checked.add(resolved)
                            self._check_single_file(loc)
                elif loc.is_dir():
                    for f in loc.iterdir():
                        if f.is_file() and _file_matches_pattern(f, SENSITIVE_FILE_PATTERNS):
                            resolved = str(f.resolve())
                            if resolved not in checked:
                                checked.add(resolved)
                                self._check_single_file(f)
            except PermissionError:
                continue

    def _check_single_file(self, filepath: Path) -> None:
        """Compare current stat against previous state for one file."""
        try:
            st = filepath.stat()
        except FileNotFoundError:
            self._handle_deleted_file(filepath)
            return
        except OSError:
            return

        file_key = str(filepath.resolve())
        prev = self.state.get("files", {}).get(file_key, {})
        curr = {
            "st_mode": st.st_mode,
            "st_size": st.st_size,
            "st_mtime": st.st_mtime,
            "permissions": oct(st.st_mode & 0o777),
            "owner": st.st_uid,
        }

        changes = []
        if prev and prev.get("exists", True):
            if prev.get("permissions") != curr["permissions"]:
                changes.append(
                    f"permissions: {prev['permissions']} → {curr['permissions']}"
                )
            if prev.get("st_size") != curr["st_size"]:
                changes.append(
                    f"size: {prev['st_size']} → {curr['st_size']} bytes"
                )
            if prev.get("owner") != curr["owner"]:
                changes.append(f"owner UID: {prev['owner']} → {curr['owner']}")

        if changes:
            self._add_event(
                "FILE_CHANGE",
                f"{file_key}: {'; '.join(changes)}",
                severity="critical"
                if any("permissions" in c or "owner" in c for c in changes)
                else "warning",
            )

        self.state.setdefault("files", {})[file_key] = curr

    def _handle_deleted_file(self, filepath: Path) -> None:
        """Handle a previously-tracked sensitive file that went missing."""
        file_key = str(filepath.resolve())
        if file_key in self.state.get("files", {}):
            self._add_event(
                "FILE_DELETED",
                f"Sensitive file removed: {file_key}",
                severity="critical",
            )
            del self.state["files"][file_key]

    # -- credential leak scanning --------------------------------------

    def check_credential_leaks(self) -> None:
        """Scan scripts/ directory for new files containing credential patterns."""
        if not SCRIPTS_DIR.is_dir():
            return

        known_files: set = set(self.state.get("scanned_files", []))
        current_files: set = set()

        for f in SCRIPTS_DIR.iterdir():
            if not f.is_file() or f.name.startswith("."):
                continue
            current_files.add(f.name)

            # Only scan new files (first-seen or previously clean)
            if f.name not in known_files:
                self._scan_file_for_keys(f)
            elif self.state.get("file_hashes", {}).get(f.name):
                # Re-scan if content changed (hash mismatch)
                new_hash = self._file_hash(f)
                old_hash = self.state["file_hashes"].get(f.name)
                if new_hash and new_hash != old_hash:
                    self._scan_file_for_keys(f)

        # Update state
        self.state["scanned_files"] = list(current_files)
        self.state.setdefault("file_hashes", {})

    @staticmethod
    def _file_hash(filepath: Path) -> Optional[str]:
        """Return SHA-256 hex digest of file content."""
        try:
            data = filepath.read_bytes()
            return hashlib.sha256(data).hexdigest()
        except OSError:
            return None

    def _scan_file_for_keys(self, filepath: Path) -> None:
        """Scan a single file for credential patterns and log matches."""
        try:
            content = filepath.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return

        # Update hash
        h = self._file_hash(filepath)
        if h:
            self.state.setdefault("file_hashes", {})[filepath.name] = h

        matches = []
        for pattern in API_KEY_PATTERNS:
            for m in pattern.finditer(content):
                raw = m.group(0)
                # Try to extract just the value part after the label
                if ":" in raw or "=" in raw:
                    parts = re.split(r'[:=]\s*', raw, maxsplit=1)
                    val = parts[-1].strip().strip("\"'")
                else:
                    val = raw
                masked = _mask_value(val)
                line_num = content[:m.start()].count("\n") + 1
                matches.append(f"line {line_num}: {masked}")

        if matches:
            self._add_event(
                "CREDENTIAL_LEAK",
                f"Potential credentials in {filepath.name}: "
                f"{'; '.join(matches[:5])}",
                severity="critical",
            )

    # -- reporting -----------------------------------------------------

    def generate_report(self) -> str:
        """Generate a formatted stdout report for cron delivery."""
        lines = []
        lines.append("=" * 64)
        lines.append("  SECURITY WATCHDOG REPORT")
        lines.append(f"  {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 64)

        if not self.events:
            lines.append("")
            lines.append("  ✅  No security events detected — system is clean.")
        else:
            crit = [e for e in self.events if e["severity"] == "critical"]
            warn = [e for e in self.events if e["severity"] == "warning"]
            info = [e for e in self.events if e["severity"] == "info"]

            lines.append("")
            lines.append(f"  📊  Summary:  {len(crit)} critical  |  "
                         f"{len(warn)} warnings  |  {len(info)} info")

            for label, colour, items in [
                ("CRITICAL", "🔴", crit),
                ("WARNINGS", "🟡", warn),
                ("INFO", "🔵", info),
            ]:
                if not items:
                    continue
                lines.append("")
                lines.append(f"  {colour}  {label}:")
                for ev in items:
                    lines.append(f"     • [{ev['type']}] {ev['details']}")

        # Monitored file summary
        lines.append("")
        lines.append("  📁  Sensitive files tracked:")
        found_count = 0
        for pat in SENSITIVE_FILE_PATTERNS:
            exists = any(
                p in self.state.get("files", {})
                for p, v in self.state.get("files", {}).items()
                if v.get("exists", False)
                and Path(p).name == pat.strip("*") or _file_matches_pattern(Path(p), [pat])
            )
            # Quick fallback check
            resolved = self.state.get("files", {})
            if not exists:
                found = any(
                    p for p in resolved
                    if pat.replace("*", "") in p
                )
                exists = bool(found)
            if exists:
                found_count += 1
            lines.append(f"     {'✓' if exists else '○'}  {pat}")

        lines.append("")
        lines.append(f"  📝  Log:  {LOG_FILE}")
        lines.append(f"  🧠  Memory Tree:  {'connected' if self._memory_available else 'unavailable'}")
        lines.append("=" * 64)

        return "\n".join(lines)

    # -- run -----------------------------------------------------------

    def run(self) -> int:
        """Execute a single security check cycle. Returns exit code."""
        self.check_file_integrity()
        self.check_credential_leaks()
        self._save_state()

        report = self.generate_report()
        print(report)

        critical_count = sum(1 for e in self.events if e["severity"] == "critical")
        return 1 if critical_count > 0 else 0

    def watch(self, interval: int = 300) -> None:
        """Run continuously, sleeping `interval` seconds between checks."""
        print("🔍  Security Watchdog started")
        print(f"    Check interval:  {interval}s")
        print(f"    Log:             {LOG_FILE}")
        print("    Press Ctrl+C to stop\n")

        while True:
            try:
                self.events.clear()
                self.run()
                print()  # blank line between cycles
                time.sleep(interval)
            except KeyboardInterrupt:
                print("\nSecurity Watchdog stopped.")
                break
            except Exception as exc:
                self.logger.error("Watchdog cycle error: %s", exc)
                print(f"  ❌  Error: {exc}")
                time.sleep(interval)


# ── CLI ──────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Security Watchdog — File Integrity & Credential Leak Monitor",
    )
    parser.add_argument(
        "--watch", "-w",
        action="store_true",
        help="Run continuously (check every 5 minutes)",
    )
    parser.add_argument(
        "--interval", "-i",
        type=int,
        default=300,
        help="Check interval in seconds (default: 300)",
    )
    parser.add_argument(
        "--check-only", "-c",
        action="store_true",
        help="Run a single check and exit (default)",
    )
    args = parser.parse_args()

    watchdog = SecurityWatchdog()
    if args.watch:
        watchdog.watch(interval=args.interval)
    else:
        sys.exit(watchdog.run())


if __name__ == "__main__":
    main()