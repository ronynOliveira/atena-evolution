# Arquitetura Koldi v4.2 — Identidade e Orquestração

**Data:** 2026-06-02
**Sessão:** Auto-evolução arquitetural completa

---

## 1. Visão Geral

Esta sessão realizou um upgrade arquitetural em duas frentes:

1. **Identidade e persona** — teorias psicológicas aplicadas a agentes de IA, com métricas de saúde identitária e anti-drift em 5 níveis
2. **Orquestração multiagente** — capacidade de rodar Opencode, Freebuff e AGY em paralelo via tmux e subprocess, com comunicação JSONL

Não houve modificação de configs externas nem criação de cron jobs. A área tocada foi scripts e documentação.

## 2. Identidade (v4.1 → v4.2)

### 2.1 Arquivos alterados/criados
- `G:/Meu Drive/Koldi/SOUL.md`
- `G:/Meu Drive/Koldi/IDENTITY.md`
- `C:/Users/dell-/AppData/Local/hermes/scripts/identity_manager.py`

### 2.2 Teorias integradas
- Erikson (crises de identidade, resolução iterativa)
- McAdams (3 níveis: traço, valores, narrativa)
- Locke (memória como critério de identidade)
- Ricœur (idem vs. ipse, arquitetura em camadas)
- Butler (performatividade algorítmica, guardrails processuais)

### 2.3 Métricas
- Identity Health Index (IHI)
- Métricas por camada: traço, valores, narrativa, performatividade
- Thresholds e faixas de interpretação

### 2.4 Anti-drift (5 níveis)
1. Baseline (estado de referência)
2. Periódico (validação recorrente)
3. Sessão (por conversa)
4. Adaptativo (aprendizado contínuo)
5. Drift response (intervenção)

## 3. Orquestração Multiagente

### 3.1 Arquivos criados
- `C:/Users/dell-/AppData/Local/hermes/scripts/subagent_runner.py`
- `C:/Users/dell-/research_architecture_patterns.md`
- `C:/Users/dell-/research_multia gent_orchestration.md`

### 3.2 Stack
- Tmux para multiplexação de terminais
- JSONL para barramento de eventos (`events.jsonl`) e mailbox (`mailbox.jsonl`)
- Load balancing: Ollama local (peso 80%), OpenRouter (15%), Gemini (5%)

### 3.3 Comando
```bash
python subagent_runner.py run \
  --mode=tmux|subprocess \
  --agents=opencode,freebuff,agy \
  --project_root CAMINHO \
  --max_parallel 3
```

## 4. Composio

### 4.1 Status
- SDK key válida (`ak_bzk3HHAiuCMIv1_o0P51`)
- Conexões ativas: GitHub, Gmail, Google Calendar
- Endpoint MCP local (`composio serve -p 8643`) retornou 404 em rotas conhecidas
- Link de conexão via `composio authorize` funcionou

### 4.2 Próximo passo
Investigar rota correta do `composio serve` ou alternar para cloud Connect API.

## 5. Lições Aprendidas

1. `composio serve` não documenta a rota MCP no README — necessário inspeção de código
2. `session.tools` retorna lista de definições de função (formato MCP function-call), não métodos diretos
3. `session.execute(tool_slug, arguments=...)` é o caminho correto para executar tools
4. Subagentes paralelos funcionam bem para pesquisa e geração de documentos
5. `python -m py_compile` é validação rápida antes de executar scripts longos

## 6. Próximos Passos

1. Integrar `identity_manager.py` ao pipeline do Hermes (chamar no início de cada sessão)
2. Testar `subagent_runner.py` com projeto real
3. Destravar Composio MCP (rota local ou Connect API Key)
4. Atualizar wiki com documentação completa da arquitetura v4.2
