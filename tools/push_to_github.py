#!/usr/bin/env python3
"""Push para GitHub — execute quando tiver um Classic PAT com escopo repo."""
import subprocess, os, sys

token = sys.argv[1] if len(sys.argv) > 1 else ""
if not token:
    print("Uso: python push_to_github.py <CLASSIC_PAT>")
    sys.exit(1)

os.chdir(r"C:\Users\dell-\AppData\Local\hermes\atena_evolution")

# Remover credential helper
subprocess.run(["git", "config", "--global", "credential.helper", ""], capture_output=True)
subprocess.run(["git", "config", "credential.helper", ""], capture_output=True)

# Configurar remote
subprocess.run(["git", "remote", "remove", "origin"], capture_output=True)
subprocess.run(
    ["git", "remote", "add", "origin", f"https://{token}@github.com/ronynOliveira/atena-evolution.git"],
    capture_output=True
)

# Push
result = subprocess.run(["git", "push", "-u", "origin", "master"], capture_output=True, text=True)
print(result.stdout)
if result.stderr:
    print(result.stderr)
sys.exit(result.returncode)
