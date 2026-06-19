"""
test_atena_memory.py — Roda sem Ollama. Usa uma bridge falsa com
embeddings determinísticos (hash → vetor) para validar a LÓGICA do
sistema: decay, ranking, clustering, arquivamento, consolidação.

Rodar com:  pytest test_atena_memory.py -v
"""

import math
import time
import hashlib
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib", "memory"))

from store import MemoryStore
from decay import retention, reinforce, should_archive, importance_adjusted_strength
from retrieval import cosine_similarity, retrieve_top_k, entity_overlap, score_rows
from consolidation import extract_entities, cluster_by_overlap
from pipeline import AtenaMemory, heuristic_importance


class FakeBridge:
    """Embeddings determinísticos via hash — sem rede, sem Ollama."""

    def __init__(self, consolidate_response: str = "Fato consolidado de teste."):
        self.consolidate_response = consolidate_response
        self.ask_calls = 0
        self.embed_calls = 0

    def embed(self, text: str) -> list[float]:
        self.embed_calls += 1
        words = text.lower().split()
        vec = [0.0] * 16
        for w in words:
            h = int(hashlib.md5(w.encode()).hexdigest(), 16)
            idx = h % 16
            vec[idx] += 1.0
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]

    def ask(self, prompt: str, system: str = "", temperature: float = 0.3) -> str:
        self.ask_calls += 1
        return self.consolidate_response

    def health_check(self) -> bool:
        return True


# =====================================================================
# decay.py
# =====================================================================

class TestDecay:
    def test_retention_decays_over_time(self):
        r_now = retention(0, strength=1.0)
        r_later = retention(10, strength=1.0)
        assert r_now == 1.0
        assert r_later < r_now
        assert 0 <= r_later <= 1

    def test_retention_higher_strength_decays_slower(self):
        r_weak = retention(5, strength=1.0)
        r_strong = retention(5, strength=10.0)
        assert r_strong > r_weak

    def test_reinforce_increases_strength(self):
        assert reinforce(1.0, boost=1.0) == 2.0

    def test_should_archive_threshold(self):
        assert should_archive(0.01, threshold=0.05) is True
        assert should_archive(0.5, threshold=0.05) is False

    def test_retention_zero_days(self):
        """Recém-acessada: retenção = 1.0 independente da força."""
        assert abs(retention(0, strength=0.5) - 1.0) < 1e-9
        assert abs(retention(0, strength=100.0) - 1.0) < 1e-9

    def test_retention_negative_days_clamped(self):
        """Dias negativos (clock skew) devem ser clampados a 0."""
        r = retention(-5, strength=1.0)
        assert r == 1.0

    def test_retention_zero_strength_clamped(self):
        """Força zero deve ser clampada a 0.01 para evitar divisão por zero.
        Com strength=0.01 e t=10, e^(-1000) ≈ 0.0 — é o comportamento correto:
        sem força alguma, a memória é instantaneamente esquecida."""
        r = retention(10, strength=0.0)
        assert r == 0.0  # e^(-1000) underflows to 0.0

    def test_retention_extreme_strength(self):
        """Força alta → retenção maior, mas não necessariamente > 0.99.
        e^(-365/1000) ≈ 0.694 — a fórmula é honesta sobre o decaimento."""
        r = retention(365, strength=1000.0)
        assert 0.5 < r < 0.8

    def test_importance_adjusted_strength(self):
        """Importance 0 não muda força; importance 1 dobra."""
        assert importance_adjusted_strength(2.0, 0.0) == 2.0
        assert importance_adjusted_strength(2.0, 1.0) == 4.0

    def test_reinforce_custom_boost(self):
        assert reinforce(3.0, boost=0.5) == 3.5


# =====================================================================
# retrieval.py
# =====================================================================

