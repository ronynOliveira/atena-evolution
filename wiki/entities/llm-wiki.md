---
title: LLM Wiki (Karpathy)
created: 2026-05-18
updated: 2026-05-18
type: entity
tags: [llm-wiki, ferramenta, projeto-atena, metodologia]
sources: [raw/articles/karpathy-llm-wiki-2026.md]
confidence: high
---

# LLM Wiki

> Ver também: [[obsidian]] (editor), [[projeto-atena]] (wiki do Projeto Atena)

Padrão de base de conhecimento criado por **Andrej Karpathy**. A ideia central: em vez de RAG (que redescobre tudo a cada query), o LLM **constrói incrementalmente um wiki persistente** de markdowns interligados.

## O Problema do RAG

RAG tradicional:
1. Upload documentos
2. Em cada query, recupera chunks relevantes
3. Gera resposta
4. **Descarta tudo** — na próxima query, repete do zero

O LLM não acumula conhecimento. Perguntas sutis que exigem sintetizar 5 documentos são caras e imprevisíveis.

## A Solução Karpathy

O LLM **compila** o conhecimento uma vez e **mantém atualizado**:
1. Lê a fonte
2. Extrai entidades e conceitos
3. Cria/atualiza páginas wiki
4. Adiciona wikilinks entre páginas
5. Registra no log

O wiki é um **artefato composto** — cada fonte adicionada enriquece tudo que já existe.

## As 3 Camadas

| Camada | Conteúdo | Quem mantém |
|---|---|---|
| **raw/** | Fontes originais (imutáveis) | Arquiteto deposita |
| **entities/, concepts/, ...** | Páginas wiki (markdown) | LLM cria e atualiza |
| **SCHEMA.md** | Convenções e estrutura | Arquiteto + LLM co-evoluem |

## Operações

- **Ingest**: adicionar fonte → LLM processa → wiki atualizado
- **Query**: perguntar → LLM busca no wiki → resposta com citações
- **Lint**: health-check → contradições, órfãos, stale content

## Por que funciona

O custo de manutenção de um wiki por humanos cresce mais rápido que o valor. LLMs não se cansam, não esquecem cross-references, e podem tocar 15 arquivos em uma passagem. O wiki se mantém porque o custo de manutenção é próximo de zero.

## Relações

- [[obsidian]] — a interface gráfica do wiki
- [[cidade-anomala]] — o wiki é o mapa da cidade
- [[projeto-atena]] — o projeto que usa o padrão
- [[hermes-agent]] — o agente que mantém o wiki
