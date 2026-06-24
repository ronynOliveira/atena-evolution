#!/usr/bin/env python3
"""
openrouter_key_monitor.py — Monitor de créditos e rotação automática de chaves OpenRouter.

Funcionalidades:
1. Verifica créditos restantes via GET /api/v1/key
2. Alerta via Telegram quando créditos ficam abaixo do limite
3. Fallback automático entre múltiplas chaves
4. Monitoramento de rate limits (headers x-ratelimit-*)
5. Cache para não exceder rate limits do endpoint

Uso:
    python openrouter_key_monitor.py --check          # Verifica status de todas as chaves
    python openrouter_key_monitor.py --daemon         # Roda continuamente (intervalo configurável)
    python openrouter_key_monitor.py --set-key KEY    # Adiciona uma nova chave
    python openrouter_key_monitor.py --alert-test     # Envia alerta de teste

Configuração via environment ou cofre:
    OPENROUTER_API_KEYS — chave1,chave2 (separadas por vírgula)
    OPENROUTER_PRIMARY_KEY — chave principal
    TELEGRAM_BOT_TOKEN — token do bot Telegram (para alertas)
    TELEGRAM_CHAT_ID — chat ID do Telegram
    CREDITS_ALERT_THRESHOLD — limite mínimo de créditos para alerta (default: 10.0)
    CHECK_INTERVAL — intervalo de checagem em segundos (default: 3600 = 1hora)
"""

import argparse
import json
import os
import re
import sys
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# ── Configuração de paths ────────────────────────────────────────────────────
HOME = Path.home()
HERMES_HOME = Path(os.environ.get("HERMES_HOME", str(HOME / "AppData/Local/hermes" if os.name == "nt" else HOME / ".hermes")))
if not HERMES_HOME.exists():
    HERMES_HOME = HOME / ".hermes"

LOG_DIR = HERMES_HOME / "logs"
STATE_FILE = HERMES_HOME / "openrouter_key_state.json"
LOG_FILE = LOG_DIR / "openrouter_monitor.log"
COFRE_SCRIPT = HERMES_HOME / "scripts" / "cofre.py" if os.name == "nt" else None

# Para Linux/Cofre, o cofre pode estar em outro lugar
if COFRE_SCRIPT is None or not COFRE_SCRIPT.exists():
    COFRE_SCRIPT = None

