# Plano de Otimização CPU-Only com Ollama

> **Hardware:** Intel i5-1235U (10 cores / 12 threads), 15GB RAM, sem GPU  
> **Objetivo:** Maximizar velocidade sem perder qualidade usando apenas 2 modelos locais  
> **Data:** Junho/2026

---

## 1. Melhor Combinação de 2 Modelos (Chat Rápido + RAG Qualidade)

### Recomendação Principal

| Função | Modelo | Justificativa |
|--------|--------|---------------|
| **Chat Rápido** | `qwen2.5:7b-instruct` | Excelente latência em CPU, suporte multilíngue nativo (PT-BR), boa coerência, ~4GB RAM |
| **RAG/Qualidade** | `mistral:7b-instruct-v0.3` | Superior em raciocínio complexo, melhor aproveitamento de contexto, ~4.1GB RAM |

### Alternativas por Cenário

| Prioridade | Chat Rápido | RAG/Qualidade | Observação |
|------------|-------------|---------------|------------|
| **Velocidade máxima** | `qwen2.5:1.5b` | `qwen2.5:7b` | 1.5b é extremamente rápido para chat simples |
| **Qualidade máxima** | `qwen2.5:7b` | `mistral:7b` (Q5_K_M) | Q5_K_M consome ~5GB mas qualidade notável |
| **Português otimizado** | `qwen2.5:7b` | `qwen2.5:14b` (Q4_K_M) | 14b Q4_K_M cabe em ~8GB, qualidade superior |
| **Menor RAM** | `phi3:3.8b-mini` | `mistral:7b` (Q4_0) | phi3 é leve e surpreendentemente capaz |

### Por que essa combinação?

```
┌─────────────────────────────────────────────────────────┐
│                    FLUXO DE USO                         │
│                                                         │
│  Usuário ──► qwen2.5:7b (chat rápido)                  │
│                    │                                    │
│                    ▼ (se precisa de qualidade/RAG)      │
│                                                         │
│  Contexto + Docs ──► mistral:7b (RAG + raciocínio)     │
│                    │                                    │
│                    ▼                                    │
│              Resposta de alta qualidade                  │
└─────────────────────────────────────────────────────────┘
```

- **qwen2.5:7b**: ~1.5s primeira token em i5-1235U, tokens seguintes ~30ms
- **mistral:7b**: ~2s primeira token, tokens seguintes ~40ms
- Ambos cabem confortavelmente nos 15GB RAM com folga para embeddings

### Comandos para Download

```bash
# Modelo de chat rápido
ollama pull qwen2.5:7b-instruct-q4_K_M

# Modelo de qualidade/RAG
ollama pull mistral:7b-instruct-v0.3-q4_K_M

# Modelo de embeddings
ollama pull nomic-embed-text

# Verificar modelos instalados
ollama list
```

---

## 2. Parâmetros de Configuração do Ollama para CPU

### 2.1 Variáveis de Ambiente (Systemd/Service ou .env)

```bash
# Arquivo: ~/.ollama/Environment ou /etc/systemd/system/ollama.service.d/override.conf

# === CPU ===
export OLLAMA_NUM_PARALLEL=1          # Requisições simultâneas (1 para CPU)
export OLLAMA_MAX_LOADED_MODELS=2    # Máximo de modelos em RAM (nosso caso: 2)
export OLLAMA_KEEP_ALIVE=5m          # Manter modelo carregado por 5 min
export OLLAMA_DEBUG=0                # Desativar debug em produção

# === Threads e CPU ===
export OLLAMA_NUM_THREAD=10          # 10 cores físicos do i5-1235U
export OLLAMA_NUMA=0                 # Desativar NUMA (single-socket)

# === Memória ===
export OLLAMA_MAX_MEMORY=0           # 0 = deixar Ollama gerenciar automaticamente
```

### 2.2 Parâmetros por Requisição (API)

```json
{
  "model": "qwen2.5:7b-instruct",
  "prompt": "Sua pergunta aqui",
  "stream": true,
  "options": {
    "num_ctx": 2048,
    "num_batch": 512,
    "num_gpu": 0,
    "num_thread": 10,
    "temperature": 0.7,
    "top_k": 40,
    "top_p": 0.9,
    "repeat_penalty": 1.1,
    "num_predict": 1024,
    "stop": ["\n\n\n", "---"]
  }
}
```

