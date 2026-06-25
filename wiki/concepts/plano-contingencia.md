---
title: Plano de Contingência — Tokens e Modelos
created: 2026-05-20
updated: 2026-05-20
type: concept
tags: [contingencia, modelos, tokens, plano-b, plano-c, ia]
sources: []
confidence: high
---

# Plano de Contingência — Tokens e Modelos

> Ver também: [[hermes-agent]] (providers), [[ambiente-tecnico]] (infraestrutura)

## Situação Atual
- **Modelo principal:** openrouter/owl-alpha (via OpenRouter)
- **Tokens:** limitados por quota/custo
- **Risco:** tokens acabarem → OWL fica sem funcionar

## Plano B — Fallback Imediato (OpenRouter Free)

### Modelos gratuitos disponíveis no OpenRouter (28 total)
Ordenados por capacidade:

| Prioridade | Modelo | Contexto | Uso |
|---|---|---|---|
| 1 | `deepseek/deepseek-v4-flash:free` | 1M | Geral, tools |
| 2 | `qwen/qwen3-coder:free` | 1M | Coding, tool use |
| 3 | `nvidia/nemotron-3-super-120b-a12b:free` | 1M | Geral, tools |
| 4 | `openai/gpt-oss-120b:free` | 131K | Geral, tools |
| 5 | `meta-llama/llama-3.3-70b-instruct:free` | 131K | Geral |
| 6 | `minimax/minimax-m2.5:free` | 205K | Geral, tools |
| 7 | `z-ai/glm-4.5-air:free` | 131K | Geral, tools |

**Limite:** ~20 req/min no tier gratuito

### Como ativar
Editar `~/.hermes/config.yaml`:
```yaml
model:
  default: openrouter/owl-alpha
  fallbacks:
    - deepseek/deepseek-v4-flash:free
    - qwen/qwen3-coder:free
    - openai/gpt-oss-120b:free
```

## Plano C — Modelos Locais (Ollama)

### Modelos instalados atualmente
| Modelo | VRAM | Status |
|---|---|---|
| gemma4:e4b | ~4GB | ✅ Instalado |
| hermes3:8b | ~6GB | ✅ Instalado |
| gemma4:e2b | ~2GB | ✅ Instalado |
| deepseek-r1:8b | ~6GB | ✅ Instalado |
| qwen3:8b | ~6GB | ✅ Instalado |
| gemma3:12b | ~8GB | ✅ Instalado |
| qwen3:4b | ~4GB | ✅ Instalado |
| gemma3:4b | ~4GB | ✅ Instalado |

### Modelos recomendados para instalar (melhor qualidade)
| Modelo | VRAM | Comando | Prioridade |
|---|---|---|---|
| qwen3:30b | ~18GB | `ollama pull qwen3:30b` | Alta |
| qwen3-coder:30b | ~18GB | `ollama pull qwen3-coder:30b` | Alta |
| gemma4:26b | ~16GB | `ollama pull gemma4:26b` | Média |

### Como ativar
```yaml
model:
  provider: ollama-launch
  default: qwen3:8b  # ou modelo local preferido
```

## Plano D — APIs Pagas (Custo-Benefício)

### Mais baratos por qualidade
| Modelo | Input/1M | Output/1M | Provedor |
|---|---|---|---|
| DeepSeek V4 Flash | $0.14 | $0.28 | DeepSeek |
| Qwen3 235B | $0.07 | $0.10 | Alibaba |
| Mistral Nemo OSS | $0.02 | $0.04 | Mistral |
| GPT-5 Nano | $0.05 | $0.40 | OpenAI |
| DeepSeek V4 | $0.28 | $0.89 | DeepSeek |
| Claude Haiku 4.6 | $0.80 | $4.00 | Anthropic |

## Estratégia de Cascata (Fallback Automático)

```
1. openrouter/owl-alpha (principal)
   ↓ quota excedida
2. deepseek-v4-flash:free (OpenRouter free)
   ↓ rate limit
3. qwen3:8b (Ollama local)
   ↓ modelo indisponível
4. gemma4:e4b (Ollama local, mais leve)
   ↓ tudo falhou
5. Modo degradado: respostas simples sem LLM
```

## Ações Imediatas Recomendadas

1. ✅ Configurar fallbacks no config.yaml
2. ✅ Instalar qwen3:30b no Ollama (melhor modelo local)
3. ✅ Testar fallback automático
4. ⏳ Configurar alerta de uso de tokens
5. ⏳ Criar script de monitoramento de quota

## Ver também
- [[hermes-agent]]
- [[ambiente-tecnico]]
- [[projetos-pendentes]]
