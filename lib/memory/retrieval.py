"""
retrieval.py — Recuperação híbrida, sem chamadas de LLM no caminho de leitura.

Este é o ponto que resolve seu requisito 4 (não consumir o contexto
inteiro, funcionar com modelos pequenos): a busca é pura matemática
vetorial + SQL. O modelo de 3.8B só "pensa" durante a consolidação
offline (consolidation.py), nunca durante uma resposta em tempo real.

Score final = combinação ponderada de:
  - similaridade semântica (cosseno embedding da query vs memória)
  - retenção temporal (curva de Ebbinghaus — memórias "vivas" pesam mais)
  - sobreposição de entidades/tags (boost direto se tópico bate)

Zero dependências externas (sem numpy) — roda em qualquer Python 3.11.
"""

import json
import math
import time
from dataclasses import dataclass, field

from decay import retention


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Similaridade de cosseno entre dois vetores de mesma dimensão."""
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def entity_overlap(query_entities: set, memory_entities: set) -> float:
    """Jaccard-like overlap entre conjuntos de entidades."""
    if not query_entities or not memory_entities:
        return 0.0
    return len(query_entities & memory_entities) / len(query_entities | memory_entities)


@dataclass
class ScoredMemory:
    id: int
    content: str
    tier: str  # "episodic" | "semantic"
    score: float
    similarity: float
    retention_score: float
    row: dict = field(default_factory=dict)  # linha original do banco


def score_rows(
    rows: list,
    query_embedding: list[float],
    query_entities: set,
    tier: str,
    weights: tuple[float, float, float] = (0.55, 0.30, 0.15),
) -> list[ScoredMemory]:
    """
    weights = (peso_similaridade, peso_retencao, peso_entidades)
    Pesos default favorecem relevância semântica sobre recência —
    ajuste se quiser um agente mais "no presente" vs mais "factual".
    """
    w_sim, w_ret, w_ent = weights
    now = time.time()
    scored: list[ScoredMemory] = []

    for row in rows:
        emb = json.loads(row["embedding"])
        sim = cosine_similarity(query_embedding, emb)

        days_since = (now - row["last_accessed_at"]) / 86400.0
        ret = retention(days_since, row["strength"])

        mem_entities = set(json.loads(row["entities"]))
        ent_score = entity_overlap(query_entities, mem_entities)

        final = (w_sim * sim) + (w_ret * ret) + (w_ent * ent_score)

        content_field = "fact" if tier == "semantic" else "content"
        scored.append(ScoredMemory(
            id=row["id"],
            content=row[content_field],
            tier=tier,
            score=final,
            similarity=sim,
            retention_score=ret,
            row=dict(row),
        ))

    return scored


def retrieve_top_k(
    episodic_rows: list,
    semantic_rows: list,
    query_embedding: list[float],
    query_entities: set,
    k: int = 5,
    token_budget: int = 400,
    chars_per_token: float = 4.0,
) -> list[ScoredMemory]:
    """
    Combina episódico + semântico num único ranking, mas respeita um
    orçamento de tokens — essencial para não estourar o contexto de
    um modelo 3.8B com num_ctx=4096.
    """
    all_scored = (
        score_rows(episodic_rows, query_embedding, query_entities, "episodic")
        + score_rows(semantic_rows, query_embedding, query_entities, "semantic")
    )
    all_scored.sort(key=lambda m: m.score, reverse=True)

    selected: list[ScoredMemory] = []
    budget_chars = token_budget * chars_per_token
    used_chars = 0

    for mem in all_scored:
        cost = len(mem.content)
        # Só pula se já tiver algo selecionado E o custo estourar o orçamento
        if selected and used_chars + cost > budget_chars:
            break
        selected.append(mem)
        used_chars += cost
        if len(selected) >= k:
            break

    return selected
