# 🏗️ Relatório de Análise Arquitetural — Atena Evolução

**Data:** 18/06/2026  
**Analista:** Arquiteto de Software Sênior (OWL)  
**Versão do Projeto:** 1.0.0  
**Escopo:** Análise completa de padrões, extensibilidade, testes, performance, segurança e documentação.

---

## 📊 Visão Geral do Projeto

O **Atena Evolução** é um sistema de IA cognitiva local-first que integra múltiplos módulos: orquestração de LLMs, sistema de memória estratificada, RAG avançado, geração de imagens multi-provider, segurança em camadas e interface web. O projeto é **single-user**, roda **100% local** (CPU-only, i5-1235U / 15.7GB RAM), e usa Ollama como backend principal.

### Estrutura de Arquivos Analisada

| Módulo | Arquivos | Linhas (aprox.) |
|--------|----------|-----------------|
| `core/` | orchestrator, atena_bridge, security_guard, ai_broker_v3, atena_evolution_core, atena_api, atena_behavior, hermes_ollama_adapter, embedding_cache | ~3.500 |
| `lib/memory/` | store, retrieval, pipeline, bridge, consolidation, decay | ~750 |
| `apis/` | image_generator, free_apis | ~1.060 |
| `rag/` | rag_engine | ~466 |
| `safety/` | safety_guard | ~178 |
| `inference/` | qwen_inference, inference_optimizer, glm5_optimizations, llm_inference_opt | ~1.200 |
| `web/` | index.html, style.css | ~1.600 |
| `tests/` | 9 arquivos de teste | ~2.500 |
| `tools/` | serve_ui, apply_security_patches, hermes_auto_update | ~350 |

**Total estimado:** ~11.600 linhas de código

---

## 1. 🔍 Padrões de Projeto

### 1.1 — Código Duplicado

#### **[P1] Três implementações de AtenaBridge**

**Problema:** Existem três classes `AtenaBridge` com funcionalidades sobrepostas:
- `core/atena_bridge.py` — ponte principal com Ollama (chat + embed + context + health_check)
- `lib/memory/bridge.py` — ponte simplificada para o sistema de memória (chat + embed + health_check)
- `core/hermes_ollama_adapter.py` — adapter HTTP que traduz OpenAI-format → Ollama-format

As duas primeiras são quase idênticas (mesmo nome de classe, mesma lógica de `_post()`, mesmo `embed()`). A terceira tem propósito diferente mas duplica a lógica de chamada HTTP.

**Solução:** Criar um módulo compartilhado `core/ollama_client.py` com uma classe `OllamaClient` base que implementa `_post()`, `embed()` e `health_check()`. As três bridges existentes herdam ou recebem essa classe via composição. O `AtenaBridge` de `core/` adiciona `ask()` com contexto; o `lib/memory/bridge.py` usa o cliente base diretamente; o `hermes_ollama_adapter.py` usa o cliente para a tradução de formato.

**Esforço:** Médio (refatoração de 3 arquivos, atualização de imports em ~10 arquivos)  
**Prioridade:** P1

---

#### **[P1] Duplicação de constantes Ollama**

**Problema:** `OLLAMA_URL = "http://localhost:11434"` está definido em **7+ arquivos diferentes**:
- `core/atena_bridge.py`
- `core/hermes_ollama_adapter.py`
- `core/embedding_cache.py`
- `core/orchestrator.py` (indireto via import)
- `lib/memory/bridge.py`
- `core/ai_broker_v3.py`
- `inference/qwen_inference.py`
- `core/atena_behavior.py`

**Solução:** Criar `core/config.py` com constantes centralizadas e classe de configuração:
```python
# core/config.py
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "atena-glm5")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")
```

**Esforço:** Baixo  
**Prioridade:** P1

---

#### **[P2] Duplicação de padrões de segurança**

**Problema:** `core/security_guard.py` e `safety/safety_guard.py` têm padrões de regex sobrepostos para detectar conteúdo perigoso (command injection, path traversal, etc.). Os padrões são similares mas não idênticos, e a versão `core/` é muito mais completa (919 linhas) que a `safety/` (178 linhas).

**Solução:** Manter apenas `core/security_guard.py` como implementação canônica. Remover `safety/safety_guard.py` ou transformá-lo em um wrapper fino que re-exporta o guard principal. Unificar os padrões de regex em um módulo `core/security_patterns.py`.

