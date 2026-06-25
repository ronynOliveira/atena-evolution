---
title: Ambiente Técnico do Arquiteto
created: 2026-05-20
updated: 2026-05-20
type: entity
tags: [hermes-agent, ferramenta, ambiente-tecnico]
sources: [raw/hermes-memory-export.md]
confidence: high
---

# Ambiente Técnico do Arquiteto

## Registro migrado da memória do sistema do Hermes.

### Hardware
- **Máquina:** Dell i5
- **SO:** Windows 11 Pro
- **RAM:** 16 GB

### Software Base
- **Shell:** git-bash (MSYS2)
- **Hermes:** `C:\Users\dell-\AppData\Local\hermes`
- **Hermes Desktop:** v0.4.2 em `C:\Users\dell-\AppData\Local\Programs\hermes-desktop`
- **Python:** `C:\Users\dell-\AppData\Local\Programs\Python\Python311\python.exe`

### Reda e Conectividade
- **Chrome CDP:** porta 9222 (matar Chrome antes de reiniciar — Google bloqueia login via CDP)
- **Kimi WebBridge:** porta 10086 (controle do Chrome para pesquisa e conversa com Gemini)
- **Gateway Hermes:** rodando

### Modelos de IA Disponíveis
- **Ollama local:** 8 modelos (ilimitado)
- **OpenRouter free:** 29 modelos
- **Gemini CLI:** via pesquisa_web.py e Kimi WebBridge
- **OpnCode:** v1.15.0, modelo `opencode/qwen3.6-plus-free`

### Ferramentas Instaladas
- Composio MCP (falta API key)
- Chrome CDP
- Kimi WebBridge

### Pitfalls Conhecidos
1. PowerShell hash tables quebram no git-bash — usar `-File .ps1`
2. Gateway UnicodeDecodeError é cosmético — usar `cron status`
3. `web_search` indisponível — usar browser/curl
4. `python` no git-bash pode não encontrar módulos — usar caminho completo do Python

### Caminhos Importantes
- **TTS scripts:** `C:\Users\dell-\AppData\Local\hermes\tools\`
- **Wiki:** `C:\Users\dell-\wiki\`
- **Hermes skills:** `C:\Users\dell-\AppData\Local\hermes\skills\`

## Ver também
- [[diretivas-acessibilidade]]
- [[hermes-agent-config]]
- [[projeto-atena]]


## Atualização 2026-06-02

- identity_manager.py criado (CRUD + anti-drift v4.2)
- subagent_runner.py criado (orquestração multi-terminal)
- Composio: Gmail, GitHub, Google Calendar conectados
- MCP Composio local em investigação (rota 404)
