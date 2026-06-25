#!/usr/bin/env python3
"""
Otimizador de Modelos para CPU - Atena Evolucao
================================================
Remove todos os modelos exceto 2 Gemma 4B quantizados.
Foco: maximizar velocidade em CPU com 15GB RAM.

Uso:
    python otimizar_cpu.py           # Executa
    python otimizar_cpu.py --dry-run # Simula
"""
import subprocess, sys, os, json, time
from pathlib import Path

OLLAMA_URL = "http://localhost:11434"
KEEP_MODELS = ["gemma4:e2b", "nomic-embed-text:latest"]
REMOVE_OTHERS = True

def get_models():
    try:
        req = __import__('urllib.request', fromlist=['urlopen']).Request(f"{OLLAMA_URL}/api/tags")
        with __import__('urllib.request', fromlist=['urlopen']).urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("data", data.get("models", []))
    except Exception as e:
        print(f"Erro ao listar: {e}")
        return []

def remove_model(name):
    try:
        result = subprocess.run(
            ["ollama", "rm", name],
            capture_output=True, text=True, timeout=60
        )
        return result.returncode == 0
    except Exception as e:
        print(f"Erro removendo {name}: {e}")
        return False

def pull_model(name):
    try:
        print(f"Baixando {name}...")
        result = subprocess.run(
            ["ollama", "pull", name],
            capture_output=True, text=True, timeout=600
        )
        return result.returncode == 0
    except Exception as e:
        print(f"Erro baixando {name}: {e}")
        return False

def benchmark_model(name, prompt="Ola! Quem e voce?"):
    try:
        import urllib.request
        payload = json.dumps({
            "model": name,
            "prompt": prompt,
            "stream": False,
            "options": {"num_predict": 30}
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{OLLAMA_URL}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"}
        )
        start = time.time()
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            elapsed = time.time() - start
            tokens = result.get("eval_count", 0)
            return elapsed, tokens
    except:
        return None, None

def main():
    print("=" * 60)
    print("OTIMIZADOR DE MODELOS CPU - ATENA EVOLUCAO")
    print("=" * 60)
    
    # 1. Listar modelos
    print("\n[1/4] Listando modelos...")
    models = get_models()
    if not models:
        print("  ERRO: Ollama offline ou sem modelos")
        return
    
    print(f"  Encontrados: {len(models)} modelos")
    for m in models:
        size_gb = m.get("size", 0) / (1024**3)
        print(f"    - {m['name']:35s} {size_gb:.1f}GB")
    
    # 2. Classificar
    print("\n[2/4] Classificando modelos...")
    keep = []
    remove = []
    for m in models:
        name = m["name"]
        if name in KEEP_MODELS or any(k in name for k in KEEP_MODELS):
            keep.append(name)
            print(f"  MANTER: {name}")
        else:
            remove.append(name)
            print(f"  REMOVER: {name}")
    
    # 3. Benchmark dos que vao ficar
    print("\n[3/4] Benchmark dos modelos mantidos...")
    for name in keep:
        elapsed, tokens = benchmark_model(name)
        if elapsed:
            speed = tokens / elapsed if elapsed > 0 else 0
            print(f"  {name}: {elapsed:.1f}s ({tokens} tokens, {speed:.1f} tok/s)")
        else:
            print(f"  {name}: ERRO no benchmark")
    
    # 4. Remover
    print(f"\n[4/4] Removendo {len(remove)} modelos...")
    if "--dry-run" in sys.argv:
        print("  (DRY-RUN: nada sera alterado)")
        for name in remove:
            print(f"  [SIMULADO] Removido: {name}")
    else:
        for name in remove:
            print(f"  Removendo {name}...", end=" ", flush=True)
            if remove_model(name):
                print("OK")
            else:
                print("FALHA")
    
    print("\n" + "=" * 60)
    print("OTIMIZACAO CONCLUIDA")
    print(f"  Mantidos: {keep}")
    print(f"  Removidos: {len(remove)}")
    print(f"  Modelos para download recomendados:")
    print(f"    ollama pull gemma4:e2b")
    print(f"    ollama pull nomic-embed-text")
    print("=" * 60)

if __name__ == "__main__":
    main()