**Esforço:** Médio  
**Prioridade:** P2

---

### 1.2 — Responsabilidade Única (SRP)

#### **[P1] security_guard.py viola SRP massivamente**

**Problema:** `core/security_guard.py` (919 linhas) implementa **7 camadas** de segurança em uma única classe:
1. Input Sanitization
2. Output Validation
3. Rate Limiting
4. Audit Log (SQLite)
5. Model Integrity (SHA-256 de arquivos)
6. Secure Context Cleanup
7. Anomaly Detection

Cada camada tem lógica independente. A classe tem 15+ métodos, estado compartilhado (`_call_timestamps`, `_conn`, `_session_context_size`), e é difícil testar cada camada isoladamente.

**Solução:** Decompor em classes especializadas:
```python
class InputSanitizer: ...
class OutputValidator: ...
class RateLimiter: ...
class AuditLogger: ...
class ModelIntegrityChecker: ...
class AnomalyDetector: ...

class SecurityGuard:  # Fachada que orquestra os acima
    def __init__(self):
        self.sanitizer = InputSanitizer()
        self.validator = OutputValidator()
        self.rate_limiter = RateLimiter()
        self.audit = AuditLogger()
        self.integrity = ModelIntegrityChecker()
        self.anomaly = AnomalyDetector()
```

**Esforço:** Alto (refatoração de 919 linhas, atualização de todos os testes)  
**Prioridade:** P1

---

#### **[P2] AtenaEvolutionCore com TODOs não implementados**

**Problema:** `core/atena_evolution_core.py` tem 4 métodos marcados com `# TODO` que são stubs:
- `_execute_direct()` — retorna string formatada, não chama LLM
- `_execute_with_rag()` — retorna string formatada, não chama RAG
- `_execute_with_agent()` — retorna string formatada, não delega
- `_safety_check()` — retorna input sem verificar

Isso significa que o "núcleo unificado" não é funcional — o `ai_broker_v3.py` implementa o pipeline real de forma independente.

**Solução:** Decidir se `AtenaEvolutionCore` é o orquestrador principal ou um stub. Se for o principal, implementar os TODOs delegando aos módulos existentes. Se for um stub, marcar claramente como `@deprecated` e direcionar para `AtenaAIBroker`.

**Esforço:** Alto (requer decisão arquitetural)  
**Prioridade:** P2

---

#### **[P2] image_generator.py mistura 3 responsabilidades**

**Problema:** `apis/image_generator.py` (837 linhas) contém:
1. Implementações de providers (OpenAI, Gemini, ComfyUI, Placeholder)
2. Cache SQLite
3. Classe `ImageGenerator` (orquestração)
4. Servidor HTTP REST (`ImageAPIHandler`)
5. CLI (`cli_main()`)
6. Testes (`run_tests()`)

**Solução:** Separar em:
- `apis/image_generator.py` — classe `ImageGenerator` + providers
- `apis/image_cache.py` — cache SQLite
- `apis/image_api.py` — servidor REST
- `apis/image_cli.py` — CLI
- `tests/test_image_generator.py` — testes

**Esforço:** Médio  
**Prioridade:** P2

---

### 1.3 — Acoplamento

#### **[P1] Acoplamento circular potencial entre core/ e lib/memory/**

**Problema:** `lib/memory/pipeline.py` importa `AtenaBridge` de `lib/memory/bridge.py`, que é uma duplicata de `core/atena_bridge.py`. Se o sistema de memória precisar de funcionalidades do `core/atena_bridge.py` (como `keep_context`), há divergência.

**Solução:** `lib/memory/bridge.py` deve importar de `core/atena_bridge.py` ou, melhor, ambas devem usar o `OllamaClient` compartilhado (problema 1.1).

**Esforço:** Baixo (após resolver 1.1)  
**Prioridade:** P1

---

#### **[P2] UI hardcoded para endpoints específicos**

**Problema:** `web/index.html` (1595 linhas) tem URLs hardcoded em JavaScript:
- `http://localhost:11434` (Ollama)
- `http://localhost:8000` (API local)
- `http://localhost:8001` (adapter)

Embora use `localStorage` para overrides, a lógica de fallback está espalhada em múltiplas funções (`sendMessage`, `checkOllamaStatus`, `checkApiStatus`).

**Solução:** Criar um módulo `config.js` centralizado com um `APIClient` que gerencia URLs, timeouts e fallbacks.

