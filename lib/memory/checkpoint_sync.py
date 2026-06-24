#!/usr/bin/env python3
"""
Koldi Checkpointing — Gerencia checkpoints de conversa via LangGraph + Postgres.
Permite continuidade de conversa entre instâncias local e nuvem.

Uso:
  python checkpoint_sync.py init          # Inicializa o banco de checkpoints
  python checkpoint_sync.py status       # Mostra estado dos checkpoints
  python checkpoint_sync.py list         # Lista checkpoints existentes
"""

import os
import sys
import json
from datetime import datetime

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "koldi_checkpoints",
    "user": "koldi",
    "password": "koldi_secure_2026",
}


def get_connection():
    """Retorna conexão com Postgres."""
    import psycopg2
    return psycopg2.connect(**DB_CONFIG)


def init_db():
    """Inicializa as tabelas de checkpoint."""
    conn = get_connection()
    cur = conn.cursor()
    
    # Tabela de checkpoints (compatível com LangGraph PostgresSaver)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS checkpoints (
            thread_id TEXT NOT NULL,
            checkpoint_id TEXT NOT NULL,
            parent_id TEXT,
            checkpoint BYTEA,
            metadata JSONB DEFAULT '{}',
            created_at TIMESTAMP DEFAULT NOW(),
            PRIMARY KEY (thread_id, checkpoint_id)
        )
    """)
    
    # Tabela de checkpoint writes
    cur.execute("""
        CREATE TABLE IF NOT EXISTS checkpoint_writes (
            thread_id TEXT NOT NULL,
            checkpoint_id TEXT NOT NULL,
            task_id TEXT NOT NULL,
            idx INTEGER NOT NULL,
            channel TEXT NOT NULL,
            type TEXT,
            value BYTEA,
            PRIMARY KEY (thread_id, checkpoint_id, task_id, idx)
        )
    """)
    
    # Tabela de checkpoint blobs
    cur.execute("""
        CREATE TABLE IF NOT EXISTS checkpoint_blobs (
            thread_id TEXT NOT NULL,
            checkpoint_id TEXT NOT NULL,
            channel TEXT NOT NULL,
            type TEXT,
            value BYTEA,
            PRIMARY KEY (thread_id, checkpoint_id, channel)
        )
    """)
    
    # Índices
    cur.execute("CREATE INDEX IF NOT EXISTS idx_checkpoints_thread ON checkpoints(thread_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_checkpoints_created ON checkpoints(created_at)")
    
    conn.commit()
    cur.close()
    conn.close()
    print("Banco de checkpoints inicializado com sucesso.")


def list_checkpoints():
    """Lista todos os checkpoints."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT thread_id, checkpoint_id, parent_id, created_at, metadata
        FROM checkpoints ORDER BY created_at DESC LIMIT 20
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    
    if not rows:
        print("Nenhum checkpoint encontrado.")
        return
    
    print(f"{'Thread ID':<40} {'Checkpoint':<40} {'Criado':<20}")
    print("-" * 100)
    for row in rows:
        thread_id, checkpoint_id, parent_id, created_at, metadata = row
        print(f"{thread_id:<40} {checkpoint_id:<40} {str(created_at):<20}")


def status():
    """Mostra status do banco de checkpoints."""
    conn = get_connection()
    cur = conn.cursor()
    
    cur.execute("SELECT COUNT(*) FROM checkpoints")
    total = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(DISTINCT thread_id) FROM checkpoints")
    threads = cur.fetchone()[0]
    
    cur.execute("SELECT pg_size_pretty(pg_database_size('koldi_checkpoints'))")
    size = cur.fetchone()[0]
    
    cur.close()
    conn.close()
    
    print(f"=== Koldi Checkpoint Status ===")
    print(f"  Total checkpoints: {total}")
    print(f"  Threads ativos:    {threads}")
    print(f"  Tamanho do banco:  {size}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python checkpoint_sync.py <init|status|list>")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "init":
        init_db()
    elif cmd == "status":
        status()
    elif cmd == "list":
        list_checkpoints()
    else:
        print(f"Comando desconhecido: {cmd}")
