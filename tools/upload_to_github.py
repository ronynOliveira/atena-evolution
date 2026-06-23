"""
upload_to_github.py — Envia arquivos para o GitHub via API REST
Funciona com Fine-grained PATs que nao tem permissao de git push.

Uso:
  python upload_to_github.py
"""
import os
import sys
import json
import base64
import urllib.request
import urllib.error

# Token do cofre (GITHUB_TOKEN_WRITE) - obtido via script cofre.py
# Este token tem escopo repo completo e funciona para API REST
import subprocess as _sp
import sys as _sys
def _get_token():
    r = _sp.run([_sys.executable, r"C:\Users\dell-\AppData\Local\hermes\scripts\cofre.py",
                 "get", "GITHUB_TOKEN_WRITE", "--password", "EW8&mRwss%SH3E9ZFpj9e@#l"],
                capture_output=True, text=True, timeout=15)
    return r.stdout.strip().split(":", 1)[1].strip() if ":" in r.stdout.strip() else r.stdout.strip()

TOKEN = _get_token()
REPO = "ronynOliveira/atena-evolution"
BASE = r"C:\Users\dell-\AppData\Local\hermes\atena_evolution"

# Arquivos a ignorar
IGNORE = {".git", "__pycache__", ".pytest_cache", ".codegraph", "image_cache.db"}


def should_ignore(path, base):
    rel = os.path.relpath(path, base).replace("\\", "/")
    parts = rel.split("/")
    return any(p in IGNORE for p in parts)


def get_all_files(base):
    files = []
    for root, dirs, filenames in os.walk(base):
        dirs[:] = [d for d in dirs if d not in IGNORE]
        for f in filenames:
            full = os.path.join(root, f)
            if not should_ignore(full, base):
                rel = os.path.relpath(full, base).replace("\\", "/")
                files.append((rel, full))
    return files


def get_sha(path):
    """Obtem SHA do arquivo no GitHub."""
    req = urllib.request.Request(
        f"https://api.github.com/repos/{REPO}/contents/{path}",
        headers={"Authorization": f"token {TOKEN}"}
    )
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read())
        return data.get("sha")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def upload_file(rel_path, full_path):
    """Envia arquivo para o GitHub via API."""
    with open(full_path, "rb") as f:
        content = f.read()

    content_b64 = base64.b64encode(content).decode()
    sha = get_sha(rel_path)

    payload = {
        "message": f"Add {rel_path}",
        "content": content_b64
    }
    if sha:
        payload["sha"] = sha

    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"https://api.github.com/repos/{REPO}/contents/{rel_path}",
        data=data,
        headers={
            "Authorization": f"token {TOKEN}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json"
        },
        method="PUT"
    )
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        result = json.loads(resp.read())
        action = "UPDATE" if sha else "CREATE"
        print(f"  {action}: {rel_path} ({len(content)} bytes)")
        return True
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print(f"  ERRO: {rel_path} - {e.code} {error_body[:100]}")
        return False


def main():
    os.chdir(BASE)
    files = get_all_files(BASE)
    print(f"Enviando {len(files)} arquivos para {REPO}...\n")

    ok = 0
    fail = 0
    for rel_path, full_path in files:
        if upload_file(rel_path, full_path):
            ok += 1
        else:
            fail += 1

    print(f"\n=== Resultado: {ok} OK, {fail} ERRO ===")
    print(f"URL: https://github.com/{REPO}")


if __name__ == "__main__":
    main()
