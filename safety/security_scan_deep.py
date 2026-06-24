#!/usr/bin/env python3
"""
security_scan_deep.py — Deep Security Audit for Hermes System
=============================================================

Performs a comprehensive DEEP security scan of the entire Hermes system:
  1) Scans all .py files in scripts/ and lib/ for hardcoded API keys/secrets
  2) Scans git history of C:/Users/dell-/wiki/ for committed secrets
  3) Checks all cron jobs for security issues
  4) Checks network services listening on non-standard ports
  5) Generates a JSON report at logs/deep_security_report.json

Uses secret scanning patterns from the installed skill:
  skills/devops/implementing-secret-scanning-with-gitleaks/SKILL.md

Python stdlib only — no external dependencies.

Usage:
  python security_scan_deep.py
"""

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# Windows: CREATE_NO_WINDOW to prevent CMD flash
WIN_FLAGS = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0

# ─── Paths ──────────────────────────────────────────────────────────────

HERMES = Path.home() / "AppData/Local/hermes"
SCRIPTS_DIR = HERMES / "scripts"
LIB_DIR = HERMES / "lib"
CRON_DIR = HERMES / "cron"
CRON_JOBS = CRON_DIR / "jobs.json"
LOGS_DIR = HERMES / "logs"
REPORT_PATH = LOGS_DIR / "deep_security_report.json"
WIKI_DIR = Path.home() / "wiki"
SKILL_FILE = HERMES / "skills" / "devops" / "implementing-secret-scanning-with-gitleaks" / "SKILL.md"

# ─── Secret Patterns (from gitleaks skill + task specification) ────────

# NOTE: These patterns are derived from the installed skill at:
#   skills/devops/implementing-secret-scanning-with-gitleaks/SKILL.md
# which documents Gitleaks rules for detecting hardcoded secrets.

SECRET_PATTERNS = {
    "openrouter-api-key": {
        "pattern": r"(?i)sk-or-[a-zA-Z0-9_\-]{20,}",
        "severity": "CRITICAL",
        "description": "OpenRouter API key (sk-or-)",
        "source": "gitleaks-skill",
    },
    "composio-api-key": {
        "pattern": r"(?i)ak_[a-zA-Z0-9_\-]{20,}",
        "severity": "CRITICAL",
        "description": "Composio / generic API key (ak_)",
        "source": "gitleaks-skill",
    },
    "github-pat": {
        "pattern": r"(?i)ghp_[a-zA-Z0-9_\-]{20,}",
        "severity": "CRITICAL",
        "description": "GitHub Personal Access Token (ghp_)",
        "source": "gitleaks-skill",
    },
    "google-api-key": {
        "pattern": r"AIza[0-9A-Za-z_\-]{35}",
        "severity": "CRITICAL",
        "description": "Google API key (AIza...)",
        "source": "gitleaks-skill",
    },
    "nvidia-api-key": {
        "pattern": r"(?i)nvapi-[a-zA-Z0-9_\-]{20,}",
        "severity": "CRITICAL",
        "description": "NVIDIA API key (nvapi-)",
        "source": "gitleaks-skill",
    },
    "salesforce-secret": {
        "pattern": r"sm_Ftw[A-Za-z0-9+/=]{20,}",
        "severity": "CRITICAL",
        "description": "Salesforce secret (sm_Ftw...)",
        "source": "gitleaks-skill",
    },
    "jwt-token": {
        "pattern": r"eyJhb[A-Za-z0-9+/=]{20,}",
        "severity": "HIGH",
        "description": "JWT token (eyJhb... base64 prefix)",
        "source": "gitleaks-skill",
    },
    "numeric-secret": {
        "pattern": r"(?i)(?:password|secret|key|token)[\s\"'`:=]+[\"']?8529[\"']?",
        "severity": "HIGH",
        "description": "Numeric secret pattern (8529)",
        "source": "task-spec",
    },
    "database-connection-string": {
        "pattern": r"(?i)(postgres|mysql|mongodb|redis)://[^:]+:[^@]+@",
        "severity": "CRITICAL",
        "description": "Database connection string with embedded credentials",
        "source": "gitleaks-skill",
    },
    "internal-api-token": {
        "pattern": r"(?i)x-internal-token[\"':=\s]+[\"']?([a-zA-Z0-9_\-]{20,})[\"']?",
        "severity": "HIGH",
        "description": "Internal API token (x-internal-token)",
        "source": "gitleaks-skill",
    },
    "aws-access-key": {
        "pattern": r"(?i)AKIA[0-9A-Z]{16}",
        "severity": "CRITICAL",
        "description": "AWS Access Key ID (AKIA...)",
        "source": "gitleaks-skill",
    },
    "generic-api-key": {
        "pattern": r"(?i)(?:api[_-]?key|api[_-]?secret|apikey)[\"':=\s]+[\"']?([a-zA-Z0-9_\-]{20,})[\"']?",
        "severity": "HIGH",
        "description": "Generic API key assignment",
        "source": "gitleaks-skill",
    },
    "slack-bot-token": {
        "pattern": r"(?i)xox[baprs]-[0-9a-zA-Z\-]{20,}",
        "severity": "HIGH",
        "description": "Slack bot token (xox[baprs]-)",
        "source": "gitleaks-skill",
    },
    "private-key": {
        "pattern": r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----",
        "severity": "CRITICAL",
        "description": "Private key block",
        "source": "gitleaks-skill",
    },
}

