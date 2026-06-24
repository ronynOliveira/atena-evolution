# ATENA EVOLUÇÃO — Projeto Consolidado

**Versão:** 2.0.0 (Fusão Koldi + Atena)
**Data:** 2026-06-24
**Repositório:** https://github.com/ronynOliveira/atena-evolution

---

## 1. VISÃO GESTO

O Atena Evolução é um sistema de IA local que funde dois mundos:

- **Koldi** (Alma): Identidade, personalidade, automação, segurança operacional
- **Atena** (Motor): RAG avançado, inferência otimizada, testes, modularidade

**Resultado:** Um assistente técnico com personalidade robusta, seguro, e 100% local.

---

## 2. NÚMEROS FINAIS

| Métrica | Antes (Atena) | Depois (Fusão) |
|---------|---------------|----------------|
| Arquivos Python | 51 | **96** |
| Linhas de código | 16,781 | **30,706** |
| Testes passando | 61 | **89** |
| Módulos de segurança | 1 | **11** |
| Modelos suportados | 5 | **5** |
| Funcionalidades | RAG, Inferência, UI | + EPR, Cofre, Voz, Visão, CRDT, Auto-fetch |

---

## 3. ESTRUTURA DO PROJETO

```
atena_evolution/
├── core/                    # Núcleo do agente
│   ├── identity.py          # Motor de identidade (Koldi)
│   ├── agent_loop.py        # Agent Loop (perceive-think-act)
│   ├── atena_evolution_core.py
│   ├── ai_broker_v3.py      # Roteamento multi-camadas
│   ├── atena_behavior.py   # System prompt hierárquico
│   ├── atena_bridge.py      # Ponte com AtenaRPAAgent
│   ├── atena_api.py         # API REST
│   ├── orchestrator.py      # Orquestrador Koldi-Atena
│   ├── security_guard.py     # 7 camadas de segurança
│   ├── cot_engine.py        # Chain-of-Thought
│   ├── metacog_engine.py    # Metacognição
│   ├── reflection_engine.py # Reflexão sobre erros
│   ├── operante.py          # Aprendizado operante
│   ├── analogia_engine.py   # Motor de analogias
│   ├── identity_mcp.py      # MCP de identidade
│   ├── persona_cli.py       # CLI de persona
│   ├── phrase_predictor.py  # Previsão de frases
│   ├── salvar_licao.py      # Persistência de aprendizados
│   └── open_human_reflect.py
│
├── safety/                  # Segurança
│   ├── security_manager.py  # Central integrada (310 linhas)
│   ├── security_layer.py    # Input/Output validation
│   ├── security_watchdog.py # Monitoramento contínuo
│   ├── security_scan_deep.py # Varredura profunda
│   ├── hardening.py         # Correção de permissões
│   └── verify_integrity.py  # SHA256 checksums
│
├── rag/                     # Recuperação aumentada
│   ├── atena_rag_engine.py  # RAG híbrido (HyDE, Fusion, CRAG)
│   └── rag_engine.py        # Motor RAG base
│
├── inference/               # Otimização de inferência
│   ├── atena_inference_advanced.py
│   ├── glm5_optimizations.py # DSA, HISA, MISA
│   ├── inference_optimizer.py
│   ├── llm_inference_opt.py
│   └── qwen_inference.py
│
├── lib/                     # Bibliotecas
│   ├── memory/              # Sistema de memória
│   │   ├── pipeline.py      # Pipeline com decay
│   │   ├── store.py         # MemoryStore
│   │   ├── retrieval.py     # Recuperação
│   │   ├── decay.py         # Decay temporal
│   │   ├── consolidation.py # Consolidação
│   │   ├── bridge.py        # Ponte
│   │   ├── memory_consolidator.py
│   │   └── checkpoint_sync.py
│   └── epr/                 # Sincronização
│       ├── crdt_sync.py     # CRDTs
│       ├── epr_watchdog.py  # Watchdog EPR
│       └── mem0_sync.py     # Sincronização Mem0
│
├── apis/                    # APIs externas
│   ├── free_apis.py         # APIs gratuitas
│   └── image_generator.py   # Gerador de imagens
│
├── tools/                   # Ferramentas
│   ├── auto_fetch.py        # Coleta periódica
│   ├── auto_update.py       # Atualização automática
│   ├── auto_release.py      # Release automático
│   ├── auto_analysis.py     # Análise automática
│   ├── check_hermes_update.py
│   ├── cli-printing-press.py
│   ├── composio_helper.py
│   ├── env_monitor.py
│   ├── migrate_to_cofre.py
│   ├── net_monitor.py
│   ├── openrouter_key_monitor.py
│   ├── patch_composio_config.py
│   ├── proactive_monitor.py
│   ├── start_koldi_server.py
│   ├── token_juice_cli.py
│   ├── visao_computacional.py
│   ├── visao_engine.py
│   ├── browser_cdp.py
│   ├── koldi_local_agent.py
│   ├── koldi_nuvem_ctl.py
│   └── voz/                 # Ferramentas de voz
│       ├── tts_koldi.py
│       ├── voz.py
│       └── fala_assistida.py
│
├── web/                     # Interface web
│   ├── index.html           # UI com streaming
│   └── style.css            # Dark mode premium
│
├── agents/                  # Agentes
│   └── (agentes especializados)
│
├── tests/                   # Testes
│   ├── test_atena_memory.py      # 61 testes
│   ├── test_identity.py          # 21 testes
│   ├── test_security.py          # 7 testes
│   ├── test_atena_optimizations.py
│   ├── test_atena_validacao.py
│   ├── test_comprehensive.py
│   ├── test_loop1.py
│   ├── test_pipeline_rapido.py
│   ├── test_pipeline_unificado.py
│   └── test_ui_validacao.py
│
└── docs/                    # Documentação
    ├── PLANO-FUSAO-ATENA-KOLDI.md
    ├── relatorio-claude-atena-evolucao.md
    ├── relatorio-ecossistema-koldi.md
    ├── pesquisa-agent-loops-2026-06-23.md
    └── memory-tdd-plan.md
```