### 2.3 Tabela de Parâmetros e Valores Recomendados

| Parâmetro | Valor Recomendado | Descrição | Impacto |
|-----------|-------------------|-----------|---------|
| `num_ctx` | 2048-4096 | Tamanho da janela de contexto | Menor = mais rápido, maior = mais contexto |
| `num_batch` | 512-1024 | Tamanho do batch de processamento | Maior = mais throughput em CPU |
| `num_gpu` | 0 | Desativar GPU (CPU-only) | Obrigatório |
| `num_thread` | 10 | Threads CPU (cores físicos) | Usar todos os cores |
| `num_predict` | 512-2048 | Máximo de tokens a gerar | Limitar para evitar demora |
| `temperature` | 0.3-0.7 | Criatividade | Menor = mais determinístico |
| `top_k` | 40 | Top-k sampling | Controla diversidade |
| `top_p` | 0.9 | Nucleus sampling | Controla diversidade |
| `repeat_penalty` | 1.1 | Penalidade de repetição | Evita loops |
| `num_keep` | 0 | Tokens a manter do prefixo | 0 para chat normal |
| `seed` | -1 | Seed aleatório | Fixar para reprodutibilidade |

### 2.4 Configuração no Windows (PowerShell/CMD)

```powershell
# Criar arquivo de configuração do Ollama
# Caminho: C:\Users\dell-\.ollama\env

# Ou definir variáveis de ambiente permanentemente:
[System.Environment]::SetEnvironmentVariable("OLLAMA_NUM_THREAD", "10", "User")
[System.Environment]::SetEnvironmentVariable("OLLAMA_MAX_LOADED_MODELS", "2", "User")
[System.Environment]::SetEnvironmentVariable("OLLAMA_KEEP_ALIVE", "5m", "User")
[System.Environment]::SetEnvironmentVariable("OLLAMA_NUM_PARALLEL", "1", "User")
```

### 2.5 Configuração no Linux (systemd)

```ini
# /etc/systemd/system/ollama.service.d/cpu-optimization.conf
[Service]
Environment="OLLAMA_NUM_THREAD=10"
Environment="OLLAMA_MAX_LOADED_MODELS=2"
Environment="OLLAMA_KEEP_ALIVE=5m"
Environment="OLLAMA_NUM_PARALLEL=1"
```

```bash
sudo systemctl daemon-reload
sudo systemctl restart ollama
```

---

## 3. Implementação de RAG Eficiente com Embeddings Locais

### 3.1 Arquitetura RAG

```
┌──────────────────────────────────────────────────────────────┐
│                    PIPELINE RAG LOCAL                        │
│                                                              │
│  ┌─────────┐    ┌──────────────┐    ┌───────────────────┐   │
│  │ Documento│───►│ nomic-embed  │───►│ Vetores (SQLite/  │   │
│  │ (PDF/TXT)│    │ -text (local)│    │ ChromaDB/LanceDB) │   │
│  └─────────┘    └──────────────┘    └─────────┬─────────┘   │
│                                                │             │
│  ┌─────────┐    ┌──────────────┐    ┌─────────▼─────────┐   │
│  │Resposta │◄───│ mistral:7b   │◄───│ Recuperação por   │   │
│  │ Final   │    │ (RAG model)  │    │ Similaridade      │   │
│  └─────────┘    └──────────────┘    └───────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

### 3.2 Indexação de Documentos

```python
# rag_index.py - Script de indexação
import requests
import os
import hashlib
import sqlite3
from pathlib import Path

OLLAMA_URL = "http://localhost:11434"
EMBED_MODEL = "nomic-embed-text"
DB_PATH = "./rag_vectors.db"

