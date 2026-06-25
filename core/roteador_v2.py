#!/usr/bin/env python3
"""
Roteador Inteligente v2 - CPU-Optimized com RAG
================================================
Usa apenas gemma4:e2b + nomic-embed-text com:
- RAG local para compensar modelo menor
- Cache de respostas similares
- Classificacao de complexidade
- Fallback para modo detalhado
"""
import json
import os
import sys
import time
import hashlib
import logging
import urllib.request
import sqlite3
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from pathlib import Path

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
EMBED_MODEL = "nomic-embed-text:latest"
CHAT_MODEL = "gemma4:e2b"
REQUEST_TIMEOUT = int(os.environ.get("OLLAMA_TIMEOUT", "180"))
RAG_DB = os.path.join(os.path.dirname(__file__), "..", "rag_cache.db")

logger = logging.getLogger("RoteadorV2")


class RAGCache:
    """Cache RAG local com embeddings SQLite."""
    
    def __init__(self, db_path=RAG_DB):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS cache (
                question_hash TEXT PRIMARY KEY,
                question TEXT,
                answer TEXT,
                model TEXT,
                tokens INTEGER,
                tempo REAL,
                created_at REAL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS knowledge (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT,
                source TEXT,
                embedding TEXT
            )
        """)
        conn.commit()
        conn.close()
    
    def get_cached(self, question: str, max_age_hours=24) -> Optional[str]:
        """Retorna resposta cacheada se existir e ser recente."""
        qhash = hashlib.md5(question.lower().encode()).hexdigest()
        conn = sqlite3.connect(self.db_path)
        row = conn.execute(
            "SELECT answer, created_at FROM cache WHERE question_hash=?",
            (qhash,)
        ).fetchone()
        conn.close()
        
        if row:
            age_hours = (time.time() - row[1]) / 3600
            if age_hours < max_age_hours:
                return row[0]
        return None
    
    def save_cache(self, question: str, answer: str, model: str, tokens: int, tempo: float):
        """Salva resposta no cache."""
        qhash = hashlib.md5(question.lower().encode()).hexdigest()
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT OR REPLACE INTO cache VALUES (?, ?, ?, ?, ?, ?, ?)",
            (qhash, question, answer, model, tokens, tempo, time.time())
        )
        conn.commit()
        conn.close()
    
    def add_knowledge(self, content: str, source: str = "wiki"):
        """Adiciona documento ao conhecimento RAG."""
        # Gerar embedding via Ollama
        try:
            payload = json.dumps({
                "model": EMBED_MODEL,
                "prompt": content
            }).encode("utf-8")
            req = urllib.request.Request(
                f"{OLLAMA_URL}/api/embeddings",
                data=payload,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=300) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                embedding = json.dumps(result.get("embedding", []))
            
            conn = sqlite3.connect(self.db_path)
            conn.execute(
                "INSERT INTO knowledge (content, source, embedding) VALUES (?, ?, ?)",
                (content, source, embedding)
            )
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Erro adicionando conhecimento: {e}")
            return False
    
    def search_similar(self, question: str, top_k=3) -> List[str]:
        """Busca documentos similares por embedding."""
        try:
            # Gerar embedding da pergunta
            payload = json.dumps({
                "model": EMBED_MODEL,
                "prompt": question
            }).encode("utf-8")
            req = urllib.request.Request(
                f"{OLLAMA_URL}/api/embeddings",
                data=payload,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                q_embedding = result.get("embedding", [])
            
            if not q_embedding:
                return []
            
            # Buscar todos e calcular similaridade (cosine)
            conn = sqlite3.connect(self.db_path)
            rows = conn.execute("SELECT content, embedding FROM knowledge").fetchall()
            conn.close()
            
            scores = []
            for content, emb_json in rows:
                try:
                    emb = json.loads(emb_json)
                    score = self._cosine_similarity(q_embedding, emb)
                    scores.append((score, content))
                except:
                    continue
            
            scores.sort(reverse=True)
            return [content for _, content in scores[:top_k]]
        except Exception as e:
            logger.error(f"Erro na busca RAG: {e}")
            return []
    
    @staticmethod
    def _cosine_similarity(a: List[float], b: List[float]) -> float:
        """Calcula similaridade cosseno entre dois vetores."""
        if len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x**2 for x in a) ** 0.5
        norm_b = sum(x**2 for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)


class RoteadorInteligente:
    """Roteador otimizado para CPU com 2 modelos."""
    
    def __init__(self):
        self.cache = RAGCache()
        self.stats = {"cache_hits": 0, "rag_hits": 0, "ollama_calls": 0}
    
    def _detect_complexity(self, question: str) -> str:
        """Detecta complexidade da pergunta."""
        q = question.lower()
        palavras = q.split()
        
        if len(palavras) <= 5:
            return "simples"
        
        complexos = ["explique", "analise", "escreva", "desenvolva", "compare", "detalhe"]
        if any(w in q for w in complexos):
            return "complexa"
        
        return "media"
    
    def _build_rag_prompt(self, question: str) -> str:
        """Constroi prompt enriquecido com RAG."""
        # Buscar contexto similar
        contextos = self.cache.search_similar(question, top_k=2)
        
        if contextos:
            self.stats["rag_hits"] += 1
            contexto_text = "\n\n--- CONHECIONTO RELEVANTE ---\n"
            ctx_text += "\n".join(f"• {c[:200]}" for c in contextos)
            return f"{contexto_text}\n\n--- PERGUNTA ---\n{question}"
        
        return question
    
    def pergunte(self, question: str, detalhado: bool = False) -> Dict[str, Any]:
        """
        Processa pergunta com roteamento inteligente.
        
        Returns:
            dict com resposta, modelo, tempo, tokens, fonte
        """
        # 1. Verificar cache
        cached = self.cache.get_cached(question)
        if cached:
            self.stats["cache_hits"] += 1
            return {
                "resposta": cached,
                "modelo": "cache",
                "tempo": 0,
                "tokens": 0,
                "fonte": "cache"
            }
        
        # 2. Detectar complexidade
        complexidade = self._detect_complexity(question)
        
        # 3. Aplicar RAG se for complexa
        prompt = self._build_rag_prompt(question) if complexidade == "complexa" else question
        
        # 4. Ajustar parametros
        max_tokens = 1024 if detalhado or complexidade == "complexa" else 512
        temperature = 0.3 if complexidade == "simples" else 0.7
        
        # 5. Gerar resposta
        payload = json.dumps({
            "model": CHAT_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature,
                "num_ctx": 2048
            }
        }).encode("utf-8")
        
        req = urllib.request.Request(
            f"{OLLAMA_URL}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"}
        )
        
        start = time.time()
        try:
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                elapsed = time.time() - start
                answer = result.get("response", "")
                tokens = result.get("eval_count", 0)
                
                self.stats["ollama_calls"] += 1
                
                # Salvar no cache
                self.cache.save_cache(question, answer, CHAT_MODEL, tokens, elapsed)
                
                return {
                    "resposta": answer,
                    "modelo": CHAT_MODEL,
                    "tempo": elapsed,
                    "tokens": tokens,
                    "complexidade": complexidade,
                    "fonte": "ollama"
                }
        except Exception as e:
            return {
                "resposta": f"[ERRO] {str(e)[:100]}",
                "modelo": CHAT_MODEL,
                "tempo": time.time() - start,
                "tokens": 0,
                "erro": str(e)
            }
    
    def aprender(self, conteudo: str, fonte: str = "wiki"):
        """Adiciona conhecimento ao RAG."""
        return self.cache.add_knowledge(conteudo, fonte)
    
    def get_stats(self) -> Dict[str, Any]:
        """Estatisticas do roteador."""
        return {
            **self.stats,
            "modelo_principal": CHAT_MODEL,
            "modelo_embed": EMBED_MODEL,
            "rag_db": self.cache.db_path
        }


# ============================================================
# CLI
# ============================================================
if __name__ == "__main__":
    roteador = RoteadorInteligente()
    
    print("=" * 60)
    print("ROTEADOR INTELIGENTE v2 - CPU + RAG")
    print(f"Modelo: {CHAT_MODEL} | Embed: {EMBED_MODEL}")
    print("Digite 'sair' | 'stats' | 'aprender:texto'")
    print("=" * 60)
    
    while True:
        try:
            q = input("\nVoce: ").strip()
            if q.lower() == "sair":
                break
            if q.lower() == "stats":
                print(json.dumps(roteador.get_stats(), indent=2))
                continue
            if q.startswith("aprender:"):
                conteudo = q[9:]
                if roteador.aprender(conteudo):
                    print("[Aprendido]")
                continue
            
            if not q:
                continue
            
            resultado = roteador.pergunte(q)
            print(f"\nAtena ({resultado['modelo']}, {resultado['tempo']:.1f}s): {resultado['resposta']}")
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Erro: {e}")
