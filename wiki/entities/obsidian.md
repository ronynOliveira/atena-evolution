---
title: Obsidian
created: 2026-05-18
updated: 2026-05-18
type: entity
tags: [obsidian, ferramenta, projeto-atena]
sources: [raw/articles/karpathy-llm-wiki-2026.md]
confidence: high
---

# Obsidian

> Ver também: [[llm-wiki]] (metodologia Karpathy), [[projeto-atena]] (wiki)

Editor de notas markdown que serve como **interface gráfica** para o wiki do Projeto Atena. É o "IDE" onde o Arquiteto navega o conhecimento construído pelos agentes.

## O que é

Obsidian é um editor de markdown baseado em links (wikilinks). Cada nota é um arquivo `.md`, e notas se conectam via wikilinks. O resultado é um **grafo de conhecimento** navegável.

## Como usamos

O wiki do Projeto Atena (`C:\Users\dell-\wiki`) é um **vault Obsidian**. Isso significa que:

- Cada página wiki é um arquivo `.md` editável no Obsidian
- `[[wikilinks]]` aparecem como links clicáveis
- O **Graph View** mostra visualmente as conexões entre conceitos
- O **Dataview** permite queries sobre frontmatter (tags, datas, tipos)

## Configuração

- **Vault path**: `C:\Users\dell-\wiki` (= `OBSIDIAN_VAULT_PATH` = `WIKI_PATH`)
- **Attachment folder**: `raw/assets/`
- **Wikilinks**: habilitado (padrão)

## Plugins Recomendados

| Plugin | Função |
|---|---|
| **Dataview** | Queries sobre frontmatter (tags, datas) |
| **Marp** | Slides a partir de markdown |
| **Web Clipper** | Salvar artigos web como markdown |

## Relações

- [[llm-wiki]] — a metodologia que o Obsidian visualiza
- [[cidade-anomala]] — o mapa que o Obsidian renderiza
- [[projeto-atena]] — o projeto que usa o Obsidian
