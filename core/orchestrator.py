"""
orchestrator.py — Koldi orquestra, Atena executa
Roteador inteligente de tarefas. Elimina APIs externas.

Uso pelo Koldi:
    from orchestrator import KoldiOrchestrator
    orch = KoldiOrchestrator()
    resultado = orch.analyze_code(open("script.py").read())
"""
import hashlib
import time
import sys, os

# Adicionar core/ ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "core"))
from atena_bridge import AtenaBridge
from embedding_cache import EmbeddingCache

TEMP_MAP = {
    "code": 0.1,
    "analysis": 0.3,
    "creative": 0.8,
    "chat": 0.6,
    "search": 0.2,
    "summary": 0.3,
    "translate": 0.2,
}

SYSTEM_PROMPTS = {
    "code": "Voce e Atena, especialista em Python. Responda APENAS com codigo funcional e comentarios tecnicos em portugues.",
    "analysis": "Voce e Atena, analista tecnica. Seja precisa, estruturada e cite evidencias.",
    "creative": "Voce e Atena, co-criadora criativa. Explore possibilidades com profundidade e elegancia.",
    "summary": "Voce e Atena. Resuma de forma densa e sem perda de informacao essencial.",
    "translate": "Voce e Atena, tradutora profissional. Traduza mantendo o tom e contexto original.",
    "default": "Voce e Atena, assistente do Senhor Roberio. Responda em portugues do Brasil, de forma direta e clara.",
}


class KoldiOrchestrator:
    """Koldi orquestra, Atena (Ollama local) executa. Zero APIs externas."""
    
    def __init__(self, model: str = "atena-glm5"):
        self.bridge = AtenaBridge(model=model)
        self.cache = EmbeddingCache()
        
        if not self.bridge.health_check():
            raise RuntimeError("Atena (Ollama) nao esta acessivel em localhost:11434")
    
    def route(self, task_type: str, prompt: str, max_tokens: int = 512) -> dict:
        """Roteia tarefa para Atena com parametros otimizados."""
        import json as _json
        temperature = TEMP_MAP.get(task_type, 0.5)
        system = SYSTEM_PROMPTS.get(task_type, SYSTEM_PROMPTS["default"])
        
        start = time.time()
        response = self.bridge.ask(
            prompt=prompt, system=system,
            temperature=temperature, max_tokens=max_tokens
        )
        elapsed = time.time() - start
        
        prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()[:16]
        
        return {
            "response": response,
            "task_type": task_type,
            "temperature": temperature,
            "latency_ms": round(elapsed * 1000, 1),
            "prompt_hash": prompt_hash,
            "model": self.bridge.model,
        }
    
    def ask(self, question: str, temperature: float = 0.3) -> str:
        """Pergunta simples — atalho para o dia a dia."""
        result = self.route("chat", question, max_tokens=256)
        return result["response"]
    
    def analyze_code(self, code: str) -> str:
        """Analisa e sugere melhorias de codigo."""
        result = self.route("code", f"Analise e melhore este codigo:\n\n```\n{code}\n```", max_tokens=512)
        return result["response"]
    
    def summarize(self, text: str) -> str:
        """Resume texto preservando informacao tecnica."""
        result = self.route("summary", f"Resuma preservando informacao tecnica importante:\n\n{text}", max_tokens=300)
        return result["response"]
    
    def research(self, query: str, context: str = "") -> str:
        """Pesquisa em base de conhecimento."""
        prompt = f"Pesquise sobre: {query}"
        if context:
            prompt += f"\n\nContexto disponivel:\n{context}"
        result = self.route("analysis", prompt, max_tokens=512)
        return result["response"]
    
    def create(self, brief: str) -> str:
        """Cria conteudo criativo (texto, historia, poema)."""
        result = self.route("creative", brief, max_tokens=512)
        return result["response"]
    
    def embed(self, text: str) -> list[float]:
        """Gera embedding (com cache)."""
        return self.cache.get_or_compute(text)


if __name__ == "__main__":
    orch = KoldiOrchestrator()
    
    r = orch.ask("Diga seu nome em uma frase.", temperature=0.1)
    print(f"Resposta: {r}")
    
    stats = orch.cache.stats()
    print(f"Cache: {stats}")
