"""
Atena Pipeline - Testes Rapidos (versao enxuta)
Foco: validar integracao com minimas chamadas Ollama
"""
import sys, os, json, time, math, re, hashlib, uuid
import urllib.request

OLLAMA_URL = "http://localhost:11434"
EMBED_MODEL = "nomic-embed-text"
GEN_MODEL = "atena-glm5"
RERANK_MODEL = "gemma4:e2b"

def _ollama_post(path, payload, timeout=30):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(f"{OLLAMA_URL}{path}", data=data,
                                  headers={"Content-Type": "application/json"})
    resp = urllib.request.urlopen(req, timeout=timeout)
    return json.loads(resp.read())

def _generate(prompt, model=GEN_MODEL, temperature=0.7, max_tokens=100):
    r = _ollama_post("/api/generate", {
        "model": model, "prompt": prompt, "stream": False,
        "options": {"temperature": temperature, "num_predict": max_tokens}
    })
    return r.get("response", "")

def _embed(text):
    r = _ollama_post("/api/embeddings", {"model": EMBED_MODEL, "prompt": text}, timeout=30)
    return r.get("embedding", [])

def _cosine(a, b):
    dot = sum(x*y for x, y in zip(a, b))
    na = math.sqrt(sum(x*x for x in a))
    nb = math.sqrt(sum(x*x for x in b))
    return dot / (na * nb) if na and nb else 0.0

# ---- Simple RAG ----
class SimpleRAG:
    def __init__(self):
        self.docs, self.embeds = [], []
    def add(self, texts):
        for t in texts:
            self.docs.append(t)
            self.embeds.append(_embed(t))
    def search(self, query, top_k=3):
        if not self.embeds: return []
        q = _embed(query)
        scored = [(self.docs[i], _cosine(q, e)) for i, e in enumerate(self.embeds)]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]
    @property
    def size(self): return len(self.docs)

# ---- Pipeline ----
SYSTEM = "Voce e Atena, IA criada pelo Senhor Roberio. Responda em portugues do Brasil, de forma direta e clara."

def classify_task(text):
    t = text.lower()
    if any(w in t for w in ["crie","escreva","historia","conto","poema","imagine","invente"]): return "criativo", 0.9
    if any(w in t for w in ["compare","analise","avali","contraste"]): return "analitico", 0.5
    if any(w in t for w in ["implemente","codigo","funcao","script","erro","bug"]): return "tecnico", 0.3
    if any(w in t for w in ["o que e","defina","explique","quem","quando"]): return "factual", 0.2
    return "geral", 0.7

def constitutional_check(response, question):
    issues = []
    if any(p in response.lower() for p in ["nao sei","nao tenho certeza","posso estar errado"]):
        issues.append("incerteza")
    if len(question) > 50 and len(response) < 20:
        issues.append("resposta_curta")
    return issues

def respond(question, rag=None, use_rag=True):
    start = time.time()
    task_type, temp = classify_task(question)
    context = ""
    rag_used = False
    
    if use_rag and rag and rag.size > 0:
        results = rag.search(question, top_k=2)
        if results:
            context = "\n".join([f"[Fonte] {doc}" for doc, _ in results])
            rag_used = True
    
    prompt = f"{SYSTEM}\n\n{context}\nPergunta: {question}\nResposta:" if context else f"{SYSTEM}\nPergunta: {question}\nResposta:"
    answer = _generate(prompt, temperature=temp, max_tokens=100)
    
    issues = constitutional_check(answer, question)
    if issues:
        answer = _generate(prompt + "\n\nSeja direto e factual.", temperature=temp*0.7, max_tokens=100)
    
    return {"answer": answer, "task_type": task_type, "rag_used": rag_used,
            "issues": issues, "time": round(time.time()-start, 1)}

# ---- 4 Loops ----
results = {"passed": 0, "failed": 0, "errors": []}

def check(name, cond, msg=""):
    if cond:
        results["passed"] += 1
        print(f"  OK {name}")
    else:
        results["failed"] += 1
        results["errors"].append(f"FAIL: {name} - {msg}")
        print(f"  FAIL {name}: {msg}")

print("="*50)
print("LOOP 1: UNITARIO (sem Ollama)")
print("="*50)

check("classify criativo", classify_task("Crie uma historia")[0] == "criativo")
check("classify tecnico", classify_task("Implemente uma funcao")[0] == "tecnico")
check("classify factual", classify_task("O que e IA")[0] == "factual")
check("classify analitico", classify_task("Compare Python e JS")[0] == "analitico")
check("classify geral", classify_task("Ola")[0] == "geral")
check("temp criativo > 0.7", classify_task("Crie")[1] > 0.7)
check("temp tecnico < 0.5", classify_task("Implemente")[1] < 0.5)
check("temp factual < 0.5", classify_task("O que e")[1] < 0.5)
check("const OK", len(constitutional_check("Brasilia e a capital.", "Qual a capital?")) == 0)
check("const incerteza", "incerteza" in constitutional_check("Nao sei talvez", "Qual?"))
check("session id unico", len(set(str(uuid.uuid4())[:12] for _ in range(50))) == 50)

print(f"\nLoop 1: {results['passed']}P/{results['failed']}F")
l1p, l1f = results["passed"], results["failed"]

print("\n" + "="*50)
print("LOOP 2: INTEGRACAO (Ollama basico)")
print("="*50)

try:
    req = urllib.request.Request(f"{OLLAMA_URL}/api/tags")
    resp = urllib.request.urlopen(req, timeout=5)
    data = json.loads(resp.read())
    models = [m.get("name","") for m in data.get("data", data.get("models",[]))]
    check("Ollama online", True)
    check("atena-glm5", any("atena" in m for m in models))
    check("nomic-embed", any("nomic" in m for m in models))
