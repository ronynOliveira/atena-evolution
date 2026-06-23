"""
Atena Validacao — Testes de Rotador, Otimizacao e Qualidade de Dados
Fase 3: Validacao completa do pipeline
"""
import sys, os, json, time, math, re, hashlib, uuid
sys.stdout.reconfigure(line_buffering=True)
import urllib.request

OLLAMA_URL = "http://localhost:11434"
EMBED_MODEL = "nomic-embed-text"
GEN_MODEL = "atena-glm5"

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

SYSTEM = "Voce e Atena, IA criada pelo Senhor Roberio. Responda em portugues do Brasil, de forma direta e clara."

def classify_task(text):
    t = text.lower()
    if any(w in t for w in ["crie","escreva","historia","conto","poema","imagine","invente"]): return "criativo", 0.9
    if any(w in t for w in ["compare","analise","avali","contraste"]): return "analitico", 0.5
    if any(w in t for w in ["implemente","codigo","funcao","script","erro","bug"]): return "tecnico", 0.3
    if any(w in t for w in ["o que e","defina","explique","quem","quando"]): return "factual", 0.2
    return "geral", 0.7

def const_check(response, question):
    issues = []
    if any(p in response.lower() for p in ["nao sei","nao tenho certeza","posso estar errado"]): issues.append("incerteza")
    if len(question) > 50 and len(response) < 20: issues.append("resposta_curta")
    if re.search(r'\b(I am|I think|I will|I cannot)\b', response): issues.append("ingles")
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
    issues = const_check(answer, question)
    return {"answer": answer, "task_type": task_type, "rag_used": rag_used, "issues": issues, "time": round(time.time()-start, 1)}

results = {"passed": 0, "failed": 0, "errors": [], "details": []}

def check(name, cond, msg=""):
    if cond:
        results["passed"] += 1
        results["details"].append(f"  OK {name}")
        print(f"  OK {name}")
    else:
        results["failed"] += 1
        results["details"].append(f"  FAIL {name}: {msg}")
        results["errors"].append(f"FAIL: {name} - {msg}")
        print(f"  FAIL {name}: {msg}")

# ═══════════════════════════════════════════════════════════
# PARTE 1: ROTADOR — 20 tarefas
# ═══════════════════════════════════════════════════════════
print("\n" + "="*60)
print("PARTE 1: ROTADOR (20 tarefas)")
print("="*60)

rotator_tests = [
    # Criativo (4)
    ("Crie uma historia sobre um robo", "criativo"),
    ("Escreva um poema sobre o mar", "criativo"),
    ("Imagine um mundo sem dinheiro", "criativo"),
    ("Conte um conto de fadas moderno", "criativo"),
    # Tecnico (4)
    ("Implemente uma funcao de busca binaria", "tecnico"),
    ("Codigo Python para ordenar lista", "tecnico"),
    ("Funcao recursiva para fibonacci", "tecnico"),
    ("Script para ler arquivo CSV", "tecnico"),
    # Factual (4)
    ("O que e inteligencia artificial", "factual"),
    ("Defina machine learning", "factual"),
    ("Quem e Alan Turing", "factual"),
    ("Quando foi criado o Python", "factual"),
    # Analitico (4)
    ("Compare Python e JavaScript", "analitico"),
    ("Analise pros e contras do Rust", "analitico"),
    ("Avalie o impacto da IA no trabalho", "analitico"),
    ("Compare SQL e NoSQL", "analitico"),
    # Geral (4)
    ("Ola, como vai", "geral"),
    ("Bom dia", "geral"),
    ("Obrigado pela ajuda", "geral"),
    ("Adeus", "geral"),
]

for text, expected in rotator_tests:
    task, temp = classify_task(text)
    check(f"Rotador: '{text[:30]}' → {expected}", task == expected, f"got {task}")
    check(f"Temp {expected}: {temp}", 0.0 <= temp <= 1.0, f"temp={temp}")

# Edge cases do rotador
check("Rotador: vazio", classify_task("")[0] == "geral")
check("Rotador: ???", classify_task("???")[0] == "geral")
check("Rotador: 12345", classify_task("12345")[0] == "geral")
check("Rotador: muito longo", classify_task("a" * 10000)[0] in ["criativo","tecnico","factual","analitico","geral"])

# Temperatura ranges
_, temp_criativo = classify_task("Crie algo")
_, temp_tecnico = classify_task("Implemente algo")
_, temp_factual = classify_task("O que e algo")
_, temp_analitico = classify_task("Compare algo")
_, temp_geral = classify_task("Ola")

