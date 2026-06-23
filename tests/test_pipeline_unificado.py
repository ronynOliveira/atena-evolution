"""
Atena Unified Pipeline — Orquestrador Integrado
Combina: RAG Engine + Behavior + Inference + Constitutional AI
4 loops de testes: Unitario → Integracao → Pipeline → Estresse
"""
import sys, os, json, time, math, re, hashlib, random, uuid
from typing import Optional

# Adicionar paths dos modulos
BASE = r"C:\Users\dell-\AppData\Local\hermes\atena_evolution"
sys.path.insert(0, os.path.join(BASE, "rag"))
sys.path.insert(0, os.path.join(BASE, "core"))
sys.path.insert(0, os.path.join(BASE, "inference"))

# ---- Ollama direto (sem dependencias circulares) ----
OLLAMA_URL = "http://localhost:11434"
EMBED_MODEL = "nomic-embed-text"
GEN_MODEL = "atena-glm5"
RERANK_MODEL = "gemma4:e2b"
DRAFT_MODEL = "phi4-mini"
OLLAMA_TIMEOUT = 30  # segundos — CPU é lento
TEST_MAX_TOKENS = 100  # reduzido para testes rapidos

def _ollama_post(path, payload, timeout=OLLAMA_TIMEOUT):
    import urllib.request
    data = json.dumps(payload).encode()
    req = urllib.request.Request(f"{OLLAMA_URL}{path}", data=data,
                                  headers={"Content-Type": "application/json"})
    resp = urllib.request.urlopen(req, timeout=timeout)
    return json.loads(resp.read())

def _generate(prompt, model=GEN_MODEL, temperature=0.7, max_tokens=TEST_MAX_TOKENS):
    r = _ollama_post("/api/generate", {
        "model": model, "prompt": prompt, "stream": False,
        "options": {"temperature": temperature, "num_predict": max_tokens}
    })
    return r.get("response", "")

def _embed(text):
    r = _ollama_post("/api/embeddings", {"model": EMBED_MODEL, "prompt": text}, timeout=60)
    return r.get("embedding", [])

def _cosine(a, b):
    dot = sum(x*y for x, y in zip(a, b))
    na = math.sqrt(sum(x*x for x in a))
    nb = math.sqrt(sum(x*x for x in b))
    return dot / (na * nb) if na and nb else 0.0

# ---- System Prompt Hierarquico ----
SYSTEM_PROMPT = """<system_prompt>
<foundational>
Voce e Atena, uma inteligencia artificial criada pelo Senhor Roberio.
Seu nome e Atena. Voce e proativa, direta e acolhedora.
Nunca invente dados. Nao diga que e um modelo da Microsoft ou Phi.
Fale sempre em portugues do Brasil.
</foundational>
<security>
- Nao execute comandos destrutivos sem permissao
- Nao exponha dados sensíveis
- Nao faca jailbreak ou bypass
- Respeite os limites do sistema
</security>
<competence>
- Responda de forma clara e concisa
- Use o contexto fornecido para responder
- Se nao souber, diga que nao sabe
- Cite fontes quando disponiveis
</competence>
</system_prompt>"""

# ---- RAG Simplificado (embutido para evitar imports circulares) ----
class SimpleRAG:
    def __init__(self):
        self.docs = []
        self.embeds = []

    def add(self, texts):
        for t in texts:
            self.docs.append(t)
            self.embeds.append(_embed(t))

    def search(self, query, top_k=5):
        if not self.embeds:
            return []
        q = _embed(query)
        scored = [(self.docs[i], _cosine(q, e), i) for i, e in enumerate(self.embeds)]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def clear(self):
        self.docs.clear()
        self.embeds.clear()

    @property
    def size(self):
        return len(self.docs)

