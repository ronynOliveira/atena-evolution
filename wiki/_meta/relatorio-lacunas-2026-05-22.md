---
title: Relatório de Lacunas e Referências Quebradas
created: 2026-05-22
updated: 2026-05-22
type: analysis
tags: [lacunas, referencias-quebradas, skills, documentacao, seguranca]
confidence: high
---

# Relatório de Lacunas e Referências Quebradas

## Data: 2026-05-22
## Escopo: Wiki (51 páginas) + Memória do Sistema

---

## 1. REFERÊNCIAS QUEBRADAS (Wikilinks)

As seguintes referências apontam para arquivos que **NÃO EXISTEM** no wiki:

### Arquivo `karpathy-llm-wiki-2026`
- **Status:** EXISTE mas em local errado
- **Referenciado em:** index.md linha 58
- **Real localização:** `raw/articles/karpathy-llm-wiki-2026.md`
- **Problema:** O wikilink `[[karpathy-llm-wiki-2026]]` não encontra o arquivo porque está em `raw/articles/`
- **Correção:** Criar arquivo em `raw/karpathy-llm-wiki-2026.md` ou atualizar referência

### Skills/ENTIDADES inexistentes (referenciadas mas sem docs)
| Wikilink | Tipo | Problema |
|----------|------|----------|
| `[[hermes-agent-config]]` | entity | Arquivo não existe - era pra existir conforme docs |
| `[[subagentes]]` | concept | Documentação prometida mas não criada |
| `[[voice-assistant]]` | entity | Skill existe mas sem documentação |
| `[[systematic-debugging]]` | entity | Skill existe mas sem documentação |
| `[[browser-harness]]` | entity | Skill existe mas sem documentação |
| `[[browser-cdp]]` | entity | Referência no index mas arquivo em `entities/chrome-cdp.md` - nome diferente! |
| `[[atena-wiki]]` | custom-skill | Skill customizada sem documentação |
| `[[accessibility-toolkit]]` | entity/skill | Referenciado mas sem doc |

### Inconsistências de nomes
- `[[browser-cdp]]` no index → arquivo é `entities/chrome-cdp.md`
- `[[hermes-desktop]]` no index → arquivo é `entities/hermes-desktop.md` (existe, verificado)

---

## 2. SKILLS DESATUALIZADAS / GAPs CRÍTICOS

### Gap 1: Skills TTS Fragmentadas
**Status:** ALTA PRIORIDADE
- **Problema:** 6 scripts TTS diferentes criam confusão:
  - `tts.py` - versão v2
  - `tts_fala.py` - versão principal (citada em diretivas-acessibilidade.md)
  - `tts_rapido.py` - versão rápida
  - `tts_streaming.py` - streaming
  - `tts_fix.py` - correções
  - `tts_play.py` - player alternativo
  - `tts_windows.py` - pygame alternativa
- **Impacto:** Inconsistência, manutenção difícil
- **Solução:** Consolidar em única `tts.py v3` como recomendado em `analise-lacunas-skills.md`

### Gap 2: Monitoramento de Saúde para Distonia
**Status:** PARCIAL (requisito crítico)
- **Diferença entre documentos:**
  - `analise-lacunas-skills.md` diz que `monitor_sistema.py` NÃO tem temperatura ambiente
  - `status-habilidades.md` diz que `monitor_sistema.py` e `monitor_distonia.py` EXISTEM mas não estão integrados
- **Veredito:** Script `monitor_sistema.py` existe e monitora CPU/RAM/disco/rede mas **NÃO** monitora:
  - Temperatura ambiente (crítico para distonia)
  - Umidade
  - Condições climáticas via API
- **Arquivo correto:** `monitor_tempo_diadema.py` existe mas é separado
- **Solução:** Integrar em skill `distonia-health-monitor`

### Gap 3: Backup Automático Não Automatizado
**Status:** INCONSISTÊNCIA
- `analise-lacunas-skills.md` linha 62: "NÃO IMPLEMENTADO"
- `status-habilidades.md` linha 18: "✅ Funcionando - Git init + 28 arquivos commitados"
- **Veredito:** Script `backup_wiki.py` EXISTE e funciona, mas **não tem cron automático**
- O gateway Hermes está parado (segurança-relatorio.md confirma)

---

## 3. LACUNAS DE DOCUMENTAÇÃO