LOG_DIR.mkdir(parents=True, exist_ok=True)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(str(LOG_FILE), encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("openrouter_monitor")

# ── Configurações padrão ────────────────────────────────────────────────────
CACHE_TTL = 300          # 5 minutos de cache para checagem de créditos
ALERT_COOLDOWN = 86400   # 24h entre alertas repetidos para a mesma chave
DEFAULT_THRESHOLD = 10.0 # Créditos mínimos antes de alertar
DEFAULT_INTERVAL = 3600  # 1 hora entre checagens


# ── Utilidades HTTP ─────────────────────────────────────────────────────────
def http_get(url: str, headers: dict, timeout: int = 10) -> tuple[int, dict, dict]:
    """Faz GET retornando (status_code, headers_dict, body_dict_or_none)."""
    import urllib.request
    req = urllib.request.Request(url, headers=headers)
    try:
        handler = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        resp = handler.open(req, timeout=timeout)
        body = resp.read().decode()
        return resp.status, dict(resp.headers), json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        try:
            parsed = json.loads(body) if body else {}
        except Exception:
            parsed = {"raw": body[:500]}
        return e.code, dict(e.headers), parsed
    except Exception as e:
        return 0, {}, {"error": str(e)}


def clean_key(key: str) -> str:
    """Remove emojis e whitespace de uma chave."""
    return re.sub(r"[^\x20-\x7E]", "", key).strip()


# ── Cofre integration ────────────────────────────────────────────────────────
COFRE_PASSWORD = "EW8&mRwss%SH3E9ZFpj9e@#l"

def cofre_get(key_name: str) -> Optional[str]:
    """Lê uma chave do cofre."""
    if COFRE_SCRIPT is None or not Path(COFRE_SCRIPT).exists():
        return None
    try:
        result = subprocess.run(
            [sys.executable, str(COFRE_SCRIPT), "--password", COFRE_PASSWORD, "get", key_name],
            capture_output=True, text=True, timeout=10
        )
        val = clean_key(result.stdout)
        return val if val and "não encontrada" not in val else None
    except Exception:
        return None

import subprocess

def cofre_set(key_name: str, value: str) -> bool:
    """Salva uma chave no cofre."""
    if COFRE_SCRIPT is None or not Path(COFRE_SCRIPT).exists():
        return False
    try:
        result = subprocess.run(
            [sys.executable, str(COFRE_SCRIPT), "--password", COFRE_PASSWORD, "set", key_name, value],
            capture_output=True, text=True, timeout=10
        )
        return result.returncode == 0
    except Exception:
        return False


# ── OpenRouter API ───────────────────────────────────────────────────────────
OR_BASE_URL = "https://openrouter.ai/api/v1"

def check_key_credits(key: str) -> dict:
    """
    Verifica créditos de uma chave OpenRouter.
    GET /api/v1/key retorn:
    {
        "data": {
            "label": "...",
            "limit": 100.0,        # limite total (null = ilimitado)
            "usage": 12.5,          # quanto já foi usado
            "limit_remaining": 87.5, # créditos restantes
            "is_free_tier": false,
            "rate_limit": {...}
        }
    }
    """
    key = clean_key(key)
    status, headers, body = http_get(
        f"{OR_BASE_URL}/key",
        {"Authorization": f"Bearer {key}"},
        timeout=10,
    )

    result = {
        "key": f"{key[:10]}...",
        "valid": False,
        "credits_remaining": None,
        "credits_total": None,
        "usage": None,
        "rate_limit": {},
        "error": None,
        "checked_at": datetime.now().isoformat(),
    }

    if status == 200:
        data = body.get("data", {})
        result["valid"] = True
        result["credits_remaining"] = data.get("limit_remaining")
        result["credits_total"] = data.get("limit")
        result["usage"] = data.get("usage")
        result["rate_limit"] = data.get("rate_limit", {})
        result["is_free_tier"] = data.get("is_free_tier", False)
    elif status == 401:
        result["error"] = "Chave inválida (401)"
    elif status == 402:
        result["error"] = "Sem créditos (402)"
        result["credits_remaining"] = 0
    else:
        result["error"] = f"HTTP {status}: {body.get('error', {}).get('message', str(body))[:100]}"

    # Capturar rate limit headers
    for hdr in ["x-ratelimit-limit", "x-ratelimit-remaining", "x-ratelimit-reset"]:
        if hdr.lower() in {k.lower(): v for k, v in headers.items()}:
            result["rate_limit"][hdr] = headers[hdr]

    return result


def check_all_keys(keys: list[str]) -> list[dict]:
    """Verifica créditos de todas as chaves."""
    results = []
    for key in keys:
        result = check_key_credits(key)
        results.append(result)
        status_icon = "✅" if result["valid"] else "❌"
        credits_str = f"${result['credits_remaining']:.2f}" if result["credits_remaining"] is not None else "N/A"
        log.info(f"  {status_icon} {result['key']} — Créditos: {credits_str} {result['error'] or ''}")
        time.sleep(1)  # Rate limit entre checagens
    return results


# ── Telegram alerts ──────────────────────────────────────────────────────────
def send_telegram_alert(bot_token: str, chat_id: str, message: str) -> bool:
    """Envia alerta via Telegram."""
    status, _, body = http_get(
        f"https://api.telegram.org/bot{bot_token}/sendMessage",
        {"Content-Type": "application/json"},
        timeout=10,
    )
    # Na verdade é POST, mas usar requests
    try:
        import urllib.request
        payload = json.dumps({"chat_id": chat_id, "text": message, "parse_mode": "HTML"}).encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            headers={"Content-Type": "application/json"},
            data=payload
        )
        handler = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        resp = handler.open(req, timeout=10)
        return resp.status == 200
    except Exception as e:
        log.error(f"Erro ao enviar alerta Telegram: {e}")
        return False


