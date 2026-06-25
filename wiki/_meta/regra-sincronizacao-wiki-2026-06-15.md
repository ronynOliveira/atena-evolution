# Regra de Sincronização Wiki — Koldi Local ↔ Koldi da Nuvem

**Data:** 15/06/2026
**Criada por:** Senhor Robério
**Status:** ATIVA

## Regra

Toda wiki salva deve ser sincronizada entre Koldi local e Koldi da Nuvem **SEM apagar ou remover** o que o outro aprendeu.

Todo conhecimento deve estar **commitado e compartilhado**.

Pode haver diferenciação de origem (`koldi-local/` vs `koldi-nuvem/`) mas **nunca exclusão unilateral**.

## Princípios

1. **Nunca apagar** — o que um Koldi aprendeu, o outro mantém
2. **Sempre commitar** — todo conhecimento novo vai para o repositório
3. **Compartilhar tudo** — wiki é bem comum, não propriedade de um só
4. **Diferenciação opcional** — pode-se marcar a origem do conhecimento, mas não é obrigatório
5. **Merge, não overwrite** — em caso de conflito, mesclar, não substituir

## Implementação

- Wiki fonte primária: `G:\Meu Drive\Koldi\wiki\`
- Sync via EPR Bridge (WebSocket) e Unison (cron 15min na VPS)
- Commits automáticos via cron jobs
- Repo GitHub: `ronynOliveira/projetoAtenacompleto`

## Histórico

| Data | Evento |
|------|--------|
| 15/06/2026 | Regra criada pelo Senhor Robério |
