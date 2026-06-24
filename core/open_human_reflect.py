import os
import json
import sqlite3
import datetime
from pathlib import Path

# Paths
HERMES_HOME = Path("C:/Users/dell-/.hermes")
WIKI_PATH = Path("C:/Users/dell-/wiki")
WIKI_LOG = WIKI_PATH / "log.md"
WIKI_INDEX = WIKI_PATH / "index.md"
STATE_DB = HERMES_HOME / "state.db"
MEMORY_MD = HERMES_HOME / "memory" / "memory.md"

def get_recent_wiki_updates():
    """Read recent entries from wiki log."""
    if not WIKI_LOG.exists():
        return "Log da Wiki não encontrado."
    
    try:
        with open(WIKI_LOG, "r", encoding="utf-8") as f:
            lines = f.readlines()
            return "".join(lines[-20:]) # Get last 20 lines
    except Exception as e:
        return f"Erro ao ler log da Wiki: {e}"

def update_memory_with_wiki_map():
    """Update memory.md with current Wiki status."""
    if not WIKI_INDEX.exists():
        return
    
    try:
        with open(WIKI_INDEX, "r", encoding="utf-8") as f:
            content = f.read()
            # Extract total pages if present (e.g. "Total: 30 páginas")
            import re
            match = re.search(r"Total: (\d+) páginas", content)
            total = match.group(1) if match else "desconhecido"
            
        with open(MEMORY_MD, "r", encoding="utf-8") as f:
            mem_content = f.readlines()
            
        new_mem = []
        in_wiki_section = False
        for line in mem_content:
            if "## Camada de Conhecimento (Wiki)" in line:
                in_wiki_section = True
                new_mem.append(line)
                new_mem.append(f"- **Localização**: {WIKI_PATH}\n")
                new_mem.append(f"- **Status**: {total} páginas indexadas.\n")
                new_mem.append(f"- **Última Reflexão**: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
                continue
            
            if in_wiki_section and line.startswith("##"):
                in_wiki_section = False
            
            if not in_wiki_section:
                new_mem.append(line)
        
        # If section didn't exist, add it
        if "## Camada de Conhecimento (Wiki)" not in "".join(new_mem):
            new_mem.append("\n## Camada de Conhecimento (Wiki)\n")
            new_mem.append(f"- **Localização**: {WIKI_PATH}\n")
            new_mem.append(f"- **Status**: {total} páginas indexadas.\n")
            new_mem.append(f"- **Última Reflexão**: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n")

        with open(MEMORY_MD, "w", encoding="utf-8") as f:
            f.writelines(new_mem)
            
    except Exception as e:
        print(f"Erro ao atualizar memória com mapa da Wiki: {e}")

def main():
    print("⚕ Starting Hermes Open Human Reflection (Wiki Bridge)...")
    
    # 1. Update memory index with Wiki status
    update_memory_with_wiki_map()
    
    # 2. Get recent wiki activity for the agent to review
    wiki_activity = get_recent_wiki_updates()
    print("\n→ Recent Wiki Activity:")
    print(wiki_activity)
    
    # 3. Future improvement: Ingest wiki activity into a 'reflection_buffer' 
    # that the agent reads at start of session.
    
    print("\n✓ Wiki bridge updated. Memory layers synchronized.")

if __name__ == "__main__":
    main()
