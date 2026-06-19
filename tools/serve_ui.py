"""
serve_ui.py — Servidor HTTP simples para a UI da Atena
Serve os arquivos web/ via HTTP para evitar problemas de CORS com file://
"""
import os
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
import urllib.request
import json

PORT = 8080
WEB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web")


class UIHandler(SimpleHTTPRequestHandler):
    """Handler que serve a UI e faz proxy para Ollama."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB_DIR, **kwargs)

    def do_GET(self):
        if self.path == "/api/ollama/status":
            self._proxy_ollama("/api/tags")
        elif self.path == "/api/ollama/models":
            self._proxy_ollama("/api/tags")
        else:
            super().do_GET()

    def do_POST(self):
        if self.path == "/api/ollama/chat":
            self._proxy_ollama_chat()
        else:
            self.send_response(404)
            self.end_headers()

    def _proxy_ollama(self, endpoint):
        """Faz proxy para Ollama GET."""
        try:
            req = urllib.request.Request(f"http://localhost:11434{endpoint}")
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = resp.read()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            error = json.dumps({"error": str(e)}).encode()
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(error)

    def _proxy_ollama_chat(self):
        """Faz proxy para Ollama POST /api/chat."""
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        try:
            req = urllib.request.Request(
                "http://localhost:11434/api/chat",
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = resp.read()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            error = json.dumps({"error": str(e)}).encode()
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(error)

    def log_message(self, format, *args):
        """Logs silenciosos."""
        pass


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else PORT
    server = HTTPServer(("127.0.0.1", port), UIHandler)
    print(f"Atena UI rodando em http://127.0.0.1:{port}")
    print(f"Web dir: {WEB_DIR}")
    print("Pressione Ctrl+C para parar")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nParando...")
        server.shutdown()


if __name__ == "__main__":
    main()
