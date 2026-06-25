---
title: Kimi WebBridge — Guia de Uso
created: 2026-05-21
updated: 2026-05-21
type: entity
tags: [kimi, webbridge, ferramenta, browser, cdp]
---

# Kimi WebBridge

Extensão do Chrome que permite controle do navegador via CDP (Chrome DevTools Protocol).

## Status
- **Versão**: v1.9.4 (extensão v1.9.7)
- **Porta**: 10086
- **Conectado**: Sim
- **Uptime**: ~40min

## Como Usar

O Kimi WebBridge controla o Chrome. Para interagir com o Kimi AI, use o **browser tool** do Hermes:

1. Navegar: `browser_navigate(url="https://kimi.moonshot.cn")`
2. Snapshot: `browser_snapshot()`
3. Clicar no input: `browser_click(ref="contenteditable/textarea")`
4. Digitar: `browser_type(ref="...", text="seu prompt")`
5. Enviar: `browser_press(key="Enter")`
6. Aguardar 5-10s
7. Capturar resposta: `browser_snapshot()`

## Quando Usar

- Gerar código (alternativa ao Opencode/Freebuff)
- Tirar dúvidas técnicas complexas
- Pesquisa web via navegador real
- Análise de código
- Quando OpenRouter está rate-limited

## Vantagens
- Não consome tokens do OpenRouter
- Acesso gratuito ao Kimi AI (moonshot.cn)
- Navegador real (bypass CAPTCHA)
- Sem rate limit

## Ferramentas de Geração (Ordem de Prioridade)
1. **Ollama local** (qwen3:8b) — mais rápido, sem internet
2. **Kimi WebBridge** — gratuito, navegador real
3. **Opencode** — código local
4. **Freebuff** — código + pesquisa
5. **Gemini CLI** — pesquisa web

## Troubleshooting
- Extensão desconectou? → Reextender extensão no Chrome (ícone do Kimi)
- Porta 10086 fechada? → Reiniciar Chrome com extensão ativa
- Resposta vazia? → Aguardar mais tempo, Kimi pode ser lento

## Script
- `kimi_tool.py` — Módulo de integração com funções auxiliares
