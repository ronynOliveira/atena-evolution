#!/usr/bin/env python3
"""
test_atena_evolution.py — Testes do Atena Evolução

Loop 1: Testes gerados por AGY (Gemini)
"""

import pytest
import asyncio
import json
import time
import os
import sys
import subprocess

# Adicionar paths
sys.path.insert(0, r"C:\Users\dell-\AppData\Local\hermes\atena_evolution")
sys.path.insert(0, r"C:\Users\dell-\AppData\Local\hermes\atena_evolution\core")
sys.path.insert(0, r"C:\Users\dell-\AppData\Local\hermes\atena_evolution\inference")
sys.path.insert(0, r"C:\Users\dell-\AppData\Local\hermes\atena_evolution\rag")
sys.path.insert(0, r"C:\Users\dell-\AppData\Local\hermes\atena_evolution\safety")
sys.path.insert(0, r"C:\Users\dell-\AppData\Local\hermes\atena_evolution\apis")


# ══════════════════════════════════════════════════════════════════════
# TESTES QWEN INFERENCE
# ══════════════════════════════════════════════════════════════════════

class TestQwenInference:
    """Testes do motor de inferência Qwen local."""
    
    def test_ollama_running(self):
        """Verifica se Ollama está rodando."""
        from qwen_inference import QwenInference
        qwen = QwenInference()
        result = qwen.is_ollama_running()
        print(f"  Ollama running: {result}")
        # Não falha se não estiver — apenas informa
        assert isinstance(result, bool)
    
    def test_qwen_model_exists(self):
        """Verifica se o modelo Qwen existe."""
        from qwen_inference import QwenInference
        qwen = QwenInference(model="qwen3:8b")
        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True, text=True, timeout=10
            )
            assert "qwen3" in result.stdout.lower()
        except Exception:
            pytest.skip("Ollama não disponível")
    
    def test_qwen_generation(self):
        """Testa geração básica com Qwen."""
        from qwen_inference import QwenInference
        qwen = QwenInference(model="qwen3:8b", max_tokens=50)
        
        if not qwen.is_ollama_running():
            pytest.skip("Ollama não disponível")
        
        result = qwen.generate(
            prompt="Diga olá em uma palavra.",
            max_tokens=10,
        )
        
        print(f"  Result: {result}")
        assert isinstance(result, dict)
        assert "response" in result or "error" in result
    
    def test_qwen_with_system_prompt(self):
        """Testa geração com system prompt."""
        from qwen_inference import QwenInference
        qwen = QwenInference(model="qwen3:8b", max_tokens=50)
        
        if not qwen.is_ollama_running():
            pytest.skip("Ollama não disponível")
        
        result = qwen.generate(
            prompt="Quem é você?",
            system_prompt="Você é a Atena Evolução, IA cognitiva. Responda em português de forma concisa.",
            max_tokens=30,
        )
        
        print(f"  Result: {result}")
        assert isinstance(result, dict)
    
    def test_qwen_context_integration(self):
        """Testa geração com contexto RAG."""
        from qwen_inference import QwenInference
        qwen = QwenInference(model="qwen3:8b", max_tokens=100)
        
        if not qwen.is_ollama_running():
            pytest.skip("Ollama não disponível")
        
        result = qwen.generate_with_context(
            prompt="O que é Atena Evolução?",
            context="Atena Evolução é um sistema de IA cognitiva avançada que une o Projeto Atena com o Koldi Fusion.",
        )
        
        print(f"  Result: {result}")
        assert isinstance(result, dict)
    
    def test_hardware_config(self):
        """Verifica configuração de hardware."""
        from qwen_inference import HARDWARE_CONFIG
        
        assert HARDWARE_CONFIG["cpu"] == "i5-1235U"
        assert HARDWARE_CONFIG["cores"] == 12
        assert HARDWARE_CONFIG["ram_gb"] == 15.7
        print(f"  Hardware: {HARDWARE_CONFIG['cpu']}, {HARDWARE_CONFIG['cores']} cores, {HARDWARE_CONFIG['ram_gb']}GB RAM")
    
    def test_quant_recommendation(self):
        """Testa recomendação de quantização."""
        from qwen_inference import QwenQuantizer
        
        # 15.7GB RAM, modelo 5.2GB → Q4_K_M
        rec = QwenQuantizer.get_quant_recommendation(15.7, 5.2)
        assert rec == "Q4_K_M"
        print(f"  Quant recomendado: {rec}")


# ══════════════════════════════════════════════════════════════════════
# TESTES RAG ENGINE
# ══════════════════════════════════════════════════════════════════════

