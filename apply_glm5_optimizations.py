#!/usr/bin/env python3
"""apply_glm5_optimizations.py — Aplica otimizações GLM-5 ao modelo local"""

import subprocess, json, logging, time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GLM5Optimizer")

def create_glm5_model():
    """Cria modelo GLM-5 otimizado no Ollama."""
    modelfile = "FROM phi4-mini:latest\nPARAMETER temperature 0.85\nPARAMETER top_p 0.92\nPARAMETER repeat_penalty 1.15\nPARAMETER num_ctx 8192\n"
    with open("Modelfile.glm5", "w") as f:
        f.write(modelfile)
    result = subprocess.run(["ollama", "create", "atena-glm5", "-f", "Modelfile.glm5"], capture_output=True, text=True, timeout=60)
    return result.returncode == 0

def test_glm5():
    """Testa o modelo GLM-5."""
    payload = {
        "model": "atena-glm5",
        "messages": [{"role": "user", "content": "Escreva um parágrafo literário sobre chuva."}],
        "stream": False,
        "options": {"temperature": 0.85, "num_predict": 100}
    }
    result = subprocess.run(["curl", "-s", "-X", "POST", "http://localhost:11434/api/chat", "-H", "Content-Type: application/json", "-d", json.dumps(payload)], capture_output=True, text=True, timeout=60)
    if result.returncode == 0:
        data = json.loads(result.stdout)
        return data.get("message", {}).get("content", "")
    return ""

if __name__ == "__main__":
    print("Criando modelo GLM-5...")
    if create_glm5_model():
        print("Modelo criado!")
        print("\nTestando...")
        response = test_glm5()
        print(f"Resposta: {response[:200]}")
    else:
        print("Erro ao criar modelo")
