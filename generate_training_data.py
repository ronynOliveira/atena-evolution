#!/usr/bin/env python3
"""
generate_training_data.py — Gera dados de treinamento no estilo dos contos

Usa o phi4-mini via Ollama para gerar textos no estilo do Senhor Robério.
Aplica as técnicas do GLM-5 para melhorar a qualidade.
"""

import subprocess
import json
import logging
import os
import time
from typing import List, Dict

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("TrainingDataGen")


def ollama_generate(
    model: str,
    prompt: str,
    system: str = "",
    max_tokens: int = 512,
    temperature: float = 0.8,
) -> str:
    """Gera texto via Ollama."""
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt}
        ],
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
        }
    }
    
    try:
        result = subprocess.run(
            ["curl", "-s", "-X", "POST",
             "http://localhost:11434/api/chat",
             "-H", "Content-Type: application/json",
             "-d", json.dumps(payload)],
            capture_output=True, text=True, timeout=120
        )
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return data.get("message", {}).get("content", "")
        return ""
    except Exception as e:
        logger.error(f"Erro: {e}")
        return ""


def generate_training_data():
    """Gera dados de treinamento no estilo dos contos."""
    
    SYSTEM_PROMPT = """Você é um escritor literário que escreve no estilo do Senhor Robério.

Características do estilo:
- Narrativa em primeira pessoa com profundidade psicológica
- Temas de memória, tempo, transcendência e solidão
- Prosa poética com fluxo de consciência
- Metáforas naturais (chuva, luar, ondas, vento, fogo)
- Tom melancólico, reflexivo e filosófico
- Frases longas e elaboradas com ritmo musical
- Referências mitológicas e filosóficas
- Sensorialidade rica (aromas, sons, texturas)
- Uso de travessões e elipses para pausas dramáticas
- Vocabulário sofisticado mas acessível

Escreva sempre em Português do Brasil."""
    
    # Prompts para gerar diferentes tipos de texto
    prompts = [
        # Contos curtos
        {
            "type": "conto",
            "prompt": "Escreva um conto curto (300-500 palavras) sobre uma casa antiga durante uma chuva noturna. Use narrativa em primeira pessoa, temas de memória e tempo, prosa poética.",
            "temperature": 0.8,
        },
        {
            "type": "conto",
            "prompt": "Escreva um conto curto (300-500 palavras) sobre alguém que encontra um objeto esquecido que desperta memórias. Use narrativa em primeira pessoa, tom melancólico e reflexivo.",
            "temperature": 0.8,
        },
        {
            "type": "conto",
            "prompt": "Escreva um conto curto (300-500 palavras) sobre uma noite de luar que evoca lembranças de um amor perdido. Use prosa poética, metáforas naturais, fluxo de consciência.",
            "temperature": 0.8,
        },
        {
            "type": "conto",
            "prompt": "Escreva um conto curto (300-500 palavras) sobre um viajante que chega a uma cidade deserta ao amanhecer. Use narrativa em primeira pessoa, temas de solidão e transcendência.",
            "temperature": 0.8,
        },
        {
            "type": "conto",
            "prompt": "Escreva um conto curto (300-500 palavras) sobre alguém que ouve uma música antiga e é transportado para o passado. Use sensorialidade rica, metáforas sonoras, tom nostálgico.",
            "temperature": 0.8,
        },
        # Análises de estilo
        {
            "type": "analise",
            "prompt": "Analise o estilo literário dos contos do Senhor Robério, identificando: 1) Narrativa (pessoa gramatical), 2) Temas recorrentes, 3) Figuras de linguagem preferidas, 4) Tom emocional, 5) Estrutura das frases, 6) Vocabulário característico. Seja detalhado e específico.",
            "temperature": 0.5,
        },
        # Exercícios de estilo
        {
            "type": "exercicio",
            "prompt": "Reescreva o seguinte trecho no estilo do Senhor Robério: 'A casa era velha e estava chovendo. Eu me lembrei de coisas do passado.' Use prosa poética, metáforas, fluxo de consciência.",
            "temperature": 0.7,
        },
        {
            "type": "exercicio",
            "prompt": "Escreva um parágrafo descritivo de uma paisagem noturna (300 palavras) no estilo do Senhor Robério, usando metáforas naturais, sensorialidade rica e tom contemplativo.",
            "temperature": 0.8,
        },
        # Diálogos internos
        {
            "type": "dialogo",
            "prompt": "Escreva um monólogo interior (400 palavras) de alguém que está em um jardim ao entardecer, refletindo sobre a passagem do tempo e as memórias que o lugar evoca. Use fluxo de consciência, perguntas retóricas, tom filosófico.",
            "temperature": 0.8,
        },
        {
            "type": "dialogo",
            "prompt": "Escreva um monólogo interior (400 palavras) de alguém que encontra uma fotografia antiga e é invadido por lembranças. Use narrativa em primeira pessoa, sensorialidade, tom melancólico.",
            "temperature": 0.8,
        },
    ]
    
    dataset = []
    
    for i, item in enumerate(prompts):
        logger.info(f"Gerando [{i+1}/{len(prompts)}]: {item['type']}")
        
        response = ollama_generate(
            model="phi4-mini:latest",
            prompt=item["prompt"],
            system=SYSTEM_PROMPT,
            max_tokens=512,
            temperature=item["temperature"],
        )
        
        if response:
            dataset.append({
                "type": item["type"],
                "instruction": item["prompt"],
                "input": "",
                "output": response,
            })
            logger.info(f"  ✓ Gerado ({len(response)} chars)")
        else:
            logger.warning(f"  ✗ Falha na geração")
        
        time.sleep(2)  # Pausa entre gerações
    
    return dataset


def save_dataset(dataset: List[Dict], output_path: str = "atena_generated_training.jsonl"):
    """Salva o dataset em formato JSONL."""
    with open(output_path, 'w', encoding='utf-8') as f:
        for item in dataset:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
    
    logger.info(f"Dataset salvo: {len(dataset)} exemplos → {output_path}")
    
    # Também salvar em formato legível
    readable_path = output_path.replace('.jsonl', '.txt')
    with open(readable_path, 'w', encoding='utf-8') as f:
        for i, item in enumerate(dataset):
            f.write(f"\n{'='*60}\n")
            f.write(f"[{i+1}] Tipo: {item['type']}\n")
            f.write(f"Instrução: {item['instruction'][:100]}...\n")
            f.write(f"\nResposta:\n{item['output'][:500]}...\n")
    
    logger.info(f"Versão legível: {readable_path}")


def main():
    logger.info("=" * 60)
    logger.info("GERAÇÃO DE DADOS DE TREINAMENTO")
    logger.info("=" * 60)
    
    # Verificar Ollama
    try:
        result = subprocess.run(
            ["curl", "-s", "http://localhost:11434/api/tags"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode != 0:
            logger.error("Ollama não está rodando!")
            return
    except:
        logger.error("Não foi possível conectar ao Ollama!")
        return
    
    logger.info("Ollama OK!")
    
    # Gerar dados
    dataset = generate_training_data()
    
    if dataset:
        save_dataset(dataset)
        
        # Estatísticas
        types = {}
        for item in dataset:
            t = item["type"]
            types[t] = types.get(t, 0) + 1
        
        logger.info("\nEstatísticas:")
        for t, count in types.items():
            logger.info(f"  {t}: {count} exemplos")
        
        total_chars = sum(len(item["output"]) for item in dataset)
        logger.info(f"Total: {len(dataset)} exemplos, {total_chars} caracteres")
    else:
        logger.error("Nenhum dado gerado!")


if __name__ == "__main__":
    main()
