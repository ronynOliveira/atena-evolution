# Auto-Análise de Habilidades do Agente Koldi
**Data:** 2026-06-01  
**Versão do inventário:** baseada em `skills_list` (130 skills)  
**Escopo:** comparativo com necessidades comuns de assistentes técnicos, acessibilidade, escrita e monitoramento

---

## 1. Skills Instaladas (Categoria + Nome + Descrição)

### 1.1 autonomous-ai-agents (5 skills)
- `claude-code` — Delegação de codificação para Claude Code CLI (features, PRs).
- `codex` — Delegação de codificação para OpenAI Codex CLI (features, PRs).
- `hermes-agent` — Configuração, extensão e contribuição ao Hermes Agent.
- `kanban-codex-lane` — Worker Kanban executando Codex CLI como lane isolada.
- `opencode` — Delegação de codificação para OpenCode CLI (features, PR review).

### 1.2 creative (22 skills)
- `ai-assistant-persona` — Framework para identidade, personalidade e modos de interação.
- `architecture-diagram` — Diagramas de arquitetura SVG/nuvem/infra como HTML.
- `ascii-art` — ASCII art via pyfiglet, cowsay, boxes, image-to-ascii.
- `ascii-video` — Conversão de vídeo/áudio para ASCII MP4/GIF colorido.
- `auto-evolucao` — Sistema de auto-evolução do OWL com freebuff/OpenCode/Gemini CLI.
- `baoyu-article-illustrator` — Ilustrações para artigos com consistência de estilo/paleta.
- `baoyu-comic` — Quadrinhos educacionais/biográficos/tutoriais.
- `baoyu-infographic` — Infográficos com 21 layouts × 21 estilos.
- `claude-design` — Protótipos HTML (landing, deck, landing page).
- `comfyui` — Geração de imagem/vídeo/áudio com ComfyUI (nodes/models/workflows).
- `design-md` — Autoria/validação/exportação de DESIGN.md (Google token spec).
- `excalidraw` — Diagramas JSON no estilo 'hand-drawn' (arch, flow, seq).
- `frontend-design` — Design de UI/UX frontend com disciplina tipográfica/layout.
- `frontend-skill` — Landing pages/websites/UIs com composição contida.
- `hermes-identity` — Persona, modos de interação e metaprompts do Projeto Atena.
- `humanizer` — Humanização de texto: remover AI-ismos e adicionar voz real.
- `ideation` — Geração de ideias de projeto via restrições criativas.
- `manim-video` — Animações matemáticas/algorítmicas 3Blue1Brown-style.
- `p5js` — Sketches p5.js (gen art, shaders, interativo, 3D).
- `pixel-art` — Pixel art com paletas de época (NES, Game Boy, PICO-8).
- `popular-web-designs` — 54 sistemas de design reais (Stripe, Linear, Vercel) como HTML/CSS.
- `pretext` — Demos criativas no navegador com DOM-free text layout e text-as-geometry.
- `sketch` — Mockups HTML descartáveis: 2-3 variantes para comparação.
- `songwriting-and-ai-music` — Composição com Suno AI (lyrics + tags).
- `touchdesigner-mcp` — Controle do TouchDesigner via MCP (operators, params, Python).

### 1.3 data-science (1 skill)
- `jupyter-live-kernel` — Python iterativo via kernel Jupyter vivo.

