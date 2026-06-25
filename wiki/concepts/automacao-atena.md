---
title: Automação do Projeto Atena
created: 2026-05-20
updated: 2026-05-20
type: concept
tags: [automacao, hermes-agent, projeto-atena, manutencao]
sources: []
confidence: high
---

# Automação do Projeto Atena

## Visão Geral
Sistema de automação que garante a manutenção contínua da memória, wiki e skills do Projeto Atena.

### Scripts Disponíveis

| Script | Função | Local |
|---|---|---|
| `cerebro_atena.py` | Orquestrador principal — executa todas as verificações | `~/AppData/Local/hermes/tools/` |
| `automacao_memoria.py` | Verifica memória e migra para wiki se necessário | `~/AppData/Local/hermes/tools/` |
| `evolucao_continua.py` | Análise com OpnCode para sugestões de melhoria | `~/AppData/Local/hermes/tools/` |
| `verificar_atualizacoes.py` | Verifica atualizações do Hermes Agent, Desktop, skills e sistema | `~/AppData/Local/hermes/tools/` |
| `monitor_sistema.py` | Monitor de CPU, RAM, disco e rede | `~/AppData/Local/hermes/tools/` |
| `backup_wiki.py` | Backup automático do wiki via git | `~/AppData/Local/hermes/tools/` |

### Cron Jobs Ativos

| Job | Frequência | O que faz |
|---|---|---|
| `atena-automacao-diaria` | 12h | Executa cerebro_atena.py — verificação completa |
| `atena-verificar-atualizacoes` | 12h | Executa verificar_atualizacoes.py — atualizações |
| `atena-monitor-sistema` | 6h | Executa monitor_sistema.py — CPU, RAM, disco, rede |

### Execução
```bash
# Verificação completa
python ~/AppData/Local/hermes/tools/cerebro_atena.py

# Apenas memória
python ~/AppData/Local/hermes/tools/automacao_memoria.py

# Apenas evolução
python ~/AppData/Local/hermes/tools/evolucao_continua.py

# Apenas atualizações
python ~/AppData/Local/hermes/tools/verificar_atualizacoes.py
```

### Frequência Recomendada
- **cerebro_atena.py**: via cron a cada 12h
- **verificar_atualizacoes.py**: via cron a cada 12h
- **automacao_memoria.py**: Quando a memória passar de 50%
- **evolucao_continua.py**: 1x por semana para sugestões de melhoria

### O Que é Verificado
1. **Memória do sistema** — uso e necessidade de migração
2. **Saúde do wiki** — páginas, índice, log
3. **Skills instaladas** — catálogo e atualizações
4. **Pendências** — GITHUB_TOKEN, Composio, Oracle Cloud, Kimi WebBridge
5. **Evolução contínua** — análise com OpnCode para melhorias
6. **Atualizações** — Hermes Agent, Hermes Desktop, skills, sistema
7. **Relatório consolidado** — salvo no wiki em `_meta/`

### Regra de Ouro
> Sempre consultar o wiki antes de qualquer tarefa.
> Sempre registrar novos aprendizados no wiki.
> Sempre buscar ser mais útil e proativo para o Arquiteto.
> Memória do sistema migra para wiki quando encher — nunca compactar.
> Se precisar de intervenção do Arquiteto, informar imediatamente via TTS.

## Ver também
- [[catalogo-skills]]
- [[projetos-pendentes]]
- [[hermes-agent]]
- [[hermes-desktop]]
