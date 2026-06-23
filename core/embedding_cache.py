"""
embedding_cache.py — Cache persistente de embeddings via SQLite
Evita re-computação custosa. Funciona 100% offline.

Uso:
    from embedding_cache import EmbeddingCache
    cache = EmbeddingCache()
    emb = cache.get_or_compute("texto para embedding")
"""
import sqlite3
import json
import hashlib
import time
from pathlib import Path
from typing import Optional

OLLAMA_URL = "http://localhost:11434"
EMBED_MODEL = "nomic-embed-text"

class EmbeddingCache:
    """Cache persistente de embeddings usando SQLite."""
    
    def __init__(self, db_path: str = "embeddings_cache.db"):
        self.db_path = Path(db_path)
        self._init_db()
    
    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS embeddings (
                    text_hash TEXT PRIMARY KEY,
                    text_preview TEXT,
                    model TEXT,
                    embedding TEXT,
                    created_at REAL,
                    hit_count INTEGER DEFAULT 0
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_model ON embeddings(model)")
    
    def _hash(self, text: str, model: str) -> str:
        return hashlib.sha256(f"{model}::{text}".encode()).hexdigest()
    
    def get(self, text: str, model: str = EMBED_MODEL) -> Optional[list[float]]:
        """Busca embedding no cache."""
        key = self._hash(text, model)
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT embedding FROM embeddings WHERE text_hash = ?", (key,)
            ).fetchone()
            if row:
                conn.execute(
                    "UPDATE embeddings SET hit_count = hit_count + 1 WHERE text_hash = ?",
                    (key,)
                )
                return json.loads(row[0])
        return None
    
    def set(self, text: str, embedding: list[float], model: str = EMBED_MODEL):
        """Armazena embedding no cache."""
        key = self._hash(text, model)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO embeddings 
                (text_hash, text_preview, model, embedding, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (key, text[:200], model, json.dumps(embedding), time.time()))
    
    def _ollama_embed(self, text: str) -> list[float]:
        """Computa embedding via Ollama."""
        import urllib.request
        data = json.dumps({"model": EMBED_MODEL, "input": text}).encode()
        req = urllib.request.Request(
            f"{OLLAMA_URL}/api/embed", data=data,
            headers={"Content-Type": "application/json"}, method="POST"
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
            return result["embeddings"][0]
    
    def get_or_compute(self, text: str, model: str = EMBED_MODEL) -> list[float]:
        """Busca no cache ou computa e armazena."""
        cached = self.get(text, model)
        if cached:
            return cached
        embedding = self._ollama_embed(text)
        self.set(text, embedding, model)
        return embedding
    
    def stats(self) -> dict:
        """Estatísticas do cache."""
        with sqlite3.connect(self.db_path) as conn:
            total = conn.execute("SELECT COUNT(*) FROM embeddings").fetchone()[0]
            hits = conn.execute("SELECT SUM(hit_count) FROM embeddings").fetchone()[0] or 0
            size_mb = self.db_path.stat().st_size / 1024 / 1024 if self.db_path.exists() else 0
        return {"total_cached": total, "total_hits": hits, "db_size_mb": round(size_mb, 2)}


if __name__ == "__main__":
    cache = EmbeddingCache()
    
    # Teste
    test_text = "Inteligência artificial transforma a medicina"
    print(f"Testando cache para: '{test_text[:40]}...'")
    
    t0 = time.time()
    emb = cache.get_or_compute(test_text)
    first_time = time.time() - t0
    print(f"1a chamada: {len(emb)} dims em {first_time:.2f}s")
    
    t0 = time.time()
    emb2 = cache.get_or_compute(test_text)
    second_time = time.time() - t0
    print(f"2a chamada (cache): {len(emb2)} dims em {second_time:.2f}s")
    
    print(f"Speedup: {first_time/second_time:.1f}x")
    print(f"Stats: {cache.stats()}")
