"""
atena_bridge.py — Ponte direta Koldi → Atena via Ollama
Elimina necessidade de APIs externas. Comunicação via localhost:11434.

Uso pelo Koldi:
    from atena_bridge import AtenaBridge
    bridge = AtenaBridge()
    resposta = bridge.ask("Analise este codigo", temperature=0.3)
"""
import urllib.request
import json
import time
from typing import Optional

OLLAMA_URL = "http://localhost:11434"
MODEL = "atena-glm5"
EMBED_MODEL = "nomic-embed-text"

class AtenaBridge:
    """Ponte de comunicação direta entre Koldi (Hermes) e Atena (Ollama local)."""
    
    def __init__(self, base_url: str = OLLAMA_URL, model: str = MODEL, timeout: int = 120):
        self.base_url = base_url
        self.model = model
        self.timeout = timeout
        self._context: list[dict] = []
    
    def _post(self, endpoint: str, payload: dict) -> dict:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}{endpoint}",            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    
    def ask(self, prompt: str, system: Optional[str] = None,
            temperature: float = 0.7, max_tokens: int = 512,
            keep_context: bool = False) -> str:
        """Envia prompt para Atena via Ollama chat API."""
        messages = list(self._context)
        if system:
            messages = [{"role": "system", "content": system}] + messages
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_ctx": 4096,
                "num_predict": max_tokens,
            }
        }
        
        result = self._post("/api/chat", payload)
        response_text = result["message"]["content"]
        
        if keep_context:
            self._context.append({"role": "user", "content": prompt})
            self._context.append({"role": "assistant", "content": response_text})
            if len(self._context) > 20:
                self._context = self._context[-20:]
        
        return response_text
    
    def embed(self, text: str) -> list[float]:
        """Gera embedding via nomic-embed-text."""
        result = self._post("/api/embed", {"model": EMBED_MODEL, "input": text})
        return result["embeddings"][0]
    
    def clear_context(self):
        """Limpa histórico de conversa."""
        self._context = []
    
    def health_check(self) -> bool:
        """Verifica se Ollama e o modelo estão acessíveis."""
        try:
            req = urllib.request.Request(f"{self.base_url}/api/tags")
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read())
                models = [m["name"] for m in data.get("models", [])]
                return any(self.model in m for m in models)
        except Exception:
            return False


if __name__ == "__main__":
    bridge = AtenaBridge()
    
    if not bridge.health_check():
        print("ERRO: Ollama nao acessivel ou modelo nao carregado")
        exit(1)
    
    print("Atena online!")
    
    # Teste simples
    resp = bridge.ask("Diga seu nome em uma frase.", temperature=0.1, max_tokens=50)
    print(f"Resposta: {resp}")
    
    # Teste com contexto
    resp2 = bridge.ask("O que eu perguntei antes?", keep_context=True)
    print(f"Com contexto: {resp2}")
