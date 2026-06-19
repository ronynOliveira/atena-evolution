"""
pipeline.py — API pública. Isto é o que você importa no resto do Atena.

Uso típico:

    from atena_memory.pipeline import AtenaMemory

    mem = AtenaMemory(db_path="atena_memory.db")
    mem.remember("Robério mencionou que tem distonia generalizada.", session_id="seg")
    mem.remember("Robério se descreveu como escritor e técnico em informática.", session_id="qua")

    contexto = mem.recall("Quem é o usuário?")
    # contexto já vem formatado e dentro do orçamento de tokens,
    # pronto para ser injetado no prompt do atena-glm5.

    mem.run_maintenance()  # rodar 1x por dia (cron/task scheduler), não a cada turno
"""

import json
import time
from functools import lru_cache

from store import MemoryStore
from bridge import AtenaBridge
from decay import retention, reinforce, importance_adjusted_strength, should_archive
from retrieval import retrieve_top_k
from consolidation import extract_entities, cluster_by_overlap, consolidate_cluster


def heuristic_importance(text: str) -> float:
    """
    Heurística barata de importância (0 a 1), sem chamar o LLM.
    Sinais: tamanho do conteúdo + presença de marcadores pessoais/decisórios.
    Ajuste os marcadores ao seu vocabulário real — esses refletem o que
    você descreveu nas suas memórias/perfil (saúde, identidade, projeto).
    """
    markers = [
        "distonia", "dor", "fadiga", "ansiedade", "atena", "ttp",
        "decidi", "preciso", "importante", "sempre", "nunca", "projeto",
    ]
    lowered = text.lower()
    score = 0.3  # piso
    score += min(len(text) / 500, 0.3)  # textos mais longos tendem a carregar mais contexto
    hits = sum(1 for m in markers if m in lowered)
    score += min(hits * 0.1, 0.4)
    return min(score, 1.0)


class AtenaMemory:
    """
    API pública do sistema de memória da Atena.

    Attributes:
        store: MemoryStore — camada de persistência SQLite
        bridge: AtenaBridge — interface com Ollama (embed + chat)
    """

    def __init__(self, db_path: str = "atena_memory.db", bridge: AtenaBridge = None):
        self.store = MemoryStore(db_path)
        self.bridge = bridge or AtenaBridge()

    # ---------- caminho de escrita (online, barato) ----------

    def remember(self, content: str, session_id: str = None, importance: float = None) -> int:
        """
        Armazena uma memória episódica.

        Args:
            content: texto da memória
            session_id: identificador de sessão (opcional)
            importance: importância manual (0-1). Se None, calculada heuristicamente.

        Returns:
            ID da memória inserida.
        """
        embedding = self.bridge.embed(content)
        entities = extract_entities(content)
        imp = importance if importance is not None else heuristic_importance(content)
        return self.store.add_episodic(
            content=content,
            embedding=embedding,
            entities=entities,
            importance=imp,
            session_id=session_id,
        )

    # ---------- caminho de leitura (online, barato — sem LLM) ----------

    def recall(self, query: str, k: int = 5, token_budget: int = 400) -> str:
        """
        Recupera memórias relevantes e retorna contexto formatado.

        Args:
            query: texto de busca
            k: número máximo de memórias a retornar
            token_budget: orçamento de tokens (controla tamanho do contexto)

        Returns:
            String formatada com memórias relevantes, pronta para injetar no prompt.
        """
        query_embedding = self.bridge.embed(query)
        query_entities = set(extract_entities(query))

        episodic_rows = self.store.all_episodic(include_archived=False)
        semantic_rows = self.store.all_semantic(include_superseded=False)

        results = retrieve_top_k(
            episodic_rows, semantic_rows, query_embedding, query_entities,
            k=k, token_budget=token_budget,
        )

        # Recall reforça a memória (MemoryBank: usar = lembrar melhor no futuro)
        for r in results:
            new_strength = reinforce(r.row["strength"])
            if r.tier == "episodic":
                self.store.reinforce_episodic(r.id, new_strength)
            else:
                self.store.reinforce_semantic(r.id, new_strength)

        return self._format_context(results)

    def _format_context(self, results) -> str:
        """Formata resultados de recall como bloco de contexto para o prompt."""
        if not results:
            return ""
        lines = ["[Memória relevante]"]
        for r in results:
            tag = "fato consolidado" if r.tier == "semantic" else "lembrança"
            lines.append(f"- ({tag}) {r.content}")
        return "\n".join(lines)

    # ---------- manutenção (offline, roda 1x/dia, NÃO a cada turno) ----------

    def run_maintenance(self, decay_threshold: float = 0.05, min_cluster_size: int = 2) -> dict:
        """
        Executa ciclo de manutenção: decay + arquivamento + consolidação.

        Deve ser rodado 1x por dia (cron/task scheduler), nunca a cada turno.

        Args:
            decay_threshold: retenção abaixo da qual memória é arquivada
            min_cluster_size: tamanho mínimo de cluster para consolidação

        Returns:
            Relatório com contadores: arquivadas, consolidadas, clusters_formados
        """
        report = {"arquivadas": 0, "consolidadas": 0, "clusters_formados": 0}
        now = time.time()

        # 1. Recalcula retenção e arquiva o que caiu abaixo do limiar
        active = self.store.all_episodic(include_archived=False)
        to_archive: list[int] = []
        strength_updates: list[tuple[int, float]] = []
        archived_ids: set[int] = set()

        for row in active:
            days = (now - row["last_accessed_at"]) / 86400.0
            adj_strength = importance_adjusted_strength(row["strength"], row["importance"])
            r = retention(days, adj_strength)
            if should_archive(r, decay_threshold) and row["promoted_to_semantic"] == 0:
                to_archive.append(row["id"])
                archived_ids.add(row["id"])
            else:
                strength_updates.append((row["id"], row["strength"]))

        self.store.archive_episodic(to_archive)
        report["arquivadas"] = len(to_archive)

        # 2. Clusteriza memórias não-promovidas restantes e consolida
        remaining = [r for r in active if r["id"] not in archived_ids and r["promoted_to_semantic"] == 0]
        clusters = cluster_by_overlap(remaining, min_shared_entities=1, min_cluster_size=min_cluster_size)
        report["clusters_formados"] = len(clusters)

        for cluster in clusters:
            fact = consolidate_cluster(cluster, self.bridge)

            # Se o modelo retornou string vazia, não salva
            if not fact or not fact.strip():
                continue

            fact_embedding = self.bridge.embed(fact)
            all_entities: set[str] = set()
            for row in cluster:
                all_entities.update(json.loads(row["entities"]))

            self.store.add_semantic(
                fact=fact,
                embedding=fact_embedding,
                entities=sorted(all_entities),
                source_episodic_ids=[row["id"] for row in cluster],
            )
            report["consolidadas"] += 1

        return report

    def stats(self) -> dict:
        """Retorna estatísticas do armazenamento."""
        return self.store.stats()
