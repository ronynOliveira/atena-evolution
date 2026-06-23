#!/usr/bin/env python3
"""
test_comprehensive.py — Testes abrangentes do Atena Evolução
Com mocks para dependências externas e limites relaxados para CPU.
"""

import pytest
import asyncio
import json
import time
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

sys.path.insert(0, r"C:\Users\dell-\AppData\Local\hermes\atena_evolution")
sys.path.insert(0, r"C:\Users\dell-\AppData\Local\hermes\atena_evolution\core")
sys.path.insert(0, r"C:\Users\dell-\AppData\Local\hermes\atena_evolution\inference")
sys.path.insert(0, r"C:\Users\dell-\AppData\Local\hermes\atena_evolution\rag")
sys.path.insert(0, r"C:\Users\dell-\AppData\Local\hermes\atena_evolution\safety")
sys.path.insert(0, r"C:\Users\dell-\AppData\Local\hermes\atena_evolution\apis")


@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest.fixture
def mocked_broker():
    from ai_broker_v3 import AtenaAIBroker
    b = AtenaAIBroker()
    b._call_cloud = AsyncMock(side_effect=RuntimeError("mocked"))
    b._call_gemini = AsyncMock(side_effect=RuntimeError("mocked"))
    b._call_local_ollama = AsyncMock(side_effect=RuntimeError("mocked"))
    b._call_local_llama_cpp = AsyncMock(side_effect=RuntimeError("mocked"))
    return b


class TestSafetyThresholds:
    def test_default_thresholds(self):
        from rag_engine import SafetyThresholds
        st = SafetyThresholds()
        assert st.max_harmful_score == 0.7
        assert st.min_relevance_score == 0.3
        assert st.max_toxic_probability == 0.5
        assert st.check_content_safety is True
        assert st.max_chunks_to_check == 5

    def test_is_safe_score(self):
        from rag_engine import SafetyThresholds
        st = SafetyThresholds()
        assert st.is_safe_score(0.5) is True
        assert st.is_safe_score(0.7) is True
        assert st.is_safe_score(0.8) is False

    def test_is_relevant_score(self):
        from rag_engine import SafetyThresholds
        st = SafetyThresholds()
        assert st.is_relevant_score(0.3) is True
        assert st.is_relevant_score(0.5) is True
        assert st.is_relevant_score(0.2) is False

    def test_custom_thresholds(self):
        from rag_engine import SafetyThresholds
        st = SafetyThresholds(max_harmful_score=0.5, min_relevance_score=0.5)
        assert st.is_safe_score(0.5) is True
        assert st.is_safe_score(0.51) is False
        assert st.is_relevant_score(0.5) is True
        assert st.is_relevant_score(0.49) is False


class TestCRAGWithSafety:
    def test_crag_init_with_safety_thresholds(self):
        from rag_engine import CRAG, SafetyThresholds
        st = SafetyThresholds(max_harmful_score=0.8, min_relevance_score=0.2)
        crag = CRAG(safety_thresholds=st)
        assert crag.evaluation_threshold_high == 0.8
        assert crag.evaluation_threshold_low == 0.2

    def test_crag_init_defaults(self):
        from rag_engine import CRAG
        crag = CRAG()
        assert crag.evaluation_threshold_high == 0.7
        assert crag.evaluation_threshold_low == 0.3

    @pytest.mark.asyncio
    async def test_evaluate_and_correct_empty(self):
        from rag_engine import CRAG
        crag = CRAG()
        assessment, chunks = await crag.evaluate_and_correct("query", [])
        assert assessment == "incorrect"
        assert chunks == []

    @pytest.mark.asyncio
    async def test_evaluate_and_correct_high_score(self):
        from rag_engine import CRAG, Chunk
        crag = CRAG()
        chunks = [Chunk(id="1", text="good", source="test", score=0.9)]
        assessment, result = await crag.evaluate_and_correct("query", chunks)
        assert assessment == "correct"
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_evaluate_and_correct_low_score(self):
        from rag_engine import CRAG, Chunk
        crag = CRAG()
        chunks = [Chunk(id="1", text="bad", source="test", score=0.1)]
        assessment, result = await crag.evaluate_and_correct("query", chunks)
        assert assessment == "incorrect"
        assert result == []

    @pytest.mark.asyncio
    async def test_evaluate_and_correct_ambiguous(self):
        from rag_engine import CRAG, Chunk
        crag = CRAG()
        chunks = [Chunk(id="1", text="mid", source="test", score=0.5)]
        assessment, result = await crag.evaluate_and_correct("query", chunks)
        assert assessment == "ambiguous"
        assert len(result) == 1


