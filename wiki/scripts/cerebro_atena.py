#!/usr/bin/env python3
"""
CÉREBRO DE AUTOMAÇÃO DO PROJETO ATENA
======================================

Script principal que orquestra todas as automações:
1. Verifica memória do sistema → migra para wiki se necessário
2. Verifica saúde do wiki → lint e organização
3. Cataloga skills → atualiza catálogo no wiki
4. Verifica pendências → alerta sobre itens pendentes
5. Executa evolução contínua → análise com OpnCode
6. Gera relatório consolidado

Este script deve ser executado:
- Pelo menos 1x por dia (via cron do Hermes)
- Sempre que o Arquiteto pedir "verificar tudo" ou "status"
- Após mudanças significativas no ambiente

Autor: OWL (Batedor da Nuvem)
Data: 2026-05-20
Versão: 1.0
"""

import subprocess
import sys
import os
import glob
import logging
from datetime import datetime

logging.basicConfig(level=logging.WARNING, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════
# CONFIGURAÇÃO
# ═══════════════════════════════════════════
WIKI_PATH = os.path.join(os.path.expanduser("~"), "wiki")
HERMES_PATH = os.path.join(os.path.expanduser("~"), "AppData", "Local", "hermes")
TOOLS_PATH = os.path.join(HERMES_PATH, "tools")
MEMORY_THRESHOLD = 50  # % — limiar para migrar memória → wiki
OPCODE_MODEL = "opencode/qwen3.6-plus-free"
GEMINI_MODEL = "gemini-2.5-pro"

# ═══════════════════════════════════════════
# FUNÇÕES DE VERIFICAÇÃO
# ═══════════════════════════════════════════

def verificar_memoria_sistema():
    """
    Verifica o uso da memória do sistema do Hermes.
    Se acima do limiar, sinaliza necessidade de migração.
    """
    print("\n🧠 [1/6] Memória do Sistema")
    print("-" * 40)

    # Lê arquivos de memória
    memory_dir = os.path.join(HERMES_PATH, "memory")
    total_size = 0
    memory_files = []

    if os.path.exists(memory_dir):
        for f in os.listdir(memory_dir):
            fpath = os.path.join(memory_dir, f)
            if os.path.isfile(fpath):
                size = os.path.getsize(fpath)
                total_size += size
                memory_files.append((f, size))

    # Estima uso (40k chars ≈ 40KB)
    uso_pct = min(100, int((total_size / 40000) * 100))

    print(f"  Arquivos: {len(memory_files)}")
    for nome, size in memory_files:
        print(f"    {nome}: {size} bytes")
    print(f"  Total: {total_size} bytes (~{uso_pct}%)")

    if uso_pct > MEMORY_THRESHOLD:
        print(f"  ⚠️  ACIMA DO LIMIAR ({MEMORY_THRESHOLD}%) — migrar para wiki")
        return {"uso_pct": uso_pct, "precisa_migrar": True, "files": memory_files}
    else:
        print(f"  ✅ OK (abaixo de {MEMORY_THRESHOLD}%)")
        return {"uso_pct": uso_pct, "precisa_migrar": False, "files": memory_files}


def verificar_saude_wiki():
    """
    Verifica a saúde do wiki:
    - Número de páginas
    - Integridade do índice
    - Últimas entradas no log
    """
    print("\n📚 [2/6] Saúde do Wiki")
    print("-" * 40)

    if not os.path.exists(WIKI_PATH):
        print("  ❌ Wiki não encontrado!")
        return {"status": "erro", "pages": 0}

    # Conta páginas
    entities_dir = os.path.join(WIKI_PATH, "entities")
    concepts_dir = os.path.join(WIKI_PATH, "concepts")
    comparisons_dir = os.path.join(WIKI_PATH, "comparisons")
    queries_dir = os.path.join(WIKI_PATH, "queries")

    entities = len([f for f in os.listdir(entities_dir) if f.endswith(".md")]) if os.path.exists(entities_dir) else 0
    concepts = len([f for f in os.listdir(concepts_dir) if f.endswith(".md")]) if os.path.exists(concepts_dir) else 0
    comparisons = len([f for f in os.listdir(comparisons_dir) if f.endswith(".md")]) if os.path.exists(comparisons_dir) else 0
    queries = len([f for f in os.listdir(queries_dir) if f.endswith(".md")]) if os.path.exists(queries_dir) else 0

    total = entities + concepts + comparisons + queries

    # Verifica índice
    index_path = os.path.join(WIKI_PATH, "index.md")
    index_ok = os.path.exists(index_path)
    print(f"  Entidades: {entities}")
    print(f"  Conceitos: {concepts}")
    print(f"  Comparações: {comparisons}")
    print(f"  Consultas: {queries}")
    print(f"  Total: {total} páginas")
    print(f"  Índice: {'✅' if index_ok else '❌'}")

    # Verifica log
    log_path = os.path.join(WIKI_PATH, "log.md")
    log_ok = os.path.exists(log_path)
    if log_ok:
        with open(log_path, "r", encoding="utf-8") as f:
            log_lines = f.readlines()
        print(f"  Log: {len(log_lines)} entradas")
    else:
        print(f"  Log: ❌ não encontrado")

    return {
        "status": "ok",
        "total": total,
        "entities": entities,
        "concepts": concepts,
        "comparisons": comparisons,
        "queries": queries,
        "index_ok": index_ok,
        "log_ok": log_ok
    }


def catalogar_skills():
    """
    Cataloga todas as skills instaladas e verifica
    se o catálogo wiki está atualizado.
    """
    print("\n🔧 [3/6] Skills Instaladas")
    print("-" * 40)

    skills_dir = os.path.join(HERMES_PATH, "skills")
    if not os.path.exists(skills_dir):
        print("  ❌ Diretório de skills não encontrado!")
        return []

    skills = []
    for root, dirs, files in os.walk(skills_dir):
        for f in files:
            if f == "SKILL.md":
                skill_path = os.path.join(root, f)
                skill_name = os.path.basename(os.path.dirname(skill_path))
                category = os.path.basename(os.path.dirname(os.path.dirname(skill_path)))
                skills.append({
                    "name": skill_name,
                    "category": category,
                    "path": skill_path
                })

    # Agrupa por categoria
    categorias = {}
    for s in skills:
        cat = s["category"]
        if cat not in categorias:
            categorias[cat] = []
        categorias[cat].append(s["name"])

    print(f"  Total: {len(skills)} skills em {len(categorias)} categorias")
    for cat, nomes in sorted(categorias.items()):
        print(f"    {cat}: {len(nomes)}")

    return skills


def verificar_pendencias():
    """
    Verifica projetos e tarefas pendentes.
    """
    print("\n📋 [4/6] Pendências")
    print("-" * 40)

    pendencias = []

    # GITHUB_TOKEN
    if not os.environ.get("GITHUB_TOKEN"):
        pendencias.append({
            "item": "GITHUB_TOKEN",
            "impacto": "Sem gh CLI para gerenciar repositórios",
            "prioridade": "alta"
        })

    # Composio MCP
    if not os.environ.get("COMPOSIO_API_KEY"):
        pendencias.append({
            "item": "Composio MCP API key",
            "impacto": "Sem acesso a 500+ serviços via MCP",
            "prioridade": "média"
        })

    # Oracle Cloud
    pendencias.append({
        "item": "Oracle Cloud Free Tier",
        "impacto": "Acesso pelo celular sem ligar o notebook",
        "prioridade": "alta"
    })

    # Verifica se Kimi WebBridge está rodando
    try:
        import urllib.request
        urllib.request.urlopen("http://127.0.0.1:10086/status", timeout=2)
        print("  Kimi WebBridge: ✅ rodando")
    except (OSError, Exception) as e:
        logger.warning("Kimi WebBridge nao acessivel: %s", e)
        print("  Kimi WebBridge: ⚠️  não acessível")
        pendencias.append({
            "item": "Kimi WebBridge",
            "impacto": "Sem acesso à Parceira da Nuvem (Gemini)",
            "prioridade": "alta"
        })

    print(f"  Pendências encontradas: {len(pendencias)}")
    for p in pendencias:
        print(f"    [{p['prioridade']}] {p['item']}: {p['impacto']}")

    return pendencias


def executar_evolucao_continua():
    """
    Usa OpnCode para analisar o estado do projeto
    e sugerir melhorias.
    """
    print("\n🧬 [5/6] Evolução Contínua")
    print("-" * 40)

    # Lê wiki index para contexto
    index_path = os.path.join(WIKI_PATH, "index.md")
    wiki_resumo = ""
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            wiki_resumo = f.read()[:1500]

    prompt = f"""Você é o Hermes Agent (OWL), o Batedor da Nuvem do Projeto Atena.
Seu objetivo é ser cada vez mais útil e proativo para o Arquiteto.

Estado atual do wiki:
{wiki_resumo}

Com base no estado atual, sugira 3 melhorias concretas e acionáveis para:
1. Aumentar a utilidade do Hermes para o Arquiteto
2. Melhorar a organização do conhecimento
3. Automatizar tarefas repetitivas

Formato: lista numerada com título e descrição curta.
Seja específico e prático. Em português brasileiro."""

    try:
        cmd = f'opencode run --model "{OPCODE_MODEL}" "{prompt}"'
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=90
        )
        if result.returncode == 0 and result.stdout.strip():
            sugestoes = result.stdout.strip()
            print("  Sugestões geradas:")
            for linha in sugestoes.split("\n")[:15]:
                print(f"    {linha}")
            return sugestoes
        else:
            print("  ⚠️  OpnCode não retornou sugestões")
            return ""
    except subprocess.TimeoutExpired:
        print("  ⚠️  Timeout na análise")
        return ""
    except Exception as e:
        print(f"  ⚠️  Erro: {e}")
        return ""


