"""
Atena RAG Engine — RAG Avancado com Chunking Semantico, Reranking, HyDE, Fusion e CRAG
Hardware: i5-1235U, 15.7GB RAM — tudo local via Ollama, custo ZERO
"""
import json, re, math, hashlib, os, time
from typing import Optional
import urllib.request

OLLAMA_URL = "http://localhost:11434"
EMBED_MODEL = "nomic-embed-text"
RERANK_MODEL = "gemma4:e2b"
GEN_MODEL = "atena-glm5"

# ---- Ollama helpers ----
def _ollama_post(path: str, payload: dict, timeout: int = 120) -> dict:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{OLLAMA_URL}{path}", data=data,
        headers={"Content-Type": "application/json"}
    )
    resp = urllib.request.urlopen(req, timeout=timeout)
    return json.loads(resp.read())

def _ollama_generate(prompt: str, model: str = GEN_MODEL,
                     temperature: float = 0.7, max_tokens: int = 512,
                     stream: bool = False) -> str:
    r = _ollama_post("/api/generate", {
        "model": model, "prompt": prompt, "stream": stream,
        "options": {"temperature": temperature, "num_predict": max_tokens}
    })
    return r.get("response", "")

def _ollama_embed(text: str) -> list[float]:
    r = _ollama_post("/api/embeddings", {
        "model": EMBED_MODEL, "prompt": text
    }, timeout=60)
    return r.get("embedding", [])

# ---- Embedding helpers ----
def _cosine_sim(a: list[float], b: list[float]) -> float:
    dot = sum(x*y for x, y in zip(a, b))
    na = math.sqrt(sum(x*x for x in a))
    nb = math.sqrt(sum(x*x for x in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)

def _embed_batch(texts: list[str], label: str = "") -> list[list[float]]:
    """Embed a batch of texts. Returns list of embeddings."""
    results = []
    for i, t in enumerate(texts):
        if label:
            print(f"  [{label}] {i+1}/{len(texts)}: {t[:50]}...")
        results.append(_ollama_embed(t))
    return results

# ---- 1. Semantic Chunking ----
def _split_sentences(text: str) -> list[str]:
    """Split text into sentences using regex."""
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s.strip() for s in sentences if s.strip()]

def semantic_chunking(text: str, target_size: int = 300, overlap: int = 2) -> list[str]:
    """
    Adaptive semantic chunking:
    1. Split into sentences
    2. Embed each sentence
    3. Group consecutive sentences until target_size reached
    4. Add overlap of N sentences between chunks
    """
    sentences = _split_sentences(text)
    if not sentences:
        return []
    if len(sentences) <= 3:
        return [" ".join(sentences)]

    # Embed sentences
    print(f"  Embedding {len(sentences)} sentencas...")
    embeds = _embed_batch(sentences, "embed")

    chunks = []
    current_group = [sentences[0]]
    current_len = len(sentences[0].split())

    for i in range(1, len(sentences)):
        sent_len = len(sentences[i].split())
        if current_len + sent_len > target_size and len(current_group) >= 2:
            chunks.append(" ".join(current_group))
            # Overlap: keep last N sentences
            current_group = current_group[-overlap:] if overlap > 0 else []
            current_len = sum(len(s.split()) for s in current_group)
        current_group.append(sentences[i])
        current_len += sent_len

    if current_group:
        chunks.append(" ".join(current_group))

    return chunks

# ---- 2. Simple in-memory vector store ----
class VectorStore:
    def __init__(self):
        self.docs: list[str] = []
        self.embeds: list[list[float]] = []
        self.meta: list[dict] = []

    def add(self, texts: list[str], metadata: Optional[list[dict]] = None):
        if not texts:
            return
        print(f"  Indexando {len(texts)} chunks...")
        new_embeds = _embed_batch(texts, "index")
        self.docs.extend(texts)
        self.embeds.extend(new_embeds)
        if metadata:
            self.meta.extend(metadata)
        else:
            self.meta.extend([{} for _ in texts])

    def search(self, query: str, top_k: int = 10) -> list[tuple[str, float, int]]:
        """Return (doc, score, index) tuples sorted by score desc."""
        if not self.embeds:
            return []
        q_emb = _ollama_embed(query)
        results = []
        for i, e in enumerate(self.embeds):
            score = _cosine_sim(q_emb, e)
            results.append((self.docs[i], score, i))
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def clear(self):
        self.docs.clear()
        self.embeds.clear()
        self.meta.clear()

    @property
    def size(self):
        return len(self.docs)

# ---- 3. Reranking ----
def rerank_chunks(question: str, chunks: list[str], top_k: int = 5) -> list[tuple[str, float]]:
    """Rerank chunks using LLM scoring via Ollama."""
    scored = []
    for i, chunk in enumerate(chunks):
        prompt = f"""Avalie a relevancia deste texto para a pergunta.
Pergunta: {question}
Texto: {chunk[:500]}
Responda apenas um numero de 0 a 10 (10 = totalmente relevante):"""
        try:
            resp = _ollama_generate(prompt, model=RERANK_MODEL, temperature=0.1, max_tokens=10)
            # Extract number
            nums = re.findall(r'\d+', resp)
            score = int(nums[0]) / 10.0 if nums else 0.5
        except Exception:
            score = 0.5
        scored.append((chunk, score))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top_k]

