# Atena Evolução v1.0

Sistema de IA cognitiva avançada que une o Projeto Atena com o Koldi Fusion.

## Arquitetura

```
atena_evolution/
├── atena_evolution_app.py    ← Aplicação principal
├── core/
│   ├── atena_evolution_core.py  ← Núcleo unificado
│   ├── ai_broker_v3.py          ← Broker de inferência v3
│   ├── atena_api.py             ← API REST + WebSocket
│   └── index.html               ← Frontend web
├── rag/
│   └── rag_engine.py            ← RAG avançado (hybrid + rerank + CRAG)
├── inference/
│   └── inference_optimizer.py   ← Otimização de inferência
├── safety/
│   └── safety_guard.py          ← Segurança constitucional
└── apis/
    └── free_apis.py             ← APIs gratuitas
```

## Instalação

```bash
pip install fastapi uvicorn httpx sentence-transformers chromadb
```

## Uso

```bash
# Iniciar servidor
python atena_evolution_app.py

# Acessar interface web
# http://localhost:8000/

# API docs
# http://localhost:8000/docs
```

## Endpoints

- `POST /api/chat` — Chat com Atena
- `POST /api/rag` — Query RAG
- `GET /api/status` — Status do sistema
- `WS /ws` — WebSocket para chat em tempo real

## Módulos

### Core
- `AtenaEvolutionCore` — Núcleo unificado com roteamento inteligente
- `AtenaAIBroker v3` — Broker de inferência com 4 camadas + circuit breaker

### RAG
- Hybrid search (BM25 + Dense + RRF)
- Reranking com cross-encoders
- CRAG (Corrective RAG)
- Chunking semântico e recursivo

### Inferência
- Quantização GGUF Q4_K_M
- Self-speculative decoding (QuantSpec/Vegas)
- KV-cache compression (q4_0/q8_0)
- Flash Attention

### Safety
- SafetyGuard (8 princípios constitucionais)
- AsFT Guard (alignment-safe)
- NeST Guard (structure-aware)

### APIs Gratuitas
- Wikipedia, arXiv, DuckDuckGo, GitHub
- wttr.in (clima), Dictionary, Quotable

## Licença

Projeto pessoal do Senhor Robério.