check("Temp criativo >= 0.8", temp_criativo >= 0.8, f"got {temp_criativo}")
check("Temp tecnico <= 0.5", temp_tecnico <= 0.5, f"got {temp_tecnico}")
check("Temp factual <= 0.4", temp_factual <= 0.4, f"got {temp_factual}")
check("Temp analitico 0.3-0.7", 0.3 <= temp_analitico <= 0.7, f"got {temp_analitico}")
check("Temp geral 0.5-0.9", 0.5 <= temp_geral <= 0.9, f"got {temp_geral}")

p1p, p1f = results["passed"], results["failed"]
print(f"\n  Rotador: {p1p}P/{p1f}F")

# ═══════════════════════════════════════════════════════════
# PARTE 2: OTIMIZACAO
# ═══════════════════════════════════════════════════════════
print("\n" + "="*60)
print("PARTE 2: OTIMIZACAO")
print("="*60)

# 2.1 Embedding speed
try:
    t0 = time.time()
    emb = _embed("teste de velocidade")
    embed_time = time.time() - t0
    check("Embedding velocidade < 2s", embed_time < 2.0, f"{embed_time:.1f}s")
    check("Embedding dims = 768", len(emb) == 768, f"got {len(emb)}")
except Exception as e:
    check("Embedding velocidade", False, str(e))
    check("Embedding dims", False, str(e))

# 2.2 Generation speed
try:
    t0 = time.time()
    r = _generate("Oi", temperature=0.1, max_tokens=10)
    gen_time = time.time() - t0
    check("Geracao velocidade < 30s", gen_time < 30.0, f"{gen_time:.1f}s")
    check("Geracao resposta curta", len(r) > 0)
except Exception as e:
    check("Geracao velocidade", False, str(e))
    check("Geracao resposta", False, str(e))

# 2.3 Pipeline with RAG
try:
    rag = SimpleRAG()
    rag.add([
        "A IA transforma a medicina moderna.",
        "Python e uma linguagem de programacao.",
        "O Senhor Roberio e escritor e tecnico.",
    ])
    t0 = time.time()
    r = respond("O que e IA?", rag=rag)
    pipe_time = time.time() - t0
    check("Pipeline RAG < 60s", pipe_time < 60.0, f"{pipe_time:.1f}s")
    check("Pipeline RAG ativo", r["rag_used"])
    check("Pipeline responde", len(r["answer"]) > 0)
except Exception as e:
    check("Pipeline RAG", False, str(e))

# 2.4 Cosine similarity
try:
    e1 = _embed("inteligencia artificial")
    e2 = _embed("inteligencia artificial")
    e3 = _embed("receita de bolo")
    sim_same = _cosine(e1, e2)
    sim_diff = _cosine(e1, e3)
    check("Cosine mesmo > 0.95", sim_same > 0.95, f"{sim_same:.3f}")
    check("Cosine diff < mesmo", sim_diff < sim_same, f"diff={sim_diff:.3f} same={sim_same:.3f}")
    check("Cosine diff < 0.8", sim_diff < 0.8, f"{sim_diff:.3f}")
except Exception as e:
    check("Cosine", False, str(e))

# 2.5 RAG melhora resposta
try:
    rag2 = SimpleRAG()
    rag2.add(["A capital do Brasil e Brasilia, fundada em 1960."])
    r_com_rag = respond("Qual a capital do Brasil?", rag=rag2)
    r_sem_rag = respond("Qual a capital do Brasil?", rag=None, use_rag=False)
    check("RAG: resposta com contexto", "brasilia" in r_com_rag["answer"].lower() or "brasil" in r_com_rag["answer"].lower())
    check("RAG: sem contexto tambem funciona", len(r_sem_rag["answer"]) > 0)
except Exception as e:
    check("RAG melhora resposta", False, str(e))

p2p, p2f = results["passed"], results["failed"]
print(f"\n  Otimizacao: {p2p-p1p}P/{p2f-p1f}F")

# ═══════════════════════════════════════════════════════════
# PARTE 3: QUALIDADE DE DADOS DE SAIDA
# ═══════════════════════════════════════════════════════════
print("\n" + "="*60)
print("PARTE 3: QUALIDADE DE DADOS DE SAIDA")
print("="*60)

# 3.1 Idioma portugues
try:
    r = _generate("Qual a capital do Brasil? Responda em uma frase.", temperature=0.1, max_tokens=50)
    # Verificar se ha palavras PT-BR comuns
    pt_words = ["capital", "brasil", "brasilia", "cidade", "pais", "uma", "que", "para"]
    has_pt = any(w in r.lower() for w in pt_words)
    check("Resposta em portugues", has_pt, f"resposta: {r[:60]}")
    check("Sem ingles", not bool(re.search(r'\b(the|is|are|was|were|have|has)\b', r.lower())))
