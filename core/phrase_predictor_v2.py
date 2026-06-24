#!/usr/bin/env python3
"""
Koldi Phrase Predictor v2 — Predição de frases com backoff e temperatura.
Usa múltiplas ordens de n-gramas para ter mais variedade.
"""

import os, sys, json, re, pickle, random
from collections import defaultdict, Counter
from datetime import datetime

MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'models')
MODEL_FILE = os.path.join(MODEL_DIR, 'phrase_predictor_v2.pkl')
TEXTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'texts', 'senhor')


def tokenize(text):
    text = text.lower().strip()
    text = re.sub(r'([.,;:!?()\[\]{}"\'-])', r' \1 ', text)
    tokens = [t for t in text.split() if t.strip()]
    return tokens


def build_multi_ngrams(tokens, max_n=6):
    """Constrói n-gramas de múltiplas ordens para backoff."""
    models = {}
    for n in range(2, max_n + 1):
        ngrams = defaultdict(Counter)
        for i in range(len(tokens) - n + 1):
            context = tuple(tokens[i:i+n-1])
            next_token = tokens[i+n-1]
            ngrams[context][next_token] += 1
        models[n] = dict(ngrams)
    return models


def train_from_file(filepath, max_n=6):
    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()
    tokens = tokenize(text)
    models = build_multi_ngrams(tokens, max_n)
    
    return {
        'models': models,
        'max_n': max_n,
        'total_tokens': len(tokens),
        'source_file': os.path.basename(filepath),
        'trained_at': datetime.now().isoformat(),
    }


def merge_models(m1, m2):
    max_n = max(m1['max_n'], m2['max_n'])
    merged_models = {}
    
    for n in range(2, max_n + 1):
        merged = defaultdict(Counter)
        for context, counter in m1.get('models', {}).get(n, {}).items():
            merged[context].update(counter)
        for context, counter in m2.get('models', {}).get(n, {}).items():
            merged[context].update(counter)
        merged_models[n] = dict(merged)
    
    return {
        'models': merged_models,
        'max_n': max_n,
        'total_tokens': m1.get('total_tokens', 0) + m2.get('total_tokens', 0),
        'source_files': list(set(
            m1.get('source_files', [m1.get('source_file', [])]) + 
            m2.get('source_files', [m2.get('source_file', [])])
        )),
        'trained_at': datetime.now().isoformat(),
    }


def predict_with_backoff(models_dict, partial_text, max_words=25, temperature=0.8):
    """Prediz usando backoff: tenta n-grama maior primeiro, se não encontrar, reduz."""
    tokens = tokenize(partial_text)
    max_n = max(models_dict.keys()) if models_dict else 2
    result = list(tokens)
    
    for _ in range(max_words):
        found = False
        
        # Tentar da maior ordem para a menor
        for n in range(min(max_n, len(result) + 1), 1, -1):
            if n not in models_dict:
                continue
            context = tuple(result[-(n-1):])
            if context in models_dict[n]:
                counter = models_dict[n][context]
                
                # Escolher com temperatura
                candidates = counter.most_common()
                total = sum(c for _, c in candidates)
                
                if temperature <= 0.3:
                    # Baixa temperatura: sempre o mais comum
                    chosen = candidates[0][0]
                else:
                    # Com temperatura: amostrar
                    r = random.uniform(0, 1) * total * (1.0 / temperature)
                    cumulative = 0
                    chosen = candidates[0][0]
                    for token, count in candidates:
                        cumulative += count
                        if cumulative >= r:
                            chosen = token
                            break
                
                result.append(chosen)
                found = True
                break
        
        if not found:
            break
    
    # Reconstruir texto
    output = ' '.join(result)
    output = re.sub(r'\s+([.,;:!?])', r'\1', output)
    output = re.sub(r'^\s*([.,;:!?])', r'\1', output)
    if output:
        output = output[0].upper() + output[1:]
    return output


def predict_multiple(models_dict, partial_text, num_suggestions=3, max_words=20, temperature=0.8):
    """Gera múltiplas sugestões diferentes."""
    suggestions = []
    seen = set()
    
    for _ in range(num_suggestions * 3):  # Tentar mais vezes para ter variedade
        result = predict_with_backoff(models_dict, partial_text, max_words, temperature + random.uniform(-0.2, 0.3))
        if result not in seen and len(result) > len(partial_text) + 5:
            suggestions.append(result)
            seen.add(result)
        if len(suggestions) >= num_suggestions:
            break
    
    return suggestions


def save_model(model):
    os.makedirs(MODEL_DIR, exist_ok=True)
    with open(MODEL_FILE, 'wb') as f:
        pickle.dump(model, f)
    print(f"Modelo salvo: {MODEL_FILE} ({os.path.getsize(MODEL_FILE) // 1024}KB)")


def load_model():
    if not os.path.exists(MODEL_FILE):
        return None
    with open(MODEL_FILE, 'rb') as f:
        return pickle.load(f)


def stats(model):
    models_dict = model.get('models', {})
    total_contexts = sum(len(v) for v in models_dict.values())
    
    print(f"=== Koldi Phrase Predictor v2 ===")
    print(f"  N-gramas: 2-{model['max_n']}")
    print(f"  Tokens treinados: {model.get('total_tokens', '?')}")
    print(f"  Contextos totais: {total_contexts}")
    for n in sorted(models_dict.keys()):
        ctx = len(models_dict[n])
        transitions = sum(len(c) for c in models_dict[n].values())
        avg = transitions / ctx if ctx > 0 else 0
        print(f"  n={n}: {ctx} contextos, {transitions} transições (média {avg:.1f})")
    print(f"  Arquivos: {model.get('source_files', [model.get('source_file', '?')])}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python phrase_predictor_v2.py <train|predict|suggest|stats> [args]")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "train":
        if len(sys.argv) < 3:
            print("Uso: python phrase_predictor_v2.py train <arquivo.txt>")
            sys.exit(1)
        
        filepath = sys.argv[2]
        new_model = train_from_file(filepath)
        
        existing = load_model()
        if existing:
            model = merge_models(existing, new_model)
            print(f"Modelo atualizado com {os.path.basename(filepath)}")
        else:
            model = new_model
            print(f"Novo modelo treinado com {os.path.basename(filepath)}")
        
        save_model(model)
        stats(model)
    
    elif cmd == "predict":
        model = load_model()
        if not model:
            print("Modelo não treinado.")
            sys.exit(1)
        
        partial = " ".join(sys.argv[2:])
        result = predict_with_backoff(model['models'], partial)
        print(result)
    
    elif cmd == "suggest":
        model = load_model()
        if not model:
            print("Modelo não treinado.")
            sys.exit(1)
        
        partial = " ".join(sys.argv[2:])
        suggestions = predict_multiple(model['models'], partial, num_suggestions=3)
        for i, s in enumerate(suggestions, 1):
            print(f"{i}. {s}")
    
    elif cmd == "stats":
        model = load_model()
        if not model:
            print("Modelo não treinado.")
            sys.exit(1)
        stats(model)
    
    else:
        print(f"Comando desconhecido: {cmd}")