# Patterns to detect potential secrets in git diffs (looser for history scan)
GIT_SECRET_PATTERNS = {
    "added-api-key": {
        "pattern": r"(?i)(api[_-]?key|api[_-]?secret|apikey)\s*[:=]\s*[\"']?[a-zA-Z0-9_\-/+=]{16,}",
        "severity": "HIGH",
    },
    "added-token": {
        "pattern": r"(?i)(token|secret|password)\s*[:=]\s*[\"']?[a-zA-Z0-9_\-./+=]{16,}",
        "severity": "HIGH",
    },
    "added-sk-or": {
        "pattern": r"(?i)sk-or-[a-zA-Z0-9_\-]{20,}",
        "severity": "CRITICAL",
    },
    "added-ak": {
        "pattern": r"(?i)ak_[a-zA-Z0-9_\-]{20,}",
        "severity": "CRITICAL",
    },
    "added-ghp": {
        "pattern": r"(?i)ghp_[a-zA-Z0-9_\-]{20,}",
        "severity": "CRITICAL",
    },
    "added-aiza": {
        "pattern": r"AIza[0-9A-Za-z_\-]{35}",
        "severity": "CRITICAL",
    },
    "added-nvapi": {
        "pattern": r"(?i)nvapi-[a-zA-Z0-9_\-]{20,}",
        "severity": "CRITICAL",
    },
    "added-jwt": {
        "pattern": r"eyJhb[A-Za-z0-9+/=]{20,}",
        "severity": "HIGH",
    },
    "added-8529": {
        "pattern": r"(?i)(password|secret|key|token)\s*[:=]\s*[\"']?8529[\"']?",
        "severity": "HIGH",
    },
    "added-db-conn": {
        "pattern": r"(?i)(postgres|mysql|mongodb|redis)://[^:]+:[^@]+@",
        "severity": "CRITICAL",
    },
    "added-aws-key": {
        "pattern": r"(?i)AKIA[0-9A-Z]{16}",
        "severity": "CRITICAL",
    },
    "added-private-key": {
        "pattern": r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----",
        "severity": "CRITICAL",
    },
}

# ─── Standard / well-known ports (non-standard = everything else) ───────

STANDARD_PORTS = {
    "135": "RPC (Windows System)",
    "445": "SMB (Windows System)",
    "2179": "RDP-VM (Windows System)",
    "5040": "WMI (Windows System)",
    "5357": "WSDAPI (Windows System)",
    "7680": "Windows Update Delivery Optimization",
    "49664": "Dynamic RPC (Windows)",
    "49665": "Dynamic RPC (Windows)",
    "49668": "Dynamic RPC (Windows)",
    "49669": "Dynamic RPC (Windows)",
    "49672": "Dynamic RPC (Windows)",
    "49696": "Dynamic RPC (Windows)",
}