except Exception as e:
    check("Resposta em portugues", False, str(e))

# 3.2 Formato consistente
try:
    rag3 = SimpleRAG()
    rag3.add(["Teste de formato de saida."])
    r = respond("Teste", rag=rag3)
    check("Formato: tem answer", "answer" in r and isinstance(r["answer"], str))
    check("Formato: tem task_type", "task_type" in r and isinstance(r["task_type"], str))
    check("Formato: tem rag_used", "rag_used" in r and isinstance(r["rag_used"], bool))
    check("Formato: tem issues", "issues" in r and isinstance(r["issues"], list))
    check("Formato: tem time", "time" in r and isinstance(r["time"], float))
except Exception as e:
    check("Formato consistente", False, str(e))

# 3.3 Constitutional check
try:
    issues_clean = const_check("A capital e Brasilia.", "Qual a capital?")
    check("Constitutional: resposta limpa", len(issues_clean) == 0)
    
    issues_uncertain = const_check("Nao sei, talvez seja Paris.", "Qual a capital?")
    check("Constitutional: detecta incerteza", "incerteza" in issues_uncertain)
    
    issues_short = const_check("X", "Explique detalhadamente o que e IA e como ela funciona")
    check("Constitutional: detecta resposta curta", "resposta_curta" in issues_short)
    
    issues_en = const_check("I am not sure about this.", "O que e IA?")
    check("Constitutional: detecta ingles", "ingles" in issues_en)
except Exception as e:
    check("Constitutional check", False, str(e))

# 3.4 Perguntas conhecidas
known_qa = [
    ("Qual a capital do Brasil?", ["brasilia", "brasil"]),
    ("O que e Python?", ["python", "linguagem", "programacao"]),
    ("Quem escreveu Dom Quixote?", ["cervantes", "miguel"]),
    ("Quanto e 2+2?", ["4", "quatro"]),
    ("O que e o sol?", ["estrela", "sol", "luz"]),
]

for question, expected_words in known_qa:
    try:
        r = respond(question, rag=None, use_rag=False)
        has_expected = any(w in r["answer"].lower() for w in expected_words)
        check(f"QA: '{question[:25]}'", has_expected, f"expected {expected_words}, got: {r['answer'][:60]}")
    except Exception as e:
        check(f"QA: '{question[:25]}'", False, str(e))

# 3.5 Nao-alucinacao (resposta baseada em contexto)
try:
    rag4 = SimpleRAG(); rag4.add(["O gato chama Felix e tem 3 anos.", "A casa tem jardim e piscina."])
    r = respond("Qual o nome do gato?", rag=rag4)
    check("Nao-alucinacao: usa contexto", "felix" in r["answer"].lower(), f"got: {r['answer'][:50]}")
    r2 = respond("Qual a cor do carro?", rag=rag4)
    check("Nao-alucinacao: nao inventa", "carro" not in r2["answer"].lower() or "nao" in r2["answer"].lower() or "informacao" in r2["answer"].lower(), f"inventou: {r2['answer'][:50]}")
except Exception as e:
    check("Nao-alucinacao", False, str(e))

# 3.6 Temperatura adaptativa
try:
    r_criativo = respond("Crie uma historia curta", rag=None, use_rag=False)
    r_factual = respond("O que e o Brasil?", rag=None, use_rag=False)
    check("Temp adaptativo: criativo", r_criativo["task_type"] == "criativo")
    check("Temp adaptativo: factual", r_factual["task_type"] == "factual")
except Exception as e:
    check("Temp adaptativo", False, str(e))

p3p, p3f = results["passed"], results["failed"]
print(f"\n  Qualidade: {p3p-p2p}P/{p3f-p2f}F")

# ═══════════════════════════════════════════════════════════
# RESUMO
# ═══════════════════════════════════════════════════════════
total = results["passed"] + results["failed"]
pct = results["passed"] / total * 100 if total else 0
print("\n" + "="*60)
print(f"RESUMO FINAL: {results['passed']}/{total} passaram ({pct:.0f}%)")
print(f"  Parte 1 (Rotador):     {p1p}P/{p1f}F")
print(f"  Parte 2 (Otimizacao): {p2p-p1p}P/{p2f-p1f}F")
print(f"  Parte 3 (Qualidade):   {p3p-p2p}P/{p3f-p2f}F")
if results["errors"]:
    print(f"\n  Erros ({len(results['errors'])}):")
    for e in results["errors"]:
        print(f"    {e}")
print("="*60)
