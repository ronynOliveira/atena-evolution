# Próximos Passos — Sessão 2026-06-01 (continuação na próxima sessão)

**Status atual:** Sessão salva. Crawl em andamento.

## O que fizemos nesta sessão
- Colocamos `net_monitor.py` em produção (DNS, gateway, ping validados)
- Criamos cron: `atena-gateway-health` (5 min) e `atena-network-check` (30 min)
- Ajustamos repetição para rodar várias vezes
- Atualizamos a wiki e fizemos commit local

## O que faltou / sequência correta para a próxima
1. **Trocar a OPENROUTER_API_KEY** e reiniciar o gateway
2. **Integrar confidence_estimator** ao pipeline de respostas
3. **Wire memory_queue** no lugar de `memory_scorer.create_entry()`
4. **Atualizar SOUL.md** com métricas de saúde identitária e protocolo de parada
5. **Teste end-to-end** de 10 turnos

## Comandos úteis para a próxima sessão
- Validar testes: `python -m pytest "C:/Users/dell-/AppData/Local/hermes/lib/tests/" -q`
- Ver o que falta no plano: ler este arquivo

## Notas
- Wiki atual: 2026-06-01T14:59:50.991084
- Caminho: G:\Meu Drive\Koldi\wiki\_meta\proximos-passos-2026-06-01.md
