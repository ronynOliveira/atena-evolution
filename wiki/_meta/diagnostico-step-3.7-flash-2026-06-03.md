# Diagnóstico — modelo step-3.7-flash:free (2026-06-03)

## Sintoma reportado pelo usuário
Modelo exibindo: `52.2K/256K │ [██░░░░░░░░] 20% │ 4m │ ⏲ 2m 7s`

## Hipóteses iniciais
1. Free tier saturado / rate limit
2. Latência alta do provedor StepFun
3. Contexto grande (>50K) tornando a resposta custosa

## Verificações necessárias
- Consultar `monitor_latencia.py`
- Checar OpenRouter/StepFun status
- Avaliar se o gerador ficou "travado" em 20%