# ── State management ─────────────────────────────────────────────────────────
def load_state() -> dict:
    """Carrega estado persistido."""
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"last_alerts": {}, "key_history": [], "total_checks": 0}


def save_state(state: dict):
    """Salva estado."""
    STATE_FILE.write_text(json.dumps(state, indent=2, default=str), encoding="utf-8")


# ── Alert logic ──────────────────────────────────────────────────────────────
def should_alert(state: dict, key_id: str, threshold: float, remaining: Optional[float]) -> bool:
    """Verifica se deve disparar alerta para uma chave."""
    if remaining is None or remaining >= threshold:
        return False

    last_alert = state.get("last_alerts", {}).get(key_id)
    if last_alert:
        last_time = datetime.fromisoformat(last_alert)
        if datetime.now() - last_time < timedelta(seconds=ALERT_COOLDOWN):
            return False  # Ainda em cooldown

    return True


def record_alert(state: dict, key_id: str):
    """Registra que um alerta foi disparado."""
    state.setdefault("last_alerts", {})[key_id] = datetime.now().isoformat()


# ── Key management ───────────────────────────────────────────────────────────
def get_keys_from_env_or_cofre() -> list[str]:
    """Obtém lista de chaves do environment ou do cofre."""
    keys = []

    # 1. Tentar do environment
    env_keys = os.environ.get("OPENROUTER_API_KEYS", "")
    if env_keys:
        for k in env_keys.split(","):
            k = clean_key(k)
            if k:
                keys.append(k)

    # 2. Tentar chave primária do env
    primary = os.environ.get("OPENROUTER_API_KEY", "")
    if primary:
        k = clean_key(primary)
        if k and k not in keys:
            keys.insert(0, k)

    # 3. Tentar do cofre
    cofre_keys = [
        cofre_get("OPENROUTER_API_KEY"),
        cofre_get("OPENROUTER_API_KEY_2"),
        cofre_get("OPENROUTER_API_KEY_BACKUP"),
    ]
    for k in cofre_keys:
        if k and k not in keys:
            keys.append(k)

    return keys


def pick_best_key(keys: list[str], state: dict) -> tuple[Optional[str], Optional[dict]]:
    """Escolhe a chave com mais créditos."""
    best_key = None
    best_remaining = -1
    best_result = None

    for key in keys:
        result = check_key_credits(key)
        if not result["valid"]:
            continue
        remaining = result.get("credits_remaining")
        if remaining is None:  # Ilimitada
            return key, result
        if remaining > best_remaining:
            best_key = key
            best_remaining = remaining
            best_result = result

    return best_key, best_result


# ── Auto-rotation logic ──────────────────────────────────────────────────────
def auto_rotate_key(current_key: str, new_key: str) -> bool:
    """
    Faz rotação automática: atualiza chave no config e reinicia gateway.
    Retorna True se bem-sucedido.
    """
    log.info(f"Iniciando rotação de chave: {current_key[:10]}... -> {new_key[:10]}...")

    # 1. Atualizar no cofre
    if cofre_set("OPENROUTER_API_KEY", new_key):
        log.info("✅ Chave atualizada no cofre")
    else:
        log.warning("⚠️ Falha ao atualizar no cofre")

    # 2. Atualizar no .env (se existir)
    env_path = HERMES_HOME / ".env"
    if env_path.exists():
        content = env_path.read_text(encoding="utf-8")
        content = re.sub(
            r'OPENROUTER_API_KEY=.*',
            f'OPENROUTER_API_KEY={new_key}',
            content
        )
        env_path.write_text(content, encoding="utf-8")
        log.info("✅ .env atualizado")

    # 3. Atualizar no config.yaml
    config_path = HERMES_HOME / "config.yaml"
    if config_path.exists():
        content = config_path.read_text(encoding="utf-8")
        # Atualizar OPENROUTER_API_KEY se estiver hardcoded
        if "OPENROUTER_API_KEY" in content:
            content = re.sub(
                r'OPENROUTER_API_KEY:\s*[^\n]+',
                f'OPENROUTER_API_KEY: {new_key}',
                content
            )
            config_path.write_text(content, encoding="utf-8")
            log.info("✅ config.yaml atualizado")

    # 4. Reiniciar gateway
    try:
        subprocess.run(["hermes", "gateway", "run", "--replace"], timeout=30)
        log.info("✅ Gateway reiniciado")
    except Exception as e:
        log.warning(f"⚠️ Reinício do gateway falhou: {e}")
        log.info("   Execute 'hermes gateway run --replace' manualmente")

    return True