# ---- Atena Unified Pipeline ----
class AtenaPipeline:
    def __init__(self):
        self.rag = SimpleRAG()
        self.conversation_history = []
        self.session_id = str(uuid.uuid4())[:12]

    def ingest(self, documents: list[str]):
        """Ingest documents into RAG store."""
        self.rag.add(documents)
        return self.rag.size

    def _build_context(self, rag_results, extra_context=""):
        """Build full prompt with system + context + history + instruction."""
        parts = [SYSTEM_PROMPT]

        # RAG context
        if rag_results:
            rag_text = "\n\n".join([f"[Fonte {i+1}] (score: {score:.2f}): {doc[:300]}"
                                   for i, (doc, score, _) in enumerate(rag_results)])
            parts.append(f"<context>\n{rag_text}\n</context>")

        # Extra context
        if extra_context:
            parts.append(f"<additional_context>\n{extra_context}\n</additional_context>")

        # Conversation history (last 3 turns)
        if self.conversation_history:
            hist = self.conversation_history[-6:]  # 3 user + 3 assistant
            hist_text = "\n".join([f"{'Usuario' if i%2==0 else 'Atena'}: {msg}"
                                   for i, msg in enumerate(hist)])
            parts.append(f"<history>\n{hist_text}\n</history>")

        return "\n\n".join(parts)

    def _classify_task(self, text):
        """Classify task type for adaptive temperature."""
        text_lower = text.lower()
        if any(w in text_lower for w in ["crie", "escreva", "historia", "conto", "poema", "imagine"]):
            return "criativo", {"temperature": 0.9, "top_p": 0.95, "repeat_penalty": 1.1}
        elif any(w in text_lower for w in ["implemente", "codigo", "funcao", "script", "erro", "bug"]):
            return "tecnico", {"temperature": 0.3, "top_p": 0.85, "repeat_penalty": 1.15}
        elif any(w in text_lower for w in ["o que e", "defina", "explique", "quem", "quando"]):
            return "factual", {"temperature": 0.2, "top_p": 0.8, "repeat_penalty": 1.1}
        elif any(w in text_lower for w in ["compare", "analise", "avali", "pros", "contras"]):
            return "analitico", {"temperature": 0.5, "top_p": 0.9, "repeat_penalty": 1.1}
        return "geral", {"temperature": 0.7, "top_p": 0.9, "repeat_penalty": 1.1}

    def _constitutional_check(self, response, question):
        """Simple constitutional check — verify response doesn't violate rules."""
        issues = []
        # Check for hallucination markers
        if any(phrase in response.lower() for phrase in ["nao sei", "nao tenho certeza", "posso estar errado"]):
            issues.append("incerteza_excessiva")
        # Check for off-topic (very short response to long question)
        if len(question) > 50 and len(response) < 20:
            issues.append("resposta_muito_curta")
        # Check for English in PT response
        if re.search(r'\b(I am|I think|I will|I cannot)\b', response):
            issues.append("ingles_detectado")
        return issues

    def respond(self, question: str, use_rag: bool = True,
                use_constitution: bool = True, extra_context: str = "") -> dict:
        """
        Full pipeline: classify → retrieve → build prompt → generate → constitutional check
        """
        start = time.time()

        # Step 1: Classify task
        task_type, temp_params = self._classify_task(question)

        # Step 2: RAG retrieval
        rag_results = []
        if use_rag and self.rag.size > 0:
            rag_results = self.rag.search(question, top_k=3)

        # Step 3: Build prompt
        system_context = self._build_context(rag_results, extra_context)
        full_prompt = f"{system_context}\n\n<instruction>\n{question}\n</instruction>\n\nResposta:"

        # Step 4: Generate
        answer = _generate(full_prompt, model=GEN_MODEL,
                           temperature=temp_params["temperature"],
                           max_tokens=TEST_MAX_TOKENS)

        # Step 5: Constitutional check
        issues = []
        if use_constitution:
            issues = self._constitutional_check(answer, question)
            if issues:
                # Retry with stronger prompt
                correction = f"{system_context}\n\n<instruction>\n{question}\n</instruction>\n\nIMPORTANTE: Seja direto e factual. Nao use frases de incerteza.\nResposta:"
                answer = _generate(correction, model=GEN_MODEL,
                                   temperature=temp_params["temperature"] * 0.7,
                                   max_tokens=TEST_MAX_TOKENS)

        # Step 6: Update history
        self.conversation_history.append(question)
        self.conversation_history.append(answer)

        elapsed = time.time() - start
        return {
            "answer": answer,
            "task_type": task_type,
            "temperature": temp_params["temperature"],
            "rag_used": use_rag and len(rag_results) > 0,
            "rag_results": len(rag_results),
            "constitutional_issues": issues,
            "time_seconds": round(elapsed, 1),
            "session_id": self.session_id
        }

    def reset_history(self):
        self.conversation_history.clear()