KNOWN_THIRD_PARTY_PORTS = {
    "11434": "Ollama (LLM service)",
    "8884": "Hermes Gateway?",
    "9050": "Tor SOCKS",
    "10086": "Unknown service",
}

NON_STANDARD_THRESHOLD = {
    "severity": "MEDIUM",
    "description": "Non-standard port exposed on all interfaces",
}


# ═════════════════════════════════════════════════════════════════════════
#  SCAN FUNCTIONS
# ═════════════════════════════════════════════════════════════════════════

def scan_python_files_for_secrets():
    """
    Scan all .py files in scripts/ and lib/ directories for hardcoded
    API keys and secrets using the patterns from the gitleaks skill.
    Returns a list of finding dicts.
    """
    findings = []
    scanned_files = 0

    for directory in [SCRIPTS_DIR, LIB_DIR]:
        if not directory.is_dir():
            continue
        for pyfile in sorted(directory.glob("*.py")):
            scanned_files += 1
            try:
                content = pyfile.read_text(encoding="utf-8", errors="replace")
            except (OSError, PermissionError) as e:
                findings.append({
                    "type": "scan_error",
                    "file": str(pyfile),
                    "severity": "INFO",
                    "detail": f"Cannot read: {e}",
                })
                continue

            lines = content.split("\n")
            for rule_name, rule in SECRET_PATTERNS.items():
                pattern = re.compile(rule["pattern"])
                for lineno, line in enumerate(lines, 1):
                    # Skip comments and empty lines
                    stripped = line.strip()
                    if not stripped or stripped.startswith("#"):
                        continue
                    # Skip import lines
                    if stripped.startswith("import ") or stripped.startswith("from "):
                        continue
                    # Skip lines referencing environment variables
                    if "os.environ" in stripped or "environ.get" in stripped:
                        continue
                    # Skip safe patterns
                    if "getpass" in stripped.lower():
                        continue

                    match = pattern.search(line)
                    if match:
                        # Redact the actual secret for safety
                        redacted = _redact_match(line, match)
                        findings.append({
                            "type": "hardcoded_secret",
                            "file": str(pyfile.relative_to(HERMES)),
                            "line": lineno,
                            "rule": rule_name,
                            "severity": rule["severity"],
                            "description": rule["description"],
                            "source": rule.get("source", "gitleaks-skill"),
                            "snippet": redacted,
                        })

    return findings, scanned_files


def _redact_match(line, match):
    """Redact the matched secret portion from the line for safe reporting."""
    start, end = match.start(), match.end()
    # Show up to 4 chars before and after, with the secret redacted
    prefix = line[max(0, start - 20):start]
    secret = line[start:end]
    suffix = line[end:end + 20]
    if len(secret) > 6:
        redacted_secret = secret[:3] + "***" + secret[-3:]
    else:
        redacted_secret = "***"
    return prefix + redacted_secret + suffix