**Esforço:** Baixo  
**Prioridade:** P2

---

## 2. 🔌 Extensibilidade

### 2.1 — Novos Providers de Imagem

**Problema atual:** Adicionar um novo provider de imagem em `apis/image_generator.py` requer:
1. Adicionar função `_generate_xxx()` no nível do módulo
2. Adicionar entrada em `PROVIDER_NAMES`
3. Adicionar branch em `ImageGenerator.generate_image()`
4. Adicionar verificação em `_is_available()`
5. Adicionar tratamento em `_resolve_provider()`

Isso viola o **Open/Closed Principle** — a classe precisa ser modificada para cada novo provider.

**Solução — Registry Pattern:**
```python
# apis/providers/base.py
class ImageProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str, size: str) -> dict: ...
    
    @abstractmethod
    def is_available(self) -> bool: ...

# apis/providers/openai_provider.py
class OpenAIProvider(ImageProvider):
    def __init__(self, api_key: str): ...
    def generate(self, prompt, size): ...

# apis/image_generator.py
class ImageGenerator:
    def __init__(self):
        self._providers: dict[str, ImageProvider] = {}
    
    def register_provider(self, name: str, provider: ImageProvider):
        self._providers[name] = provider
    
    def generate_image(self, prompt, provider="auto", ...):
        if provider == "auto":
            for name, p in self._providers.items():
                if p.is_available():
                    return p.generate(prompt, size)
        return self._providers[provider].generate(prompt, size)
```

**Esforço:** Médio  
**Prioridade:** P1

---

### 2.2 — Novos Tipos de Memória

**Problema atual:** O sistema de memória tem duas tabelas fixas (episódica e semântica). Adicionar um terceiro tipo (ex: procedural memory para habilidades) requer modificar `store.py`, `retrieval.py` e `pipeline.py`.

**Solução — Plugin-based Memory Tier:**
```python
class MemoryTier(ABC):
    @abstractmethod
    def store(self, content: str, embedding: list[float], **kwargs) -> int: ...
    
    @abstractmethod
    def retrieve(self, query_embedding: list[float], k: int) -> list[ScoredMemory]: ...

class EpisodicTier(MemoryTier): ...
class SemanticTier(MemoryTier): ...

class AtenaMemory:
    def __init__(self):
        self.tiers: list[MemoryTier] = []
    
    def register_tier(self, tier: MemoryTier):
        self.tiers.append(tier)
    
    def recall(self, query, k=5):
        all_results = []
        for tier in self.tiers:
            all_results.extend(tier.retrieve(query, k))
        return rank_and_budget(all_results, k)
```

**Esforço:** Alto  
**Prioridade:** P2

---

### 2.3 — Novas Skills/Actions

**Problema atual:** Não há um sistema de skills/actions. Cada nova capacidade (clima, busca, etc.) é adicionada como função em `free_apis.py` ou como método em `ai_broker_v3.py`. Não há registro dinâmico.

**Solução — Skill Registry:**
```python
class Skill(ABC):
    name: str
    description: str
    
    @abstractmethod
    def can_handle(self, query: str) -> bool: ...
    
    @abstractmethod
    async def execute(self, query: str, context: dict) -> str: ...

class WeatherSkill(Skill):
    name = "weather"
    description = "Obtém clima atual de uma cidade"
    
    def can_handle(self, query: str) -> bool:
        return any(kw in query.lower() for kw in ["clima", "tempo", "temperatura"])
    
    async def execute(self, query, context):
        city = extract_city(query)
        return await self.weather_api.get_weather(city)

class SkillRegistry:
    def __init__(self):
        self._skills: list[Skill] = []
    
    def register(self, skill: Skill):
        self._skills.append(skill)
    
    def find_skill(self, query: str) -> Skill | None:
        for skill in self._skills:
            if skill.can_handle(query):
                return skill
        return None
```

**Esforço:** Alto  
**Prioridade:** P2

---

## 3. 🧪 Testes

### 3.1 — Cobertura Atual