### 1.4 devops (30 skills)
- `academic-research` — Skill consolidada: arxiv + web-search-extract + atena-integrated-research + busca-web.
- `adaptive-light-filter` — Filtro de luz azul adaptativo (hora/temperatura/luminosidade).
- `auto-fetch` — Coleta periódica de dados de fontes conectadas para contexto Hermes.
- `cofre-koldi` — Cofre criptografado AES-256 com senha mestra e PBKDF2.
- `distonia-health-monitor` — Monitoramento de saúde com alertas ambientais para distonia.
- `google-search-playwright` — Busca Google real via Playwright Chromium headless.
- `implementing-aes-encryption-for-data-at-rest` — Implementação AES-256-GCM.
- `implementing-end-to-end-encryption-for-messaging` — E2EE simplificado via CLI/MCP.
- `implementing-secret-scanning-with-gitleaks` — Detecção de secrets com gitleaks + hooks/CI.
- `kanban-orchestrator` — Orquestrador Kanban (playbook de decomposição + anti-tentação).
- `kanban-worker` — Worker Kanban: pitfalls, exemplos, casos extremos.
- `koldi-computer-use-plugin` — Controle unificado de navegador (Kimi WebBridge + Chrome CDP).
- `koldi-hardening` — Varredura de segurança, correção de permissões, detecção de keys expostas.
- `memory-care` — Memory Tree hierárquico com scoring e consolidação automática.
- `memory-decay-queue` — Decay exponencial + fila assíncrona de memórias (TTL/lambda).
- `memory-pipeline` — Wrapper para gravação de memórias (queue async + fallback sync).
- `metacog-tools` — Ferramentas metacognitivas (estimador de confiança + poda de contexto).
- `owl-tts-unified` — Text-to-Speech unificado (edge-tts + ffmpeg + PowerShell).
- `reliability-tools` — Confiabilidade: detector de falhas em logs + checkpoints + retomada.
- `sensory-overload-alert` — Detecção de sobrecarga sensorial com sugestão de pausas.
- `subagentes` — Sistema de subagentes especializados (monitor-distonia, busca-web, etc.).
- `system-health-monitor` — Monitoramento proativo de disco, processos, gateway, cron.
- `token-juice` — Compressão de contexto em pipeline (até 80% redução de tokens).
- `voice-navigation` — Navegação por voz com confirmação (ideal para distonia).
- `webhook-subscriptions` — Webhook subscriptions: event-driven agent runs.

### 1.5 email (1 skill)
- `himalaya` — Email via terminal (IMAP/SMTP).

### 1.6 gaming (1 skill)
- `pokemon-player` — Automação de Pokemon via emulador headless + RAM reads.

### 1.7 github (6 skills)
- `codebase-inspection` — Inspeção de codebase (pygount: LOC, linguagens, ratios).
- `github-auth` — Autenticação GitHub (HTTPS tokens, SSH keys, gh CLI).
- `github-code-review` — Code review via gh or REST.
- `github-issues` — Issues: triage, labels, assignees via gh/REST.
- `github-pr-workflow` — PR lifecycle: branch/commit/open/CI/merge.
- `github-repo-management` — Gerenciamento de repositórios, remotos, releases.

### 1.8 mcp (4 skills)
- `composio-mcp` — Conexão a 500+ serviços/APIs via MCP.
- `mcp-integration` — Integração de servidores MCP (stdio/HTTP).
- `native-mcp` — Cliente MCP nativo para conexão/registro de tools.
- `zapier-mcp` — Conexão a 9k+ apps via Zapier hosted MCP.

### 1.9 media (5 skills)
- `gif-search` — Busca/download GIFs Tenor via curl + jq.
- `heartmula` — Geração de músicas Suno-like via lyrics + tags.
- `songsee` — Espectrogramas/features de áudio (mel, chroma, MFCC).
- `spotify` — Controle Spotify (play, search, queue, playlists).
- `youtube-content` — Transcrições do YouTube para summaries/threads/blogs.

### 1.10 mlops (6 skills)
- `ai-agent-self-evolution` — Framework de auto-evolução via reflexion-based memory.
- `dspy` — Programas declarativos LM, otimização de prompts, RAG.
- `huggingface-hub` — Hub CLI (search/download/upload modelos/datasets).
- `llama-cpp` — Inferência local GGUF + descoberta de modelos no HF Hub.
- `segment-anything-model` — Segmentação de imagem zero-shot (SAM).
- `weights-and-biases` — Rastreio de experimentos ML, sweeps, model registry.

### 1.11 note-taking (1 skill)
- `obsidian` — Leitura, busca, criação e edição de notas no vault Obsidian.

### 1.12 openclaw-imports (1 skill)
- `kimi-webbridge` — Controle do navegador real via Kimi WebBridge.

