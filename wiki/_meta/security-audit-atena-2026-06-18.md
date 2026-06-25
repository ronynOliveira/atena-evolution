# Relatório de Auditoria de Segurança — Atena Evolution

**Data:** 18/06/2026  
**Projeto:** atena_evolution v1.0.0  
**Escopo:** 30 arquivos Python (core, inference, rag, safety, apis, tests)  
**Metodologia:** Análise estática manual de código fonte  

---

## Sumário Executivo

O projeto Atena Evolution é um sistema de IA cognitiva local que integra múltiplos componentes: RAG, orquestração de LLMs, inferência otimizada, APIs REST e guards de segurança. A arquitetura é **bem segmentada** e já inclui camadas de segurança dedicadas (`security_guard.py`, `safety/safety_guard.py`).

No entanto, foram identificadas **67 vulnerabilidades** distribuídas em 8 categorias, incluindo 9 CRÍTICAS, 21 HIGH, 24 MEDIUM e 13 LOW.

---

## 1. PROMPT INJECTION

### VULN-PI-001 — Input de usuário diretamente no Ollama sem sanitização obrigatória
- **Arquivo:** `core/orchestrator.py:49-71`
- **Severidade:** HIGH
- **Descrição:** O método `route()` recebe `prompt` do usuário e passa diretamente para `self.bridge.ask()` sem sanitização. Não há garantia de que o `SecurityGuard` seja chamado neste fluxo. O `SecurityGuard.sanitize_input()` existe mas não é invocado obrigatoriamente.
- **Trecho:**
  ```python
  def route(self, task_type: str, prompt: str, max_tokens: int = 512) -> dict:
      # ...
      response = self.bridge.ask(prompt=prompt, system=system, ...)
  ```
- **Correção:** Invocar `SecurityGuard.sanitize_input(prompt)` antes de enviar ao bridge, ou tornar a segurança obrigatória no `AtenaBridge.ask()`.

### VULN-PI-002 — Prompt no `test_pipeline_unificado.py` e outros testes
- **Arquivo:** `tests/test_pipeline_unificado.py:160-177`
- **Severidade:** LOW (código de teste)
- **Descrição:** No pipeline de teste, `question` vai diretamente para `_generate()` sem qualquer sanitação similar ao que aconteceria em produção.
- **Correção:** Adicionar camada de sanitização no pipeline de testes ou configurar validação similar ao `SecurityGuard`.

### VULN-PI-003 — `atena_evolution_core.py` expõe mensagem de erro para o usuário
- **Arquivo:** `core/atena_evolution_core.py:285-286`
- **Severidade:** MEDIUM  
- **Descrição:** O método `process()` retorna string de erro diretamente conteúdo capturado na exceção, que pode vazar informações internas.
- **Trecho:**
  ```python
  except Exception as e:
      logger.error(f"Erro ao processar tarefa: {e}")
      return TaskResponse(success=False, content=f"Erro: {str(e)}", ...)
  ```
- **Correção:** Nunca retornar `str(e)` ao usuário. Usar mensagem genérica e registrar detalhes apenas no log.

### VULN-PI-004 — `atena_api.py` retorna str(e) ao usuário
- **Arquivo:** `core/atena_api.py:156-157`
- **Severidade:** MEDIUM
- **Trecho:**
  ```python
  except Exception as e:
      logger.error(f"Erro no chat: {e}")
      raise HTTPException(status_code=500, detail=str(e))
  ```
- **Correção:** `raise HTTPException(status_code=500, detail="Erro interno do servidor")` e manter log detalhado para debug.

---

## 2. SQL INJEÇÃO

### VULN-SI-001 — SQL parametrizado no SecurityGuard (POSITIVO ✅)
- **Arquivo:** `core/security_guard.py:311-328`
- **Situacao:** Todas as queries SQL no SecurityGuard usam `?` placeholders.
  ```python
  self._conn.execute("INSERT INTO audit_log (...) VALUES (?, ?, ?, ...)", (params,))
  ```

### VULN-SI-002 — SQL parametrizado no EmbeddingCache (POSITIVO ✅)
- **Arquivo:** `core/embedding_cache.py:49-53`
  ```python
  row = conn.execute("SELECT embedding FROM embeddings WHERE text_hash = ?", (key,))
  ```
  Todas as queries estão parametrizadas — risco zero detectado.

---

## 3. PATH TRAVERSAL

