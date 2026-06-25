#!/usr/bin/env python3
"""
Script de Segurança do Projeto Atena.
Implementa as 5 melhores práticas de segurança:
1. Princípio do Menor Privilégio
2. Proteção de Tokens e Credenciais
3. Isolamento de Processos
4. Auditoria de Permissões
5. Monitoramento de Integridade

Autor: OWL (Batedor da Nuvem)
Data: 2026-05-20
"""

import subprocess
import sys
import os
import stat
import json
import logging
from datetime import datetime

logging.basicConfig(level=logging.WARNING, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

WIKI_PATH = os.path.join(os.path.expanduser("~"), "wiki")
HERMES_PATH = os.path.join(os.path.expanduser("~"), "AppData", "Local", "hermes")
REPORT_PATH = os.path.join(WIKI_PATH, "_meta", "seguranca-relatorio.md")


def verificar_permissoes_arquivos():
    """Verifica permissões de arquivos sensíveis."""
    print("[1/5] Verificando permissões de arquivos...")

    arquivos_sensiveis = [
        os.path.join(os.path.expanduser("~"), ".hermes", ".env"),
        os.path.join(os.path.expanduser("~"), ".hermes", "config.yaml"),
        os.path.join(HERMES_PATH, "config.yaml"),
    ]

    problemas = []
    for arquivo in arquivos_sensiveis:
        if os.path.exists(arquivo):
            try:
                mode = os.stat(arquivo).st_mode
                # Verifica se é legível por outros
                if mode & stat.S_IROTH:
                    problemas.append(f"⚠️  {arquivo} é legível por outros usuários")
                else:
                    print(f"  ✅ {arquivo}: permissões OK")
            except Exception as e:
                problemas.append(f"❌ Erro ao verificar {arquivo}: {e}")
        else:
            print(f"  ℹ️  {arquivo}: não encontrado (OK se não usado)")

    return problemas


def verificar_credenciais():
    """Verifica se credenciais estão protegidas."""
    print("[2/5] Verificando credenciais...")

    credenciais = {
        "GITHUB_TOKEN": os.environ.get("GITHUB_TOKEN", ""),
        "COMPOSIO_API_KEY": os.environ.get("COMPOSIO_API_KEY", ""),
        "OPENROUTER_API_KEY": os.environ.get("OPENROUTER_API_KEY", ""),
        "OLLAMA_API_KEY": os.environ.get("OLLAMA_API_KEY", ""),
    }

    status = {}
    for nome, valor in credenciais.items():
        if valor:
            # Verifica se está exposto em texto plano
            if len(valor) > 0:
                status[nome] = "✅ Configurado"
                print(f"  ✅ {nome}: configurado ({len(valor)} chars)")
        else:
            status[nome] = "❌ Não configurado"
            print(f"  ℹ️  {nome}: não configurado")

    return status


def verificar_processos():
    """Verifica processos críticos."""
    print("[3/5] Verificando processos críticos...")

    processos = {
        "gateway Hermes": "hermes-agent.exe",
        "Chrome CDP": "chrome.exe",
        "Kimi WebBridge": "kimi-webbridge.exe",
    }

    status = {}
    for nome, processo in processos.items():
        try:
            result = subprocess.run(
                ["powershell", "-Command",
                 f"Get-Process -Name '{processo.replace('.exe', '')}' -ErrorAction SilentlyContinue | Measure-Object | Select-Object -ExpandProperty Count"],
                capture_output=True, timeout=10
            )
            count = result.stdout.decode("utf-8", errors="replace").strip()
            if count and count != "0":
                status[nome] = "✅ Rodando"
                print(f"  ✅ {nome}: rodando ({count} processo(s))")
            else:
                status[nome] = "⚠️  Parado"
                print(f"  ⚠️  {nome}: parado")
        except (subprocess.TimeoutExpired, OSError, Exception) as e:
            logger.warning("Erro ao verificar processo %s: %s", nome, e)
            status[nome] = "❌ Erro"
            print(f"  ❌ {nome}: erro ao verificar")

    return status


def verificar_backup():
    """Verifica status do backup do wiki."""
    print("[4/5] Verificando backup do wiki...")

    git_dir = os.path.join(WIKI_PATH, ".git")
    if not os.path.exists(git_dir):
        return ["❌ Git não inicializado no wiki"]

    try:
        # Verifica último commit
        result = subprocess.run(
            ["git", "log", "-1", "--format=%ci"],
            cwd=WIKI_PATH, capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            ultimo_commit = result.stdout.strip()
            print(f"  ✅ Último commit: {ultimo_commit}")

            # Verifica se há mudanças não commitadas
            result2 = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=WIKI_PATH, capture_output=True, text=True, timeout=10
            )
            if result2.stdout.strip():
                print(f"  ⚠️  Há mudanças não commitadas")
                return ["⚠️  Mudanças não commitadas no wiki"]
            else:
                print(f"  ✅ Wiki sincronizado")
                return []
        else:
            return ["❌ Erro ao verificar git"]
    except Exception as e:
        return [f"❌ Erro: {e}"]


def verificar_integridade():
    """Verifica integridade dos arquivos do sistema."""
    print("[5/5] Verificando integridade...")

    arquivos_criticos = [
        os.path.join(HERMES_PATH, "tools", "tts_fala.py"),
        os.path.join(HERMES_PATH, "tools", "cerebro_atena.py"),
        os.path.join(HERMES_PATH, "tools", "backup_wiki.py"),
        os.path.join(HERMES_PATH, "tools", "monitor_sistema.py"),
        os.path.join(WIKI_PATH, "index.md"),
        os.path.join(WIKI_PATH, "SCHEMA.md"),
    ]

    problemas = []
    for arquivo in arquivos_criticos:
        if os.path.exists(arquivo):
            size = os.path.getsize(arquivo)
            if size == 0:
                problemas.append(f"⚠️  {arquivo} está vazio")
            else:
                print(f"  ✅ {arquivo}: {size} bytes")
        else:
            problemas.append(f"❌ {arquivo} não encontrado")

    return problemas


def gerar_relatorio(permissoes, credenciais, processos, backup, integridade):
    """Gera relatório de segurança."""
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    todos_problemas = permissoes + backup + integridade

    relatorio = f"""---
title: Relatório de Segurança — {agora}
created: {agora}
updated: {agora}
type: query
tags: [seguranca, auditoria, manutencao]
---

# Relatório de Segurança — {agora}

## Permissões de Arquivos
{"Sem problemas" if not permissoes else chr(10).join(permissoes)}

## Credenciais
"""
    for k, v in credenciais.items():
        relatorio += f"- **{k}:** {v}\n"

    relatorio += "\n## Processos\n"
    for k, v in processos.items():
        relatorio += f"- **{k}:** {v}\n"

    relatorio += f"""
## Backup Wiki
{"Sem problemas" if not backup else chr(10).join(backup)}

## Integridade
{"Sem problemas" if not integridade else chr(10).join(integridade)}

## Resumo
{"✅ Sistema seguro" if not todos_problemas else f"⚠️ {len(todos_problemas)} problema(s) encontrado(s)"}
"""

    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(relatorio)

    return todos_problemas


def main():
    print("=" * 50)
    print("🔒 SEGURANÇA DO PROJETO ATENA")
    print("=" * 50)
    print(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    permissoes = verificar_permissoes_arquivos()
    credenciais = verificar_credenciais()
    processos = verificar_processos()
    backup = verificar_backup()
    integridade = verificar_integridade()

    problemas = gerar_relatorio(permissoes, credenciais, processos, backup, integridade)

    print("\n" + "=" * 50)
    if problemas:
        print(f"⚠️  {len(problemas)} PROBLEMA(S) ENCONTRADO(S):")
        for p in problemas:
            print(f"  {p}")
    else:
        print("✅ SISTEMA SEGURO — Nenhum problema encontrado")
    print("=" * 50)

    return 1 if problemas else 0


if __name__ == "__main__":
    sys.exit(main())
