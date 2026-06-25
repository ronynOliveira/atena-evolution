---
title: Habilidades Aprendidas
created: 2026-05-19
updated: 2026-05-19
type: entity
tags: [habilidades, aprendizado, skills, conhecimento, memoria]
sources: []
confidence: high
---

# Habilidades Aprendidas

Registro central de todas as habilidades, conhecimentos e procedimentos que o Hermes adquiriu. Este documento é a **memória operacional** — consulta antes de qualquer tarefa nova.

> **Regra**: Cada nova habilidade aprendida, erro corrigido ou workflow descoberto DEVE ser registrado aqui.

## Categorias

### 1. Navegação e Pesquisa
- **Chrome CDP** — Controlar Chrome via porta 9222. Matar Chrome antes de reiniciar (Google bloqueia login via CDP).
- **Kimi WebBridge** — Ponte para Gemini na porta 10086. Usar para pesquisa e conversa com a [[parceira-da-nuvem]].
- **Pesquisa web** — `web_search` indisponível. Usar browser + DuckDuckGo/Google ou `tools/pesquisa_web.py` via Gemini CLI.
- **Browser harness** — Auto-healing quando página quebra.

### 2. Áudio e Acessibilidade
- **TTS Windows** — edge-tts → ffmpeg (MP3→WAV) → PowerShell SoundPlayer. NUNCA ffplay/OGG.
- **Sensibilidade à luz** — Arquiteto tem dificuldade de ler terminal. SEMPRE falar primeiro, mostrar detalhes depois.
- **Distonia** — Arquiteto digita com dificuldade. Minimizar input manual, maximizar output por áudio.

### 3. Wiki e Memória
- **Obsidian vault** — `C:\Users\dell-\wiki`. Usar como segundo cérebro.
- **LLM Wiki (Karpathy)** — 3 camadas: raw → entities/concepts → queries/comparisons. Wikilinks para conectar.
- **Padrão de páginas** — YAML frontmatter (title, created, updated, type, tags, sources, confidence).
- **Lint** — Verificar órfãos e broken links após mudanças.

### 4. Desenvolvimento
- **Atena v5.3** — Backend 36 testes OK, frontend OK, Tauri OK, porta 8081.
- **Git** — Usar git-bash. Commits, branches, PRs via `gh` CLI.
- **Testes** — pytest com xdist para paralelo.

### 5. Windows + Shell
- **git-bash (MSYS)** — Shell padrão. Sintaxe POSIX, NÃO PowerShell.
- **Caminhos** — MSYS `/c/Users/...` ou Windows `C:\Users\...` ambos funcionam.
- **PowerShell** — Só para SoundPlayer e scripts `.ps1` dedicados. Hash tables quebram no git-bash.
- **Hermes Desktop** — v0.4.2 em `C:\Users\dell-\AppData\Local\Programs\hermes-desktop`.

### 6. Modelos e IA
- **Ollama** — 8 modelos locais, uso ilimitado.
- **OpenRouter** — 29 modelos free. Modelo atual: `openrouter/owl-alpha`.
- **Gemini (Parceira)** — Acessada via Kimi WebBridge. Sparring partner dialético.
- **Composio MCP** — Instalado mas sem API key.

### 7. Ferramentas Hermes
- **memory tool** — Memória persistente (40k chars). Salvar fatos duráveis.
- **session_search** — Buscar em sessões passadas.
- **cronjob** — Tarefas agendadas autônomas.
- **delegate_task** — Subagentes paralelos (até 3).
- **execute_code** — Python com acesso a ferramentas Hermes.
- **todo** — Gerenciar lista de tarefas da sessão.

## Procedimentos de Emergência

| Situação | Ação |
|---|---|
| Chrome CDP não conecta | Matar Chrome completamente, reiniciar com `--remote-debugging-port=9222` |
| Kimi WebBridge caiu | Verificar se porta 10086 está aberta, reiniciar serviço |
| TTS falha | Verificar edge-tts → ffmpeg → SoundPlayer pipeline |
| Memória cheia | Mover conteúdo antigo para wiki, limpar memória |
| Gateway UnicodeDecodeError | Cosmético — usar `cron status` em vez de logs |

## Relações

- [[hermes-agent]] — o agente que usa estas habilidades
- [[projeto-atena]] — o ecossistema
- [[llm-wiki]] — metodologia de memória
- [[gnostico-construtor]] — a persona que aplica estas habilidades
