#!/usr/bin/env python3
"""
epr_watchdog.py — Watchdog que mantém o EPR Client sempre vivo.
Verifica a cada 30 segundos se o processo está rodando.
Se não estiver, reinicia automaticamente.
"""
import subprocess, time, ctypes, os, sys
from ctypes import wintypes

DETACHED_PROCESS = 0x00000008
CREATE_NEW_PROCESS_GROUP = 0x00000200

class STARTUPINFO(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD), ("lpReserved", wintypes.LPWSTR),
        ("lpDesktop", wintypes.LPWSTR), ("lpTitle", wintypes.LPWSTR),
        ("dwX", wintypes.DWORD), ("dwY", wintypes.DWORD),
        ("dwXSize", wintypes.DWORD), ("dwYSize", wintypes.DWORD),
        ("dwXCountChars", wintypes.DWORD), ("dwYCountChars", wintypes.DWORD),
        ("dwFillAttribute", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
        ("wShowWindow", wintypes.WORD), ("cbReserved2", wintypes.WORD),
        ("lpReserved2", wintypes.LPBYTE),
        ("hStdInput", wintypes.HANDLE), ("hStdOutput", wintypes.HANDLE),
        ("hStdError", wintypes.HANDLE),
    ]

class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("hProcess", wintypes.HANDLE), ("hThread", wintypes.HANDLE),
        ("dwProcessId", wintypes.DWORD), ("dwThreadId", wintypes.DWORD),
    ]

def create_detached(cmd, cwd):
    si = STARTUPINFO()
    si.cb = ctypes.sizeof(STARTUPINFO)
    pi = PROCESS_INFORMATION()
    r = ctypes.windll.kernel32.CreateProcessW(None, cmd, None, None, False,
        DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP, None, cwd,
        ctypes.byref(si), ctypes.byref(pi))
    if r:
        ctypes.windll.kernel32.CloseHandle(pi.hProcess)
        ctypes.windll.kernel32.CloseHandle(pi.hThread)
        return pi.dwProcessId
    return None

epr_cmd = r'pythonw "C:\Users\dell-\AppData\Local\hermes\lib\epr\epr_bridge.py" --mode client --config "C:\Users\dell-\AppData\Local\hermes\epr_client.json"'
epr_cwd = r'C:\Users\dell-\AppData\Local\hermes\lib\epr'

while True:
    result = subprocess.run(
        ['cmd', '//c', 'tasklist /FI "IMAGENAME eq pythonw.exe" /FO TABLE 2>nul'],
        capture_output=True, text=True, errors='replace'
    )
    if 'pythonw.exe' not in result.stdout:
        print(f"[{time.strftime('%H:%M:%S')}] EPR Client died, restarting...")
        pid = create_detached(epr_cmd, epr_cwd)
        print(f"  Restarted: PID={pid}")
        time.sleep(15)
    time.sleep(30)