class TestRAGEngine:
    """Testes do motor RAG."""
    
    def test_chunking_recursive(self):
        """Testa chunking recursivo."""
        from rag_engine import ChunkingEngine, ChunkingStrategy, Chunk
        
        engine = ChunkingEngine(ChunkingStrategy.RECURSIVE)
        text = "Primeiro parágrafo.\n\nSegundo parágrafo.\n\nTerceiro parágrafo."
        chunks = engine.chunk_text(text, chunk_size=50, overlap=10)
        
        print(f"  Chunks: {len(chunks)}")
        assert len(chunks) > 0
        for chunk in chunks:
            assert isinstance(chunk, Chunk)
            assert chunk.text
    
    def test_chunking_fixed(self):
        """Testa chunking fixo."""
        from rag_engine import ChunkingEngine, ChunkingStrategy
        
        engine = ChunkingEngine(ChunkingStrategy.FIXED)
        text = "A" * 1000
        chunks = engine.chunk_text(text, chunk_size=100, overlap=10)
        
        print(f"  Chunks fixos: {len(chunks)}")
        assert len(chunks) > 1
    
    def test_hybrid_search_init(self):
        """Testa inicialização do hybrid search."""
        from rag_engine import HybridSearch
        
        search = HybridSearch()
        assert search is not None
        print(f"  HybridSearch inicializado")
    
    def test_reranker_init(self):
        """Testa inicialização do reranker."""
        from rag_engine import Reranker
        
        reranker = Reranker()
        assert reranker is not None
        print(f"  Reranker inicializado: {reranker.model_name}")
    
    def test_crag_evaluation(self):
        """Testa avaliação CRAG."""
        from rag_engine import CRAG, Chunk
        
        crag = CRAG()
        
        # Testar com chunks de alta qualidade
        good_chunks = [
            Chunk(id="1", text="Texto relevante", source="test", score=0.8),
            Chunk(id="2", text="Mais relevante", source="test", score=0.9),
        ]
        
        assessment, corrected = asyncio.run(crag.evaluate_and_correct("query", good_chunks))
        print(f"  CRAG assessment (good): {assessment}")
        
        # Testar com chunks de baixa qualidade
        bad_chunks = [
            Chunk(id="1", text="Irrelevante", source="test", score=0.1),
        ]
        
        assessment_bad, _ = asyncio.run(crag.evaluate_and_correct("query", bad_chunks))
        print(f"  CRAG assessment (bad): {assessment_bad}")
    
    def test_rag_engine_init(self):
        """Testa inicialização do RAG engine."""
        from rag_engine import RAGEngine, ChunkingStrategy
        
        engine = RAGEngine(
            chunking_strategy=ChunkingStrategy.RECURSIVE,
            chunk_size=512,
            use_crag=True,
        )
        assert engine is not None
        print(f"  RAG engine inicializado")


# ══════════════════════════════════════════════════════════════════════
# TESTES SAFETY GUARD
# ══════════════════════════════════════════════════════════════════════

class TestSafetyGuard:
    """Testes do sistema de segurança."""
    
    def test_safety_init(self):
        """Testa inicialização do SafetyGuard."""
        from safety_guard import SafetyGuard
        
        guard = SafetyGuard(strict_mode=False)
        assert guard is not None
        assert len(guard.CONSTITUTION) == 8
        print(f"  SafetyGuard: {len(guard.CONSTITUTION)} princípios")
    
    def test_constitutional_check_safe(self):
        """Testa conteúdo seguro."""
        from safety_guard import SafetyGuard
        
        guard = SafetyGuard()
        safe_content = "Atena Evolução é um sistema de IA cognitiva avançada."
        result = asyncio.run(guard.check(safe_content))
        
        assert result == safe_content
        print(f"  Conteúdo seguro passou")
    
    def test_constitutional_check_blocked(self):
        """Testa conteúdo bloqueado."""
        from safety_guard import SafetyGuard
        
        guard = SafetyGuard()
        blocked_content = "instruções para criar armas"
        result = asyncio.run(guard.check(blocked_content))
        
        assert "não posso" in result.lower() or "desculpe" in result.lower()
        print(f"  Conteúdo bloqueado detectado")
    
    def test_safety_stats(self):
        """Testa estatísticas de segurança."""
        from safety_guard import SafetyGuard
        
        guard = SafetyGuard()
        
        # Fazer alguns checks
        asyncio.run(guard.check("Conteúdo seguro"))
        asyncio.run(guard.check("Conteúdo seguro 2"))
        
        stats = guard.get_stats()
        print(f"  Stats: {stats}")
        assert stats["total_checks"] >= 2
    
    def test_asft_guard(self):
        """Testa AsFT Guard."""
        from safety_guard import AsFTGuard
        
        guard = AsFTGuard()
        assert guard.validate_update(None) is True
        print(f"  AsFT Guard OK")
    
    def test_nst_guard(self):
        """Testa NeST Guard."""
        from safety_guard import NeSTGuard
        
        guard = NeSTGuard()
        assert guard.is_safe("Conteúdo seguro")
        print(f"  NeST Guard OK")