# ── CLI commands ─────────────────────────────────────────────────────────────
def cmd_check(args):
    """Verifica status de todas as chaves."""
    print("\n" + "=" * 64)
    print("  OPENROUTER KEY MONITOR — Status Report")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 64)

    keys = get_keys_from_env_or_cofre()
    if not keys:
        print("\n❌ Nenhuma chave encontrada!")
        print("   Configure OPENROUTER_API_KEY ou salve no cofre.")
        return

    print(f"\n🔑 {len(keys)} chave(s) encontrada(s):\n")
    results = check_all_keys(keys)

    # Resumo
    total_remaining = sum(r["credits_remaining"] for r in results if r["credits_remaining"] is not None)
    valid_keys = [r for r in results if r["valid"]]
    invalid_keys = [r for r in results if not r["valid"]]

    print(f"\n{'─' * 64}")
    print(f"  📊 Resumo:")
    print(f"     Chaves válidas:   {len(valid_keys)}/{len(keys)}")
    print(f"     Créditos totais:  ${total_remaining:.2f}" if total_remaining else "     Créditos totais:  N/A")
    print(f"     Chaves inválidas: {len(invalid_keys)}")

    for r in invalid_keys:
        print(f"       ❌ {r['key']} — {r['error']}")

    # Salvar estado
    state = load_state()
    state.setdefault("key_history", []).append({
        "timestamp": datetime.now().isoformat(),
        "results": results,
        "total_remaining": total_remaining,
    })
    state["total_checks"] = state.get("total_checks", 0) + 1
    save_state(state)

    print(f"\n  Estado salvo em: {STATE_FILE}")


def cmd_daemon(args):
    """Rodando continuamente, verificando e alertando."""
    log.info("Iniciando OpenRouter Key Monitor daemon...")
    state = load_state()
    threshold = float(os.environ.get("CREDITS_ALERT_THRESHOLD", DEFAULT_THRESHOLD))
    interval = int(os.environ.get("CHECK_INTERVAL", DEFAULT_INTERVAL))

    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")

    log.info(f"  Threshold: ${threshold:.2f}")
    log.info(f"  Interval:  {interval}s")
    log.info(f"  Telegram:  {'ON' if bot_token and chat_id else 'OFF'}")

    while True:
        try:
            log.info("--- Ciclo de checagem ---")
            keys = get_keys_from_env_or_cofre()
            if not keys:
                log.warning("Nenhuma chave encontrada. Tentando novamente em 60s.")
                time.sleep(60)
                continue

            results = check_all_keys(keys)

            # Verificar alertas
            for result in results:
                key_id = result["key"]
                if should_alert(state, key_id, threshold, result["credits_remaining"]):
                    msg = (
                        f"⚠️ <b>ALERTA: Créditos OpenRouter Baixos</b>\n\n"
                        f"Chave: <code>{key_id}</code>\n"
                        f"Créditos restantes: <b>${result['credits_remaining']:.2f}</b>\n"
                        f"Threshold: ${threshold:.2f}\n"
                        f"Horário: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                        f"💰 Recarregue em: https://openrouter.ai/settings/credits\n"
                        f"🔧 Troque a chave: python openrouter_key_monitor.py --set-key NOVA_CHAVE"
                    )

                    if bot_token and chat_id:
                        if send_telegram_alert(bot_token, chat_id, msg):
                            log.info(f"Alerta Telegram enviado para {key_id}")
                        else:
                            log.error("Falha ao enviar alerta Telegram")
                    else:
                        log.warning(f"ALERTA (sem Telegram): {msg}")

                    record_alert(state, key_id)

            # Salvar estado
            state["total_checks"] = state.get("total_checks", 0) + 1
            save_state(state)

            # Dormir
            next_check = datetime.now() + timedelta(seconds=interval)
            log.info(f"Próxima checagem em {interval}s ({next_check.strftime('%H:%M:%S')})")
            time.sleep(interval)

        except KeyboardInterrupt:
            log.info("Daemon interrompido pelo usuário.")
            break
        except Exception as e:
            log.error(f"Erro no ciclo: {e}")
            time.sleep(60)


