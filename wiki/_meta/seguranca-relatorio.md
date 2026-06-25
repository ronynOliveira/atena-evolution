---
title: Relatório de Segurança — 2026-05-20
created: 2026-05-20
updated: 2026-05-20
type: query
tags: [seguranca, auditoria, manutencao]
---

# Relatório de Segurança — 2026-05-20

## Resumo
**Status geral:** ⚠️ 3 problemas críticos encontrados

---

## 1. Hardware e Recursos

| Recurso | Valor | Status |
|---------|-------|--------|
| CPU | 26% | ✅ Saudável |
| RAM | 12.8/15.7GB (81.3%) | ⚠️ Alto mas dentro do limite |
| Disco C: | 535/933GB (57.4%) — 397GB livre | ✅ OK |
| Rede | Ping OK | ✅ OK |

---

## 2. Processos Críticos

| Processo | Status | Detalhes |
|----------|--------|----------|
| Chrome CDP | ✅ Rodando | 23 processos |
| Kimi WebBridge | ✅ Rodando | 1 processo |
| Gateway Hermes | ⚠️ PARADO | Impacta todos os cron jobs |

---

## 3. Cron Jobs (6 ativos)

| Job | Frequência | Status |
|-----|-----------|--------|
| atena-automacao-diaria | 12h | ⚠️ Não dispara (gateway down) |
| atena-verificar-atualizacoes | 12h | ⚠️ Não dispara (gateway down) |
| atena-monitor-sistema | 6h | ⚠️ Não dispara (gateway down) |
| atena-auto-evolucao | 24h | ⚠️ Não dispara (gateway down) |
| atena-monitor-distonia | 7d | ⚠️ Não dispara (gateway down) |
| Segurança Atena - Red Teaming | 12h | ❌ Erro: Connection error (desde 16/05) |

**⚠️ Gateway is not running — jobs won't fire automatically.**

---

## 4. Credenciais

| Credencial | Status |
|------------|--------|
| GITHUB_TOKEN | ✅ Configurado no Windows registry |
| OPENROUTER_API_KEY | ❌ Não encontrado |
| COMPOSIO_API_KEY | ❌ Não configurado |
| OLLAMA_API_KEY | ❌ Não configurado (não necessário para local) |
| BRAVE_SEARCH_API_KEY | ❌ Não configurado |
| SERPER_API_KEY | ❌ Não configurado |

---

## 5. Backup do Wiki

| Item | Status |
|------|--------|
| Git inicializado | ✅ |
| Último commit | 2026-05-20 13:47 |
| Sincronizado com GitHub | ✅ |
| Mudanças pendentes | Nenhuma |

---

## 6. Integridade dos Arquivos

| Arquivo | Tamanho | Status |
|---------|---------|--------|
| tools/tts_fala.py | 345 bytes | ✅ |
| tools/cerebro_atena.py | 14,267 bytes | ✅ |
| tools/backup_wiki.py | 6,326 bytes | ✅ |
| tools/monitor_sistema.py | 5,990 bytes | ✅ |
| wiki/index.md | 3,281 bytes | ✅ |
| wiki/SCHEMA.md | 2,992 bytes | ✅ |

---

## 7. Segurança do Sistema

| Item | Status |
|------|--------|
| Firewall (Domain) | ✅ Ativo |
| Firewall (Private) | ✅ Ativo |
| Firewall (Public) | ✅ Ativo |
| Windows Defender | ✅ Ativo |
| McAfee | ✅ Ativo |
| Atualizações | ✅ Automático (nível 4) |

---

## 8. Problemas Encontrados

### 🔴 Crítico: Gateway Parado
- **Impacto:** 6 cron jobs não disparam automaticamente
- **Solução:** Executar `hermes gateway install` como Administrador
- **Workaround:** `hermes gateway run` em foreground (não persiste após reboot)

### 🔴 Crítico: Permissões de Arquivos
- **Arquivos afetados:**
  - `C:\Users\dell-\.hermes\.env`
  - `C:\Users\dell-\.hermes\config.yaml`
  - `C:\Users\dell-\AppData\Local\hermes\config.yaml`
- **Problema:** Legíveis por outros usuários
- **Solução:** Executar como Admin:
  ```
  icacls "C:\Users\dell-\.hermes\.env" /inheritance:r /grant:r "dell-:R"
  icacls "C:\Users\dell-\.hermes\config.yaml" /inheritance:r /grant:r "dell-:R"
  icacls "C:\Users\dell-\AppData\Local\hermes\config.yaml" /inheritance:r /grant:r "dell-:R"
  ```

### 🟡 Médio: Job Red Teaming com Erro
- **Job:** Segurança Atena - Red Teaming Auto
- **Erro:** RuntimeError: Connection error (desde 16/05)
- **Causa provável:** Gateway caiu e nunca voltou
- **Solução:** Resolver o gateway e re-executar o job

### 🟡 Médio: RAM Alta (81%)
- **Uso:** 12.8GB de 15.7GB
- **Causa provável:** Múltiplos processos Chrome + Ollama
- **Monitorar:** Se passar de 85%, investigar

---

## 9. Ações Requeridas do Arquiteto

1. **Abrir terminal como Administrador**
2. **Executar:** `hermes gateway install`
3. **Corrigir permissões:** Executar os 3 comandos icacls acima
4. **Verificar:** `hermes cron list` deve mostrar gateway rodando

---

## Ver também
- [[automacao-atena]]
- [[projetos-pendentes]]
- [[analise-arquitetura]]
