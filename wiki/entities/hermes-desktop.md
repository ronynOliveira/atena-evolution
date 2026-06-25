---
title: Hermes Desktop v0.4.3
created: 2026-05-20
updated: 2026-05-20
type: entity
tags: [hermes-agent, ferramenta]
sources: [raw/hermes-memory-export.md]
confidence: high
---

# Hermes Desktop v0.4.3

> Ver também: [[hermes-agent]] (framework), [[koldi-browser-plugin]] (plugin navegador)

## Registro migrado da memória do sistema do Hermes.

### O que é
Interface gráfica (GUI) para o Hermes Agent. Electron 39 + React 19 + TypeScript 5.9.

### Instalação
- **Local:** `C:\Users\dell-\AppData\Local\Programs\hermes-desktop`
- **Instalador:** `hermes-desktop-0.4.3-setup.exe`
- **Atalho:** Start Menu > Hermes Agent

### Funcionalidades
- Chat com o agente
- Gerenciamento de sessões
- Profiles (perfis de configuração)
- Memory (visualização e edição)
- Skills (gerenciamento)
- Tools (configuração de ferramentas)
- Scheduling (tarefas agendadas/cron)
- Messaging gateways (Telegram, Discord, etc.)

### Versão
- **Atual:** v0.4.3 (atualizado de v0.4.2 em 20/05/2026)
- **Stack:** Electron 39, React 19, TypeScript 5.9

### Verificação de Atualizações
Script `tools/verificar_atualizacoes.py` executa a cada 12h via cron job `atena-verificar-atualizacoes`.

## Ver também
- [[hermes-agent]]
- [[ambiente-tecnico]]
- [[automacao-atena]]
