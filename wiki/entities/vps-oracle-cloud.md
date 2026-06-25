---
title: VPS Oracle Cloud — Projeto Nuvem
created: 2026-05-20
updated: 2026-05-20
type: entity
tags: [projeto-atena, ferramenta, ia]
sources: [raw/hermes-memory-export.md]
confidence: medium
---

# VPS Oracle Cloud — Projeto Nuvem

> Ver também: [[ambiente-tecnico]] (infraestrutura), [[hermes-agent]] (gateway)

## Registro migrado da memória do sistema do Hermes.

### Objetivo
Manter o Hermes na nuvem para o Arquiteto acessar pelo celular sem precisar ligar o notebook.

### Melhor Opção: Oracle Cloud Free Tier
- **CPU:** 4 ARM cores
- **RAM:** 24 GB
- **Disco:** 200 GB
- **Custo:** Grátis para sempre

### Acesso pelo Celular
- **Telegram Bot** — interface principal
- **SSH via Termius** — acesso técnico

### Banco de Dados
- **SQLite local** — para o wiki
- **Supabase Free** — para dados estruturados
- **Upstash Redis** — para cache

### Status
- **Pendente:** Criar conta Oracle Cloud e provisionar instância
- **Decisão:** Aprovada pelo Arquiteto, aguardando implementação

## Ver também
- [[projeto-atena]]
- [[hermes-agent]]
- [[ambiente-tecnico]]