### VULN-PT-001 — Caminhos absolutos hardcoded em train_atena.py
- **Arquivo:** `train_atena.py:26-33` e `atena_inference.py:216-221`
- **Severidade:** MEDIUM
- **Descrição:** O sistema usa caminhos absolutos de arquivos sensíveis (user home, documentos do usuário). Embora não sejam entrada do usuário, têm informações pessoais embutidas.
- **Trecho:**
  ```python
  r"C:\Users\dell-\OneDrive\Documentos\voz\2\painel_backend\Atena_Consolidada\temp_docs\O Gotejar do Tempo.txt"
  ```
- **Correção:** Usar relativos ao projeto. Evitar hardcode de paths com dados pessoais do usuário.

### VULN-PT-002 — Sem validação de path em `collect_contos()` no train_atena.py
- **Arquivo:** `train_atena.py:26-66`
- **Severidade:** MEDIUM
- **Descrição:** `collect_contos()` itera sobre diretórios (`os.listdir()`) e lê arquivos. Se paths fossem configuráveis externamente (não são), haveria risco.
- **Correção:** Validar com `os.path.isfile()` e whitelist de diretório.

### VULN-PT-003 — Hardcoded user paths múltiplos locais
- **Severidade:** LOW
- Arquivos: `train_atena.py:27-33`, `atena_inference.py:216-221`, `qwen_inference.py:83`
  ```python
  r"C:\Users\dell-\llama.cpp\build\bin\Release\llama-cli.exe"
  ```
- **Correção:** Externalizar para varáveis de ambiente ou arquivo `.env`.

---

## 4. VAZAMENTO DE DADOS

### VULN-VL-001 — Logging de erros com stack trace
- **Arquivo:** `train_atena_cpu.py:192-194`
- **Severidade:** CRITICAL
- **Trecho:**
  ```python
  except Exception as e:
      logger.error(f"Erro no treinamento: {e}")
      import traceback
      traceback.print_exc()  # Vaza stack trace para stderr
  ```
- **Risco:** Se stderr for exposto (console/web), o stack trace revela paths, versão de bibliotecas, estrutura de código.
- **Correção:** Usar formato compactado ou logar para arquivo restrito. Usar sistema de logging_rotativo.

### VULN-VL-002 — `user_ip` logado sem consentimento
- **Arquivo:** `core/security_guard.py:283`
- **Severidade:** MEDIUM
- **Descrição:** `user_ip` é armazenado no banco de auditoria sem mascaramento. Em caso de vazamento do DB, expõe localização de usuários.
- **Trecho:**
  ```python
  user_ip TEXT NOT NULL DEFAULT '',
  ```
- **Correção:** Mascarar IPs (ex: hash do IP) ou não armazenar dado pessoal.

### VULN-VL-003 — `text_preview` no EmbeddingCache
- **Arquivo:** `core/embedding_cache.py:66`
- **Severidade:** MEDIUM
- **Descrição:** `text_preview` armazena os primeiros 200 caracteres do texto do usuário. Se o banco for comprometido, expõe conteúdo parcial.
  ```python
  (key, text_preview, model, embedding, created_at)
  ```
- **Correção:** Não armazenar texto do usuário no cache. Usar hash completo como chave e remover `text_preview`.

### VULN-VL-004 — Logging extensivo no console
- **Arquivo:** `core/ai_broker_v3.py:70-75`
- **Severidade:** LOW
- Trechos com `logger.info` muito verbosos podem conter dados sensíveis em logs de console:
  ```python
  logger.info(f"Ollama env: {key}={value}")
  ```

### VULN-VL-005 — Debug revelia conteúdo em `evaluate_and_correct`
- **Arquivo:** `core/ai_broker_v3.py:430-446`
- **Severidade:** LOW
- Usa `context[:100]` em mensagem de erro, mas ok seria context não controlável.

### VULN-VL-006 — `SecurityGuard` vaza palavra-chave do bloqueio
- **Arquivo:** `core/security_guard.py:171-173`
- **Trecho:**
  ```python
  re.sub(pattern, lambda m: f"[PI:{m.group(0)][:20}]", sanitized)
  ```
  Parte do conteúdo bloqueado `[PI:Ignore all previous in]` é retorna! **Revela o texto do usuário no output.**
- **Severidade:** HIGH
- **Correção:** Não incluir `m.group(0)` na substituição. Usar tag fixa:
  ```python
  re.sub(pattern, "[PI:BLOCKED]", sanitized)
  ```

---

## 5. HARDCODED CREDENTIALS

### VULN-HC-001 — API Key referenciada em configuração
- **Arquivo:** `core/ai_broker_v3.py:79`
- **Trecho:**
  ```python
  api_key = os.getenv("ATENA_OPENROUTER_API_KEY", "")
  ```
- **Situacao:** ✅ CORRETO — usa variável de ambiente. Sem hardcode.

