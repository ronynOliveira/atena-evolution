---
title: TTS Windows — Solução Definitiva
created: 2026-05-20
updated: 2026-05-20
type: concept
tags: [tts, ferramenta, acessibilidade, hermes-agent]
sources: [raw/hermes-memory-export.md]
confidence: high
---

# TTS Windows — Solução Definitiva

> Ver também: [[diretivas-acessibilidade]] (TTS obrigatório), [[fala-assistida-koldi]] (sistema de fala)

## Registro migrado da memória do sistema do Hermes.

### Problema
O git-bash/MSYS2 não tem drivers de áudio. Nenhum player funciona nativamente:
- ffplay com OGG/Opus → falha silenciosamente
- VLC → não funciona no MSYS2
- pulseaudio → não disponível
- sox → não disponível
- mpv → não disponível

### Solução Definitiva (confirmada em 18/05/2026)
Usar Python do Windows nativo com pipeline em três etapas:

1. **edge-tts** gera MP3 a partir do texto
2. **ffmpeg** converte MP3 → WAV (44100Hz, stereo)
3. **PowerShell Media.SoundPlayer** toca o WAV

### Script Principal
- **Local:** `C:\Users\dell-\AppData\Local\hermes\tools\tts_fala.py`
- **Uso:** `python tools/tts_fala.py "texto aqui"`
- **Voz padrão:** pt-BR-FranciscaNeural

### Regras de Uso
- **SEMPRE** usar este script para TTS
- **NUNCA** usar `text_to_speech` nativo do Hermes (gera OGG que não toca)
- **NUNCA** usar `ffplay` (falha silenciosamente)
- Textos longos devem ser **divididos em partes curtas** (máx ~15s cada)
- O script usa `PlaySync()` que bloqueia até o áudio terminar

### Scripts Relacionados
- `tts_rapido.py` — versão rápida
- `tts_streaming.py` — versão streaming
- `tts_fix.py` — correções
- `tts_play.py` — player alternativo
- `tts_windows.py` — versão com pygame (alternativa)

### Vozes Disponíveis
- **Principal:** pt-BR-FranciscaNeural
- Configurável via parâmetro `--voice`

## Ver também
- [[diretivas-acessibilidade]]
- [[hermes-agent]]
- [[ambiente-tecnico]]