def cmd_set_key(args):
    """Define uma nova chave."""
    new_key = args.set_key if hasattr(args, 'set_key') and args.set_key else args.key
    if not new_key:
        print("❌ Forneça a chave com --set-key sk-or-...")
        return

    new_key = clean_key(new_key)
    if not new_key.startswith("sk-or-"):
        print("⚠️ A chave não parece ser uma chave OpenRouter válida (deve começar com sk-or-)")
        if input("Continuar mesmo assim? (s/n): ").lower() != "s":
            return

    # Verificar se a chave funciona
    print(f"\n🔍 Verificando chave {new_key[:10]}...")
    result = check_key_credits(new_key)

    if result["valid"]:
        print(f"✅ Chave válida! Créditos: ${result['credits_remaining']:.2f}")

        # Salvar no cofre
        if cofre_set("OPENROUTER_API_KEY", new_key):
            print("✅ Chave salva no cofre")
        else:
            print("⚠️ Falha ao salvar no cofre")

        # Perguntar se quer fazer rotação automática
        if input("\nFazer rotação automática (atualizar config + reiniciar gateway)? (s/n): ").lower() == "s":
            auto_rotate_key("", new_key)
    else:
        print(f"❌ Chave inválida: {result['error']}")


def cmd_alert_test(args):
    """Envia alerta de teste."""
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")

    if not bot_token or not chat_id:
        print("❌ Configure TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID")
        return

    msg = (
        "🧪 <b>Teste de Alerta — OpenRouter Monitor</b>\n\n"
        "Este é um alerta de teste. Se o Senhor recebeu, o sistema está funcionando!\n\n"
        f"Horário: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )

    if send_telegram_alert(bot_token, chat_id, msg):
        print("✅ Alerta de teste enviado!")
    else:
        print("❌ Falha ao enviar alerta")


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="OpenRouter Key Monitor — Monitoramento e rotação automática de chaves"
    )
    parser.add_argument("--check", action="store_true", help="Verifica status de todas as chaves")
    parser.add_argument("--daemon", action="store_true", help="Roda continuamente")
    parser.add_argument("--set-key", type=str, metavar="KEY", help="Define uma nova chave")
    parser.add_argument("--key", type=str, metavar="KEY", help="Alias para --set-key")
    parser.add_argument("--alert-test", action="store_true", help="Envia alerta de teste")
    parser.add_argument("--rotate", type=str, metavar="NEW_KEY", help="Faz rotação de chave")
    args = parser.parse_args()

    if args.check:
        cmd_check(args)
    elif args.daemon:
        cmd_daemon(args)
    elif args.set_key or getattr(args, 'key', None):
        cmd_set_key(args)
    elif args.alert_test:
        cmd_alert_test(args)
    elif args.rotate:
        auto_rotate_key("", args.rotate)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