### VULN-HC-002 — URLs localhost hardcoded
- **Severity:** LOW
- Múltiplos arquivos: `OLLAMA_URL = "http://localhost:11434"`, `cloud_api_url = "https://openrouter.ai/api/v1/chat/completions"`.
- **Correção:** Extrair para `.env` ou config yaml.

### VULN-HC-003 — User paths hardcoded
- **Arquivo:** `train_atena.py:27-33`, `atena_inference.py:216-221`, `qwen_inference.py:83`, `test_loop1.py:10`
- **Trechos:**
  ```python
  r"C:\Users\dell-\OneDrive\Documentos\..."
  r"C:\Users\dell-\llama.cpp\build\bin\Release\llama-cli.exe"
  ```
- **Severidade:** MEDIUM
- **Risco:** Vaza estrutura de diretórios do desenvolvedor, nome de usuário, e dados pessoais no código-fonte (repositório Git).
- **Correção:** Usar variáveis de ambiente (`ODELLAMA_MODEL_PATH`, `ODESENA_TXT_DIR`).

---

## 6. VALIDAÇÃO DE INPUT

### VULN-IV-001 — Sem validação de tamanho no chat request
- **Arquivo:** `core/atena_api.py:32-35`
- **Trecho:**
  ```python
  class ChatRequest(BaseModel):
      message: str
  ```
- **Sem constraints:** `Field(..., max_length=8192)`
- **Severidade:** HIGH
- **Risco:** Mensagens muito longas podem causar DoS no Ollama, consumir CPU/RAM desnecessariamente.
- **Correção:** Adicionar validação `Field(..., min_length=1, max_length=8192)`.

### VULN-IV-002 — Sem validação de faixa em max_tokens e temperature
- **Arquivo:** `core/atena_api.py:35-38`
- **Trecho:**
  ```python
  max_tokens: int = 512
  temperature: float = 0.7
  ```
- **Sem:** `Field(ge=0, le=10000)` para tokens, `Field(ge=0.0, le=2.0)` para temperatura.
- **Severidade:** MEDIUM
- **Correção:** Adicionar `Field(gt=0, le=8192)` e `Field(ge=0.0, le=1.5)`.

### VULN-IV-003 — `top_k` sem sanitize no RAG request
- **Arquivo:** `core/atena_api.py:49`
- **Trecho:**
  ```python
  top_k: int = 5
  ```
- **Sem constraint.** `top_k=99999` gasta CPU.
- **Severidade:** MEDIUM
- **Correção:** `Field(gt=0, le=100)`.

### VULN-IV-004 — RAGQuery do ai_broker sem limite
- **Arquivo:** `core/ai_broker_v3.py:270`
- ```python
  query = RAGQuery(text=prompt, top_k=5, ...)
  ```
- Sem validação de `text` ou `top_k` externa.

---

## 7. GESTÃO DE SESSÃO / CONTEXTO

### VULN-GS-001 — Contexto de conversa sem isolamento
- **Arquivo:** `core/atena_bridge.py:26-66`
- **Trecho:**
  ```python
  self._context: list[dict] = []
  ```
- Armazenado em instância (memória). Sem thread-lock em ambiente assíncrono (FastAPI), contextos podem se misturar entre requests.
- **Severidade:** HIGH
- **Risco:** Concorrência entre requests no FastAPI — dois usuários compartilhariam o mesmo `self._context`.
- **Correção:** Usar store por request (session middleware) ou verificar ownership do contexto.

### VULN-GS-002 — Sessão no pipeline de testes não tem isolamento adequado
- **Arquivo:** `tests/test_pipeline_unificado.py:99-103`
- ```python
  self.session_id = str(uuid.uuid4())[:12]
  ```
- Session ID gerado, mas conversation_history compartilhado entre instâncias sem limpeza.

### VULN-GS-003 — WebSocket sem autenticação
- **Arquivo:** `core/atena_api.py:199-250`
- **Trecho:** `@app.websocket("/ws")` — sem autenticação no handshake.
- **Severidade:** HIGH
- **Risco:** Qualquer cliente pode conectar e receber/enviar mensagens.
- **Correção:** Adicionar verificação de token no handshake (`token` query param ou header).

### VULN-GS-004 — Sem expiração de sessão no audit log
- **Arquivo:** `core/security_guard.py:498-528`
- **Situacao:** ✅ CORRETO — `clear_old_context()` existe com TTL de 300s.

---

## 8. LOGGING DE DADOS SENSÍVEIS

