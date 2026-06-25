# Sessão 2026-05-30: Google Search Skill via Playwright

## Data
30 de maio de 2026

## Solicitação do Senhor Robério
Pesquisar uma skill no GitHub para usar o Google como pesquisa, conferir downloads/nota dos usuários, e priorizar segurança.

## Pesquisa Realizada

### Repositórios encontrados

1. **web-agent-master/google-search** (⭐ 598, 🍴 95)
   - URL: https://github.com/web-agent-master/google-search
   - Licença: ISC (open source)
   - Linguagem: TypeScript/Node.js
   - Descrição: Playwright-based Node.js tool que bypassa anti-scraping do Google
   - Recursos: MCP Server, CLI, anti-bot detection bypass
   - Último commit: abril/2025
   - Issues: 7 abertas (nenhum de segurança grave)

2. **alirezarezvani/claude-skills** (⭐ 16.582, 🍴 2.284)
   - URL: https://github.com/alirezarezvani/claude-skills
   - Licença: MIT
   - Descrição: 337 skills para Claude Code, Codex, Gemini CLI, Cursor, Hermes, etc.
   - Conclusão: NÃO tem skill específica de Google Search para Hermes

## Análise de Segurança (web-agent-master/google-search)

### ✅ Pontos positivos
- Código aberto (19 arquivos TypeScript)
- 0 vulnerabilities no npm audit
- Sem envio de dados para terceiros
- Sem API keys necessárias
- Dependências seguras: playwright, commander, zod, pino, @modelcontextprotocol/sdk
- Acessa apenas: google.com, google.co.uk, google.com.au, google.ca

### ⚠️ Pontos de atenção
- Projeto parado desde abril/2025 (sem manutenção ativa)
- Google detecta automação e exige CAPTCHA
- Requer Node.js + Chromium (~200MB)

## Instalação Realizada

### Passo a passo
1. Clone: `C:\Users\dell-\AppData\Local\hermes\tools\google-search\`
2. npm install: 178 pacotes, 0 vulnerabilities
3. Build: TypeScript compilado com sucesso
4. MCP Server: Configurado no config.yaml

### Teste do Playwright
- Resultado: **FALHOU** — Google detectou headless browser e exigiu CAPTCHA
- O modo `--no-headless` abre o browser para resolver CAPTCHA manualmente, mas não é prático para uso automatizado
- Após resolver CAPTCHA uma vez, o estado é salvo em `browser-state.json` e funciona

## Solução Criada: Wrapper com Fallback

Criado `scripts/google_search.py` com 3 camadas:

1. **DuckDuckGo (ddgs)** — funciona sem CAPTCHA, mais confiável
2. **Bing (web scraping)** — fallback funcionando via urllib
3. **Google Playwright** — último recurso (requer CAPTCHA manual)

### Arquivos criados
- `skills/devops/google-search-playwright/SKILL.md` — documentação completa
- `scripts/google_search.py` — wrapper com fallback (3 fontes)
- `config.yaml` — atualizado com MCP server `google-search`

### Resultados dos testes
- `google_search.py "climate change" --fallback-only` → ✅ Retornou resultados do Bing em 0.8s
- `google_search.py "noticias Brasil" --fallback-only` → ✅ Retornou resultados do Bing
- DuckDuckGo (ddgs) funciona mas retornou resultados irrelevantes para algumas queries

## Conclusão

A skill foi instalada e testada. O Google Playwright **não funciona de forma automatizada** devido ao CAPTCHA. A solução prática é o wrapper `google_search.py` que usa DuckDuckGo e Bing como fontes principais.

**Recomendação**: Para buscas Google de verdade, o melhor é:
1. Kimi WebBridge (navegador real, sem detecção)
2. DuckDuckGo via ddgs (já funciona)
3. Serper API (2500 buscas grátis/mês, mas requer API key)

## Observações sobre o Clima
- Senhor confirmou que 16°C é frio para ele (distonia piora)
- Limite prático de alerta ajustado para 16°C (era 15°C)
- Recomendação: cobertor quente ou aquecedor quando temperatura <= 16°C

## Próximos passos
- [ ] Resolver CAPTCHA do Google Playwright manualmente (uma vez só)
- [ ] Alternativa: configurar Serper API key para buscas Google de verdade
- [ ] Considerar remover o Playwright se não for usado (liberar ~200MB)
