#!/usr/bin/env python3
"""
atena_evolution_app.py — Aplicação Principal da Atena Evolução

Integra todos os módulos:
- AtenaEvolutionCore (núcleo)
- AtenaAIBroker v3 (inferência)
- RAGEngine (RAG avançado)
- InferenceOptimizer (otimização)
- SafetyGuard (segurança)
- FreeAPIManager (APIs gratuitas)
- AtenaAPI (interface web)

Versão: 1.0.0
Data: 17/06/2026
"""

import logging
import asyncio
from typing import Optional
from pathlib import Path

logger = logging.getLogger("AtenaEvolutionApp")


class AtenaEvolutionApp:
    """
    Aplicação principal da Atena Evolução.
    
    Responsabilidades:
    1. Inicializar todos os módulos
    2. Conectar componentes
    3. Iniciar servidor API
    4. Gerenciar ciclo de vida
    """
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path
        self.core = None
        self.ai_broker = None
        self.rag_engine = None
        self.inference_optimizer = None
        self.safety_guard = None
        self.free_apis = None
        self.api = None
        self._initialized = False
        
        logger.info("AtenaEvolutionApp criado")
    
    async def initialize(self):
        """Inicializa todos os módulos."""
        logger.info("=" * 60)
        logger.info("Inicializando Atena Evolução v1.0...")
        logger.info("=" * 60)
        
        # 1. Safety Guard (primeiro, para proteger os demais)
        try:
            from safety.safety_guard import SafetyGuard
            self.safety_guard = SafetyGuard(strict_mode=False)
            logger.info("✅ SafetyGuard inicializado")
        except Exception as e:
            logger.warning(f"⚠️ SafetyGuard: {e}")
        
        # 2. Free APIs Manager
        try:
            from apis.free_apis import FreeAPIManager
            self.free_apis = FreeAPIManager()
            logger.info("✅ FreeAPIManager inicializado")
        except Exception as e:
            logger.warning(f"⚠️ FreeAPIManager: {e}")
        
        # 3. Inference Optimizer
        try:
            from inference.inference_optimizer import InferenceOptimizer, InferenceConfig
            config = InferenceConfig(
                engine="llama.cpp",
                model_format="GGUF_Q4_K_M",
                max_context=8192,
                speculative_decoding=True,
                kv_cache_compression=True,
            )
            self.inference_optimizer = InferenceOptimizer(config)
            logger.info("✅ InferenceOptimizer inicializado")
        except Exception as e:
            logger.warning(f"⚠️ InferenceOptimizer: {e}")
        
        # 4. RAG Engine
        try:
            from rag.rag_engine import RAGEngine, ChunkingStrategy
            self.rag_engine = RAGEngine(
                chunking_strategy=ChunkingStrategy.RECURSIVE,
                chunk_size=512,
                chunk_overlap=50,
                use_crag=True,
            )
            logger.info("✅ RAGEngine inicializado")
        except Exception as e:
            logger.warning(f"⚠️ RAGEngine: {e}")
        
        # 5. AI Broker v3
        try:
            from core.ai_broker_v3 import AtenaAIBroker
            self.ai_broker = AtenaAIBroker(
                evolution_core=self.core,
                free_apis=self.free_apis,
                safety_guard=self.safety_guard,
                qwen_inference=self.qwen_inference,
            )
            logger.info("✅ AtenaAIBroker v3 inicializado")
        except Exception as e:
            logger.warning(f"⚠️ AtenaAIBroker: {e}")
        
        # 5.5 Qwen Inference (motor local prioritário)
        try:
            from inference.qwen_inference import QwenInference, setup_ollama_env
            setup_ollama_env()
            self.qwen_inference = QwenInference(
                model="qwen3:8b",
                max_context=8192,
            )
            # Iniciar Ollama se necessário
            if not self.qwen_inference.is_ollama_running():
                logger.info("Iniciando Ollama...")
                self.qwen_inference.start_ollama()
            logger.info("✅ Qwen Inference inicializado (qwen3:8b)")
        except Exception as e:
            logger.warning(f"⚠️ Qwen Inference: {e}")
        
        # 6. Evolution Core
        try:
            from core.atena_evolution_core import AtenaEvolutionCore, EvolutionConfig
            config = EvolutionConfig()
            self.core = AtenaEvolutionCore(config)
            await self.core.initialize()
            logger.info("✅ AtenaEvolutionCore inicializado")
        except Exception as e:
            logger.warning(f"⚠️ AtenaEvolutionCore: {e}")
        
        # 7. API + Frontend
        try:
            from core.atena_api import create_api
            self.api = create_api(
                ai_broker=self.ai_broker,
                rag_engine=self.rag_engine,
                free_apis=self.free_apis,
                safety_guard=self.safety_guard,
            )
            logger.info("✅ AtenaAPI inicializado")
        except Exception as e:
            logger.warning(f"⚠️ AtenaAPI: {e}")
        
        self._initialized = True
        logger.info("=" * 60)
        logger.info("Atena Evolução v1.0 inicializada com sucesso!")
        logger.info("=" * 60)
    
    async def run(self, host: str = "127.0.0.1", port: int = 8000):
        """Inicia o servidor."""
        if not self._initialized:
            await self.initialize()
        
        if not self.api:
            logger.error("API não inicializada")
            return
        
        import uvicorn
        
        logger.info(f"Iniciando servidor em {host}:{port}")
        logger.info(f"Interface web: http://localhost:{port}/")
        logger.info(f"API docs: http://localhost:{port}/docs")
        
        config = uvicorn.Config(
            self.api,
            host=host,
            port=port,
            log_level="info",
        )
        server = uvicorn.Server(config)
        await server.serve()
    
    async def chat(self, message: str, use_rag: bool = False) -> str:
        """Chat direto via API interna."""
        if not self.ai_broker:
            return "Erro: AI Broker não inicializado"
        
        result = await self.ai_broker.generate_response(
            prompt=message,
            use_rag=use_rag,
        )
        
        if isinstance(result, dict):
            return result.get("content", "")
        return str(result)
    
    async def rag_query(self, query: str) -> str:
        """Query RAG direta."""
        if not self.rag_engine:
            return "Erro: RAG Engine não inicializado"
        
        from rag.rag_engine import RAGQuery
        result = await self.rag_engine.query(RAGQuery(text=query))
        return result.final_context
    
    def get_status(self) -> dict:
        """Status do sistema."""
        return {
            "initialized": self._initialized,
            "modules": {
                "core": self.core is not None,
                "ai_broker": self.ai_broker is not None,
                "rag_engine": self.rag_engine is not None,
                "inference_optimizer": self.inference_optimizer is not None,
                "safety_guard": self.safety_guard is not None,
                "free_apis": self.free_apis is not None,
                "api": self.api is not None,
            }
        }


# ── Entry Point ──────────────────────────────────────────────────────

async def main():
    """Função principal."""
    app = AtenaEvolutionApp()
    await app.initialize()
    
    # Mostrar status
    status = app.get_status()
    logger.info(f"Status: {status}")
    
    # Teste básico
    if app.ai_broker:
        result = await app.chat("Olá, Atena Evolução!")
        logger.info(f"Teste: {result}")
    
    # Iniciar servidor
    await app.run()


if __name__ == "__main__":
    asyncio.run(main())
