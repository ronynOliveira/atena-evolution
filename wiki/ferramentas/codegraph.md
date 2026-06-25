# CodeGraph

**Status:** Instalado e configurado ✅
**Versão:** v0.9.4
**Instalação:** `C:\Users\dell-\AppData\Local\codegraph\current\`
**Licença:** MIT

## O que é

CodeGraph cria um grafo de conhecimento pré-indexado do código para agentes de IA. Suporta Hermes Agent, Claude Code, Codex, Cursor e OpenCode. Reduz tokens em ~35% e tool calls em ~70%.

## Índices Ativos

### Wiki (C:\Users\dell-\wiki)
- **89 arquivos indexados**
- 3.581 nós, 3.471 arestas
- Indexado em 2.4s

### Hermes Tools (C:\Users\dell-\AppData\Local\hermes\tools)
- **57 arquivos indexados**
- 1.262 nós, 2.108 arestas
- Indexado em 1.1s

## Comandos Úteis

```bash
# Executar (via cmd)
cmd //c "C:\Users\dell-\AppData\Local\codegraph\current\bin\codegraph.cmd" <comando>

# Inicializar em um projeto
cd /c/caminho/do/projeto
cmd //c "C:\Users\dell-\AppData\Local\codegraph\current\bin\codegraph.cmd" init -i

# Buscar símbolos
cmd //c "C:\Users\dell-\AppData\Local\codegraph\current\bin\codegraph.cmd" query <termo>

# Ver status do índice
cmd //c "C:\Users\dell-\AppData\Local\codegraph\current\bin\codegraph.cmd" status

# Build context para tarefa
cmd //c "C:\Users\dell-\AppData\Local\codegraph\current\bin\codegraph.cmd" context <descrição da tarefa>

# Análise de impacto
cmd //c "C:\Users\dell-\AppData\Local\codegraph\current\bin\codegraph.cmd" impact <símbolo>
```

## MCP Server

Configurado automaticamente no `config.yaml` do Hermes Agent. Ativo após reiniciar a sessão do Hermes (`/reset`).

## Notas Técnicas

- PATH adicionado pelo installer, mas precisa reiniciar terminal para pegar
- No bash MSYS, usar `cmd //c` com path completo
- Flag de target para Hermes é `-t hermes`, não `-t hermes-agent`
- Usa Node.js próprio empacotado (não precisa ter Node instalado)
- Backend: SQLite com WAL
- Data de instalação: 25/05/2026