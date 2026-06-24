#!/usr/bin/env python3
"""
Memory Consolidator — Periodic memory maintenance for Hermes.
Run daily to:
1. Apply score decay to old entries
2. Consolidate low-score entries
3. Update embeddings for semantic search
4. Report memory health stats
"""

import sys
from pathlib import Path

# Add lib to path
sys.path.insert(0, str(Path.home() / "AppData/Local/hermes/lib"))
sys.path.insert(0, str(Path.home() / "AppData" / "Local" / "hermes" / "lib"))

try:
    from memory_scorer import (
        ensure_dirs, decay_scores, get_consolidation_candidates,
        consolidate, update_embeddings, get_stats, print_tree
    )
except ImportError:
    # Try alternate path
    sys.path.insert(0, str(Path(__file__).parent / "lib"))
    from memory_scorer import (
        ensure_dirs, decay_scores, get_consolidation_candidates,
        consolidate, update_embeddings, get_stats, print_tree
    )


def main():
    print("🧠 Memory Care — Iniciando manutenção...")
    
    ensure_dirs()
    
    # Step 1: Apply score decay
    print("\n1. Aplicando decaimento de scores...")
    decayed = decay_scores()
    print(f"   {decayed} entradas com score ajustado")
    
    # Step 2: Update embeddings
    print("\n2. Atualizando embeddings...")
    embedded = update_embeddings()
    print(f"   {embedded} embeddings gerados/atualizados")
    
    # Step 3: Consolidate low-score entries
    print("\n3. Consolidando entradas de baixo score...")
    candidates = get_consolidation_candidates()
    print(f"   {len(candidates)} candidatos encontrados")
    if len(candidates) >= 2:
        n = min(len(candidates), 10)
        new_id = consolidate(candidates[:n])
        print(f"   {n} entradas consolidadas em: {new_id}")
    
    # Step 4: Stats
    print("\n4. Status do Memory Tree:")
    print_tree()
    
    stats = get_stats()
    print(f"\n   Resumo: {stats['total_entries']} entradas, "
          f"{stats['categories']} categorias, "
          f"score médio {stats['avg_score']}")
    print(f"   Ativas: {stats['active']} | Consolidadas: {stats['consolidated']}")
    
    print("\n✅ Memory Care concluído!")


if __name__ == "__main__":
    main()