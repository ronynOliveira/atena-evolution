# AUTO-ANÁLISE OWL — 24/05/2026

## 1. PONTOS FRACOS IDENTIFICADOS

### Críticos:
1. **Qwen3 reasoning model** — retorna content vazio, Hermes não lê reasoning field
2. **TTS nativo não funciona no CLI** — precisa de script Python com edge-tts + ffmpeg + PowerShell
3. **Gateway restart não sobe sozinho** — precisa de `hermes gateway install` manual
4. **Gateway/run.py tem 18.270 linhas** — monolítico, difícil de debugar
5. **Context compressor frágil** — ratio fixo de 20%, pode estourar contexto

### Moderados:
6. **Ollama usa ~5.5GB RAM base** — 10 modelos = 44GB em disco
7. **user_char_limit: 5000** — muito baixo para tarefas complexas
8. **api_timeout: 120s** — insuficiente para Ollama local com modelos grandes
9. **Windows support "early beta"** — POSIX paths quebram no MSYS
10. **Cache de sessão sem limite claro** — 128 agentes podem consumir vários GB

### Menores:
11. **SQLite WAL mode** — incompatível com NFS/SMB
12. **Permissões .env bloqueadas** — não pode editar sem admin
13. **API keys espalhadas** — registry, .env, config.yaml, credential_pool.py

## 2. MELHORIAS DE APRENDIZAGEM E HABILIDADES

### Auto-evolução:
- **Lesson Loop** — escrever regras em lessons.md após erros
- **Reflexion** — autocrítica verbal (+11% em benchmarks)
- **EvolveR** — distilação offline + reforço iterativo

### Gestão de Skills:
- Manter SKILL.md <500 linhas
- Testing/evals como código
- Ferramenta opencode-skill-creator

### Memória:
- Arquitetura multi-camada (episódica, RAG, semântica, procedural)
- RAG com chunking semântico reduz tokens 60-80%
- Cuidado com "lost in the middle"

### Uso de Ferramentas:
- Resposta no modelo → não use ferramentas
- Fatos recentes → web_search
- Interação UI → browser
- Validar output → execute_code
- Tarefas paralelas → delegate_task

### Token Economy:
- 1 tarefa = 1 sessão (msg #30 custa 31× mais que #1)
- Pedidos precisos, sumarização de histórico
- Model routing (pequeno para trivial, grande para complexo)

## 3. SEGURANÇA

### Portas expostas:
- 11434 (Ollama) — 0.0.0.0 (rede local)
- 8642 (Gateway API) — 127.0.0.1 (OK)
- 10086 (Kimi WebBridge) — 127.0.0.1 (OK)

### Vulnerabilidades:
- API keys no registry do Windows (acessível por qualquer processo do usuário)
- .env bloqueado (proteção acidental)
- Sem rate limiting no gateway
- Dados sensíveis na MEMORY.md (informações de saúde)
- Tokens em logs (RedactingFormatter existe)

### Recomendações:
- Mover API keys para Windows Credential Manager
- Adicionar rate limiting ao gateway
- Reduzir portas expostas do Ollama para 127.0.0.1 apenas
- Criptografar MEMORY.md
- Implementar health check endpoint (:8080/health)

## 4. AÇÕES PRIORITÁRIAS

### Imediato:
1. Aumentar user_char_limit para 20000
2. Aumentar api_timeout para 300s
3. Implementar fallback para reasoning models
4. Health check endpoint no gateway

### Curto prazo:
5. Reduzir modelos Ollama para 3-4 ativos
6. Centralizar credenciais no Windows Credential Manager
7. Watchdog para gateway no Windows
8. Refatorar gateway/run.py em módulos

### Médio prazo:
9. Implementar RAG com chunking semântico
10. Lesson Loop para auto-evolução
11. Migrar para WSL2 (mais estável)
12. Log shipping centralizado
