# Prompt Enhancer - Sistema de Melhoria de Prompts

**Data:** 2026-06-22
**Criador:** Koldi (OWL)
**Versão:** 1.0

## O que é

Script Python que transforma prompts simples do usuário em prompts otimizados para agentes de IA, aplicando 8 técnicas de prompt engineering e context engineering.

## Localização

- Script: `C:\Users\dell-\AppData\Local\hermes\scripts\melhorar_prompt.py`
- Skill: `C:\Users\dell-\AppData\Local\hermes\skills\productivity\prompt-enhancer\SKILL.md`
- Wrapper CMD: `C:\Users\dell-\AppData\Local\hermes\scripts\prompt-melhorar.bat`
- Wrapper PS1: `C:\Users\dell-\AppData\Local\hermes\scripts\prompt-melhorar.ps1`

## Uso

```bash
# Prompt simples → prompt otimizado
python melhorar_prompt.py "seu prompt aqui"

# Com flags
python melhorar_prompt.py "crie um relatório" --no-expert
python melhorar_prompt.py "analise de dados" --save
python melhorar_prompt.py "projete uma api" --no-cot --save
```

## Flags

| Flag | Efeito |
|------|--------|
| `--no-expert` | Remove perfil de especialista |
| `--no-cot` | Remove chain-of-thought |
| `--no-constraints` | Remove restrições anti-alucinação |
| `--no-format` | Remove formato de saída automático |
| `--save` | Salva em arquivo |

## Técnicas Aplicadas

1. **Role Assignment** — Detecta domínio e atribui perfil de especialista
2. **Context Enriching** — Expande instruções vagas com contexto implícito
3. **Output Formatting** — Detecta formato apropriado automaticamente
4. **Chain-of-Thought** — Adiciona instruções de raciocínio estruturado
5. **Constraint Injection** — Adiciona restrições anti-alucinação
6. **XML Tag Structuring** — Usa tags XML para estruturar o prompt
7. **Anti-Hallucination** — Instruções para não inventar informações
8. **Proactivity Hints** — Sugere próximos passos automaticamente

## Detecção de Domínios

| Domínio | Especialista | Gatilhos |
|---------|-------------|----------|
| code | Engenheiro de Software Sênior | código, programar, script, api, python... |
| research | Pesquisador Científico | pesquisar, estudo, análise, metodologia... |
| writing | Editor Literário | escrever, texto, conto, narrativa... |
| analysis | Analista de Dados | analisar, comparar, métrica, tendência... |
| creative | Diretor Criativo | criar, ideia, design, inovar... |
| technical | Arquiteto de Sistemas | arquitetura, infraestrutura, docker... |
| general | Assistente Especialista | (padrão) |

## Detecção de Fraquezas

- `muito_curto` — menos de 20 caracteres
- `falta_contexto` — sem palavras de contexto
- `falta_intencao` — sem verbos de intenção
- `falta_detalhamento` — menos de 8 palavras
- `sem_formato` — sem especificação de formato
- `pergunta_simples` — termina com ? sem corpo

## Exemplo de Transformação

**Entrada:**
```
me ajude a criar uma api rest com autenticação jwt
```

**Saída:**
```
<role>
Você é um Engenheiro de Software Senior especialista em clean code, design patterns, testes, performance. Responda de forma técnico e preciso, usando melhores práticas da área.
</role>

<task>
Forneça orientação detalhada sobre criar uma api rest com autenticação jwt
</task>

<context>
- Considere o contexto brasileiro quando aplicável
- Use terminologia técnica apropriada
- Cite fontes ou referências quando possível
</context>

<reasoning>
Antes de responder:
1. Analise cuidadosamente o que foi solicitado
2. Identifique os principais conceitos envolvidos
3. Estruture a resposta de forma lógica e progressiva
4. Verifique se a resposta atende completamente ao solicitado
</reasoning>

<constraints>
- Não invente informações; se não souber, diga claramente
- Baseie-se em fatos verificáveis
- Quando fizer suposições, declare-as explicitamente
- Se a pergunta for ambígua, apresente as possíveis interpretações
- Priorize precisão sobre quantidade de informação
</constraints>

<proactivity>
- Após a resposta principal, sugira próximos passos relevantes
- Identifique possíveis problemas ou limitações da solução
- Mencione alternativas quando aplicável
</proactivity>
```

## Integração com Koldi

Quando o Senhor Robério pedir para melhorar um prompt:
1. Koldi usa o script `melhorar_prompt.py` com o texto do Senhor
2. Exibe o resultado formatado
3. Oferece para salvar se o Senhor quiser
4. Pode usar o prompt melhorado diretamente na tarefa
