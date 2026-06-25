---
title: Projetos Pendentes
created: 2026-05-20
updated: 2026-05-20
type: concept
tags: [projeto-atena, planejamento, hermes-agent]
sources: [raw/hermes-memory-export.md]
confidence: high
---

# Projetos Pendentes

## Registro migrado da memória do sistema do Hermes.

### Pendências Atuais

#### GITHUB_TOKEN
- **Status:** Não configurado
- **Impacto:** Sem o token, não é possível usar gh CLI para gerenciar repositórios, PRs, issues
- **Ação:** Arquiteto precisa gerar um token no GitHub e configurar

#### Composio MCP API Key
- **Status:** Instalado, falta API key
- **Impacto:** Sem a key, não é possível conectar aos 500+ serviços via MCP
- **Ação:** Obter API key do Composio e configurar

#### Oracle Cloud Free Tier
- **Status:** Aprovado, não implementado
- **Impacto:** Arquiteto não consegue acessar o Hermes pelo celular
- **Ação:** Criar conta e provisionar instância
- **Detalhes:** Ver [[vps-oracle-cloud]]

### Fluxo de Pesquisa Web
1. **Primeira opção:** Kimi WebBridge (porta 10086) — navegador real do usuário
2. **Segunda opção:** Gemini CLI — `gemini --model gemini-2.5-pro --skip-trust`
3. **Terceira opção:** OpnCode — `opencode run "pesquisa"`
4. **Navegador nativo:** Só para sites com login/visual
5. **Google direto:** NÃO funciona (bloqueia com CAPTCHA)

### Segurança
- Cron job a cada 12h com Gemini CLI + OpnCode para monitoramento

## Ver também
- [[vps-oracle-cloud]]
- [[hermes-agent]]
- [[ambiente-tecnico]]
