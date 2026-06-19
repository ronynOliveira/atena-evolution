"""
store.py — Camada de persistência da Memória da Atena.

Duas tabelas centrais, espelhando a distinção episódica/semântica
da literatura cognitiva (Tulving, 1972) que a survey de memória de
agentes 2026 também usa como eixo organizador:

- episodic_memory: registros atômicos de interações (estilo A-MEM:
  notas atômicas com atributos, não um log cru).
- semantic_memory: fatos consolidados, gerados offline a partir de
  clusters de memórias episódicas relacionadas (estilo LightMem MTM/LTM).

Tudo em SQLite. Zero dependências externas. Zero rede.
"""

import sqlite3
import json
import time
from pathlib import Path
from typing import Optional, Iterator
from contextlib import contextmanager


SCHEMA = """
CREATE TABLE IF NOT EXISTS episodic_memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL,
    embedding TEXT NOT NULL,
    entities TEXT NOT NULL DEFAULT '[]',
    importance REAL NOT NULL DEFAULT 0.5,
    strength REAL NOT NULL DEFAULT 1.0,
    created_at REAL NOT NULL,
    last_accessed_at REAL NOT NULL,
    access_count INTEGER NOT NULL DEFAULT 0,
    session_id TEXT,
    promoted_to_semantic INTEGER NOT NULL DEFAULT 0,
    archived INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS semantic_memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fact TEXT NOT NULL,
    embedding TEXT NOT NULL,
    entities TEXT NOT NULL DEFAULT '[]',
    source_episodic_ids TEXT NOT NULL DEFAULT '[]',
    strength REAL NOT NULL DEFAULT 2.5,
    created_at REAL NOT NULL,
    last_accessed_at REAL NOT NULL,
    access_count INTEGER NOT NULL DEFAULT 0,
    superseded_by INTEGER
);

CREATE INDEX IF NOT EXISTS idx_episodic_archived ON episodic_memory(archived);
CREATE INDEX IF NOT EXISTS idx_episodic_promoted ON episodic_memory(promoted_to_semantic);
CREATE INDEX IF NOT EXISTS idx_episodic_last_accessed ON episodic_memory(last_accessed_at);
CREATE INDEX IF NOT EXISTS idx_semantic_superseded ON semantic_memory(superseded_by);
"""


class MemoryStore:
    """Persistência SQLite com WAL mode e transações explícitas."""

    def __init__(self, db_path: str = "atena_memory.db"):
        self.db_path = Path(db_path)
        with self._conn() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.executescript(SCHEMA)

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(str(self.db_path), timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # ---------- escrita: episódico ----------

    def add_episodic(
        self,
        content: str,
        embedding: list[float],
        entities: list[str],
        importance: float = 0.5,
        session_id: Optional[str] = None,
    ) -> int:
        now = time.time()
        with self._conn() as conn:
            cur = conn.execute(
                """INSERT INTO episodic_memory
                   (content, embedding, entities, importance, strength,
                    created_at, last_accessed_at, access_count, session_id)
                   VALUES (?, ?, ?, ?, 1.0, ?, ?, 0, ?)""",
                (content, json.dumps(embedding), json.dumps(entities),
                 importance, now, now, session_id),
            )
            return cur.lastrowid

    def add_semantic(
        self,
        fact: str,
        embedding: list[float],
        entities: list[str],
        source_episodic_ids: list[int],
        strength: float = 2.5,
    ) -> int:
        now = time.time()
        with self._conn() as conn:
            cur = conn.execute(
                """INSERT INTO semantic_memory
                   (fact, embedding, entities, source_episodic_ids, strength,
                    created_at, last_accessed_at, access_count)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 0)""",
                (fact, json.dumps(embedding), json.dumps(entities),
                 json.dumps(source_episodic_ids), strength, now, now),
            )
            new_id = cur.lastrowid
            # Marca memórias episódicas como promovidas
            if source_episodic_ids:
                placeholders = ",".join("?" * len(source_episodic_ids))
                conn.execute(
                    f"UPDATE episodic_memory SET promoted_to_semantic = 1 WHERE id IN ({placeholders})",
                    source_episodic_ids,
                )
            return new_id

    # ---------- leitura ----------

    def all_episodic(self, include_archived: bool = False) -> list[sqlite3.Row]:
        with self._conn() as conn:
            q = "SELECT * FROM episodic_memory"
            if not include_archived:
                q += " WHERE archived = 0"
            return conn.execute(q).fetchall()

    def all_semantic(self, include_superseded: bool = False) -> list[sqlite3.Row]:
        with self._conn() as conn:
            q = "SELECT * FROM semantic_memory"
            if not include_superseded:
                q += " WHERE superseded_by IS NULL"
            return conn.execute(q).fetchall()

    def count_episodic_active(self) -> int:
        """Conta memórias episódicas ativas sem carregar tudo em memória."""
        with self._conn() as conn:
            return conn.execute(
                "SELECT COUNT(*) FROM episodic_memory WHERE archived = 0"
            ).fetchone()[0]

    def count_semantic_active(self) -> int:
        """Conta memórias semânticas ativas sem carregar tudo em memória."""
        with self._conn() as conn:
            return conn.execute(
                "SELECT COUNT(*) FROM semantic_memory WHERE superseded_by IS NULL"
            ).fetchone()[0]

    # ---------- atualização (recall reforça memória — MemoryBank) ----------

    def reinforce_episodic(self, memory_id: int, new_strength: float) -> None:
        with self._conn() as conn:
            conn.execute(
                """UPDATE episodic_memory
                   SET strength = ?, last_accessed_at = ?, access_count = access_count + 1
                   WHERE id = ?""",
                (new_strength, time.time(), memory_id),
            )

    def reinforce_semantic(self, memory_id: int, new_strength: float) -> None:
        with self._conn() as conn:
            conn.execute(
                """UPDATE semantic_memory
                   SET strength = ?, last_accessed_at = ?, access_count = access_count + 1
                   WHERE id = ?""",
                (new_strength, time.time(), memory_id),
            )

    def update_episodic_strength_bulk(self, updates: list[tuple[int, float]]) -> None:
        """updates: lista de (id, nova_strength) — usado na manutenção/decay."""
        if not updates:
            return
        with self._conn() as conn:
            conn.executemany(
                "UPDATE episodic_memory SET strength = ? WHERE id = ?",
                [(s, i) for i, s in updates],
            )

    def archive_episodic(self, memory_ids: list[int]) -> None:
        if not memory_ids:
            return
        with self._conn() as conn:
            placeholders = ",".join("?" * len(memory_ids))
            conn.execute(
                f"UPDATE episodic_memory SET archived = 1 WHERE id IN ({placeholders})",
                memory_ids,
            )

    def supersede_semantic(self, old_id: int, new_id: int) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE semantic_memory SET superseded_by = ? WHERE id = ?",
                (new_id, old_id),
            )

    def stats(self) -> dict:
        with self._conn() as conn:
            ep_total = conn.execute("SELECT COUNT(*) FROM episodic_memory").fetchone()[0]
            ep_active = conn.execute("SELECT COUNT(*) FROM episodic_memory WHERE archived=0").fetchone()[0]
            sem_total = conn.execute("SELECT COUNT(*) FROM semantic_memory").fetchone()[0]
            sem_active = conn.execute("SELECT COUNT(*) FROM semantic_memory WHERE superseded_by IS NULL").fetchone()[0]
        return {
            "episodic_total": ep_total,
            "episodic_ativas": ep_active,
            "episodic_arquivadas": ep_total - ep_active,
            "semantic_total": sem_total,
            "semantic_ativas": sem_active,
        }