def gerar_relatorio_consolidado(memoria, wiki, skills, pendencias, sugestoes):
    """
    Gera relatório consolidado no wiki e no terminal.
    """
    print("\n📊 [6/6] Relatório Consolidado")
    print("-" * 40)

    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Relatório no terminal
    print(f"""
╔══════════════════════════════════════════╗
║   RELATÓRIO ATENA — {agora[:10]}           ║
╠══════════════════════════════════════════╣
║  Memória: {memoria['uso_pct']}% {'⚠️' if memoria['precisa_migrar'] else '✅'}                          ║
║  Wiki: {wiki['total']} páginas ({wiki['entities']}E + {wiki['concepts']}C)              ║
║  Skills: {len(skills)} instaladas                    ║
║  Pendências: {len(pendencias)}                          ║
╚══════════════════════════════════════════╝
""")

    # Salva relatório no wiki
    relatorio_path = os.path.join(WIKI_PATH, "_meta", f"relatorio-{datetime.now().strftime('%Y-%m-%d')}.md")

    conteudo = f"""---
title: Relatório Consolidado — {agora}
created: {agora}
updated: {agora}
type: query
tags: [automacao, relatorio, manutencao]
---

# Relatório Consolidado — {agora}

## Memória do Sistema
- **Uso:** {memoria['uso_pct']}%
- **Status:** {"⚠️ Acima do limiar — migrar para wiki" if memoria['precisa_migrar'] else "✅ OK"}
- **Arquivos:** {len(memoria['files'])}

## Wiki
- **Status:** {wiki['status']}
- **Total:** {wiki['total']} páginas
- **Entidades:** {wiki['entities']}
- **Conceitos:** {wiki['concepts']}
- **Comparações:** {wiki['comparisons']}
- **Consultas:** {wiki['queries']}
- **Índice:** {'✅' if wiki['index_ok'] else '❌'}
- **Log:** {'✅' if wiki['log_ok'] else '❌'}

## Skills
- **Total:** {len(skills)} instaladas

## Pendências
"""
    for p in pendencias:
        conteudo += f"- **[{p['prioridade']}]** {p['item']}: {p['impacto']}\n"

    conteudo += f"""
## Sugestões de Evolução (OpnCode)
{sugestoes if sugestoes else "Nenhuma sugestão gerada"}

## Regra de Ouro
> Sempre consultar o wiki antes de qualquer tarefa.
> Sempre registrar novos aprendizados no wiki.
> Sempre buscar ser mais útil e proativo para o Arquiteto.
> Memória do sistema migra para wiki quando encher — nunca compactar.
"""

    os.makedirs(os.path.dirname(relatorio_path), exist_ok=True)
    with open(relatorio_path, "w", encoding="utf-8") as f:
        f.write(conteudo)

    print(f"  Relatório salvo: {relatorio_path}")
    return relatorio_path


