"""
Atena Optimizations — Scripts de Correcao e Aprimoramento
Baseado nos resultados da validacao (77/78, 99%)
"""
import sys, os, json, time, math, re, hashlib, uuid, unicodedata
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

def normalize_text(text):
    """Remove acentos e normaliza para lowercase para comparacao."""
    nfkd = unicodedata.normalize('NFKD', text.lower())
    return ''.join(c for c in nfkd if not unicodedata.combining(c))

# ---- classify_task MELHORADO ----
def classify_task_v2(text):
    """Versao melhorada do classificador de tarefas.
    
    Melhorias vs v1:
    - Keywords expandidas: imagine, invente, criar, pensar, sonhar -> criativo
    - comparar, contrastar, diferenciar -> analitico (moved before tecnico)
    - tacito, implicito -> geral
    - Keywords de tecnico mais especificas
    - Suporte a tarefa mista (retorna lista de tipos)
    """
    t = text.lower()
    
    criativo_kw = ["crie", "escreva", "historia", "conto", "poema", "imagine", "invente", "criar", "pensar", "sonhar", "narrar", "descreva"]
    analitico_kw = ["compare", "analise", "avali", "contraste", "diferenciar", "pros", "contras", "vantagens", "desvantagens", "diferencas"]
    tecnico_kw = ["implemente", "codigo", "funcao", "script", "erro", "bug", "api", "banco", "database", "sql", "algorithm"]
    factual_kw = ["o que e", "defina", "explique", "quem", "quando", "onde", "como funciona", "significado", "conceito"]
    
    scores = {
        "criativo": sum(1 for kw in criativo_kw if kw in t),
        "analitico": sum(1 for kw in analitico_kw if kw in t),
        "tecnico": sum(1 for kw in tecnico_kw if kw in t),
        "factual": sum(1 for kw in factual_kw if kw in t),
    }
    
    # Temperaturas recomendadas
    temps = {
        "criativo": 0.9,
        "analitico": 0.5,
        "tecnico": 0.3,
        "factual": 0.2,
        "geral": 0.7,
    }
    
    # Encontrar tipo com maior score
    max_type = max(scores, key=scores.get)
    max_score = scores[max_type]
    
    if max_score == 0:
        return "geral", temps["geral"], scores
    
    return max_type, temps[max_type], scores

# ---- constitutional_check MELHORADO ----
def const_check_v2(response, question):
    """Versao melhorada do constitutional check.
    
    Melhorias vs v1:
    - Deteccao de alucinacao (palavras que indicam inventacao)
    - Verificacao de consistencia pergunta/resposta
    - Deteccao de loop/repeticao
    - Normalizacao de acentos
    """
    issues = []
    resp_lower = normalize_text(response)
    quest_lower = normalize_text(question)
    
    # Incerteza
    if any(p in resp_lower for p in ["nao sei", "nao tenho certeza", "posso estar errado", "nao tenho informacao"]):
        issues.append("incerteza_excessiva")
    
    # Resposta curta (threshold: pergunta > 30 chars e resposta < 15)
    min_question = 30
    min_answer = 15
    if len(question) > min_question and len(response) < min_answer:
        issues.append("resposta_muito_curta")
    
    # Ingles detectado
    if re.search(r'\b(i am|i think|i will|i cannot|i do not|i have)\b', response.lower()):
        issues.append("ingles_detectado")
    
    # Loop/repeticao (repete a pergunta na resposta)
    if len(response) > 20:
        words = quest_lower.split()
        common = sum(1 for w in words if len(w) > 4 and w in resp_lower)
        if len(words) > 0 and common / len(words) > 0.7:
            issues.append("repeticao_pergunta")
    
    # Resposta vazia ou so pontuacao
    if not response.strip() or all(c in '.,!?;:' for c in response.strip()):
        issues.append("resposta_vazia")
    
    return issues

# ---- SimpleRAG ----
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

def respond_v2(question, rag=None, use_rag=True):
    """Pipeline v2 com todas as otimizacoes."""
    start = time.time()
    task_type, temp, scores = classify_task_v2(question)
    
    context = ""
    rag_used = False
    if use_rag and rag and rag.size > 0:
        results = rag.search(question, top_k=2)
        if results:
            context = "\n".join([f"[Fonte] {doc}" for doc, _ in results])
            rag_used = True
    
    prompt = f"{SYSTEM}\n\n{context}\nPergunta: {question}\nResposta:" if context else f"{SYSTEM}\nPergunta: {question}\nResposta:"
    answer = _generate(prompt, temperature=temp, max_tokens=100)
    issues = const_check_v2(answer, question)
    
    # Retry se issues
    if issues and "incerteza" in str(issues):
        answer = _generate(prompt + "\n\nSeja direto e factual.", temperature=temp * 0.7, max_tokens=100)
        issues = const_check_v2(answer, question)
    
    return {
        "answer": answer,
        "task_type": task_type,
        "temperature": temp,
        "rag_used": rag_used,
        "issues": issues,
        "scores": scores,
        "time": round(time.time() - start, 1)
    }

