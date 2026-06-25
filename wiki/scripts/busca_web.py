#!/usr/bin/env python3
"""
BUSCA WEB UNIFICADA DO PROJETO ATENA
=====================================

Consolida toda a funcionalidade de busca web em um único script.
Substitui: busca_web.py, pesquisa_web.py

Fontes de busca (em ordem de prioridade):
1. Cache local (instantâneo, TTL configurável)
2. Kimi WebBridge (navegador real - mais confiável)
3. Gemini CLI (pesquisa web integrada)
4. Opencode (análise + pesquisa)
5. Freebuff (criação + pesquisa)

Uso:
  python busca_web.py "sua pesquisa"
  python busca_web.py --fontes           # lista fontes disponíveis
  python busca_web.py --cache "query"   # busca apenas no cache
  python busca_web.py --limpar-cache    # limpa cache expirado
  python busca_web.py --no-cache        # ignora cache
  python busca_web.py --fonte gemini    # usa apenas Gemini

Autor: OWL (Batedor da Nuvem) - Consolidação 2026-05-20
Versão: 2.0
"""

import subprocess
import sys
import os
import json
import hashlib
import time
import logging
import argparse
from datetime import datetime, timedelta
from pathlib import Path

# ═══════════════════════════════════════════
# LOGGING
# ═══════════════════════════════════════════
try:
    from atena_logging import get_logger
    logger = get_logger("busca_web")
except ImportError:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    logger = logging.getLogger("busca_web")

# ═══════════════════════════════════════════
# CONFIGURAÇÃO
# ═══════════════════════════════════════════
CACHE_DIR = Path.home() / "AppData" / "Local" / "hermes" / "search_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
CACHE_TTL = 3600  # 1 hora padrão
KIMI_PORT = 10086
CHROME_CDP_PORT = 9222
GEMINI_PATH = os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "npm", "gemini.cmd")
OPCODE_MODEL = "opencode/qwen3.6-plus-free"

# ════════════════════════════════════════════
# LEARNING SYSTEM
# ════════════════════════════════════════════
LEARNED_FILE = Path.home() / "wiki" / "scripts" / "learned_sources.json"
DEFAULT_ORDER = ["opencode", "kimi", "gemini", "freebuff"]

