# Pesquisa: Agent Loops - Sistemas de Loop Autônomo

**Data:** 2026-06-23
**Fontes:** arXiv API, Wikipedia API
**Projeto:** Atena Evolução

---

## 1. O que é um Agent Loop?

Um **Agent Loop** (ou ciclo de agente) é o padrão fundamental de operação de agentes de IA autônomos. Consiste em um ciclo repetitivo de três fases:

1. **PERCEIVE** (Perceber): Observar o ambiente, coletar informações, ler tarefas pendentes
2. **THINK** (Pensar): Usar raciocínio (LLM) para decidir a próxima ação
3. **ACT** (Agir): Executar a ação decidida e observar o resultado

O ciclo se repete até que uma condição de parada seja atingida (tarefas completadas, máximo de iterações, timeout, etc.).

---

## 2. Padrões de Agent Loops (da literatura)

### 2.1 ReAct (Synergizing Reasoning and Acting)
- **Autores:** Yao et al. (2022)
- **Conceito:** Alterna entre passos de raciocínio (Thought) e ações (Action)
- **Padrão:** Thought → Action → Observation → Thought → ...
- **Inovação:** Combina chain-of-thought com execução de ações externas

### 2.2 Reflexion (Verbal Reinforcement Learning)
- **Autores:** Shinn et al. (2022)
- **Conceito:** Após cada ação, o agente auto-reflete sobre o resultado
- **Padrão:** Act → Reflect → Adjust → Act (melhorado)
- **Inovação:** Memória de reflexão para evitar repetir erros

### 2.3 MRKL Systems (Modular Neuro-Symbolic)
- **Autores:** Karpas et al. (2022)
- **Conceito:** Arquitetura modular combinando LLM + ferramentas externas + conhecimento
- **Padrão:** Input → LLM Router → Knowledge Source / Tool → Output
- **Inovação:** Separação entre raciocínio (neuro) e conhecimento estruturado (symbolic)

### 2.4 Chain-of-Thought (CoT)
- **Autores:** Wei et al. (2022)
- **Conceito:** Geração de passos intermediários de raciocínio
- **Padrão:** Problem → Step1 → Step2 → ... → Answer
- **Inovação:** Raciocínio emergente em modelos grandes

### 2.5 MetaGPT (Multi-Agent Collaborative)
- **Autores:** Hong et al. (2023)
- **Conceito:** Múltiplos agentes colaborando em um fluxo de trabalho
- **Padrão:** Agent1 → Message → Agent2 → Message → ... → Result
- **Inovação:** Comunicação estruturada entre agentes com papéis definidos

### 2.6 AutoGPT (Autonomous GPT-4)
- **Ano:** 2023
- **Conceito:** Agente autônomo com memória, planejamento e execução
- **Padrão:** Goal → Plan → Execute → Reflect → Adjust → Complete
- **Inovação:** Autonomia completa com ferramentas (filesystem, web, etc.)

---

## 3. Arquitetura de um Agent Loop Robusto

### 3.1 Componentes Essenciais
1. **State Machine:** Gerencia estados (idle, thinking, acting, error, paused, stopped)
2. **Memory Buffer:** Armazena contexto entre iterações (working memory)
3. **LLM Client:** Interface com modelo de linguagem (Ollama, OpenAI, etc.)
4. **Retry System:** Backoff exponencial com jitter para erros transitórios
5. **Hook System:** Callbacks para logging, monitoramento, extensibilidade
6. **Stop Conditions:** Critérios de parada configuráveis

### 3.2 Condições de Parada
- `max_iterations` — Limite de iterações do loop
- `max_errors` — Limite de erros consecutivos
- `timeout` — Tempo máximo de execução
- `all_completed` — Todas as tarefas foram completadas
- `user_stop` — Parada solicitada pelo usuário

### 3.3 Tratamento de Erros
- **Backoff exponencial:** delay = base * multiplier^error_count
- **Jitter:** ±25% de variação para evitar thundering herd
- **Fallback:** Modo degradado quando LLM indisponível
- **Logging:** Registro estruturado de erros e contextos

---

## 4. Implementação no Projeto Atena Evolução

### 4.1 Arquivo: `core/agent_loop.py`
- **476 linhas** de código
- **Classe principal:** `AgentLoop`
- **Componentes:** MemoryBuffer, OllamaClient, HookSystem
- **Testado:** ✅ Funcionando (modo degradado sem Ollama)

### 4.2 Integração com Ollama
- Endpoint: `http://localhost:11434/api/chat`
- Modelo padrão: `hermes3:8b` (único modelo seguro no Ollama local)
- Timeout: 120s por chamada
- Fallback: modo degradado quando offline

### 4.3 Memory Buffer
- Working memory com limite configurável (padrão: 50 entradas)
- Context window para prompts (padrão: últimas 10 entradas)
- Busca por palavra-chave
- Contador de acesso para priorização

---

## 5. Próximos Passos
1. Integrar com o pipeline RAG da Atena Evolução
2. Adicionar suporte a múltiplos modelos (fallback chain)
3. Implementar persistência de memória (SQLite)
4. Criar testes unitários com pytest
5. Integrar com o sistema de orquestração multi-LLM

---

## Referências
- Yao et al. (2022) - ReAct: Synergizing Reasoning and Acting in Language Models
- Shinn et al. (2022) - Reflexion: Language Agents with Verbal Reinforcement Learning
- Karpas et al. (2022) - MRKL Systems: A modular, neuro-symbolic architecture
- Wei et al. (2022) - Chain-of-Thought Prompting Elicits Reasoning
- Hong et al. (2023) - MetaGPT: Meta Programming for A Multi-Agent Collaborative Framework
- Wang et al. (2023) - A Survey on Large Language Model based Autonomous Agents
- Xi et al. (2023) - The Rise and Potential of Large Language Model Based Agents: A Survey