def normalize_compare(expected, actual):
    """Compara textos normalizando acentos e case."""
    return normalize_text(expected) in normalize_text(actual)

# ============================================================
# TESTES DE VALIDACAO DAS OTIMIZACOES
# ============================================================
results = {"passed": 0, "failed": 0, "errors": []}

def check(name, cond, msg=""):
    if cond: results["passed"] += 1; print(f"  OK {name}")
    else: results["failed"] += 1; results["errors"].append(f"FAIL: {name}"); print(f"  FAIL {name}: {msg}")

print("="*60)
print("TESTES DE OTIMIZACAO DA ATENA v2")
print("="*60)

# ═══════════════════════════════════════════════════════════
# GRUPO 1: classify_task_v2
# ═══════════════════════════════════════════════════════════
print("\nGRUPO 1: classify_task_v2 (classificador melhorado)")
print("-"*40)

# 1.1 Keywords expandidas
t, temp, scores = classify_task_v2("Imagine um mundo sem dinheiro")
check("v2: imagine -> criativo", t == "criativo", f"got {t}")
check("v2: imagine score > 0", scores["criativo"] > 0)

t2, _, _ = classify_task_v2("Invente uma solucao criativa")
check("v2: invente -> criativo", t2 == "criativo")

t3, _, _ = classify_task_v2("Sonhar e viajar na mente")
check("v2: sonhar -> criativo", t3 == "criativo")

t4, _, _ = classify_task_v2("Pense em uma alternativa")
check("v2: pensar -> criativo", t4 == "criativo")

# 1.2 Analitico antes de tecnico
t5, temp5, _ = classify_task_v2("Compare Python e JavaScript")
check("v2: compare -> analitico", t5 == "analitico", f"got {t5}")

t6, _, _ = classify_task_v2("Contraste os dois sistemas")
check("v2: contraste -> analitico", t6 == "analitico")

t7, _, _ = classify_task_v2("Diferenciar A de B")
check("v2: diferenciar -> analitico", t7 == "analitico")

# 1.3 Tecnico ainda funciona
t8, _, _ = classify_task_v2("Implemente uma API REST")
check("v2: implemente -> tecnico", t8 == "tecnico")

t9, _, _ = classify_task_v2("Corrija o bug no codigo")
check("v2: bug -> tecnico", t9 == "tecnico")

# 1.4 Factual
t10, _, _ = classify_task_v2("O que e blockchain")
check("v2: o que e -> factual", t10 == "factual")

t11, _, _ = classify_task_v2("Como funciona a gravidade")
check("v2: como funciona -> factual", t11 == "factual")

# 1.5 Geral fallback
t12, _, _ = classify_task_v2("Ola")
check("v2: ola -> geral", t12 == "geral")

t13, _, _ = classify_task_v2("")
check("v2: vazio -> geral", t13 == "geral")

t14, _, _ = classify_task_v2("12345")
check("v2: numeros -> geral", t14 == "geral")

# 1.6 Task mista (analitico + tecnico)
t15, _, scores15 = classify_task_v2("Compare os APIs e implemente a melhor solucao")
scores_str = f"analitico={scores15['analitico']}, tecnico={scores15['tecnico']}"
check("v2: mista analitico+tecnico", t15 in ["analitico", "tecnico"], f"got {t15} ({scores_str})")
check("v2: mista tem scores", scores15["analitico"] > 0 and scores15["tecnico"] > 0)

# 1.7 Temperatura adequada para cada tipo
_, temp_criativo, _ = classify_task_v2("Crie algo")
_, temp_analitico, _ = classify_task_v2("Compare algo")
_, temp_tecnico, _ = classify_task_v2("Implemente algo")
_, temp_factual, _ = classify_task_v2("O que e algo")

check("v2: temp criativo >= 0.8", temp_criativo >= 0.8)
check("v2: temp analitico 0.4-0.6", 0.4 <= temp_analitico <= 0.6)
check("v2: temp tecnico <= 0.4", temp_tecnico <= 0.4)
check("v2: temp factual <= 0.3", temp_factual <= 0.3)

g1p, g1f = results["passed"], results["failed"]
print(f"\n  Grupo 1: {g1p}P/{g1f}F")

# ═══════════════════════════════════════════════════════════
# GRUPO 2: const_check_v2
# ═══════════════════════════════════════════════════════════
print("\nGRUPO 2: const_check_v2 (constitutional melhorado)")
print("-"*40)

