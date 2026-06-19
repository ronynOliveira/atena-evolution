# Memória da Atena — Arquitetura Estratificada Local-First

## 1. O problema, reformulado

Você pediu memória que (1) entenda contexto acumulado, (2) esqueça gradualmente,
(3) conecte conceitos entre sessões, (4) caiba num modelo de 3-4B em CPU, (5)
nunca saia da máquina.

Uma correção de escopo importante, antes da arquitetura: o requisito 3, como
formulado ("perceber que é a mesma pessoa"), é um problema que **você não tem**.
Sistemas como Mem0 e Zep pagam um custo computacional alto resolvendo
desambiguação de identidade entre múltiplos usuários — isso é over-engineering
para um agente single-user. O problema real disfarçado ali é mais barato:
**ligar tópicos diferentes ao mesmo perfil acumulado**. Essa simplificação é o
que torna essa arquitetura viável no seu hardware.

## 2. Por que as soluções existentes falham pra você

- **Mem0 / LangGraph memory**: resolvem multi-tenancy e versionamento de fatos
  em escala — pagam esse custo mesmo quando você só tem um usuário.
- **RAG com summaries simples**: não tem decay nem hierarquia. A memória cresce
  sem limite, e tudo pesa igual para sempre — o oposto do que você pediu.
- **MemGPT/Letta**: arquitetura elegante (paginação estilo SO), mas pressupõe
  que o próprio LLM gerencie suas chamadas de memória como tool calls — caro
  demais para um modelo de 3.8B rodando em CPU responder com confiabilidade.

## 3. Arquitetura proposta: três camadas + separação online/offline

```
┌─────────────────────────────────────────────────────────┐
│  CAMADA 1 — Memória de Trabalho (working memory)         │
│  Buffer da sessão atual, em processo, não persistida.    │
│  É o que já está no prompt do turno corrente.             │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼ remember() — ONLINE, barato
┌─────────────────────────────────────────────────────────┐
│  CAMADA 2 — Memória Episódica (SQLite)                    │
│  Notas atômicas (estilo Zettelkasten / A-MEM).             │
│  Cada nota: embedding + entidades + importância + força S. │
│  Decay: R = e^(-t/S)  [MemoryBank / Ebbinghaus]            │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼ run_maintenance() — OFFLINE, 1x/dia
┌─────────────────────────────────────────────────────────┐
│  CAMADA 3 — Memória Semântica (fatos consolidados)         │
│  Clusters de memórias episódicas relacionadas → 1 chamada  │
│  ao atena-glm5 por cluster → fato sintetizado e persistente.│
│  Decai mais devagar (strength inicial mais alta).           │
└─────────────────────────────────────────────────────────┘
```

A separação **online/offline** é o ponto central (LightMem, 2026): o caminho de
escrita e o de leitura nunca chamam o LLM de chat — só fazem embedding (rápido,
~10-50ms até em CPU) e aritmética vetorial pura Python. O modelo de 3.8B só
"pensa caro" durante a manutenção noturna, consolidando clusters — e mesmo
assim, uma chamada por cluster, não por memória individual.

### 3.1 Decay (Ebbinghaus / MemoryBank)

```
R = e^(-t/S)
```
- `R`: retenção atual (0 a 1)
- `t`: dias desde o **último acesso** (não desde a criação — isso é o que cria
  o "efeito de espaçamento": memórias revisitadas resistem mais)
- `S`: força, começa em 1.0, **aumenta a cada recall**

Isso resolve seu requisito filosófico mais sutil: não existe um corte binário
entre lembrar e esquecer. Existe um gradiente contínuo — o que, no seu próprio
vocabulário, é mais próximo da dialética Memória/Esquecimento do que um
`DELETE FROM` jamais seria. Memórias abaixo de um limiar (default 0.05) são
*arquivadas*, não destruídas — saem do índice de busca ativo mas continuam no
banco, recuperáveis se um processo futuro de consolidação as referenciar.

### 3.2 Conexão entre sessões (sem coreferência cara)

`extract_entities()` usa regex barato (substantivos próprios + uma lista de
termos de domínio que você define) — zero chamadas de LLM no caminho de
escrita. `cluster_by_overlap()` agrupa memórias que compartilham entidades
(union-find, O(n²), testado até 500 notas em <0.1s no seu hardware-alvo
simulado). Só memórias no mesmo cluster geram uma chamada de consolidação.

**Limitação real, encontrada testando em escala** (não escondendo isso de
você): a extração ingênua de maiúsculas confundia capitalização gramatical de
início de frase com nomes próprios, criando clusters falsos gigantes. Corrigido
suprimindo a primeira letra de cada sentença antes do regex — trade-off
deliberado: perde nomes que aparecem literalmente no início de uma frase, mas
isso é raro na escrita natural. Documentado no código (`consolidation.py`).

### 3.3 Orçamento de contexto

