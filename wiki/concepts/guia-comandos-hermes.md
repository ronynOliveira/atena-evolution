---
title: Guia de Comandos do Hermes Agent
created: 2026-05-20
updated: 2026-05-20
type: concept
tags: [hermes-agent, comandos, cli, referencia]
sources: []
confidence: high
---

# Guia de Comandos do Hermes Agent

> Ver também: [[hermes-agent]] (framework), [[guia-comando-goal]] (delegação)

## Comandos CLI Principais

### Chat e Sessão
```bash
hermes                          # Chat interativo
hermes chat -q "pergunta"       # Consulta única (não-interativo)
hermes --resume SESSION_ID      # Retomar sessão anterior
hermes --continue               # Retomar última sessão
```

### Configuração
```bash
hermes setup                    # Assistente de configuração
hermes model                    # Escolher modelo/provedor
hermes config                   # Ver configuração atual
hermes config edit              # Editar config.yaml
hermes config set KEY VAL       # Definir valor
hermes doctor                   # Verificar saúde do sistema
hermes status                   # Status dos componentes
```

### Ferramentas e Skills
```bash
hermes tools                    # Gerenciar ferramentas (interativo)
hermes tools list               # Listar todas as ferramentas
hermes tools enable NOME        # Habilitar toolset
hermes tools disable NOME       # Desabilitar toolset
hermes skills list              # Listar skills instaladas
hermes skills search BUSCA      # Buscar skills
hermes skills install ID        # Instalar skill
hermes skills update            # Atualizar skills
```

### Gateway (Mensageria)
```bash
hermes gateway run              # Iniciar gateway (primeiro plano)
hermes gateway install          # Instalar como serviço (auto-start)
hermes gateway start/stop       # Controlar serviço
hermes gateway restart          # Reiniciar
hermes gateway status           # Ver status
hermes gateway setup            # Configurar plataformas
```

### Cron Jobs
```bash
hermes cron list                # Listar jobs
hermes cron create "30m"        # Criar job (30 min, 2h, "0 9 * * *")
hermes cron edit ID             # Editar job
hermes cron pause/resume ID     # Pausar/retomar
hermes cron run ID              # Executar agora
hermes cron remove ID           # Remover
hermes cron status              # Status do scheduler
```

### Sessões
```bash
hermes sessions list            # Listar sessões
hermes sessions browse          # Navegador interativo
hermes sessions export ARQUIVO  # Exportar para JSONL
hermes sessions rename ID NOME  # Renomear
hermes sessions delete ID       # Deletar
```

### Perfis
```bash
hermes profile list             # Listar perfis
hermes profile create NOME      # Criar perfil
hermes profile use NOME         # Definir padrão
hermes profile delete NOME      # Deletar
```

### Outros
```bash
hermes update                   # Atualizar Hermes
hermes insights                 # Análise de uso
hermes mcp list                 # Listar MCP servers
hermes mcp add NOME             # Adicionar MCP server
hermes auth add                 # Adicionar credencial
hermes auth list                # Listar credenciais
```

## Comandos de Sessão (Slash Commands)

### Durante o chat interativo:

**Sessão:**
- `/new` ou `/reset` — Nova sessão
- `/retry` — Reenviar última mensagem
- `/undo` — Desfazer última troca
- `/title NOME` — Nomear sessão
- `/compress` — Comprimir contexto
- `/stop` — Parar processos
- `/rollback [N]` — Restaurar checkpoint
- `/goal [texto]` — Definir objetivo permanente

**Configuração:**
- `/model [nome]` — Mudar modelo
- `/reasoning [nível]` — Nível de raciocínio
- `/verbose` — Modo verboso
- `/yolo` — Pular aprovação de comandos

**Ferramentas:**
- `/tools` — Gerenciar ferramentas
- `/skills` — Buscar/instalar skills
- `/skill NOME` — Carregar skill
- `/reload-skills` — Re-escanear skills
- `/reload` — Recarregar .env
- `/cron` — Gerenciar cron jobs

**Gateway:**
- `/approve` — Aprovar comando pendente
- `/deny` — Negar comando
- `/restart` — Reiniciar gateway
- `/platforms` — Status das plataformas

**Utilitários:**
- `/branch` — Ramificar sessão
- `/history` — Ver histórico
- `/save` — Salvar conversa
- `/copy` — Copiar resposta
- `/help` — Ver comandos
- `/usage` — Uso de tokens
- `/status` — Info da sessão
- `/quit` ou `/exit` — Sair

## Modelos Disponíveis (20+ provedores)

### Gratuitos:
- **OpenRouter Free:** 28 modelos (deepseek-v4-flash, qwen3-coder, llama-3.3-70b, etc.)
- **Ollama Local:** 9 modelos instalados (qwen3:8b, gemma4:e4b, hermes3:8b, etc.)

### Configurados:
- **Ollama:** 8 modelos locais (ilimitado, grátis)
- **OpenRouter:** modelo principal (owl-alpha)

## Toolsets Disponíveis

| Toolset | Função |
|---|---|
| `web` | Busca web |
| `browser` | Automação de navegador |
| `terminal` | Comandos shell |
| `file` | Leitura/escrita de arquivos |
| `code_execution` | Execução Python |
| `vision` | Análise de imagens |
| `tts` | Texto para fala |
| `memory` | Memória persistente |
| `delegation` | Subagentes |
| `cronjob` | Tarefas agendadas |
| `todo` | Lista de tarefas |
| `session_search` | Busca em sessões |

## Ver também
- [[hermes-agent]]
- [[ambiente-tecnico]]
- [[plano-contingencia]]
