#!/usr/bin/env python3
"""
Koldi Proactive Monitor — Monitoramento proativo que age antes de o Senhor pedir.
Verifica saúde do sistema, detecta problemas e toma ação automática quando possível.

Rodado via cron a cada 60 minutos.
"""

import json
import os
import subprocess
import sys
from datetime import datetime

HOME = os.path.expanduser("~")
LOG_DIR = os.path.join(HOME, "AppData", "Local", "hermes", "logs")
REPORT_FILE = os.path.join(LOG_DIR, "proactive_report.json")
os.makedirs(LOG_DIR, exist_ok=True)


def run_cmd(cmd, timeout=15):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                          creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0)
        return r.stdout.strip(), r.returncode
    except Exception as e:
        return str(e), -1


def check_ram():
    """Verifica uso de RAM."""
    out, _ = run_cmd(["powershell", "-Command", 
        "(Get-CimInstance Win32_OperatingSystem | Select-Object -ExpandProperty FreePhysicalMemory) / 1MB"])
    try:
        free_gb = float(out.strip())
        total_gb = 15.7  # conhecido
        used_pct = ((total_gb - free_gb) / total_gb) * 100
        return {
            'free_gb': round(free_gb, 1),
            'used_pct': round(used_pct, 1),
            'status': 'ok' if used_pct < 85 else 'warning' if used_pct < 95 else 'critical'
        }
    except:
        return {'status': 'unknown'}


def check_disk():
    """Verifica espaço em disco."""
    out, _ = run_cmd(["powershell", "-Command",
        "Get-PSDrive -PSProvider FileSystem | Where-Object {$_.Used -gt 0} | ForEach-Object { \"$($_.Name):$([math]::Round($_.Free/1GB,1))\" }"])
    drives = {}
    for line in out.split('\n'):
        if ':' in line:
            name, free = line.strip().split(':', 1)
            drives[name] = float(free)
    return drives


def check_ollama():
    """Verifica se Ollama está respondendo."""
    out, code = run_cmd(["curl", "-s", "--max-time", "5", "http://localhost:11434/api/tags"])
    if code == 0 and '"models"' in out:
        return {'status': 'ok', 'models': len(out.split('"name"')) - 1}
    return {'status': 'down'}


def check_gateway():
    """Verifica se o Gateway Hermes está rodando."""
    out, code = run_cmd(["powershell", "-Command",
        "Get-Process -Name 'python' -ErrorAction SilentlyContinue | Where-Object {$_.CommandLine -like '*hermes*gateway*'} | Select-Object -ExpandProperty Id"])
    if out.strip():
        return {'status': 'ok', 'pid': out.strip().split('\n')[0]}
    return {'status': 'down'}


def check_vps():
    """Verifica conectividade com a VPS."""
    out, code = run_cmd(["ssh", "-i", os.path.join(HOME, ".ssh", "id_ed25519_vps"),
                        "-o", "ConnectTimeout=5", "-o", "StrictHostKeyChecking=no",
                        "root@2.25.168.233", "echo ok"])
    if code == 0 and 'ok' in out:
        return {'status': 'ok'}
    return {'status': 'unreachable'}


def check_vps_services():
    """Verifica serviços na VPS."""
    out, code = run_cmd(["ssh", "-i", os.path.join(HOME, ".ssh", "id_ed25519_vps"),
                        "-o", "ConnectTimeout=5", "-o", "StrictHostKeyChecking=no",
                        "root@2.25.168.233", 
                        "systemctl is-active postgresql nats-koldi 2>&1"])
    if code == 0:
        services = out.strip().split('\n')
        return {
            'postgresql': services[0] if len(services) > 0 else 'unknown',
            'nats': services[1] if len(services) > 1 else 'unknown',
        }
    return {'status': 'unreachable'}


def check_temperature():
    """Verifica temperatura de Diadema/SP."""
    out, code = run_cmd(["curl", "-s", "--max-time", "10",
        "https://api.open-meteo.com/v1/forecast?latitude=-23.6861&longitude=-46.6117&current_weather=true"])
    if code == 0 and out:
        try:
            data = json.loads(out)
            temp = data.get('current_weather', {}).get('temperature', '?')
            return {
                'temp_c': temp,
                'status': 'cold' if temp < 16 else 'cool' if temp < 20 else 'normal'
            }
        except:
            pass
    return {'status': 'unknown'}


def check_unison_last_sync():
    """Verifica quando foi o último sync do Unison."""
    out, _ = run_cmd(["powershell", "-Command",
        "Get-ChildItem '$env:USERPROFILE\\.unison\\ar*' -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1 -ExpandProperty LastWriteTime"])
    if out.strip():
        return {'last_sync': out.strip()}
    return {'last_sync': 'unknown'}


def generate_report():
    """Gera relatório completo de saúde."""
    now = datetime.now().isoformat()
    
    report = {
        'timestamp': now,
        'system': {
            'ram': check_ram(),
            'disk': check_disk(),
            'ollama': check_ollama(),
            'gateway': check_gateway(),
        },
        'vps': {
            'connectivity': check_vps(),
            'services': check_vps_services(),
        },
        'weather': check_temperature(),
        'sync': {
            'unison': check_unison_last_sync(),
        }
    }
    
    # Determinar alertas
    alerts = []
    
    ram = report['system']['ram']
    if ram.get('status') == 'critical':
        alerts.append(f"RAM crítica: {ram.get('used_pct', '?')}% usado")
    
    ollama = report['system']['ollama']
    if ollama.get('status') == 'down':
        alerts.append("Ollama está offline")
    
    gateway = report['system']['gateway']
    if gateway.get('status') == 'down':
        alerts.append("Gateway Hermes está offline")
    
    vps = report['vps']['connectivity']
    if vps.get('status') == 'unreachable':
        alerts.append("VPS inacessível")
    
    weather = report['weather']
    if weather.get('status') == 'cold':
        alerts.append(f"Frio em Diadema: {weather.get('temp_c', '?')}°C — distonia pode piorar")
    
    report['alerts'] = alerts
    report['status'] = 'critical' if any('crític' in a.lower() or 'offline' in a.lower() for a in alerts) else \
                       'warning' if alerts else 'ok'
    
    # Salvar relatório
    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    return report


def format_alert_message(report):
    """Formata mensagem de alerta para TTS."""
    alerts = report.get('alerts', [])
    if not alerts:
        return "Sistema saudável. Nenhum alerta."
    
    msg = f"{len(alerts)} alerta{'s' if len(alerts) > 1 else ''} detectado{'s' if len(alerts) > 1 else ''}: "
    msg += ". ".join(alerts)
    return msg


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--json':
        report = generate_report()
        print(json.dumps(report, indent=2, ensure_ascii=False))
    elif len(sys.argv) > 1 and sys.argv[1] == '--alert':
        report = generate_report()
        print(format_alert_message(report))
    else:
        report = generate_report()
        print(f"=== Koldi Proactive Monitor ===")
        print(f"Status: {report['status'].upper()}")
        print(f"RAM: {report['system']['ram'].get('used_pct', '?')}% usado")
        print(f"Ollama: {report['system']['ollama'].get('status', '?')}")
        print(f"Gateway: {report['system']['gateway'].get('status', '?')}")
        print(f"VPS: {report['vps']['connectivity'].get('status', '?')}")
        print(f"Temp: {report['weather'].get('temp_c', '?')}°C ({report['weather'].get('status', '?')})")
        if report['alerts']:
            print(f"\nAlertas:")
            for a in report['alerts']:
                print(f"  ⚠ {a}")