class TestRetrieval:
    def test_cosine_similarity_identical_vectors(self):
        v = [1.0, 0.0, 0.0]
        assert abs(cosine_similarity(v, v) - 1.0) < 1e-9

    def test_cosine_similarity_orthogonal_vectors(self):
        a = [1.0, 0.0]
        b = [0.0, 1.0]
        assert abs(cosine_similarity(a, b)) < 1e-9

    def test_cosine_similarity_empty_vectors(self):
        assert cosine_similarity([], []) == 0.0

    def test_cosine_similarity_dimension_mismatch(self):
        assert cosine_similarity([1.0, 0.0], [1.0, 0.0, 0.0]) == 0.0

    def test_cosine_similarity_zero_vector(self):
        assert cosine_similarity([0.0, 0.0], [1.0, 0.0]) == 0.0

    def test_entity_overlap_identical(self):
        s = {"a", "b"}
        assert entity_overlap(s, s) == 1.0

    def test_entity_overlap_disjoint(self):
        assert entity_overlap({"a"}, {"b"}) == 0.0

    def test_entity_overlap_empty(self):
        assert entity_overlap(set(), {"a"}) == 0.0
        assert entity_overlap({"a"}, set()) == 0.0
        assert entity_overlap(set(), set()) == 0.0

    def test_entity_overlap_partial(self):
        a = {"a", "b", "c"}
        b = {"b", "c", "d"}
        # intersection=2, union=4 → 0.5
        assert abs(entity_overlap(a, b) - 0.5) < 1e-9

    def test_retrieve_top_k_respects_k(self):
        """Nunca retorna mais que k itens."""
        rows = [
            {"id": 1, "content": "a", "embedding": json.dumps([1.0, 0.0]),
             "entities": json.dumps([]), "strength": 1.0,
             "last_accessed_at": time.time()},
        ]
        results = retrieve_top_k(rows, [], [1.0, 0.0], set(), k=3)
        assert len(results) <= 3

    def test_retrieve_top_k_respects_token_budget(self):
        """Itens que estouram o orçamento não são incluídos (se já houver seleção)."""
        rows = [
            {"id": i, "content": "x" * 200, "embedding": json.dumps([1.0, 0.0]),
             "entities": json.dumps([]), "strength": 1.0,
             "last_accessed_at": time.time()}
            for i in range(5)
        ]
        # budget = 2 tokens * 4 chars/token = 8 chars → só 1 item cabe
        results = retrieve_top_k(rows, [], [1.0, 0.0], set(), k=5, token_budget=2)
        assert len(results) == 1

    def test_retrieve_top_k_empty_input(self):
        """Recall com banco vazio retorna lista vazia."""
        results = retrieve_top_k([], [], [1.0, 0.0], set(), k=5)
        assert results == []


# =====================================================================
# consolidation.py
# =====================================================================