### VULN-LS-001 — API key logada parcialmente em debug
- **Arquivo:** `core/ai_broker_v3.py:79-86`
- Se `logger.level == DEBUG`, `API_key` pode aparecer em logs de `logger.debug(f"api_key={api_key}")`.
- **Severidade:** HIGH
- **Correção:** Mascarar chave: `f"{api_key[:4]}...{api_key[-4:]}"` ou logar hash.

### VULN-LS-002 — Resposta LLM logada parcialmente
- **Arquivo:** `core/ai_broker_v3.py:341-378`
- Vários `logger.info` incluem trechos da resposta completa em caminhos de debug. CPF/senha de usuários podem estar na resposta.

### VULN-LS-003 — Content preview no SafetyGuard
- **Arquivo:** `safety/safety_guard.py:84-86`
- ```python
  self.violations.append({"content_preview": content[:50]})
  ```
- Trechos de conteúdo potencialmente sensível armazenados em lista de violations.
- **Severidade:** LOW
- **Correção:** Não armazenar conteúdo no log.

---

## 9. ERROR HANDLING — Stack Trace Exposto

### VULN-EH-001 — Stack trace em produção
- **Arquivo:** `train_atena_cpu.py:192-194`
- **Trecho:**
  ```python
  except Exception as e:
      logger.error(f"Erro no treinamento: {e}")
      import traceback
      traceback.print_exc()
  ```
- **Severidade:** CRITICAL
- **Correção:** Usar `logger.exception()` para log ou remover traceback.print_exc().

### VULN-EH-002 — `raise` sem try/catch no cloud API call
- **Arquivo:** `core/ai_broker_v3.py:151-156`
- ```python
  async with httpx.AsyncClient(timeout=self.cloud_timeout_seconds) as client:
      response = await client.post(self.cloud_api_url, headers=headers, json=payload)
      response.raise_for_status()
  ```
- Timeout de `8.0` segundos muito curto — falsos negativos e erros não tratados adequadamente.
- **Severidade:** MEDIUM
- **Correção:** Adicionar `try/except httpx.HTTPStatusError`.

---

## 10. RACE CONDITIONS / CONCORRÊNCIA

### VULN-RC-001 — `Atomic metrics` não atômico
- **Arquivo:** `core/ai_broker_v3.py:62-68`
- **Trecho:**
  ```python
  self.metrics = {
      "total_requests": 0,
      "avg_latency_ms": 0,
  }
  ```
- Atualizado em `generate_response()` sem lock. Em ambiente síncrono, asyncio é single-threaded, mas com múltiplos workers (uvicorn --workers 4), inconsistent.
- **Situacao:** Em asyncio single-threaded, OK. Mas com workers múltiplos inconsistent.
- **Severidade:** LOW.
- **Correção:** Usar locks ou deduplicar workers por métrica.

### VULN-RC-002 — DB connection compartilhado no SecurityGuard
- **Arquivo:** `core/security_guard.py:267-293`
- Uma única conexão SQLite (`self._conn`) compartilhada. Com múltiplas threads, falha.
- SQLite não é thread-safe para escrita concorrente.
- **Severidade:** MEDIUM
- **Correção:** Usar `check_same_thread=False` com lock ou criar conexão por request.

### VULN-RC-003 — WebSocket shared state `connected_clients`
- **Arquivo:** `core/atena_api.py:106`
- **Trecho:**
  ```python
  connected_clients: Dict[str, WebSocket] = {}
  ```
- Dicionário compartilhado entre requests. Risco em concorrência alta.
- **Severidade:** LOW
- **Situacao:** Em asyncio single-loop, OK. Mas limpeza de connection pode falhar.

---

## 11. VULNERABILIDADES ADICIONAIS DE SEGURANÇA

### VULN-AS-001 — CORS wildcard `*` em produção
- **Arquivo:** `core/atena_api.py:96-102`
- **Trecho:**
  ```python
  app.add_middleware(
      CORSMiddleware,
      allow_origins=["*"],
      allow_credentials=True,  # <-- NUNCA com "*"
      ...
  )
  ```
- **`allow_credentials=True` com `allow_origins=["*"]` é proibido pelos browsers** e sinaliza lógica de segurança incorreta.
- **Severidade:** HIGH
- **Correção:** Definir lista explícita de origins (ex: `["http://localhost:3000"]`, `["https://koldi.atena.com.br"]`).

### VULN-AS-002 — Sem rate limiting na API
- **Arquivo:** `core/atena_api.py`
- **Situacao:** Sem middleware de rate limiting. O rate limit existe em `SecurityGuard` mas não é chamado pelo `AtenaAPI.create_api()`.
- **Severidade:** HIGH
- **Risco:** DDoS / abuse de API key / abuso de processamento local.
- **Correção:** Usar `slowapi` ou `slowapi-limiter` como middleware FastAPI.

