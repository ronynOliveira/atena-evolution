---
title: Plano de Refinamento da Lógica do OWL
created: 2026-05-20
updated: 2026-05-20
type: concept
tags: [refinamento, arquitetura, evolucao, planejamento]
sources: [analise-arquitetura.md]
confidence: high
---

# Plano de Refinamento da Lógica do OWL

## Resumo Executivo

Análise completa da arquitetura do Projeto Atena realizada em 20/05/2026.
**103 skills** analisadas, **25 scripts Python** verificados, **47 cron jobs** identificados.

### Status Geral
- ✅ Sintaxe: 100% (25/25 scripts OK)
- ⚠️ Tratamento de erro: 88% (22/25 scripts)
- ⚠️ Logging: 36% (9/25 scripts)
- 🔴 Gateway: NÃO RODANDO (47 cron jobs não disparam)

---

## Pontos Fracos Identificados

### 🔴 Críticos (Corrigidos)
1. **automacao_memoria.py** — Sem try/except nem logging → ✅ CORRIGIDO
2. **tts_rapido.py** — Sem try/except nem logging → ✅ CORRIGIDO
3. **tts_streaming.py** — Sem try/except nem logging → ✅ CORRIGIDO

### 🟡 Alertas (35 identificados)
- 16 scripts sem logging
- 4 páginas do wiki não referenciadas no index.md
- Sobreposição: busca_web.py e pesquisa_web.py
- Sobreposição: 5 scripts TTS (tts_fala, tts_rapido, tts_streaming, tts_play, tts_fix)
- Skills de categorias mlops/* sem SKILL.md (são subdiretórios, não skills)

### 🔴 Gateway não rodando
- **Causa:** UnicodeDecodeError no subprocess + permissão de administrador
- **Impacto:** 47 cron jobs ativos mas NÃO disparam automaticamente
- **Solução:** Executar `hermes gateway install` como Administrador
- **Status:** ⏳ Aguardando execução pelo Arquiteto

---

## Melhorias Implementadas

### 1. Módulo de Logging Centralizado
- **Arquivo:** `tools/atena_logging.py`
- **Função:** Logger consistente para todos os scripts
- **Recursos:** Log em arquivo + console, rotação diária, fallback se módulo indisponível

### 2. Scripts de Evolução (gerados pelo Opencode)
- **analisador_arquitetura.py** (~480 linhas) — Análise completa da arquitetura
- **gerador_skill.py** (~620 linhas) — Gera skills automaticamente
- **testador_scripts.py** (~720 linhas) — Testa sintaxe, imports, execução

### 3. Correções Aplicadas
- automacao_memoria.py: +try/except, +logging
- tts_rapido.py: +try/except, +logging
- tts_streaming.py: +try/except, +logging

---

## Próximos Passos

### Imediatos
1. ✅ Módulo de logging centralizado criado
2. ✅ Scripts críticos corrigidos com try/except
3. ⏳ Executar `hermes gateway install` como Administrador
4. ⏳ Consolidar busca_web.py e pesquisa_web.py
5. ⏳ Consolidar scripts TTS em módulo único

### Curto Prazo
6. Adicionar logging aos 16 scripts restantes
7. Adicionar type hints a funções públicas
8. Criar testes unitários para funções críticas
9. Atualizar index.md com páginas faltantes

### Médio Prazo
10. Implementar health check para todos os scripts
11. Criar dashboard de monitoramento
12. Implementar retry automático para operações de rede
13. Adicionar métricas de performance

---

## Arquitetura de Dependências (Mapa)

```
cerebro_atena.py (orquestrador)
  ├── automacao_memoria.py
  ├── evolucao_continua.py
  └── (chama outros via subprocess)

seguranca.py (auditoria)
  ├── backup_wiki.py
  ├── cerebro_atena.py
  ├── monitor_sistema.py
  └── tts_fala.py

motor_evolucao.py (auto-evolução)
  └── seguranca.py

ensemble_modelos.py
  └── ollama_chat.py

raciocinar.py
  └── ollama_chat.py

tts_rapido.py
  └── tts_streaming.py
```

---

## Ver também
- [[analise-arquitetura]] — Relatório completo da análise
- [[automacao-atena]] — Sistema de automação
- [[catalogo-skills]] — Catálogo de 103 skills
- [[projetos-pendentes]] — Pendências do projeto