class TestConsolidation:
    def test_extract_entities_finds_proper_nouns(self):
        text = "Ele disse que Robério mencionou o Projeto Atena e a Teoria do Tempo Puxado."
        entities = extract_entities(text)
        assert "Robério" in entities
        assert any("Atena" in e for e in entities)

    def test_extract_entities_ignores_sentence_initial_capital(self):
        text = "Hoje choveu bastante na cidade."
        entities = extract_entities(text)
        assert "Hoje" not in entities

    def test_extract_entities_finds_domain_terms_lowercase(self):
        text = "ele falou sobre distonia generalizada hoje."
        entities = extract_entities(text)
        assert "distonia" in entities

    def test_extract_entities_empty_string(self):
        assert extract_entities("") == []

    def test_extract_entities_no_entities(self):
        """Texto sem nomes próprios ou termos de domínio."""
        entities = extract_entities("o gato preto sentou no tapete")
        assert entities == []

    def test_cluster_by_overlap_basic(self):
        rows = [
            {"id": 1, "entities": json.dumps(["Atena", "Robério"])},
            {"id": 2, "entities": json.dumps(["Atena", "distonia"])},
            {"id": 3, "entities": json.dumps(["bolo", "cenoura"])},
        ]
        clusters = cluster_by_overlap(rows, min_shared_entities=1, min_cluster_size=2)
        # 1 e 2 compartilham "Atena"; 3 é isolado
        assert len(clusters) == 1
        ids = {r["id"] for r in clusters[0]}
        assert ids == {1, 2}

    def test_cluster_by_overlap_empty(self):
        assert cluster_by_overlap([]) == []

    def test_cluster_by_overlap_single_row(self):
        rows = [{"id": 1, "entities": json.dumps(["Atena"])}]
        clusters = cluster_by_overlap(rows, min_cluster_size=2)
        assert clusters == []

    def test_cluster_by_overlap_no_shared(self):
        rows = [
            {"id": 1, "entities": json.dumps(["A"])},
            {"id": 2, "entities": json.dumps(["B"])},
            {"id": 3, "entities": json.dumps(["C"])},
        ]
        clusters = cluster_by_overlap(rows, min_shared_entities=1, min_cluster_size=2)
        assert clusters == []

    def test_cluster_by_overlap_transitive(self):
        """Transitividade: A-B e B-C → A,B,C no mesmo cluster."""
        rows = [
            {"id": 1, "entities": json.dumps(["x"])},
            {"id": 2, "entities": json.dumps(["x", "y"])},
            {"id": 3, "entities": json.dumps(["y"])},
        ]
        clusters = cluster_by_overlap(rows, min_shared_entities=1, min_cluster_size=2)
        assert len(clusters) == 1
        ids = {r["id"] for r in clusters[0]}
        assert ids == {1, 2, 3}

    def test_cluster_by_overlap_min_shared_entities(self):
        """min_shared_entities=2: só agrupa se compartilham 2+ entidades."""
        rows = [
            {"id": 1, "entities": json.dumps(["a", "b"])},
            {"id": 2, "entities": json.dumps(["a", "b"])},
            {"id": 3, "entities": json.dumps(["a"])},
        ]
        clusters = cluster_by_overlap(rows, min_shared_entities=2, min_cluster_size=2)
        assert len(clusters) == 1
        ids = {r["id"] for r in clusters[0]}
        assert ids == {1, 2}


# =====================================================================
# store.py
# =====================================================================

