---
title: Status das Habilidades Faltantes — Atualização
created: 2026-05-20
updated: 2026-05-20
type: query
tags: [automacao, evolucao, habilidades, status]
sources: [_meta/auto-analise-owl.md]
confidence: high
---

# Status das Habilidades Faltantes — Atualização 20/05/2026

## Já Resolvidas ✅

| Habilidade | Status | Detalhes |
|---|---|---|
| gh CLI | ✅ Instalado | v2.92, aguardando GITHUB_TOKEN |
| Backup wiki | ✅ Funcionando | Git init + 28 arquivos commitados |
| Monitor sistema | ✅ Ativo | CPU 22%, RAM/disco/rede OK, cron 6h |
| OCR/PyMuPDF | ✅ Testado | Extração de texto PDF funcionando |

## Aguardando Configuração do Arquiteto ⏳

| Habilidade | O que falta | Como configurar |
|---|---|---|
| **GITHUB_TOKEN** | Token do GitHub | github.com/settings/tokens → setx GITHUB_TOKEN "token" |
| **Telegram Bot** | Token do BotFather | Criar bot @BotFather → adicionar token ao config.yaml |
| **Composio MCP** | API key | composio.dev → obter key → configurar |
| **Gateway Hermes** | Iniciar serviço | `hermes gateway install` (auto-start no login) |

## Já Instalados, Precisam de Configuração 🔧

| Habilidade | Status | Próximo passo |
|---|---|---|
| Whisper STT | ✅ Instalado (faster-whisper + openai-whisper) | Testar pipeline de voz |
| PyAudio | ✅ Instalado | Verificar microfone |
| sounddevice | ✅ Instalado | Verificar dispositivos de áudio |
| Composio MCP | ✅ Instalado (v0.13.1) | Obter API key |

## Próximas Ações do OWL

1. **Imediato:** Pedir GITHUB_TOKEN ao Arquiteto
2. **Imediato:** Pedir token do Telegram Bot ao Arquiteto
3. **Imediato:** Pedir API key do Composio ao Arquiteto
4. **Após tokens:** Configurar gateway e iniciar
5. **Após gateway:** Testar acesso pelo celular

## Ver também
- [[automacao-atena]]
- [[projetos-pendentes]]
- [[hermes-agent]]
