# PLANO DE FUSÃO: ATENA EVOLUÇÃO + ECOSISTEMA KOLDI

**Data:** 2026-06-24
**Versão:** 1.0
**Status:** Pronto para execução

---

## 1. VISÃO GERAL

Fundir o melhor dos dois mundos:
- **Koldi** = Alma, identidade, automação, infraestrutura, segurança operacional
- **Atena Evolução** = Motor técnico, RAG avançado, inferência otimizada, testes

**Resultado esperado:** Um sistema completo com personalidade robusta E capacidade técnica avançada.

---

## 2. O QUE CADA UM TEM

### 2.1 Koldi (46 scripts + wiki + plugins + infra)

**Identidade/Personalidade:**
- SOUL.md v4.4 com 9 teorias psicológicas
- 6 modos operacionais (Técnico, Literário, Dialético, Suporte, Protetor, Reflexivo)
- Anti-drift em 5 níveis
- Protocolo de crise identitária
- Modelo JARVIS

**Infraestrutura:**
- EPR Bridge (WebSocket TLS bidirecional Local <-> VPS)
- CRDTs (Vector Clock + LWW-Register + OR-Set)
- Cofre AES-256 (PBKDF2 600k iterações)
- 5 cron jobs automáticos
- 2 plugins (koldi-browser, koldi-computer-use)

**Segurança Operacional:**
- hardening.py (scan e correção de permissões)
- security_watchdog.py (monitoramento contínuo)
- security_scan_deep.py (varredura profunda)
- verify_integrity.py (SHA256 checksums)

**Automação/Monitoramento:**
- auto_fetch.py (coleta periódica)
- auto_update.py (atualização automática)
- net_monitor.py (monitoramento de rede)
- openrouter_key_monitor.py (créditos)
- proactive_monitor.py

**Comunicação:**
- tts_koldi.py (4 tiers de fallback)
- voz.py, fala_assistida.py
- phrase_predictor.py

**Cognição:**
- cot_engine.py, metacog_engine.py
- reflection_engine.py, operante.py
- analogia_engine.py, identity_mcp.py

**Wiki (165 páginas):**
- Memória durável do projeto
- Análises históricas
- Arquitetura evolutiva

### 2.2 Atena Evolução (51 scripts + 61 testes)

**Motor Técnico:**
- RAG avançado (HyDE, Fusion, Rerank, CRAG)
- System Prompt Hierárquico (6 camadas XML)
- Adaptive Temperature (4 perfis)
- Constitutional AI (gerar -> auto-critica -> revisar)
- Speculative Decoding
- KV-Cache Manager

**Inferência:**
- 5 camadas de fallback (Qwen -> OpenRouter -> Gemini -> Ollama -> Llama.cpp)
- GLM-5 otimizações (DSA, HISA, MISA)
- Embedding cache
- Hermes-Ollama Adapter

**Memória:**
- Pipeline com decay temporal
- Consolidação por entidades
- Token budget

**APIs/UI:**
- FastAPI REST + WebSocket
- UI Web com streaming
- Image Generator (4 providers, 8 estilos)

**Segurança:**
- SecurityGuard com 7 camadas (919 linhas)
- Sanitize input/output
- Rate limiting
- Audit log

**Testes:**
- 61 testes pytest passando

---

## 3. PLANO DE FUSÃO (5 FASES)

### FASE 1: IMPORTAÇÃO (Prioridade: CRÍTICA)
**Objetivo:** Copiar todos os 46 scripts Koldi para o projeto

Scripts a copiar para `tools/`:
- cofre.py, verify_integrity.py, win_subprocess.py
- auto_fetch.py, auto_update.py, auto_release.py
- net_monitor.py, openrouter_key_monitor.py
- env_monitor.py, proactive_monitor.py
- cli-printing-press.py, composio_helper.py
- migrate_to_cofre.py, patch_composio_config.py
- start_koldi_server.py, token_juice_cli.py
- auto_analysis.py, check_hermes_update.py
- visao_engine.py, visao_computacional.py
- browser_cdp.py
- koldi_local_agent.py, koldi_nuvem_ctl.py

Scripts a copiar para `safety/`:
- security_layer.py, security_watchdog.py
- security_scan_deep.py, hardening.py

Scripts a copiar para `core/`:
- cot_engine.py, metacog_engine.py
- reflection_engine.py, operante.py
- analogia_engine.py, identity_mcp.py
- persona_cli.py, phrase_predictor.py, phrase_predictor_v2.py
- salvar_licao.py, open_human_reflect.py

Scripts a copiar para `tools/voz/`:
- tts_koldi.py, voz.py, fala_assistida.py

Scripts a copiar para `lib/epr/`:
- crdt_sync.py, epr_watchdog.py

Scripts a copiar para `lib/memory/`:
- mem0_sync.py, memory_consolidator.py, checkpoint_sync.py