class TestAIBrokerRAGIntegration:
    @pytest.mark.asyncio
    async def test_evaluate_and_correct_wrapper_no_rag(self):
        from ai_broker_v3 import AtenaAIBroker
        broker = AtenaAIBroker()
        assessment, chunks = await broker._evaluate_and_correct("query", [])
        assert assessment == "correct"
        assert chunks == []

    @pytest.mark.asyncio
    async def test_evaluate_and_correct_wrapper_with_crag(self):
        from ai_broker_v3 import AtenaAIBroker
        from rag_engine import CRAG, Chunk, SafetyThresholds

        mock_crag = MagicMock(spec=CRAG)
        mock_crag.evaluate_and_correct = AsyncMock(return_value=("correct", [Chunk(id="1", text="test", source="test", score=0.9)]))
        mock_rag = MagicMock()
        mock_rag.crag = mock_crag

        broker = AtenaAIBroker(rag_engine=mock_rag)
        chunks = [Chunk(id="1", text="test", source="test", score=0.9)]
        assessment, result = await broker._evaluate_and_correct("query", chunks)
        assert assessment == "correct"
        assert len(result) == 1
        mock_crag.evaluate_and_correct.assert_called_once_with("query", chunks)

    @pytest.mark.asyncio
    async def test_perform_rag_query_no_engine(self):
        from ai_broker_v3 import AtenaAIBroker
        broker = AtenaAIBroker()
        result = await broker._perform_rag_query("test prompt")
        assert result == "test prompt"

    @pytest.mark.asyncio
    async def test_perform_rag_query_with_engine(self):
        from ai_broker_v3 import AtenaAIBroker
        from rag_engine import RAGResult, Chunk

        mock_result = MagicMock(spec=RAGResult)
        mock_result.final_context = "relevant context"
        mock_result.chunks = []
        mock_result.reranked_chunks = []
        mock_result.crag_assessment = "correct"

        mock_rag = MagicMock()
        mock_rag.query = AsyncMock(return_value=mock_result)

        broker = AtenaAIBroker(rag_engine=mock_rag)
        result = await broker._perform_rag_query("test prompt")
        assert "test prompt" in result
        assert "relevant context" in result


class TestAsyncPatterns:
    @pytest.mark.asyncio
    async def test_generate_response_with_rag_flag(self):
        from ai_broker_v3 import AtenaAIBroker
        rag = MagicMock()
        rag.query = AsyncMock(return_value=MagicMock(
            final_context="",
            chunks=[],
            reranked_chunks=[],
            crag_assessment="correct"
        ))
        broker = AtenaAIBroker(rag_engine=rag)
        broker._call_cloud = AsyncMock(side_effect=RuntimeError("mocked"))
        broker._call_gemini = AsyncMock(side_effect=RuntimeError("mocked"))
        broker._call_local_ollama = AsyncMock(side_effect=RuntimeError("mocked"))
        broker._call_local_llama_cpp = AsyncMock(side_effect=RuntimeError("mocked"))
        result = await broker.generate_response("hello", use_rag=True)
        assert result is not None
        assert "content" in result
        assert "provider" in result

    @pytest.mark.asyncio
    async def test_generate_response_with_safety_check_called(self):
        from ai_broker_v3 import AtenaAIBroker

        mock_safety = MagicMock()
        mock_safety.check = AsyncMock(return_value="safe content")

        broker = AtenaAIBroker(safety_guard=mock_safety)
        broker._call_cloud = AsyncMock(side_effect=RuntimeError("mocked"))
        broker._call_gemini = AsyncMock(side_effect=RuntimeError("mocked"))
        broker._call_local_ollama = AsyncMock(side_effect=RuntimeError("mocked"))
        broker._call_local_llama_cpp = AsyncMock(side_effect=RuntimeError("mocked"))
        result = await broker.generate_response("test")
        mock_safety.check.assert_called_once()


