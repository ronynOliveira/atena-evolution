---
title: Próximos Passos de Evolução do OWL
created: 2026-05-20
updated: 2026-05-20
type: concept
tags: [evolucao, proximos-passos, melhorias, owl]
sources: []
confidence: high
---

# Próximos Passos de Evolução do OWL

## Concluído ✅
- [x] Corrigir bugs críticos (3)
- [x] Criar módulo lib/ compartilhado
- [x] Consolidar scripts TTS
- [x] Adicionar tipos de exceção específicos (12)
- [x] Validar ideia de subagentes paralelos

## Próximas Prioridades

### 1. Expandir Memória do Hermes
- MEMORY.md: apenas 2.200 chars (muito limitado)
- Solução: migrar mais dados para o wiki, usar memória dinâmica
- Prioridade: ALTA

### 2. Instalar Modelo de Visão Leve
- PaddleOCR-VL 0.9B (~1GB) — OCR rápido em CPU
- LLaVA 7B (~4.7GB) — visão mais leve
- Prioridade: MÉDIA (sem GPU, será lento)

### 3. Configurar Gateway Hermes
- `hermes gateway install` — instalar como serviço
- Configurar Telegram Bot para acesso celular
- Prioridade: ALTA

### 4. Melhorar RAG Local
- Implementar busca semântica em sessões passadas
- Usar nomic-embed-text para embeddings
- Prioridade: MÉDIA

### 5. Otimizar Prompts
- Reduzir system prompt pesado
- Implementar lazy loading de context files
- Prioridade: BAIXA

### 6. Testes Automatizados
- Criar suite de testes para os scripts
- Testar TTS, busca web, monitoramento
- Prioridade: MÉDIA
