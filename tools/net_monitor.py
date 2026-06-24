#!/usr/bin/env python3
"net_monitor.py — Monitoramento de rede/local."""
from __future__ import annotations
import argparse, json, socket, subprocess, sys, time
from datetime import datetime
from pathlib import Path

# Windows: CREATE_NO_WINDOW
WIN_FLAGS = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0

HERMES_HOME = Path.home() / "AppData/Local/hermes"
LOG = HERMES_HOME / "logs/net_monitor.log"

def _log(msg: str) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(f"{datetime.now().isoformat()} {msg}\n")

def ping(host: str, count: int = 4) -> dict:
    try:
        env = {**__import__('os').environ, 'PYTHONIOENCODING': 'utf-8'}
        out = subprocess.check_output(
            ["ping", "-n" if sys.platform.startswith("win") else "-c", str(count), host],
            stderr=subprocess.STDOUT, timeout=30, env=env,
        )
        text = out.decode('utf-8', errors='replace') if isinstance(out, (bytes, bytearray)) else str(out)
        return {"host": host, "ok": True, "output": text[-300:]}
    except Exception as exc:
        return {"host": host, "ok": False, "error": str(exc)}

def dns_resolve(host: str) -> dict:
    try:
        ip = socket.gethostbyname(host)
        return {"host": host, "ip": ip, "ok": True}
    except Exception as exc:
        return {"host": host, "ok": False, "error": str(exc)}

def gateway_status() -> dict:
    gw = None
    try:
        if sys.platform.startswith("win"):
            out = subprocess.check_output(
                ["powershell", "-NoProfile", "-Command",
                 "(Get-NetRoute -DestinationPrefix '0.0.0.0/0' -ErrorAction SilentlyContinue | Sort-Object RouteMetric | Select-Object -First 1).NextHop"],
                text=True, timeout=10,
            )
            gw = out.strip() or None
    except Exception:
        gw = None
    return {"gateway": gw}

def network_interfaces() -> dict:
    try:
        if sys.platform.startswith("win"):
            out = subprocess.check_output(
                ["powershell", "-NoProfile", "-Command",
                 "Get-NetIPAddress -AddressFamily IPv4 -CimSession (Get-CimSession -ErrorAction SilentlyContinue) | "
                 "Select-Object InterfaceAlias, IPAddress | ConvertTo-Json -Compress"],
                text=True, timeout=15, stderr=subprocess.STDOUT,
            )
        else:
            out = subprocess.check_output(
                ["ip", "-brief", "addr"],
                text=True, timeout=15, stderr=subprocess.STDOUT,
            )
        return {"ok": True, "output": out[:1000]}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}

def run(target: str) -> dict:
    now = datetime.now().isoformat()
    res = {"timestamp": now, "target": target}
    if target == "ping":
        res["data"] = ping("8.8.8.8")
    elif target == "dns":
        res["data"] = {
            "google": dns_resolve("google.com"),
            "openrouter": dns_resolve("openrouter.ai"),
            "ollama": dns_resolve("ollama.com"),
        }
    elif target == "gateway":
        res["data"] = gateway_status()
    elif target == "interfaces":
        res["data"] = network_interfaces()
    elif target == "all":
        res["data"] = {
            "ping": ping("8.8.8.8"),
            "dns": {
                "google": dns_resolve("google.com"),
                "openrouter": dns_resolve("openrouter.ai"),
            },
            "gateway": gateway_status(),
            "interfaces": network_interfaces(),
        }
    else:
        res["error"] = f"alvo desconhecido: {target}"
    _log(json.dumps(res, ensure_ascii=False))
    return res

def main() -> int:
    parser = argparse.ArgumentParser(description="Monitor de rede/local")
    parser.add_argument("target", nargs="?", default="all", choices=["ping","dns","gateway","interfaces","all"])
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    res = run(args.target)
    if args.json:
        print(json.dumps(res, indent=2, ensure_ascii=False))
    else:
        print(json.dumps(res, indent=2, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