def init_db():
    """Inicializa o banco de dados de vetores."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS chunks (
            id TEXT PRIMARY KEY,
            content TEXT NOT NULL,
            source TEXT,
            embedding TEXT,  # JSON array
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_source ON chunks(source)")
    conn.commit()
    return conn

def get_embedding(text: str) -> list:
    """Obtém embedding via Ollama API."""
    response = requests.post(
        f"{OLLAMA_URL}/api/embeddings",
        json={
            "model": EMBED_MODEL,
            "prompt": text,
            "options": {
                "num_ctx": 2048,
                "num_batch": 1
            }
        }
    )
    response.raise_for_status()
    return response.json()["embedding"]

def chunk_document(text: str, chunk_size: int = 512, overlap: int = 50) -> list:
    """Divide documento em chunks com overlap."""
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i + chunk_size])
        if chunk.strip():
            chunks.append(chunk)
    return chunks

def index_file(filepath: str, conn):
    """Indexa um documento."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    chunks = chunk_document(content)
    source = os.path.basename(filepath)
    
    for i, chunk in enumerate(chunks):
        chunk_id = hashlib.md5(f"{source}_{i}_{chunk[:50]}".encode()).hexdigest()
        embedding = get_embedding(chunk)
        
        conn.execute(
            "INSERT OR REPLACE INTO chunks (id, content, source, embedding) VALUES (?, ?, ?, ?)",
            (chunk_id, chunk, source, str(embedding))
        )
    
    conn.commit()
    print(f"Indexado: {filepath} ({len(chunks)} chunks)")

if __name__ == "__main__":
    conn = init_db()
    # Indexar documentos em ./docs/
    docs_dir = Path("./docs")
    for doc in docs_dir.glob("*.txt"):
        index_file(str(doc), conn)
    conn.close()
```

### 3.3 Recuperação e Geração (RAG Query)

```python
# rag_query.py - Script de consulta RAG
import requests
import sqlite3
import json
import numpy as np

OLLAMA_URL = "http://localhost:11434"
EMBED_MODEL = "nomic-embed-text"
CHAT_MODEL = "mistral:7b-instruct-v0.3"
DB_PATH = "./rag_vectors.db"

def cosine_similarity(a, b):
    """Calcula similaridade cosseno entre dois vetores."""
    a, b = np.array(a), np.array(b)
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def search_chunks(query: str, top_k: int = 5) -> list:
    """Busca os chunks mais relevantes."""
    query_embedding = get_embedding(query)
    
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT id, content, source, embedding FROM chunks").fetchall()
    conn.close()
    
    results = []
    for row in rows:
        chunk_embedding = json.loads(row[3])
        similarity = cosine_similarity(query_embedding, chunk_embedding)
        results.append({
            "id": row[0],
            "content": row[1],
            "source": row[2],
            "similarity": similarity
        })
    
    results.sort(key=lambda x: x["similarity"], reverse=True)
    return results[:top_k]

def get_embedding(text: str) -> list:
    """Obtém embedding via Ollama API."""
    response = requests.post(
        f"{OLLAMA_URL}/api/embeddings",
        json={
            "model": EMBED_MODEL,
            "prompt": text
        }
    )
    return response.json()["embedding"]

def rag_query(question: str) -> str:
    """Executa consulta RAG completa."""
    # 1. Buscar contexto relevante
    chunks = search_chunks(question, top_k=3)
    context = "\n\n".join([f"[Fonte: {c['source']}]\n{c['content']}" for c in chunks])
    
    # 2. Construir prompt com contexto
    prompt = f"""Com base no contexto abaixo, responda à pergunta de forma precisa e completa.

CONTEXTO:
{context}

PERGUNTA:
{question}

RESPOSTA:"""
    
    # 3. Gerar resposta com modelo de qualidade
    response = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={
            "model": CHAT_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_ctx": 4096,
                "num_batch": 512,
                "num_gpu": 0,
                "num_thread": 10,
                "temperature": 0.3,
                "num_predict": 1024,
                "repeat_penalty": 1.1
            }
        }
    )
    
    return response.json()["response"]

if __name__ == "__main__":
    question = "Qual é o processo de indexação de documentos?"
    answer = rag_query(question)
    print(f"Resposta: {answer}")
```

### 3.4 Usando ChromaDB (Alternativa Robusta)

```bash
# Instalar dependências
pip install chromadb
```

```python
# rag_chromadb.py - RAG com ChromaDB
import chromadb
from chromadb.utils import embedding_functions
import requests

# Configurar embedding function do Ollama
ollama_ef = embedding_functions.OllamaEmbeddingFunction(
    url="http://localhost:11434/api/embeddings",
    model_name="nomic-embed-text"
)

# Criar cliente ChromaDB
client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_or_create_collection(
    name="documentos",
    embedding_function=ollama_ef
)

# Adicionar documentos
collection.add(
    documents=["Texto do documento 1...", "Texto do documento 2..."],
    metadatas=[{"source": "doc1.txt"}, {"source": "doc2.txt"}],
    ids=["doc1", "doc2"]
)

