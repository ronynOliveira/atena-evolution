# Sessão 2026-05-30 (Parte 3): Code Profiler e Finalização

## Data
30 de maio de 2026 — Terceira parte da sessão

## Tarefas do Senhor Robério
"Use Opencode em 2+ terminais, Freebuff, e outras ferramentas para melhorar pontos fracos. Pesquise na web se necessário."

## Resultados dos Processos Paralelos

Todos os 4 processos (3 Opencode + 1 Freebuff) falharam pelo mesmo bug:
- **Causa**: `cd C:\Users\dell-` no bash MSYS quebra por causa do espaço
- **Solução**: Usar `cd "/c/Users/dell-"` ou `cd '/c/Users/dell-'`
- **Lição**: Sempre usar paths com aspas no bash MSYS

## Ferramentas Criadas (Manualmente)

### 3. Code Profiler (tools/code_profiler.py)
**Status**: ✅ Funcionando
**Descrição**: Analisa scripts Python e gera relatório de qualidade com score 0-100

**Funcionalidades**:
- Conta LOC, funções, classes, imports
- Detecta code smells: funções >50 linhas, variáveis globais, exceções sem tipo, falta de docstrings
- Verifica segurança: shell=True, eval/exec, paths hardcoded
- Score 0-100 com grade (A/B/C/D/F)
- Comandos: analyze, scan, compare

**Scan da pasta tools/**:
- 53 arquivos analisados
- Média: 87.2/100
- Melhores: atena_logging.py (100), comparar_modelos_visao.py (100)
- Piores: teste_tts.py (55), code_profiler.py (57), qmd_memory.py (59)

## Resumo Final da Sessão Completa

### Ferramentas criadas hoje:
1. `tools/qmd_memory.py` — Índice FTS5 para wiki (88 docs, 447 chunks)
2. `tools/auto_research.py` — Pesquisa web multi-fonte com cache
3. `tools/google_search.py` — Wrapper com fallback triplo
4. `tools/google-search/` — Playwright Google search (limitado por CAPTCHA)
5. `tools/code_profiler.py` — Análise de qualidade de código
6. `skills/devops/google-search-playwright/SKILL.md` — Skill documentada

### Arquivos atualizados:
- `~/.hermes/config.yaml` — Adicionado MCP server google-search
- `G:\Meu Drive\Koldi\wiki\_meta\sessao-2026-05-30-google-search.md`
- `G:\Meu Drive\Koldi\wiki\_meta\sessao-2026-05-30-ferramentas.md`
- `G:\Meu Drive\Koldi\wiki\index.md`

### Git commits:
- `2836468` — sessão Google Search
- `2ca64ea` — QMD Memory + Auto Research

## Comandos Úteis (Resumo)

```bash
# QMD Memory
python tools/qmd_memory.py reindex
python tools/qmd_memory.py search "termo"
python tools/qmd_memory.py status

# Auto Research
python tools/auto_research.py search "query" --depth 2
python tools/auto_research.py stats

# Google Search (com fallback)
python scripts/google_search.py "termo" --limit 5

# Code Profiler
python tools/code_profiler.py analyze tools/qmd_memory.py
python tools/code_profiler.py scan tools/ --recursive
python tools/code_profiler.py compare tools/arquivo1.py tools/arquivo2.py
```

## Bugs Encontrados e Corrigidos
1. `start_lineno` não existe em FunctionDef AST do Python 3.11 → usar `lineno`
2. `', '.join(depth)` com depth=int → corrigido para `sources`
3. `node.body[0].value` pode ser None → usar `getattr(..., None)`

## Próximos Passos Sugeridos
- [ ] Adicionar docstrings nas funções do qmd_memory.py (melhorar score de 59→80+)
- [ ] Adicionar embeddings vetoriais ao qmd_memory (Jina v3 GGUF ~1GB)
- [ ] Resolver CAPTCHA do Google Playwright manualmente uma vez
- [ ] Usar code_profiler para melhorar todos os scripts com score <80
