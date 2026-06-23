"""
hermes_ollama_adapter.py — Proxy entre Hermes (OpenAI-format) e Ollama (Ollama-format)
Traduz chamadas /v1/chat/completions para /api/chat
"""
import json
import time
import hashlib
import urllib.request
import urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional

OLLAMA_URL = "http://localhost:11434"
DEFAULT_MODEL = "atena-glm5"
PORT = 8001


def get_ollama_url():
    """Retorna URL do Ollama (permite override em runtime)."""
    return OLLAMA_URL


def set_ollama_url(url: str):
    """Define URL do Ollama em runtime."""
    global OLLAMA_URL
    OLLAMA_URL = url


def ollama_chat(messages: list, model: str = DEFAULT_MODEL,
                temperature: float = 0.7, max_tokens: int = 512) -> str:
    """Envia chat para Ollama e retorna a resposta."""
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
        }
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{get_ollama_url()}/api/chat",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        result = json.loads(resp.read())
        return result["message"]["content"]


def ollama_models() -> list[str]:
    """Lista modelos disponíveis no Ollama."""
    try:
        req = urllib.request.Request(f"{get_ollama_url()}/api/tags")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            return [m["name"] for m in data.get("models", [])]
    except Exception:
        return []


class AdapterHandler(BaseHTTPRequestHandler):
    """Handler HTTP que traduz OpenAI-format para Ollama-format."""

    def do_GET(self):
        if self.path == "/v1/models":
            models = ollama_models()
            response = {
                "data": [
                    {"id": m, "object": "model", "created": int(time.time()),
                     "owned_by": "ollama"}
                    for m in models
                ]
            }
            self._send_json(200, response)
        elif self.path == "/health":
            self._send_json(200, {"status": "ok", "ollama": OLLAMA_URL})
        else:
            self._send_json(404, {"error": "not found"})

    def do_POST(self):
        if self.path == "/v1/chat/completions":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)

            try:
                request = json.loads(body)
            except json.JSONDecodeError:
                self._send_json(400, {"error": "invalid JSON"})
                return

            messages = request.get("messages", [])
            model = request.get("model", DEFAULT_MODEL)
            temperature = request.get("options", {}).get("temperature", 0.7)
            max_tokens = request.get("options", {}).get("max_tokens", 512)

            # Fallback para options no payload raiz
            if not temperature or temperature == 0.7:
                temperature = request.get("temperature", 0.7)
            if not max_tokens or max_tokens == 512:
                max_tokens = request.get("max_tokens", 512)

            try:
                t0 = time.time()
                content = ollama_chat(messages, model, temperature, max_tokens)
                latency_ms = (time.time() - t0) * 1000

                response = {
                    "id": f"chatcmpl-{hashlib.md5(content.encode()).hexdigest()[:12]}",
                    "object": "chat.completion",
                    "created": int(time.time()),
                    "model": model,
                    "choices": [{
                        "index": 0,
                        "message": {"role": "assistant", "content": content},
                        "finish_reason": "stop"
                    }],
                    "usage": {
                        "prompt_tokens": sum(len(m.get("content", "")) for m in messages),
                        "completion_tokens": len(content),
                        "total_tokens": sum(len(m.get("content", "")) for m in messages) + len(content)
                    }
                }
                self._send_json(200, response)

            except urllib.error.URLError as e:
                self._send_json(502, {"error": f"Ollama unavailable: {e}"})
            except Exception as e:
                self._send_json(500, {"error": f"Internal error: {type(e).__name__}"})
        else:
            self._send_json(404, {"error": "not found"})

    def _send_json(self, status: int, data: dict):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        """Silenciar logs HTTP."""
        pass


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Hermes ↔ Ollama Adapter")
    parser.add_argument("--port", type=int, default=PORT, help="Porta (default: 8001)")
    parser.add_argument("--ollama", type=str, default=None, help="URL do Ollama")
    args = parser.parse_args()

    if args.ollama:
        set_ollama_url(args.ollama)

    server = HTTPServer(("127.0.0.1", args.port), AdapterHandler)
    print(f"Hermes <-> Ollama Adapter rodando em http://127.0.0.1:{args.port}")
    print(f"Ollama: {get_ollama_url()}")
    print("Pressione Ctrl+C para parar")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nParando...")
        server.shutdown()


if __name__ == "__main__":
    main()
