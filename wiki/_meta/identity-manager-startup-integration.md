# Integração do Identity Manager no Startup do Hermes

**Data:** 2026-06-02
**Status:** Documentado, aguardando hook de bootstrap

---

## 1. O que é

`identity_manager.py` é o gerenciador de identidade Koldi. Ele carrega o `IDENTITY.md` e o `SOUL.md`, valida princípios contra ambos documentos e executa 5 níveis de anti-drift: baseline, periódico, sessão, adaptativo, drift response.

## 2. Estado atual

- Script: `C:/Users/dell-/AppData/Local/hermes/scripts/identity_manager.py`
- Logs: `~/.hermes/logs/identity_manager.log`
- Baseline: `C:/Users/dell-/AppData/Local/hermes/state/identity_baseline.json`
- Sessões de drift: `C:/Users/dell-/AppData/Local/hermes/state/identity_sessions/`

## 3. Execução manual

```bash
python "C:/Users/dell-/AppData/Local/hermes/scripts/identity_manager.py" --action list
python "C:/Users/dell-/AppData/Local/hermes/scripts/identity_manager.py" --action validate --key "princípio" --value "texto"
python "C:/Users/dell-/AppData/Local/hermes/scripts/identity_manager.py" --action drift_response
```

## 4. Integração planejada no startup

**Condição:** aguardando identificação do hook de bootstrap do Hermes (arquivo/skill que executa scripts no início de cada sessão).

**Quando o hook for encontrado, adicionar:**
```bash
python "C:/Users/dell-/AppData/Local/hermes/scripts/identity_manager.py" --action drift_baseline
python "C:/Users/dell-/AppData/Local/hermes/scripts/identity_manager.py" --action drift_session --session-id "<SESSION_ID>"
```

**Critério de acoplamento:**
- Não modificar configs do Hermes às cegas
- O hook deve ser oficialmente documentado na skill `hermes-identity` ou no código do agente
- A integração será feita via patch direcionado, não reescrita

## 5. Exemplo de uso programático

```python
from identity_manager import IdentityManager

mgr = IdentityManager()
print(mgr.list_principles())
issues = mgr.validate_against_soul("novo conteúdo...")
issues += mgr.validate_against_identity("novo conteúdo...")
result = mgr.drift_response()
```

## 6. Próximo passo

1. Identificar o arquivo/skill de bootstrap do Hermes
2. Acoplar as chamadas de drift_baseline e drift_session
3. Validar em uma nova sessão
4. Atualizar esta página com `status: integrado`