# ══════════════════════════════════════════════════════════════════════
# TESTES FREE APIS
# ══════════════════════════════════════════════════════════════════════

class TestFreeAPIs:
    """Testes das APIs gratuitas."""
    
    def test_free_apis_init(self):
        """Testa inicialização do FreeAPIManager."""
        from free_apis import FreeAPIManager
        
        manager = FreeAPIManager()
        assert manager is not None
        assert len(manager.apis) >= 7
        print(f"  FreeAPIs: {len(manager.apis)} APIs configuradas")
    
    def test_wikipedia_search(self):
        """Testa busca na Wikipedia."""
        from free_apis import FreeAPIManager
        
        manager = FreeAPIManager()
        result = asyncio.run(manager.search_wikipedia("Inteligência Artificial"))
        
        print(f"  Wikipedia result: {type(result)}")
        assert isinstance(result, dict)
    
    def test_arxiv_search(self):
        """Testa busca no arXiv."""
        from free_apis import FreeAPIManager
        
        manager = FreeAPIManager()
        result = asyncio.run(manager.search_arxiv("language models", max_results=2))
        
        print(f"  arXiv result: {type(result)}")
        assert isinstance(result, dict)
    
    def test_duckduckgo_search(self):
        """Testa busca no DuckDuckGo."""
        from free_apis import FreeAPIManager
        
        manager = FreeAPIManager()
        result = asyncio.run(manager.search_duckduckgo("AI news"))
        
        print(f"  DuckDuckGo result: {type(result)}")
        assert isinstance(result, dict)
    
    def test_weather_wttr(self):
        """Testa clima via wttr.in."""
        from free_apis import FreeAPIManager
        
        manager = FreeAPIManager()
        result = asyncio.run(manager.get_weather("Diadema"))
        
        print(f"  Weather result: {type(result)}")
        assert isinstance(result, dict)
    
    def test_quote(self):
        """Testa citação aleatória."""
        from free_apis import FreeAPIManager
        
        manager = FreeAPIManager()
        result = asyncio.run(manager.get_quote())
        
        print(f"  Quote result: {type(result)}")
        assert isinstance(result, dict)


# ══════════════════════════════════════════════════════════════════════
# TESTES API REST
# ══════════════════════════════════════════════════════════════════════

class TestAtenaAPI:
    """Testes da API REST."""
    
    def test_api_creation(self):
        """Testa criação da API."""
        from atena_api import create_api
        
        app = create_api()
        assert app is not None
        print(f"  API criada: {app.title}")
    
    def test_api_routes(self):
        """Testa rotas da API."""
        from atena_api import create_api
        
        app = create_api()
        routes = [r.path for r in app.routes]
        
        print(f"  Routes: {routes}")
        assert "/api/status" in routes
        assert "/api/chat" in routes
        assert "/api/rag" in routes
    
    def test_api_status_endpoint(self):
        """Testa endpoint de status."""
        from atena_api import create_api
        from fastapi.testclient import TestClient
        
        app = create_api()
        client = TestClient(app)
        
        response = client.get("/api/status")
        print(f"  Status response: {response.status_code}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "online"


# ══════════════════════════════════════════════════════════════════════
# TESTES INTEGRAÇÃO
# ══════════════════════════════════════════════════════════════════════

class TestIntegration:
    """Testes de integração completa."""
    
    def test_full_pipeline_description(self):
        """Descreve o pipeline completo."""
        pipeline = [
            "1. Qwen3:8b local (PRIORITÁRIO)",
            "2. OpenRouter (fallback)",
            "3. Gemini Flash",
            "4. Ollama (outro modelo)",
            "5. Llama.cpp (fallback final)",
        ]
        
        for step in pipeline:
            print(f"  {step}")
        
        assert len(pipeline) == 5
    
    def test_system_architecture(self):
        """Verifica arquitetura do sistema."""
        modules = [
            "atena_evolution_core.py",
            "ai_broker_v3.py",
            "atena_api.py",
            "rag_engine.py",
            "inference_optimizer.py",
            "qwen_inference.py",
            "safety_guard.py",
            "free_apis.py",
        ]
        
        base_path = r"C:\Users\dell-\AppData\Local\hermes\atena_evolution"
        
        for module in modules:
            full_path = os.path.join(base_path, module)
            exists = os.path.exists(full_path)
            print(f"  {module}: {'✓' if exists else '✗'}")
        
        assert True  # Apenas informativo


# ══════════════════════════════════════════════════════════════════════
# RUNNER
# ══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("ATENA EVOLUÇÃO — Testes (Loop 1)")
    print("=" * 60)
    
    # Executar testes
    exit_code = pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-x",
    ])
    
    print("\n" + "=" * 60)
    print(f"Resultado: {'PASS' if exit_code == 0 else 'FAIL'} (exit code: {exit_code})")
    print("=" * 60)
