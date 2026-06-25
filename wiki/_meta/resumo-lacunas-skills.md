---
title: Resumo Executivo — Lacunas na Biblioteca de Skills
created: 2026-05-22
updated: 2026-05-22
type: summary
tags: [skills, lacunas, executivo, projetos-atena]
confidence: high
---

# Resumo Executivo — Lacunas Críticas na Biblioteca de Skills

## Estado Atual
- **Total de skills disponíveis:** 104 skills
- **Localização:** `C:\Users\dell-\AppData\Local\hermes\skills\`
- **Skills customizadas Projeto Atena:** ~15 skills específicas

## 🔴 CRÍTICO — Ações Imediatas Necessárias

### 1. Monitoramento de Saúde para Distonia
**Status:** PARCIAL - `monitor_sistema.py` e `monitor_distonia.py` existem mas não integrados
**Problema:** Não monitora temperatura ambiente (frio piora distonia)
**Solução:** Criar skill `distonia-health-monitor`

### 2. Backup Automático do Wiki
**Status:** SCRIPT EXISTE (`backup_wiki.py`) mas não automatizado
**Problema:** Falta cron job automático
**Solução:** Ativar via `hermes cron` + TTS notificação

### 3. GitHub CLI (gh)
**Status:** NÃO INSTALADO no sistema
**Problema:** Impossibilita automação de código
**Solução:** Instalar gh CLI e configurar GITHUB_TOKEN

## 🟡 IMPORTANTE — Próximas Ações

### 4. Composio MCP
**Status:** Skill existe mas precisa API key
**Impacto:** 500+ integrações externas (Google, Slack, Notion)

### 5. OCR e Documentos
**Status:** Skill existe mas não testada (`productivity/ocr-and-documents`)

### 6. Consolidar Scripts TTS
**Status:** 5 scripts TTS diferentes → precisam unificação
**Script correto:** `owl_tts.py` + `tts.py` v3

## 📋 Skills por Categoria (Status)

| Categoria | Qtd | Status | Notes |
|-----------|-----|--------|-------|
| Accessibility | 2 | ⚠️ PARCIAL | `accessibility-toolkit` e `voice-assistant` |
| DevOps | 4 | ✅ OK | Monitor, webhooks, subagents |
| Research | 5 | ✅ OK | Busca web, arxiv, llm-wiki |
| Creative | 20 | ✅ OK | Hermes-identity, comfyui, etc |
| GitHub | 5 | ⚠️ SEM CLI | Skills existem mas gh não instalado |

## 🎯 Recomendações Prioritárias

### Semana 1
1. [ ] Instalar gh CLI + GITHUB_TOKEN
2. [ ] Ativar backup automático do wiki via cron
3. [ ] Criar skill `distonia-health-monitor`
4. [ ] Configurar Composio MCP

### Mês 1
5. [ ] Testar e validar OCR
6. [ ] Consolidar scripts TTS
7. [ ] Criar automação de arquivos
8. [ ] Configurar Telegram Bot

## 🔗 Arquivos Chave

- **Análise completa:** `wiki/_meta/analise-lacunas-skills.md`
- **Catalogo skills:** `wiki/entities/catalogo-skills.md`
- **Auto-análise OWL:** `wiki/_meta/auto-analise-owl.md`
- **Diretivas acessibilidade:** `wiki/concepts/diretivas-acessibilidade.md`

---

*Documento gerado para apoio à evolução do Projeto Atena*