# ---- 4. HyDE ----
def hyde_query(question: str) -> str:
    """Generate a hypothetical document for the query."""
    prompt = f"""Escreva um paragrafo curto (3-5 frases) que responda esta pergunta de forma factual e detalhada. Seja especifico.
Pergunta: {question}"""
    return _ollama_generate(prompt, model=GEN_MODEL, temperature=0.8, max_tokens=200)

# ---- 5. RAG Fusion (Multi-Query) ----
def expand_query(question: str, n: int = 3) -> list[str]:
    """Generate query variations for RAG Fusion."""
    prompt = f"""Gere {n} variacoes desta pergunta, cada uma com enfoque diferente.
Pergunta original: {question}
Liste as variacoes, uma por linha, sem numeracao:"""
    resp = _ollama_generate(prompt, model=GEN_MODEL, temperature=0.9, max_tokens=200)
    variations = [v.strip() for v in resp.split('\n') if v.strip() and len(v.strip()) > 10]
    return [question] + variations[:n]

def reciprocal_rank_fusion(ranked_lists: list[list[tuple[str, float]]], k: int = 60) -> list[tuple[str, float]]:
    """Combine multiple ranked lists using RRF."""
    scores: dict[str, float] = {}
    for ranked in ranked_lists:
        for rank, (doc, _) in enumerate(ranked):
            if doc not in scores:
                scores[doc] = 0.0
            scores[doc] += 1.0 / (k + rank + 1)
    results = [(doc, score) for doc, score in scores.items()]
    results.sort(key=lambda x: x[1], reverse=True)
    return results

# ---- 6. CRAG (Corrective RAG) ----
def evaluate_relevance(question: str, chunks: list[str]) -> list[float]:
    """Evaluate relevance of each chunk. Returns scores 0-1."""
    scores = []
    for chunk in chunks:
        prompt = f"""Pergunta: {question}
Trecho: {chunk[:300]}
Este trecho responde a pergunta? Responda apenas: SIM ou NAO e um score de 0-10."""
        try:
            resp = _ollama_generate(prompt, model=RERANK_MODEL, temperature=0.1, max_tokens=30)
            nums = re.findall(r'\d+', resp)
            score = int(nums[0]) / 10.0 if nums else 0.3
            if "SIM" in resp.upper():
                score = max(score, 0.6)
        except Exception:
            score = 0.3
        scores.append(min(max(score, 0.0), 1.0))
    return scores

# ---- Main RAG Engine ----
class AtenaRAGEngine:
    def __init__(self):
        self.store = VectorStore()

    def add_documents(self, texts: list[str], metadata: Optional[list[dict]] = None):
        """Chunk and index documents."""
        all_chunks = []
        all_meta = []
        for i, text in enumerate(texts):
            chunks = semantic_chunking(text)
            for chunk in chunks:
                all_chunks.append(chunk)
                meta = {"doc_id": i, "chunk_hash": hashlib.md5(chunk.encode()).hexdigest()[:8]}
                if metadata and i < len(metadata):
                    meta.update(metadata[i])
                all_meta.append(meta)
        self.store.add(all_chunks, all_meta)
        print(f"  Total: {self.store.size} chunks indexados")

    def query(self, question: str, use_hyde: bool = True,
              use_fusion: bool = True, use_rerank: bool = True,
              top_k: int = 5) -> dict:
        """
        Full RAG pipeline:
        1. HyDE (optional): generate hypothetical doc, use its embedding for search
        2. Fusion (optional): expand query, search each, RRF combine
        3. Rerank (optional): LLM-based reranking
        4. CRAG: evaluate relevance, filter low scores
        5. Generate answer with top chunks as context
        """
        start_time = time.time()
        method_parts = []

        # Step 1: Retrieval
        if use_hyde:
            method_parts.append("HyDE")
            hypo_doc = hyde_query(question)
            hypo_emb = _ollama_embed(hypo_doc)
            # Search with hypothetical embedding
            raw_results = []
            for i, e in enumerate(self.store.embeds):
                score = _cosine_sim(hypo_emb, e)
                raw_results.append((self.store.docs[i], score, i))
            raw_results.sort(key=lambda x: x[1], reverse=True)
            candidates = raw_results[:20]
        elif use_fusion:
            method_parts.append("Fusion")
            queries = expand_query(question)
            ranked_lists = []
            for q in queries:
                results = self.store.search(q, top_k=10)
                ranked_lists.append(results)
            fused = reciprocal_rank_fusion(ranked_lists)
            candidates = [(doc, score, -1) for doc, score in fused[:20]]
        else:
            method_parts.append("Standard")
            candidates = self.store.search(question, top_k=20)

        if not candidates:
            return {
                "answer": "Nao encontrei informacoes relevantes na base de conhecimento.",
                "sources": [], "scores": [], "method_used": "+".join(method_parts),
                "time_seconds": time.time() - start_time
            }

        chunk_texts = [c[0] for c in candidates]

        # Step 2: Reranking
        if use_rerank and len(chunk_texts) > top_k:
            method_parts.append("Rerank")
            reranked = rerank_chunks(question, chunk_texts, top_k=top_k + 3)
            chunk_texts = [r[0] for r in reranked]
            rerank_scores = [r[1] for r in reranked]
        else:
            rerank_scores = [c[1] for c in candidates[:top_k + 3]]

        # Step 3: CRAG - evaluate relevance
        method_parts.append("CRAG")
        relevance_scores = evaluate_relevance(question, chunk_texts)
        filtered = [(chunk, score) for chunk, score in zip(chunk_texts, relevance_scores) if score >= 0.3]

        if not filtered:
            # Fallback: use top chunks anyway
            filtered = list(zip(chunk_texts[:top_k], relevance_scores[:top_k]))

        # Take top_k
        final_chunks = filtered[:top_k]
        context = "\n\n".join([f"[Fonte {i+1}]: {chunk}" for i, (chunk, _) in enumerate(final_chunks)])

        # Step 4: Generate answer
        method_parts.append("Generate")
        prompt = f"""Com base no contexto abaixo, responda a pergunta de forma clara e direta em portugues do Brasil.

Contexto:
{context}

Pergunta: {question}

Resposta:"""
        answer = _ollama_generate(prompt, model=GEN_MODEL, temperature=0.7, max_tokens=512)

        elapsed = time.time() - start_time
        return {
            "answer": answer,
            "sources": [chunk[:200] + "..." for chunk, _ in final_chunks],
            "scores": [round(score, 2) for _, score in final_chunks],
            "method_used": " + ".join(method_parts),
            "time_seconds": round(elapsed, 1),
            "chunks_retrieved": len(candidates),
            "chunks_used": len(final_chunks)
        }