| Módulo | Arquivo de Teste | Testes | Cobertura |
|--------|-----------------|--------|-----------|
| `lib/memory/` | `test_atena_memory.py` | 15 | Boa (decay, retrieval, clustering, pipeline) |
| `core/ai_broker_v3` | `test_ai_broker.py` | 30+ | Boa (mocks, fallback, safety, RAG) |
| `rag/` | `test_comprehensive.py` | 25+ | Média (CRAG, thresholds, chunking) |
| `apis/image_generator` | `run_tests()` inline | 10 | Média (styles, cache, placeholder) |
| `core/orchestrator` | ❌ Não existe | 0 | Zero |
| `core/security_guard` | Inline `__main__` | 7 | Baixa (só sanitize/rate/anomaly) |
| `core/atena_bridge` | ❌ Não existe | 0 | Zero |
| `core/atena_evolution_core` | ❌ Não existe | 0 | Zero |
| `core/atena_behavior` | ❌ Não existe | 0 | Zero |
| `core/atena_api` | ❌ Não existe | 0 | Zero |
| `apis/free_apis` | ❌ Não existe | 0 | Zero |
| `web/index.html` | `test_ui_validacao.py` | ? | Desconhecida |

**Total estimado:** ~87 testes unitários + testes inline

### 3.2 — Problemas de Teste

#### **[P0] Ausência total de testes de integração end-to-end**

**Problema:** Não há testes que validem o fluxo completo: UI → API → Broker → Ollama → Resposta. O `test_pipeline_unificado.py` tenta isso mas requer Ollama real e é mais um script de validação manual do que um teste automatizado.

**Solução:** Criar testes de integração com `pytest` + `pytest-asyncio` + `httpx` (AsyncClient) que:
1. Iniciam o servidor FastAPI em background
2. Fazem requests HTTP reais
3. Validam respostas
4. Usam mocks apenas para Ollama externo

```python
# tests/integration/test_chat_flow.py
@pytest.mark.asyncio
async def test_chat_returns_response():
    async with httpx.AsyncClient(app=create_api(...), base_url="http://test") as client:
        response = await client.post("/api/chat", json={"message": "Olá"})
        assert response.status_code == 200
        assert "response" in response.json()
```

**Esforço:** Alto  
**Prioridade:** P0

---

#### **[P1] Testes de segurança insuficientes**

**Problema:** Os testes de `security_guard.py` (inline no `__main__`) cobrem apenas casos básicos. Faltam testes para:
- Unicode smuggling (caracteres que bypassam regex)
- Multi-step injection (injeção dividida em múltiplas mensagens)
- Output validation com edge cases (respostas vazias, muito longas, com encoding)
- Rate limiting com timestamps manipulados
- SQL injection no audit log
- Path traversal com encoding (%2e%2e, Unicode normalization)

**Solução:** Criar `tests/test_security_comprehensive.py` com casos de teste baseados em OWASP Top 10 para LLMs.

**Esforço:** Médio  
**Prioridade:** P1

---

#### **[P1] Sem testes de performance automatizados**

**Problema:** `test_comprehensive.py` tem 2 benchmarks de performance (chunking, RRF) mas não há:
- Testes de latência de inferência
- Testes de throughput do sistema de memória (1000+ memórias)
- Testes de vazamento de memória
- Testes de carga no servidor HTTP

**Solução:** Adicionar `tests/performance/` com:
```python
# tests/performance/test_memory_scale.py
def test_recall_with_1000_memories():
    mem = AtenaMemory(db_path=":memory:", bridge=FakeBridge())
    for i in range(1000):
        mem.remember(f"Memória de teste número {i} sobre o tópico {i % 10}")
    
    start = time.time()
    result = mem.recall("tópico 5")
    elapsed = time.time() - start
    assert elapsed < 1.0, f"Recall com 1000 memórias levou {elapsed:.2f}s"
```

**Esforço:** Médio  
**Prioridade:** P1

---

#### **[P2] Testes de memória usam FakeBridge frágil**

**Problema:** O `FakeBridge` em `test_atena_memory.py` gera embeddings via hash MD5 → vetor 16-dim. Isso é determinístico mas não representa a semântica real. Testes de ranking podem passar com FakeBridge mas falhar com embeddings reais.

**Solução:** Adicionar testes de propriedade (property-based testing) com `hypothesis` que validam invariantes independentes do modelo de embedding:
```python
from hypothesis import given, strategies as st

@given(st.lists(st.text(min_size=10, max_size=200), min_size=5, max_size=20))
def test_recall_returns_results_for_similar_topics(memories):
    # Se todas as memórias compartilham uma entidade, recall deve retornar resultados
    ...
```

**Esforço:** Médio  
**Prioridade:** P2

---

## 4. ⚡ Performance

### 4.1 — Gargalos Identificados

