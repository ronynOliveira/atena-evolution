# Contexto Atual do Koldi

> **Última atualização:** 2026-06-05 13:00
> **Sessão:** 20260604_080848_2ae589 (continuação)

## Estado Atual

### Projetos em Andamento
- **Memória Hierárquica:** Implementando sistema de contexto em camadas (MEMORY.md → memory-tree → wiki)
- **Auto-Cofre:** Script de monitoramento automático de informações sensíveis (cron 1h)
- **VPS Hostinger:** Configurando acesso SSH com nova chave ed25519

### Infraestrutura
| Componente | Windows | VPS Hostinger |
|------------|---------|---------------|
| memory_char_limit | 300.000 | 300.000 |
| user_char_limit | 60.000 | 60.000 |
| SSH Key | id_ed25519_vps | root@2.25.168.233 |
| Gateway | PID 28708 | PID 32182 |
| TTS | edge-tts v4 ✅ | edge-tts v7.2.8 ✅ |

### Chaves no Cofre
- SSH_VPS_PRIVATE_KEY / SSH_VPS_PUBLIC_KEY
- SSH_PUBLIC_KEY (original)
- GITHUB_PAT_FINEGRAINED
- GOOGLE_API_KEY
- OPENAI_API_KEY
- OPENROUTER_API_KEY
- TELEGRAM_BOT_TOKEN
- TELEGRAM_USER_ID
- GOOGLE_OAUTH_CLIENT_ID / SECRET

### Cron Jobs Ativos (Windows)
- `koldi-auto-cofre-1h` (35539e0453f4) — Monitor de informações sensíveis
- `atena-auto-fetch` (20d6053b5cd4) — Auto-Fetch a cada 60min
- `atena-memory-care` (95c13a381be3) — Memory Tree a cada 24h
- `key-checkin-1h` (9d7182f27edc) — Verificação de providers
- `koldi-security-watchdog` (d73b31d99d39) — Segurança a cada 60min
- `atena-monitor-sistema` (b4b8aea8f0df) — Monitor a cada 360min
- `atena-auto-evolucao` (7057507dd297) — Auto-evolução a cada 1440min

### Últimas Ações
1. Update Hermes 0.15.1 (126 commits)
2. Limpeza do memory-tree (34 → 10 entradas)
3. Migração de 16 entradas para wiki/_meta/memoria/
4. Criação do auto_cofre.py + cron 1h
5. Aumento de memória (150k → 300k)
6. Nova chave SSH para VPS Hostinger
7. Instalação edge-tts na VPS

### Próximos Passos
- [ ] Criar template de checkpoint de sessão
- [ ] Testar conexão VPS completa
- [ ] Consolidar memory-tree com fatos das sessões antigas
- [ ] Migrar mais entradas antigas da memória para wiki

### Notas Importantes
- MEMORY.md no disco: C:\Users\dell-\.hermes\memories\MEMORY.md (não o do AppData)
- Wiki primária: G:\Meu Drive\Koldi\wiki\
- Wiki backup: C:\Users\dell-\wiki\ (desatualizado)
- Sessões do Hermes: C:\Users\dell-\AppData\Local\hermes\state.db
- Memory-tree: C:\Users\dell-\AppData\Local\hermes\memory-tree\entries\