### 1.13 productivity (11 skills)
- `accessibility-toolkit` — Ferramentas de acessibilidade para deficiências motoras.
- `airtable` — API Airtable via curl (CRUD, filters, upserts).
- `google-workspace` — Gmail, Calendar, Drive, Docs, Sheets via gws/Python.
- `linear` — Gestão no Linear (issues, projects, teams via GraphQL).
- `maps` — Geocode, POIs, rotas e fusos via OpenStreetMap/OSRM.
- `nano-pdf` — Edição de PDFs via CLI (texto/typos/títulos).
- `notion` — Notion API + ntn CLI (pages, databases, markdown).
- `ocr-and-documents` — OCR de PDFs/scans (pymupdf, marker-pdf).
- `powerpoint` — Criação/edição de apresentações .pptx.
- `teams-meeting-pipeline` — Pipeline de resumo de reuniões Teams via Graph.
- `voice-assistant` — Pipeline de voz (mic → STT Whisper → Hermes → TTS Edge → speaker).

### 1.14 red-teaming (2 skills)
- `godmode` — Jailbreak LLMs (Parseltongue, GODMODE, ULTRAPLINIAN).
- `prompt-injection-defense` — Defesas contra prompt injection e adversarial prompts.

### 1.15 research (7 skills)
- `arxiv` — Busca arXiv por keyword, autor, categoria, ID.
- `atena-integrated-research` — Pesquisa multi-camadas (Web + Gemini + Kilo + Reflexion).
- `blogwatcher` — Monitor de blogs/feeds RSS/Atom via blogwatcher-cli.
- `busca-web` — Sistema de busca web multi-fonte (DDG, Bing, Google, cache, APIs).
- `llm-wiki` — Wiki interligada em markdown (estilo Karpathy LLM Wiki).
- `polymarket` — Query de mercados prediction (markets, prices, orderbooks).
- `web-search-extract` — Busca e extração web SEM APIs pagas (ddgs, trafilatura, selectolax).

### 1.16 smart-home (1 skill)
- `openhue` — Controle de luzes/cenas/quartos Philips Hue via OpenHue CLI.

### 1.17 software-development (23 skills)
- `12-factor-agents` — Princípios de design para agentes em produção.
- `browser-cdp` — Controle Chrome via CDP (sessão compartilhada com usuário).
- `browser-control` — Plugin Koldi Browser Control via CDP (daemon mode).
- `browser-harness` — Browser self-healing (auto-geração de funções faltantes).
- `cli-printing-press` — Templates de CLI/MCP server prontos para uso.
- `cloak-browser` — Automação stealth (fingerprinting, user-agent, desafios Cloudflare).
- `code-intelligence` — Inteligência de código (knowledge graphs, CodeGraph).
- `debugging-hermes-tui-commands` — Debug de TUI slash commands (Python/gateway/Ink).
- `free-llm-api` — Agregador de LLMs grátis (Ollama + OpenRouter free + fallback).
- `hermes-agent-skill-authoring` — Autorias de SKILL.md (frontmatter, validator, estrutura).
- `hermes-plugin-development` — Desenvolvimento de plugins Hermes (manifest, tools, hooks).
- `hermes-s6-container-supervision` — Supervisão via s6-overlay no Docker Hermes.
- `langgraph-orchestration` — Orquestração stateful de agentes (Python/TypeScript).
- `node-inspect-debugger` — Debug Node.js via --inspect + Chrome CDP.
- `openai-realtime-meeting` — Assistente de reunião em tempo real via OpenAI Realtime.
- `plan` — Modo plan: gera plano markdown sem execução.
- `reflexion-engine` — Motor de reflexão com memória compartilhada + roteamento por confiança.
- `requesting-code-review` — Pre-commit review (scan security, quality gates, auto-fix).
- `spike` — Experimentos descartáveis para validação pré-build.
- `subagent-driven-development` — Execução de planos via subagentes (2-stage review).
- `systematic-debugging` — Debugging 4 fases (compreender antes de corrigir).
- `test-driven-development` — TDD: RED-GREEN-REFACTOR.
- `writing-plans` — Escrita de planos de implementação (tarefas pequenas, paths, código).