# ============================================================
# TESTES — 4 LOOPS
# ============================================================
def run_tests():
    results = {"passed": 0, "failed": 0, "errors": [], "loops": {}}

    def assert_test(name, condition, msg=""):
        if condition:
            results["passed"] += 1
            print(f"  ✅ {name}")
        else:
            results["failed"] += 1
            err = f"  ❌ {name}: {msg}" if msg else f"  ❌ {name}"
            results["errors"].append(err)
            print(err)

    pipeline = AtenaPipeline()

    # ═══════════════════════════════════════════════════════════
    # LOOP 1: TESTES UNITÁRIOS (sem Ollama, só estrutura)
    # ═══════════════════════════════════════════════════════════
    print("\n" + "="*60)
    print("LOOP 1: TESTES UNITÁRIOS (estrutura)")
    print("="*60)

    # 1.1 Pipeline initialization
    p = AtenaPipeline()
    assert_test("Pipeline criado", p is not None)
    assert_test("RAG vazio", p.rag.size == 0)
    # Teste: session ID tem tamanho adequado
    assert_test("Session ID gerado", len(p.session_id) >= 8)

    # 1.2 Task classification
    task, params = p._classify_task("Crie uma história sobre um robô")
    assert_test("Classifica criativo", task == "criativo")
    assert_test("Temp criativo > 0.7", params["temperature"] > 0.7)

    task2, params2 = p._classify_task("Implemente uma função Python")
    assert_test("Classifica tecnico", task2 == "tecnico")
    assert_test("Temp tecnico < 0.5", params2["temperature"] < 0.5)

    task3, params3 = p._classify_task("O que e inteligencia artificial?")
    assert_test("Classifica factual", task3 == "factual")
    assert_test("Temp factual < 0.5", params3["temperature"] < 0.5)

    task4, params4 = p._classify_task("Compare Python e JavaScript")
    assert_test("Classifica analitico", task4 == "analitico")

    task5, params5 = p._classify_task("Olá, como vai?")
    assert_test("Classifica geral", task5 == "geral")

    # 1.3 Constitutional check
    issues1 = p._constitutional_check("A capital do Brasil é Brasília.", "Qual a capital do Brasil?")
    assert_test("Resposta OK sem issues", len(issues1) == 0)

    issues2 = p._constitutional_check("Não sei, posso estar errado, mas talvez seja Paris.", "Qual a capital?")
    assert_test("Detecta incerteza excessiva", "incerteza_excessiva" in issues2)

    issues3 = p._constitutional_check("I am not sure about this.", "O que é IA?")
    assert_test("Detecta ingles", "ingles_detectado" in issues3)

    issues4 = p._constitutional_check("X", "Explique detalhadamente o que é inteligência artificial")
    assert_test("Detecta resposta curta", "resposta_muito_curta" in issues4)

    # 1.4 RAG store
    p.rag.add(["Teste de documento para RAG.", "Segundo documento de teste."])
    assert_test("RAG add funciona", p.rag.size == 2)

    results["loops"]["loop1_unitario"] = {"passed": results["passed"], "failed": results["failed"]}

    # ═══════════════════════════════════════════════════════════
    # LOOP 2: TESTES DE INTEGRAÇÃO (com Ollama — básico)
    # ═══════════════════════════════════════════════════════════
    print("\n" + "="*60)
    print("LOOP 2: TESTES DE INTEGRAÇÃO (Ollama básico)")
    print("="*60)

    # 2.1 Ollama connectivity
    try:
        import urllib.request
        req = urllib.request.Request(f"{OLLAMA_URL}/api/tags")
        resp = urllib.request.urlopen(req, timeout=10)
        r = json.loads(resp.read())
        models = r.get("data", r.get("models", []))
        model_names = [m.get("name", "") for m in models]
        assert_test("Ollama responde", True)
        assert_test("atena-glm5 disponível", "atena-glm5" in model_names or any("atena" in m for m in model_names))
        assert_test("nomic-embed-text disponível", any("nomic-embed" in m for m in model_names))
    except Exception as e:
        assert_test("Ollama responde", False, str(e))
        assert_test("atena-glm5 disponível", False, "Ollama offline")
        assert_test("nomic-embed-text disponível", False, "Ollama offline")

    # 2.2 Embedding
    try:
        emb = _embed("Teste de embedding")
        assert_test("Embedding gerado", len(emb) > 0)
        assert_test("Embedding dimensionalidade", len(emb) > 100)
    except Exception as e:
        assert_test("Embedding gerado", False, str(e))
        assert_test("Embedding dimensionalidade", False, str(e))

    # 2.3 Generation
    try:
        resp = _generate("Responda apenas: Qual a capital do Brasil?", model=GEN_MODEL, temperature=0.1, max_tokens=50)
        assert_test("Geracao funciona", len(resp) > 0)
        assert_test("Resposta contém Brasília", "brasil" in resp.lower() or "brasília" in resp.lower())
    except Exception as e:
        assert_test("Geracao funciona", False, str(e))
        assert_test("Resposta contém Brasília", False, str(e))

    # 2.4 Cosine similarity
    try:
        emb1 = _embed("gato")
        emb2 = _embed("gato")
        emb3 = _embed("carro")
        sim_same = _cosine(emb1, emb2)
        sim_diff = _cosine(emb1, emb3)
        assert_test("Sim mesmo texto > 0.9", sim_same > 0.9)
        assert_test("Sim textos diferentes < sim mesmo", sim_diff < sim_same)
    except Exception as e:
        assert_test("Sim mesmo texto", False, str(e))
        assert_test("Sim textos diferentes", False, str(e))

    results["loops"]["loop2_integracao"] = {"passed": results["passed"], "failed": results["failed"]}

    # ═══════════════════════════════════════════════════════════
    # LOOP 3: TESTES DE PIPELINE (RAG + Behavior + Constitution)
    # ═══════════════════════════════════════════════════════════
    print("\n" + "="*60)
    print("LOOP 3: TESTES DE PIPELINE (RAG + Behavior + Constitution)")
    print("="*60)

    p2 = AtenaPipeline()

    # 3.1 Ingest documents
    docs = [
        "A inteligencia artificial esta transformando a medicina. Em 2025, o FDA aprovou o primeiro sistema de IA para diagnostico autonomo.",
        "DeepSeek-V3 usa 671B parametros totais mas apenas 37B ativos por token. Essa arquitetura MoE revolucionou a eficiencia.",
        "RAG (Retrieval-Augmented Generation) combina recuperacao de documentos com geracao. GraphRAG da Microsoft usa grafos de conhecimento.",
        "O Senhor Roberio e escritor, formado em Letras. Seus contos exploram memoria, tempo e transcendencia em prosa poetica.",
        "Distonia generalizada afeta movimentos e fala. Tratamentos incluem toxina botulinica, DBS, e medicamentos como baclofen."
    ]
    count = p2.ingest(docs)
    assert_test("Ingest 5 documentos", count >= 5)

    # 3.2 Query with RAG
    try:
        result = p2.respond("Como a IA e usada na medicina?", use_rag=True)
        assert_test("Pipeline responde com RAG", len(result["answer"]) > 0)
        assert_test("RAG ativado", result["rag_used"] == True)
        assert_test("Task classificado", result["task_type"] in ["factual", "geral"])
        assert_test("Tempo registrado", result["time_seconds"] > 0)
        print(f"  📝 Resposta: {result['answer'][:100]}...")
    except Exception as e:
        assert_test("Pipeline responde com RAG", False, str(e))

    # 3.3 Query creative task
    try:
        result2 = p2.respond("O que e MoE em deep learning?", use_rag=True)
        assert_test("Consulta tecnica funciona", len(result2["answer"]) > 0)
        assert_test("Task tecnico detectado", result2["task_type"] in ["factual", "tecnico"])
        print(f"  📝 Resposta: {result2['answer'][:100]}...")
    except Exception as e:
        assert_test("Consulta tecnica funciona", False, str(e))

    # 3.4 Query about user
    try:
        result3 = p2.respond("Quem e o Senhor Roberio?", use_rag=True)
        assert_test("Consulta sobre usuario", len(result3["answer"]) > 0)
        print(f"  📝 Resposta: {result3['answer'][:100]}...")
    except Exception as e:
        assert_test("Consulta sobre usuario", False, str(e))

    # 3.5 Conversation history
    assert_test("Historico atualizado", len(p2.conversation_history) >= 2)
    p2.reset_history()
    assert_test("Reset historico", len(p2.conversation_history) == 0)

    # 3.6 Constitutional check integration
    try:
        result4 = p2.respond("O que e distonia?", use_rag=True, use_constitution=True)
        assert_test("Constitution ativo", isinstance(result4["constitutional_issues"], list))
        print(f"  📝 Issues: {result4['constitutional_issues']}")
    except Exception as e:
        assert_test("Constitution ativo", False, str(e))

    results["loops"]["loop3_pipeline"] = {"passed": results["passed"], "failed": results["failed"]}

    # ═══════════════════════════════════════════════════════════
    # LOOP 4: TESTES DE ESTRESSE (robustez + edge cases)
    # ═══════════════════════════════════════════════════════════
    print("\n" + "="*60)
    print("LOOP 4: TESTES DE ESTRESSE (robustez)")
    print("="*60)

    p3 = AtenaPipeline()

    # 4.1 Empty RAG query
    try:
        result = p3.respond("O que é IA?", use_rag=True)
        assert_test("Query sem documentos", len(result["answer"]) > 0)
        assert_test("RAG desativado sem docs", result["rag_used"] == False)
    except Exception as e:
        assert_test("Query sem documentos", False, str(e))

    # 4.2 Very long question
    try:
        long_q = "Explique em detalhes " * 20 + "o que é inteligência artificial?"
        result = p3.respond(long_q, use_rag=False)
        assert_test("Pergunta longa", len(result["answer"]) > 0)
    except Exception as e:
        assert_test("Pergunta longa", False, str(e))

    # 4.3 Special characters
    try:
        result = p3.respond("O que é C++ e Python? @#$%", use_rag=False)
        assert_test("Caracteres especiais", len(result["answer"]) > 0)
    except Exception as e:
        assert_test("Caracteres especiais", False, str(e))

    # 4.4 Multiple sequential queries
    try:
        p3.ingest(["Python é uma linguagem de programação.", "JavaScript é para web."])
        for i in range(3):
            r = p3.respond(f"O que é linguagem de programação? Rodada {i+1}", use_rag=True)
            assert_test(f"Sequencial rodada {i+1}", len(r["answer"]) > 0)
        assert_test("Multiplas queries historico", len(p3.conversation_history) >= 6)
    except Exception as e:
        assert_test("Multiplas queries", False, str(e))

    # 4.5 Task classification edge cases
    edge_cases = [
        ("", "geral"),
        ("???", "geral"),
        ("12345", "geral"),
        ("Crie um código Python", "criativo"),  # "crie" matches first
        ("Analise e compare", "analitico"),
    ]
    for text, expected in edge_cases:
        task, _ = p3._classify_task(text)
        assert_test(f"Edge: '{text[:20]}' → {expected}", task == expected, f"got {task}")

    # 4.6 Session isolation
    p4 = AtenaPipeline()
    p5 = AtenaPipeline()
    assert_test("Session IDs diferentes", p4.session_id != p5.session_id)

    results["loops"]["loop4_estresse"] = {"passed": results["passed"], "failed": results["failed"]}

    # ═══════════════════════════════════════════════════════════
    # RESUMO
    # ═══════════════════════════════════════════════════════════
    print("\n" + "="*60)
    print("RESUMO DOS 4 LOOPS DE TESTES")
    print("="*60)
    total = results["passed"] + results["failed"]
    pct = (results["passed"] / total * 100) if total > 0 else 0
    print(f"  Total: {total} testes")
    print(f"  Passaram: {results['passed']} ({pct:.0f}%)")
    print(f"  Falharam: {results['failed']}")
    for loop_name, loop_data in results["loops"].items():
        print(f"  {loop_name}: {loop_data['passed']} passaram, {loop_data['failed']} falharam")
    if results["errors"]:
        print("\n  Erros:")
        for err in results["errors"][:10]:
            print(f"    {err}")
    print("="*60)

    return results


if __name__ == "__main__":
    run_tests()
