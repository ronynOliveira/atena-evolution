---
title: Monitor de Temperatura — Diadema/SP
created: 2026-05-20
updated: 2026-05-20
type: concept
tags: [saude, distonia, temperatura, diadema, monitoramento]
sources: []
confidence: high
---

# Monitor de Temperatura — Diadema/SP

> Ver também: [[distonia-generalizada]] (condição), [[diretivas-acessibilidade]] (saúde)

## Contexto
O Senhor Robério mora em **Diadema, SP** e tem distonia generalizada. Temperaturas frias (abaixo de 15°C) pioram os sintomas. Por isso, foi criado um monitor automático de previsão do tempo.

## Configuração

### Localização
- **Cidade**: Diadema
- **Estado**: SP
- **País**: Brasil
- **Latitude**: -23.6861
- **Longitude**: -46.6167

### Limiar de Alerta
- **Temperatura mínima**: 15°C
- Quando a previsão indica temperatura abaixo desse limite, o OWL alerta o Senhor Robério

### APIs Utilizadas
1. **Open-Meteo** (principal) — `https://api.open-meteo.com/v1/forecast`
   - Gratuita, sem necessidade de API key
   - Fornece previsão de 3 dias com temperaturas mínimas/máximas e códigos de clima

2. **wttr.in** (fallback) — `https://wttr.in/Diadema+SP+BR?format=j1`
   - Gratuita, sem API key
   - Usada quando Open-Meteo falha

### Script
- **Local**: `C:\Users\dell-\AppData\Local\hermes\tools\monitor_tempo_diadema.py`
- **Execução**: `python monitor_tempo_diadema.py`
- **Retornos**:
  - `0` = Há alerta de temperatura baixa
  - `1` = Erro na execução
  - `2` = Sem alerta (temperatura OK)

### Cron Job
- **Nome**: `atena-monitor-tempo-diadema`
- **Frequência**: A cada 12 horas
- **Ação quando alerta**: TTS com aviso + recomendações
- **Ação quando silêncio**: Apenas registra no log

## Recomendações Quando Temperatura Cai

1. **Agasalhar-se bem** — Casacos, luvas, cachecóis
2. **Evitar exposição ao frio** — Sair apenas quando necessário
3. **Manter-se aquecido** — Ambientes aquecidos, bebidas quentes
4. **Monitorar sintomas** — Atenção a aumento de espasmos ou dor

## Log
- **Arquivo**: `C:\Users\dell-\AppData\Local\hermes\logs\monitor-tempo.log`
- Registra todas as verificações e alertas

## Ver também
- [[diretivas-acessibilidade]]
- [[distonia-generalizada]]
- [[automacao-atena]]