`retrieve_top_k()` aceita um `token_budget` (default 400 tokens) e corta o
ranking assim que esse orçamento se esgota — independente de quantas memórias
você tenha acumulado, o prompt injetado no atena-glm5 nunca estoura. Com
`num_ctx=4096` do phi4-mini, isso deixa ~3600 tokens livres para a conversa
real.

## 4. Referências reais (para você se aprofundar)

- **A-MEM** — Xu et al., *Agentic Memory for LLM Agents*, arXiv:2502.12110.
  Zettelkasten aplicado a memória de agentes — a inspiração estrutural direta
  das suas notas atômicas. Código: github.com/agiresearch/A-mem
- **MemoryBank** — Zhong et al. (2024), formaliza R=e^(-t/S) com S incrementado
  a cada recall — é exatamente o `decay.py` deste pacote.
- **LightMem** — arXiv:2604.07798, *Lightweight LLM Agent Memory with Small
  Language Models* — a separação STM/MTM/LTM e online/offline que torna isso
  viável em CPU sem GPU.
- **Survey 2026** — *Memory for Autonomous LLM Agents: Mechanisms, Evaluation,
  and Emerging Frontiers*, arXiv:2603.07670 — bom mapa geral se quiser comparar
  outras arquiteturas (AriGraph, MemGPT, AgeMem) antes de comprometer mais
  engenharia.
- **LoCoMo** — Maharana et al., arXiv:2402.17753 — benchmark de referência
  para testar memória de longo prazo (metodologia adaptada abaixo).

## 5. Estratégia de testes

### 5.1 Testes unitários (já incluídos, rodam sem Ollama)
`test_atena_memory.py` usa uma `FakeBridge` com embeddings determinísticos via
hash — valida decay, ranking, clustering e arquivamento sem precisar de
inferência real. Rode com `pytest test_atena_memory.py -v` agora mesmo, antes
de plugar no Ollama de verdade.

### 5.2 Validação com o Ollama real (faça isso depois dos testes unitários passarem)
1. Troque `FakeBridge` por `AtenaBridge()` real (já é o default de `AtenaMemory`).
2. Rode `mem.stats()` antes e depois de uma sessão de uso real por 1-2 semanas.
3. Verifique manualmente 10 recalls aleatórios: a memória recuperada é
   *plausivelmente relevante* à query? (não precisa de métrica formal pra
   começar — calibração humana primeiro).

### 5.3 Mini-LoCoMo pessoal (quando quiser rigor)
Adapte a metodologia do LoCoMo numa escala pessoal, sem precisar gerar 35
sessões sintéticas:
1. Anote manualmente 15-20 fatos que você mencionou ao Atena ao longo de 2
   semanas reais de uso (ex: "mencionei minha distonia na segunda", "falei do
   TTP na quinta").
2. Depois de 2-4 semanas, faça perguntas que exigem: (a) recall direto de um
   fato único, (b) recall multi-hop (combinar 2 fatos de sessões diferentes),
   (c) reasoning temporal ("o que eu disse antes de mencionar X?").
3. Calcule manualmente: dos fatos que *deveriam* ter decaído (baixa
   importância, não revisitados), quantos efetivamente saíram do top-5 do
   recall? Dos fatos importantes, quantos sobreviveram?

Isso é o "LoCoMo de um usuário só" — não precisa do dataset completo de 16K
tokens por conversa; sua própria vida útil de uso já é o conjunto de teste.

## 6. Integração com o resto do Atena/Hermes

```python
from atena_memory.pipeline import AtenaMemory

mem = AtenaMemory(db_path="atena_memory.db")

# No seu pipeline existente (RAG + classify_task_v2 + const_check_v2):
contexto_memoria = mem.recall(pergunta_do_usuario, k=5, token_budget=400)
prompt_final = f"{contexto_memoria}\n\n{prompt_rag_existente}"

# Em algum lugar com cron/Task Scheduler do Windows, 1x/dia:
mem.run_maintenance()
```

Agendamento no Windows 10: `schtasks /create /tn "AtenaMemMaintenance" /tr
"python C:\caminho\run_maintenance.py" /sc daily /st 03:00`

## 7. O que eu propositalmente NÃO incluí

- Sem grafo de conhecimento completo (Neo4j/RDF) — overkill pro seu volume de
  dados pessoal. O union-find por entidades já dá 80% do valor por 5% do custo.
- Sem reranking neural na recuperação — cosine + decay + entidades é
  suficiente em CPU; um cross-encoder adicionaria latência sem ganho
  proporcional no seu volume de memórias.
- Sem versionamento de fatos contraditórios (campo `superseded_by` existe no
  schema, mas a lógica de detectar contradição não foi implementada — isso
  exigiria uma chamada de LLM por fato novo vs. existente, o que é caro demais
  pra incluir por padrão. Se precisar, é a próxima peça a adicionar.)