# Buscar documentos relevantes
results = collection.query(
    query_texts=["pergunta do usuário"],
    n_results=3
)
```

### 3.5 Otimizações para RAG em CPU

| Técnica | Implementação | Ganho |
|---------|---------------|-------|
| **Chunk size menor** | 256-512 tokens | Embeddings mais rápidos |
| **Overlap mínimo** | 20-50 tokens | Menos chunks redundantes |
| **Top-K baixo** | 2-3 chunks | Menos tokens no prompt |
| **Cache de embeddings** | SQLite/ChromaDB | Evita re-computação |
| **Batch de embeddings** | Processar múltiplos chunks | Melhor uso de CPU |
| **Filtro por metadados** | Pré-filtrar por categoria | Reduz espaço de busca |

---

## 4. Técnicas de Otimização de Prompt para Modelos Menores

### 4.1 Estrutura de Prompt Otimizada

```markdown
# Template de prompt para máxima qualidade em modelos 7b

[INST]
Você é um assistente especializado em [DOMÍNIO]. 
Responda SEMPRE em português brasileiro.

REGRAS:
1. Seja conciso e direto
2. Use apenas informações fornecidas no contexto
3. Se não souber, diga "Não tenho informação suficiente"
4. Estruture respostas com bullet points quando apropriado

CONTEXTO:
{context}

PERGUNTA:
{question}

RESPOSTA DIRETA E OBJETIVA:
[/INST]
```

### 4.2 Técnicas por Complexidade

| Técnica | Quando Usar | Exemplo |
|---------|-------------|---------|
| **Zero-shot** | Tarefas simples | "Resuma este texto:" |
| **Few-shot (1-3 exemplos)** | Formato específico | "Exemplo 1: ... Exemplo 2: ... Agora faça o mesmo:" |
| **Chain-of-Thought** | Raciocínio lógico | "Pense passo a passo antes de responder" |
| **Role-playing** | Domínios específicos | "Você é um especialista em X com 20 anos de experiência" |
| **Structured output** | Extração de dados | "Retorne JSON com campos: nome, idade, cidade" |
| **Negative instructions** | Evitar alucinações | "NÃO invente informações. Se não sabe, diga 'não sei'" |

### 4.3 Exemplos Práticos

#### Few-shot para classificação:
```
Classifique o sentimento como POSITIVO, NEGATIVO ou NEUTRO.

Exemplo 1: "Adorei o produto, chegou antes do prazo!" → POSITIVO
Exemplo 2: "Péssima qualidade, não recomendo." → NEGATIVO
Exemplo 3: "O produto é ok, nada demais." → NEUTRO

Agora classifique: "A entrega atrasou mas o produto é bom."
```

#### Chain-of-Thought para raciocínio:
```
Resolva passo a passo:

Se um carro percorre 120km em 2 horas, e depois percorre 
mais 180km em 3 horas, qual a velocidade média total?

Vamos calcular:
1. Distância total = 120 + 180 = 300km
2. Tempo total = 2 + 3 = 5 horas
3. Velocidade média = 300 / 5 = 60 km/h

Resposta: 60 km/h
```

#### Prompt anti-alucinação:
```
Com base EXCLUSIVAMENTE no contexto abaixo, responda à pergunta.
Se a informação não estiver no contexto, responda: 
"Não encontrei essa informação no contexto fornecido."

CONTEXTO: {context}
PERGUNTA: {question}
```

### 4.4 Parâmetros de Prompt Avançados

```python
# Configuração ideal para diferentes tarefas

