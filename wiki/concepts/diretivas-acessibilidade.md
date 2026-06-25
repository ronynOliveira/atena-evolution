---
title: Memória do Sistema — Diretivas de Acessibilidade
created: 2026-05-20
updated: 2026-05-20
type: concept
tags: [hermes-agent, acessibilidade, protocolo, tts]
sources: [raw/hermes-memory-export.md]
confidence: high
---

# Memória do Sistema — Diretivas de Acessibilidade

## Registro migrado da memória do sistema do Hermes.

### Sensibilidade à Luz
O Arquiteto tem sensibilidade à luz e dificuldade para ler o terminal. **SEMPRE** usar TTS em todas as respostas. Falar em voz alta primeiro, depois mostrar detalhes no terminal como complemento. Nunca dizer "olhe para a tela" — descrever tudo verbalmente.

### Modelo de Comunicação
- **Arquiteto DIGITA, Hermes FALA**
- TTS obrigatório em TODAS as respostas
- Voz: pt-BR-FranciscaNeural
- Script correto: `python C:\Users\dell-\AppData\Local\hermes\tools\tts_fala.py "texto"`
- NUNCA usar `text_to_speech` nativo do Hermes (gera OGG que não toca no Windows)
- NUNCA usar `ffplay` (falha silenciosamente)
- Textos longos devem ser divididos em partes curtas (máximo 15 segundos cada)

### Acessibilidade Motora
- Distonia generalizada afeta fala e movimentos
- Minimizar input manual
- Maximizar controle por voz e automação
- Cada clique desnecessário é uma batalha a ser vencida
- NUNCA pedir para o Arquiteto falar

### Localização e Saúde
- **Localização**: Diadema, SP
- **Alerta de temperatura**: Temperatura fria (abaixo de 15°C) piora os sintomas da distonia
- **Monitor**: Script `monitor_tempo_diadema.py` verifica previsão a cada 12h via API Open-Meteo
- **Ações quando temperatura cair**: agasalhar-se, evitar exposição ao frio, manter-se aquecido
- **Latitude**: -23.6861 | **Longitude**: -46.6167

### Formato de Resposta
- Respostas estruturadas, não blocos de texto densos
- Listas e headers para fácil leitura
- Priorizar áudio sobre texto visual
- Sempre explicar o PORQUÊ de cada ação

### Verificação
- 2026-05-20: Script de TTS confirmado em `C:\Users\dell-\AppData\Local\hermes\tools\tts_fala.py`
- Pipeline: edge-tts → ffmpeg (MP3→WAV) → PowerShell Media.SoundPlayer

## Ver também
- [[hermes-agent-config]]
- [[tts-windows-pipeline]]
- [[hermes-identity]]
