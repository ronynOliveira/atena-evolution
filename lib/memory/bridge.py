"""
bridge.py — Interface mínima com Ollama. Reaproveitável do resto do
seu projeto Atena (você provavelmente já tem algo parecido nos 31
arquivos — pode substituir por um import do seu módulo existente).

100% local: urllib puro, sem SDKs, sem chaves de API, sem rede externa.
"""

import json
import time
import urllib.request
from typing import Optional


class AtenaBridge:
    """Interface com Ollama local para chat e embeddings."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        chat_model: str = "atena-glm5",
        embed_model: str = "nomic-embed-text",
        timeout: int = 60,
        max_retries: int = 2,
    ):
        self.base_url = base_url
        self.chat_model = chat_model
        self.embed_model = embed_model
        self.timeout = timeout
        self.max_retries = max_retries

    def _post(self, endpoint: str, payload: dict) -> dict:
        """POST com retry para falhas transitórias."""
        data = json.dumps(payload).encode("utf-8")
        last_exc: Optional[Exception] = None

        for attempt in range(1 + self.max_retries):
            try:
                req = urllib.request.Request(
                    f"{self.base_url}{endpoint}",
                    data=data,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except Exception as e:
                last_exc = e
                if attempt < self.max_retries:
                    time.sleep(0.5 * (attempt + 1))
        raise last_exc  # type: ignore[misc]

    def ask(self, prompt: str, system: str = "", temperature: float = 0.3) -> str:
        """Chat completion com Ollama."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        result = self._post("/api/chat", {
            "model": self.chat_model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature, "num_ctx": 4096, "num_predict": 256},
        })
        return result["message"]["content"].strip()

    def embed(self, text: str) -> list[float]:
        """Gera embedding via Ollama. Retorna vetor de floats."""
        result = self._post("/api/embed", {"model": self.embed_model, "input": text})
        embeddings = result.get("embeddings", [])
        if not embeddings:
            raise ValueError(
                f"Ollama retornou embeddings vazios para o modelo '{self.embed_model}'. "
                "Verifique se o modelo está carregado (ollama pull nomic-embed-text)."
            )
        return embeddings[0]

    def health_check(self) -> bool:
        """Verifica se o Ollama está acessível e o modelo de chat disponível."""
        try:
            req = urllib.request.Request(f"{self.base_url}/api/tags")
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read())
                names = [m["name"] for m in data.get("models", [])]
                return any(self.chat_model in n for n in names)
        except Exception:
            return False
