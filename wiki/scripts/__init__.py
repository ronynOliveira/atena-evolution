#!/usr/bin/env python3
"""
Módulo compartilhado do OWL - Utilitários comuns.
Centraliza funções duplicadas dos scripts de tools.

Autor: OWL (Batedor da Nuvem)
Data: 2026-05-20
"""

import subprocess
import sys
import os
import json
import hashlib
import time
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

OLLAMA_URL = "http://127.0.0.1:11434"
DEFAULT_MODEL = "qwen3:8b"

# ═══════════════════════════════════════════
# SUBPROCESS
# ═══════════════════════════════════════════

def run_cmd(cmd: str | list, timeout: int = 60, **kwargs) -> str:
    """Executa comando e retorna output. Suporta string (shell=True) ou lista (shell=False)."""
    try:
        if isinstance(cmd, list):
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, **kwargs)
        else:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout, **kwargs)
        return result.stdout.strip() if result.returncode == 0 else ""
    except subprocess.TimeoutExpired:
        return ""
    except Exception:
        return ""


# ═══════════════════════════════════════════
# OLLAMA
# ═══════════════════════════════════════════

def ollama_chat(model: str, prompt: str, system: str = "", temperature: float = 0.1, timeout: int = 60) -> str:
    """Envia prompt para modelo Ollama e retorna resposta."""
    try:
        import urllib.request
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        data = json.dumps({
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": False
        }).encode("utf-8")

        req = urllib.request.Request(
            f"{OLLAMA_URL}/api/chat",
            data=data,
            headers={"Content-Type": "application/json"}
        )
        resp = urllib.request.urlopen(req, timeout=timeout)
        result = json.loads(resp.read().decode("utf-8"))
        return result.get("message", {}).get("content", "")
    except Exception:
        return ""


def ollama_list_models() -> list:
    """Lista modelos Ollama instalados."""
    try:
        import urllib.request
        resp = urllib.request.urlopen(f"{OLLAMA_URL}/api/tags", timeout=5)
        data = json.loads(resp.read().decode("utf-8"))
        return [m["name"] for m in data.get("models", [])]
    except Exception:
        return []


# ═══════════════════════════════════════════
# CACHE
# ═══════════════════════════════════════════

def get_cache_dir(name: str = "default") -> Path:
    """Retorna diretório de cache."""
    cache_dir = Path.home() / "AppData" / "Local" / "hermes" / f"{name}_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def cache_save(name: str, key: str, value: Any, ttl: int = 3600) -> None:
    """Salva valor no cache com TTL (segundos)."""
    try:
        cache_dir = get_cache_dir(name)
        cache_file = cache_dir / f"{hashlib.md5(key.encode()).hexdigest()[:12]}.json"
        data = {"timestamp": time.time(), "ttl": ttl, "key": key, "value": value}
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception:
        pass


def cache_load(name: str, key: str) -> Optional[Any]:
    """Carrega valor do cache se não expirado."""
    try:
        cache_dir = get_cache_dir(name)
        cache_file = cache_dir / f"{hashlib.md5(key.encode()).hexdigest()[:12]}.json"
        if not cache_file.exists():
            return None
        with open(cache_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        if time.time() - data.get("timestamp", 0) < data.get("ttl", 3600):
            return data.get("value")
        else:
            cache_file.unlink(missing_ok=True)
            return None
    except Exception:
        return None


def cache_clear(name: str, max_age: int = 86400) -> int:
    """Limpa cache expirado. Retorna quantidade removida."""
    removed = 0
    try:
        cache_dir = get_cache_dir(name)
        for f in cache_dir.glob("*.json"):
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    data = json.load(fp)
                if time.time() - data.get("timestamp", 0) > data.get("ttl", max_age):
                    f.unlink()
                    removed += 1
            except Exception:
                pass
    except Exception:
        pass
    return removed


# ═══════════════════════════════════════════
# TEMP FILE
# ═══════════════════════════════════════════

def get_temp_path(filename: str) -> str:
    """Retorna path seguro para arquivo temporário."""
    return os.path.join(tempfile.gettempdir(), filename)


# ═══════════════════════════════════════════
# LOGGING
# ═══════════════════════════════════════════

def log_info(msg: str) -> None:
    """Log de informação."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] INFO: {msg}")


def log_error(msg: str) -> None:
    """Log de erro."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] ERRO: {msg}", file=sys.stderr)


def log_warning(msg: str) -> None:
    """Log de aviso."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] AVISO: {msg}")
