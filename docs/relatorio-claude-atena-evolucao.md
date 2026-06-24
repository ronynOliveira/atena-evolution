# Relatório Técnico: Projeto Atena Evolução

**Data:** 24/06/2026  
**Versão do Projeto:** 1.0.0  
**Analista:** OWL (subagent de análise técnica)  
**Repositório:** `C:/Users/dell-/AppData/Local/hermes/atena_evolution/`

---

## 1. Arquitetura Geral

### 1.1 Visão de Alto Nível

O **Atena Evolução** é um sistema de IA local com arquitetura multi-camadas, projetado para operar com inferência primariamente local (Ollama/llama.cpp) e fallback para APIs em nuvem. O projeto integra cinco grandes subsistemas:

```
┌─────────────────────────────────────────────────────────────────┐
│                    HERMES AGENT (Host)                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              ATENA BROKER v3 (ai_broker_v3.py)           │   │
│  │   Roteamento Dinâmico │ Circuit Breaker │ Fallback Chain │   │
│  └────────┬──────────────┬──────────────┬──────────────────┘   │
│           │              │              │                        │
│  ┌────────▼────┐  ┌──────▼──────┐  ┌───▼────────────────┐     │
│  │  BEHAVIOR   │  │  CORE       │  │  SAFETY GUARD      │     │
│  │  (Prompt    │  │  (Unificado)│  │  (AsFT/NeST/Const.) │     │
│  │   Engine)   │  │             │  │                     │     │
│  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘     │
│         │                │                    │                  │
│  ┌──────▼──────┐  ┌──────▼──────┐  ┌──────────▼──────────┐     │
│  │  ORCHESTRA- │  │  RAG        │  │  MEMORY PIPELINE    │     │
│  │  TOR        │  │  ENGINE     │  │  (SQLite + Decay)   │     │
│  │  (Koldi)    │  │  (Hybrid)   │  │                     │     │
│  └─────────────┘  └─────────────┘  └─────────────────────┘     │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              OLLAMA (localhost:11434)                     │   │
│  │   atena-glm5 │ qwen3:8b │ nomic-embed-text │ gemma4:e2b  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              APIS EXTERNAS (Fallback)                    │   │
│  │   OpenRouter │ Gemini Flash │ Free APIs (8 serviços)     │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 Componentes Principais

#### 1.2.1 `core/atena_evolution_core.py` — Núcleo Unificado
- **Responsabilidade:** Orquestração central, roteamento de tarefas, inicialização de subsistemas.
- **Padrão:** Facade central com inicialização sequencial (providers → RAG → safety → agents → APIs).
- **Configuração:** Dataclass `EvolutionConfig` com parâmetros para inferência, RAG, fine-tuning e APIs.
- **Estado:** Contém mocks/TODOs significativos — é mais um blueprint de arquitetura do que implementação funcional.

#### 1.2.2 `core/ai_broker_v3.py` — Roteador Dinâmico de Consciência
- **Responsabilidade:** Roteamento de inferência com cadeia de fallback de 5 camadas.
- **Pipeline de Fallback:**
  1. **Camada 0:** Qwen Local (prioritário, sem custo)
  2. **Camada 1:** OpenRouter (nuvem principal)
  3. **Camada 2:** Gemini Flash (nuvem secundária)
  4. **Camada 3:** Ollama local (modelo alternativo)
  5. **Camada 4:** Llama.cpp (fallback final)
- **Features:** Enriquecimento via APIs gratuitas, RAG opcional, safety check pós-geração, métricas de latência.

#### 1.2.3 `core/atena_behavior.py` — Sistema de Comportamento
- **Responsabilidade:** Construção de prompts e modulação comportamental.
- **Submódulos:**
  1. **HierarchicalSystemPrompt:** 6 camadas XML (Fundacional → Identidade → Segurança → Competência → Contexto → Instrução)
  2. **DynamicFewShotSelector:** Seleção de exemplos via embeddings (nomic-embed-text)
  3. **ConstitutionalAgent:** Pipeline gerar → auto-critica → revisar
  4. **AdaptiveTemperature:** Classificação heurística de tarefas com 4 perfis de temperatura
  5. **TokenSteering:** logit_bias via Ollama para controle de tokens

#### 1.2.4 `core/orchestrator.py` — Koldi Orchestrator
- **Responsabilidade:** Interface de alto nível para roteamento de tarefas.
- **Modelo:** "Koldi orquestra, Atena executa" — abstração sobre AtenaBridge.
- **Features:** Temperature mapping por tipo de tarefa, system prompts especializados, embedding cache.

#### 1.2.5 `rag/atena_rag_engine.py` — Motor RAG Avançado
- **Responsabilidade:** Recuperação e geração aumentada.
- **Pipeline RAG:**
  1. **HyDE:** Geração de documento hipotético para embedding
  2. **RAG Fusion:** Multi-query + Reciprocal Rank Fusion
  3. **Reranking:** Scoring LLM-based via gemma4:e2b
  4. **CRAG:** Avaliação de relevância com filtragem
  5. **Geração:** Resposta final com contexto
- **Chunking:** Semântico adaptativo com overlap configurável.
- **Vector Store:** Implementação in-memory (sem persistência).

#### 1.2.6 `lib/memory/pipeline.py` — Sistema de Memória
- **Responsabilidade:** API pública de memória episódica e semântica.
- **Arquitetura:** SQLite + embeddings + decay temporal.
- **Features:**
  - Memórias episódicas (eventos) e semantic (fatos consolidados)
  - Decay temporal com reforço por uso (MemoryBank)
  - Consolidação por clusterização de entidades
  - Manutenção offline (arquivamento + promoção)
  - Token budget para contexto

#### 1.2.7 `safety/safety_guard.py` — Guarda de Segurança
- **Responsabilidade:** Verificação constitucional de conteúdo.
- **Componentes:**
  - **SafetyGuard:** Regex patterns + keyword matching
  - **AsFTGuard:** Validação de atualizações ortogonais (stub)
  - **NeSTGuard:** Safety estrutural (stub)
- **Constituição:** 8 princípios de segurança

### 1.3 Modelos Utilizados

| Modelo | Função | Engine |
|--------|--------|--------|
| `atena-glm5` | Geração principal | Ollama |
| `qwen3:8b` | Inferência prioritária local | Ollama |
| `nomic-embed-text` | Embeddings | Ollama |
| `gemma4:e2b` | Reranking/avaliação | Ollama |
| `mistral-7b-instruct` | Cloud fallback | OpenRouter |
| `gemini-2.0-flash` | Cloud secundária | Google API |

---

## 2. Pontos Fortes

### 2.1 Arquitetura de Resiliência Excepcional
O sistema de **fallback em 5 camadas** do `ai_broker_v3.py` é robusto e bem projetado. A cadeia Qwen → OpenRouter → Gemini → Ollama → Llama.cpp garante disponibilidade mesmo com falhas múltiplas. O padrão de circuit breaker integrado com `health_monitor` adiciona uma camada de proteção contra degradação.

### 2.2 Sistema de Memória Sofisticado
O `lib/memory/pipeline.py` implementa um dos sistemas de memória mais avançados para um projeto local:
- **Decay temporal** com reforço por uso (MemoryBank)
- **Consolidação automática** de memórias episódicas em semânticas
- **Clusterização por entidades** para agrupamento inteligente
- **Token budget** para controle de contexto injetado

### 2.3 RAG de Alta Qualidade
O `rag/atena_rag_engine.py` implementa um pipeline RAG com técnicas de ponta:
- **HyDE** para melhor recuperação semântica
- **RAG Fusion** com multi-query e RRF
- **CRAG** para auto-correção de relevância
- **Chunking semântico adaptativo** (não apenas divisão por tamanho)

### 2.4 System Prompt Hierárquico
O `HierarchicalSystemPrompt` com 6 camadas XML-like é uma abordagem elegante que separa preocupações (fundacional, identidade, segurança, competência, contexto, instrução) e permite atualização seletiva de camadas mutáveis.

### 2.5 Controle de Temperatura Adaptativo
O `AdaptiveTemperature` com 4 perfis (criativo, técnico, factual, analítico) e classificação heurística permite otimizar a geração sem intervenção manual, ajustando parâmetros de amostragem ao tipo de tarefa.

### 2.6 Operação Local com Custo Zero
A prioridade por inferência local (Qwen 3:8b como camada 0) com fallback para APIs gratuitas (Wikipedia, arXiv, DuckDuckGo) permite operação cotidiana sem custos de API.

### 2.7 Modularidade e Separação de Responsabilidades
Cada arquivo tem responsabilidade bem definida. A separação core/rag/lib/safety permite evolução independente dos subsistemas.

### 2.8 Testes Unitários Embutidos
O `atena_behavior.py` inclui um suite de testes completo (>100 assertions) que valida todos os submódulos, facilitando regressão.

---

## 3. Pontos Fracos

### 3.1 Alto Número de TODOs e Stubs
O `atena_evolution_core.py` é essencialmente um **blueprint** — os métodos `_execute_direct`, `_execute_with_rag`, `_execute_with_agent`, `_safety_check` são todos stubs com `return f"[Atena Evolução] Processando: ..."`. O núcleo não é funcional sem os componentes que o envolvem.

### 3.2 Vector Store In-Memory Sem Persistência
O `VectorStore` em `atena_rag_engine.py` é puramente em memória. Todos os embeddings são perdidos a cada reinicialização. Para um sistema sério, isso é inaceitável — deveria usar ChromaDB, FAISS, ou persistência em SQLite.

### 3.3 TokenSteering com Hash Determinístico
O `TokenSteering._token_to_ids()` usa `hashlib.md5` como fallback para mapear tokens para IDs. Isso é tecnicamente incorreto — colisões de hash podem causar steering em tokens errados. O código admite: *"Em produção, usar tiktoken ou o tokenizador do modelo."*

### 3.4 Safety Guard Baseado em Regex
O `SafetyGuard` usa apenas 3 padrões regex e uma lista de 4 keywords perigosas. Isso é extremamente limitado:
- Falsos positivos: "como hackear" em contexto educacional seria bloqueado
- Falsos negativos: técnicas de jailbreak não detectadas
- Sem análise semântica real (o código admite: *"em produção, usar LLM para análise semântica"*)

### 3.5 AsFT e NeST São Stubs
Tanto `AsFTGuard` quanto `NeSTGuard` são implementações vazias:
- `AsFTGuard.validate_update()` sempre retorna `True`
- `NeSTGuard.is_safe()` sempre retorna `True`
- Nenhum dos dois tem lógica real de validação

### 3.6 Ausência de requirements.txt
O projeto não possui arquivo de dependências (`requirements.txt`, `pyproject.toml`, `setup.py`). Isso dificulta reprodução e deploy.

### 3.7 Dependência de Múltiplos Modelos Ollama Simultâneos
O sistema requer 4+ modelos carregados simultaneamente no Ollama (atena-glm5, qwen3:8b, nomic-embed-text, gemma4:e2b). Para o hardware alvo (i5-1235U, 15.7GB RAM), isso é problemático — modelos Q4_K_M de 8b consomem ~5-6GB cada em RAM/VRAM.

### 3.8 Concorrência e Bloqueio
O `DynamicFewShotSelector.index_all()` faz chamadas sequenciais à API de embeddings do Ollama. Para documentos grandes, isso é um gargalo significativo sem paralelização.

### 3.9 Sem Tratamento de Timeout Robusto
Vários pontos do código usam `urlopen` síncrono (em `atena_behavior.py`) dentro de contextos que deveriam ser assíncronos. O `orchestrator.py` faz chamadas síncronas ao Ollama sem timeout configurável.

### 3.10 Mistura de Estilos de Código
- `ai_broker_v3.py` usa `httpx.AsyncClient` (assíncrono)
- `atena_behavior.py` usa `urllib.request.urlopen` (síncrono)
- `atena_rag_engine.py` usa `urllib.request.urlopen` (síncrono)
- Isso cria inconsistência e potencial para event loop blocks

---

## 4. Dependências

### 4.1 Diretas (identificadas no código)

| Dependência | Versão | Uso | Arquivo |
|-------------|--------|-----|---------|
| `httpx` | não especificada | Client HTTP assíncrono | ai_broker_v3.py |
| `google-generativeai` | não especificada | Gemini Flash API | ai_broker_v3.py |
| `ollama` (serviço) | localhost:11434 | Inferência local | todos os módulos |
| `sqlite3` | stdlib | Persistência de memória | lib/memory/store.py |

### 4.2 Implícitas / Recomendadas

| Dependência | Motivo |
|-------------|--------|
| `chromadb` ou `faiss-cpu` | Substituto para VectorStore persistente |
| `tiktoken` | Tokenização correta para logit_bias |
| `numpy` | Operações vetoriais mais eficientes que Python puro |
| `pydantic` | Validação de configuração |
| `pytest` | Testes (já há arquivos test_*.py) |
| `aiohttp` ou `httpx` | Substituir urllib síncrono |

### 4.3 Serviços Externos

| Serviço | Tipo | Arquivo | Observação |
|---------|------|---------|------------|
| OpenRouter | API paga | ai_broker_v3.py | Fallback cloud |
| Google Generative AI | API paga | ai_broker_v3.py | Fallback cloud |
| OpenWeatherMap | API gratuita | atena_evolution_core.py | Requer API key |
| NewsAPI | API gratuita | atena_evolution_core.py | Requer API key |
| Wikipedia | API aberta | ai_broker_v3.py | Sem auth |
| arXiv | API aberta | ai_broker_v3.py | Sem auth |
| DuckDuckGo | API aberta | atena_evolution_core.py | Sem auth |
| GitHub API | API aberta | atena_evolution_core.py | Rate limit |

### 4.4 Hardware Requerido

| Recurso | Mínimo | Recomendado |
|---------|--------|-------------|
| RAM | 16GB | 32GB |
| VRAM (GPU) | 8GB (1 modelo Q4) | 16GB+ (2-3 modelos) |
| Disco | 20GB (modelos) | 50GB+ (com RAG) |
| CPU | 4 cores | 8+ cores (i5-1235U é mínimo) |

---

## 5. Riscos de Segurança

### 5.1 CRÍTICO: Safety Guard Ineficaz

**Descrição:** O `SafetyGuard` atual é puramente baseado em regex (3 padrões) e keyword matching (4 palavras-chave).  
**Impacto:** Qualquer conteúdo prejudicial que não corresponda exatamente aos padrões será aprovado.  
**Cenários de falha:**
- Prompt injection pode burlar regex facilmente
- Conteúdo prejudicial em português com gírias não é capturado
- Contextos educacionais ("como funciona um exploit") são falsos positivos
- O `_check_constitution()` é explicitamente marcado como "implementação simplificada"

**Mitigação recomendada:**
- Usar um LLM para análise semântica (self-check com modelo menor)
- Implementar classificação de toxicidade com modelos especializados
- Adicionar camada de output filtering com classificação de risco

### 5.2 CRÍTICO: AsFT e NeST Não Implementados

**Descrição:** Os guards `AsFTGuard` e `NeSTGuard` são stubs que sempre retornam `True`/`pass`.  
**Impacto:** Atualizações de modelo ou prompts adversariais não são validados.  
**Risco:** Fine-tuning malicioso ou prompt injection pode alterar comportamento sem detecção.

### 5.3 ALTO: Exposição de Chaves de API

**Descrição:** O código tenta obter API keys de `app.atena_vault` mas cai silenciosamente para variáveis de ambiente.  
**Risco:** Se `atena_vault` não estiver configurado, o sistema pode operar sem autenticação em APIs rate-limited.  
**Arquivo:** `ai_broker_v3.py:77-86`

### 5.4 ALTO: Sem Sanitização de Input do Usuário

**Descrição:** O `prompt` do usuário é passado diretamente para o Ollama sem sanitização.  
**Risco:** Prompt injection pode alterar comportamento do modelo, especialmente com modelos menores (phi-3.8b) que têm menor robustez a adversarial inputs.

### 5.5 MÉDIO: TokenSteering com MD5 Hash

**Descrição:** O `TokenSteering._token_to_ids()` usa `md5(token) % 100_000` como ID de token.  
**Risco:** Colisões de hash podem banir/impulsionar tokens incorretos. Além disso, o range 0-100.000 pode não corresponder ao vocabulário real do modelo.

### 5.6 MÉDIO: Sem Rate Limiting para APIs Externas

**Descrição:** As chamadas a OpenRouter, Wikipedia, arXiv etc. não têm rate limiting.  
**Risco:** Loop infinito ou bug pode esgotar quotas de API ou causar throttling.

### 5.7 MÉDIO: Sem Autenticação no Sistema

**Descrição:** Não há sistema de autenticação ou autorização para quem pode interagir com o Atena.  
**Risco:** Se exposto em rede local, qualquer dispositivo pode enviar comandos.

### 5.8 BAIXO: Dados Sensíveis em Logs

**Descrição:** O `SafetyGuard` registra `content_preview: content[:50]` em violações.  
**Risco:** Informações potencialmente sensíveis podem aparecer em logs.

---

## 6. Oportunidades de Melhoria

### 6.1 Curto Prazo (1-2 semanas)

1. **Persistência do Vector Store**
   - Substituir `VectorStore` in-memory por ChromaDB ou FAISS com persistência em disco
   - Benefício: RAG funcional entre reinicializações

2. **Consolidar requirements.txt**
   - Listar todas as dependências com versões fixas
   - Adicionar `pyproject.toml` com metadata do projeto

3. **Padronizar Assincronia**
   - Migrar `atena_behavior.py` e `atena_rag_engine.py` para `httpx.AsyncClient`
   - Eliminar `urllib.request.urlopen` síncrono

4. **Expandir Safety Guard**
   - Adicionar mais padrões regex (incluindo variações em português)
   - Implementar camada de análise semântica com modelo local pequeno
   - Adicionar logging estruturado de violações

5. **Implementar TokenSteering Correto**
   - Usar `tiktoken` ou API de tokenização do Ollama
   - Remover fallback MD5

### 6.2 Médio Prazo (1-2 meses)

6. **Implementar AsFT Real**
   - Calcular direção de alinhamento a partir de embeddings de respostas seguras/inseguras
   - Validar atualizações de modelo contra essa direção

7. **Sistema de Plugins**
   - Criar arquitetura de plugins para agentes especializados
   - Permitir extensão sem modificação do core

8. **Cache de Respostas**
   - Implementar cache semântico de respostas (similaridade > 0.95 → retorna cached)
   - Reduzir latência para queries repetitivas

9. **Paralelização do RAG**
   - Embeddings em batch com `asyncio.gather`
   - Reranking paralelo de chunks

10. **Dashboard de Métricas**
    - Interface web para monitorar uso, latência, violações de segurança
    - Exportar métricas para Prometheus/Grafana

### 6.3 Longo Prazo (3-6 meses)

11. **Treinamento Real do AsFT/NeST**
    - Implementar fine-tuning com QLoRA para segurança
    - Usar `atena_training.jsonl` existente como base

12. **Suporte a Multi-Usuários**
    - Isolamento de memória por usuário
    - Autenticação via OAuth2 local

13. **RAG com Grafos de Conhecimento**
    - Integrar LightRAG/GraphRAG conforme especificado na config
    - Extração automática de entidades e relações

14. **Otimização de Hardware**
    - Quantização dinâmica baseada em disponibilidade de RAM
    - GPU offloading seletivo para camadas críticas
    - Speculative decoding real (não apenas flag)

15. **Testes de Integração**
    - Suite de testes end-to-end com Ollama mockado
    - CI/CD pipeline com GitHub Actions

16. **Documentação de API**
    - OpenAPI spec para endpoints REST
    - Tutoriais de extensão e personalização

---

## 7. Métricas do Projeto

| Métrica | Valor |
|---------|-------|
| Arquivos Python | ~50 |
| Tamanho total | ~7.2 MB |
| Linhas de código (estimada) | ~8.000-10.000 |
| Modelos Ollama requeridos | 4+ |
| APIs externas integradas | 8 |
| Camadas de fallback | 5 |
| Princípios constitucionais | 8 |
| Perfis de temperatura | 4 |
| Camadas de system prompt | 6 |
| Cobertura de testes | Parcial (behavior apenas) |

---

## 8. Conclusão

O **Atena Evolução** é um projeto arquiteturalmente ambicioso e bem concebido, com design de resiliência excepcional e separação de responsabilidades clara. A visão de um sistema de IA local com múltiplas camadas de fallback, RAG avançado, memória de longo prazo e segurança constitucional é tecnicamente sólida.

No entanto, o estado atual é de **desenvolvimento inicial/protótipo** — o núcleo é em grande parte stub, o safety guard é ineficaz, e o RAG não tem persistência. O projeto tem uma fundação arquitetural forte que pode suportar evolução significativa, mas requer implementação substancial dos componentes marcados como TODO para se tornar funcional em produção.

**Recomendação:** Priorizar (1) persistência do Vector Store, (2) implementação real do Safety Guard com análise semântica, e (3) padronização da camada assíncrona antes de qualquer deploy.

---

*Relatório gerado automaticamente em 24/06/2026*