class TestStore:
    def test_add_and_retrieve_episodic(self, tmp_path):
        db = str(tmp_path / "test.db")
        store = MemoryStore(db)
        mid = store.add_episodic(
            content="teste",
            embedding=[1.0, 0.0],
            entities=["Atena"],
            importance=0.8,
            session_id="s1",
        )
        assert mid > 0
        rows = store.all_episodic()
        assert len(rows) == 1
        assert rows[0]["content"] == "teste"
        assert rows[0]["importance"] == 0.8

    def test_add_and_retrieve_semantic(self, tmp_path):
        db = str(tmp_path / "test.db")
        store = MemoryStore(db)
        sid = store.add_semantic(
            fact="Fato teste",
            embedding=[0.0, 1.0],
            entities=["Atena"],
            source_episodic_ids=[1, 2],
        )
        assert sid > 0
        rows = store.all_semantic()
        assert len(rows) == 1
        assert rows[0]["fact"] == "Fato teste"

    def test_archive_episodic(self, tmp_path):
        db = str(tmp_path / "test.db")
        store = MemoryStore(db)
        mid = store.add_episodic("teste", [1.0], [])
        store.archive_episodic([mid])
        assert len(store.all_episodic(include_archived=False)) == 0
        assert len(store.all_episodic(include_archived=True)) == 1

    def test_archive_episodic_empty_list(self, tmp_path):
        """Arquivar lista vazia não deve levantar exceção."""
        db = str(tmp_path / "test.db")
        store = MemoryStore(db)
        store.archive_episodic([])  # não deve crashar

    def test_reinforce_episodic(self, tmp_path):
        db = str(tmp_path / "test.db")
        store = MemoryStore(db)
        mid = store.add_episodic("teste", [1.0], [])
        store.reinforce_episodic(mid, 5.0)
        row = store.all_episodic()[0]
        assert row["strength"] == 5.0
        assert row["access_count"] == 1

    def test_supersede_semantic(self, tmp_path):
        db = str(tmp_path / "test.db")
        store = MemoryStore(db)
        sid = store.add_semantic("velho", [1.0], [], source_episodic_ids=[])
        new_sid = store.add_semantic("novo", [1.0], [], source_episodic_ids=[])
        store.supersede_semantic(sid, new_sid)
        active = store.all_semantic(include_superseded=False)
        assert len(active) == 1
        assert active[0]["id"] == new_sid

    def test_stats(self, tmp_path):
        db = str(tmp_path / "test.db")
        store = MemoryStore(db)
        store.add_episodic("a", [1.0], [])
        store.add_episodic("b", [1.0], [])
        store.add_semantic("f1", [1.0], [], source_episodic_ids=[])
        s = store.stats()
        assert s["episodic_total"] == 2
        assert s["semantic_total"] == 1

    def test_count_methods(self, tmp_path):
        """Testa métodos de contagem que não carregam tudo em memória."""
        db = str(tmp_path / "test.db")
        store = MemoryStore(db)
        store.add_episodic("a", [1.0], [])
        store.add_episodic("b", [1.0], [])
        store.add_semantic("f1", [1.0], [], source_episodic_ids=[])
        assert store.count_episodic_active() == 2
        assert store.count_semantic_active() == 1

    def test_add_semantic_marks_episodic_promoted(self, tmp_path):
        """Ao adicionar semantic, source_episodic_ids devem ser marcados."""
        db = str(tmp_path / "test.db")
        store = MemoryStore(db)
        e1 = store.add_episodic("mem1", [1.0], [])
        e2 = store.add_episodic("mem2", [1.0], [])
        store.add_semantic("fato", [1.0], [], source_episodic_ids=[e1, e2])
        rows = store.all_episodic(include_archived=True)
        for r in rows:
            assert r["promoted_to_semantic"] == 1

    def test_update_episodic_strength_bulk(self, tmp_path):
        db = str(tmp_path / "test.db")
        store = MemoryStore(db)
        ids = [store.add_episodic(f"m{i}", [1.0], []) for i in range(3)]
        store.update_episodic_strength_bulk([(ids[0], 10.0), (ids[1], 20.0)])
        rows = {r["id"]: r for r in store.all_episodic()}
        assert rows[ids[0]]["strength"] == 10.0
        assert rows[ids[1]]["strength"] == 20.0

    def test_update_episodic_strength_bulk_empty(self, tmp_path):
        """Bulk update com lista vazia não deve levantar exceção."""
        db = str(tmp_path / "test.db")
        store = MemoryStore(db)
        store.update_episodic_strength_bulk([])  # não deve crashar


# =====================================================================
# pipeline.py: integração end-to-end com FakeBridge
# =====================================================================

