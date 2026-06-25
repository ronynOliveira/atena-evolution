# Pesquisa: Técnicas Avançadas de RAG (Retrieval-Augmented Generation) — 2025/2026

**Data:** 17 de junho de 2026  
**Automação:** Pesquisa compilada com base no estado da arte em RAG  
**Referências principais:** Microsoft GraphRAG, LangChain, LlamaIndex, RAGAS, Cohere, Pinecone, Academic Papers 2024-2026

---

## Índice

1. [Visão Geral do Estado da Arte](#visão-geral)
2. [1. RAG Multimodal (Texto + Imagem + Áudio)](#1-rag-multimodal)
3. [2. Graph RAG](#2-graph-rag)
4. [3. CRAG — Corrective RAG](#3-crag)
5. [4. Self-RAG](#4-self-rag)
6. [5. RAG com Rerankers Avançados](#5-rerankers-avançados)
7. [6. Chunking Semântico Adaptativo](#6-chunking-semântico-adaptativo)
8. [7. HyDE — Hypothetical Document Embeddings](#7-hyde)
9. [8. RAG Fusion com Múltiplas Queries](#8-rag-fusion)
10. [Comparação Geral das Técnicas](#comparação-geral)
11. [Stack Recomendado 2025-2026](#stack-recomendado)
12. [Referências](#referências)

---

## Visão Geral do Estado da Arte

O RAG evoluiu drasticamente desde sua concepção em 2020 (Lewis et al.). Em 2025-2026, o campo se diversificou em múltiplas frentes:

- **RAG clássico** (retrieve → generate) mostrou limitações em precisão, relevância e robustez contra alucinações.
- **Avanços-chave:** Graph RAG da Microsoft (abril/2024, com adoção massiva em 2025), CRAG (Corrective RAG), Self-RAG (auto-reflexivo), e rerankers cross-encoder de nova geração tendem a ser o "novo baseline" para sistemas sérios.
- **Tendência dominante:** pipelines híbridos que combinam múltiplas técnicas (busca densa + esparsa + grafo + reranking + avaliação) em um único fluxo.
- **Benchmarks atuais:** RAGAS, TruLens, e ARES são os frameworks de avaliação mais usados.
- **Modelos de embedding líderes:** `text-embedding-3-large` (OpenAI), `embed-v3` (Cohere), `BGE-M3` (BAAI — multilingue), `voyage-3` (Voyage AI), e `jina-embeddings-v3` (Jina AI).
- **Rerankers líderes:** Cohere Rerank 3.5, BGE-reranker-v2-m3, Jina Reranker v2.

---

## 1. RAG Multimodal

### Como Funciona

O RAG multimodal estende o retrieval tradicional (baseado apenas em texto) para incorporar **imagens, áudio, vídeo e tabelas** como fontes de contexto recuperado. O pipeline funciona assim:

1. **Indexação:** Documentos multimodais são processados por modelos de embedding multimodal (que mapeiam texto, imagem, áudio para um espaço vetorial compartilhado).
2. **Armazenamento:** Embeddings multimodais são armazenados em um banco de dados vetorial que suporta múltiplos tipos de mídia (Pinecone, Milvus, Qdrant, Weaviate).
3. **Recuperação:** A query do usuário (que pode ser texto, imagem ou áudio) é embedada no mesmo espaço compartido, e os chunks mais similares são recuperados.
4. **Geração:** O LLM multimodal (GPT-4V, GPT-4o, Gemini 1.5, LLaVA, Claude 3.5/4) recebe os chunks recuperados (texto + imagem + áudio transcrito) e gera a resposta.

**Arquiteturas principais em 2025-2026:**

- **ColBERT multimodal:** Usa late interaction para matching fino entre query e documento multimodal.
- **DSE (Dual-encoder Similarity Embedding):** Encoders separados para cada modalidade, projetados em espaço compartilhado.
- **CLIP-based RAG:** Usa CLIP/RN50 para embedding conjunto de texto+imagem, eficiente para retrieval de imagens contextualizadas.
- **Embedding-geral multimodal:** Modelos como `Cohere embed-v3`, `Jina CLIP-v2`, e `E5-mistral` já suportam múltiplas modalidades.

### Quando Usar

- Quando a base de conhecimento contém **documentos visuais** (manuais técnicos, diagramas, plantas, gráficos).
- Quando o usuário faz perguntas sobre **imagens** ("O que mostra este raio-X?").
- Quando há **áudio** a ser transcrito e consultado (reuniões, podcasts, atendimento).
- Sistemas de **customer support** com screenshots e diagramas.
- **Educação:** materiais didáticos com texto + figuras + vídeo.

### Implementação Prática em Python

```python
# ============================================================
# RAG Multimodal com CLIP + GPT-4o + Qdrant
# ============================================================
# Bibliotecas: pip install openai qdrant-client torch torchvision
#              pip install transformers Pillow librosa openai-whisper

import os
import torch
import openai
from PIL import Image
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from transformers import CLIPProcessor, CLIPModel
import whisper
import uuid

# --- Configuração ---
openai.api_key = os.getenv("OPENAI_API_KEY")
QDRANT_URL = "http://localhost:6333"

# --- Modelos ---
clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
whisper_model = whisper.load_model("base")

# --- Banco Vetorial ---
client = QdrantClient(url=QDRANT_URL)
COLLECTION = "multimodal_rag"

# Criar coleção (executar uma vez)
client.recreate_collection(
    collection_name=COLLECTION,
    vectors_config=VectorParams(size=512, distance=Distance.COSINE),
)

# ============================================================
# INDEXAÇÃO
# ============================================================

def index_text(text: str, metadata: dict):
    """Indexa texto usando embedding CLIP."""
    inputs = clip_processor(text=[text], return_tensors="pt", padding=True)
    with torch.no_grad():
        embedding = clip_model.get_text_features(**inputs).squeeze().tolist()
    client.upsert(
        collection_name=COLLECTION,
        points=[PointStruct(
            id=str(uuid.uuid4()),
            vector=embedding,
            payload={"type": "text", "content": text, **metadata}
        )]
    )

def index_image(image_path: str, caption: str, metadata: dict):
    """Indexa imagem com caption usando CLIP."""
    image = Image.open(image_path).convert("RGB")
    inputs = clip_processor(
        text=[caption], images=image, return_tensors="pt", padding=True
    )
    with torch.no_grad():
        embedding = clip_model.get_image_features(**inputs).squeeze().tolist()
    client.upsert(
        collection_name=COLLECTION,
        points=[PointStruct(
            id=str(uuid.uuid4()),
            vector=embedding,
            payload={
                "type": "image",
                "content": caption,
                "image_path": image_path,
                **metadata
            }
        )]
    )

def index_audio(audio_path: str, metadata: dict):
    """Transcreve áudio com Whisper e indexa o texto."""
    result = whisper_model.transcribe(audio_path)
    transcript = result["text"]
    index_text(transcript, {"type": "audio", "audio_path": audio_path, **metadata})

# ============================================================
# RECUPERAÇÃO E GERAÇÃO
# ============================================================

def retrieve_multimodal(query: str, top_k: int = 5) -> list:
    """Recupera chunks multimodais relevantes para a query."""
    inputs = clip_processor(text=[query], return_tensors="pt", padding=True)
    with torch.no_grad():
        query_embedding = clip_model.get_text_features(**inputs).squeeze().tolist()

    results = client.search(
        collection_name=COLLECTION,
        query_vector=query_embedding,
        limit=top_k,
    )
    return results

def generate_response(query: str, retrieved_chunks: list) -> str:
    """Gera resposta com GPT-4o usando contexto multimodal."""
    context_parts = []
    for chunk in retrieved_chunks:
        p = chunk.payload
        if p["type"] == "text":
            context_parts.append(f"[TEXTO] {p['content']}")
        elif p["type"] == "image":
            context_parts.append(f"[IMAGEM: {p.get('image_path', '')}] {p['content']}")
        elif p["type"] == "audio":
            context_parts.append(f"[ÁUDIO: {p.get('audio_path', '')}] {p['content']}")

    context = "\n---\n".join(context_parts)

    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Você é um assistente multimodal. Use o contexto fornecido (texto, imagem, áudio) para responder."},
            {"role": "user", "content": f"Contexto:\n{context}\n\nPergunta: {query}"}
        ],
        max_tokens=1024,
    )
    return response.choices[0].message.content

# ============================================================
# PIPELINE COMPLETO
# ============================================================

def multimodal_rag(query: str) -> str:
    chunks = retrieve_multimodal(query, top_k=5)
    return generate_response(query, chunks)

# --- Exemplo de uso ---
if __name__ == "__main__":
    # Indexar
    index_text("O fígado está localizado no quadrante superior direito do abdômen.", {"source": "anatomia_vet"})
    index_image("figuras/liver_diagram.png", "Diagrama anatômico do fígado", {"source": "atlas_2025"})
    index_audio("consulta_001.mp3", {"source": "consulta_veterinaria"})

    # Consultar
    resposta = multimodal_rag("Onde fica o fígado do animal?")
    print(resposta)
```

### Versão Avançada com Cohere Embed-v3 (multimodal nativo)

```python
# ============================================================
# RAG Multimodal com Cohere embed-v3 (suporte nativo a imagem)
# ============================================================
# pip install cohere

import cohere
import base64

co = cohere.ClientV2(os.getenv("COHERE_API_KEY"))

def cohere_embed_image(image_path: str):
    """Embedding multimodal nativo via Cohere."""
    with open(image_path, "rb") as f:
        image_b64 = base64.b64encode(f.read()).decode()
    
    response = co.embed(
        model="embed-english-v3.0",  # ou embed-multilingual-v3.0
        input_type="image",
        embedding_types=["float"],
        images=[f"data:image/png;base64,{image_b64}"],
    )
    return response.embeddings.float[0]
```

### Bibliotecas Necessárias

| Biblioteca | Uso |
|---|---|
| `transformers` (HuggingFace) | Modelos CLIP, processamento multimodal |
| `openai` | GPT-4o para geração multimodal |
| `qdrant-client` / `pinecone-client` | Banco vetorial |
| `whisper` (OpenAI) | Transcrição de áudio |
| `cohere` | Embeddings multimodais (embed-v3) |
| `llama-index` | Orquestração RAG multimodal |
| `langchain` | Pipelines RAG |
| `Pillow` | Processamento de imagem |
| `librosa` | Processamento de áudio |

---

## 2. Graph RAG

### Como Funciona

O **Graph RAG** (Microsoft, abril/2024, com evolução contínua em 2025) combina RAG tradicional com **grafos de conhecimento**. Em vez de buscar apenas chunks de texto similares, ele:

1. **Extração:** Usa LLMs para extrair entidades, relações e comunidades do corpus, construindo um grafo de conhecimento.
2. **Indexação em grafo:** O grafo é armazenado em um banco de dados de grafos (Neo4j, NetworkX, ou grafo em memória).
3. **Comunidades:** Detecta comunidades (clusters) no grafo usando algoritmos como Leiden ou Louvain.
4. **Sumarização:** Gera sumários hierárquicos de cada comunidade.
5. **Recuperação em dois níveis:**
   - **Local search:** Busca por entidades/relações específicas (perguntas de detalhe).
   - **Global search:** Usa sumários de comunidades para perguntas amplas ("Qual o tema principal deste corpus?").
6. **Geração:** Combina informações do grafo com o contexto textual para gerar respostas.

**Evolução 2025-2026:**
- **GraphRAG 2.0 (Microsoft):** Adicionou dynamic community selection, query-focused summarization, e integração com vector search híbrido.
- **LightRAG:** Implementação leve e rápida, com indexação incremental.
- **Nano-GraphRAG:** Versão minimalista para prototipagem rápida.
- **RAPTOR:** Recursive Abstractive Processing of Tree Organized Retrieval — hierarquia de sumários via árvore.

### Quando Usar

- **Perguntas que exigem raciocínio relacional:** "Qual a relação entre X e Y?"
- **Corpus grandes e interconectados:** documentos legais, científicos, médicos.
- **Perguntas globais/de alto nível:** "Quais são os principais temas discutidos?"
- **Detecção de comunidades e clusters temáticos.**
- **Domínios com entidades bem definidas:** farmacêutica, jurídica, biomédica.

### Implementação Prática em Python

```python
# ============================================================
# Graph RAG com Microsoft graphrag + LightRAG
# ============================================================
# pip install graphrag lightrag-hku neo4j langchain

# ============================================================
# OPÇÃO 1: Microsoft GraphRAG (oficial)
# ============================================================
# Instalação: pip install graphrag
# Configuração via CLI:

# graphrag init --root ./graphrag_project
# graphrag index --root ./graphrag_project
# graphrag query --root ./graphrag_project --method local "Qual a relação entre X e Y?"
# graphrag query --root ./graphrag_project --method global "Quais os temas principais?"

# ============================================================
# OPÇÃO 2: LightRAG (leve e rápido)
# ============================================================
# pip install lightrag-hku

from lightrag import LightRAG, QueryParam
from lightrag.llm import gpt_4o_mini_complete, openai_embedding
from lightrag.utils import EmbeddingFunc
import os

WORKING_DIR = "./lightrag_storage"

rag = LightRAG(
    working_dir=WORKING_DIR,
    llm_model_func=gpt_4o_mini_complete,
    embedding_func=EmbeddingFunc(
        embedding_dim=1536,
        max_token_size=8192,
        func=lambda texts: openai_embedding(
            texts, model="text-embedding-3-small"
        ),
    ),
)

# Indexar documentos
with open("documento.txt", "r") as f:
    rag.insert(f.read())

# Consulta
result = rag.query(
    "Qual a relação entre as entidades principais?",
    param=QueryParam(mode="global")  # "local", "global", "hybrid"
)
print(result)

# ============================================================
# OPÇÃO 3: Graph RAG manual com LangChain + Neo4j
# ============================================================
# pip install langchain langchain-experimental neo4j

from langchain_experimental.graph_transformers import LLMGraphTransformer
from langchain_community.graphs import Neo4jGraph
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import Neo4jVector
from langchain.chains import GraphCypherQAChain

# Construir grafo a partir de documentos
llm = ChatOpenAI(model="gpt-4o-mini")
transformer = LLMGraphTransformer(llm=llm)

# Extrair entidades e relações
from langchain_core.documents import Document
documents = [Document(page_content="Roberto trabalha na Koldi. Koldi é uma empresa de IA.")]
graph_documents = transformer.convert_to_graph_documents(documents)

# Armazenar no Neo4j
graph = Neo4jGraph(
    url="bolt://localhost:7687",
    username="neo4j",
    password="senha"
)
graph.add_graph_documents(graph_documents)

# Vector search no grafo
vector_index = Neo4jVector.from_existing_graph(
    OpenAIEmbeddings(),
    url="bolt://localhost:7687",
    username="neo4j",
    password="senha",
    index_name="entity_index",
    node_label="Entity",
    text_node_properties=["name"],
    embedding_node_property="embedding",
)

# QA Chain com Cypher
chain = GraphCypherQAChain.from_llm(
    llm=ChatOpenAI(model="gpt-4o"),
    graph=graph,
    verbose=True,
)
response = chain.invoke({"query": "Onde Roberto trabalha?"})
print(response)
```

### Bibliotecas Necessárias

| Biblioteca | Uso |
|---|---|
| `graphrag` (Microsoft) | Graph RAG oficial, completo |
| `lightrag-hku` | Graph RAG leve, rápido, incremental |
| `nano-graphrAG` | Versão minimalista |
| `langchain-experimental` | LLMGraphTransformer |
| `neo4j` | Banco de dados de grafos |
| `networkx` | Grafos em memória |
| `langchain-community` | Neo4jVector, GraphCypherQAChain |

---

## 3. CRAG — Corrective RAG

### Como Funciona

O **Corrective RAG (CRAG)** foi proposto por Shi et al. (2024) e se tornou um padrão em 2025. A ideia central é **avaliar a qualidade dos documentos recuperados** e, se necessário, **corrigir** a busca antes de gerar a resposta.

**Pipeline:**

1. **Retrieval:** Recupera documentos relevantes (como no RAG clássico).
2. **Avaliação (Retrieval Evaluator):** Um modelo leve (ou heurística) classifica cada documento como:
   - **Correct** → Usado diretamente para geração.
   - **Incorrect** → Descartado; busca web ou fonte alternativa é acionada.
   - **Ambiguous** → Combinado com busca web para complementar.
3. **Correção:**
   - Se documentos estão **incorrentes**: busca web (Tavily, Serper, Bing) é usada como fallback.
   - Se **ambíguos**: combina documentos recuperados com resultados web.
   - Se **corretos**: prossegue para geração.
4. **Decompose-then-Recompose:** Documentos corretos são decompostos em "stripes" (fichas de conhecimento), filtrados e recompostos.
5. **Geração:** O LLM gera a resposta com o contexto corrigido.

**Evolução 2025-2026:**
- **CRAG v2:** Usa modelos de avaliação mais leves (classificadores binários fine-tuned).
- **Adaptive CRAG:** O limiar de confiança é dinâmico, ajustado por tipo de query.
- **CRAG + Reranker:** Combina avaliação com reranking para maior precisão.

### Quando Usar

- Quando a **qualidade da base de dados é variável** (nem todos os documentos são confiáveis).
- Quando é crítico **evitar alucinações** por documentos irrelevantes.
- Sistemas de **QA de alta precisão** (jurídico, médico, financeiro).
- Quando há acesso a **busca web** como complemento.
- Quando o custo de uma resposta errada é alto.

### Implementação Prática em Python

```python
# ============================================================
# CRAG — Corrective RAG
# ============================================================
# pip install langchain langchain-openai langchain-community
# pip install tavily-python

import os
from enum import Enum
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings

# --- Configuração ---
llm = ChatOpenAI(model="gpt-4o", temperature=0)
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
web_search = TavilySearchResults(max_results=3)

# --- Classificação do Retrieval ---
class RetrievalConfidence(Enum):
    CORRECT = "correct"
    INCORRECT = "incorrect"
    AMBIGUOUS = "ambiguous"

EVALUATION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """Você é um avaliador de relevância. 
Dada uma pergunta e um documento recuperado, avalie se o documento é relevante.
Responda APENAS com uma das opções:
- CORRECT: O documento é relevante e contém informação correta para responder a pergunta.
- INCORRECT: O documento é irrelevante ou contém informação incorreta.
- AMBIGUOUS: O documento é parcialmente relevante mas insuficiente sozinho."""),
    ("user", "Pergunta: {query}\n\nDocumento recuperado: {document}\n\nAvaliação:")
])

eval_chain = EVALUATION_PROMPT | llm | StrOutputParser()

def evaluate_retrieval(query: str, document: str) -> RetrievalConfidence:
    """Avalia se o documento recuperado é relevante para a query."""
    result = eval_chain.invoke({"query": query, "document": document}).strip().upper()
    if "CORRECT" in result:
        return RetrievalConfidence.CORRECT
    elif "INCORRECT" in result:
        return RetrievalConfidence.INCORRECT
    else:
        return RetrievalConfidence.AMBIGUOUS

# --- Busca Web (Fallback) ---
def web_search_correction(query: str) -> str:
    """Busca web como fallback para documentos incorretos."""
    results = web_search.invoke(query)
    return "\n".join([r["content"] for r in results])

# --- Decompose then Recompose ---
DECOMPOSE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "Decomponha o documento em fichas de conhecimento individuais (stripes). Cada ficha deve conter um fato ou informação distinta. Uma ficha por linha."),
    ("user", "Documento: {document}")
])

RECOMPOSE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "Combine as fichas de conhecimento relevantes em um contexto coerente para responder a pergunta."),
    ("user", "Pergunta: {query}\n\nFichas:\n{stripes}")
])

decompose_chain = DECOMPOSE_PROMPT | llm | StrOutputParser()
recompose_chain = RECOMPOSE_PROMPT | llm | StrOutputParser()

def decompose_and_recompose(query: str, documents: list[str]) -> str:
    """Decompõe documentos em fichas e recompõe apenas as relevantes."""
    all_stripes = []
    for doc in documents:
        stripes = decompose_chain.invoke({"document": doc})
        for stripe in stripes.strip().split("\n"):
            stripe = stripe.strip()
            if stripe and len(stripe) > 10:
                all_stripes.append(stripe)
    
    # Filtrar fichas relevantes
    relevant_stripes = [
        s for s in all_stripes
        if evaluate_retrieval(query, s) != RetrievalConfidence.INCORRECT
    ]
    
    return recompose_chain.invoke({
        "query": query,
        "stripes": "\n".join(relevant_stripes)
    })

# --- Geração Final ---
GENERATION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "Você é um assistente preciso. Responda APENAS com base no contexto fornecido. Se não souber, diga que não sabe."),
    ("user", "Contexto:\n{context}\n\nPergunta: {query}")
])

gen_chain = GENERATION_PROMPT | llm | StrOutputParser()

# ============================================================
# PIPELINE CRAG COMPLETO
# ============================================================

def crag_pipeline(query: str, vectorstore: Chroma) -> str:
    """Pipeline completo de Corrective RAG."""
    
    # 1. Retrieval
    retrieved = vectorstore.similarity_search(query, k=5)
    documents = [doc.page_content for doc in retrieved]
    
    # 2. Avaliação de cada documento
    evaluations = [(doc, evaluate_retrieval(query, doc)) for doc in documents]
    
    correct_docs = [doc for doc, ev in evaluations if ev == RetrievalConfidence.CORRECT]
    incorrect_docs = [doc for doc, ev in evaluations if ev == RetrievalConfidence.INCORRECT]
    ambiguous_docs = [doc for doc, ev in evaluations if ev == RetrievalConfidence.AMBIGUOUS]
    
    print(f"[CRAG] Correct: {len(correct_docs)}, Incorrect: {len(incorrect_docs)}, Ambiguous: {len(ambiguous_docs)}")
    
    # 3. Correção
    if not correct_docs:
        # Todos incorretos → busca web
        print("[CRAG] Todos documentos irrelevantes. Buscando na web...")
        web_context = web_search_correction(query)
        context = web_context
    elif ambiguous_docs:
        # Alguns ambíguos → complementa com web
        print("[CRAG] Documentos ambíguos. Complementando com web...")
        web_context = web_search_correction(query)
        refined = decompose_and_recompose(query, correct_docs + ambiguous_docs)
        context = refined + "\n\n[Web]\n" + web_context
    else:
        # Todos corretos → decompose and recompose
        context = decompose_and_recompose(query, correct_docs)
    
    # 4. Geração
    return gen_chain.invoke({"context": context, "query": query})

# --- Exemplo de uso ---
if __name__ == "__main__":
    # Criar vectorstore de exemplo
    from langchain_core.documents import Document
    docs = [
        Document(page_content="A Koldi foi fundada em 2024 e foca em IA."),
        Document(page_content="O clima hoje está ensolarado."),
        Document(page_content="Graph RAG é uma técnica que combina grafos com RAG."),
    ]
    vs = Chroma.from_documents(docs, embeddings)
    
    resposta = crag_pipeline("O que é Graph RAG?", vs)
    print(f"\nResposta: {resposta}")
```

### Bibliotecas Necessárias

| Biblioteca | Uso |
|---|---|
| `langchain` / `langchain-openai` | Orquestração do pipeline |
| `tavily-python` | Busca web como fallback |
| `chromadb` | Vector store local |
| `openai` | LLM e embeddings |
| `ragas` | Avaliação da qualidade do CRAG |

---

## 4. Self-RAG

### Como Funciona

O **Self-RAG** (Asai et al., 2023, com adoção massiva em 2024-2025) torna o RAG **auto-reflexivo**: o modelo decide **se** precisa buscar, **quando** buscar, e **como** usar os documentos recuperados, tudo via tokens especiais de reflexão.

**Tokens de reflexão (Reflection Tokens):**

| Token | Significado |
|---|---|
| `[Retrieve]` | Decide se precisa buscar (Sim/Não) |
| `[IsRel]` | O documento recuperado é relevante? (Relevante/Irrelevante) |
| `[IsSup]` | A geração é suportada pelo documento? (Totalmente/Parcialmente/Não) |
| `[IsUse]` | A resposta final é útil? (5 níveis de utilidade) |

**Pipeline:**

1. O modelo recebe a pergunta e decide se precisa de retrieval (`[Retrieve]`).
2. Se sim, busca documentos.
3. Para cada documento, avalia relevância (`[IsRel]`).
4. Gera uma resposta candidata.
5. Avalia se a resposta é suportada pelo documento (`[IsSup]`).
6. Avalia a utilidade da resposta (`[IsUse]`).
7. Seleciona a melhor resposta (pode gerar múltiplas e escolher a de maior utilidade).

**Evolução 2025-2026:**
- **Self-RAG com modelos open-source:** Fine-tuning de Llama 3.1, Mistral, Qwen 2.5 com tokens de reflexão.
- **Adaptive Self-RAG:** O modelo aprende a ajustar a frequência de retrieval por tipo de query.
- **Self-RAG + CRAG:** Combinação das duas abordagens para máxima robustez.

### Quando Usar

- Quando você quer que o **próprio modelo decida** se precisa buscar ou não.
- Para **reduzir custo** (evitar buscas desnecessárias).
- Quando a qualidade dos documentos recuperados é **variável**.
- Sistemas que precisam de **transparência** (os tokens de reflexão mostram o raciocínio).
- Quando você quer **múltiplas candidatas** de resposta e selecionar a melhor.

### Implementação Prática em Python

```python
# ============================================================
# Self-RAG — Retrieval Auto-Reflexivo
# ============================================================
# pip install langchain langchain-openai chromadb

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document

# --- Configuração ---
llm = ChatOpenAI(model="gpt-4o", temperature=0)
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

# --- Prompts com Tokens de Reflexão ---

# 1. Decidir se precisa de retrieval
RETRIEVAL_DECISION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """Você é um sistema auto-reflexivo. 
Dada uma pergunta, decida se precisa buscar informações adicionais.
Responda com [Retrieve] SIM ou [Retrieve] NAO.

SIM se: a pergunta requer informação factual específica, dados atualizados, ou detalhes que você não tem certeza.
NAO se: a pergunta é geral, criativa, ou você pode responder com conhecimento geral."""),
    ("user", "Pergunta: {query}\n\nDecisão de retrieval:")
])

# 2. Avaliar relevância do documento
RELEVANCE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """Avalie se o documento é relevante para responder a pergunta.
Responda com [IsRel] RELEVANTE ou [IsRel] IRRELEVANTE."""),
    ("user", "Pergunta: {query}\n\nDocumento: {document}\n\nRelevância:")
])

# 3. Gerar resposta com contexto
GENERATION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """Gere uma resposta baseada no documento fornecido.
Após a resposta, avalie:
- [IsSup] TOTALMENTE, PARCIALMENTE, ou NAO (se a resposta é suportada pelo documento)
- [IsUse] 1 a 5 (utilidade da resposta, onde 5 é máxima)

Formato:
<resposta>
[IsSup] <avaliação>
[IsUse] <nota>"""),
    ("user", "Pergunta: {query}\n\nDocumento: {document}\n\nResposta:")
])

# 4. Gerar resposta sem contexto (conhecimento geral)
GENERAL_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """Responda a pergunta usando seu conhecimento geral.
Após a resposta, avalie:
- [IsSup] TOTALMENTE, PARCIALMENTE, ou NAO
- [IsUse] 1 a 5

Formato:
<resposta>
[IsSup] <avaliação>
[IsUse] <nota>"""),
    ("user", "Pergunta: {query}\n\nResposta:")
])

# --- Cadeias ---
retrieve_decision_chain = RETRIEVAL_DECISION_PROMPT | llm | StrOutputParser()
relevance_chain = RELEVANCE_PROMPT | llm | StrOutputParser()
gen_with_context_chain = GENERATION_PROMPT | llm | StrOutputParser()
gen_general_chain = GENERAL_PROMPT | llm | StrOutputParser()

# ============================================================
# PIPELINE SELF-RAG
# ============================================================

def self_rag_pipeline(query: str, vectorstore: Chroma) -> dict:
    """Pipeline completo de Self-RAG."""
    
    candidates = []
    
    # === Caminho 1: Resposta sem retrieval ===
    general_response = gen_general_chain.invoke({"query": query})
    candidates.append({
        "source": "general",
        "response": general_response,
    })
    
    # === Decisão de Retrieval ===
    decision = retrieve_decision_chain.invoke({"query": query})
    print(f"[Self-RAG] Decisão: {decision.strip()}")
    
    if "SIM" in decision.upper():
        # === Caminho 2: Com retrieval ===
        retrieved = vectorstore.similarity_search(query, k=3)
        
        for doc in retrieved:
            # Avaliar relevância
            relevance = relevance_chain.invoke({
                "query": query,
                "document": doc.page_content
            })
            print(f"[Self-RAG] Relevância: {relevance.strip()}")
            
            if "RELEVANTE" in relevance.upper():
                # Gerar com contexto
                response = gen_with_context_chain.invoke({
                    "query": query,
                    "document": doc.page_content
                })
                candidates.append({
                    "source": "retrieval",
                    "document": doc.page_content[:100],
                    "response": response,
                })
    
    # === Selecionar melhor resposta ===
    # (Em produção, parseia [IsUse] e seleciona a de maior nota)
    print(f"\n[Candidatos gerados: {len(candidates)}]")
    
    best = candidates[-1]  # Simplificado: último candidato (com retrieval)
    return best

# --- Exemplo de uso ---
if __name__ == "__main__":
    docs = [
        Document(page_content="Self-RAG foi proposto por Asai et al. em 2023."),
        Document(page_content="Graph RAG usa grafos de conhecimento para retrieval."),
    ]
    vs = Chroma.from_documents(docs, embeddings)
    
    resultado = self_rag_pipeline("O que é Self-RAG?", vs)
    print(f"\nMelhor resposta: {resultado['response']}")
```

### Bibliotecas Necessárias

| Biblioteca | Uso |
|---|---|
| `langchain` / `langchain-openai` | Orquestração |
| `transformers` (HuggingFace) | Fine-tuning com tokens de reflexão |
| `chromadb` / `qdrant-client` | Vector store |
| `openai` | LLM |
| `ragas` | Avaliação de qualidade |

---

## 5. RAG com Rerankers Avançados

### Como Funciona

O **reranking** é uma etapa de **reordenação** dos documentos recuperados, aplicada **após** o retrieval inicial. Enquanto o retriever (bi-encoder) é rápido mas menos preciso, o reranker (cross-encoder) é mais lento mas muito mais preciso.

**Arquitetura em duas etapas:**

1. **Retrieval (Bi-encoder):** Busca rápida no vector store, retorna top-20~50 candidatos.
2. **Reranking (Cross-encoder):** Reavalia cada par (query, documento) com um modelo mais poderoso, reordena e seleciona top-3~5.

**Rerankers de ponta em 2025-2026:**

| Reranker | Tipo | Características |
|---|---|---|
| **Cohere Rerank 3.5** | API | Multilingue, 1024 tokens, excelente para produção |
| **BGE-reranker-v2-m3** | Open-source | Multilingue, 8192 tokens, rodável localmente |
| **Jina Reranker v2** | API/Open | Multimodal, 8192 tokens |
| **FlashRank** | Open-source | Ultra-leve, baseado em cross-encoder T5 |
| **RankLLaMA** | Open-source | LLaMA-based, zero-shot |
| **ColBERT v2** | Open-source | Late interaction, muito preciso |

**Técnicas avançadas de reranking:**

- **Multi-stage reranking:** Bi-encoder → Cross-encoder → LLM-based reranker.
- **Diversity-aware reranking:** Maximiza diversidade entre os documentos selecionados (MMR — Maximal Marginal Relevance).
- **Query-specific reranking:** Ajusta o reranker por tipo de query.

### Quando Usar

- **Sempre que a precisão do retrieval for crítica.**
- Quando o retriever inicial recupera muitos documentos irrelevantes (ruído).
- Quando você precisa de **poucos documentos de alta qualidade** (top-3) em vez de muitos.
- Sistemas de **QA de produção** onde cada token de contexto conta.
- Quando o contexto do LLM é limitado (janela de contexto pequena).

### Implementação Prática em Python

```python
# ============================================================
# RAG com Rerankers Avançados
# ============================================================
# pip install cohere FlagEmbedding sentence-transformers ragas

import cohere
from FlagEmbedding import FlagReranker
from sentence_transformers import CrossEncoder
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# ============================================================
# OPÇÃO 1: Cohere Rerank 3.5 (API)
# ============================================================

co = cohere.ClientV2(os.getenv("COHERE_API_KEY"))

def cohere_rerank(query: str, documents: list[str], top_n: int = 3) -> list[dict]:
    """Reranking com Cohere Rerank 3.5."""
    response = co.rerank(
        model="rerank-v3.5",
        query=query,
        documents=documents,
        top_n=top_n,
    )
    results = []
    for r in response.results:
        results.append({
            "index": r.index,
            "text": documents[r.index],
            "relevance_score": r.relevance_score,
        })
    return results

# ============================================================
# OPÇÃO 2: BGE-reranker-v2-m3 (Open-source, local)
# ============================================================

bge_reranker = FlagReranker(
    "BAAI/bge-reranker-v2-m3",
    use_fp16=True,  # Mais rápido em GPU
)

def bge_rerank(query: str, documents: list[str], top_n: int = 3) -> list[dict]:
    """Reranking com BGE (local)."""
    pairs = [(query, doc) for doc in documents]
    scores = bge_reranker.compute_score(pairs, normalize=True)
    
    # Ordenar por score
    scored = sorted(
        [{"text": doc, "score": score} for doc, score in zip(documents, scores)],
        key=lambda x: x["score"],
        reverse=True,
    )
    return scored[:top_n]

# ============================================================
# OPÇÃO 3: FlashRank (ultra-leve)
# ============================================================
# pip install flashrank

from flashrank import Ranker, RerankRequest

flash_ranker = Ranker(model_name="ms-marco-MiniLM-L-12-v2", cache_dir="/tmp/flashrank")

def flash_rerank(query: str, documents: list[str], top_n: int = 3) -> list[dict]:
    """Reranking ultra-leve com FlashRank."""
    passages = [{"id": i, "text": doc} for i, doc in enumerate(documents)]
    request = RerankRequest(query=query, passages=passages)
    results = flash_ranker.rerank(request)
    return results[:top_n]

# ============================================================
# OPÇÃO 4: MMR (Maximal Marginal Relevance) para diversidade
# ============================================================

from langchain_community.vectorstores import Chroma

def mmr_retrieval(query: str, vectorstore: Chroma, k: int = 5, lambda_mult: float = 0.7) -> list[Document]:
    """Retrieval com diversidade via MMR."""
    results = vectorstore.max_marginal_relevance_search(
        query, k=k, lambda_mult=lambda_mult
    )
    return results

# ============================================================
# PIPELINE COMPLETO: Retrieval + Rerank + Generate
# ============================================================

def rag_with_rerank(
    query: str,
    vectorstore: Chroma,
    reranker: str = "cohere",  # "cohere", "bge", "flash"
    initial_k: int = 20,
    final_k: int = 3,
) -> str:
    """Pipeline RAG com reranking."""
    
    # 1. Retrieval inicial (busca ampla)
    retrieved = vectorstore.similarity_search(query, k=initial_k)
    documents = [doc.page_content for doc in retrieved]
    
    # 2. Reranking
    if reranker == "cohere":
        reranked = cohere_rerank(query, documents, top_n=final_k)
    elif reranker == "bge":
        reranked = bge_rerank(query, documents, top_n=final_k)
    elif reranker == "flash":
        reranked = flash_rerank(query, documents, top_n=final_k)
    else:
        reranked = [{"text": doc} for doc in documents[:final_k]]
    
    # 3. Construir contexto
    context = "\n---\n".join([r["text"] for r in reranked])
    
    # 4. Geração
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Responda com base no contexto. Se não souber, diga que não sabe."),
        ("user", "Contexto:\n{context}\n\nPergunta: {query}")
    ])
    chain = prompt | llm | StrOutputParser()
    return chain.invoke({"context": context, "query": query})

# --- Exemplo de uso ---
if __name__ == "__main__":
    docs = [
        Document(page_content="RAG combina retrieval com geração de linguagem."),
        Document(page_content="Rerankers melhoram a precisão do retrieval."),
        Document(page_content="Hoje é um dia ensolarado."),
        Document(page_content="Cross-encoders são mais precisos que bi-encoders."),
        Document(page_content="O Brasil é o maior país da América do Sul."),
    ]
    vs = Chroma.from_documents(docs, OpenAIEmbeddings())
    
    resposta = rag_with_rerank("Como melhorar a precisão do RAG?", vs, reranker="bge")
    print(resposta)
```

### Bibliotecas Necessárias

| Biblioteca | Uso |
|---|---|
| `cohere` | Cohere Rerank 3.5 (API) |
| `FlagEmbedding` | BGE-reranker-v2-m3 (local) |
| `flashrank` | FlashRank (ultra-leve) |
| `sentence-transformers` | Cross-encoders genéricos |
| `ragas` | Avaliação de rerankers |
| `langchain` | MMR retrieval |

---

## 6. Chunking Semântico Adaptativo

### Como Funciona

O **chunking** (divisão de documentos em pedaços) é uma das etapas mais críticas do RAG. Chunking ruim = retrieval ruim. O **chunking semântico adaptativo** vai além de divisões fixas por tamanho:

**Técnicas de chunking:**

| Técnica | Descrição | Quando usar |
|---|---|---|
| **Fixed-size** | Chunks de N tokens com overlap | Baseline simples |
| **Sentence-based** | Divide por sentenças | Documentos bem estruturados |
| **Semantic chunking** | Divide por similaridade semântica entre sentenças | Documentos com tópicos variados |
| **Topic-based** | Divide por detecção de tópicos (LDA, BERTopic) | Corpus temático |
| **Structure-based** | Divide por estrutura do documento (headers, seções) | PDFs, HTML, Markdown |
| **Agentic chunking** | LLM decide os melhores pontos de divisão | Máxima qualidade, mais lento |
| **Late chunking** | Embedding do documento inteiro, depois divide | Preserva contexto global |
| **Hierarchical chunking** | Chunks em múltiplas granularidades (parágrafo → seção → documento) | Documentos longos |

**Chunking semântico adaptativo (estado da arte 2025-2026):**

1. **Calcula embeddings de sentenças consecutivas.**
2. **Mede a similaridade cossenal entre sentenças adjacentes.**
3. **Detecta "quebras semânticas"** (queda abrupta na similaridade).
4. **Divide nos pontos de quebra**, criando chunks que respeitam unidades de significado.
5. **Adapta o tamanho** do chunk ao conteúdo (chunks menores em seções densas, maiores em seções narrativas).

### Quando Usar

- **Sempre que fizer RAG** — chunking é a base de tudo.
- Quando documentos têm **tópicos variados** em seções longas.
- Quando chunks fixos cortam **sentenças ou parágrafos ao meio**.
- Quando você precisa de **múltiplas granularidades** (busca fina + busca ampla).
- Documentos **técnicos ou científicos** com estrutura complexa.

### Implementação Prática em Python

```python
# ============================================================
# Chunking Semântico Adaptativo
# ============================================================
# pip install langchain langchain-experimental sentence-transformers
# pip install spacy scikit-learn numpy

import numpy as np
from sentence_transformers import SentenceTransformer
from langchain_experimental.text_splitter import SemanticChunker
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import (
    RecursiveCharacterTextSplitter,
    MarkdownHeaderTextSplitter,
)
from langchain_core.documents import Document

# ============================================================
# OPÇÃO 1: LangChain SemanticChunker (mais simples)
# ============================================================

def semantic_chunking_langchain(texts: list[str]) -> list[Document]:
    """Chunking semântico com LangChain."""
    semantic_chunker = SemanticChunker(
        embeddings=OpenAIEmbeddings(model="text-embedding-3-small"),
        breakpoint_threshold_type="percentile",  # "percentile", "standard_deviation", "interquartile", "gradient"
        breakpoint_threshold_amount=95,  # Percentil para quebra
    )
    all_chunks = []
    for text in texts:
        chunks = semantic_chunker.create_documents([text])
        all_chunks.extend(chunks)
    return all_chunks

# ============================================================
# OPÇÃO 2: Chunking semântico manual (mais controle)
# ============================================================

class AdaptiveSemanticChunker:
    """Chunking semântico adaptativo com controle fino."""
    
    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        max_chunk_size: int = 512,
        min_chunk_size: int = 100,
        similarity_threshold: float = 0.5,
    ):
        self.model = SentenceTransformer(model_name)
        self.max_chunk_size = max_chunk_size
        self.min_chunk_size = min_chunk_size
        self.similarity_threshold = similarity_threshold
    
    def split_sentences(self, text: str) -> list[str]:
        """Divide texto em sentenças."""
        import re
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def compute_similarities(self, sentences: list[str]) -> list[float]:
        """Calcula similaridade entre sentenças consecutivas."""
        embeddings = self.model.encode(sentences)
        similarities = []
        for i in range(len(embeddings) - 1):
            sim = np.dot(embeddings[i], embeddings[i+1]) / (
                np.linalg.norm(embeddings[i]) * np.linalg.norm(embeddings[i+1])
            )
            similarities.append(float(sim))
        return similarities
    
    def chunk(self, text: str) -> list[str]:
        """Divide texto em chunks semânticos adaptativos."""
        sentences = self.split_sentences(text)
        
        if len(sentences) <= 1:
            return [text]
        
        similarities = self.compute_similarities(sentences)
        
        chunks = []
        current_chunk = [sentences[0]]
        current_size = len(sentences[0])
        
        for i, sim in enumerate(similarities):
            next_sentence = sentences[i + 1]
            next_size = len(next_sentence)
            
            # Decisão de quebra
            should_break = (
                sim < self.similarity_threshold  # Quebra semântica
                or current_size + next_size > self.max_chunk_size  # Tamanho máximo
            )
            
            if should_break and current_size >= self.min_chunk_size:
                chunks.append(" ".join(current_chunk))
                current_chunk = [next_sentence]
                current_size = next_size
            else:
                current_chunk.append(next_sentence)
                current_size += next_size
        
        # Último chunk
        if current_chunk:
            chunks.append(" ".join(current_chunk))
        
        return chunks

# ============================================================
# OPÇÃO 3: Chunking Hierárquico (múltiplas granularidades)
# ============================================================

from langchain.text_splitter import MarkdownTextSplitter

def hierarchical_chunking(text: str) -> dict:
    """Cria chunks em múltiplas granularidades."""
    
    # Nível 1: Seções (por headers markdown)
    headers_to_split_on = [("#", "Header 1"), ("##", "Header 2"), ("###", "Header 3")]
    markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
    sections = markdown_splitter.split_text(text)
    
    # Nível 2: Parágrafos dentro de cada seção
    paragraph_splitter = RecursiveCharacterTextSplitter(
        chunk_size=512, chunk_overlap=50,
        separators=["\n\n", "\n", ". ", " "]
    )
    
    # Nível 3: Sentenças (para busca fina)
    sentence_splitter = RecursiveCharacterTextSplitter(
        chunk_size=128, chunk_overlap=20,
        separators=[". ", "! ", "? ", " "]
    )
    
    result = {"sections": [], "paragraphs": [], "sentences": []}
    
    for section in sections:
        result["sections"].append(section.page_content)
        paragraphs = paragraph_splitter.split_text(section.page_content)
        result["paragraphs"].extend(paragraphs)
        for p in paragraphs:
            sentences = sentence_splitter.split_text(p)
            result["sentences"].extend(sentences)
    
    return result

# ============================================================
# OPÇÃO 4: Agentic Chunking (LLM decide as quebras)
# ============================================================

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

AGENTIC_CHUNK_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """Você é um especialista em divisão de texto.
Dado um texto, identifique os pontos ideais de divisão onde o tópico muda.
Retorne o texto dividido em seções, cada uma com um tópico coerente.
Formado: Seção 1: [conteúdo]\\n\\nSeção 2: [conteúdo]..."""),
    ("user", "Texto:\n{text}")
])

def agentic_chunking(text: str) -> list[str]:
    """Chunking onde o LLM decide os pontos de divisão."""
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    chain = AGENTIC_CHUNK_PROMPT | llm | StrOutputParser()
    result = chain.invoke({"text": text})
    
    chunks = []
    for section in result.split("Seção "):
        section = section.strip()
        if ":" in section:
            content = section.split(":", 1)[1].strip()
            if content:
                chunks.append(content)
    return chunks

# --- Exemplo de uso ---
if __name__ == "__main__":
    texto = """
    Inteligência Artificial é um campo da ciência da computação. 
    Ela se concentra em criar sistemas que podem realizar tarefas que normalmente requerem inteligência humana.
    Machine learning é um subcampo da IA. Redes neurais são uma técnica de machine learning.
    
    A medicina veterinária é a área da saúde animal. 
    Animais de companhia incluem cães e gatos. 
    O diagnóstico veterinário envolve exames clínicos e laboratoriais.
    """
    
    # Chunking semântico adaptativo
    chunker = AdaptiveSemanticChunker(
        model_name="all-MiniLM-L6-v2",
        max_chunk_size=300,
        similarity_threshold=0.4,
    )
    chunks = chunker.chunk(texto)
    
    for i, chunk in enumerate(chunks):
        print(f"--- Chunk {i+1} ---")
        print(chunk[:200])
        print()
```

### Bibliotecas Necessárias

| Biblioteca | Uso |
|---|---|
| `langchain-experimental` | SemanticChunker |
| `sentence-transformers` | Embeddings para chunking semântico |
| `langchain` | RecursiveCharacterTextSplitter, MarkdownHeaderTextSplitter |
| `spacy` | Segmentação de sentenças |
| `scikit-learn` | Similaridade, clustering |
| `bertopic` | Detecção de tópicos para chunking |

---

## 7. HyDE — Hypothetical Document Embeddings

### Como Funciona

O **HyDE** (Hypothetical Document Embeddings, Gao et al., 2022, amplamente adotado em 2024-2025) resolve um problema fundamental: a **incompatibilidade semântica** entre queries (curtas, em linguagem do usuário) e documentos (longos, em linguagem técnica).

**Ideia central:** Em vez de usar a query diretamente para buscar, **gera-se um documento hipotético** que responderia à query, e usa-se o embedding desse documento hipotético para buscar.

**Pipeline:**

1. O usuário faz uma pergunta.
2. Um LLM gera um **documento hipotético** (resposta fictícia) para essa pergunta.
3. O embedding desse documento hipotético é calculado.
4. Esse embedding é usado para buscar no vector store.
5. Os documentos reais recuperados são usados para gerar a resposta final.

**Por que funciona?** O documento hipotético está no mesmo "espaço linguístico" dos documentos reais (ambos são textos longos, com vocabulário técnico), tornando a busca por similaridade mais eficaz.

**Evolção 2025-2026:**
- **Multi-HyDE:** Gera múltiplos documentos hipotéticos e combina os resultados.
- **HyDE + Step-back:** Combina HyDE com "step-back prompting" (generaliza a query antes de gerar o documento hipotético).
- **HyDE adaptativo:** Usa modelos menores para gerar documentos hipotéticos (reduz latência).

### Quando Usar

- Quando há **gap semântico** entre a linguagem do usuário e a linguagem dos documentos.
- Quando queries são **curtas e ambíguas**.
- Quando o retrieval direto (query → documento) tem **baixa precisão**.
- Domínios **técnicos ou especializados** (médico, jurídico, científico).
- Quando você quer melhorar o retrieval **sem mudar o vector store**.

### Implementação Prática em Python

```python
# ============================================================
# HyDE — Hypothetical Document Embeddings
# ============================================================
# pip install langchain langchain-openai chromadb

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.documents import Document

# --- Configuração ---
llm = ChatOpenAI(model="gpt-4o", temperature=0.7)  # Temperature > 0 para diversidade
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

# --- Prompt para gerar documento hipotético ---
HYDE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """Você é um especialista no domínio do conhecimento do usuário.
Dada uma pergunta, gere um documento hipotético (150-300 palavras) que responderia perfeitamente a essa pergunta.
O documento deve:
- Usar linguagem técnica apropriada ao domínio
- Conter fatos relevantes (mesmo que hipotéticos)
- Ter a estrutura de um documento real do corpus

Responda APENAS com o documento hipotético, sem explicações."""),
    ("user", "Pergunta: {query}\n\nDocumento hipotético:")
])

hyde_chain = HYDE_PROMPT | llm | StrOutputParser()

# --- Geração de múltiplos documentos hipotéticos (Multi-HyDE) ---
def generate_hypothetical_documents(query: str, n: int = 3) -> list[str]:
    """Gera N documentos hipotéticos para uma query."""
    docs = []
    for _ in range(n):
        doc = hyde_chain.invoke({"query": query})
        docs.append(doc.strip())
    return docs

# ============================================================
# PIPELINE HyDE
# ============================================================

def hyde_rag(query: str, vectorstore: Chroma, top_k: int = 5) -> str:
    """Pipeline RAG com HyDE."""
    
    # 1. Gerar documento hipotético
    print(f"[HyDE] Gerando documento hipotético para: {query}")
    hyp_doc = hyde_chain.invoke({"query": query})
    print(f"[HyDE] Documento gerado: {hyp_doc[:100]}...")
    
    # 2. Embedding do documento hipotético
    hyp_embedding = embeddings.embed_query(hyp_doc)
    
    # 3. Busca no vector store usando o embedding hipotético
    results = vectorstore.similarity_search_by_vector(hyp_embedding, k=top_k)
    
    # 4. Geração com documentos recuperados
    context = "\n---\n".join([doc.page_content for doc in results])
    
    gen_prompt = ChatPromptTemplate.from_messages([
        ("system", "Responda com base no contexto fornecido."),
        ("user", "Contexto:\n{context}\n\nPergunta: {query}")
    ])
    gen_chain = gen_prompt | llm | StrOutputParser()
    
    return gen_chain.invoke({"context": context, "query": query})

# ============================================================
# PIPELINE Multi-HyDE (avançado)
# ============================================================

def multi_hyde_rag(query: str, vectorstore: Chroma, n_hyp: int = 3, top_k: int = 5) -> str:
    """RAG com múltiplos documentos hipotéticos."""
    
    # 1. Gerar múltiplos documentos hipotéticos
    hyp_docs = generate_hypothetical_documents(query, n=n_hyp)
    
    # 2. Buscar para cada documento hipotético e combinar
    all_results = []
    for hyp_doc in hyp_docs:
        hyp_embedding = embeddings.embed_query(hyp_doc)
        results = vectorstore.similarity_search_by_vector(hyp_embedding, k=top_k)
        all_results.extend(results)
    
    # 3. Deduplicar (por conteúdo)
    seen = set()
    unique_results = []
    for doc in all_results:
        if doc.page_content not in seen:
            seen.add(doc.page_content)
            unique_results.append(doc)
    
    # 4. Selecionar top-k únicos
    final_docs = unique_results[:top_k]
    
    # 5. Geração
    context = "\n---\n".join([doc.page_content for doc in final_docs])
    gen_prompt = ChatPromptTemplate.from_messages([
        ("system", "Responda com base no contexto fornecido."),
        ("user", "Contexto:\n{context}\n\nPergunta: {query}")
    ])
    gen_chain = gen_prompt | llm | StrOutputParser()
    
    return gen_chain.invoke({"context": context, "query": query})

# --- Exemplo de uso ---
if __name__ == "__main__":
    docs = [
        Document(page_content="Graph RAG é uma técnica que combina grafos de conhecimento com retrieval augmented generation. Foi proposta pela Microsoft em 2024."),
        Document(page_content="RAG multimodal permite recuperar texto, imagens e áudio para geração de respostas."),
        Document(page_content="O clima tropical é caracterizado por altas temperaturas e chuvas frequentes."),
    ]
    vs = Chroma.from_documents(docs, embeddings)
    
    # HyDE simples
    resposta = hyde_rag("Como funciona Graph RAG?", vs)
    print(f"\nResposta: {resposta}")
    
    # Multi-HyDE
    resposta_multi = multi_hyde_rag("Como funciona Graph RAG?", vs, n_hyp=3)
    print(f"\nResposta Multi-HyDE: {resposta_multi}")
```

### Bibliotecas Necessárias

| Biblioteca | Uso |
|---|---|
| `langchain` / `langchain-openai` | Pipeline HyDE |
| `openai` | LLM para gerar documentos hipotéticos |
| `chromadb` / `qdrant-client` | Vector store |
| `sentence-transformers` | Embeddings locais |

---

## 8. RAG Fusion com Múltiplas Queries

### Como Funciona

O **RAG Fusion** (Aakko, 2023, com evolução contínua em 2024-2025) parte de uma observação simples: **uma única query raramente captura toda a intenção do usuário**. A solução é gerar **múltiplas queries** a partir da pergunta original e combinar os resultados.

**Pipeline:**

1. **Query Expansion:** Um LLM gera N variações da query original (sinônimos, reformulações, sub-perguntas).
2. **Multi-Retrieval:** Cada query é usada para buscar documentos no vector store.
3. **Fusion:** Os resultados de todas as buscas são combinados usando **Reciprocal Rank Fusion (RRF)** ou **weighted scoring**.
4. **Geração:** O LLM gera a resposta com o contexto fusionado.

**Técnicas de fusão:**

| Técnica | Descrição |
|---|---|
| **Reciprocal Rank Fusion (RRF)** | Combina rankings dando peso inversamente proporcional à posição |
| **Weighted linear fusion** | Combina scores com pesos aprendidos |
| **Learned fusion** | Modelo treinado para combinar resultados |
| **Query decomposition** | Decompõe perguntas complexas em sub-perguntas |

**Evolução 2025-2026:**
- **RAG-Fusion + HyDE:** Combina múltiplas queries com documentos hipotéticos.
- **Adaptive query expansion:** O número de queries geradas depende da complexidade da pergunta.
- **Step-back prompting:** Gera uma pergunta mais geral antes de expandir.

### Quando Usar

- Quando a **query do usuário é complexa** ou ambígua.
- Quando você quer **maximizar a cobertura** do retrieval.
- Quando uma única busca não retorna documentos suficientes.
- Perguntas que têm **múltiplas facetas** ou sub-tópicos.
- Quando combinado com reranking para máxima precisão.

### Implementação Prática em Python

```python
# ============================================================
# RAG Fusion com Múltiplas Queries
# ============================================================
# pip install langchain langchain-openai chromadb rank-bm25

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.documents import Document
from collections import defaultdict
import numpy as np

# --- Configuração ---
llm = ChatOpenAI(model="gpt-4o", temperature=0.7)
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

# ============================================================
# 1. Query Expansion
# ============================================================

QUERY_EXPANSION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """Você é um especialista em busca de informação.
Dada uma pergunta do usuário, gere 4 variações de query que capturem diferentes aspectos da pergunta.
Inclua:
- Uma reformulação com sinônimos
- Uma versão mais específica
- Uma versão mais geral (step-back)
- Uma sub-pergunta relevante

Retorne UMA query por linha, sem numeração."""),
    ("user", "Pergunta original: {query}\n\nVariações de query:")
])

expansion_chain = QUERY_EXPANSION_PROMPT | llm | StrOutputParser()

def expand_query(query: str) -> list[str]:
    """Expande a query original em múltiplas variações."""
    result = expansion_chain.invoke({"query": query})
    variations = [q.strip() for q in result.strip().split("\n") if q.strip()]
    return [query] + variations  # Inclui a original

# ============================================================
# 2. Reciprocal Rank Fusion (RRF)
# ============================================================

def reciprocal_rank_fusion(
    ranked_lists: list[list[Document]],
    k: int = 60,
    top_n: int = 5,
) -> list[Document]:
    """Combina múltiplas listas ranqueadas usando RRF.
    
    RRF score = Σ(1 / (k + rank_i)) para cada lista onde o documento aparece.
    k é uma constante de suavização (padrão: 60).
    """
    scores = defaultdict(float)
    doc_map = {}
    
    for ranked_list in ranked_lists:
        for rank, doc in enumerate(ranked_list):
            # Usar conteúdo como chave de deduplicação
            doc_key = doc.page_content[:200]
            scores[doc_key] += 1.0 / (k + rank + 1)
            if doc_key not in doc_map:
                doc_map[doc_key] = doc
    
    # Ordenar por score RRF
    sorted_docs = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    
    return [doc_map[doc_key] for doc_key, _ in sorted_docs[:top_n]]

# ============================================================
# 3. Weighted Fusion (alternativa ao RRF)
# ============================================================

def weighted_fusion(
    query_results: dict[str, list[tuple[Document, float]]],
    weights: dict[str, float] = None,
    top_n: int = 5,
) -> list[Document]:
    """Combina resultados com pesos por query."""
    if weights is None:
        # Primeira query (original) tem peso maior
        queries = list(query_results.keys())
        weights = {q: 1.0 / (i + 1) for i, q in enumerate(queries)}
    
    combined_scores = defaultdict(float)
    doc_map = {}
    
    for query, results in query_results.items():
        w = weights.get(query, 1.0)
        for doc, score in results:
            doc_key = doc.page_content[:200]
            combined_scores[doc_key] += w * score
            if doc_key not in doc_map:
                doc_map[doc_key] = doc
    
    sorted_docs = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)
    return [doc_map[doc_key] for doc_key, _ in sorted_docs[:top_n]]

# ============================================================
# 4. Query Decomposition (para perguntas complexas)
# ============================================================

DECOMPOSITION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """Decomponha a pergunta complexa em sub-perguntas independentes.
Cada sub-pergunta deve poder ser respondida separadamente.
Retorne UMA sub-pergunta por linha."""),
    ("user", "Pergunta: {query}\n\nSub-perguntas:")
])

decomp_chain = DECOMPOSITION_PROMPT | llm | StrOutputParser()

def decompose_and_fuse(query: str, vectorstore: Chroma) -> str:
    """Decompõe pergunta complexa, busca para cada sub-pergunta, e funde."""
    
    # Decompor
    sub_questions = decomp_chain.invoke({"query": query})
    sub_qs = [q.strip() for q in sub_questions.strip().split("\n") if q.strip()]
    print(f"[Decomposição] Sub-perguntas: {sub_qs}")
    
    # Buscar para cada sub-pergunta
    all_ranked = []
    for sq in sub_qs:
        results = vectorstore.similarity_search(sq, k=5)
        all_ranked.append(results)
    
    # Fusion
    fused = reciprocal_rank_fusion(all_ranked, top_n=5)
    
    # Geração
    context = "\n---\n".join([doc.page_content for doc in fused])
    gen_prompt = ChatPromptTemplate.from_messages([
        ("system", "Responda a pergunta original usando o contexto das sub-perguntas."),
        ("user", "Pergunta original: {query}\n\nContexto:\n{context}")
    ])
    gen_chain = gen_prompt | llm | StrOutputParser()
    return gen_chain.invoke({"query": query, "context": context})

# ============================================================
# PIPELINE RAG FUSION COMPLETO
# ============================================================

def rag_fusion(
    query: str,
    vectorstore: Chroma,
    n_queries: int = 4,
    top_k: int = 5,
) -> str:
    """Pipeline completo de RAG Fusion."""
    
    # 1. Expandir query
    queries = expand_query(query)[:n_queries]
    print(f"[RAG Fusion] Queries expandidas: {queries}")
    
    # 2. Buscar para cada query
    all_ranked = []
    for q in queries:
        results = vectorstore.similarity_search(q, k=top_k)
        all_ranked.append(results)
    
    # 3. Fusion (RRF)
    fused_docs = reciprocal_rank_fusion(all_ranked, top_n=top_k)
    
    # 4. Geração
    context = "\n---\n".join([doc.page_content for doc in fused_docs])
    gen_prompt = ChatPromptTemplate.from_messages([
        ("system", "Responda com base no contexto fornecido. Seja preciso e completo."),
        ("user", "Pergunta: {query}\n\nContexto:\n{context}")
    ])
    gen_chain = gen_prompt | llm | StrOutputParser()
    
    return gen_chain.invoke({"query": query, "context": context})

# ============================================================
# RAG FUSION + RERANKER (pipeline avançado)
# ============================================================

def rag_fusion_with_rerank(
    query: str,
    vectorstore: Chroma,
    reranker,  # BGE reranker
    n_queries: int = 4,
    initial_k: int = 10,
    final_k: int = 3,
) -> str:
    """RAG Fusion + Reranking para máxima precisão."""
    
    # 1. Expandir e buscar
    queries = expand_query(query)[:n_queries]
    all_docs = []
    for q in queries:
        results = vectorstore.similarity_search(q, k=initial_k)
        all_docs.extend(results)
    
    # 2. Deduplicar
    seen = set()
    unique_docs = []
    for doc in all_docs:
        if doc.page_content not in seen:
            seen.add(doc.page_content)
            unique_docs.append(doc)
    
    # 3. Reranking
    pairs = [(query, doc.page_content) for doc in unique_docs]
    scores = reranker.compute_score(pairs, normalize=True)
    
    scored_docs = sorted(
        zip(unique_docs, scores),
        key=lambda x: x[1],
        reverse=True,
    )[:final_k]
    
    # 4. Geração
    context = "\n---\n".join([doc.page_content for doc, _ in scored_docs])
    gen_prompt = ChatPromptTemplate.from_messages([
        ("system", "Responda com base no contexto fornecido."),
        ("user", "Pergunta: {query}\n\nContexto:\n{context}")
    ])
    gen_chain = gen_prompt | llm | StrOutputParser()
    
    return gen_chain.invoke({"query": query, "context": context})

# --- Exemplo de uso ---
if __name__ == "__main__":
    docs = [
        Document(page_content="Graph RAG combina grafos de conhecimento com retrieval augmented generation."),
        Document(page_content="Microsoft lançou o GraphRAG em abril de 2024 como uma evolução do RAG tradicional."),
        Document(page_content="RAG usa busca vetorial para recuperar documentos relevantes antes da geração."),
        Document(page_content="LLMs podem alucinar quando não têm contexto suficiente."),
    ]
    vs = Chroma.from_documents(docs, embeddings)
    
    resposta = rag_fusion("Como o Graph RAG melhora o RAG tradicional?", vs)
    print(f"\nResposta: {resposta}")
```

### Bibliotecas Necessárias

| Biblioteca | Uso |
|---|---|
| `langchain` / `langchain-openai` | Pipeline RAG Fusion |
| `rank-bm25` | BM25 para busca esparsa (híbrida) |
| `chromadb` / `qdrant-client` | Vector store |
| `FlagEmbedding` | Reranker para fusão |
| `openai` | LLM e embeddings |

---

## Comparação Geral das Técnicas

| Técnica | Complexidade | Custo | Precisão | Latência | Melhor para |
|---|---|---|---|---|---|
| **RAG Multimodal** | Alta | Alto | Alta | Alta | Conteúdo com imagem/áudio |
| **Graph RAG** | Alta | Médio-Alto | Muito Alta | Média | Raciocínio relacional, perguntas globais |
| **CRAG** | Média | Médio | Alta | Média | Bases com qualidade variável |
| **Self-RAG** | Média | Médio | Alta | Baixa-Média | Decisão adaptativa de retrieval |
| **Rerankers** | Baixa | Baixo-Médio | Muito Alta | Baixa | Melhorar qualquer pipeline RAG |
| **Chunking Adaptativo** | Média | Baixo | Alta | Baixo | Base de qualquer RAG |
| **HyDE** | Baixa | Baixo | Alta | Baixa | Gap semântico query-documento |
| **RAG Fusion** | Média | Médio | Muito Alta | Média | Queries complexas/ambíguas |

---

## Stack Recomendado 2025-2026

### Para Prototipagem Rápida

```
Embedding: text-embedding-3-small (OpenAI) ou BGE-M3 (local)
Vector Store: Chroma (local) ou Pinecone (nuvem)
LLM: GPT-4o-mini ou Claude 3.5 Sonnet
Reranker: BGE-reranker-v2-m3 (local, gratuito)
Chunking: SemanticChunker (LangChain)
Framework: LlamaIndex ou LangChain
Avaliação: RAGAS
```

### Para Produção de Alta Performance

```
Embedding: Cohere embed-v3 ou voyage-3
Vector Store: Qdrant (self-hosted) ou Pinecone (managed)
LLM: GPT-4o ou Claude 3.5/4 Sonnet
Reranker: Cohere Rerank 3.5
Chunking: Hierarchical + Semantic
Pipeline: CRAG + RAG Fusion + Reranker
Graph: LightRAG ou Microsoft GraphRAG (para queries relacionais)
Avaliação: RAGAS + TruLens
Orquestração: LangGraph
```

### Stack Open-Source Completo

```
Embedding: BAAI/BGE-M3 (multilingue)
Vector Store: Qdrant ou Milvus
LLM: LLaMA 3.1 70B ou Qwen 2.5 72B (via vLLM)
Reranker: BAAI/bge-reranker-v2-m3
Chunking: SemanticChunker + AgenticChunker
Graph: LightRAG
Framework: LlamaIndex
Avaliação: RAGAS
Orquestração: LangGraph
```

---

## Referências

### Papers Fundamentais

1. **RAG Original:** Lewis et al. (2020) — "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks"
2. **Self-RAG:** Asai et al. (2023) — "Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection"
3. **CRAG:** Shi et al. (2024) — "Corrective Retrieval Augmented Generation"
4. **HyDE:** Gao et al. (2022) — "Precise Zero-Shot Dense Retrieval without Relevance Labels"
5. **GraphRAG:** Edge et al. (2024) — "From Local to Global: A Graph RAG Approach to Query-Focused Summarization" (Microsoft)
6. **RAG Fusion:** Aakko (2023) — "RAG-Fusion: A New Way of Searching"
7. **RAPTOR:** Sarthi et al. (2024) — "RAPTOR: Recursive Abstractive Processing of Tree Organized Retrieval"
8. **LightRAG:** Guo et al. (2024) — "LightRAG: Simple and Fast Retrieval-Augmented Generation"

### Frameworks e Ferramentas

- **LangChain:** https://python.langchain.com/
- **LlamaIndex:** https://docs.llamaindex.ai/
- **Microsoft GraphRAG:** https://github.com/microsoft/graphrag
- **LightRAG:** https://github.com/HKUDS/LightRAG
- **RAGAS:** https://docs.ragas.io/
- **TruLens:** https://www.trulens.org/
- **Qdrant:** https://qdrant.tech/
- **Pinecone:** https://www.pinecone.io/

### Benchmarks e Avaliação

- **RAGAS Metrics:** Faithfulness, Answer Relevancy, Context Precision, Context Recall
- **ARES:** Automated RAG Evaluation System
- **RGB:** RAG Benchmark (Chinese/English)

---

*Documento gerado em 17 de junho de 2026. As técnicas e bibliotecas mencionadas refletem o estado da arte até esta data.*
