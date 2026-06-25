---
title: Saúde dos Scripts — Projeto Atena
created: 2026-05-20 10:00:13
updated: 2026-05-20 10:00:13
type: query
tags: [automacao, testes, saude, manutencao]
---

# Saúde dos Scripts — Projeto Atena

> Gerado em: 2026-05-20 10:00:13

## Resumo

| Métrica | Valor |
|---------|-------|
| Total de scripts | 25 |
| Saudáveis | 20 |
| Com problemas | 5 |
| Nota média | 96/100 |
| Taxa de saúde | 80% |

## Status Geral

| Script | Nota | Status | Problemas |
|--------|------|--------|-----------|
| `ollama_chat.py` | 80 | ❌ | — |
| `pesquisa_web.py` | 80 | ❌ | — |
| `teste_ocr.py` | 80 | ❌ | 1 import(s) falharam: fitz |
| `teste_tts.py` | 80 | ❌ | 1 import(s) falharam: tts |
| `tts_fix.py` | 80 | ❌ | — |
| `analisador_arquitetura.py` | 100 | ✅ | — |
| `automacao_memoria.py` | 100 | ✅ | — |
| `backup_wiki.py` | 100 | ✅ | — |
| `busca_web.py` | 100 | ✅ | — |
| `cerebro_atena.py` | 100 | ✅ | — |
| `ensemble_modelos.py` | 100 | ✅ | — |
| `evolucao_continua.py` | 100 | ✅ | — |
| `gerador_skill.py` | 100 | ✅ | — |
| `monitor_distonia.py` | 100 | ✅ | — |
| `monitor_sistema.py` | 100 | ✅ | — |
| `monitor_tokens.py` | 100 | ✅ | — |
| `motor_evolucao.py` | 100 | ✅ | — |
| `raciocinar.py` | 100 | ✅ | — |
| `seguranca.py` | 100 | ✅ | — |
| `testador_scripts.py` | 100 | ✅ | — |
| `tts_fala.py` | 100 | ✅ | — |
| `tts_play.py` | 100 | ✅ | — |
| `tts_rapido.py` | 100 | ✅ | — |
| `tts_streaming.py` | 100 | ✅ | — |
| `verificar_atualizacoes.py` | 100 | ✅ | — |

## Imports Falhando

- **`teste_ocr.py`**: 1 import(s) falharam: fitz
- **`teste_tts.py`**: 1 import(s) falharam: tts

## Top 5 Scripts Mais Saudáveis

1. `analisador_arquitetura.py` — nota 100
2. `automacao_memoria.py` — nota 100
3. `backup_wiki.py` — nota 100
4. `busca_web.py` — nota 100
5. `cerebro_atena.py` — nota 100

## Scripts que Precisam de Atenção

1. `ollama_chat.py` — nota 80
2. `pesquisa_web.py` — nota 80
3. `teste_ocr.py` — nota 80
4. `teste_tts.py` — nota 80
5. `tts_fix.py` — nota 80


---

## Recomendações

2. **Instalar dependências faltando** para 2 script(s)
4. **Adicionar docstrings** em 3 script(s)

---

*Relatório gerado automaticamente por `testador_scripts.py`*