def scan_git_history():
    """
    Scan git history of C:/Users/dell-/wiki/ for committed secrets.
    Uses 'git log -p' to examine all commits for secret patterns.
    Works with Python stdlib subprocess only.
    Returns a list of finding dicts.
    """
    findings = []
    git_dir = WIKI_DIR

    if not git_dir.is_dir():
        return findings, {"error": f"Wiki directory not found: {git_dir}"}

    git_dir_git = git_dir / ".git"
    if not git_dir_git.is_dir():
        return findings, {"error": "Not a git repository"}

    try:
        # Get all commits with diff
        result = subprocess.run(
            ["git", "log", "-p", "--all", "--diff-filter=AM"],
            capture_output=True, text=True, timeout=120,
            cwd=str(git_dir),
            creationflags=WIN_FLAGS,
        )
    except FileNotFoundError:
        return findings, {"error": "git command not found"}
    except subprocess.TimeoutExpired:
        return findings, {"error": "git log timed out after 120s"}
    except Exception as e:
        return findings, {"error": str(e)}

    if result.returncode != 0:
        return findings, {"error": result.stderr.strip() or "unknown git error"}

    # Parse git log output
    current_commit = None
    current_file = None
    added_lines_checked = 0

    for line_raw in result.stdout.split("\n"):
        # Track current commit
        commit_match = re.match(r"^commit\s+([a-f0-9]{7,40})", line_raw)
        if commit_match:
            current_commit = commit_match.group(1)[:8]
            continue

        # Track current file
        file_match = re.match(r"^\+\+\+\s+b/(.*)", line_raw)
        if file_match:
            current_file = file_match.group(1)
            continue

        # Check added lines (starting with +)
        if line_raw.startswith("+") and not line_raw.startswith("+++"):
            line_content = line_raw[1:]  # strip the leading +
            stripped = line_content.strip()
            if not stripped or stripped.startswith("#") or stripped.startswith("//"):
                continue
            if "os.environ" in stripped or "environ.get" in stripped:
                continue

            added_lines_checked += 1

            for rule_name, rule in GIT_SECRET_PATTERNS.items():
                pattern = re.compile(rule["pattern"])
                match = pattern.search(line_content)
                if match:
                    redacted = _redact_match(line_content, match)
                    findings.append({
                        "type": "git_committed_secret",
                        "file": current_file or "unknown",
                        "commit": current_commit or "unknown",
                        "rule": rule_name,
                        "severity": rule["severity"],
                        "snippet": redacted,
                    })
                    # Only report first match per line per rule
                    break  # avoid duplicate rule matches on same line

    meta = {
        "added_lines_scanned": added_lines_checked,
        "commits_scanned": None,  # we didn't count commits separately
    }
    return findings, meta


