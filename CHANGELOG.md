# CHANGELOG - Atena Evolução

## [2.0.0] - 2026-06-24 — FUSÃO KOLDI + ATENA

### Adicionado
- **45 scripts** importados do ecossistema Koldi
- `core/identity.py` (186 linhas) — Motor de identidade do Koldi
- `safety/security_manager.py` (310 linhas) — Central de segurança integrada
- `tests/test_identity.py` — 21 testes de identidade
- `tests/test_security.py` — 7 testes de segurança
- `scripts/senha_descartavel.py` — Sistema de senhas de uso único
- `docs/PLANO-FUSAO-ATENA-KOLDI.md` — Plano completo de fusão
- `docs/relatorio-claude-atena-evolucao.md` — Análise técnica
- `docs/relatorio-ecossistema-koldi.md` — Análise do ecossistema
- `README.md` — Documentação consolidada

### Segurança
- Corrigidas permissões de `.env`, `config.yaml`, `vault.enc`, `vault.salt`
- Criado sistema de senhas descartáveis com TTL
- Security Manager com 11 módulos de segurança integrados

### Métricas
- 96 arquivos Python (+45)
- 30.706 linhas de código (+13.925)
- 89 testes passando (+28)

---

## [1.0.0] - 2026-06-23 — ATENA EVOLUÇÃO

### Adicionado
- `core/agent_loop.py` (656 linhas) — Agent Loop perceber-pensar-agir
- `docs/pesquisa-agent-loops-2026-06-23.md` — 8 padrões de agentes
- Pesquisa acadêmica sobre Agent Loops (arXiv)
- Sistema de memória com 61 testes

---

## Pré-histórico (Koldi)
- SOUL.md v4.1-v4.4 — Personalidade e valores
- 46 scripts Python no ecossistema
- Sistema de memória com decay, cofre AES-256, EPR Bridge
- 5 cron jobs automáticos
- 2 plugins (browser, computer-use)
