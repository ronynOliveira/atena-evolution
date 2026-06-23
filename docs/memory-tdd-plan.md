# Plano: Implementar Sistema de Memória da Atena (TDD)

**Data:** 18/06/2026
**Contexto:** O teste `tests/test_atena_memory.py` já existe e define a interface completa. Precisamos implementar os módulos faltantes para fazer os testes passarem.

## Módulos a Implementar

### 1. `store.py` — MemoryStore
Classe que gerencia armazenamento SQLite com duas tabelas:
- `episodic_memory`: memórias individuais (texto, embedding, strength, last_accessed_at, session_id, importance, archived)
- `semantic_memory`: fatos consolidados (fact, source_ids, created_at)

Métodos necessários:
- `add_episodic(text, embedding, session_id, importance) -> id`
- `add_semantic(fact, source_ids) -> id`
- `all_episodic(include_archived=True) -> list[dict]`
- `all_semantic() -> list[dict]`
- `update_strength(episodic_id, new_strength)`
- `touch(episodic_id)` — atualiza last_accessed_at
- `archive(episodic_id)`
- `search_episodic(query_embedding, top_k, threshold) -> list[dict]`
- `_conn()` — context manager para SQLite

### 2. `decay.py` — Funções de Decay
- `retention(time_delta, strength) -> float`: calcula retenção baseada no tempo e força
- `reinforce(current_strength, boost) -> float`: aumenta a força
- `should_archive(strength, threshold) -> bool`: decide se deve arquivar

### 3. `retrieval.py` — Recuperação
- `cosine_similarity(a, b) -> float`: similaridade cosseno entre dois vetores
- `retrieve_top_k(query_embedding, candidates, k) -> list[dict]`: retorna top-k por similaridade

### 4. `consolidation.py` — Consolidação
- `extract_entities(text) -> list[str]`: extrai nomes próprios e termos de domínio
- `cluster_by_overlap(episodic_memories, min_overlap) -> list[list]`: agrupa memórias por overlap de palavras
- `_suppress_sentence_initial_capitals(words) -> list[str]`: remove capitalização inicial de frase

### 5. `pipeline.py` — AtenaMemory (orquestrador)
Classe principal que coordena tudo:
- `__init__(db_path, bridge)`: inicializa store e bridge
- `remember(text, session_id, importance) -> id`: armazena memória
- `recall(query, top_k) -> str`: recupera memórias relevantes e retorna contexto formatado
- `run_maintenance(decay_threshold, min_cluster_size) -> dict`: executa decay + arquivamento + consolidação
- `heuristic_importance(text) -> float`: heurística de importância baseada em marcadores pessoais

## Dependências
- Python 3.11 padrão (sqlite3, hashlib, math, json, time, re)
- pytest para testes
- Sem dependências externas

## Testes
Rodar: `pytest tests/test_atena_memory.py -v`

## Critérios de Sucesso
- Todos os 15 testes passando
- Código limpo e documentado
- Type hints em todas as funções
- Docstrings em todos os módulos