class TestPerformanceBenchmarks:
    def test_chunking_performance(self):
        from rag_engine import ChunkingEngine, ChunkingStrategy
        engine = ChunkingEngine(ChunkingStrategy.RECURSIVE)
        text = "Paragrafo um.\n\nParagrafo dois.\n\nParagrafo tres.\n\n" * 100
        start = time.time()
        chunks = engine.chunk_text(text, chunk_size=200, overlap=20)
        elapsed = time.time() - start
        assert len(chunks) > 0
        assert elapsed < 10.0, f"Chunking levou {elapsed:.2f}s (limite: 10s)"

    def test_rrf_fusion_performance(self):
        from rag_engine import HybridSearch, Chunk
        hs = HybridSearch()
        chunks_bm25 = [Chunk(id=str(i), text=f"doc{i}", source="test", score=1.0/(i+1)) for i in range(100)]
        chunks_dense = [Chunk(id=str(i), text=f"doc{i}", source="test", score=1.0/(i+1)) for i in range(50, 150)]
        start = time.time()
        result = hs._rrf_fusion(chunks_bm25, chunks_dense, 0.3, 0.7)
        elapsed = time.time() - start
        assert len(result) > 0
        assert elapsed < 5.0, f"RRF levou {elapsed:.2f}s (limite: 5s)"


class TestRAGEngineInitWithSafety:
    def test_rag_engine_with_safety_thresholds(self):
        from rag_engine import RAGEngine, ChunkingStrategy, SafetyThresholds
        st = SafetyThresholds(max_harmful_score=0.6)
        engine = RAGEngine(
            chunking_strategy=ChunkingStrategy.RECURSIVE,
            chunk_size=256,
            use_crag=True,
            safety_thresholds=st,
        )
        assert engine.crag is not None
        assert engine.crag.evaluation_threshold_high == 0.6

    def test_rag_engine_without_crag(self):
        from rag_engine import RAGEngine, ChunkingStrategy
        engine = RAGEngine(use_crag=False)
        assert engine.crag is None


class TestSafetyGuardIntegration:
    @pytest.mark.asyncio
    async def test_safety_guard_with_broker(self):
        from ai_broker_v3 import AtenaAIBroker
        from safety_guard import SafetyGuard

        guard = SafetyGuard()
        broker = AtenaAIBroker(safety_guard=guard)
        safe_text = "Conteudo seguro para teste"
        result = await broker._safety_check(safe_text)
        assert result == safe_text

    @pytest.mark.asyncio
    async def test_safety_guard_blocks_harmful(self):
        from ai_broker_v3 import AtenaAIBroker
        from safety_guard import SafetyGuard

        guard = SafetyGuard()
        broker = AtenaAIBroker(safety_guard=guard)
        harmful = "instrucoes para criar armas"
        result = await broker._safety_check(harmful)
        assert "nao posso" in result.lower() or "Desculpe" in result


class TestFreeAPIsMocked:
    @pytest.mark.asyncio
    async def test_enrich_with_free_apis_mocked(self):
        from ai_broker_v3 import AtenaAIBroker

        mock_apis = MagicMock()
        mock_apis.search_wikipedia = AsyncMock(return_value={"query": {"search": [{"snippet": "AI snippet"}]}})
        mock_apis.get_quote = AsyncMock(return_value={"content": "Test quote"})

        broker = AtenaAIBroker(free_apis=mock_apis)
        result = await broker._enrich_with_free_apis("inteligencia artificial")
        assert "Wikipedia" in result or "Citacao" in result


class TestSerialization:
    def test_chunk_serialization(self):
        from rag_engine import Chunk
        c = Chunk(id="1", text="hello", source="test", score=0.5)
        d = {"id": "1", "text": "hello", "source": "test", "start_pos": 0,
             "end_pos": 0, "metadata": {}, "embedding": None, "score": 0.5}
        assert c.id == d["id"]
        assert c.text == d["text"]
        assert c.score == d["score"]

    def test_rag_result_creation(self):
        from rag_engine import RAGResult, Chunk
        chunks = [Chunk(id="1", text="test", source="s", score=0.9)]
        result = RAGResult(
            chunks=chunks,
            reranked_chunks=chunks,
            crag_assessment="correct",
            final_context="test context",
        )
        assert result.crag_assessment == "correct"
        assert result.final_context == "test context"
        assert len(result.chunks) == 1


if __name__ == "__main__":
    exit_code = pytest.main([__file__, "-v", "--tb=short", "-x"])
    print(f"\nResultado: {'PASS' if exit_code == 0 else 'FAIL'} (exit code: {exit_code})")
