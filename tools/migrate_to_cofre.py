#!/usr/bin/env python3
"""
Koldi's Cofre — Script de Migração Única
Importa todas as variáveis sensíveis do .env para o cofre criptografado.
Requer senha mestra uma única vez.

Uso: python scripts/migrate_to_cofre.py [--password SENHA]
  Se --password não for fornecido, será solicitado interativamente.
  
  Exemplos:
    python scripts/migrate_to_cofre.py
    python scripts/migrate_to_cofre.py --password "minha_senha_secreta"
"""

import argparse
import base64
import getpass
import hashlib
import json
import os
import sys
from pathlib import Path

HERMES = Path.home() / "AppData/Local/hermes"
ENV_FILE = HERMES / ".env"
COFRE_FILE = HERMES / "cofre" / "vault.enc"
SALT_FILE = HERMES / "cofre" / "vault.salt"
STATE_FILE = HERMES / "cofre" / "vault.state"

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
except ImportError:
    os.system("pip install cryptography -q")
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


# Chaves SENSÍVEIS que devem ir para o cofre (não ficar no .env)
SENSITIVE_KEYS = [
    "OPENROUTER_API_KEY",
    "GOOGLE_API_KEY",
    "GEMINI_API_KEY",
    "TELEGRAM_BOT_TOKEN",
    "NVIDIA_API_KEY",
    "KILOCODE_API_KEY",
    "SUPERMEMORY_API_KEY",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "DEEPSEEK_API_KEY",
    "XAI_API_KEY",
    "COPILOT_GITHUB_TOKEN",
    "GROQ_API_KEY",
    "MISTRAL_API_KEY",
    "ELEVENLABS_API_KEY",
    "COMPOSIO_API_KEY",
    "BROWSERBASE_API_KEY",
    "BROWSERBASE_PROJECT_ID",
    "FIRECRAWL_API_KEY",
    "TAVILY_API_KEY",
    "EXA_API_KEY",
    "JINA_API_KEY",
    "HF_TOKEN",
    "GITHUB_TOKEN",
]


def derive_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=600000)
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def read_env() -> dict:
    """Lê o arquivo .env e retorna dict de variáveis."""
    if not ENV_FILE.exists():
        print(f"❌ .env não encontrado em: {ENV_FILE}")
        return {}
    
    env_vars = {}
    with open(ENV_FILE, encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip("\"'")
            env_vars[key] = val
    
    return env_vars


def filter_sensitive(env_vars: dict) -> dict:
    """Filtra apenas variáveis sensíveis."""
    sensitive = {}
    for key in SENSITIVE_KEYS:
        if key in env_vars:
            # Oculta parte do valor pra mostrar preview
            val = env_vars[key]
            preview = val[:6] + "..." + val[-4:] if len(val) > 12 else val[:6] + "..."
            sensitive[key] = {"value": val, "preview": preview}
    return sensitive


def main():
    parser = argparse.ArgumentParser(description="Migrar .env para o cofre")
    parser.add_argument("--password", "-p", help="Senha mestra (opcional, se não fornecida será solicitada)")
    args = parser.parse_args()
    
    print("🔐 Koldi's Cofre — Migração Única")
    print("=" * 50)
    
    # 1. Ler .env
    print("\n📖 Lendo .env...")
    all_vars = read_env()
    if not all_vars:
        return
    
    sensitive = filter_sensitive(all_vars)
    if not sensitive:
        print("✅ Nenhuma chave sensível encontrada no .env.")
        return
    
    print(f"\n🔑 Chaves sensíveis encontradas ({len(sensitive)}):")
    for key, info in sorted(sensitive.items()):
        print(f"  • {key}: {info['preview']}")
    
    # 2. Verificar se cofre já existe
    if COFRE_FILE.exists():
        print("\n🔓 Cofre já existe. Vamos usá-lo.")
        senha = args.password or getpass.getpass("Digite a SENHA MESTRA do cofre: ")
        
        state = json.loads(STATE_FILE.read_text())
        if hash_password(senha) != state.get("password_hash", ""):
            print("❌ Senha incorreta.")
            return
        
        salt = SALT_FILE.read_bytes()
        key = derive_key(senha, salt)
        cipher = Fernet(key)
        
        # Descriptografar dados existentes
        encrypted = COFRE_FILE.read_bytes()
        decrypted = cipher.decrypt(encrypted)
        data = json.loads(decrypted.decode())
        
    else:
        print("\n🆕 Cofre novo. Vamos criar.")
        if args.password:
            senha = args.password
        else:
            senha1 = getpass.getpass("Digite a SENHA MESTRA: ")
            senha2 = getpass.getpass("Confirme a senha: ")
            if senha1 != senha2:
                print("❌ Senhas não conferem.")
                return
            if len(senha1) < 6:
                print("❌ Senha muito curta (mínimo 6 caracteres).")
                return
            senha = senha1
        
        data = {}
        
        # Criar cofre
        (HERMES / "cofre").mkdir(parents=True, exist_ok=True)
        salt = os.urandom(16)
        SALT_FILE.write_bytes(salt)
        
        # Salvar hash
        state = {"password_hash": hash_password(senha), "locked": False}
        STATE_FILE.write_text(json.dumps(state, indent=2))
        
        key = derive_key(senha, salt)
        cipher = Fernet(key)
    
    # 3. Migrar chaves
    print("\n📦 Migrando chaves para o cofre...")
    imported = 0
    for key, info in sorted(sensitive.items()):
        data[f"env_{key.lower()}"] = info["value"]
        imported += 1
        print(f"  ✅ {key}")
    
    # 4. Criptografar e salvar
    new_encrypted = cipher.encrypt(json.dumps(data).encode())
    COFRE_FILE.write_bytes(new_encrypted)
    
    # 5. Limpar .env (remover linhas sensíveis)
    print(f"\n🧹 Limpando {imported} chaves do .env...")
    with open(ENV_FILE, encoding="utf-8") as f:
        lines = f.readlines()
    
    clean_lines = []
    removed = 0
    for line in lines:
        stripped = line.strip()
        key = stripped.split("=")[0].strip() if "=" in stripped else ""
        if key in SENSITIVE_KEYS:
            clean_lines.append(f"# {stripped}  # MOVIDO PARA O COFRE\n")
            removed += 1
        else:
            clean_lines.append(line)
    
    with open(ENV_FILE, "w", encoding="utf-8") as f:
        f.writelines(clean_lines)
    
    print(f"\n✅ Migração concluída!")
    print(f"  • {imported} chaves guardadas no cofre")
    print(f"  • {removed} linhas comentadas no .env")
    print(f"  • Cofre: {COFRE_FILE}")
    print(f"\n📌 Para recuperar: python scripts/cofre.py get env_<chave>")


if __name__ == "__main__":
    main()