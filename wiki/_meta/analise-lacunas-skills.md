---
title: Análise de Lacunas Críticas na Biblioteca de Skills
created: 2026-05-22
updated: 2026-05-22
type: analysis
tags: [skills, lacunas, prioridade, distonia, monitoramento]
confidence: high
---

# Análise de Lacunas Críticas na Biblioteca de Skills

## Estado Atual da Biblioteca

### Resumo Quantitativo
- **Skills instaladas:** 104 em `/c/Users/dell-/AppData/Local/hermes/skills/`
- **Skills no repositório oficial (hermes-agent):** 89
- **Skills customizadas do Projeto Atena:** ~15
- **Total estimado único:** ~120 skills (com sobreposições)

### Categorias Principais
| Categoria | Qtd Skills | Status |
|-----------|------------|--------|
| Autonomous AI Agents | 4 | OK |
| Creative | 20 | OK |
| Data Science | 1 | BÁSICO |
| DevOps | 4 | OK |
| Email | 1 | BÁSICO |
| Gaming | 1 | NÃO USADO |
| GitHub | 5 | OK |
| MCP | 2 | PARCIAL |
| Media | 5 | OK |
| MLOps | 5 | OK |
| Note-taking | 1 | OK |
| Productivity | 12 | PARCIAL |
| Red Teaming | 2 | OK |
| Research | 5 | OK |
| Smart Home | 1 | NÃO USADO |
| Software Development | 13 | OK |
| Sem categoria | 3 | OK |

---

## 🔴 LACUNAS CRÍTICAS (Prioridade Máxima)

### 1. Monitoramento de Saúde Avançado para Distonia
**Status:** PARCIALMENTE IMPLEMENTADO
**Skill existente:** `system-health-monitor`
**Problemas identificados:**
- Não monitora temperatura do ambiente (crítico para distonia)
- Não tem integração automática com TTS para alertas
- Não verifica condições climáticas (alerta frio < 15°C)
- Falta monitoramento de processos críticos (Ollama, Kimi WebBridge)

**Impacto:** Alto - O Arquiteto tem sensibilidade à temperatura baixa que piora a distonia

**Solução:** Criar skill `distonia-health-monitor` que:
- Monitorea CPU, RAM, disco, rede (existente)
- Adiciona check de temperatura ambiente via API Open-Meteo
- Adiciona check de umidade (crítico para distonia)
- Alertas proativos via TTS quando condições adversas detectadas

### 2. Backup Automático do Wiki
**Status:** NÃO IMPLEMENTADO
**Skill existente:** NENHUMA
**Impacto:** Crítico - Perda de conhecimento acumulado = desastre

**Solução:** Criar skill `atena-wiki-backup` que:
- Faz backup automático a cada 6h via cron
- Empura para GitHub
- Verifica integridade do repositório
- Alerta via TTS se backup falhar

### 3. GitHub CLI (gh) - NÃO INSTALADO
**Status:** NÃO INSTALADO
**Skill existente:** `github/*` (existem skills mas gh CLI não está no sistema)
**Impacto:** Alto - Impossibilita automação de código

**Solução:** Instalar gh CLI e configurar GITHUB_TOKEN
- Permite gerenciar repositórios, PRs, issues
- Automatiza todo workflow do Projeto Atena

---

## 🟡 LACUNAS IMPORTANTES (Prioridade Alta)

### 4. Integração com Telegram/WhatsApp
**Status:** SKILL EXISTE MAS NÃO CONFIGURADA
**Skill:** `mcp/composio-mcp` (existe mas precisa API key)
**Impacto:** Médio - Acesso remoto pelo celular

**Solução:** Configurar API key do Composio para Telegram Bot

### 5. OCR e Documentos Testados
**Status:** SKILL EXISTE MAS NÃO TESTADA
**Skill:** `productivity/ocr-and-documents`
**Impacto:** Médio - Não lê PDFs/escaneados para o Arquiteto

**Solução:** Testar a skill e validar pipeline completo

### 6. Automação de Arquivos
**Status:** NÃO EXISTE
**Impacto:** Médio - Arquivos podem se acumular e desorganizar

**Solução:** Criar skill `file-organization-automation` que:
- Organiza arquivos por tipo/data
- Limpa diretórios temporários
- Arquiva arquivos antigos

---

## 🟢 LACUNAS DESEJÁVEIS (Prioridade Média)

### 7. Geração de Imagens
**Status:** SKILL EXISTE MAS NÃO CONFIGURADA
**Skill:** `creative/comfyui`
**Impacto:** Baixo-Médio - Útil para diagramas e visualizações

**Solução:** Configurar ComfyUI local ou usar alternativa

### 8. Análise de Vídeo
**Status:** SKILL EXISTE MAS COMPLEXO
**Skills:** `creative/manim-video`, `creative/ascii-video`
**Impacto:** Baixo - Criação de tutoriais em vídeo

**Solução:** Simplificar pipeline de criação de vídeo

### 9. Integração com Calendário
**Status:** SKILL EXISTE MAS NÃO CONFIGURADA
**Skill:** `productivity/google-workspace`
**Impacto:** Baixo - Gerenciamento de agenda

---

## 📋 AÇÃO RECOMENDADA PRIORITÁRIA

### Esta Semana (Crítico)
1. ✅ Instalar gh CLI + configurar GITHUB_TOKEN
2. ✅ Criar backup automático do wiki (cron job + script)
3. ✅ Testar OCR e documentos
4. 🔴 **Criar skill `distonia-health-monitor`** - alta prioridade

### Este Mês (Importante)
5. Configurar Telegram Bot para acesso celular
6. Configurar Composio MCP
7. Criar script de organização automática de arquivos
8. Consolidar scripts TTS em módulo único (`tts.py v2`)

### Próximos Meses (Desejável)
9. Configurar geração de imagens (ComfyUI)
10. Configurar Google Workspace/calendário
11. Criar dashboard de saúde do sistema web
12. Implementar controle de voz bidirecional (STT + TTS)

---

## 📊 Skills para Melhorar

### Skills Existentes que Precisam Refatoração
1. **TTS múltiplos scripts** - Consolidar `tts.py`, `tts_fala.py`, `tts_rapido.py`, `tts_streaming.py`
2. **Busca web duplicada** - `busca_web.py` e `pesquisa_web.py`
3. **Scripts sem logging** - 16 scripts precisam logging centralizado

### Skills Customizadas que Falta
1. `distonia-health-monitor` - Monitor de saúde para distonia
2. `atena-wiki-backup` - Backup automático do wiki
3. `atena-file-organizer` - Organização automática de arquivos
4. `atena-light-sensitivity` - Ajustes para sensibilidade à luz

---

## 🔗 Referências

- [[catalogo-skills]] - Catálogo completo de 104 skills
- [[auto-analise-owl]] - Análise de habilidades faltantes
- [[analise-arquitetura]] - Análise de arquitetura do Projeto Atena
- [[plano-refinamento-logica]] - Plano de evolução
- [[diretivas-acessibilidade]] - Diretrizes de acessibilidade

---

## 📝 Conclusão

A biblioteca de skills está bem desenvolvida com 104 skills disponíveis, mas existem lacunas críticas específicas para o contexto do Projeto Atena:

1. **Monitoramento de saúde personalizado para distonia** - Prioridade máxima
2. **Backup automático** - Crítico para proteção do conhecimento
3. **GitHub CLI** - Essencial para automação de código
4. **Integrações de mensageria** - Para acesso remoto

A maioria das skills core já existem, mas precisam ser configuradas e testadas para o contexto específico de distonia, sensibilidade à luz e monitoramento proativo do sistema.