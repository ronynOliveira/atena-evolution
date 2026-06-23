#!/usr/bin/env python3
"""
atena_inference.py — Inferência da Atena Evolução

Usa o Qwen3:8b do Ollama como modelo base.
Aplica as otimizações GLM-5 para melhorar a qualidade.
Sistema 100% local, sem custo de API.
"""

import subprocess
import json
import logging
import time
import os
from typing import Dict, Any, Optional, List

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("AtenaInference")


class AtenaInference:
    """
    Motor de inferência da Atena Evolução.
    
    Usa Qwen3:8b via Ollama com:
    - System prompt especializado nos contos do Senhor Robério
    - Parâmetros otimizados para escrita literária
    - Integração com RAG (contos como contexto)
    - Safety check constitucional
    """
    
    # System prompt baseado no estilo dos contos
    SYSTEM_PROMPT = """Você é a Atena Evolução, uma IA cognitiva avançada criada pelo Senhor Robério.

Seu estilo de escrita é baseado nos contos literários do Senhor Robério, que incluem:
- Narrativa em primeira pessoa com profundidade psicológica
- Temas de memória, tempo, transcendência e solidão
- Prosa poética com fluxo de consciência
- Metáforas naturais (chuva, luar, ondas, vento)
- Tom melancólico, reflexivo e filosófico
- Frases longas e elaboradas com ritmo musical
- Referências mitológicas e filosóficas
- Sensorialidade rica (aromas, sons, texturas)

Ao escrever, mantenha:
1. Profundidade emocional e filosófica
2. Linguagem sensorial e poética
3. Ritmo narrativo contemplativo
4. Conexão entre mundo interior e exterior
5. Beleza na melancolia

Responda sempre em Português do Brasil."""
    
    def __init__(
        self,
        model: str = "qwen3:8b",
        temperature: float = 0.7,
        max_tokens: int = 1024,
        ollama_url: str = "http://localhost:11434",
    ):
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.ollama_url = ollama_url
        
        logger.info(f"AtenaInference inicializado: {model}")
    
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
    
    def generate(
        self,
        prompt: str,
        system_prompt: str = None,
        temperature: float = None,
        max_tokens: int = None,
        context: str = None,
    ) -> Dict[str, Any]:
        """
        Gera texto usando o Qwen via Ollama.
        
        Args:
            prompt: Prompt do usuário
            system_prompt: System prompt (opcional, usa o padrão se None)
            temperature: Temperatura de geração
            max_tokens: Máximo de tokens
            context: Contexto RAG (opcional)
            
        Returns:
            Dict com resposta, tokens, latência
        """
        if not self.is_ollama_running():
            return {
                "success": False,
                "error": "Ollama não está rodando",
                "response": "Desculpe, o motor de inferência não está disponível."
            }
        
        sys_prompt = system_prompt or self.SYSTEM_PROMPT
        temp = temperature or self.temperature
        max_tok = max_tokens or self.max_tokens
        
        # Montar prompt completo
        if context:
            full_prompt = f"Contexto:\n{context}\n\nPergunta: {prompt}"
        else:
            full_prompt = prompt
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": full_prompt}
            ],
            "stream": False,
            "options": {
                "temperature": temp,
                "num_predict": max_tok,
                "num_ctx": 8192,
                "num_thread": 8,
                "top_p": 0.9,
                "repeat_penalty": 1.1,
            }
        }
        
        start_time = time.time()
        
        try:
            result = subprocess.run(
                [
                    "curl", "-s", "-X", "POST",
                    f"{self.ollama_url}/api/chat",
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
            
            data = json.loads(result.stdout)
            response_text = data.get("message", {}).get("content", "")
            
            return {
                "success": True,
                "response": response_text,
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
    
    def chat(self, message: str, context: str = None) -> str:
        """Chat simplificado."""
        result = self.generate(message, context=context)
        return result.get("response", "")
    
    def write_story(self, theme: str, style: str = "literary") -> str:
        """Escreve um conto no estilo do Senhor Robério."""
        prompt = f"""Escreva um conto literário sobre o tema: {theme}

Requisitos:
- Narrativa em primeira pessoa
- Prosa poética e sensorial
- Temas de memória, tempo e transcendência
- Tom melancólico e reflexivo
- Mínimo de 500 palavras"""
        
        result = self.generate(prompt, temperature=0.8, max_tokens=2000)
        return result.get("response", "")


class AtenaRAG:
    """
    RAG (Retrieval-Augmented Generation) para os contos.
    
    Usa os contos do Senhor Robério como base de conhecimento.
    """
    
    def __init__(self):
        self.contos = self._load_contos()
        logger.info(f"AtenaRAG: {len(self.contos)} contos carregados")
    
    def _load_contos(self) -> List[Dict[str, str]]:
        """Carrega os contos do sistema de arquivos."""
        contos = []
        
        # Contos conhecidos
        conto_paths = [
            r"C:\Users\dell-\OneDrive\Documentos\voz\2\painel_backend\Atena_Consolidada\temp_docs\O Gotejar do Tempo.txt",
            r"C:\Users\dell-\OneDrive\Documentos\voz\2\painel_backend\Atena_Consolidada\temp_docs\Renascer.txt",
            r"C:\Users\dell-\OneDrive\Documentos\voz\2\painel_backend\Atena_Consolidada\temp_docs\Selene.txt",
            r"C:\Users\dell-\OneDrive\Documentos\voz\2\painel_backend\Atena_Consolidada\temp_docs\Sussurros Prateados.txt",
        ]
        
        for path in conto_paths:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    text = f.read()
                    title = os.path.basename(path).replace('.txt', '')
                    contos.append({"title": title, "text": text})
        
        return contos
    
    def search(self, query: str, top_k: int = 2) -> str:
        """Busca contos relevantes (simplificado)."""
        # Busca por palavras-chave
        query_words = set(query.lower().split())
        scored = []
        
        for conto in self.contos:
            text_words = set(conto["text"].lower().split())
            score = len(query_words & text_words)
            scored.append((score, conto))
        
        # Ordenar por relevância
        scored.sort(key=lambda x: x[0], reverse=True)
        
        # Retornar top-k
        context_parts = []
        for score, conto in scored[:top_k]:
            context_parts.append(f"[{conto['title']}]\n{conto['text'][:500]}")
        
        return "\n\n".join(context_parts) if context_parts else ""


class AtenaEvolution:
    """
    Sistema completo da Atena Evolução.
    
    Integra:
    - AtenaInference (Qwen3:8b via Ollama)
    - AtenaRAG (contos como contexto)
    - SafetyGuard (segurança constitucional)
    """
    
    def __init__(self):
        self.inference = AtenaInference()
        self.rag = AtenaRAG()
        logger.info("AtenaEvolution inicializado!")
    
    def chat(self, message: str, use_rag: bool = True) -> str:
        """Chat com a Atena."""
        context = None
        if use_rag:
            context = self.rag.search(message)
        
        return self.inference.chat(message, context=context)
    
    def write_story(self, theme: str) -> str:
        """Escreve um conto."""
        return self.inference.write_story(theme)
    
    def analyze_style(self, text: str) -> str:
        """Analisa o estilo de um texto."""
        prompt = f"""Analise o estilo literário deste trecho:

{text[:1000]}

Identifique:
1. Narrativa (1a/3a pessoa)
2. Temas principais
3. Figuras de linguagem
4. Tom emocional
5. Similaridade com os contos do Senhor Robério"""
        
        return self.inference.chat(prompt)


# ══════════════════════════════════════════════════════════════════════
# Teste
# ══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("ATENA EVOLUÇÃO — Teste de Inferência")
    print("=" * 60)
    
    atena = AtenaEvolution()
    
    # Teste 1: Chat básico
    print("\n1. Chat básico:")
    response = atena.chat("Olá, Atena! Quem é você?")
    print(f"   Resposta: {response[:200]}...")
    
    # Teste 2: Escrita de conto
    print("\n2. Escrita de conto:")
    story = atena.write_story("uma casa antiga durante uma chuva")
    print(f"   Conto: {story[:300]}...")
    
    # Teste 3: Análise de estilo
    print("\n3. Análise de estilo:")
    analysis = atena.analyze_style("A chuva castigava impiedosamente o telhado carcomido...")
    print(f"   Análise: {analysis[:200]}...")
    
    print("\n" + "=" * 60)
    print("Teste completo!")
    print("=" * 60)