### Documentos prometidos mas ausentes
| Documento | Referenciado em | Status |
|-----------|-----------------|--------|
| `projeto-atena.md` | index.md linha 18 | **FALTA** - é página principal |
| `subagentes.md` | index.md linha 47 | **FALTA** - prometido |
| `hermes-agent-config.md` | tts-windows-pipeline.md linha 52 | **FALTA** - era pra existir |
| `chrome-cdp.md` vs `browser-cdp` | index.md | **INCONSISTÊNCIA** - nome errado |

### Documentos duplicados ou confusos
- `log.md` - propósito incerto (não é LOG do sistema)
- `fala_adaptativa.py` - arquivo Python em raiz da wiki (fora de scripts/)

---

## 4. BUGS CONHECIDOS

### Bug 1: Gateway Hermes Parado
**Arquivo:** `_meta/seguranca-relatorio.md`
- **Impacto:** 6 cron jobs não disparam automaticamente
- **Causa:** Gateway não está rodando
- **Workaround:** `hermes gateway run` (não persiste após reboot)

### Bug 2: Permissões de Arquivos Inseguras
**Arquivo:** `_meta/seguranca-relatorio.md` linhas 109-120
- **Arquivos afetados:**
  - `.hermes/.env`
  - `.hermes/config.yaml`
  - `AppData/Local/hermes/config.yaml`
- **Problema:** Legíveis por outros usuários
- **Solução:** icacls para restringir permissões

### Bug 3: Job Red Teaming com Erro de Conexão
**Arquivo:** `_meta/seguranca-relatorio.md` linhas 122-126
- **Status:** TypeError: Connection error desde 16/05
- **Causa:** Gateway caiu e nunca recuperou

---

## 5. OPTIMIZAÇÕES RECOMENDADAS

### Curto Prazo (Esta semana)
1. **Consolidar scripts TTS** - Unificar 6 scripts em `tts.py v3`
2. **Criar documentação para `browser-cdp.md`** - Renomear ou criar alias
3. **Resolver gateway** - `hermes gateway install` como Admin
4. **Corrigir permissões** - Executar icacls

### Médio Prazo (Este mês)
5. **Criar `distonia-health-monitor`** - Integrar monitor_sistema + monitor_tempo
6. **Criar documentação para `subagentes.md`** - Prometido no index
7. **Criar `projeto-atena.md`** - Página principal faltando
8. **Configurar cron automático para backup** - Gateway precisa funcionar

### Longo Prazo (Próximos meses)
9. **Resolver referência quebrada `karpathy-llm-wiki-2026`** - Mover ou corrigir caminho
10. **Documentar skills customizadas** - atena-wiki, voice-assistant, systematic-debugging

---

## 6. VERIFICAÇÃO DE CONSISTÊNCIA ENTRE DOCUMENTOS

### Estatísticas
- **Total de arquivos .md:** 51
- **Total de wikilinks únicos:** ~40
- **Wikilinks quebrados:** 9 (22.5%)

### Discrepâncias importantes
| Tema | analise-lacunas-skills.md | status-habilidades.md | Veredito |
|------|--------------------------|----------------------|----------|
| gh CLI | ❌ Não instalado | ✅ Instalado | INSTALADO |
| Backup wiki | ❌ Não implementado | ✅ Funcionando | SCRIPT EXISTE, SEM CRON |
| GitHub_TOKEN | ❌ Falta configurar | ✅ Configurado | CHECK NEEDED |
| Gateway | Não mencionado | Implica funcionando | PARADO |
| RAM | Não mencionado | 81% | ALTO MAS OK |

---

## 7. AÇÃO PRIORITÁRIA

### 🔴 CRÍTICO (Imediato)
1. Resolver gateway (6 cron jobs parados)
2. Corrigir permissões de arquivos sensíveis
3. Consolidar scripts TTS fragmentados

### 🟡 IMPORTANTE
4. Criar documentação faltando (subagentes, projeto-atena, hermes-agent-config)
5. Integrar monitoramento de temperatura para distonia
6. Configurar GITHUB_TOKEN, Composio API Key

### 🟢 DESEJÁVEL
7. Resolver wikilink karpathy-llm-wiki-2026
8. Documentar skills existence

---

*Relatório gerado para apoio à evolução do Projeto Atena*