#### **[P0] SQLite sem WAL mode**

**Problema:** `lib/memory/store.py` e `core/embedding_cache.py` usam SQLite sem `PRAGMA journal_mode=WAL`. Em cenários de leitura concorrente (UI consultando enquanto manutenção escreve), isso causa bloqueios.

**Solução:**
```python
@contextmanager
def _conn(self):
    conn = sqlite3.connect(self.db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")  # Mais rápido, ainda seguro
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()
```

**Esforço:** Baixo (3 linhas)  
**Prioridade:** P0

---

#### **[P1] Embedding cache sem limite de tamanho**

**Problema:** `core/embedding_cache.py` cresce indefinidamente. Com embeddings de 768 dimensões (nomic-embed-text) e ~36 bytes por float, cada embedding ocupa ~27KB. 10.000 embeddings = ~270MB.

**Solução:** Adicionar LRU eviction:
```python
class EmbeddingCache:
    def __init__(self, db_path="embeddings_cache.db", max_size=5000):
        self.max_size = max_size
    
    def _evict_if_needed(self):
        with sqlite3.connect(self.db_path) as conn:
            count = conn.execute("SELECT COUNT(*) FROM embeddings").fetchone()[0]
            if count > self.max_size:
                # Remove oldest 20%
                conn.execute("""
                    DELETE FROM embeddings WHERE text_hash IN (
                        SELECT text_hash FROM embeddings 
                        ORDER BY created_at ASC 
                        LIMIT ?
                    )
                """, (count - self.max_size,))
```

**Esforço:** Baixo  
**Prioridade:** P1

---

#### **[P1] Busca vetorial O(n) sem índice**

**Problema:** `lib/memory/retrieval.py` calcula cosine similarity contra **todas** as memórias ativas. Com 1000 memórias, são 1000 multiplicações de vetores 768-dim. Em CPU, isso é ~50-100ms. Com 10.000 memórias, ~500ms-1s.

**Solução para CPU-only:**
1. Usar `sqlite-vec` (extensão SQLite para busca vetorial aproximada)
2. Ou implementar HNSW simples com `hnswlib` (funciona em CPU)
3. Ou usar FAISS com índice `IndexFlatIP` (otimizado para CPU)

```python
# Com hnswlib (leve, CPU-only)
import hnswlib

class VectorIndex:
    def __init__(self, dim=768, max_elements=10000):
        self.index = hnswlib.Index(space='cosine', dim=dim)
        self.index.init_index(max_elements=max_elements, ef_construction=200, M=16)
        self.index.set_ef(50)
    
    def add(self, id: int, vector: list[float]):
        self.index.add_items([vector], [id])
    
    def search(self, query: list[float], k: int) -> list[tuple[int, float]]:
        labels, distances = self.index.knn_query([query], k=k)
        return list(zip(labels[0], distances[0]))
```

**Esforço:** Médio  
**Prioridade:** P1

---

#### **[P2] ComfyUI polling bloqueante**

**Problema:** `apis/image_generator.py` usa polling síncrono com `time.sleep(1)` em loop de 120 iterações para ComfyUI. Isso bloqueia a thread por até 2 minutos.

**Solução:** Usar `aiohttp` para polling assíncrono, ou melhor, usar WebSocket do ComfyUI para receber notificação de conclusão.

**Esforço:** Médio  
**Prioridade:** P2

---

#### **[P2] UI faz health check a cada 5s sem backoff**

**Problema:** `web/index.html` chama `checkOllamaStatus()` e `checkApiStatus()` em intervalo fixo. Se Ollama está offline, isso gera requisições HTTP falhas a cada 5s.

**Solução:** Implementar exponential backoff:
```javascript
let healthCheckInterval = 5000;
let consecutiveFailures = 0;

async function checkOllamaStatus() {
    try {
        // ... check logic
        consecutiveFailures = 0;
        healthCheckInterval = 5000;
    } catch (e) {
        consecutiveFailures++;
        healthCheckInterval = Math.min(5000 * Math.pow(2, consecutiveFailures), 60000);
    }
    setTimeout(checkOllamaStatus, healthCheckInterval);
}
```

**Esforço:** Baixo  
**Prioridade:** P2

---

## 5. 🔒 Segurança

### 5.1 — Vulnerabilidades Identificadas

#### **[P0] API keys em localStorage (XSS)**