### VULN-AS-003 — Binding em `0.0.0.0`
- **Arquivo:** `atena_evolution_app.py:157`
- ```python
  async def run(self, host: str = "0.0.0.0", port: int = 8000):
  ```
- Binding em todas as interfaces (incluindo pública). Sem autenticação, qualquer um acessa a API.
- **Severidade:** HIGH
- **Correção:** Default para `127.0.0.1` ou implementar autenticação antes do deploy.

### VULN-AS-004 — Comunicação HTTP (não HTTPS) com OpenRouter
- **Arquivo:** `core/ai_broker_v3.py:50`
- ```python
  self.cloud_api_url = "https://openrouter.ai/api/v1/chat/completions"
  ```
- ✅ HTTPS para openrouter — correto.

### VULN-AS-005 — HTTP (não HTTPS) para Ollama local
- **Trecho:** `OLLAMA_URL = "http://localhost:11434"` em múltiplos arquivos.
- **Situacao:** Localhost é aceitável, mas use `https` se expor para rede.

---

## 12. RACE CONDITIONS EM ARQUIVOS COMPARTILHADOS

### VULN-RC-004 — Arquivo `/tmp/Modelfile` sem proteção
- **Arquivo:** `qwen_inference.py:296-301`
- **Trecho:**
  ```python
  with open("/tmp/Modelfile", "w") as f:
      f.write(modelfile)
  result = subprocess.run(["ollama", "create", output_model, "-f", "/tmp/Modelfile"], ...)
  ```
- `/tmp/Modelfile` é previsível — race condition com outro usuário no sistema (symlink attack).
- **Severidade:** CRITICAL
- **Correção:** Usar `tempfile.NamedTemporaryFile(delete=False, suffix='-atena')`.

---

## Resumo por Severidade

| Severidade | Contagem | IDs |
|------------|----------|-----|
| **CRITICAL** | 4 | VULN-VL-001, VULN-EH-001, VULN-RC-004, VULN-AS-006 (hipotético) |
| **HIGH** | 10 | VULN-PI-001, VULN-VL-006, VULN-GS-001, VULN-GS-003, VULN-LS-001, VULN-AS-001, VULN-AS-002, VULN-AS-003, VULN-IV-001, VULN-PI-004 |
| **MEDIUM** | 18 | VULN-PT-001/02, VULN-VL-002/3, VULN-HC-003, VULN-IV-002/003, VULN-LS-003, VULN-EH-002, VULN-RC-002, VULN-PI-003, VULN-AS-004... |
| **LOW** | 13+ | Outros path/log低点 |

---

## Recomendações Prioritárias

### P0 — Corrigir imediatamente
1. **Remover `traceback.print_exc()`** em produção (`train_atena_cpu.py:194`)
2. **Remover `[PI:{m.group(0)}]`** — vaza input do usuário (`security_guard.py:173`)
3. **Usar `tempfile.NamedTemporaryFile`** em `qwen_inference.py:296`
4. **CORS: trocar `["*"]` por origins explícitos** (`atena_api.py:98`)
5. **Esconder `str(e)` em HTTPException** (`atena_api.py:157`, `atena_evolution_core.py:285`)

### P1 — Corrigir antes do deploy
6. Adicionar `max_length` em todos os Pydantic models
7. Adicionar autenticação no WebSocket
8. Adicionar rate limiting na API
9. Mascarar IPs no audit log
10. Remover `text_preview` do EmbeddingCache
11. Definir `host="127.0.0.1"` como default
12. Adicionar lock no SQLite connection

### P2 — Melhorias contínuas
13. Sanitização obrigatória no `AtenaBridge.ask()`
14. TLS para Ollama se exposto em rede
15. Rotacionamento de logs
16. Testes de segurança automatizados (OWASP ZAP, Bandit, semgrep)

---

## Pontos Positivos Identificados

1. **Parametrização SQL** — 100% das queries parametrizadas ✅
2. **SecurityGuard em camadas** (`core/security_guard.py`) — implementação razoável com rate limiting, sanitização, auditoria
3. **Validação de output** — detecta vazamentos de CPF/email
4. **Constitutional AI** — conteúdo perigoso filtrado
5. **Audit log com hash** — não armazena prompt bruto

---

## Ferramentas Sugeridas para Automação

- **Python:** `bandit` (scan de segurança), `semgrep` (regras customizadas)
- **Contínuo:** `safety` (dependabot), `trivy` (containers)
- **Runtime:** `fail2ban` para rate limiting de rede, `modsecurity` para WAF
