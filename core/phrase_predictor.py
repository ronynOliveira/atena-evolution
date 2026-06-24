#!/usr/bin/env python3
"""
Koldi Phrase Predictor — Prediz frases completas baseado no padrão de escrita do Senhor.
Usa n-gramas extraídos dos textos do Senhor para sugerir continuações.

Uso:
  python phrase_predictor.py train <arquivo.txt>     # Treina com texto do Senhor
  python phrase_predictor.py predict <frase_parcial> # Sugere continuação
  python phrase_predictor.py stats                   # Mostra estatísticas do modelo
"""

import os
import sys
import json
import re
import pickle
from collections import defaultdict, Counter
from datetime import datetime

MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'models')
MODEL_FILE = os.path.join(MODEL_DIR, 'phrase_predictor.pkl')
TEXTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'texts', 'senhor')


def tokenize(text):
    """Tokeniza texto preservando pontuação como tokens separados."""
    text = text.lower().strip()
    # Separar pontuação das palavras
    text = re.sub(r'([.,;:!?()\[\]{}"\'-])', r' \1 ', text)
    tokens = text.split()
    return [t for t in tokens if t.strip()]


def build_ngrams(tokens, n=4):
    """Constrói n-gramas a partir de tokens."""
    ngrams = defaultdict(Counter)
    for i in range(len(tokens) - n + 1):
        context = tuple(tokens[i:i+n-1])
        next_token = tokens[i+n-1]
        ngrams[context][next_token] += 1
    return ngrams


def train_from_file(filepath, n=4):
    """Treina o modelo com um arquivo de texto."""
    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()
    
    tokens = tokenize(text)
    ngrams = build_ngrams(tokens, n)
    
    return {
        'ngrams': dict(ngrams),
        'n': n,
        'total_tokens': len(tokens),
        'source_file': os.path.basename(filepath),
        'trained_at': datetime.now().isoformat(),
    }


def merge_models(model1, model2):
    """Merge dois modelos de n-gramas."""
    n = model1['n']
    merged_ngrams = defaultdict(Counter)
    
    for context, counter in model1.get('ngrams', {}).items():
        merged_ngrams[context].update(counter)
    
    for context, counter in model2.get('ngrams', {}).items():
        merged_ngrams[context].update(counter)
    
    return {
        'ngrams': dict(merged_ngrams),
        'n': n,
        'total_tokens': model1.get('total_tokens', 0) + model2.get('total_tokens', 0),
        'source_files': model1.get('source_files', [model1.get('source_file', '?')]) + 
                       model2.get('source_files', [model2.get('source_file', '?')]),
        'trained_at': datetime.now().isoformat(),
    }


def predict(model, partial_text, max_words=20, temperature=0.7):
    """Prediz continuação de uma frase parcial."""
    n = model['n']
    ngrams = model.get('ngrams', {})
    
    tokens = tokenize(partial_text)
    if len(tokens) < n - 1:
        # Poucos tokens — buscar por prefixo
        return predict_from_prefix(ngrams, tokens, max_words, temperature)
    
    result = list(tokens)
    
    for _ in range(max_words):
        context = tuple(result[-(n-1):])
        
        if context in ngrams:
            counter = ngrams[context]
            # Escolher próximo token com temperatura
            candidates = counter.most_common()
            total = sum(c for _, c in candidates)
            
            import random
            r = random.uniform(0, 1) * total
            cumulative = 0
            chosen = candidates[0][0]  # fallback: mais comum
            
            for token, count in candidates:
                cumulative += count
                if cumulative >= r:
                    chosen = token
                    break
            
            result.append(chosen)
        else:
            # Contexto não encontrado — parar
            break
    
    # Reconstruir texto
    output = ' '.join(result)
    # Limpar espaços antes de pontuação
    output = re.sub(r'\s+([.,;:!?])', r'\1', output)
    # Capitalizar primeira letra
    if output:
        output = output[0].upper() + output[1:]
    
    return output


