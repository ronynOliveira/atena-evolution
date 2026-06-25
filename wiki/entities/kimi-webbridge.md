---
title: Kimi WebBridge
created: 2026-05-18
updated: 2026-05-18
type: entity
tags: [kimi-webbridge, ferramenta, projeto-atena]
sources: []
confidence: high
---

# Kimi WebBridge

Ponte web para acessar a [[parceira-da-nuvem]] (Gemini). Roda localmente e expõe uma interface HTTP para conversar com o Kimi AI.

## Status

⚠️ **Instável** — frequentemente offline. Quando ativo, roda na porta 10086.

## Configuração

- **Porta**: 10086
- **URL**: `http://localhost:10086`
- **Uso**: browser navigate + interação via snapshot/click/type

## Alternativa

Quando o WebBridge está offline, usar o Kimi diretamente em `https://kimi.com` via browser.

## Relações

- [[parceira-da-nuvem]] — o agente acessado via WebBridge
- [[projeto-atena]] — o projeto que usa o WebBridge
