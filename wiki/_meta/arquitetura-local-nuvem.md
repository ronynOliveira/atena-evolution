# Arquitetura Local ↔ Nuvem

**Data:** 2026-06-25
**Versão:** 1.0

---

## Visão Geral

```
┌─────────────────────────┐          ┌─────────────────────────┐
│     KOLDI LOCAL         │          │     KOLDI NUVEM         │
│   (Windows 10)          │          │   (VPS Hostinger)       │
│                         │          │                         │
│  ┌───────────────────┐  │          │  ┌───────────────────┐  │
│  │ Ollama (local)    │  │          │  │ Sem Ollama        │  │
│  │ hermes3:8b        │  │          │  │ (VPN bloqueia)    │  │
│  │ nomic-embed-text  │  │          │  │                   │  │
│  └───────────────────┘  │          │  └───────────────────┘  │
│           │             │          │           │             │
│  ┌───────────────────┐  │  EPR     │  ┌───────────────────┐  │
│  │ Agente Local      │◄─┼──────────┼─►│ Koldi Nuvem Agent │  │
│  │ Roteador v2       │  │ WebSocket│  │ EPR Bridge Server │  │
│  │ Identity Engine   │  │   TLS    │  │ Sync Unison       │  │
│  │ Security Manager  │  │          │  │ Watchdog          │  │
│  │ Interface Web     │  │          │  │                   │  │
│  └───────────────────┘  │          │  └───────────────────┘  │
│           │             │          │           │             │
│  ┌───────────────────┐  │  SCP     │  ┌───────────────────┐  │
│  │ GitHub (origin)    │◄─┼──────────┼─►│ GitHub (mirror)   │  │
│  │ atena-evolution   │  │          │  │ projetoAtena      │  │
│  └───────────────────┘  │          │  └───────────────────┘  │
└─────────────────────────┘          └─────────────────────────┘
```

---

## Função de Cada Nó

### Koldi Local (Windows)
- **Chat**: Ollama com hermes3:8b (custo ZERO)
- **RAG**: nomic-embed-text + SQLite local
- **Interface**: Web holográfica cyberpunk
- **Roteamento**: Roteador v2 (complexidade + cache)
- **Segurança**: Security Manager (11 módulos)
- **Identidade**: Identity Engine (6 modos)

### Koldi Nuvem (VPS 2.25.168.233)
- **Sincronização**: EPR Bridge (WebSocket TLS)
- **Backup**: Unison (bidirecional)
- **Monitoramento**: Watchdog + Koldi Nuvem Agent
- **Relay**: Ponto de presença para acesso remoto
- **Sem chat**: Ollama não disponível (VPN)

---

## Sincronização

| Direção | Método | Porta | Frequência |
|---------|--------|-------|------------|
| Local → Nuvem | EPR Bridge | 8443 (WSS) | Contínuo |
| Nuvem → Local | EPR Bridge | 8443 (WSS) | Contínuo |
| Local ↔ GitHub | git push/pull | 443 (HTTPS) | Manual |
| Local → VPS | SCP | 22 (SSH) | Manual |

---

## Por que sem Ollama na VPS?

A VPS Hostinger usa uma configuração de VPN/firewall que bloqueia:
1. Download de modelos grandes (>4GB)
2. Portas necessárias para Ollama (11434)
3. Acesso a repositórios de modelos

**Decisão:** A VPS funciona como relay/sync apenas. O processamento de IA (chat, RAG, roteamento) é feito localmente no Windows.

---

## Como Usar

### Chat Local
```bash
# Iniciar Ollama (Windows)
ollama serve

# Iniciar interface web
cd atena_evolution
python -m http.server 8080
# Abrir http://localhost:8080/web/index.html
```

### Sincronizar com VPS
```bash
# Enviar arquivos novos
scp -i ~/.ssh/id_ed25519_vps core/*.py root@2.25.168.233:/opt/hermes/.hermes/atena_evolution/core/

# Receber atualizações
scp -i ~/.ssh/id_ed25519_vps root@2.25.168.233:/opt/hermes/.hermes/atena_evolution/web/*.html web/
```

---

## Próximos Passos

- [ ] Migrar para VPS que permita Ollama (Oracle Cloud, etc.)
- [ ] Implementar relay de chat via EPR Bridge
- [ ] Configurar acesso remoto à interface web via túnel SSH
