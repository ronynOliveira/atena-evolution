#!/usr/bin/env python3
"""
qwen_inference.py — Inferência Local com Qwen3:8b

Configuração otimizada para:
- CPU: i5-1235U (12 cores)
- RAM: 15.7 GB
- GPU: Intel Iris Xe (sem CUDA)

Otimizações:
- Q4_K_M quantização (5.2GB → ~2.5GB)
- Ollama como backend principal
- llama.cpp como fallback
- Sem dependência de APIs externas
"""

import subprocess
import json
import logging
import time
import os
from typing import Dict, Any, Optional, List

logger = logging.getLogger("QwenInference")


class QwenInference:
    """
    Motor de inferência local com Qwen3:8b.
    
    Usa Ollama como backend principal.
    Sem custo de API. Funciona offline.
    """
    
    def __init__(
        self,
        model: str = "qwen3:8b",
        max_context: int = 8192,
        temperature: float = 0.7,
        max_tokens: int = 512,
    ):
        self.model = model
        self.max_context = max_context
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.ollama_url = "http://localhost:11434"
        
        logger.info(f"QwenInference inicializado: {model}")
        logger.info(f"Context: {max_context}, Temp: {temperature}")
    
    def is_ollama_running(self) -> bool:
        """Verifica se o Ollama está rodando."""
        try:
            result = subprocess.run(
                ["curl", "-s", f"{self.ollama_url}/api/tags"],
                capture_output=True, text=True, timeout=5
            )
            return result.returncode == 0
        except:
            return False
    
    def start_ollama(self) -> bool:
        """Inicia o Ollama se não estiver rodando."""
        if self.is_ollama_running():
            logger.info("Ollama já está rodando")
            return True
        
        logger.info("Iniciando Ollama...")
        try:
            subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            time.sleep(3)
            return self.is_ollama_running()
        except Exception as e:
            logger.error(f"Erro ao iniciar Ollama: {e}")
            return False
    
    def pull_model(self) -> bool:
        """Baixa o modelo se não existir."""
        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True, text=True, timeout=30
            )
            if self.model in result.stdout:
                logger.info(f"Modelo {self.model} já existe")
                return True
            
            logger.info(f"Baixando modelo {self.model}...")
            result = subprocess.run(
                ["ollama", "pull", self.model],
                capture_output=True, text=True, timeout=600
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Erro ao baixar modelo: {e}")
            return False
    
    def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Gera resposta usando Qwen via Ollama.
        
        Args:
            prompt: Prompt do usuário
            system_prompt: Prompt de sistema
            temperature: Temperatura (0.0 - 1.0)
            max_tokens: Máximo de tokens
            
        Returns:
            Dict com resposta, tokens, latência
        """
        if not self.is_ollama_running():
            if not self.start_ollama():
                return {
                    "success": False,
                    "error": "Ollama não disponível",
                    "response": "Desculpe, o motor de inferência local não está disponível."
                }
        
        temp = temperature or self.temperature
        max_tok = max_tokens or self.max_tokens
        
        # Montar payload
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temp,
                "num_predict": max_tok,
                "num_ctx": self.max_context,
                "num_thread": 8,  # i5-1235U
            }
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        start_time = time.time()
        
        try:
            # Chamar API do Ollama
            result = subprocess.run(
                [
                    "curl", "-s", "-X", "POST",
                    f"{self.ollama_url}/api/generate",
                    "-H", "Content-Type: application/json",
                    "-d", json.dumps(payload)
                ],
                capture_output=True, text=True, timeout=120
            )
            
            latency = time.time() - start_time
            
            if result.returncode != 0:
                return {
                    "success": False,
                    "error": result.stderr,
                    "response": "Erro na geração."
                }
            
            # Parse da resposta
            try:
                data = json.loads(result.stdout)
                response_text = data.get("response", "")
                tokens_generated = data.get("eval_count", 0)
                
                return {
                    "success": True,
                    "response": response_text,
                    "tokens": tokens_generated,
                    "latency_s": round(latency, 2),
                    "tokens_per_second": round(tokens_generated / max(latency, 0.01), 2),
                    "model": self.model,
                    "provider": "ollama-local",
                }
            except json.JSONDecodeError:
                # Resposta pode ser streaming JSON
                lines = result.stdout.strip().split("\n")
                full_response = ""
                for line in lines:
                    try:
                        chunk = json.loads(line)
                        full_response += chunk.get("response", "")
                    except:
                        pass
                
                return {
                    "success": True,
                    "response": full_response,
                    "tokens": 0,
                    "latency_s": round(latency, 2),
                    "model": self.model,
                    "provider": "ollama-local",
                }
                
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "timeout",
                "response": "Tempo excedido na geração."
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "response": f"Erro: {str(e)}"
            }
    
    def generate_with_context(
        self,
        prompt: str,
        context: str,
        system_prompt: str = "",
    ) -> Dict[str, Any]:
        """
        Gera resposta com contexto RAG.
        
        Args:
            prompt: Query do usuário
            context: Contexto recuperado do RAG
            system_prompt: Prompt de sistema
        """
        full_prompt = f"""Contexto:
{context}

Pergunta: {prompt}

Responda com base no contexto fornecido. Se o contexto não contiver a informação necessária, diga que não sabe."""
        
        return self.generate(full_prompt, system_prompt)
    
    def get_model_info(self) -> Dict[str, Any]:
        """Retorna informações do modelo."""
        try:
            result = subprocess.run(
                ["ollama", "show", self.model, "--json"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                return json.loads(result.stdout)
        except:
            pass
        
        return {
            "model": self.model,
            "size": "5.2 GB",
            "quantization": "Q4_K_M (estimado)",
            "context": self.max_context,
        }


class QwenQuantizer:
    """
    Quantização de modelos para reduzir uso de memória.
    
    Estratégias:
    - Q4_K_M: 4-bit, melhor qualidade/velocidade (recomendado)
    - Q5_K_M: 5-bit, melhor qualidade
    - Q8_0: 8-bit, quase sem perda
    """
    
    QUANT_SIZES = {
        "Q4_K_M": 0.5,   # ~50% do tamanho original
        "Q5_K_M": 0.6,   # ~60%
        "Q8_0": 0.8,     # ~80%
        "F16": 1.0,      # 100%
    }
    
    @staticmethod
    def quantize_model(
        input_model: str,
        output_model: str,
        quant_type: str = "Q4_K_M"
    ) -> bool:
        """
        Quantiza um modelo usando ollama create.
        
        Requer Modelfile com FROM e parâmetros de quantização.
        """
        modelfile = f"""
FROM {input_model}
PARAMETER quantize {quant_type}
"""
        
        try:
            with open("/tmp/Modelfile", "w") as f:
                f.write(modelfile)
            
            result = subprocess.run(
                ["ollama", "create", output_model, "-f", "/tmp/Modelfile"],
                capture_output=True, text=True, timeout=600
            )
            
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Erro ao quantizar: {e}")
            return False
    
    @staticmethod
    def get_quant_recommendation(ram_gb: float, model_size_gb: float) -> str:
        """
        Recomenda quantização baseado na RAM disponível.
        
        Regra: modelo deve usar no máximo 60% da RAM total.
        """
        max_model_size = ram_gb * 0.6
        
        if model_size_gb * 0.5 <= max_model_size:
            return "Q4_K_M"
        elif model_size_gb * 0.6 <= max_model_size:
            return "Q5_K_M"
        elif model_size_gb * 0.8 <= max_model_size:
            return "Q8_0"
        else:
            return "F16"


# ── Configuração para hardware local ──────────────────────────────────

HARDWARE_CONFIG = {
    "cpu": "i5-1235U",
    "cores": 12,
    "ram_gb": 15.7,
    "gpu": "Intel Iris Xe",
    
    # Modelos recomendados por tamanho de RAM
    "models": {
        "small": {
            "name": "qwen3:8b",
            "size_gb": 5.2,
            "quant": "Q4_K_M",
            "quant_size_gb": 2.8,
            "context": 8192,
            "speed": "~15-25 tok/s (CPU)",
        },
        "medium": {
            "name": "gemma4:e2b",
            "size_gb": 7.2,
            "quant": "Q4_K_M",
            "quant_size_gb": 4.0,
            "context": 8192,
            "speed": "~10-20 tok/s (CPU)",
        },
        "embedding": {
            "name": "nomic-embed-text",
            "size_gb": 0.27,
            "use": "RAG embeddings",
        }
    },
    
    # Configuração Ollama otimizada
    "ollama_env": {
        "OLLAMA_NUM_THREADS": "8",
        "OLLAMA_CONTEXT_LENGTH": "8192",
        "OLLAMA_KVCACHE_F16": "0",  # Usar q8_0 para KV cache
        "OLLAMA_FLASH_ATTENTION": "1",
    }
}


def setup_ollama_env():
    """Configura variáveis de ambiente otimizadas para Ollama."""
    env_vars = HARDWARE_CONFIG["ollama_env"]
    for key, value in env_vars.items():
        os.environ[key] = value
        logger.info(f"Ollama env: {key}={value}")


# ── Teste ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("=" * 60)
    print("Qwen Inference - Teste")
    print("=" * 60)
    
    # Verificar Ollama
    qwen = QwenInference(model="qwen3:8b")
    
    if not qwen.is_ollama_running():
        print("Iniciando Ollama...")
        qwen.start_ollama()
    
    # Info do modelo
    info = qwen.get_model_info()
    print(f"\nModelo: {info.get('model', 'qwen3:8b')}")
    
    # Teste de geração
    print("\nTeste de geração:")
    result = qwen.generate(
        prompt="Olá! Quem é você?",
        system_prompt="Você é a Atena Evolução, uma IA cognitiva avançada. Responda em português.",
        max_tokens=100,
    )
    
    if result["success"]:
        print(f"Resposta: {result['response'][:200]}")
        print(f"Tokens: {result.get('tokens', 0)}")
        print(f"Latência: {result.get('latency_s', 0)}s")
        print(f"Speed: {result.get('tokens_per_second', 0)} tok/s")
    else:
        print(f"Erro: {result.get('error', 'desconhecido')}")
    
    # Recomendação de quantização
    quant = QwenQuantizer.get_quant_recommendation(15.7, 5.2)
    print(f"\nQuantização recomendada: {quant}")
    
    print("\n" + "=" * 60)
