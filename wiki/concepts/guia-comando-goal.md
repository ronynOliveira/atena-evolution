---
title: Comando /goal — Guia Completo
created: 2026-05-20
updated: 2026-05-20
type: concept
tags: [hermes-agent, goal, comando, produtividade]
sources: []
confidence: high
---

# Comando /goal — Guia Completo

> Ver também: [[guia-comandos-hermes]] (referência completa), [[hermes-agent]] (framework)

## O que é?
O `/goal` define um **objetivo permanente** que o Hermes persegue automaticamente, turno após turno, até completar. É inspirado no "Ralph loop" — um loop de trabalho autônomo.

## Como funciona?
1. Você define um objetivo com `/goal <texto>`
2. O Hermes trabalha nele automaticamente
3. Após cada turno, um "modelo juiz" avalia se o objetivo foi completado
4. Se não foi, o Hermes continua trabalhando
5. Loop continua até: objetivo completado, budget de turnos esgotado, ou você pausar/limpar

## Comandos

| Comando | Função |
|---|---|
| `/goal <texto>` | Definir novo objetivo |
| `/goal` ou `/goal status` | Ver estado atual |
| `/goal pause` | Pausar objetivo |
| `/goal resume` | Retomar objetivo |
| `/goal clear` / `/goal stop` / `/goal done` | Limpar objetivo |
| `/subgoal <texto>` | Adicionar critério extra |

## Exemplos

```
# Definir objetivo
/goal Criar um sistema de backup automático do wiki com git push a cada hora

# Ver progresso
/goal status

# Adicionar critério
/subgoal O backup deve incluir todos os arquivos .md

# Pausar
/goal pause

# Limpar quando terminar
/goal clear
```

## Mecânica Interna

### GoalState (estado do objetivo):
- **goal** — texto do objetivo
- **status** — active | paused | done | cleared
- **turns_used** — turnos usados
- **max_turns** — budget máximo (padrão: 20)
- **subgoals** — critérios adicionais

### Judge (juiz):
- Um modelo auxiliar avalia se o objetivo foi completado
- Retorna: `{"done": true/false, "reason": "..."}`
- Fail-open: se o juiz falhar, continua trabalhando
- Após 3 falhas consecutivas de parsing, o loop pausa automaticamente

### Continuação:
- Após cada turno, se o objetivo não foi completado, o Hermes recebe um prompt de continuação
- O agente trabalha no objetivo sem intervenção do usuário
- O usuário pode enviar mensagens normais a qualquer momento (pausa o loop naquele turno)

## Casos de Uso

### 1. Tarefas longas e complexas
```
/goal Refatorar o módulo de autenticação do Projeto Atena:
- Separar lógica de validação
- Adicionar testes unitários
- Atualizar documentação
```

### 2. Pesquisa e síntese
```
/goal Pesquisar as 10 principais novidades em IA para 2026 e criar um resumo executivo
```

### 3. Monitoramento contínuo
```
/goal Monitorar o espaço em disco C: e alertar se ficar abaixo de 50GB
```

### 4. Desenvolvimento iterativo
```
/goal Implementar a feature de exportação do wiki para PDF
```

## Dicas

1. **Seja específico** — objetivos claros têm melhor resultado
2. **Use subgoals** — para adicionar critérios detalhados
3. **Monitore com /goal status** — para ver progresso
4. **Pare com /goal pause** — se quiser pausar temporariamente
5. **Limpe com /goal clear** — quando terminar

## Configuração

No `config.yaml`:
```yaml
goals:
  max_turns: 20  # Budget de turnos (padrão: 20)
```

## Notas

- O estado é persistido no SessionDB (sobrevive a /new e /resume)
- O judge usa um modelo auxiliar (configurado em `auxiliary.goal_judge`)
- O loop respeita o budget de turnos (padrão: 20)
- Mensagens do usuário têm prioridade sobre o loop de goal