**Problema:** `web/index.html` salva API keys (Gemini, OpenAI, Anthropic) em `localStorage`:
```javascript
localStorage.setItem('atena_geminiKey', value);
localStorage.setItem('atena_openaiKey', value);
```
Qualquer XSS na página (via CDN do Font Awesome, ou inline script) pode exfiltrar essas chaves.

**Solução:**
1. **Nunca** armazene API keys no frontend. O backend (`atena_api.py`) deve gerenciar chaves via variáveis de ambiente ou cofre seguro.
2. Se o frontend precisa enviar chaves, use headers HTTP-only cookies.
3. Remover todos os inputs de API key da UI e mover para configuração do servidor.

**Esforço:** Alto (requer reestruturação do fluxo de configuração)  
**Prioridade:** P0

---

#### **[P0] Sem autenticação na API local**

**Problema:** `core/atena_api.py` (FastAPI) e `apis/image_generator.py` (HTTPServer) não têm autenticação. Qualquer processo na máquina (ou na rede, se acessível) pode:
- Enviar prompts arbitrários ao Ollama
- Gerar imagens ilimitadas (consumindo APIs pagas)
- Acessar o audit log com dados sensíveis

**Solução:**
```python
# core/atena_api.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials.credentials != os.getenv("ATENA_API_TOKEN", "change-me"):
        raise HTTPException(status_code=403, detail="Invalid token")
    return credentials.credentials

@app.post("/api/chat", dependencies=[Depends(verify_token)])
async def chat(request: ChatRequest): ...
```

Para o `image_generator.py`, adicionar token simples no header.

**Esforço:** Médio  
**Prioridade:** P0

---

#### **[P1] CORS permissivo**

**Problema:** `core/atena_api.py` usa `allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"]` mas `apis/image_generator.py` e `core/security_guard.py` usam `Access-Control-Allow-Origin: *` sem restrição.

**Solução:** Restringir CORS ao origin real da UI:
```python
# apis/image_generator.py
self.send_header("Access-Control-Allow-Origin", "http://127.0.0.1:8080")
```

**Esforço:** Baixo  
**Prioridade:** P1

---

#### **[P1] Sem sanitização de output no image_generator**

**Problema:** `apis/image_generator.py` aceita prompts arbitrários e os envia para APIs externas (OpenAI, Gemini) sem sanitização. Um prompt malicioso pode:
- Tentar injeção de instruções no modelo de imagem
- Exfiltrar dados via prompt injection

**Solução:** Aplicar `SecurityGuard.sanitize_input()` antes de enviar prompts para providers externos.

**Esforço:** Baixo  
**Prioridade:** P1

---

#### **[P1] CSP permite 'unsafe-inline'**

**Problema:** O `Content-Security-Policy` no `index.html` inclui `'unsafe-inline'` para scripts e styles. Isso anula a proteção contra XSS que o CSP deveria fornecer.

**Solução:**
1. Mover todos os inline scripts para arquivos `.js` separados
2. Mover todos os inline styles para `style.css`
3. Remover `'unsafe-inline'` do CSP
4. Se necessário, usar nonce-based CSP

**Esforço:** Alto (1595 linhas de HTML com JS inline)  
**Prioridade:** P1

---

#### **[P2] Rate limiting apenas em memória**

**Problema:** `core/security_guard.py` mantém `_call_timestamps` em memória. Se o processo reinicia, o rate limit é perdido. Além disso, não há rate limiting na API HTTP.

**Solução:** Implementar rate limiting no nível do servidor HTTP (middleware FastAPI) com armazenamento em Redis ou SQLite.

**Esforço:** Médio  
**Prioridade:** P2

---

#### **[P2] Audit log sem rotação**

**Problema:** `security_audit.db` cresce indefinidamente. O método `clear_old_context()` remove registros antigos, mas é chamado manualmente e também executa `VACUUM` (operação cara em SQLite).

**Solução:** Adicionar rotação automática baseada em tamanho:
```python
def _rotate_if_needed(self):
    size_mb = os.path.getsize(self.db_path) / (1024 * 1024)
    if size_mb > 100:  # 100MB
        cutoff = time.time() - (30 * 86400)  # 30 dias
        self._conn.execute("DELETE FROM audit_log WHERE timestamp < ?", (cutoff,))
        self._conn.execute("VACUUM")
```

**Esforço:** Baixo  
**Prioridade:** P2

---

## 6. 📚 Documentação

### 6.1 — Estado Atual

