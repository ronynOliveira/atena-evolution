# Análise Update Hermes 0.15.1 — 2026-06-04

## Resumo do Update

- **126 novos commits** entre a versão anterior e 0.15.1
- **377 arquivos alterados**: +27.729 linhas, -10.798 linhas
- Mudanças principais: Dashboard, Desktop, Gateway Windows, Skills, MCP

## Mudanças Relevantes para o Koldi

### 1. Gateway Windows (IMPORTANTE)
- `fix(gateway-windows): anchor detached/startup cwd at HERMES_HOME` — Corrige bug onde o gateway perdia o diretório de trabalho
- `fix(constants): use windows native default hermes home` — Usa o path correto do Windows
- `fix(gateway): decode schtasks output with locale encoding on Windows` — Corrige encoding de tasks no Windows
- **Impacto**: Nosso gateway já estava configurado corretamente, mas agora é mais estável

### 2. Memory System
- `refactor(supermemory): session-level ingest + kebab aliases` — Supermemory agora suporta ingestão por sessão
- `fix(memory): fall back to pip when uv is unavailable` — Fallback para pip se uv não disponível
- **Impacto**: Nosso memory_pipeline já funciona independente do supermemory

### 3. Skills
- `feat(prompt): broaden Hermes self-knowledge pointer to docs + skill` — O Hermes agora sabe mais sobre si mesmo
- `fix(skills): document xurl X Article ingestion` — Documentação de X/Twitter
- `fix(update): don't fail desktop rebuild / skills sync on mid-rebuild venv` — Update não quebra mais skills
- **Impacto**: Positivo — skills mais estáveis durante updates

### 4. MCP
- `fix(mcp): resolve ${ENV} in discovery probe so header auth works` — Variáveis de ambiente resolvidas em MCP
- **Impacto**: Nosso Composio MCP e google-workspace MCP se beneficiam

### 5. Dashboard
- `feat(dashboard): always enable embedded chat; remove dashboard --tui flag` — Chat embutido sempre ativo
- `feat(dashboard): add Debug Share to the System page` — Debug Share
- `feat(dashboard): check-before-update flow` — Verificação antes de update
- **Impacto**: Não afeta uso via CLI

### 6. Desktop (não afeta CLI)
- Muitas melhorias de UI/UX no Desktop
- OAuth-aware remote gateway connection
- Username/password login for remote gateways
- **Impacto**: Nenhum para uso via terminal

### 7. Ferramentas
- `fix(tools): stop hermes tools reporting kanban as removed` — Kanban não aparece mais como removido
- **Impacto**: Neutro

## Ações Executadas

### Correções
1. ✅ **Gateway reiniciado** (PID 28708) — estava parado
2. ✅ **security_watchdog.py corrigido** — import path de `lib.memory_pipeline` (adiciona HERMES_HOME ao sys.path em vez de LIB_DIR)
3. ✅ **3 cron jobs removidos** (scripts inexistentes):
   - `atena-evolution-monitor` (evolution_monitor.py não existe)
   - `Hermes Auto-Update` (auto_update.py não existe)
   - `koldi-g-backup-auto` (tools/backup_automatico.py não existe no path esperado)

### Otimizações
4. ✅ **Skills de memória mescladas** — memory-care e memory-decay-queue marcadas como deprecated, memory-pipeline é a skill unificada
5. ✅ **Ollama reiniciado** — 7 modelos online (gemma4:e2b, gemma4:e4b, hermes3:8b, qwen3:8b, deepseek-r1:8b, nomic-embed-text)
6. ✅ **103/103 testes passando** — lib/ tests OK

### Estado Atual
- Gateway: ✅ Rodando (PID 28708)
- Ollama: ✅ Rodando (7 modelos)
- Cron jobs: 22 ativos, 0 com erro
- Skills: 103 instaladas, 2 deprecated (memory-care, memory-decay-queue)
- Testes: 103/103 passando

## Próximos Passos Sugeridos
1. Recriar o cron job de backup automático com path correto
2. Avaliar se o supermemory session-level ingest substitui nosso memory_pipeline
3. Testar o novo Debug Share do dashboard
4. Verificar se há novos tools MCP disponíveis
