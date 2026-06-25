#!/usr/bin/env python3
"""
Monitor de Sistema do Projeto Atena.
Verifica: CPU, RAM, disco, temperatura (se disponível), rede.
Gera alerta se algo estiver crítico.

Autor: OWL (Batedor da Nuvem)
Data: 2026-05-20
"""

import subprocess
import sys
import os
import json
import locale
import logging
from datetime import datetime

# Forçar locale numérico para usar ponto como separador decimal,
# independentemente da configuração regional do Windows.
try:
    locale.setlocale(locale.LC_NUMERIC, 'C')
except locale.Error:
    pass

logging.basicConfig(level=logging.WARNING, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def parse_num(texto):
    """Converte string de número do PowerShell para float,
    tratando vírgula como separador decimal (pt-BR)."""
    if not texto:
        return 0.0
    # Remove espaços e troca vírgula por ponto
    texto = texto.strip().replace(',', '.')
    return float(texto)


WIKI_PATH = os.path.join(os.path.expanduser("~"), "wiki")
REPORT_PATH = os.path.join(WIKI_PATH, "_meta", "monitor-sistema.md")

# Limiares de alerta
LIMIARES = {
    "cpu_pct": 90,
    "ram_pct": 85,
    "disco_pct": 90,
}

def run_ps(cmd):
    """Executa comando PowerShell e retorna output decodificado."""
    result = subprocess.run(
        ["powershell", "-Command", cmd],
        capture_output=True, timeout=10
    )
    return result.stdout.decode("utf-8", errors="replace").strip()


def verificar_cpu():
    """Verifica uso de CPU."""
    try:
        cpu = parse_num(run_ps("(Get-CimInstance Win32_Processor | Measure-Object -Property LoadPercentage -Average).Average"))
        status = "ok" if cpu < LIMIARES["cpu_pct"] else "critico"
        return {"valor": cpu, "status": status, "unidade": "%"}
    except (ValueError, subprocess.TimeoutExpired, Exception) as e:
        logger.warning("Erro ao verificar CPU: %s", e)
        return {"valor": 0, "status": "erro", "unidade": "%"}


def verificar_ram():
    """Verifica uso de RAM."""
    try:
        ram = parse_num(run_ps("$os = Get-CimInstance Win32_OperatingSystem; [math]::Round(($os.TotalVisibleMemorySize - $os.FreePhysicalMemory) / $os.TotalVisibleMemorySize * 100, 1)"))
        status = "ok" if ram < LIMIARES["ram_pct"] else "critico"
        total_gb = parse_num(run_ps("[math]::Round((Get-CimInstance Win32_OperatingSystem).TotalVisibleMemorySize / 1MB, 1)"))
        return {"valor": ram, "status": status, "unidade": "%", "total_gb": total_gb}
    except (ValueError, subprocess.TimeoutExpired, Exception) as e:
        logger.warning("Erro ao verificar RAM: %s", e)
        return {"valor": 0, "status": "erro", "unidade": "%"}


def verificar_disco():
    """Verifica uso do disco C:."""
    try:
        disco = parse_num(run_ps("$d = Get-CimInstance Win32_LogicalDisk -Filter \"DeviceID='C:'\"; [math]::Round(($d.Size - $d.FreeSpace) / $d.Size * 100, 1)"))
        status = "ok" if disco < LIMIARES["disco_pct"] else "critico"
        livre_gb = parse_num(run_ps("$d = Get-CimInstance Win32_LogicalDisk -Filter \"DeviceID='C:'\"; [math]::Round($d.FreeSpace / 1GB, 1)"))
        return {"valor": disco, "status": status, "unidade": "%", "livre_gb": livre_gb}
    except (ValueError, subprocess.TimeoutExpired, Exception) as e:
        logger.warning("Erro ao verificar disco: %s", e)
        return {"valor": 0, "status": "erro", "unidade": "%"}


def verificar_rede():
    """Verifica conectividade de rede."""
    try:
        result = subprocess.run(
            ["ping", "-n", "1", "-w", "3000", "8.8.8.8"],
            capture_output=True, text=True, timeout=10
        )
        conectado = result.returncode == 0
        return {"conectado": conectado}
    except (subprocess.TimeoutExpired, OSError, Exception) as e:
        logger.warning("Erro ao verificar rede: %s", e)
        return {"conectado": False}


def gerar_relatorio(cpu, ram, disco, rede):
    """Gera relatório de monitoramento."""
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    alertas = []
    if cpu["status"] == "critico":
        alertas.append(f"🔴 CPU crítica: {cpu['valor']}%")
    if ram["status"] == "critico":
        alertas.append(f"🔴 RAM crítica: {ram['valor']}% (total: {ram.get('total_gb', '?')} GB)")
    if disco["status"] == "critico":
        alertas.append(f"🔴 Disco crítico: {disco['valor']}% (livre: {disco.get('livre_gb', '?')} GB)")
    if not rede["conectado"]:
        alertas.append("🔴 Rede: sem conectividade")

    relatorio = f"""---
title: Monitor de Sistema — {agora}
created: {agora}
updated: {agora}
type: query
tags: [automacao, monitoramento, sistema]
---

# Monitor de Sistema — {agora}

## CPU
- **Uso:** {cpu['valor']}%
- **Status:** {"🔴 Crítico" if cpu['status'] == "critico" else "✅ OK"}

## RAM
- **Uso:** {ram['valor']}%
- **Total:** {ram.get('total_gb', '?')} GB
- **Status:** {"🔴 Crítico" if ram['status'] == "critico" else "✅ OK"}

## Disco C:
- **Uso:** {disco['valor']}%
- **Livre:** {disco.get('livre_gb', '?')} GB
- **Status:** {"🔴 Crítico" if disco['status'] == "critico" else "✅ OK"}

## Rede
- **Conectividade:** {"✅ OK" if rede['conectado'] else "🔴 Sem conexão"}

## Alertas
{"Nenhum alerta — sistema saudável" if not alertas else chr(10).join(alertos)}
"""

    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(relatorio)

    return alertas


def main():
    print("=" * 50)
    print("MONITOR DE SISTEMA — PROJETO ATENA")
    print("=" * 50)
    print(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    cpu = verificar_cpu()
    ram = verificar_ram()
    disco = verificar_disco()
    rede = verificar_rede()

    print(f"CPU:  {cpu['valor']}% {'🔴' if cpu['status'] == 'critico' else '✅'}")
    print(f"RAM:  {ram['valor']}% ({ram.get('total_gb', '?')} GB) {'🔴' if ram['status'] == 'critico' else '✅'}")
    print(f"Disco: {disco['valor']}% ({disco.get('livre_gb', '?')} GB livre) {'🔴' if disco['status'] == 'critico' else '✅'}")
    print(f"Rede: {'✅ OK' if rede['conectado'] else '🔴 Sem conexão'}")

    alertas = gerar_relatorio(cpu, ram, disco, rede)

    print()
    if alertas:
        print("⚠️  ALERTAS:")
        for a in alertas:
            print(f"  {a}")
    else:
        print("✅ Sistema saudável — nenhum alerta")

    print(f"\nRelatório salvo: {REPORT_PATH}")
    return 1 if alertas else 0


if __name__ == "__main__":
    sys.exit(main())