| Item | Status |
|------|--------|
| README.md | ⚠️ Desatualizado (não menciona lib/memory, image_generator, etc.) |
| Docstrings em módulos | ✅ Boa (quase todos os módulos têm docstring de cabeçalho) |
| Docstrings em funções | ⚠️ Parcial (muitas funções públicas sem docstring) |
| Type hints | ⚠️ Parcial (alguns módulos usam, outros não) |
| Architecture Decision Records | ❌ Não existe |
| API docs (Swagger) | ✅ FastAPI gera automaticamente em /docs |
| Guia de contribuição | ❌ Não existe |
| Changelog | ❌ Não existe |

### 6.2 — Melhorias Propostas

#### **[P1] README.md desatualizado**

**Problema:** O `README.md` lista uma estrutura de diretórios que não corresponde à realidade (faltam `lib/memory/`, `apis/image_generator.py`, `inference/`, `tools/`). A seção de instalação lista dependências que não são mais necessárias (fastapi, uvicorn, httpx, sentence-transformers, chromadb) — o sistema de memória roda com zero dependências externas.

**Solução:** Reescrever o README com:
1. Estrutura real do projeto
2. Arquitetura de módulos (diagrama ASCII)
3. Guia de instalação por módulo
4. Exemplos de uso para cada módulo
5. Roadmap

**Esforço:** Médio  
**Prioridade:** P1

---

#### **[P1] Faltam docstrings em funções públicas**

**Problema:** Muitas funções públicas não têm docstring com Args/Returns. Exemplos:
- `core/embedding_cache.py`: `get_or_compute()`, `stats()` — sem docstring
- `apis/free_apis.py`: métodos `async` sem documentação de parâmetros
- `core/atena_evolution_core.py`: `process()`, `_route_task()` — sem docstring

**Solução:** Adicionar docstrings no formato Google ou NumPy para todas as funções públicas.

**Esforço:** Médio  
**Prioridade:** P1

---

#### **[P2] Sem Architecture Decision Records (ADRs)**

**Problema:** Decisões arquiteturais importantes (por que SQLite e não ChromaDB? Por que Ebbinghaus decay? Por que separação online/offline?) estão apenas no `lib/memory/README.md` mas não são rastreáveis.

**Solução:** Criar `docs/adr/` com ADRs no formato MADR:
```
docs/adr/
  001-sqlite-for-memory.md
  002-ebbinghaus-decay.md
  003-online-offline-separation.md
  004-ollama-as-primary-backend.md
```

**Esforço:** Baixo  
**Prioridade:** P2

---

#### **[P2] Sem guia de contribuição**

**Problema:** Não há `CONTRIBUTING.md` ou instruções para novos desenvolvedores. O projeto tem convenções inconsistentes (alguns arquivos usam `snake_case`, outros `camelCase`; alguns usam type hints, outros não).

**Solução:** Criar `CONTRIBUTING.md` com:
1. Convenções de código (PEP 8, type hints obrigatórios)
2. Como adicionar novos providers de imagem
3. Como adicionar novos tipos de memória
4. Como executar testes
5. Template para PRs

**Esforço:** Baixo  
**Prioridade:** P2

---

## 7. 📋 Resumo de Melhorias por Prioridade

### P0 — Crítico (4 itens)

| # | Melhoria | Esforço | Módulo |
|---|----------|---------|--------|
| 1 | Adicionar autenticação na API local | Médio | `core/atena_api.py`, `apis/image_generator.py` |
| 2 | Remover API keys do localStorage (XSS) | Alto | `web/index.html`, `core/atena_api.py` |
| 3 | Habilitar WAL mode no SQLite | Baixo | `lib/memory/store.py`, `core/embedding_cache.py` |
| 4 | Criar testes de integração end-to-end | Alto | `tests/integration/` |

### P1 — Importante (12 itens)