**Total: 46 scripts**

### FASE 2: INTEGRAÇÃO DE IDENTIDADE
**Objetivo:** Personalidade Koldi + Motor Atena

- Importar SOUL.md v4.4 como base
- Integrar 6 modos operacionais no core
- Adicionar anti-drift ao pipeline de inferência
- Conectar Agent Loop com sistema de memória Koldi
- Integrar Personalidade nos prompts do Atena

### FASE 3: SEGURANÇA COMPLETA
**Objetivo:** Defesa em profundidade

- SecurityGuard (Atena) + security_watchdog (Koldi)
- Cofre para todas as chaves API
- Verificação de integridade de todos os arquivos
- Hardening do ambiente Windows
- Rate limiting e audit log

### FASE 4: TESTES
**Objetivo:** Qualidade garantida

- Testes para cada script importado
- Testes de integração (cofre, segurança, rede)
- Testes de regressão
- 4 loops de validação

### FASE 5: DOCUMENTAÇÃO
**Objetivo:** Wiki completa

- Migrar páginas relevantes da wiki Koldi
- Documentar arquitetura fundida
- Criar guia de manutenção
- Atualizar index.md

---

## 4. MÉTRICAS ALVO

| Métrica | Atual (Atena) | Pós-Fusão |
|---------|---------------|-----------|
| Arquivos Python | 51 | ~97 |
| Linhas de código | 16,781 | ~30,600 |
| Testes passing | 61 | 100+ |
| Camadas de segurança | 7 | 12+ |
| Modelos suportados | 5 | 5 (mesmos) |
| Funcionalidades | RAG, Inferência, UI | + EPR, Cofre, Voz, Visão, CRDT |

---

## 5. RISCOS E MITIGAÇÃO

| Risco | Probabilidade | Mitigação |
|-------|--------------|-----------|
| Conflitos de importação | Alta | Testar cada script individualmente |
| Duplicação de funcionalidade | Média | Manter versão mais robusta |
| RAM insuficiente (15GB) | Média | Lazy loading de modelos |
| Complexidade excessiva | Baixa | Modularidade estrita |

---

## 6. ANÁLISE DE COMPATIBILIDADE

### 6.1 Tipos de Scripts

**Módulos com classes (importáveis diretamente):**
- security_watchdog.py (17 defs)
- cot_engine.py (4 classes)
- metacog_engine.py (5 classes)
- reflection_engine.py (9 classes)
- operante.py (6 classes)
- crdt_sync.py (5 classes)
- epr_watchdog.py (2 classes, lib)

**Scripts CLI-only (precisam de adaptação):**
- hardening.py, auto_fetch.py, tts_koldi.py, fala_assistida.py
- cofre.py, net_monitor.py, security_scan_deep.py, verify_integrity.py
- mem0_sync.py, memory_consolidator.py, checkpoint_sync.py

**Libs puras (funções soltas):**
- voz.py

### 6.2 Ações por Script

| Script | Tipo | Ação |
|--------|------|------|
| cofre.py | CLI | Adicionar classe wrapper ou usar via subprocess |
| tts_koldi.py | CLI | Adicionar função `falar(texto)` exportável |
| auto_fetch.py | CLI | Adicionar classe `AutoFetcher` com métodos |
| hardening.py | CLI | Adicionar função `scan()` exportável |
| security_watchdog | Classe | Importar diretamente |
| cot_engine | Classe | Importar diretamente |
| metacog_engine | Classe | Importar diretamente |
| reflection_engine | Classe | Importar diretamente |
| operante | Classe | Importar diretamente |
| crdt_sync | Classe | Importar diretamente |
| epr_watchdog | Classe | Importar diretamente |

### 6.3 Dependências Externas Necessárias

- `httpx` — já no projeto
- `numpy` — já no projeto
- `fastapi` — já no projeto
- `pydantic` — já no projeto
- `pytest` — já no projeto
- `cryptography` (Fernet) — necessária para cofre

## 7. PRÓXIMOS PASSOS IMEDIATOS

1. Instalar dependência: `pip install cryptography`
2. Copiar scripts de classes (core/, safety/, lib/epr/)
3. Adaptar scripts CLI para funções exportáveis
4. Copiar scripts de voz (tools/voz/)
5. Copiar scripts de monitoramento (tools/)
6. Rodar testes de integração
7. Commit e push

---

## Referências

- `docs/relatorio-claude-atena-evolucao.md` (408 linhas) — Análise técnica completa
- `docs/relatorio-ecossistema-koldi.md` (457 linhas) — Análise do ecossistema
- `docs/pesquisa-agent-loops-2026-06-23.md` — Pesquisa de padrões de agentes
- `core/agent_loop.py` (656 linhas) — Novo Agent Loop
- `scripts/senha_descartavel.py` (172 linhas) — Sistema de senhas descartáveis