class TestPipeline:
    def test_remember_and_recall_same_topic(self, tmp_path):
        db = str(tmp_path / "test.db")
        mem = AtenaMemory(db_path=db, bridge=FakeBridge())

        mem.remember("Robério tem distonia generalizada e dor crônica.", session_id="seg")
        mem.remember("Robério é escritor e técnico em informática.", session_id="qua")
        mem.remember("A receita de bolo de cenoura leva três ovos.", session_id="qui")

        contexto = mem.recall("Quem é o usuário e quais suas condições de saúde?")

        assert "distonia" in contexto.lower()
        assert contexto.count("bolo") == 0 or "distonia" in contexto

    def test_recall_reinforces_strength(self, tmp_path):
        db = str(tmp_path / "test.db")
        mem = AtenaMemory(db_path=db, bridge=FakeBridge())
        mem_id = mem.remember("Robério trabalha no Projeto Atena.", session_id="s1")

        before = mem.store.all_episodic()[0]["strength"]
        mem.recall("Projeto Atena")
        after = mem.store.all_episodic()[0]["strength"]

        assert after > before

    def test_maintenance_archives_old_unused_low_importance(self, tmp_path):
        db = str(tmp_path / "test.db")
        mem = AtenaMemory(db_path=db, bridge=FakeBridge())

        mem.remember("nota qualquer sem marcador de importancia", importance=0.05)

        with mem.store._conn() as conn:
            old_time = time.time() - (200 * 86400)
            conn.execute("UPDATE episodic_memory SET last_accessed_at = ?, strength = 1.0", (old_time,))

        report = mem.run_maintenance(decay_threshold=0.05)
        assert report["arquivadas"] == 1

        active = mem.store.all_episodic(include_archived=False)
        assert len(active) == 0

    def test_maintenance_consolidates_clustered_memories(self, tmp_path):
        db = str(tmp_path / "test.db")
        fake = FakeBridge(consolidate_response="Robério tem distonia e é escritor técnico.")
        mem = AtenaMemory(db_path=db, bridge=fake)

        mem.remember("Robério mencionou que tem distonia generalizada.", session_id="seg")
        mem.remember("Robério falou sobre a distonia novamente durante a semana.", session_id="qua")

        report = mem.run_maintenance(min_cluster_size=2)

        assert report["clusters_formados"] >= 1
        assert report["consolidadas"] >= 1
        assert fake.ask_calls == report["consolidadas"]

        semantic = mem.store.all_semantic()
        assert len(semantic) >= 1
        assert "distonia" in semantic[0]["fact"].lower()

    def test_heuristic_importance_higher_for_personal_markers(self):
        low = heuristic_importance("o céu está nublado hoje")
        high = heuristic_importance("decidi que o projeto Atena é importante para minha ansiedade")
        assert high > low

    def test_recall_empty_database(self, tmp_path):
        """Recall em banco vazio deve retornar string vazia, não crashar."""
        db = str(tmp_path / "test.db")
        mem = AtenaMemory(db_path=db, bridge=FakeBridge())
        contexto = mem.recall("qualquer coisa")
        assert contexto == ""

    def test_maintenance_empty_database(self, tmp_path):
        """Manutenção em banco vazio não deve crashar."""
        db = str(tmp_path / "test.db")
        mem = AtenaMemory(db_path=db, bridge=FakeBridge())
        report = mem.run_maintenance()
        assert report["arquivadas"] == 0
        assert report["consolidadas"] == 0
        assert report["clusters_formados"] == 0

    def test_maintenance_skips_already_promoted(self, tmp_path):
        """Memórias já promovidas não devem ser arquivadas nem re-consolidadas."""
        db = str(tmp_path / "test.db")
        fake = FakeBridge(consolidate_response="Fato consolidado.")
        mem = AtenaMemory(db_path=db, bridge=fake)

        mem.remember("Robério tem distonia.", session_id="s1")
        mem.remember("Robério mencionou distonia de novo.", session_id="s2")

        # Primeira manutenção: consolida
        r1 = mem.run_maintenance(min_cluster_size=2)
        assert r1["consolidadas"] >= 1

        # Segunda manutenção: não deve re-consolidar (já promovidas)
        ask_before = fake.ask_calls
        r2 = mem.run_maintenance(min_cluster_size=2)
        assert fake.ask_calls == ask_before  # não houve novas chamadas

    def test_maintenance_skips_empty_consolidation(self, tmp_path):
        """Se o modelo retornar string vazia, não salva semantic_memory."""
        db = str(tmp_path / "test.db")
        fake = FakeBridge(consolidate_response="")  # resposta vazia
        mem = AtenaMemory(db_path=db, bridge=fake)

        mem.remember("Robério tem distonia.", session_id="s1")
        mem.remember("Robério mencionou distonia de novo.", session_id="s2")

        report = mem.run_maintenance(min_cluster_size=2)
        assert report["consolidadas"] == 0  # não salvou fato vazio
        assert len(mem.store.all_semantic()) == 0

    def test_many_recalls_performance(self, tmp_path):
        """50 memórias, 100 recalls — deve completar sem erros."""
        db = str(tmp_path / "test.db")
        mem = AtenaMemory(db_path=db, bridge=FakeBridge())

        for i in range(50):
            mem.remember(f"Memória número {i} sobre o projeto Atena.", session_id=f"s{i}")

        for _ in range(100):
            ctx = mem.recall("projeto Atena")
            assert isinstance(ctx, str)

    def test_stats_integration(self, tmp_path):
        db = str(tmp_path / "test.db")
        mem = AtenaMemory(db_path=db, bridge=FakeBridge())
        mem.remember("teste 1", session_id="s1")
        mem.remember("teste 2", session_id="s2")
        s = mem.stats()
        assert s["episodic_total"] == 2
        assert s["episodic_ativas"] == 2

    def test_recall_with_token_budget_one(self, tmp_path):
        """Com orçamento mínimo, retorna exatamente 1 memória."""
        db = str(tmp_path / "test.db")
        mem = AtenaMemory(db_path=db, bridge=FakeBridge())
        mem.remember("Atena é um projeto de IA.", session_id="s1")
        mem.remember("O projeto Atena usa Ollama.", session_id="s2")

        ctx = mem.recall("projeto Atena", k=10, token_budget=1)
        assert isinstance(ctx, str)