| # | Melhoria | Esforço | Módulo |
|---|----------|---------|--------|
| 5 | Unificar AtenaBridge duplicados | Médio | `core/atena_bridge.py`, `lib/memory/bridge.py` |
| 6 | Centralizar constantes Ollama | Baixo | `core/config.py` (novo) |
| 7 | Decompor SecurityGuard (SRP) | Alto | `core/security_guard.py` |
| 8 | Implementar Registry Pattern para providers | Médio | `apis/image_generator.py` |
| 9 | Adicionar limite de tamanho no embedding cache | Baixo | `core/embedding_cache.py` |
| 10 | Implementar índice vetorial (hnswlib/FAISS) | Médio | `lib/memory/retrieval.py` |
| 11 | Adicionar testes de segurança abrangentes | Médio | `tests/test_security_comprehensive.py` |
| 12 | Adicionar testes de performance automatizados | Médio | `tests/performance/` |
| 13 | Restringir CORS | Baixo | `apis/image_generator.py` |
| 14 | Sanitizar prompts no image_generator | Baixo | `apis/image_generator.py` |
| 15 | Reescrever README.md | Médio | `README.md` |
| 16 | Adicionar docstrings em funções públicas | Médio | Múltiplos |

### P2 — Desejável (10 itens)

| # | Melhoria | Esforço | Módulo |
|---|----------|---------|--------|
| 17 | Unificar safety_guard duplicado | Médio | `safety/safety_guard.py` |
| 18 | Decidir futuro do AtenaEvolutionCore | Alto | `core/atena_evolution_core.py` |
| 19 | Separar image_generator em módulos | Médio | `apis/image_generator.py` |
| 20 | Criar config.js centralizado para UI | Baixo | `web/config.js` (novo) |
| 21 | Implementar Plugin-based Memory Tier | Alto | `lib/memory/` |
| 22 | Implementar Skill Registry | Alto | `core/skills/` (novo) |
| 23 | Adicionar exponential backoff no health check | Baixo | `web/index.html` |
| 24 | Implementar rotação de audit log | Baixo | `core/security_guard.py` |
| 25 | Criar ADRs | Baixo | `docs/adr/` |
| 26 | Criar CONTRIBUTING.md | Baixo | `CONTRIBUTING.md` |

---

## 8. 🎯 Recomendações de Curto Prazo (Próximas 2 Semanas)

1. **Imediato:** Habilitar WAL mode no SQLite (30 minutos)
2. **Imediato:** Centralizar constantes Ollama em `core/config.py` (1 hora)
3. **Dia 1-2:** Adicionar autenticação na API local (4 horas)
4. **Dia 2-3:** Remover API keys do localStorage (4 horas)
5. **Dia 3-5:** Unificar AtenaBridge + criar `core/ollama_client.py` (1 dia)
6. **Dia 5-7:** Adicionar testes de segurança abrangentes (1 dia)
7. **Dia 7-10:** Reescrever README.md + adicionar docstrings (1 dia)
8. **Dia 10-14:** Implementar Registry Pattern para providers de imagem (2 dias)

---

## 9. 🏆 Pontos Fortes do Projeto

Apesar dos problemas identificados, o projeto tem **qualidades notáveis**:

1. **Arquitetura de memória bem fundamentada** — A separação episódica/semântica com decay de Ebbinghaus é baseada em literatura acadêmica real (A-MEM, MemoryBank, LightMem). O `lib/memory/README.md` é excelente.

2. **Testes de memória com FakeBridge** — A abordagem de usar embeddings determinísticos para testar a lógica sem Ollama é inteligente e eficaz.

3. **Segurança em camadas** — O `security_guard.py` é abrangente (7 camadas) e bem documentado. Os testes inline são práticos.

4. **Zero dependências externas no sistema de memória** — `lib/memory/` roda com apenas `sqlite3`, `json`, `math`, `time`, `re` da stdlib.

5. **UI polida** — O `index.html` é uma interface moderna com streaming, temas, modals e toast notifications.

6. **Pipeline de inferência com fallback** — O `ai_broker_v3.py` implementa 5 camadas de fallback (Qwen → OpenRouter → Gemini → Ollama → Llama.cpp) com circuit breaker.

---

## 10. 📊 Métricas de Qualidade

| Métrica | Valor | Nota |
|---------|-------|------|
| Linhas de código | ~11.600 | Médio |
| Arquivos Python | ~25 | Médio |
| Cobertura de testes | ~40% | Baixa |
| Duplicação de código | ~8% | Média |
| Complexidade ciclomática média | ~5 | Boa |
| Dependências externas diretas | 3 (requests, fastapi, uvicorn) | Baixa |
| Segurança (OWASP) | 4/10 | Baixa |
| Documentação | 5/10 | Média |
| Extensibilidade | 4/10 | Baixa |
| Manutenibilidade | 5/10 | Média |

---

**Fim do relatório.**  
*Para dúvidas ou discussões sobre qualquer item, consulte o arquiteto.*
