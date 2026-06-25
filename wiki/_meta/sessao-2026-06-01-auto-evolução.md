# Sessão de Auto-Evolução — 01/06/2026

## Data
2026-06-01

## Gatilho
Solicitação do Senhor Robério: "koldi, se autoatualize por favor"

## Diagnóstico Inicial
- Gateway rodando (PID 2188, 18 jobs ativos)
- Hermes v0.15.1 (53 commits atrás da última versão)
- Ollama online (6 modelos disponíveis)
- koldi-computer-use plugin criado na sessão anterior
- Wiki com 50+ páginas, 2 commits à frente da origin

## Problemas Identificados e Corrigidos

### 1. Plugin antigo koldi-browser desativado
- **Problema**: koldi-browser (9 tools) e koldi-computer-use (16 tools) coexistindo — risco de conflito
- **Ação**: Diretório renomeado para koldi-browser.desativado
- **Config**: `# koldi-browser desativado` comentado no config.yaml
- **Status**: ✅ Resolvido

### 2. Bug de locale no monitor_sistema.py
- **Problema**: float() falhava com separador decimal virgula (pt-BR), resultando em monitor silenciosamente quebrado
- **Ação**: Adicionada função parse_num() que trata vírgulas antes da conversão
- **Status**: ✅ Corrigido

### 3. Wiki com mudanças pendentes
- **Problema**: 2 arquivos modificados sem commit
- **Ação**: git add -A && git commit -m "auto-evolucao: atualizacao 2026-06-01_0805"
- **Status**: ✅ Commit feito (1a409d5)

### 4. Ollama
- **Status**: ✅ Rodando normalmente, qwen3:8b e gemma4:e2b disponíveis

### 5. Hermes update bloqueado
- **Problema**: hermes.exe rodando (PID 3964), Windows bloqueia overwrite
- **Ação**: Requer restart completo do Hermes para aplicar
- **Status**: ⏳ Pendente (necessita reinicialização manual)

### 6. Motor de auto-evolução
- **Problema**: Timeout ao executar motor_evolucao.py (60s)
- **Status**: ⏳ Cron job roda a cada 24h (próxima: 16:22)

## Lições
1. Hermes update precisa de gateway parado — programar para reinicialização
2. monitor_sistema.py vulnerável a locale pt-BR — parse_num() como padrão em novos scripts
3. Auto-evolução manual vs automática: motor_evolucao.py é pesado, melhor deixar para o cron
