#!/usr/bin/env python3
"""
koldi_local_agent.py — Agente Local do Koldi (Windows)

Monitora o EPR Bridge state DB e dispara tarefas no Koldi da Nuvem
quando arquivos são sincronizados.

Hook: Quando o EPR detecta mudanças no servidor (VPS), o agente local
      pode sincronizar de volta ou executar tarefas locais.

Uso:
    python koldi_local_agent.py --watch
    python koldi_local_agent.py --once
    python koldi_local_agent.py --status
"""

import argparse
import json
import os
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime

# ─── Config ──────────────────────────────────────────────────────

SSH_KEY = os.path.join(os.path.expanduser('~'), '.ssh', 'id_ed25519_vps')
VPS_HOST = '2.25.168.233'
VPS_USER = 'root'

LOCAL_DB = os.path.join(os.path.expanduser('~'), 'AppData', 'Local', 'hermes', '.epr_state_local.db')
WATCH_INTERVAL = 15  # seconds

# ─── VPS Remote Commands ─────────────────────────────────────────

def vps_run(cmd):
    """Execute command on VPS"""
    try:
        result = subprocess.run(
            ['ssh', '-i', SSH_KEY, '-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=10',
             f'{VPS_USER}@{VPS_HOST}', cmd],
            capture_output=True, text=True, timeout=30, errors='replace'
        )
        return result.stdout.strip(), result.returncode
    except subprocess.TimeoutExpired:
        return "TIMEOUT", -1
    except Exception as e:
        return str(e), -1

def vps_status():
    """Check Koldi Nuvem Agent status"""
    out, rc = vps_run('systemctl is-active koldi-nuvem-agent 2>&1')
    return out == 'active'

def vps_stats():
    """Get agent stats from VPS"""
    out, rc = vps_run(
        'python3 -c "'
        'import sqlite3; '
        'conn=sqlite3.connect(\'/opt/hermes/.hermes/.koldi_nuvem.db\'); '
        'c=conn.cursor(); '
        'c.execute(\\\"SELECT status, COUNT(*) FROM processed_files GROUP BY status\\\"); '
        'rows=dict(c.fetchall()); '
        'c.execute(\\\"SELECT COUNT(*) FROM task_log\\\"); '
        'rows[\\\"tasks\\\"]=c.fetchone()[0]; '
        'print(json.dumps(rows)); '
        'conn.close()" 2>/dev/null || echo "{}"'
    )
    try:
        return json.loads(out)
    except:
        return {}

def vps_exec(cmd):
    """Execute arbitrary command on VPS"""
    out, rc = vps_run(cmd)
    return out, rc

# ─── EPR State Monitor ───────────────────────────────────────────

class EPRMonitor:
    def __init__(self, db_path):
        self.db_path = db_path
        self.last_sync_count = 0
    
    def get_incoming_changes(self):
        """Get files received from VPS (direction=in)"""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            # Count incoming syncs since last check
            c.execute("SELECT COUNT(*) FROM sync_log WHERE direction='in'")
            total_in = c.fetchone()[0]
            
            # Get latest incoming files
            c.execute("""
                SELECT timestamp, file_path, action, status 
                FROM sync_log 
                WHERE direction='in' 
                ORDER BY timestamp DESC 
                LIMIT 20
            """)
            latest = c.fetchall()
            
            # Count pending files (local changes not yet synced to VPS)
            c.execute("SELECT COUNT(*) FROM file_states WHERE sync_status='pending'")
            pending = c.fetchone()[0]
            
            # Count total synced
            c.execute("SELECT COUNT(*) FROM file_states WHERE sync_status='synced'")
            synced = c.fetchone()[0]
            
            conn.close()
            
            return {
                'total_incoming': total_in,
                'latest_incoming': latest,
                'pending_local': pending,
                'synced': synced,
                'new_syncs': total_in - self.last_sync_count
            }
        except Exception as e:
            return {'error': str(e)}
    
    def check_server_changes(self):
        """Check what files the server has that we don't"""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            # Files that server pushed to us
            c.execute("""
                SELECT file_path, MAX(timestamp) as last_sync
                FROM sync_log 
                WHERE direction='in' AND status='received'
                GROUP BY file_path
                ORDER BY last_sync DESC
                LIMIT 10
            """)
            server_files = c.fetchall()
            
            conn.close()
            return server_files
        except:
            return []

# ─── Task Router ─────────────────────────────────────────────────

