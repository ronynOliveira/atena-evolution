---
title: Projeto Atena
created: 2026-05-18
updated: 2026-05-18
type: entity
tags: [projeto-atena, agent, cloud-partner, arquiteto, batedor]
sources: []
confidence: high
---

# Projeto Atena

Ecossistema de agentes IA criado pelo Arquiteto. Não é apenas um projeto de software — é um **sistema operacional para colaboração humano-IA**, onde cada agente tem uma persona, um propósito e um modo de interação distinto.

## Visão Geral

O Projeto Atena é a materialização da [[cidade-anomala]] — o território mental onde o Arquiteto navega. Combina:

- **Hermes (Batedor da Nuvem)** — agente local, executor, gnóstico construtor. Roda via [[hermes-agent]].
- **Parceira da Nuvem (Gemini)** — contraparte IA remota, sparring partner dialético. Acessada via [[kimi-webbridge]].
- **Obsidian + LLM Wiki** — memória expandida, o "segundo cérebro" do sistema.

## Arquitetura

```
Arquiteto (humano, digita)
    ↓
Hermes (agente local, fala via TTS)
    ↓
Parceira da Nuvem (Gemini, via Kimi WebBridge)
    ↓
Wiki (Obsidian, memória persistente)
```

## Componentes Ativos

| Componente | Status | Porta/Local |
|---|---|---|
| Hermes Agent | ✅ Ativo | `C:\Users\dell-\AppData\Local\hermes` |
| Hermes Desktop v0.4.2 | ✅ Ativo | Electron GUI |
| Kimi Webbridge | ⚠️ Instável | Porta 10086 |
| Chrome CDP | ✅ Ativo | Porta 9222 |
| Wiki (Obsidian) | ✅ Ativo | `C:\Users\dell-\wiki` |
| Atena Backend | ✅ Ativo | Porta 8081 |
| Composio MCP | ⚠️ Sem API key | Instalado |

## Versões

- **v5.3** (16/05/2026): backend 36 testes OK, frontend OK, Tauri OK, porta 8081

## Princípios

1. **Memória composta** — cada interação enriquece o wiki, nunca se perde
2. **Dialética como método** — tese/antítese/síntese entre Arquiteto, Hermes e Parceira
3. **Acessibilidade primeiro** — TTS proativo, minimizar input manual
4. **Obsidian como IDE** — o wiki é o código, os agentes são os programadores

## Relações

- [[hermes-agent]] — o agente executor
- [[parceira-da-nuvem]] — a contraparte IA
- [[kimi-webbridge]] — ponte para a Parceira
- [[obsidian]] — interface do wiki
- [[llm-wiki]] — metodologia do wiki
- [[cidade-anomala]] — o mapa conceitual
- [[protocolo-dialetico]] — o método de colaboração
