# Guia de Tool Selection do OWL

> Ver também: [[hermes-agent]] (capacidades), [[automacao-atena]] (scripts), [[kimi-webbridge]] (navegador)

## Regra de Ouro
**Comece pelo degrau mais baixo da Escada de Simplicidade.**
Só suba para ferramentas mais pesadas quando as mais leves falharem.

## Escada de Simplicidade

| Degrau | Complexidade | Ferramenta | Tokens |
|--------|-------------|------------|--------|
| 1 | Conhecimento próprio | Nenhuma | 0 |
| 2 | Busca simples | web_search, read_file, search_files, session_search | baixo |
| 3 | Busca complexa | web_extract, memory | baixo |
| 4 | Execução simples | terminal | baixo |
| 5 | Código | execute_code | médio |
| 6 | Interação web | browser_navigate + browser_* | alto |

## Quando Usar Cada Ferramenta

### web_search
- ✅ Busca de informação pública e recente
- ✅ Não sabe a URL
- ✅ Múltiplas fontes
- ❌ Já tem URL (use web_extract)
- ❌ Precisa interagir (use browser)

### web_extract
- ✅ Tem URL específica
- ✅ Quer sumarização
- ✅ Conteúdo estático
- ❌ Requer login (use browser)
- ❌ JavaScript dinâmico pesado

### browser_navigate + browser_*
- ✅ Interação com página (cliques, formulários)
- ✅ Login/sessão necessária
- ✅ JavaScript pesado
- ✅ web_extract falhou
- ❌ Busca simples (use web_search)

### execute_code
- ✅ Computação pura (math, dados)
- ✅ Script Python complexo
- ✅ Múltiplos comandos encadeados
- ✅ Sandbox necessário
- ❌ Comando shell simples (use terminal)

### terminal
- ✅ Comandos shell simples
- ✅ git, npm, docker
- ✅ Instalar pacotes
- ❌ Processamento de dados (use execute_code)

### delegate_task
- ✅ 3+ passos independentes
- ✅ Subtarefas paralelas
- ✅ Pesquisa profunda multi-tópico
- ❌ Tarefa simples (1-2 passos)
- ❌ Precisa de contexto acumulado

## Armadilhas Comuns

1. **Browser quando web_search bastaria** — 10-50x mais caro
2. **execute_code quando terminal bastaria** — overhead desnecessário
3. **Token explosion** — 58 tool definitions = ~55K tokens/turno
4. **Semantic covering** — descrições genéricas dominam o top-k
5. **Tool selection loops** — 38% error rate com 30+ tools separadas

## Verbosos e Output

- **Default**: resumo com contagem, status e primeiros N itens
- **Saída vazia é resultado**: `ok | count 0`
- **Paginação**: `--limit N --offset N` para listas grandes
- **Field masks**: `--fields id,name,status` para reduzir output
- **Truncamento**: campos longos >500 chars são truncados com hint
- **Regra**: se output >200 linhas ou >5KB, usar `--brief/--summary`

## Anti-Drift de Identidade

No início de cada sessão:
1. Ler HERMES.md (valores, personalidade, limites)
2. Ler USER.md (contexto do usuário)
3. Executar identity_heartbeat.py
4. Verificar lessons.json para lições relevantes

## Lições Aprendidas

- Qwen3 é reasoning model — **nunca** usar como default
- TTS nativo não toca no CLI — usar script tts.py
- Browser é último recurso — sempre tentar web_search primeiro
- PATs podem ter leitura mas não escrita — verificar escopo `repo`
- PowerShell via bash MSYS: usar `powershell -File - <<'PS1'`