def predict_from_prefix(ngrams, prefix_tokens, max_words, temperature):
    """Busca n-gramas que começam com o prefixo dado."""
    prefix = tuple(prefix_tokens)
    matches = []
    
    for context, counter in ngrams.items():
        if context[:len(prefix)] == prefix:
            for token, count in counter.items():
                matches.append((token, count, context))
    
    if not matches:
        return ' '.join(prefix_tokens).capitalize()
    
    # Escolher o mais comum
    matches.sort(key=lambda x: -x[1])
    next_token = matches[0][0]
    
    result = list(prefix_tokens) + [next_token]
    
    # Continuar predição
    import random
    for _ in range(max_words - 1):
        context = tuple(result[-(len(prefix)+1):])
        if context in ngrams:
            counter = ngrams[context]
            chosen = counter.most_common(1)[0][0]
            result.append(chosen)
        else:
            break
    
    output = ' '.join(result)
    output = re.sub(r'\s+([.,;:!?])', r'\1', output)
    if output:
        output = output[0].upper() + output[1:]
    return output


def save_model(model):
    """Salva modelo em arquivo."""
    os.makedirs(MODEL_DIR, exist_ok=True)
    with open(MODEL_FILE, 'wb') as f:
        pickle.dump(model, f)
    print(f"Modelo salvo em {MODEL_FILE}")


def load_model():
    """Carrega modelo do arquivo."""
    if not os.path.exists(MODEL_FILE):
        return None
    with open(MODEL_FILE, 'rb') as f:
        return pickle.load(f)


def stats(model):
    """Mostra estatísticas do modelo."""
    ngrams = model.get('ngrams', {})
    total_contexts = len(ngrams)
    total_transitions = sum(len(c) for c in ngrams.values())
    avg_choices = total_transitions / total_contexts if total_contexts > 0 else 0
    
    print(f"=== Koldi Phrase Predictor Stats ===")
    print(f"  N-grama ordem:     {model['n']}")
    print(f"  Contextos únicos:  {total_contexts}")
    print(f"  Transições totais: {total_transitions}")
    print(f"  Média escolhas:    {avg_choices:.1f}")
    print(f"  Tokens treinados:  {model.get('total_tokens', '?')}")
    print(f"  Arquivos:          {model.get('source_files', [model.get('source_file', '?')])}")
    print(f"  Treinado em:       {model.get('trained_at', '?')}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python phrase_predictor.py <train|predict|stats|add> [args]")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "train":
        if len(sys.argv) < 3:
            print("Uso: python phrase_predictor.py train <arquivo.txt>")
            sys.exit(1)
        
        filepath = sys.argv[2]
        if not os.path.exists(filepath):
            print(f"Arquivo não encontrado: {filepath}")
            sys.exit(1)
        
        new_model = train_from_file(filepath)
        
        # Se já existe modelo, fazer merge
        existing = load_model()
        if existing:
            model = merge_models(existing, new_model)
            print(f"Modelo atualizado com {os.path.basename(filepath)}")
        else:
            model = new_model
            print(f"Novo modelo treinado com {os.path.basename(filepath)}")
        
        save_model(model)
        stats(model)
    
    elif cmd == "add":
        # Adicionar texto ao corpus
        if len(sys.argv) < 3:
            print("Uso: python phrase_predictor.py add <arquivo_ou_texto>")
            sys.exit(1)
        
        arg = sys.argv[2]
        os.makedirs(TEXTS_DIR, exist_ok=True)
        
        if os.path.exists(arg):
            # É arquivo — copiar para corpus
            dest = os.path.join(TEXTS_DIR, os.path.basename(arg))
            with open(arg, 'r', encoding='utf-8') as f:
                text = f.read()
            with open(dest, 'w', encoding='utf-8') as f:
                f.write(text)
            print(f"Texto adicionado ao corpus: {dest}")
        else:
            # É texto direto
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            dest = os.path.join(TEXTS_DIR, f'input_{timestamp}.txt')
            with open(dest, 'w', encoding='utf-8') as f:
                f.write(arg)
            print(f"Texto salvo: {dest}")
    
    elif cmd == "predict":
        model = load_model()
        if not model:
            print("Modelo não treinado. Use 'train' primeiro.")
            sys.exit(1)
        
        partial = " ".join(sys.argv[2:])
        if not partial:
            print("Uso: python phrase_predictor.py predict <frase parcial>")
            sys.exit(1)
        
        result = predict(model, partial)
        print(result)
    
    elif cmd == "stats":
        model = load_model()
        if not model:
            print("Modelo não treinado.")
            sys.exit(1)
        stats(model)
    
    else:
        print(f"Comando desconhecido: {cmd}")