---

## 2. Análise de Gaps

### 2.1 Cobertura existente
- **Acessibilidade:** parcial (accessibility-toolkit, voice-assistant, voice-navigation, sensory-overload-alert).
- **Escrita/Apresentação:** boa (humanizer, powerPoint, notion, google-workspace, ascii-art).
- **Monitoramento:** forte (system-health-monitor, reliability-tools, memory-care, memory-decay-queue, subagentes).
- **Técnico/DevOps:** muito forte (github, mcp, security, kanban, browser-control).

### 2.2 Habilidades faltantes

#### 2.2.1 Críticas

| Categoria | Habilidade Faltante | Motivo |
|-----------|----------------------|--------|
| **acessibilidade** | `leitor-de-tela-simulado` | Necessário para validar usabilidade por deficientes visuais mesmo sem JAWS/NVDA instalados. |
| **acessibilidade** | `automacao-teclado-avancada` | Falta suporte a Keyboard Klicks complexos + macros acessíveis persistentes (Windows). |
| **escrita** | `gramatica-e-estilo-avancado` | Sem skill dedicada a revisão gramatical, coesão, estilo e terminologia técnica consistente. |
| **monitoramento** | `monitoramento-de-rede-locale` | Não há skill para monitoramento de conectividade/ips experna; útil para diagnósticos de gateway. |
| **tecnico** | `assistente-de-api-design` | Não existe skill REST/gRPC/GraphQL que ajude a projetar schemas, contratos, versãoamento. |

#### 2.2.2 Importantes

| Categoria | Habilidade Faltante | Motivo |
|-----------|----------------------|--------|
| **acessibilidade** | `high-contrast-and-zoom-manager` | Ausência de skill para alternar temas de alto contraste e ajustar zoom global do Windows. |
| **acessibilidade** | `reader-for-dyslexia` | Falta suporte a síntese de voz com velocidade/fontes dislexia-friendly. |
| **escrita** | `documentacao-tecnica-automatica` | Ausência de skill que gera README, changelog, API docs a partir de código existente. |
| **escrita** | `traducao-e-localizacao` | Não há skill de tradução/localização técnica com manutenção de glossário. |
| **monitoramento** | `monitoramento-de-bateria-e-energia` | Ausência para dispositivos móveis/portáteis. |
| **monitoramento** | `central-de-logs-agregada` | Não há skill que agregue logs de múltiplas fontes em dashboard único. |
| **tecnico** | `proxy-e-interceptacao-http` | Falta skill para configurar/validar proxies, mitmproxy e auditoria HTTP. |
| **tecnico** | `gerenciador-de-secrets` | Apesar de cofre-koldi, falta integração com Windows Credential Manager/Keychain. |

#### 2.2.3 Desejáveis

| Categoria | Habilidade Faltante | Motivo |
|-----------|----------------------|--------|
| **acessibilidade** | `eye-tracking-automation` | Automação via controle ocular (caso hardware suporte). |
| **escrita** | `storytelling-para-dados` | Transforma dados brutos em narrativas (dataviz story, relatórios contáuticos). |
| **escrita** | `roteiro-de-video-e-podcast` | Roteirização e estruturação de conteúdo em vídeo/podcast. |
| **monitoramento** | `service-dependency-graph` | Mapeamento dinâmico de dependências para alertas de cascata. |
| **tecnico** | `schema-migration-manager` | Gerenciamento de migrations (SQL/NoSQL) integrado ao workflow. |
| **tecnico** | `chaos-engineering-lite` | Experimentos de resiliência (kill process, latency injection) em dev. |
| **utilidades** | `clipboard-manager-avancado` | Histórico rico, sync entre devices, OCR de clipboard. |

---

## 3. Prioridade de Implementação

### 3.1 Ordem sugerida (crítica → desejável)

1. **P0 — Crítica** · `gramatica-e-estilo-avancado`
   - Justificativa: escrita é core; revisão gramatical e estilo impacta diretamente a qualidade de toda saída.

2. **P0 — Crítica** · `leitor-de-tela-simulado`
   - Justificativa: validação objetiva de acessibilidade sem depender de ferramentas pagas.

