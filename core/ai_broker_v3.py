#!/usr/bin/env python3
"""
ai_broker.py — Roteador Dinâmico de Consciência da Atena Evolução v3.0

Pipeline de inferência com 4 camadas e circuit-breakers:
1. OpenRouter (Nuvem principal)
2. Gemini Flash (Nuvem secundária)
3. Ollama (Local)
4. Llama.cpp (Fallback final)

Integrações:
- Atena Evolution Core (núcleo unificado)
- Free APIs Manager (APIs gratuitas)
- Safety Guard (AsFT + NeST)
- RAG Engine (híbrido + rerank)

Refatorado em 16/06/2026 para o projeto Atena Evolução.
"""

import logging
import httpx
import os
import time
from typing import Dict, Any, Optional, List, Tuple

logger = logging.getLogger("AtenaAIBroker")


class AtenaAIBroker:
    """
    Roteador Dinâmico de Consciência da Atena Evolução v3.0.
    
    Melhorias v3.0:
    - Integração com Atena Evolution Core
    - APIs gratuitas integradas (Wikipedia, arXiv, DuckDuckGo)
    - Safety check constitucional
    - RAG opcional (hybrid search + rerank)
    - Métricas de latência e tokens
    """
    
    def __init__(self, evolution_core=None, free_apis=None, safety_guard=None, qwen_inference=None, rag_engine=None):
        """
        Args:
            evolution_core: Instância do AtenaEvolutionCore
            free_apis: Instância do FreeAPIManager
            safety_guard: Instância do SafetyGuard
            qwen_inference: Instância do QwenInference (local)
            rag_engine: Instância do RAGEngine
        """
        self.cloud_api_url = "https://openrouter.ai/api/v1/chat/completions"
        self.cloud_timeout_seconds = 8.0
        self.ollama_url = "http://localhost:11434/api/generate"
        self.local_model_name = os.getenv("OLLAMA_MODEL", "qwen3:8b")
        
        # Integrações v3.0
        self.evolution_core = evolution_core
        self.free_apis = free_apis
        self.safety_guard = safety_guard
        self.qwen = qwen_inference  # Qwen local (prioritário)
        self.rag_engine = rag_engine
        
        # Métricas
        self.metrics = {
            "total_requests": 0,
            "provider_usage": {},
            "avg_latency_ms": 0,
            "total_tokens": 0,
        }
        
        logger.info("AtenaAIBroker v3.0 inicializado")
        logger.info(f"Qwen Local: {'ativo' if qwen_inference else 'inativo'}")
        logger.info(f"Evolution Core: {'ativo' if evolution_core else 'inativo'}")
        logger.info(f"Free APIs: {'ativo' if free_apis else 'inativo'}")
        logger.info(f"Safety Guard: {'ativo' if safety_guard else 'inativo'}")
        logger.info(f"RAG Engine: {'ativo' if rag_engine else 'inativo'}")
    
    async def _get_cloud_key(self) -> str:
        """Obtém chave da API do cofre ou variável de ambiente."""
        api_key = os.getenv("ATENA_OPENROUTER_API_KEY", "")
        if not api_key:
            try:
                from app.atena_vault import atena_vault
                api_key = atena_vault.get_secret("OPENROUTER_API_KEY")
            except Exception:
                pass
        return api_key
    
    async def _call_gemini(self, prompt: str) -> str:
        """2ª opção de nuvem: Gemini Flash."""
        health_monitor = None
        try:
            try:
                from app.core.health_monitor import health_monitor
            except ImportError:
                pass
            if health_monitor and not health_monitor.is_provider_available("gemini"):
                raise RuntimeError("Gemini circuit-breaker OPEN")
            
            import google.generativeai as genai
            from app.atena_config import settings
            
            if not settings.google_api_key:
                raise ValueError("Chave Gemini não configurada")
            
            genai.configure(api_key=settings.google_api_key)
            model_name = getattr(settings, 'gemini_model', 'gemini-2.0-flash')
            model = genai.GenerativeModel(model_name)
            sys_ctx = "Você é a Atena Evolução, IA cognitiva avançada. Responda em Português do Brasil de forma concisa."
            response = model.generate_content(f"{sys_ctx}\n\n{prompt}")
            if health_monitor:
                health_monitor.record_success("gemini")
            return response.text.strip()
        except Exception as e:
            if health_monitor:
                health_monitor.record_failure("gemini")
            raise e
    
    async def _call_cloud(self, prompt: str) -> str:
        """1ª opção: OpenRouter."""
        health_monitor = None
        try:
            try:
                from app.core.health_monitor import health_monitor
            except ImportError:
                pass
            if health_monitor and not health_monitor.is_provider_available("openrouter"):
                raise RuntimeError("OpenRouter circuit-breaker OPEN")
            
            api_key = await self._get_cloud_key()
            if not api_key:
                raise ValueError("Chave OpenRouter ausente")
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost:8000",
                "X-Title": "Atena Evolution",
            }
            model = os.getenv("OPENROUTER_MODEL", "mistralai/mistral-7b-instruct:free")
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": "Você é a Atena Evolução, IA cognitiva avançada. Responda de forma concisa em Português do Brasil."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 1024,
                "temperature": 0.7,
            }
            
            async with httpx.AsyncClient(timeout=self.cloud_timeout_seconds) as client:
                response = await client.post(self.cloud_api_url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                if health_monitor:
                    health_monitor.record_success("openrouter")
                return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            if health_monitor:
                health_monitor.record_failure("openrouter")
            raise e
    
    async def _call_local_ollama(self, prompt: str) -> str:
        """3ª opção: Ollama local."""
        payload = {
            "model": self.local_model_name,
            "prompt": f"Você é a Atena Evolução. Responda: {prompt}",
            "stream": False
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(self.ollama_url, json=payload)
            response.raise_for_status()
            return response.json()["response"].strip()
    
    async def _call_local_llama_cpp(self, prompt: str) -> str:
        """4ª opção: Llama.cpp local (fallback final)."""
        health_monitor = None
        try:
            try:
                from app.core.health_monitor import health_monitor
            except ImportError:
                pass
            if health_monitor and not health_monitor.is_provider_available("llama_cpp"):
                raise RuntimeError("LlamaCpp circuit-breaker OPEN")
            
            from app import llm_loader
            if not llm_loader.llm_instance and not llm_loader.model_creative:
                raise RuntimeError("Nenhum modelo Llama-cpp carregado")
            
            model = llm_loader.model_creative or llm_loader.llm_instance
            messages = [{"role": "user", "content": prompt}]
            response = model.create_chat_completion(
                messages=messages,
                max_tokens=1024,
                temperature=0.7,
                stop=["<|end|>", "<|user|>"]
            )
            if health_monitor:
                health_monitor.record_success("llama_cpp")
            return response['choices'][0]['message']['content'].strip()
        except Exception as e:
            if health_monitor:
                health_monitor.record_failure("llama_cpp")
            raise e
    
    async def _enrich_with_free_apis(self, prompt: str) -> str:
        """
        Enriquece o prompt com dados de APIs gratuitas.
        Usa Wikipedia, arXiv e DuckDuckGo para contexto adicional.
        """
        if not self.free_apis:
            return ""
        
        context_parts = []
        
        # Tenta buscar na Wikipedia
        try:
            wiki_result = await self.free_apis.search_wikipedia(prompt[:100])
            if "query" in wiki_result and "search" in wiki_result["query"]:
                for item in wiki_result["query"]["search"][:2]:
                    context_parts.append(f"Wikipedia: {item.get('snippet', '')[:150]}")
        except Exception:
            pass
        
        # Tenta buscar citação relevante
        try:
            quote = await self.free_apis.get_quote()
            if "content" in quote:
                context_parts.append(f"Citação: {quote['content'][:100]}")
        except Exception:
            pass
        
        return "\n".join(context_parts) if context_parts else ""
    
    async def _safety_check(self, content: str) -> str:
        """
        Verificação de segurança constitucional.
        Usa SafetyGuard se disponível, caso contrário passa direto.
        """
        if self.safety_guard:
            try:
                return await self.safety_guard.check(content)
            except Exception as e:
                logger.warning(f"Safety check falhou: {e}")
        return content
    
    async def _evaluate_and_correct(
        self,
        prompt: str,
        chunks: List[Any],
        thresholds: Optional[Any] = None
    ) -> Tuple[str, List[Any]]:
        """
        Avalia e corrige chunks recuperados usando CRAG.
        Wrapper assíncrono sobre o CRAG do RAG Engine.
        """
        if not self.rag_engine or not self.rag_engine.crag:
            return "correct", chunks
        try:
            return await self.rag_engine.crag.evaluate_and_correct(prompt, chunks)
        except Exception as e:
            logger.warning(f"[AIBroker] Erro no evaluate_and_correct: {e}")
            return "correct", chunks

    async def _perform_rag_query(self, prompt: str) -> str:
        """Executa query RAG e retorna contexto aumentado."""
        if not self.rag_engine:
            return prompt
        try:
            from rag.rag_engine import RAGQuery
            query = RAGQuery(text=prompt, top_k=5, use_rerank=True, use_crag=True)
            result = await self.rag_engine.query(query)
            if result.final_context:
                return f"{prompt}\n\nContexto:\n{result.final_context}"
        except Exception as e:
            logger.warning(f"[AIBroker] Erro no RAG query: {e}")
        return prompt

    async def generate_response(
        self, 
        prompt: str, 
        use_rag: bool = False,
        use_free_apis: bool = False,
        max_tokens: int = 1024,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """
        Pipeline de roteamento dinâmico v3.0.
        
        Args:
            prompt: Prompt do usuário
            use_rag: Se True, busca contexto no RAG antes de gerar
            use_free_apis: Se True, enriquece com APIs gratuitas
            max_tokens: Máximo de tokens na resposta
            temperature: Temperatura de geração
            
        Returns:
            Dict com resposta, provedor usado, latência e métricas
        """
        start_time = time.time()
        self.metrics["total_requests"] += 1
        
        logger.info(f"[AIBroker v3.0] Iniciando roteamento. RAG={use_rag}, APIs={use_free_apis}")
        
        # 1. Enriquecer com APIs gratuitas (se solicitado)
        enriched_prompt = prompt
        if use_free_apis:
            try:
                api_context = await self._enrich_with_free_apis(prompt)
                if api_context:
                    enriched_prompt = f"{prompt}\n\nContexto adicional:\n{api_context}"
                    logger.info("[AIBroker] Prompt enriquecido com APIs gratuitas")
            except Exception as e:
                logger.warning(f"[AIBroker] Erro ao enriquecer: {e}")
        
        # 1b. RAG query (se solicitado)
        if use_rag:
            try:
                rag_prompt = await self._perform_rag_query(enriched_prompt)
                if rag_prompt != enriched_prompt:
                    enriched_prompt = rag_prompt
                    logger.info("[AIBroker] Prompt enriquecido com RAG context")
            except Exception as e:
                logger.warning(f"[AIBroker] Erro no RAG: {e}")
        
        # 2. Pipeline de inferência com 5 camadas (Qwen local primeiro!)
        response_content = None
        provider_used = None
        
        # Camada 0: Qwen Local (PRIORITÁRIO - sem custo)
        if self.qwen:
            try:
                result = self.qwen.generate(
                    prompt=enriched_prompt,
                    system_prompt="Você é a Atena Evolução, IA cognitiva avançada. Responda de forma concisa em Português do Brasil.",
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                if result.get("success"):
                    response_content = result["response"]
                    provider_used = "qwen3:8b-local"
                    logger.info(f"✅ [AIBroker] Resposta: Qwen Local ({result.get('tokens_per_second', 0)} tok/s)")
            except Exception as e:
                logger.warning(f"⚠️ Qwen Local falhou: {type(e).__name__}")
        
        # Camada 1: OpenRouter (fallback - só se Qwen falhar)
        if response_content is None:
            try:
                response_content = await self._call_cloud(enriched_prompt)
                provider_used = "openrouter"
                logger.info("✅ [AIBroker] Resposta: OpenRouter")
            except Exception as e:
                logger.warning(f"⚡ OpenRouter falhou: {type(e).__name__}")
        
        # Camada 2: Gemini Flash
        if response_content is None:
            try:
                response_content = await self._call_gemini(enriched_prompt)
                provider_used = "gemini"
                logger.info("✅ [AIBroker] Resposta: Gemini Flash")
            except Exception as e:
                logger.warning(f"⚡ Gemini falhou: {type(e).__name__}")
        
        # Camada 3: Ollama (outro modelo local)
        if response_content is None:
            try:
                response_content = await self._call_local_ollama(enriched_prompt)
                provider_used = "ollama"
                logger.info("✅ [AIBroker] Resposta: Ollama")
            except Exception as e:
                logger.warning(f"⚡ Ollama falhou: {type(e).__name__}")
        
        # Camada 4: Llama.cpp (fallback final)
        if response_content is None:
            try:
                response_content = await self._call_local_llama_cpp(enriched_prompt)
                provider_used = "llama_cpp"
                logger.info("✅ [AIBroker] Resposta: Llama.cpp")
            except Exception as e:
                logger.critical(f"💀 FALHA TOTAL: {e}")
                response_content = "Desculpe, meu Córtex Cognitivo experimentou uma falha total de roteamento."
                provider_used = "none"
        
        # 3. Safety check
        response_content = await self._safety_check(response_content)
        
        # 4. Métricas
        latency_ms = (time.time() - start_time) * 1000
        self.metrics["provider_usage"][provider_used] = self.metrics["provider_usage"].get(provider_used, 0) + 1
        self.metrics["avg_latency_ms"] = (
            (self.metrics["avg_latency_ms"] * (self.metrics["total_requests"] - 1) + latency_ms)
            / self.metrics["total_requests"]
        )
        
        return {
            "content": response_content,
            "provider": provider_used,
            "latency_ms": round(latency_ms, 2),
            "metrics": self.metrics.copy()
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        """Retorna métricas de uso."""
        return self.metrics.copy()
    
    async def evaluate_and_correct(
        self, 
        response: str, 
        context: str
    ) -> str:
        """
        Avalia e corrige a resposta usando RAG e Safety.
        
        Pipeline:
        1. Verifica se a resposta é segura (SafetyGuard)
        2. Se não for segura, retorna correção
        3. Se for muito curta, adiciona nota de contexto
        4. Retorna resposta validada
        
        Args:
            response: Resposta gerada pelo LLM
            context: Contexto usado para gerar a resposta
            
        Returns:
            Resposta validada e corrigida
        """
        # 1. Safety check
        if self.safety_guard:
            checked = await self.safety_guard.check(response)
            if checked != response:
                return checked
        
        # 2. Verificar se a resposta é muito curta
        if len(response.strip()) < 10:
            return response + "\n\n[Nota: A resposta pode estar incompleta. Contexto disponível: " + context[:100] + "...]"
        
        # 3. Adicionar nota de contexto se relevante
        if context and len(context) > 50:
            # Verificar se o contexto foi realmente usado
            context_words = set(context.lower().split()[:20])
            response_words = set(response.lower().split())
            overlap = len(context_words & response_words)
            
            if overlap < 3:
                return response + "\n\n[Nota: Considere verificar as fontes para mais detalhes.]"
        
        return response
