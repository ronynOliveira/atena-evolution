---
title: Catálogo de Skills do Hermes
created: 2026-05-20
updated: 2026-05-20
type: entity
tags: [hermes-agent, skill, ferramenta, projeto-atena]
sources: [raw/hermes-memory-export.md]
confidence: high
---

# Catálogo de Skills do Hermes

## Registro migrado da memória do sistema do Hermes.

### Visão Geral
O Hermes Agent possui **83 skills** organizadas em **17 categorias**. Skills são carregáveis sob demanda — não ficam todas na memória ao mesmo tempo.

### Categorias e Quantidades

| Categoria | Qtd | Skills Principais |
|---|---|---|
| **autonomous-ai-agents** | 4 | claude-code, codex, hermes-agent, opencode |
| **creative** | 18 | hermes-identity, architecture-diagram, ascii-art, comfyui, excalidraw, p5js, pixel-art, sketch |
| **data-science** | 1 | jupyter-live-kernel |
| **devops** | 3 | kanban-orchestrator, kanban-worker, webhook-subscriptions |
| **email** | 1 | himalaya |
| **gaming** | 1 | pokemon-player |
| **github** | 5 | github-auth, github-code-review, github-issues, github-pr-workflow, github-repo-management |
| **mcp** | 2 | composio-mcp, native-mcp |
| **media** | 5 | gif-search, heartmula, songsee, spotify, youtube-content |
| **mlops** | 5 | dspy, huggingface-hub, llama-cpp, segment-anything-model, weights-and-biases |
| **note-taking** | 1 | obsidian |
| **productivity** | 10 | accessibility-toolkit, airtable, google-workspace, linear, maps, nano-pdf, notion, ocr-and-documents, powerpoint, voice-assistant |
| **red-teaming** | 2 | godmode, prompt-injection-defense |
| **research** | 5 | arxiv, blogwatcher, kimi-webbridge, llm-wiki, polymarket |
| **smart-home** | 1 | openhue |
| **software-development** | 13 | browser-cdp, browser-harness, hermes-agent-skill-authoring, plan, requesting-code-review, spike, subagent-driven-development, systematic-debugging, test-driven-development, writing-plans |
| **sem categoria** | 3 | atena-wiki, dogfood, yuanbao |

### Skills Mais Usadas no Projeto Atena
1. [[hermes-identity]] — persona e protocolo dialético
2. [[llm-wiki]] — wiki de conhecimento
3. [[obsidian]] — interface do wiki
4. [[kimi-webbridge]] — ponte para a Parceira da Nuvem
5. [[browser-cdp]] — controle do navegador
6. [[browser-harness]] — auto-healing de navegação
7. [[accessibility-toolkit]] — ferramentas de acessibilidade
8. [[atena-wiki]] — memória expandida do Projeto Atena
9. [[voice-assistant]] — assistente de voz completo
10. [[systematic-debugging]] — debug em 4 fases

### Skills Customizadas do Projeto Atena
- **atena-wiki** — memória expandida do Projeto Atena
- **hermes-identity** — persona do Batedor da Nuvem
- **voice-assistant** — pipeline microfone→STT→Hermes→TTS

### Regra de Uso
- Skills são carregadas sob demanda via `skill_view(name)`
- Sempre verificar se uma skill existe antes de executar uma tarefa
- Após usar uma skill, se encontrar problemas, atualizá-la com `skill_manage(action='patch')`
- Skills customizadas do Projeto Atena têm prioridade

## Ver também
- [[hermes-agent]]
- [[diretivas-acessibilidade]]
- [[projetos-pendentes]]
