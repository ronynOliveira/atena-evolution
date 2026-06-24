#!/usr/bin/env python3
"""
koldi_nuvem_ctl.py — Controle remoto do Koldi Nuvem Agent

Uso:
    python koldi_nuvem_ctl.py status     — Verifica status do agente
    python koldi_nuvem_ctl.py start      — Inicia o agente
    python koldi_nuvem_ctl.py stop       — Para o agente
    python koldi_nuvem_ctl.py restart    — Reinicia o agente
    python koldi_nuvem_ctl.py log        — Mostra logs recentes
    python koldi_nuvem_ctl.py stats      — Estatísticas do agente
    python koldi_nuvem_ctl.py exec COMANDO — Executa comando na VPS
"""

import subprocess
import sys
import os

SSH_KEY = os.path.expanduser('~/.ssh/id_ed25519_vps')
VPS_HOST = '2.25.168.233'
VPS_USER = 'root'

def ssh_run(cmd):
    """Execute command on VPS via SSH"""
    result = subprocess.run(
        ['ssh', '-i', SSH_KEY, '-o', 'StrictHostKeyChecking=no',
         f'{VPS_USER}@{VPS_HOST}', cmd],
        capture_output=True, text=True
    )
    return result.stdout.strip(), result.returncode

def status():
    out, _ = ssh_run('systemctl status koldi-nuvem-agent --no-pager 2>&1')
    print(out)

def start():
    out, rc = ssh_run('systemctl start koldi-nuvem-agent')
    if rc == 0:
        print("Koldi Nuvem Agent iniciado com sucesso!")
    else:
        print(f"Erro ao iniciar: {out}")

def stop():
    out, rc = ssh_run('systemctl stop koldi-nuvem-agent')
    if rc == 0:
        print("Koldi Nuvem Agent parado.")
    else:
        print(f"Erro ao parar: {out}")

def restart():
    out, rc = ssh_run('systemctl restart koldi-nuvem-agent')
    if rc == 0:
        print("Koldi Nuvem Agent reiniciado!")
    else:
        print(f"Erro ao reiniciar: {out}")

def log():
    out, _ = ssh_run('tail -30 /opt/hermes/logs/koldi_nuvem.log 2>/dev/null || echo "Sem logs"')
    print(out)

def stats():
    out, _ = ssh_run('cat /opt/hermes/.hermes/.koldi_nuvem.db 2>/dev/null | head -5 || echo "sem stats"')
    # Better: query the SQLite DB
    out, _ = ssh_run(
        'python3 -c "'
        'import sqlite3, json; '
        'conn=sqlite3.connect(\"/opt/hermes/.hermes/.koldi_nuvem.db\"); '
        'c=conn.cursor(); '
        'c.execute(\"SELECT status, COUNT(*) FROM processed_files GROUP BY status\"); '
        'print(dict(c.fetchall())); '
        'c.execute(\"SELECT COUNT(*) FROM task_log\"); '
        'print(f\"task_log: {c.fetchone()[0]}\"); '
        'conn.close()" 2>/dev/null || echo "Stats unavailable"'
    )
    print(out)

def exec_cmd(args):
    cmd = ' '.join(args)
    out, _ = ssh_run(cmd)
    print(out)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    action = sys.argv[1].lower()
    
    actions = {
        'status': status,
        'start': start,
        'stop': stop,
        'restart': restart,
        'log': log,
        'stats': stats,
    }
    
    if action in actions:
        actions[action]()
    elif action == 'exec':
        exec_cmd(sys.argv[2:])
    else:
        print(f"Ação desconhecida: {action}")
        print("Ações disponíveis: status, start, stop, restart, log, stats, exec")
