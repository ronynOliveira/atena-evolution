---
title: Chrome CDP
created: 2026-05-18
updated: 2026-05-18
type: entity
tags: [chrome-cdp, ferramenta, projeto-atena]
sources: []
confidence: high
---

# Chrome CDP

> Ver também: [[kimi-webbridge]] (Kimi), [[hermes-agent]] (browser tools)

Controle do navegador Chrome via **Chrome DevTools Protocol**. Permite ao [[hermes-agent]] navegar páginas, clicar, digitar e extrair conteúdo.

## Configuração

- **Porta**: 9222
- **URL**: `http://localhost:9222`
- **Uso**: browser tools do Hermes Agent

## Nota Importante

Google bloqueia login via CDP. Se precisar reiniciar o Chrome, **matar o processo antes** (`taskkill /IM chrome.exe /F`).

## Relações

- [[hermes-agent]] — o agente que usa o CDP
- [[projeto-atena]] — o projeto que usa o CDP