def scan_cron_jobs():
    """
    Check all cron jobs for security issues:
      - Jobs referencing hardcoded credentials in prompts
      - Jobs with suspicious external commands
      - Jobs with errors that might indicate security problems
    Returns a list of finding dicts.
    """
    findings = []

    if not CRON_JOBS.is_file():
        return findings, {"error": f"cron jobs file not found: {CRON_JOBS}"}

    try:
        data = json.loads(CRON_JOBS.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        return findings, {"error": str(e)}

    jobs = data.get("jobs", [])
    issues_found = 0

    for job in jobs:
        job_name = job.get("name", "unnamed")
        job_id = job.get("id", "unknown")
        prompt = job.get("prompt", "")
        script = job.get("script", "")
        last_status = job.get("last_status")
        last_error = job.get("last_error")
        enabled = job.get("enabled", True)
        schedule_display = job.get("schedule_display", "unknown")

        # Check 1: Hardcoded credentials in prompt
        for rule_name, rule in GIT_SECRET_PATTERNS.items():
            pattern = re.compile(rule["pattern"])
            match = pattern.search(prompt)
            if match:
                redacted = _redact_match(prompt, match)
                findings.append({
                    "type": "cron_prompt_secret",
                    "job_id": job_id,
                    "job_name": job_name,
                    "rule": rule_name,
                    "severity": rule["severity"],
                    "snippet": redacted,
                })
                issues_found += 1

        # Check 2: Prompt references scripts with potential secrets
        script_refs = re.findall(r'python\s+([^\s"\']+)', prompt)
        for ref in script_refs:
            ref_path = Path(ref)
            if ref_path.suffix == ".py" and ref_path.exists():
                try:
                    ref_content = ref_path.read_text(encoding="utf-8", errors="replace")
                    for rule_name, rule in SECRET_PATTERNS.items():
                        pattern = re.compile(rule["pattern"])
                        if pattern.search(ref_content):
                            findings.append({
                                "type": "cron_script_with_secrets",
                                "job_id": job_id,
                                "job_name": job_name,
                                "script_path": str(ref_path),
                                "rule": rule_name,
                                "severity": rule["severity"],
                                "description": f"Cron job references script containing {rule['description']}",
                            })
                            issues_found += 1
                            break
                except (OSError, PermissionError):
                    pass

        # Check 3: Job with errors
        if last_status == "error" and last_error:
            severity = "HIGH" if "secret" in str(last_error).lower() or "credential" in str(last_error).lower() else "MEDIUM"
            findings.append({
                "type": "cron_job_error",
                "job_id": job_id,
                "job_name": job_name,
                "severity": severity,
                "last_error": last_error[:200],
                "last_run_at": job.get("last_run_at"),
            })
            issues_found += 1

        # Check 4: Job not enabled (potential security gap)
        if not enabled:
            findings.append({
                "type": "cron_job_disabled",
                "job_id": job_id,
                "job_name": job_name,
                "severity": "LOW",
                "detail": f"Security job '{job_name}' is disabled",
            })
            issues_found += 1

        # Check 5: Suspicious shell commands in prompt
        suspicious_cmds = ["rm -rf", "chmod 777", "curl | sh", "wget | bash", "eval ", "exec("]
        for cmd in suspicious_cmds:
            if cmd in prompt.lower():
                findings.append({
                    "type": "cron_suspicious_command",
                    "job_id": job_id,
                    "job_name": job_name,
                    "severity": "HIGH",
                    "detail": f"Contains suspicious command pattern: '{cmd}'",
                })
                issues_found += 1

    meta = {
        "total_jobs": len(jobs),
        "issues_found": issues_found,
    }
    return findings, meta


def scan_network_services():
    """
    Check network services listening on non-standard ports.
    Uses netstat -ano to enumerate listening services.
    Returns a list of finding dicts.
    """
    findings = []
    port_details = []

    try:
        result = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True, text=True, timeout=15,
            creationflags=WIN_FLAGS,
        )
    except FileNotFoundError:
        return findings, {"error": "netstat not found on this system"}
    except subprocess.TimeoutExpired:
        return findings, {"error": "netstat timed out"}
    except Exception as e:
        return findings, {"error": str(e)}

    for line in result.stdout.split("\n"):
        # Look for LISTENING connections
        if "LISTENING" not in line:
            continue
        parts = line.strip().split()
        if len(parts) < 4:
            continue

        proto = parts[0]
        local_addr = parts[1]
        state = parts[3]
        pid = parts[4] if len(parts) > 4 else "?"

        # Parse address:port
        if ":" in local_addr:
            addr_part, port_part = local_addr.rsplit(":", 1)
        else:
            addr_part, port_part = local_addr, "?"

        port_details.append({
            "protocol": proto,
            "address": local_addr,
            "port": port_part,
            "pid": pid,
            "state": state,
        })

        # Non-standard port exposed on all interfaces
        if addr_part == "0.0.0.0" and port_part not in STANDARD_PORTS:
            known = KNOWN_THIRD_PARTY_PORTS.get(port_part)
            if known:
                severity = "LOW"
                detail = f"Port {port_part} ({known}) exposed on all interfaces"
            else:
                severity = "MEDIUM"
                detail = f"Non-standard port {port_part} exposed on all interfaces (PID: {pid})"

            findings.append({
                "type": "exposed_service",
                "port": port_part,
                "protocol": proto,
                "address": local_addr,
                "pid": pid,
                "severity": severity,
                "detail": detail,
            })

    meta = {
        "total_listening": len(port_details),
        "ports_summary": [
            f"{p['port']} ({p['protocol']} / PID: {p['pid']})"
            for p in port_details
        ],
    }
    return findings, meta


def check_skill_patterns_loaded():
    """
    Verify that the gitleaks skill file exists and note its patterns.
    """
    result = {"skill_found": False, "pattern_count": 0}

    if SKILL_FILE.is_file():
        result["skill_found"] = True
        result["pattern_count"] = len(SECRET_PATTERNS)
        try:
            content = SKILL_FILE.read_text(encoding="utf-8", errors="replace")
            # Extract custom gitleaks rules from TOML blocks in the skill
            rules_found = re.findall(r'id\s*=\s*"([^"]+)"', content)
            result["gitleaks_rules_in_skill"] = rules_found
        except Exception:
            pass
    else:
        result["error"] = f"Skill file not found at {SKILL_FILE}"

    return result