# ---- Tests ----
if __name__ == "__main__":
    print("=== Atena RAG Engine - Testes ===\n")

    engine = AtenaRAGEngine()

    # Test documents
    docs = [
        """A inteligencia artificial esta transformando a medicina. Modelos de linguagem como GPT-4 e Med-PaLM 2 
        estao sendo usados para diagnostico assistido, analise de prontuarios e descoberta de medicamentos. 
        Em 2025, o FDA aprovou o primeiro sistema de IA para diagnostico autonomo de retinopatia diabetica.
        A precisao desses sistemas atingiu 95% em testes clinicos, superando oftalmologistas humanos em alguns casos.""",

        """Redes neurais avancadas como Mixture of Experts (MoE) permitem modelos com centenas de bilhoes de 
        parametros mas com custo computacional proporcional apenas aos parametros ativos. DeepSeek-V3, 
        lancado em dezembro de 2024, usa 671B parametros totais mas apenas 37B ativos por token.
        Essa arquitetura revolucionou a eficiencia de LLMs.""",

        """RAG (Retrieval-Augmented Generation) e uma tecnica que combina recuperacao de documentos com 
        geracao de texto. O GraphRAG da Microsoft, lancado em abril de 2024, usa grafos de conhecimento 
        para melhorar a qualidade da recuperacao. Em 2025, tecnicas como CRAG (Corrective RAG) e 
        Self-RAG adicionaram capacidades de auto-correcao e avaliacao de relevancia."""
    ]

    print("1. Indexando documentos...")
    engine.add_documents(docs)
    print(f"   Chunks na base: {engine.store.size}\n")

    print("2. Consulta com HyDE + Rerank + CRAG:")
    result = engine.query("Como a IA esta sendo usada na medicina?",
                          use_hyde=True, use_fusion=False, use_rerank=True)
    print(f"   Metodo: {result['method_used']}")
    print(f"   Tempo: {result['time_seconds']}s")
    print(f"   Chunks: {result['chunks_retrieved']} recuperados, {result['chunks_used']} usados")
    print(f"   Resposta: {result['answer'][:200]}...\n")

    print("3. Consulta com Fusion:")
    result2 = engine.query("O que e Mixture of Experts e como funciona?",
                           use_hyde=False, use_fusion=True, use_rerank=True)
    print(f"   Metodo: {result2['method_used']}")
    print(f"   Tempo: {result2['time_seconds']}s")
    print(f"   Resposta: {result2['answer'][:200]}...\n")

    print("4. Avaliacao de relevancia (CRAG):")
    test_chunks = [
        "O FDA aprovou sistema de IA para diagnostico em 2025.",
        "O clima hoje esta ensolarado com 25 graus.",
        "DeepSeek-V3 usa 671B parametros com 37B ativos."
    ]
    scores = evaluate_relevance("Como a IA e usada na medicina?", test_chunks)
    for chunk, score in zip(test_chunks, scores):
        print(f"   Score {score:.1f}: {chunk[:60]}...")

    print("\n=== Testes concluidos ===")
