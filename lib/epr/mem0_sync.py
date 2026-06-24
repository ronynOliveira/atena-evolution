#!/usr/bin/env python3
"""
Koldi Mem0 Sync v2 — Sincroniza memória semântica via Mem0 v2 + Postgres/pgvector.
"""

import os, sys, json
from datetime import datetime

def load_env():
    paths = [
        '/root/.hermes/.env',
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'),
    ]
    for env_path in paths:
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        k, v = line.split('=', 1)
                        os.environ.setdefault(k.strip(), v.strip())
            break

load_env()
OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY", "")


def get_memory():
    from mem0 import Memory
    config = {
        "vector_store": {
            "provider": "pgvector",
            "config": {
                "host": "localhost", "port": 5432,
                "dbname": "koldi_checkpoints", "user": "koldi",
                "password": "koldi_secure_2026", "collection_name": "koldi_memories",
                "embedding_model_dims": 1536,
            }
        },
        "llm": {
            "provider": "openai",
            "config": {
                "model": "openrouter/owl-alpha",
                "api_key": OPENROUTER_KEY,
                "openai_base_url": "https://openrouter.ai/api/v1",
            }
        },
        "embedder": {
            "provider": "openai",
            "config": {
                "model": "text-embedding-3-small",
                "api_key": OPENROUTER_KEY,
                "openai_base_url": "https://openrouter.ai/api/v1",
            }
        }
    }
    return Memory.from_config(config)


def add_memory(text, user_id="koldi"):
    m = get_memory()
    return m.add(text, user_id=user_id)


def search_memories(query, user_id="koldi", limit=5):
    m = get_memory()
    return m.search(query, filters={"user_id": user_id}, limit=limit)


def get_all_memories(user_id="koldi"):
    m = get_memory()
    return m.get_all(filters={"user_id": user_id})


def export_memories(user_id="koldi"):
    memories = get_all_memories(user_id)
    return json.dumps(memories, ensure_ascii=False, indent=2, default=str)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python mem0_sync.py <add|search|export|stats> [args]")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "add":
        text = " ".join(sys.argv[2:])
        result = add_memory(text)
        adicionados = result.get('results', [])
        for item in adicionados:
            print(f"  + {item.get('memory', '?')[:80]}")

    elif cmd == "search":
        query = " ".join(sys.argv[2:])
        result = search_memories(query)
        items = result.get('results', result) if isinstance(result, dict) else result
        for item in items:
            if isinstance(item, dict):
                score = item.get('score', '?')
                mem = item.get('memory', str(item))[:100]
                print(f"  [{score:.2f}] {mem}")
            else:
                print(f"  - {item}")

    elif cmd == "export":
        print(export_memories())

    elif cmd == "stats":
        result = get_all_memories()
        items = result.get('results', result) if isinstance(result, dict) else result
        print(f"Total de memorias: {len(items)}")

    else:
        print(f"Comando desconhecido: {cmd}")