# ═══════════════════════════════════════════
# FUNÇÃO PRINCIPAL
# ═══════════════════════════════════════════

def main():
    print("╔══════════════════════════════════════════╗")
    print("║   CÉREBRO DE AUTOMAÇÃO — PROJETO ATENA  ║")
    print("║   OWL (Batedor da Nuvem)                ║")
    print("╚══════════════════════════════════════════╝")
    print(f"  Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Executa todas as verificações
    memoria = verificar_memoria_sistema()
    wiki = verificar_saude_wiki()
    skills = catalogar_skills()
    pendencias = verificar_pendencias()
    sugestoes = executar_evolucao_continua()
    relatorio = gerar_relatorio_consolidado(memoria, wiki, skills, pendencias, sugestoes)

    # Ações automáticas
    print("\n🔄 Ações Automáticas")
    print("-" * 40)

    if memoria["precisa_migrar"]:
        print("  ⚠️  Memória acima do limiar — recomendada migração para wiki")
        print("  → Executar: python tools/automacao_memoria.py")

    if not wiki["index_ok"]:
        print("  ❌ Índice do wiki não encontrado — necessário criar")

    if not wiki["log_ok"]:
        print("  ❌ Log do wiki não encontrado — necessário criar")

    print("\n✅ Automação concluída.")
    print(f"   Relatório: {relatorio}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