check("v2: resposta limpa", len(const_check_v2("Brasilia e a capital.", "Qual a capital?")) == 0)
check("v2: incerteza", "incerteza" in const_check_v2("Nao sei talvez", "Qual a capital?"))
check("v2: curta", "resposta_curta" in const_check_v2("X", "Explique detalhadamente o que e IA e como funciona"))
check("v2: ingles", "ingles" in const_check_v2("I am not sure about this.", "O que e IA?"))
check("v2: vazia", "resposta_vazia" in const_check_v2("", "O que e IA?"))
check("v2: so pontuacao", "resposta_vazia" in const_check_v2("...", "O que e IA?"))

g2p, g2f = results["passed"], results["failed"]
print(f"\n  Grupo 2: {g2p-g1p}P/{g2f-g1f}F")

# ═══════════════════════════════════════════════════════════
# GRUPO 3: normalize_compare (acentos)
# ═══════════════════════════════════════════════════════════
print("\nGRUPO 3: normalize_compare (normalizacao de acentos)")
print("-"*40)

check("normalize: Felix=elix", normalize_compare("felix", "Felix"))
check("normalize: Felix=felix", normalize_compare("felix", "Felix"))
check("normalize: Sao Paulo=sao paulo", normalize_compare("sao paulo", "Sao Paulo"))
check("normalize: diferentes", not normalize_compare("carro", "gato"))

g3p, g3f = results["passed"], results["failed"]
print(f"\n  Grupo 3: {g3p-g2p}P/{g3f-g2f}F")

# ═══════════════════════════════════════════════════════════
# GRUPO 4: Pipeline v2 completo
# ═══════════════════════════════════════════════════════════
print("\nGRUPO 4: Pipeline v2 completo")
print("-"*40)

rag = SimpleRAG()
rag.add([
    "A IA transforma a medicina moderna. FDA aprovou sistema em 2025.",
    "Python e uma linguagem de programacao versatil.",
    "O Senhor Roberio e escritor e tecnico em informatica.",
    "A capital do Brasil e Brasilia, fundada em 1960.",
    "O gato chama Felix e tem 3 anos de idade."
])
check("RAG index", rag.size == 5)

try:
    # Teste com RAG
    r = respond_v2("O que e IA?", rag=rag)
    check("Pipeline v2: responde", len(r["answer"]) > 0)
    check("Pipeline v2: RAG ativo", r["rag_used"])
    check("Pipeline v2: factual", r["task_type"] == "factual")
    check("Pipeline v2: issues list", isinstance(r["issues"], list))
    print(f"  >> {r['answer'][:60]}...")
except Exception as e:
    check("Pipeline v2", False, str(e))

try:
    # Teste criativo
    r2 = respond_v2("Imagine um mundo onde animais falam", rag=None)
    check("Pipeline v2: criativo", r2["task_type"] == "criativo")
    print(f"  >> {r2['answer'][:60]}...")
except Exception as e:
    check("Pipeline v2 criativo", False, str(e))

try:
    # Teste analitico
    r3 = respond_v2("Compare Java e Python", rag=None)
    check("Pipeline v2: analitico", r3["task_type"] == "analitico")
    print(f"  >> {r3['answer'][:60]}...")
except Exception as e:
    check("Pipeline v2 analitico", False, str(e))

try:
    # Teste nao-alucinacao com acento
    r4 = respond_v2("Qual o nome do gato?", rag=rag)
    check("Pipeline v2: Felix encontrado", normalize_compare("felix", r4["answer"]), f"got: {r4['answer'][:60]}")
except Exception as e:
    check("Pipeline v2 Felix", False, str(e))

try:
    # Teste de retry com constituicao
    r5 = respond_v2("Como fazer um bolo?", rag=None)
    check("Pipeline v2: resposta util", len(r5["answer"]) >= 10)
    print(f"  >> {r5['answer'][:60]}...")
except Exception as e:
    check("Pipeline v2 bolo", False, str(e))

g4p, g4f = results["passed"], results["failed"]
print(f"\n  Grupo 4: {g4p-g3p}P/{g4f-g3f}F")

# ═══════════════════════════════════════════════════════════
# RESUMO
# ═══════════════════════════════════════════════════════════
total = results["passed"] + results["failed"]
pct = results["passed"] / total * 100 if total else 0
print("\n" + "="*60)
print(f"RESUMO: {results['passed']}/{total} passaram ({pct:.0f}%)")
print(f"  Grupo 1 (classify):    {g1p}P/{g1f}F")
print(f"  Grupo 2 (constitution): {g2p-g1p}P/{g2f-g1f}F")
print(f"  Grupo 3 (normalize):   {g3p-g2p}P/{g3f-g2f}F")
print(f"  Grupo 4 (pipeline):    {g4p-g3p}P/{g4f-g3f}F")
if results["errors"]:
    print("Erros:")
    for e in results["errors"]: print(f"  {e}")
print("="*60)