3. **P0 — Crítica** · `monitoramento-de-rede-locale`
   - Justificativa: diagnosticar problemas de gateway/conectividade que afetam todos os MCPs.

4. **P1 — Importante** · `documentacao-tecnica-automatica`
   - Justificativa: reduz trabalho manual e mantém docs sincronizadas com código.

5. **P1 — Importante** · `automacao-teclado-avancada`
   - Justificativa: complementa voice-navigation e acessibilidade para distonia/RSI.

6. **P1 — Importante** · `gerenciador-de-secrets`
   - Justificativa: hardens o acesso a credenciais no Windows com Credential Manager.

7. **P2 — Desejável** · `high-contrast-and-zoom-manager`
   - Justificativa: acessibilidade visual rápida sem depender de NVDA/zoomText completo.

8. **P2 — Desejável** · `reader-for-dyslexia`
   - Justificativa: atendimento a público com dislexia.

9. **P2 — Desejável** · `proxy-e-interceptacao-http`
   - Justificativa: debug e auditoria HTTP para integrações MCP.

10. **P3 — Futuro** · demais itens desejáveis
    - Para iteração futura após consolidação das prioridades acima.

---

## 4. Comandos/Skills Sugeridos

### 4.1 Comandos sugeridos por gap

| Gap | Comando/Skill Sugerido | Exemplo de uso |
|-----|------------------------|----------------|
| `gramatica-e-estilo-avancado` | skill: `gramatica-e-estilo` | `Revisar gramática e estilo deste documento mantendo termos técnicos.` |
| `leitor-de-tela-simulado` | skill: `leitor-de-tela` | `Simular leitor de tela nesta página e reportar inconsistências ARIA.` |
| `monitoramento-de-rede-locale` | skill: `net-monitor` | `Monitorar rede local: gateway, DNS, latência e status das interfaces.` |
| `documentacao-tecnica-automatica` | skill: `doc-sync` | `Gerar README e changelog a partir deste repositório.` |
| `automacao-teclado-avancada` | skill: `keyboard-macros` | `Criar macro acessível para abrir Teams, mutar mic e gravar reunião.` |
| `gerenciador-de-secrets` | skill: `win-secrets` | `Armazenar/recuperar esta API key via Credential Manager.` |
| `high-contrast-and-zoom-manager` | skill: `high-contrast` | `Ativar alto contraste e zoom 150% até 18:00.` |
| `reader-for-dyslexia` | skill: `dyslexia-reader` | `Ler este relatório em voz lenta com fonte OpenDyslexic.` |
| `proxy-e-interceptacao-http` | skill: `http-proxy` | `Iniciar interceptador HTTP para debug de payload JSON.` |

### 4.2 PS1/PowerShell snippets úteis associados

```powershell
# Exemplo 1: credencial via Windows Credential Manager
cmdkey /generic:KoldiAPI /user:apikey /pass:*REMOVIDO*
cmdkey /list | findstr KoldiAPI

# Exemplo 2: alternância rápida de tema de alto contraste
$contrastMode = (Get-ItemProperty "HKCU:\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize").HighContrastMode
Set-ItemProperty "HKCU:\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize" HighContrastMode (1 - $contrastMode)
```

### 4.3 python UV scripts sugeridos

```bash
# Estrutura sugerida
uv run --with pyreadline3 scripts/generate_readme.py
uv run --with Pillow scripts/simulate_screen_reader.py
uv run --with requests scripts/net_monitor.py
```

### 4.4 Padrão de criação de skill

```bash
skill_manage action=create name='<novo-nome>' category='<categoria>' content='$(cat SKILL.md)'
```

---

## 5. Conclusão

- **Total de skills inventariadas:** 130
- **Cobertura forte:** DevOps, Software Development, Accessibility, Monitoring
- **Gaps mais relevantes:** gramática/estilo, leitor de tela simulado, monitoramento de rede, documentação técnico automática
- **Recomendação:** iniciar implementação por P0 (crítico) para elevar qualidade de escrita e validação de acessibilidade + confiabilidade de rede.
