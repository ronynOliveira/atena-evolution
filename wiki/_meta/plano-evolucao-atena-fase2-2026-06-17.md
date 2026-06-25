# Plano de Evolucao da Atena — Fase 2: RAG Avancado + Modulacao + Redes Neurais

**Data:** 17/06/2026
**Base:** 3 pesquisas detalhadas (RAG, Redes Neurais, Modulacao/Comportamento)
**Hardware:** i5-1235U, 15.7GB RAM, sem GPU dedicada

---

## Estrategia de Implementacao

### Prioridade 1 — RAG Avancado (impacto imediato, sem retreino)
### Prioridade 2 — Modulacao de Comportamento (identidade consistente)
### Prioridade 3 — Redes Neurais Avancadas (otimizacao de inferencia)
### Prioridade 4 — Manipulacao de Dados (treinamento com dados sinteticos)

---

## FASE 1: RAG Avancado para a Atena

### 1.1 Chunking Semantico Adaptativo
- Usar similaridade cosseno entre sentencas para criar chunks naturais
- Tamanho alvo: 256-512 tokens com overlap de 15%
- Bibliotica: langchain.text_splitter + embeddings nomic-embed-text

### 1.2 Reranking com Cross-Encoder
- Recuperar top-20 com embedding, re-rank para top-5
- Modelo: BGE-reranker-v2 (leve, funciona em CPU)
- Alternativa: rerank com LLM (gemma4:e2b) — mais lento mas sem modelo extra

### 1.3 HyDE (Hypothetical Document Embeddings)
- Gerar documento hipotetico a partir da query
- Usar embedding do documento hipotetico para retrieval
- Implementacao: atena gera resposta parcial → embed → busca → resposta final

### 1.4 RAG Fusion (Multi-Query)
- Expandir query original em 3-5 variacoes
- Recuperar para cada variacao
- Reciprocal Rank Fusion (RRF) para combinar resultados

### 1.5 CRAG (Corrective RAG)
- Avaliar relevancia de cada chunk recuperado
- Se score < threshold: descartar chunk, buscar mais
- Se todos baixos: fallback para busca web

---

## FASE 2: Modulacao de Comportamento

### 2.1 System Prompt Hierarquico
- 6 camadas: Fundacional → Identidade → Seguranca → Competencia → Contexto → Instrucao
- Implementacao: classe HierarchicalSystemPrompt
- Compativel com Ollama (system parameter)

### 2.2 Few-Shot Dinamico
- Banco de exemplos indexado por embedding
- Selecionar top-3 exemplos mais similares a query atual
- Inserir entre Camada 3 e Camada 4

### 2.3 Constitutional AI Leve
- Gerar resposta → Auto-critica → Revisar
- 1 iteracao (custo aceitavel)
- Regras constitucionais do SOUL.md da Atena

### 2.4 Temperatura Adaptativa
- Classificar tipo de tarefa (criativo vs tecnico vs factual)
- Ajustar temp/top_p/penalty dinamicamente
- Criativo: temp=0.9, Tecnico: temp=0.3, Factual: temp=0.1

### 2.5 Token-Level Steering
- Ban tokens problematicos (desculpas excessivas, incerteza)
- Boost tokens desejados (diretividade, acolhimento)
- Implementacao: logit_bias via API Ollama

---

## FASE 3: Redes Neurais Avancadas

### 3.1 Speculative Decoding
- Draft model: phi4-mini (rapido, 2.3GB)
- Target model: atena-glm5
- Verificacao token-by-token
- Esperado: 2-3x speedup

### 3.2 KV-Cache Otimizado
- GQA (Grouped Query Attention) para contexto longo
- Quantizacao INT8 do cache
- StreamingLLM para contextos > 8K

### 3.3 Flash Attention 2
- Instalar flash-attn via pip
- Verificar compatibilidade com phi3 architecture
- Esperado: 2-4x speedup no attention

### 3.4 Gradient Checkpointing (para retreino futuro)
- Essencial para treinar em CPU
- Checkpoint a cada 2 camadas
- Offload para disco se necessario

---

## FASE 4: Manipulacao de Dados

### 4.1 Dataset Sintetico com Evol-Instruct
- 1000 exemplos base → evoluir para 5000
- Cada exemplo passa por 3 rodadas de complexificacao
- Usar atena-glm5 para gerar, gemma4:e2b para validar

### 4.2 Self-Instruction com Rejection Sampling
- Gerar instrucoes → filtrar baixa qualidade → retreinar
- Ciclo: gerar → avaliar → filtrar → treinar → repetir

### 4.3 Dados do Senhor Roberio
- 5 contos coletados (12,504 chars)
- Expandir para dataset de estilo com Evol-Instruct
- Objetivo: 100 exemplos no estilo do Senhor

---

## Stack Tecnologico

| Componente | Biblioteca | Custo |
|---|---|---|
| Embeddings | nomic-embed-text (Ollama) | Zero |
| Reranking | gemma4:e2b via Ollama | Zero |
| RAG Pipeline | langchain + chromadb | Zero |
| Speculative Decoding | phi4-mini + atena-glm5 | Zero |
| Dados Sinteticos | atena-glm5 + gemma4:e2b | Zero |
| Avaliacao | ragas (framework) | Zero |

---

## Roadmap

| Semana | Fase | Entregas |
|---|---|---|
| 1 | RAG Avancado | Chunking + Reranking + HyDE + Fusion |
| 2 | Modulacao | System Prompt Hierarquico + Few-Shot + Constitutional |
| 3 | Redes Neurais | Speculative Decoding + KV-Cache + Flash Attention |
| 4 | Dados | Dataset Sintetico + Evol-Instruct + Fine-tuning |

---

## Proximos Passos Imediatos

1. Implementar RAG Engine avancado (Fase 1)
2. Implementar System Prompt Hierarquico (Fase 2)
3. Testar Speculative Decoding (Fase 3)
4. Gerar dataset sintetico inicial (Fase 4)