---

## 4. FUNCIONALIDADES

### 4.1 Motor Técnico (Atena)
- **RAG Híbrido:** HyDE + RAG Fusion + Reranking + CRAG
- **Inferência:** 5 camadas de fallback (Qwen → OpenRouter → Gemini → Ollama → Llama.cpp)
- **GLM-5:** DSA, HISA, MISA, KV-Cache
- **System Prompt Hierárquico:** 6 camadas XML
- **Constitutional AI:** Gerar → Auto-crítica → Revisar
- **Adaptive Temperature:** 4 perfis por tipo de tarefa
- **Speculative Decoding** + **KV-Cache Manager**

### 4.2 Identidade (Koldi)
- **6 Modos Operacionais:** Técnico, Literário, Dialético, Suporte, Protetor, Reflexivo
- **Valores Hierarquizados:** 3 camadas (Pétrea, Nuclear, Adaptativa)
- **Anti-Drift:** 5 níveis de verificação
- **Protocolo de Crise:** 4 níveis
- **Perfil do Usuário:** Senhor Robério, 34, escritor, Diadema/SP

### 4.3 Segurança (Fusão)
- **SecurityGuard (Atena):** 7 camadas, sanitização, rate limiting, audit log
- **SecurityWatchdog (Koldi):** Monitoramento contínuo de integridade
- **Hardening:** Scan e correção de permissões
- **Deep Scanner:** Varredura profunda de credenciais
- **Input/Output Validation:** Sanitização e filtro de conteúdo
- **Integrity Checker:** SHA256 de arquivos sensíveis

### 4.4 Automação (Koldi)
- **Auto-Fetch:** Coleta periódica (GitHub, wiki, RAM, Ollama)
- **Auto-Update:** Verificação e aplicação de updates
- **Net Monitor:** Monitoramento de rede
- **OpenRouter Monitor:** Créditos e alertas
- **Proactive Monitor:** Monitoramento proativo

### 4.5 Comunicação (Koldi)
- **TTS (4 tiers):** SAPI5 → edge-tts CLI → edge-tts direct → VBScript
- **Fala Assistida:** Para distonia
- **Phrase Predictor:** Previsão de frases

### 4.6 Visão (Koldi)
- **EasyOCR:** OCR PT/EN em CPU
- **BLIP:** Image captioning
- **YOLOv8:** Detecção de objetos
- **Browser CDP:** Controle de navegador

---

## 5. SEGURANÇA

### 5.1 Arquivos Protegidos
| Arquivo | Permissões | Proprietário |
|---------|-----------|--------------|
| `.env` | SYSTEM + dell- | Restrito |
| `config.yaml` | SYSTEM + dell- | Restrito |
| `vault.enc` | SYSTEM + dell- | Restrito |
| `vault.salt` | SYSTEM + dell- | Restrito |

### 5.2 Cofre (AES-256)
- **Algoritmo:** Fernet (AES-256-CBC)
- **Derivação:** PBKDF2HMAC SHA-256, 600k iterações
- **Localização:** `~/AppData/Local/hermes/cofre/`
- **Chaves armazenadas:** OPENROUTER_API_KEY, GOOGLE_API_KEY, OPENAI_API_KEY, GITHUB_TOKEN_WRITE, EPR_SECRET

### 5.3 Senhas Descartáveis
- Sistema de uso único com TTL
- Armazenado no cofre criptografado
- Queimadas automaticamente após uso ou expiração

---

## 6. COMO USAR

### 6.1 Instalação
```bash
git clone https://github.com/ronynOliveira/atena-evolution.git
cd atena_evolution
pip install -r requirements.txt
```

### 6.2 Executar Testes
```bash
python -m pytest tests/ -q
```

### 6.3 Executar Agent Loop
```bash
python -c "from core.agent_loop import AgentLoop; AgentLoop().run()"
```

### 6.4 Verificar Segurança
```bash
python -c "from safety.security_manager import get_security_manager; print(get_security_manager().get_security_report())"
```

### 6.5 Verificar Identidade
```bash
python -c "from core.identity import get_identity; i=get_identity(); print(i.build_full_system_addition())"
```

---

## 7. PRÓXIMOS PASSOS (Roadmap)

- [ ] Adicionar requirements.txt
- [ ] CI/CD pipeline (GitHub Actions)
- [ ] Testes de integração completos (com Ollama)
- [ ] Documentação da API REST
- [ ] Docker Compose para deploy
- [ ] Migração completa da wiki Koldi
- [ ] Fine-tuning com contos do Senhor Robério

---

## 8. CRÉDITOS

- **Koldi:** Personalidade, identidade, automação, segurança operacional
- **Atena Evolução:** Motor técnico, RAG, inferência, testes
- **Senhor Robério:** Direção, visão, contos para treinamento

---

## Referências

- `docs/PLANO-FUSAO-ATENA-KOLDI.md` — Plano completo de fusão
- `docs/relatorio-claude-atena-evolucao.md` — Análise técnica (408 linhas)
- `docs/relatorio-ecossistema-koldi.md` — Análise do ecossistema (457 linhas)
- `docs/pesquisa-agent-loops-2026-06-23.md` — Pesquisa de padrões