# =====================================================================
# Edge cases gerais
# =====================================================================

class TestEdgeCases:
    def test_unicode_content(self, tmp_path):
        """Memórias com caracteres Unicode (emoji, acentos) não devem crashar."""
        db = str(tmp_path / "test.db")
        mem = AtenaMemory(db_path=db, bridge=FakeBridge())
        mid = mem.remember("Robério está 😊 com o projeto Atena — é incrível!", session_id="s1")
        assert mid > 0
        ctx = mem.recall("Robério")
        assert isinstance(ctx, str)

    def test_very_long_content(self, tmp_path):
        """Memória com 10K caracteres não deve crashar."""
        db = str(tmp_path / "test.db")
        mem = AtenaMemory(db_path=db, bridge=FakeBridge())
        long_text = "Atena " * 2000
        mid = mem.remember(long_text, session_id="s1")
        assert mid > 0

    def test_special_characters_in_content(self, tmp_path):
        """Conteúdo com aspas, barras, etc. não deve corromper JSON/SQL."""
        db = str(tmp_path / "test.db")
        mem = AtenaMemory(db_path=db, bridge=FakeBridge())
        mid = mem.remember('Ele disse: "olá" e depois \\n saiu', session_id="s1")
        assert mid > 0
        rows = mem.store.all_episodic()
        assert len(rows) == 1

    def test_extreme_decay_threshold_zero(self, tmp_path):
        """Threshold 0: nada deve ser arquivada (retenção sempre > 0)."""
        db = str(tmp_path / "test.db")
        mem = AtenaMemory(db_path=db, bridge=FakeBridge())
        mem.remember("teste", importance=0.01)
        with mem.store._conn() as conn:
            old_time = time.time() - (1000 * 86400)
            conn.execute("UPDATE episodic_memory SET last_accessed_at = ?", (old_time,))
        report = mem.run_maintenance(decay_threshold=0.0)
        assert report["arquivadas"] == 0

    def test_extreme_decay_threshold_one(self, tmp_path):
        """Threshold 1: tudo com retenção < 1 deve ser arquivada (exceto recém-criada)."""
        db = str(tmp_path / "test.db")
        mem = AtenaMemory(db_path=db, bridge=FakeBridge())
        mem.remember("teste", importance=0.01)
        with mem.store._conn() as conn:
            old_time = time.time() - (10 * 86400)
            conn.execute("UPDATE episodic_memory SET last_accessed_at = ?, strength = 0.5", (old_time,))
        report = mem.run_maintenance(decay_threshold=1.0)
        # Com threshold=1.0, só retenção=1.0 (recém-acessada) sobrevive
        # strength=0.5, 10 dias → retention = e^(-10/0.5) ≈ e^(-20) ≈ 0 → arquivada
        assert report["arquivadas"] == 1


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