def load_learned_data():
    """Load learned source scores from JSON file."""
    if LEARNED_FILE.exists():
        try:
            with open(LEARNED_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.debug(f"Erro ao carregar learned data: {e}")
            return {}
    return {}

def save_learned_data(data):
    """Save learned source scores to JSON file."""
    try:
        LEARNED_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LEARNED_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.debug(f"Erro ao salvar learned data: {e}")

def categorize_query(query: str) -> str:
    """Categorize the query to apply different learning strategies."""
    q_lower = query.lower()
    # News/time-sensitive
    if any(word in q_lower for word in ["notícia", "hoje", "últimas", "últimos", "agora", "último", "última", "notícias"]):
        return "news"
    # Historical/fact-based
    if any(word in q_lower for word in ["histórico", "história", "definição", "o que é", "quem foi", "quando ocorreu", "ano", "data"]):
        return "history"
    # Generic
    return "generic"


def get_dynamic_ttl(query: str) -> int:
    """Return TTL in seconds based on query category."""
    category = categorize_query(query)
    if category == "news":
        return 300  # 5 minutes for news
    if category == "history":
        return 86400  # 24 hours for historical/fact-based
    return CACHE_TTL  # default 1 hour for generic


def update_learning(query: str, successful_source: str):
    """Update the learned scores for the query's category."""
    data = load_learned_data()
    category = categorize_query(query)
    if category not in data:
        data[category] = {source: 0 for source in DEFAULT_ORDER}
    # Increment score for the successful source
    if successful_source in data[category]:
        data[category][successful_source] += 1
    else:
        # Ensure the source exists in the dict
        data[category][successful_source] = 1
    save_learned_data(data)

def get_learned_order(query: str) -> list:
    """Return source order based on learned scores for the query's category."""
    data = load_learned_data()
    category = categorize_query(query)
    if category in data and data[category]:
        # Sort sources by score descending, then by default order for ties
        scored = [(source, data[category].get(source, 0)) for source in DEFAULT_ORDER]
        scored.sort(key=lambda x: (-x[1], DEFAULT_ORDER.index(x[0])))
        return [source for source, _ in scored]
    return DEFAULT_ORDER.copy()

# Rate limit cooldown for Gemini
GEMINI_COOLDOWN = 60  # seconds
_gemini_rate_limit_reset = 0  # timestamp when cooldown ends


# ═══════════════════════════════════════════
# CACHE
# ═══════════════════════════════════════════

def cache_path(query: str) -> Path:
    """Retorna caminho do arquivo de cache para a query."""
    h = hashlib.md5(query.lower().strip().encode()).hexdigest()
    return CACHE_DIR / f"{h}.json"


def cache_load(query: str, ttl: int | None = None) -> str | None:
    """Carrega resultado do cache se válido.
    Se ttl for None, usa TTL dinâmico baseado na categoria da query.
    """
    if ttl is None:
        ttl = get_dynamic_ttl(query)
    try:
        p = cache_path(query)
        if not p.exists():
            return None
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        if time.time() - data.get("timestamp", 0) < ttl:
            logger.info("Cache hit: %s", query[:60])
            return data.get("resultado")
        else:
            logger.debug("Cache expirado: %s", query[:60])
            return None
    except Exception as e:
        logger.debug("Erro no cache load: %s", e)
        return None


def cache_save(query: str, resultado: str):
    """Salva resultado no cache."""
    try:
        p = cache_path(query)
        data = {
            "timestamp": time.time(),
            "query": query,
            "resultado": resultado,
            "fonte": "unknown"
        }
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.debug("Erro no cache save: %s", e)


def cache_list() -> list:
    """Lista todas as entradas em cache."""
    entries = []
    for f in sorted(CACHE_DIR.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            with open(f, "r", encoding="utf-8") as fp:
                data = json.load(fp)
            age = datetime.now() - datetime.fromtimestamp(data.get("timestamp", 0))
            valid = time.time() - data.get("timestamp", 0) < CACHE_TTL
            entries.append({
                "query": data.get("query", "")[:60],
                "age": f"{age.seconds//3600}h {(age.seconds%3600)//60}m",
                "valid": valid
            })
        except Exception:
            pass
    return entries


def cache_clean() -> int:
    """Remove entradas expiradas. Retorna quantidade removida."""
    removed = 0
    for f in CACHE_DIR.glob("*.json"):
        try:
            with open(f, "r", encoding="utf-8") as fp:
                data = json.load(fp)
            if time.time() - data.get("timestamp", 0) > CACHE_TTL:
                f.unlink()
                removed += 1
        except Exception:
            pass
    return removed


# ═══════════════════════════════════════════
# FONTES DE BUSCA
# ═══════════════════════════════════════════

def run_cmd(cmd: str, timeout: int = 60) -> str:
    """Executa comando e retorna output."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except subprocess.TimeoutExpired:
        logger.warning("Timeout: %s", cmd[:60])
        return ""
    except Exception as e:
        logger.debug("Erro no comando: %s", e)
        return ""


def buscar_kimi(query: str) -> str | None:
    """
    Busca via Kimi WebBridge (navegador real).
    Mais confiável porque usa o Chrome real do usuário.
    """
    try:
        import urllib.request
        import urllib.parse

        url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"

        # Navega
        req_data = json.dumps({
            "action": "navigate",
            "args": {"url": url, "newTab": True},
            "session": "owl_search"
        }).encode()

        req = urllib.request.Request(
            f"http://127.0.0.1:{KIMI_PORT}/command",
            data=req_data,
            headers={"Content-Type": "application/json"}
        )
        resp = urllib.request.urlopen(req, timeout=5)

        # Aguarda carregar
        time.sleep(4)

        # Lê resultado
        req2 = urllib.request.Request(
            f"http://127.0.0.1:{KIMI_PORT}/command",
            data=json.dumps({"action": "snapshot", "args": {}, "session": "owl_search"}).encode(),
            headers={"Content-Type": "application/json"}
        )
        resp2 = urllib.request.urlopen(req2, timeout=15)
        data = json.loads(resp2.read().decode("utf-8", errors="replace"))

        if "data" in data and "tree" in data["data"]:
            tree = data["data"]["tree"]
            # Extrai texto do accessibility tree
            texto = _extrair_texto_tree(tree)
            if texto and len(texto) > 100:
                return texto[:3000]

        return None
    except Exception as e:
        logger.debug("Kimi WebBridge indisponível: %s", e)
        return None


def _extrair_texto_tree(tree) -> str:
    """Extrai texto legível do accessibility tree."""
    partes = []

    def _percorrer(no):
        if isinstance(no, dict):
            if no.get("role") in ("StaticText", "InlineTextBox"):
                nome = no.get("name", "")
                if nome and len(nome) > 2:
                    partes.append(nome)
            for filho in no.get("children", []):
                _percorrer(filho)
        elif isinstance(no, list):
            for item in no:
                _percorrer(item)

    _percorrer(tree)
    return " ".join(partes)


def buscar_gemini(query: str) -> str | None:
    """Busca via Gemini CLI com detecção de rate limit."""
    global _gemini_rate_limit_reset
    # Verificar cooldown
    if time.time() < _gemini_rate_limit_reset:
        logger.debug("Gemini em cooldown devido a rate limit")
        return None
    try:
        cmd = [
            GEMINI_PATH, "--model", "gemini-2.5-pro",
            "--skip-trust", "--prompt",
            f"Pesquise na web e resuma de forma detalhada em português: {query}"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        if result.returncode == 0 and result.stdout.strip():
            output = result.stdout.strip()
            # Verificar indicadores de rate limit
            lower_output = output.lower()
            if any(indicator in lower_output for indicator in ("429", "rate limit", "quota")):
                logger.warning("Detectado rate limit no Gemini: %s", output[:100])
                _gemini_rate_limit_reset = time.time() + GEMINI_COOLDOWN
                return None
            return output
        else:
            logger.debug("Gemini retornou erro ou vazio: %s", result.stderr[:100] if result.stderr else "sem stderr")
            return None
    except Exception as e:
        logger.debug("Gemini indisponível: %s", e)
        return None


def buscar_opencode(query: str) -> str | None:
    """Busca via Opencode."""
    cmd = f'opencode run --model "{OPCODE_MODEL}" "Pesquise na web e resuma em português: {query}"'
    output = run_cmd(cmd, timeout=120)
    return output if output else None


def buscar_freebuff(query: str) -> str | None:
    """Busca via Freebuff."""
    cmd = f'freebuff "Pesquise na web e resuma em português: {query}"'
    output = run_cmd(cmd, timeout=120)
    return output if output else None


# ═══════════════════════════════════════════
# BUSCA UNIFICADA
# ═══════════════════════════════════════════

FONTES = {
    "kimi": {"fn": buscar_kimi, "desc": "Kimi WebBridge (navegador real)"},
    "gemini": {"fn": buscar_gemini, "desc": "Gemini CLI"},
    "opencode": {"fn": buscar_opencode, "desc": "Opencode"},
    "freebuff": {"fn": buscar_freebuff, "desc": "Freebuff"},
}


def buscar(query: str, usar_cache: bool = True, fonte: str = None) -> str | None:
    """
    Busca unificada com fallback automático.
    
    Args:
        query: Termo de busca
        usar_cache: Se True, verifica cache primeiro
        fonte: Se especificado, usa apenas essa fonte
    
    Returns:
        Resultado da busca ou None
    """
    logger.info("Buscando: %s", query[:80])

    # 1. Cache
    if usar_cache and not fonte:
        resultado = cache_load(query)
        if resultado:
            print("  ✅ Resultado do cache")
            return resultado

    # 2. Fonte específica ou cascata
    if fonte:
        if fonte in FONTES:
            print(f"  🔍 Usando: {FONTES[fonte]['desc']}")
            resultado = FONTES[fonte]["fn"](query)
            if resultado:
                cache_save(query, resultado)
                return resultado
        else:
            logger.error("Fonte desconhecida: %s", fonte)
            return None
    else:
        # Cascata: learned order based on query category
        ordem = get_learned_order(query)
        for nome in ordem:
            print(f"  🔍 Tentando: {FONTES[nome]['desc']}...")
            try:
                resultado = FONTES[nome]["fn"](query)
                if resultado and len(resultado.strip()) > 50:
                    print(f"  ✅ Sucesso: {FONTES[nome]['desc']}")
                    cache_save(query, resultado)
                    update_learning(query, nome)  # Record success
                    return resultado
            except Exception as e:
                logger.debug("Erro em %s: %s", nome, e)
                continue

    return None


# ═══════════════════════════════════════════
# DIAGNÓSTICO
# ═══════════════════════════════════════════

def listar_fontes() -> list:
    """Lista e verifica todas as fontes de busca."""
    fontes = []

    # Cache
    entries = len(list(CACHE_DIR.glob("*.json")))
    fontes.append(f"✅ Cache local: {entries} resultado(s) em cache")

    # Kimi WebBridge
    try:
        import urllib.request
        req = urllib.request.Request(
            f"http://127.0.0.1:{KIMI_PORT}/command",
            data=json.dumps({"action": "list_tabs", "args": {}, "session": "check"}).encode(),
            headers={"Content-Type": "application/json"}
        )
        urllib.request.urlopen(req, timeout=3)
        fontes.append(f"✅ Kimi WebBridge: rodando (porta {KIMI_PORT})")
    except Exception:
        fontes.append(f"⚠️  Kimi WebBridge: não acessível (porta {KIMI_PORT})")

    # Gemini
    gemini_check = run_cmd("gemini --version 2>&1", timeout=5)
    fontes.append(f"{'✅' if gemini_check else '❌'} Gemini CLI: {gemini_check or 'não encontrado'}")

    # Opencode
    opencode_check = run_cmd("opencode --version 2>&1", timeout=5)
    fontes.append(f"{'✅' if opencode_check else '❌'} Opencode: {opencode_check or 'não encontrado'}")

    # Freebuff
    freebuff_check = run_cmd("freebuff --version 2>&1", timeout=5)
    fontes.append(f"{'✅' if freebuff_check else '❌'} Freebuff: {freebuff_check or 'não encontrado'}")

    # Chrome CDP
    try:
        import urllib.request
        urllib.request.urlopen(f"http://127.0.0.1:{CHROME_CDP_PORT}/json/version", timeout=2)
        fontes.append(f"✅ Chrome CDP: rodando (porta {CHROME_CDP_PORT})")
    except Exception:
        fontes.append(f"⚠️  Chrome CDP: não acessível (porta {CHROME_CDP_PORT})")

    return fontes


# ═══════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════

def main():
    """Interface de linha de comando."""
    parser = argparse.ArgumentParser(
        description="Busca Web Unificada do Projeto Atena v2.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python busca_web.py "novidades IA 2026"
  python busca_web.py --fontes
  python busca_web.py --cache "novidades IA"
  python busca_web.py --limpar-cache
  python busca_web.py --fonte kimi "pesquisa"
  python busca_web.py --no-cache "pesquisa"
        """
    )

    parser.add_argument("query", nargs="*", help="Termo de busca")
    parser.add_argument("--fontes", action="store_true", help="Lista fontes disponíveis")
    parser.add_argument("--cache", metavar="QUERY", help="Busca apenas no cache")
    parser.add_argument("--limpar-cache", action="store_true", help="Limpa cache expirado")
    parser.add_argument("--lista-cache", action="store_true", help="Lista entradas em cache")
    parser.add_argument("--fonte", choices=["kimi", "gemini", "opencode", "freebuff"],
                        help="Usa apenas a fonte especificada")
    parser.add_argument("--no-cache", action="store_true", help="Ignora cache")
    parser.add_argument("--ttl", type=int, default=CACHE_TTL, help=f"TTL do cache em segundos (padrão: {CACHE_TTL})")

    args = parser.parse_args()

    # Listar fontes
    if args.fontes:
        print("📡 Fontes de busca disponíveis:\n")
        for f in listar_fontes():
            print(f"  {f}")
        return 0

    # Limpar cache
    if args.limpar_cache:
        removidos = cache_clean()
        print(f"✅ Cache limpo: {removidos} entrada(s) removida(s)")
        return 0

    # Listar cache
    if args.lista_cache:
        entries = cache_list()
        if not entries:
            print("Cache vazio.")
        else:
            print(f"\n📋 Entradas em cache ({len(entries)}):\n")
            for e in entries:
                status = "✅" if e["valid"] else "⏰"
                print(f"  {status} [{e['age']}] {e['query']}")
        return 0

    # Busca de cache específico
    if args.cache:
        resultado = cache_load(args.cache, ttl=args.ttl)
        if resultado:
            print(f"[CACHE] {resultado}")
        else:
            print("Cache não encontrado para esta query.")
        return 0

    # Busca normal
    if args.query:
        query = " ".join(args.query)
    else:
        query = input("🔍 O que deseja pesquisar? ")
        if not query.strip():
            print("❌ Query vazia")
            return 1

    resultado = buscar(
        query,
        usar_cache=not args.no_cache,
        fonte=args.fonte
    )

    if resultado:
        print(f"\n{'='*60}")
        print("📊 RESULTADO:")
        print(f"{'='*60}\n")
        print(resultado)
        return 0
    else:
        print("\n❌ Nenhum resultado encontrado em nenhuma fonte.")
        print("Dica: Verifique as fontes com --fontes")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nBusca cancelada.")
        sys.exit(0)
    except Exception as e:
        logger.error("Erro fatal: %s", e)
        print(f"Erro: {e}", file=sys.stderr)
        sys.exit(1)