except Exception as e:
    check("Ollama online", False, str(e))
    check("atena-glm5", False, "offline")
    check("nomic-embed", False, "offline")

try:
    t0 = time.time()
    emb = _embed("teste")
    check("embedding", len(emb) > 0)
    check("embedding dims", len(emb) > 100)
    check("embedding rapido", time.time()-t0 < 5)
except Exception as e:
    check("embedding", False, str(e))
    check("embedding dims", False, str(e))
    check("embedding rapido", False, str(e))

try:
    t0 = time.time()
    r = _generate("Qual a capital do Brasil? Uma frase.", temperature=0.1, max_tokens=50)
    check("geracao", len(r) > 0)
    check("resposta PT", "brasil" in r.lower())
    check("geracao rapida", time.time()-t0 < 30)
except Exception as e:
    check("geracao", False, str(e))
    check("resposta PT", False, str(e))
    check("geracao rapida", False, str(e))

try:
    e1 = _embed("gato")
    e2 = _embed("gato")
    e3 = _embed("carro")
    check("cosine igual", _cosine(e1, e2) > 0.9)
    check("cosine diff", _cosine(e1, e3) < _cosine(e1, e2))
except Exception as e:
    check("cosine igual", False, str(e))
    check("cosine diff", False, str(e))

print(f"\nLoop 2: {results['passed']-l1p}P/{results['failed']-l1f}F")
l2p, l2f = results["passed"], results["failed"]

print("\n" + "="*50)
print("LOOP 3: PIPELINE (RAG + Behavior)")
print("="*50)

rag = SimpleRAG()
docs = [
    "A IA transforma a medicina. FDA aprovou diagnostico autonomo em 2025.",
    "DeepSeek-V3 usa 671B parametros com 37B ativos. MoE e eficiente.",
    "RAG combina recuperacao e geracao. GraphRAG usa grafos.",
    "O Senhor Roberio e escritor. Seus contos exploram memoria e tempo.",
    "Distonia generalizada afeta movimentos e fala. Tratamentos incluem DBS."
]
rag.add(docs)
check("RAG index", rag.size == 5)

try:
    r = respond("Como a IA e usada na medicina?", rag=rag)
    check("RAG responde", len(r["answer"]) > 0)
    check("RAG ativado", r["rag_used"])
    check("task tipo", r["task_type"] in ["factual","geral"])
    check("tempo ok", r["time"] > 0)
    print(f"  >> {r['answer'][:80]}...")
except Exception as e:
    check("RAG responde", False, str(e))

try:
    r2 = respond("O que e MoE?", rag=rag)
    check("RAG MoE", len(r2["answer"]) > 0)
    print(f"  >> {r2['answer'][:80]}...")
except Exception as e:
    check("RAG MoE", False, str(e))

try:
    r3 = respond("Quem e o Senhor Roberio?", rag=rag)
    check("RAG usuario", len(r3["answer"]) > 0)
    print(f"  >> {r3['answer'][:80]}...")
except Exception as e:
    check("RAG usuario", False, str(e))

try:
    r4 = respond("O que e distonia?", rag=rag)
    check("RAG distonia", len(r4["answer"]) > 0)
    check("sem issues", len(r4["issues"]) == 0)
    print(f"  >> {r4['answer'][:80]}...")
except Exception as e:
    check("RAG distonia", False, str(e))

print(f"\nLoop 3: {results['passed']-l2p}P/{results['failed']-l2f}F")
l3p, l3f = results["passed"], results["failed"]

print("\n" + "="*50)
print("LOOP 4: ESTRESSE")
print("="*50)

try:
    r = respond("O que e IA?", rag=None, use_rag=False)
    check("sem RAG", len(r["answer"]) > 0)
    check("rag desativado", r["rag_used"] == False)
except Exception as e:
    check("sem RAG", False, str(e))

try:
    r = respond("Explique em detalhes " * 10 + "o que e IA?", rag=None, use_rag=False)
    check("pergunta longa", len(r["answer"]) > 0)
except Exception as e:
    check("pergunta longa", False, str(e))

try:
    r = respond("O que e C++? @#$%", rag=None, use_rag=False)
    check("chars especiais", len(r["answer"]) > 0)
except Exception as e:
    check("chars especiais", False, str(e))

try:
    rag2 = SimpleRAG()
    rag2.add(["Python e uma linguagem.", "JavaScript e para web."])
    for i in range(3):
        r = respond(f"O que e programacao? Rodada {i+1}", rag=rag2)
        check(f"seq {i+1}", len(r["answer"]) > 0)
except Exception as e:
    check("sequencial", False, str(e))

try:
    r = respond("Escreva um conto sobre memoria", rag=None, use_rag=False)
    check("criativo detectado", r["task_type"] == "criativo")
except Exception as e:
    check("criativo detectado", False, str(e))

print(f"\nLoop 4: {results['passed']-l3p}P/{results['failed']-l3f}F")

# ---- RESUMO ----
total = results["passed"] + results["failed"]
pct = results["passed"] / total * 100 if total else 0
print("\n" + "="*50)
print(f"RESUMO: {results['passed']}/{total} passaram ({pct:.0f}%)")
print(f"  Loop 1 (Unitario):  {l1p}P/{l1f}F")
print(f"  Loop 2 (Integracao): {l2p-l1p}P/{l2f-l1f}F")
print(f"  Loop 3 (Pipeline):  {l3p-l2p}P/{l3f-l2f}F")
print(f"  Loop 4 (Estresse):  {results['passed']-l3p}P/{results['failed']-l3f}F")
if results["errors"]:
    print(f"\n  Erros:")
    for e in results["errors"]:
        print(f"    {e}")
print("="*50)
