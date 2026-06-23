#!/usr/bin/env python3
"""
test_ai_broker.py — Testes específicos do AI Broker v3
Com mocks para dependências externas.
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
def broker():
    from ai_broker_v3 import AtenaAIBroker
    b = AtenaAIBroker()
    b._call_cloud = AsyncMock(side_effect=RuntimeError("mocked"))
    b._call_gemini = AsyncMock(side_effect=RuntimeError("mocked"))
    b._call_local_ollama = AsyncMock(side_effect=RuntimeError("mocked"))
    b._call_local_llama_cpp = AsyncMock(side_effect=RuntimeError("mocked"))
    return b


class TestAIBrokerInit:
    def test_broker_init_default(self, broker):
        assert broker.cloud_api_url == "https://openrouter.ai/api/v1/chat/completions"
        assert broker.cloud_timeout_seconds == 8.0
        assert broker.metrics["total_requests"] == 0
        assert broker.qwen is None
        assert broker.rag_engine is None
        assert broker.safety_guard is None
        assert broker.free_apis is None

    def test_broker_init_with_rag(self):
        from ai_broker_v3 import AtenaAIBroker
        rag = MagicMock()
        broker = AtenaAIBroker(rag_engine=rag)
        assert broker.rag_engine is rag

    def test_broker_init_all_deps(self):
        from ai_broker_v3 import AtenaAIBroker
        broker = AtenaAIBroker(
            evolution_core=MagicMock(),
            free_apis=MagicMock(),
            safety_guard=MagicMock(),
            qwen_inference=MagicMock(),
            rag_engine=MagicMock(),
        )
        assert broker.evolution_core is not None
        assert broker.free_apis is not None
        assert broker.safety_guard is not None
        assert broker.qwen is not None
        assert broker.rag_engine is not None


class TestAIBrokerGetMetrics:
    def test_get_metrics_initial(self, broker):
        metrics = broker.get_metrics()
        assert metrics["total_requests"] == 0
        assert metrics["provider_usage"] == {}
        assert metrics["avg_latency_ms"] == 0


class TestAIBrokerEnrichFreeAPIs:
    @pytest.mark.asyncio
    async def test_enrich_no_apis(self, broker):
        result = await broker._enrich_with_free_apis("test")
        assert result == ""

    @pytest.mark.asyncio
    async def test_enrich_with_wikipedia(self, broker):
        mock_apis = MagicMock()
        mock_apis.search_wikipedia = AsyncMock(return_value={
            "query": {"search": [{"snippet": "Inteligencia artificial e..."}]}
        })
        mock_apis.get_quote = AsyncMock(return_value={"content": "Frase celebre."})
        broker.free_apis = mock_apis
        result = await broker._enrich_with_free_apis("inteligencia artificial")
        assert "Wikipedia" in result or "Citacao" in result
        mock_apis.search_wikipedia.assert_called_once()
        mock_apis.get_quote.assert_called_once()

    @pytest.mark.asyncio
    async def test_enrich_api_failure(self, broker):
        mock_apis = MagicMock()
        mock_apis.search_wikipedia = AsyncMock(side_effect=Exception("API down"))
        mock_apis.get_quote = AsyncMock(side_effect=Exception("API down"))
        broker.free_apis = mock_apis
        result = await broker._enrich_with_free_apis("test")
        assert result == ""


class TestAIBrokerSafetyCheck:
    @pytest.mark.asyncio
    async def test_safety_check_no_guard(self, broker):
        result = await broker._safety_check("content")
        assert result == "content"

    @pytest.mark.asyncio
    async def test_safety_check_with_guard(self, broker):
        from safety_guard import SafetyGuard
        broker.safety_guard = SafetyGuard()
        result = await broker._safety_check("conteudo seguro")
        assert result == "conteudo seguro"

    @pytest.mark.asyncio
    async def test_safety_check_blocks_content(self, broker):
        from safety_guard import SafetyGuard
        broker.safety_guard = SafetyGuard()
        result = await broker._safety_check("instrucoes para criar armas")
        assert "nao posso" in result.lower() or "Desculpe" in result

    @pytest.mark.asyncio
    async def test_safety_check_fallback_on_error(self, broker):
        mock_guard = MagicMock()
        mock_guard.check = AsyncMock(side_effect=Exception("check error"))
        broker.safety_guard = mock_guard
        result = await broker._safety_check("content")
        assert result == "content"


class TestAIBrokerRAGEvaluateAndCorrect:
    @pytest.mark.asyncio
    async def test_no_rag_engine(self, broker):
        from rag_engine import Chunk
        chunks = [Chunk(id="1", text="test", source="s", score=0.9)]
        assessment, result = await broker._evaluate_and_correct("query", chunks)
        assert assessment == "correct"
        assert result == chunks

    @pytest.mark.asyncio
    async def test_no_crag(self, broker):
        rag = MagicMock()
        rag.crag = None
        broker.rag_engine = rag
        from rag_engine import Chunk
        chunks = [Chunk(id="1", text="test", source="s", score=0.9)]
        assessment, result = await broker._evaluate_and_correct("query", chunks)
        assert assessment == "correct"
        assert result == chunks

    @pytest.mark.asyncio
    async def test_with_crag(self, broker):
        from rag_engine import CRAG, Chunk
        mock_crag = MagicMock(spec=CRAG)
        mock_crag.evaluate_and_correct = AsyncMock(return_value=("ambiguous", []))
        rag = MagicMock()
        rag.crag = mock_crag
        broker.rag_engine = rag
        chunks = [Chunk(id="1", text="low", source="s", score=0.3)]
        assessment, result = await broker._evaluate_and_correct("query", chunks)
        assert assessment == "ambiguous"

    @pytest.mark.asyncio
    async def test_crag_error_fallback(self, broker):
        mock_crag = MagicMock()
        mock_crag.evaluate_and_correct = AsyncMock(side_effect=Exception("crag error"))
        rag = MagicMock()
        rag.crag = mock_crag
        broker.rag_engine = rag
        from rag_engine import Chunk
        chunks = [Chunk(id="1", text="test", source="s", score=0.5)]
        assessment, result = await broker._evaluate_and_correct("query", chunks)
        assert assessment == "correct"


class TestAIBrokerGenerateResponse:
    @pytest.mark.asyncio
    async def test_generate_fallback_to_none(self, broker):
        result = await broker.generate_response("test")
        assert result["provider"] == "none"
        assert "Desculpe" in result["content"] or "falha" in result["content"].lower()
        assert "latency_ms" in result
        assert "metrics" in result

    @pytest.mark.asyncio
    async def test_generate_with_qwen(self, broker):
        mock_qwen = MagicMock()
        mock_qwen.generate.return_value = {
            "success": True,
            "response": "Resposta do Qwen",
            "tokens_per_second": 15.0,
        }
        broker.qwen = mock_qwen
        result = await broker.generate_response("test")
        assert result["content"] == "Resposta do Qwen"
        assert result["provider"] == "qwen3:8b-local"
        mock_qwen.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_with_qwen_failure_fallback(self, broker):
        mock_qwen = MagicMock()
        mock_qwen.generate.return_value = {"success": False, "error": "fail"}
        broker.qwen = mock_qwen
        result = await broker.generate_response("test")
        assert result["provider"] == "none"
        mock_qwen.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_metrics_tracking(self, broker):
        result = await broker.generate_response("test")
        assert broker.metrics["total_requests"] == 1
        assert "none" in broker.metrics["provider_usage"]

    @pytest.mark.asyncio
    async def test_generate_use_rag_flag(self, broker):
        rag = MagicMock()
        rag.query = AsyncMock(return_value=MagicMock(
            final_context="",
            chunks=[],
            reranked_chunks=[],
            crag_assessment="correct"
        ))
        broker.rag_engine = rag
        result = await broker.generate_response("test", use_rag=True)
        rag.query.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_use_free_apis_flag(self, broker):
        mock_apis = MagicMock()
        mock_apis.search_wikipedia = AsyncMock(return_value={"error": "no results"})
        mock_apis.get_quote = AsyncMock(return_value={"error": "no results"})
        broker.free_apis = mock_apis
        result = await broker.generate_response("test", use_free_apis=True)
        assert result is not None
        mock_apis.search_wikipedia.assert_called_once()


class TestAIBrokerCloudCalls:
    @pytest.mark.asyncio
    async def test_get_cloud_key_no_env(self, broker):
        with patch.dict(os.environ, {}, clear=True):
            key = await broker._get_cloud_key()
            assert key == ""

    @pytest.mark.asyncio
    async def test_get_cloud_key_from_env(self, broker):
        with patch.dict(os.environ, {"ATENA_OPENROUTER_API_KEY": "sk-test-key"}):
            key = await broker._get_cloud_key()
            assert key == "sk-test-key"

    @pytest.mark.asyncio
    async def test_call_cloud_no_key(self):
        from ai_broker_v3 import AtenaAIBroker
        broker = AtenaAIBroker()
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="Chave OpenRouter ausente"):
                await broker._call_cloud("test")


class TestAIBrokerConcurrency:
    @pytest.mark.asyncio
    async def test_concurrent_calls_dont_corrupt_metrics(self, broker):
        async def make_call(i):
            return await broker.generate_response(f"test {i}")

        results = await asyncio.gather(*[make_call(i) for i in range(5)])
        assert len(results) == 5
        assert broker.metrics["total_requests"] == 5


class TestAIBrokerRAGQuery:
    @pytest.mark.asyncio
    async def test_perform_rag_query_no_engine(self, broker):
        result = await broker._perform_rag_query("test")
        assert result == "test"

    @pytest.mark.asyncio
    async def test_perform_rag_query_with_context(self, broker):
        from rag_engine import RAGResult, Chunk
        mock_result = MagicMock(spec=RAGResult)
        mock_result.final_context = "Contexto recuperado do RAG"
        mock_result.chunks = [Chunk(id="1", text="doc", source="s", score=0.9)]
        mock_result.reranked_chunks = []
        mock_result.crag_assessment = "correct"

        mock_rag = MagicMock()
        mock_rag.query = AsyncMock(return_value=mock_result)
        broker.rag_engine = mock_rag

        result = await broker._perform_rag_query("O que e Atena?")
        assert "O que e Atena?" in result
        assert "Contexto recuperado do RAG" in result

    @pytest.mark.asyncio
    async def test_perform_rag_query_empty_context(self, broker):
        from rag_engine import RAGResult
        mock_result = MagicMock(spec=RAGResult)
        mock_result.final_context = ""

        mock_rag = MagicMock()
        mock_rag.query = AsyncMock(return_value=mock_result)
        broker.rag_engine = mock_rag

        result = await broker._perform_rag_query("query")
        assert result == "query"

    @pytest.mark.asyncio
    async def test_perform_rag_query_error(self, broker):
        mock_rag = MagicMock()
        mock_rag.query = AsyncMock(side_effect=Exception("RAG error"))
        broker.rag_engine = mock_rag

        result = await broker._perform_rag_query("query")
        assert result == "query"


class TestAIBrokerEdgeCases:
    def test_broker_with_no_args(self):
        from ai_broker_v3 import AtenaAIBroker
        broker = AtenaAIBroker()
        assert broker is not None

    @pytest.mark.asyncio
    async def test_empty_prompt(self, broker):
        result = await broker.generate_response("")
        assert result is not None
        assert "content" in result

    @pytest.mark.asyncio
    async def test_long_prompt(self, broker):
        long_prompt = "test " * 1000
        result = await broker.generate_response(long_prompt)
        assert result is not None
        assert "content" in result


class TestAIBrokerMetrics:
    def test_metrics_isolated(self, broker):
        m1 = broker.get_metrics()
        m1["total_requests"] = 999
        m2 = broker.get_metrics()
        assert m2["total_requests"] == 0

    @pytest.mark.asyncio
    async def test_metrics_after_generation(self, broker):
        await broker.generate_response("test")
        metrics = broker.get_metrics()
        assert metrics["total_requests"] == 1
        assert metrics["avg_latency_ms"] >= 0


class TestAIBrokerIntegrationExternalMocked:
    @pytest.mark.asyncio
    async def test_full_pipeline_with_mocks(self):
        from ai_broker_v3 import AtenaAIBroker
        from rag_engine import RAGResult, Chunk

        mock_rag = MagicMock()
        mock_rag.query = AsyncMock(return_value=MagicMock(
            spec=RAGResult,
            final_context="RAG context data",
            chunks=[Chunk(id="1", text="doc", source="s", score=0.9)],
            reranked_chunks=[Chunk(id="1", text="doc", source="s", score=0.9)],
            crag_assessment="correct"
        ))

        mock_safety = MagicMock()
        mock_safety.check = AsyncMock(return_value="safe response")

        mock_apis = MagicMock()
        mock_apis.search_wikipedia = AsyncMock(return_value={"query": {"search": []}})
        mock_apis.get_quote = AsyncMock(return_value={})

        broker = AtenaAIBroker(
            rag_engine=mock_rag,
            safety_guard=mock_safety,
            free_apis=mock_apis,
        )

        result = await broker.generate_response(
            prompt="test",
            use_rag=True,
            use_free_apis=True,
        )

        assert result is not None
        assert "content" in result
        mock_rag.query.assert_called_once()
        mock_safety.check.assert_called_once()


if __name__ == "__main__":
    exit_code = pytest.main([__file__, "-v", "--tb=short", "-x"])
    print(f"\nResultado: {'PASS' if exit_code == 0 else 'FAIL'} (exit code: {exit_code})")
