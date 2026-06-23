"""
sync_c_to_g.py — Sincroniza C: (repo principal) -> G: (copia de trabalho)
Executar sempre que houver mudancas em C: ou antes de comecar a trabalhar.

Uso:
  python sync_c_to_g.py          # sincroniza C: -> G:
  python sync_c_to_g.py --check  # apenas verifica diferencas
"""
import os
import sys
import shutil
import filecmp
import time

C_PATH = r"C:\Users\dell-\AppData\Local\hermes\atena_evolution"
G_PATH = r"G:\Meu Drive\Koldi\atena_evolution"

# Arquivos/diretorios a ignorar
IGNORE = {".git", "__pycache__", ".pytest_cache", ".codegraph"}


def should_ignore(path, base):
    rel = os.path.relpath(path, base)
    parts = rel.replace("\\", "/").split("/")
    return any(p in IGNORE for p in parts)


def get_all_files(base):
    files = {}
    for root, dirs, filenames in os.walk(base):
        dirs[:] = [d for d in dirs if d not in IGNORE]
        for f in filenames:
            full = os.path.join(root, f)
            rel = os.path.relpath(full, base).replace("\\", "/")
            files[rel] = full
    return files


def sync(check_only=False):
    if not os.path.exists(C_PATH):
        print(f"ERRO: C: nao existe: {C_PATH}")
        sys.exit(1)

    os.makedirs(G_PATH, exist_ok=True)

    c_files = get_all_files(C_PATH)
    g_files = get_all_files(G_PATH) if os.path.exists(G_PATH) else {}

    to_copy = []
    to_delete = []

    # Arquivos que precisam ser copiados (novos ou modificados)
    for rel, c_full in c_files.items():
        g_full = os.path.join(G_PATH, rel)
        if rel not in g_files:
            to_copy.append((rel, c_full, g_full, "NOVO"))
        elif not os.path.exists(g_full):
            to_copy.append((rel, c_full, g_full, "FALTANDO"))
        else:
            c_mtime = os.path.getmtime(c_full)
            g_mtime = os.path.getmtime(g_full)
            if c_mtime > g_mtime:
                to_copy.append((rel, c_full, g_full, "ATUALIZAR"))

    # Arquivos que precisam ser deletados (existem em G mas nao em C)
    for rel in g_files:
        if rel not in c_files:
            to_delete.append((rel, os.path.join(G_PATH, rel)))

    if check_only:
        print(f"=== Verificacao C: -> G: ===")
        print(f"C: {len(c_files)} arquivos")
        print(f"G: {len(g_files)} arquivos")
        print(f"Copiar: {len(to_copy)}")
        print(f"Deletar: {len(to_delete)}")
        for rel, _, _, action in to_copy[:10]:
            print(f"  {action}: {rel}")
        for rel, _ in to_delete[:10]:
            print(f"  DELETAR: {rel}")
        if len(to_copy) > 10:
            print(f"  ... e mais {len(to_copy) - 10}")
        if len(to_delete) > 10:
            print(f"  ... e mais {len(to_delete) - 10}")
        return len(to_copy) + len(to_delete) == 0

    # Executar copia
    copied = 0
    for rel, c_full, g_full, action in to_copy:
        os.makedirs(os.path.dirname(g_full), exist_ok=True)
        shutil.copy2(c_full, g_full)
        copied += 1

    # Executar delecao
    deleted = 0
    for rel, g_full in to_delete:
        if os.path.exists(g_full):
            os.remove(g_full)
            deleted += 1

    # Limpar diretorios vazios em G:
    for root, dirs, files in os.walk(G_PATH, topdown=False):
        if root == G_PATH:
            continue
        if not dirs and not files:
            os.rmdir(root)

    print(f"Sincronizado: {copied} copiados, {deleted} deletados")
    return True


if __name__ == "__main__":
    check = "--check" in sys.argv
    sync(check_only=check)
