#!/usr/bin/env python3
"""
Koldi Integrity Verifier — Verifica integridade dos arquivos de identidade.
Baseado na auditoria de seguranca de Jun 2026.

Uso:
  python verify_integrity.py          # Verifica todos os arquivos
  python verify_integrity.py --update # Recalcula e atualiza checksums
"""

import hashlib
import os
import sys

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECKSUMS_FILE = os.path.join(_BASE, 'checksums.sha256')


def load_expected():
    expected = {}
    if not os.path.exists(CHECKSUMS_FILE):
        print("WARN: checksums.sha256 nao encontrado.")
        return None
    with open(CHECKSUMS_FILE, 'r') as f:
        for line in f:
            line = line.strip()
            if '  ' in line:
                h, name = line.split('  ', 1)
                expected[name] = h.upper()  # normalizar para maiusculas
    return expected


def sha256_file(path):
    with open(path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest().upper()  # maiusculas


def verify():
    expected = load_expected()
    if expected is None:
        return 2

    all_ok = True
    for name, exp_hash in expected.items():
        path = os.path.join(_BASE, name)
        if not os.path.exists(path):
            print(f"  MISSING: {name}")
            all_ok = False
            continue

        current = sha256_file(path)
        if current == exp_hash:
            print(f"  OK:   {name}")
        else:
            print(f"  FAIL: {name}")
            print(f"         esperado: {exp_hash}")
            print(f"         atual:   {current}")
            all_ok = False

    return 0 if all_ok else 1


def update():
    """Recalcula checksums de todos os arquivos de identidade."""
    files = [
        "IDENTITY/SOUL.md",
        "IDENTITY/HERMES.md",
        "IDENTITY/USER.md",
        "IDENTITY/TOOL_GUIDE.md",
        "SOUL.md",
        "USER.md",
        "MEMORY.md",
        "config.yaml",
    ]
    lines = []
    for name in files:
        path = os.path.join(_BASE, name)
        if os.path.exists(path):
            h = sha256_file(path)
            lines.append(f"{h}  {name}")
            print(f"  {name}: {h}")
        else:
            print(f"  MISSING: {name}")
    with open(CHECKSUMS_FILE, 'w') as f:
        f.write('\n'.join(lines) + '\n')
    print(f"\nChecksums atualizados em: {CHECKSUMS_FILE}")


if __name__ == '__main__':
    print("=== Koldi Integrity Check ===\n")

    if '--update' in sys.argv:
        print("Atualizando checksums...\n")
        update()
        sys.exit(0)

    rc = verify()
    if rc == 0:
        print("\n=== TODOS OS ARQUIVOS OK ===")
    elif rc == 1:
        print("\n=== ALERTA: ARQUIVOS MODIFICADOS ===")
        print("Se a modificacao nao foi autorizada pelo Senhor Roberio:")
        print("  1. Pare de operar imediatamente")
        print("  2. Verifique o conteudo dos arquivos marcados como FAIL")
        print("  3. Restaure a partir do backup")
    else:
        print("\n=== ERRO: checksums nao encontrados ===")
    sys.exit(rc)
