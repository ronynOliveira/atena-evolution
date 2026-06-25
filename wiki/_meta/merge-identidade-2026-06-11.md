# Merge de Identidade — Koldi Local ↔ Koldi Nuvem

**Data:** 2026-06-11
**Ação:** Consolidação e sincronização de personalidade entre instâncias

---

## O que foi feito

### Problema
- SOUL.md no C: (AppData) era versão curta (30 linhas, desatualizada)
- SOUL.md na G: (Meu Drive) era versão completa (v4.1, 382 linhas)
- VPS recebeu versão curta durante sessão anterior que crashou
- MEMORY.md não existia como arquivo

### Ações executadas

1. **Promoção do SOUL.md v4.1**
   - Origem: `G:\Meu Drive\Koldi\.hermes\IDENTITY\SOUL.md` (v4.1, 382 linhas)
   - Destino C: `\AppData\Local\hermes\IDENTITY\SOUL.md` ✅
   - Destino C: raiz `\AppData\Local\hermes\SOUL.md` ✅
   - Destino VPS: `/opt/hermes/IDENTITY/SOUL.md` ✅
   - Destino VPS: raiz `/opt/hermes/SOUL.md` ✅

2. **Sincronização dos arquivos de identidade**
   - HERMES.md → C: + VPS ✅
   - TOOL_GUIDE.md → C: + VPS ✅
   - USER.md → C: + VPS ✅

3. **Criação do MEMORY.md**
   - C: `\AppData\Local\hermes\MEMORY.md` ✅
   - VPS: `/opt/hermes/MEMORY.md` ✅

### Estado após merge

| Arquivo | C: (local) | G: (fonte) | VPS (nuvem) |
|---------|-----------|-----------|-------------|
| SOUL.md | v4.1 ✅ | v4.1 ✅ | v4.1 ✅ |
| HERMES.md | ✅ | ✅ | ✅ |
| TOOL_GUIDE.md | ✅ | ✅ | ✅ |
| USER.md | ✅ | ✅ | ✅ |
| MEMORY.md | ✅ | N/A | ✅ |

---

## Próximos passos da ponte
- Fase 2: Unison bidirecional (configurar perfil e cron)
- Fase 3: Checkpointing Postgres
- Fase 4: Mem0 sync