PROMPT_CONFIGS = {
    "chat_rapido": {
        "temperature": 0.7,
        "top_k": 40,
        "top_p": 0.9,
        "repeat_penalty": 1.1,
        "num_predict": 512,
        "system": "Assistente rápido e útil. Seja conciso."
    },
    "rag_qualidade": {
        "temperature": 0.2,        # Mais determinístico
        "top_k": 20,               # Menos diversidade
        "top_p": 0.85,
        "repeat_penalty": 1.05,
        "num_predict": 2048,
        "system": "Especialista completo. Forneça respostas detalhadas e precisas."
    },
    "classificacao": {
        "temperature": 0.1,        # Quase determinístico
        "top_k": 10,
        "top_p": 0.5,
        "repeat_penalty": 1.0,
        "num_predict": 64,
        "system": "Classificador. Retorne apenas a categoria."
    },
    "sumarizacao": {
        "temperature": 0.3,
        "top_k": 30,
        "top_p": 0.8,
        "repeat_penalty": 1.15,
        "num_predict": 1024,
        "system": "Resumista. Extraia os pontos principais."
    }
}
```

### 4.5 Dicas de Ouro para Modelos em CPU

1. **Seja explícito no formato de saída** - "Liste em bullets:" vs "Responda:"
2. **Limite o escopo** - "Em no máximo 3 frases:" ou "Use até 100 palavras:"
3. **Forneça o formato esperado** - Mostre o template da resposta
4. **Evite ambiguidades** - "Liste os 3 principais" vs "Liste os principais"
5. **Use delimitadores claros** - `"""`, `---`, `###` para separar seções
6. **Instrua o modelo a pensar** - "Analise cuidadosamente antes de responder"
7. **Prefira instruções positivas** - "Faça X" em vez de "Não faça Y"

---

## 5. Configuração de Cache de KV e Batching

### 5.1 Cache de KV (Key-Value)

O cache de KV armazena os tokens já processados para evitar re-computação em conversas longas.

```bash
# O Ollama gerencia KV cache automaticamente, mas podemos otimizar:

# 1. Manter modelo aquecido (evita recarregar)
export OLLAMA_KEEP_ALIVE=-1       # Nunca descarregar modelo
# ou
export OLLAMA_KEEP_ALIVE=30m      # Manter por 30 minutos

# 2. Limitar contexto para evitar uso excessivo de memória
# Na API:
curl http://localhost:11434/api/generate -d '{
  "model": "qwen2.5:7b",
  "prompt": "...",
  "options": {
    "num_ctx": 2048,             # Limitar contexto (padrão pode ser 4096+)
    "num_batch": 512
  }
}'
```

### 5.2 Batching (Processamento em Lote)

```python
# batch_processor.py - Processamento em lote otimizado
import requests
import concurrent.futures
import time

OLLAMA_URL = "http://localhost:11434"

def process_single(prompt: str, model: str = "qwen2.5:7b") -> dict:
    """Processa um único prompt."""
    start = time.time()
    response = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_ctx": 2048,
                "num_batch": 512,     # Batch size para processamento
                "num_thread": 10,
                "num_predict": 512
            }
        }
    )
    elapsed = time.time() - start
    return {
        "response": response.json()["response"],
        "time": elapsed,
        "tokens": response.json().get("eval_count", 0)
    }

def process_batch(prompts: list, model: str = "qwen2.5:7b") -> list:
    """Processa múltiplos prompts sequencialmente (CPU)."""
    # Em CPU, processamento sequencial é mais eficiente que paralelo
    # devido à limitação de cores
    results = []
    for prompt in prompts:
        result = process_single(prompt, model)
        results.append(result)
    return results

# Para processamento paralelo (cuidado com CPU):
def process_parallel(prompts: list, model: str = "qwen2.5:7b", max_workers: int = 2) -> list:
    """Processa em paralelo com limite de workers."""
    # max_workers=2 é conservador para não saturar CPU
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(process_single, p, model) for p in prompts]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]
    return results
```

### 5.3 Configuração de Batching por Cenário

```python
# batch_configs.py

BATCH_CONFIGS = {
    # Para chat interativo (latência mínima)
    "interactive": {
        "num_ctx": 2048,
        "num_batch": 256,          # Menor batch = resposta mais rápida
        "num_thread": 10,
        "num_predict": 512,
        "OLLAMA_NUM_PARALLEL": 1   # Uma requisição por vez
    },
    
    # Para processamento em lote (throughput máximo)
    "batch": {
        "num_ctx": 4096,
        "num_batch": 1024,         # Maior batch = mais tokens/seg
        "num_thread": 10,
        "num_predict": 1024,
        "OLLAMA_NUM_PARALLEL": 2   # Duas requisições simultâneas
    },
    
    # Para RAG (contexto longo)
    "rag": {
        "num_ctx": 8192,           # Contexto maior para documentos
        "num_batch": 512,
        "num_thread": 10,
        "num_predict": 2048,
        "OLLAMA_NUM_PARALLEL": 1
    },
    
    # Para embeddings (velocidade pura)
    "embedding": {
        "num_ctx": 2048,
        "num_batch": 2048,         # Embeddings se beneficiam de batches grandes
        "num_thread": 10
    }
}
```

### 5.4 Script de Benchmark

```python
# benchmark.py - Medir performance em CPU
import requests
import time
import json

OLLAMA_URL = "http://localhost:11434"

def benchmark_model(model: str, prompt: str, runs: int = 5):
    """Benchmark de um modelo no Ollama."""
    times = []
    tokens_per_sec = []
    
    for i in range(runs):
        start = time.time()
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_ctx": 2048,
                    "num_batch": 512,
                    "num_thread": 10,
                    "num_predict": 256
                }
            }
        )
        elapsed = time.time() - start
        data = response.json()
        
        eval_count = data.get("eval_count", 0)
        eval_duration = data.get("eval_duration", 1) / 1e9  # ns to s
        
        times.append(elapsed)
        if eval_duration > 0:
            tokens_per_sec.append(eval_count / eval_duration)
    
    print(f"\n=== {model} ===")
    print(f"Latência média: {sum(times)/len(times):.2f}s")
    print(f"Min/Max: {min(times):.2f}s / {max(times):.2f}s")
    if tokens_per_sec:
        print(f"Tokens/s: {sum(tokens_per_sec)/len(tokens_per_sec):.1f}")

if __name__ == "__main__":
    test_prompt = "Explique o que é machine learning em 3 frases."
    
    print("Benchmark de modelos em CPU (i5-1235U):")
    benchmark_model("qwen2.5:7b", test_prompt)
    benchmark_model("mistral:7b", test_prompt)
```

### 5.5 Monitoramento de Recursos

```bash
# Monitorar uso de CPU e memória em tempo real
# Linux:
watch -n 1 'echo "=== CPU ===" && top -bn1 | head -5 && echo "=== RAM ===" && free -h && echo "=== Ollama ===" && ps aux | grep ollama | grep -v grep'

# Verificar status do Ollama
curl http://localhost:11434/api/ps | python -m json.tool

# Resposta exemplo:
# {
#   "models": [
#     {
#       "name": "qwen2.5:7b",
#       "size": 5482464676,
#       "digest": "abc123...",
#       "details": { ... },
#       "model_info": { ... },
#       "expires_at": "2026-06-25T15:30:00Z"
#     }
#   ]
# }
```

---

## Resumo de Comandos Essenciais

```bash
# 1. Instalar modelos
ollama pull qwen2.5:7b-instruct-q4_K_M
ollama pull mistral:7b-instruct-v0.3-q4_K_M
ollama pull nomic-embed-text

# 2. Testar chat rápido
curl http://localhost:11434/api/generate -d '{"model":"qwen2.5:7b","prompt":"Olá!","stream":false,"options":{"num_ctx":2048,"num_batch":512,"num_thread":10}}'

# 3. Testar RAG com embeddings
curl http://localhost:11434/api/embeddings -d '{"model":"nomic-embed-text","prompt":"Documento de teste"}'

# 4. Verificar status
curl http://localhost:11434/api/ps

# 5. Verificar modelos
ollama list

# 6. Configurar variáveis de ambiente (Windows PowerShell)
[System.Environment]::SetEnvironmentVariable("OLLAMA_NUM_THREAD", "10", "User")
[System.Environment]::SetEnvironmentVariable("OLLAMA_MAX_LOADED_MODELS", "2", "User")
[System.Environment]::SetEnvironmentVariable("OLLAMA_KEEP_ALIVE", "5m", "User")
```

---

## Checklist de Implementação

- [ ] Instalar Ollama v0.2+
- [ ] Baixar qwen2.5:7b-instruct (chat rápido)
- [ ] Baixar mistral:7b-instruct-v0.3 (RAG/qualidade)
- [ ] Baixar nomic-embed-text (embeddings)
- [ ] Configurar variáveis de ambiente (threads, keep_alive, max_models)
- [ ] Implementar pipeline de indexação RAG
- [ ] Implementar pipeline de consulta RAG
- [ ] Criar templates de prompt otimizados
- [ ] Executar benchmark e ajustar parâmetros
- [ ] Configurar monitoramento de recursos

---

*Documento gerado para otimização de IA local em hardware Intel i5-1235U sem GPU.*