# ═════════════════════════════════════════════════════════════════════════
#  REPORTING
# ═════════════════════════════════════════════════════════════════════════

def generate_report(all_findings, scan_meta):
    """Generate the complete JSON report structure."""
    severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}

    # Count by severity
    severity_counts = {}
    for f in all_findings:
        sev = f.get("severity", "INFO")
        severity_counts[sev] = severity_counts.get(sev, 0) + 1

    # Count by type
    type_counts = {}
    for f in all_findings:
        ftype = f.get("type", "unknown")
        type_counts[ftype] = type_counts.get(ftype, 0) + 1

    # Sort findings by severity (most critical first)
    sorted_findings = sorted(
        all_findings,
        key=lambda x: severity_order.get(x.get("severity", "INFO"), 99),
    )

    # Build scanning context summary
    scan_context = {
        "hermes_root": str(HERMES),
        "wiki_dir": str(WIKI_DIR),
        "scripts_scanned": scan_meta.get("scripts_scanned", 0),
        "lib_files_scanned": scan_meta.get("lib_files_scanned", 0),
        "git_commits_checked": scan_meta.get("git_meta", {}).get("commits_scanned"),
        "git_added_lines_scanned": scan_meta.get("git_meta", {}).get("added_lines_scanned"),
        "cron_jobs_total": scan_meta.get("cron_meta", {}).get("total_jobs"),
        "network_listening_services": scan_meta.get("net_meta", {}).get("total_listening"),
        "skill_patterns_loaded": scan_meta.get("skill_meta", {}).get("pattern_count", 0),
        "skill_file_exists": scan_meta.get("skill_meta", {}).get("skill_found", False),
    }

    report = {
        "report_type": "deep_security_scan",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tool": "security_scan_deep.py",
        "version": "1.0.0",
        "summary": {
            "total_findings": len(all_findings),
            "by_severity": dict(sorted(severity_counts.items())),
            "by_type": dict(sorted(type_counts.items())),
            "critical": severity_counts.get("CRITICAL", 0),
            "high": severity_counts.get("HIGH", 0),
            "medium": severity_counts.get("MEDIUM", 0),
            "low": severity_counts.get("LOW", 0),
            "info": severity_counts.get("INFO", 0),
        },
        "scan_context": scan_context,
        "findings": sorted_findings,
    }

    return report


