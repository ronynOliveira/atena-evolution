# Guia de Integração Hermes ↔ Atena Local

**Data:** 18/06/2026
**Objetivo:** Integrar o Hermes Agent com a Atena (Ollama local) para eliminar dependência de APIs externas.

---

## Arquitetura Proposta

```
Senhor Robério
    ↓ (mensagem)
Hermes Agent (localhost:8642)
    ↓ (roteia para provider local)
KoldiOrchestrator (Python script)
    ↓ (HTTP POST)
AtenaBridge → Ollama API (localhost:11434)
    ↓ (resposta)
Hermes → Senhor Robério
```

---

## Opção 1: Provider Customizado no config.yaml

O Hermes suporta providers customizados. Adicione ao `~/.hermes/config.yaml`:

```yaml
providers:
  atena-local:
    name: "Atena Local (Ollama)"
    base_url: "http://localhost:11434"
    api_key_env: "OLLAMA_API_KEY"  # Ollama não precisa de key, mas o Hermes exige
    default_model: "atena-glm5"
    models:
      - atena-glm5
      - phi4-mini
      - gemma4:e2b
      - gemma4:e4b
      - qwen3:8b
      - hermes3:8b
    api_timeout: 120
```

**Problema:** O Hermes espera o formato OpenAI (`/v1/chat/completions`), mas o Ollama usa `/api/chat`. É necessário um adapter.

---

## Opção 2: Script Adapter (Recomendado)

Crie um script que atua como proxy entre o formato Hermes e o formato Ollama:

```python
# hermes_ollama_adapter.py
# Proxy que traduz chamadas OpenAI-format para Ollama-format
```

---

## Opção 3: Plugin Hermes (Mais Elegante)

Crie um plugin Hermes que se registra como provider:

```python
# ~/.hermes/plugins/atena-provider/plugin.py
```

---

## Recomendação Final

A **Opção 2** é a mais simples e funcional:

1. Script `hermes_ollama_adapter.py` roda como servidor HTTP
2. Expõe endpoint `/v1/chat/completions` (formato OpenAI)
3. Traduz para `/api/chat` (formato Ollama)
4. Hermes configura o provider apontando para o adapter

**Vantagens:**
- Zero modificação no código do Hermes
- Funciona com qualquer versão do Hermes
- Fácil de debugar e manter
- Pode adicionar cache, logging, etc

---

## Passo a Passo

### 1. Criar o adapter

Ver arquivo `core/hermes_ollama_adapter.py`

### 2. Iniciar o adapter

```bash
python core/hermes_ollama_adapter.py --port 8001
```

### 3. Configurar o Hermes

```yaml
# ~/.hermes/config.yaml
providers:
  atena-local:
    base_url: "http://localhost:8001/v1"
    api_key_env: "DUMMY_KEY"
    default_model: "atena-glm5"
    models:
      - atena-glm5
      - phi4-mini
      - gemma4:e2b
```

### 4. Reiniciar o Hermes

```bash
hermes gateway restart
```

### 5. Testar

Enviar uma mensagem pelo Telegram/CLI e verificar se a resposta vem da Atena local.

---

## Troubleshooting

| Problema | Solução |
|---|---|
| Hermes não conecta | Verificar se o adapter está rodando na porta 8001 |
| Resposta vazia | Verificar se Ollama está rodando: `curl localhost:11434/api/tags` |
| Timeout | Aumentar `api_timeout` no config.yaml |
| Modelo não encontrado | Verificar se o modelo está no Ollama: `ollama list` |