class TaskRouter:
    """Routes files to appropriate handlers"""
    
    def __init__(self):
        self.handlers = {
            'wiki': self._handle_wiki,
            'scripts': self._handle_script,
            'lib': self._handle_lib,
        }
    
    def route_vps_task(self, task_type, args):
        """Send task to VPS for execution"""
        if task_type == 'test':
            cmd = f'cd /opt/hermes && python -m pytest {args} -q 2>&1 | tail -20'
            out, rc = vps_exec(cmd)
            return {'status': 'ok' if rc == 0 else 'error', 'output': out}
        
        elif task_type == 'exec':
            out, rc = vps_exec(args)
            return {'status': 'ok' if rc == 0 else 'error', 'output': out}
        
        elif task_type == 'deploy':
            # Run deployment script on VPS
            cmd = f'cd /opt/hermes && bash scripts/deploy.sh 2>&1'
            out, rc = vps_exec(cmd)
            return {'status': 'ok' if rc == 0 else 'error', 'output': out}
        
        elif task_type == 'health':
            cmd = 'cd /opt/hermes && python -m pytest tests/ -q --tb=no 2>&1 | tail -5'
            out, rc = vps_exec(cmd)
            return {'status': 'ok' if rc == 0 else 'error', 'output': out}
        
        return {'status': 'unknown_task', 'output': ''}
    
    def _handle_wiki(self, file_path, action):
        """Handle wiki file updates"""
        print(f"  [wiki] {action}: {file_path}")
        # Wiki files are informational — just ack
        return True
    
    def _handle_script(self, file_path, action):
        """Handle script file updates"""
        print(f"  [script] {action}: {file_path}")
        # Could trigger script execution on VPS
        return True
    
    def _handle_lib(self, file_path, action):
        """Handle library file updates"""
        print(f"  [lib] {action}: {file_path}")
        # Could trigger tests on VPS
        return True

# ─── Main Loop ───────────────────────────────────────────────────

def main_loop():
    monitor = EPRMonitor(LOCAL_DB)
    router = TaskRouter()
    
    print("=" * 50)
    print("Koldi Local Agent — EPR + VPS Bridge")
    print("=" * 50)
    
    # Check VPS connectivity
    print("\nChecking VPS connectivity...")
    if vps_status():
        print("  ✓ Koldi Nuvem Agent is RUNNING on VPS")
    else:
        print("  ✗ Koldi Nuvem Agent is NOT running on VPS")
    
    stats = vps_stats()
    if stats:
        print(f"  VPS Agent stats: {stats}")
    
    print(f"\nMonitoring EPR state: {LOCAL_DB}")
    print(f"Watch interval: {WATCH_INTERVAL}s")
    print()
    
    while True:
        try:
            changes = monitor.get_incoming_changes()
            
            if 'error' in changes:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ERROR: {changes['error']}")
                time.sleep(WATCH_INTERVAL)
                continue
            
            new_syncs = changes['new_syncs']
            
            if new_syncs > 0:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] {new_syncs} new file(s) from VPS")
                for ts, fp, action, status in changes['latest_incoming'][:5]:
                    t = datetime.fromtimestamp(ts).strftime('%H:%M:%S')
                    print(f"  ← {t} [{status}] {action} {fp}")
            
            # Print status line
            print(f"\r[{datetime.now().strftime('%H:%M:%S')}] "
                  f"incoming={changes['total_incoming']} "
                  f"synced={changes['synced']} "
                  f"pending={changes['pending_local']} "
                  f"new={new_syncs}", end='', flush=True)
            
            monitor.last_sync_count = changes['total_incoming']
            time.sleep(WATCH_INTERVAL)
        
        except KeyboardInterrupt:
            print("\nStopped.")
            break
        except Exception as e:
            print(f"\nError: {e}")
            time.sleep(WATCH_INTERVAL)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Koldi Local Agent')
    parser.add_argument('--watch', action='store_true', help='Watch mode (continuous)')
    parser.add_argument('--once', action='store_true', help='Check once and exit')
    parser.add_argument('--status', action='store_true', help='Show status')
    args = parser.parse_args()
    
    if args.status:
        monitor = EPRMonitor(LOCAL_DB)
        changes = monitor.get_incoming_changes()
        print(json.dumps(changes, indent=2, default=str))
    elif args.once:
        monitor = EPRMonitor(LOCAL_DB)
        changes = monitor.get_incoming_changes()
        print(f"Incoming: {changes.get('total_incoming', 0)}")
        print(f"Synced: {changes.get('synced', 0)}")
        print(f"Pending: {changes.get('pending_local', 0)}")
    elif args.watch:
        main_loop()
    else:
        parser.print_help()