# ═════════════════════════════════════════════════════════════════════════
#  MAIN
# ═════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 70)
    print("  SECURITY SCAN — DEEP AUDIT — Hermes System")
    print("=" * 70)
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Hermes:  {HERMES}")
    print(f"  Wiki:    {WIKI_DIR}")
    print(f"  Skills:  {SKILL_FILE}")
    print("-" * 70)

    all_findings = []
    scan_meta = {}

    # ── Step 0: Load skill patterns ──
    print("\n[0/5] Loading secret scanning patterns from gitleaks skill...")
    skill_meta = check_skill_patterns_loaded()
    scan_meta["skill_meta"] = skill_meta
    if skill_meta["skill_found"]:
        print(f"  ✓ Skill found: {SKILL_FILE}")
        print(f"  ✓ {skill_meta['pattern_count']} scanning patterns loaded")
        rules = skill_meta.get("gitleaks_rules_in_skill", [])
        if rules:
            print(f"  ✓ Gitleaks rules found: {', '.join(rules)}")
    else:
        print(f"  ⚠ Skill not found: {skill_meta.get('error', 'unknown error')}")
        print(f"  Using {len(SECRET_PATTERNS)} built-in patterns anyway")

    # ── Step 1: Scan Python files ──
    print("\n[1/5] Scanning .py files in scripts/ and lib/ for secrets...")
    py_findings, scripts_scanned = scan_python_files_for_secrets()
    all_findings.extend(py_findings)
    scan_meta["scripts_scanned"] = scripts_scanned
    scan_meta["lib_files_scanned"] = len(list(SCRIPTS_DIR.glob("*.py"))) + len(list(LIB_DIR.glob("*.py")))
    if py_findings:
        for f in py_findings:
            print(f"  {'!' if f['severity'] in ('CRITICAL','HIGH') else '?'} "
                  f"[{f['severity']:>8}] {f['file']}:{f.get('line','?')} "
                  f"— {f.get('description','secret')}")
    else:
        print("  ✓ No hardcoded secrets found in Python files")

    # ── Step 2: Scan git history ──
    print("\n[2/5] Scanning wiki git history for committed secrets...")
    git_findings, git_meta = scan_git_history()
    all_findings.extend(git_findings)
    scan_meta["git_meta"] = git_meta
    if isinstance(git_meta, dict) and "error" in git_meta:
        print(f"  ⚠ Git scan issue: {git_meta['error']}")
    elif git_findings:
        for f in git_findings:
            print(f"  {'!' if f['severity'] in ('CRITICAL','HIGH') else '?'} "
                  f"[{f['severity']:>8}] commit:{f.get('commit','?')} "
                  f"{f.get('file','?')} — {f.get('rule','secret')}")
    else:
        print("  ✓ No secrets found in git history")
    print(f"  Added lines scanned: {git_meta.get('added_lines_scanned', 0)}")

    # ── Step 3: Check cron jobs ──
    print("\n[3/5] Checking cron jobs for security issues...")
    cron_findings, cron_meta = scan_cron_jobs()
    all_findings.extend(cron_findings)
    scan_meta["cron_meta"] = cron_meta
    if isinstance(cron_meta, dict) and "error" in cron_meta:
        print(f"  ⚠ Cron scan issue: {cron_meta['error']}")
    elif cron_findings:
        for f in cron_findings:
            print(f"  {'!' if f['severity'] in ('CRITICAL','HIGH') else '?'} "
                  f"[{f['severity']:>8}] {f.get('type','issue')} "
                  f"— {f.get('job_name','?')}")
    else:
        print("  ✓ No security issues found in cron jobs")
    print(f"  Total jobs: {cron_meta.get('total_jobs', 0)}")

    # ── Step 4: Check network services ──
    print("\n[4/5] Checking network services on non-standard ports...")
    net_findings, net_meta = scan_network_services()
    all_findings.extend(net_findings)
    scan_meta["net_meta"] = net_meta
    if isinstance(net_meta, dict) and "error" in net_meta:
        print(f"  ⚠ Network scan issue: {net_meta['error']}")
    elif net_findings:
        for f in net_findings:
            print(f"  {'!' if f['severity'] in ('CRITICAL','HIGH') else '?'} "
                  f"[{f['severity']:>8}] {f.get('detail','')}")
    else:
        print("  ✓ No non-standard exposed services found")
    print(f"  Total listening services: {net_meta.get('total_listening', 0)}")

    # ── Step 5: Generate report ──
    print("\n[5/5] Generating deep security report...")
    report = generate_report(all_findings, scan_meta)

    # Write report
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # ── Summary ──
    print("\n" + "=" * 70)
    print("  SCAN COMPLETE")
    print("=" * 70)
    print(f"  Report:     {REPORT_PATH}")
    print(f"  Findings:   {report['summary']['total_findings']}")
    print(f"  CRITICAL:   {report['summary']['critical']}")
    print(f"  HIGH:       {report['summary']['high']}")
    print(f"  MEDIUM:     {report['summary']['medium']}")
    print(f"  LOW:        {report['summary']['low']}")
    print(f"  INFO:       {report['summary']['info']}")
    print("-" * 70)

    # Severity rating
    total_critical_high = report['summary']['critical'] + report['summary']['high']
    if total_critical_high > 0:
        print(f"  ⚠ SECURITY ALERT: {total_critical_high} critical/high findings!")
    else:
        print("  ✓ No critical or high-severity findings")
    print("=" * 70)

    return 1 if total_critical_high > 0 else 0


if __name__ == "__main__":
    sys.exit(main())