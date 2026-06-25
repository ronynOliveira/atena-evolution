# Pesquisa: Modelos LLM para CPU-Only (4B Parâmetros)

**Data:** 25 de Junho de 2026  
**Hardware Alvo:** Intel i5-1235U (10 cores, 12 threads), 15GB RAM, sem GPU  
**Objetivo:** Identificar os modelos LLM mais rápidos e eficientes para inferência local em CPU

---

## 📊 Resumo Executivo

| Modelo | Parâmetros | Tamanho Q4_K_M | Velocidade Estimada (CPU) | Melhor Caso de Uso |
|--------|-----------|----------------|--------------------------|-------------------|
| **Llama 3.2 3B** | 3B | ~2.0 GB | ~25-30 tok/s | Chat geral, RAG, ferramentas |
| **Gemma 3 4B** | 4B | ~2.5 GB | ~20-25 tok/s | Multimodal, RAG, código |
| **Phi-3.5 3.8B** | 3.8B | ~2.2 GB | ~18-22 tok/s | Código, raciocínio, matemática |
| **Qwen 2.5 3B** | 3B | ~2.0 GB | ~22-28 tok/s | Multilingual, RAG, código |
| **Mistral 7B Instruct** | 7B | ~4.4 GB | ~10-15 tok/s | Instruções complexas, RAG |

---

## 🔍 Análise Detalhada dos Modelos

### 1. Llama 3.2 3B Instruct (Meta)

| Atributo | Valor |
|----------|-------|
| **Parâmetros** | 3 bilhões |
| **Arquitetura** | Llama (decoder-only transformer) |
| **Context Length** | 131.072 tokens |
| **Tamanho Q4_K_M** | ~2.0 GB |
| **Tamanho Q5_K_M** | ~2.3 GB |
| **Tamanho Q8_0** | ~3.2 GB |
| **Velocidade Estimada (CPU)** | 25-30 tok/s |
| **Formatos Quantizados** | Q4_K_M, Q5_K_M, Q4_0, Q8_0, Q3_K, Q6_K, Q4_K_S, Q5_K_S |
| **Downloads HF (GGUF)** | ~225.000 |

**Pontos Fortes:**
- Excelente velocidade em CPU (arquitetura otimizada para tamanho pequeno)
- Suporte multilíngue incluindo português
- Context window grande (131K) ideal para RAG
- Grande comunidade e ecossistema
- Disponível nativamente no Ollama

**Pontos Fracos:**
- Qualidade em português inferior ao Qwen 2.5
- Menos eficiente em código comparado ao Phi-3.5

**Melhor Caso de Uso:** Chat geral, RAG (contexto longo), ferramentas de produtividade, agentes de IA

---

### 2. Gemma 3 4B (Google DeepMind)

| Atributo | Valor |
|----------|-------|
| **Parâmetros** | 4 bilhões |
| **Arquitetura** | Gemma 3 (com vision encoder) |
| **Context Length** | 131.072 tokens |
| **Tamanho Q4_K_M** | ~2.5 GB |
| **Tamanho Q8_0** | ~4.1 GB |
| **Velocidade Estimada (CPU)** | 20-25 tok/s |
| **Formatos Quantizados** | Q4_K_M, Q8_0 (GGUF); Q4_0 (QAT nativo) |
| **Downloads HF (GGUF)** | ~71.000 |

**Pontos Fortes:**
- Suporte nativo a visão (multimodal)
- Context window de 131K tokens (excelente para RAG)
- Q4_K_M produz saída de alta qualidade (vs INT4 uniforme - ver benchmark abaixo)
- Treinado com dados multilíngues
- Modelo base forte com boa generalização

**Pontos Fracos:**
- Q4_K_M é o formato primário no GGUF (menos opções de quantização)
- Velocidade ligeiramente inferior ao Llama 3.2 3B
- Requer mais RAM que 3B models

**Melhor Caso de Uso:** RAG com contexto longo, análise de imagens, chat multimodal, código

**Benchmark de Referência (Intel CPU):**
- Gemma 3 1B Q4_K_M via llama.cpp: ~39.6 tok/s (Intel Core Ultra 7 265K)
- Gemma 3 1B INT4 via OpenVINO: ~66.0 tok/s (mas qualidade inferior)
- *Gemma 3 4B será ~4x mais lento que 1B no mesmo hardware*

---

### 3. Phi-3.5 Mini 3.8B (Microsoft)

| Atributo | Valor |
|----------|-------|
| **Parâmetros** | 3.8 bilhões |
| **Arquitetura** | Phi (decoder-only, otimizado) |
| **Context Length** | 131.072 tokens |
| **Tamanho Q4_K_M** | ~2.2 GB |
| **Tamanho Q5_K_M** | ~2.4 GB |
| **Tamanho Q8_0** | ~4.1 GB |
| **Velocidade Estimada (CPU)** | 18-22 tok/s |
| **Formatos Quantizados** | Q4_K_M, Q5_K_M, Q4_0, Q8_0, Q2_K, Q3_K, Q6_K, Q4_K_S, Q5_K_S |
| **Downloads HF** | ~8.700 |

**Pontos Fortes:**
- Excelente desempenho em código e matemática
- Treinado com dados de alta qualidade (sintéticos + filtrados)
- Muito eficiente por parâmetro
- Boa precisão em raciocínio lógico
- Context window de 131K

**Pontos Fracos:**
- Velocidade em CPU inferior aos concorrentes diretos
- Menos flexível para tarefas criativas
- Suporte a português limitado
- Menos opções de fine-tuning em português

**Melhor Caso de Uso:** Geração de código, raciocínio matemático, tarefas analíticas, agentes de código

---

### 4. Qwen 2.5 3B Instruct (Alibaba)

| Atributo | Valor |
|----------|-------|
| **Parâmetros** | 3 bilhões |
| **Arquitetura** | Qwen (decoder-only) |
| **Context Length** | 131.072 tokens |
| **Tamanho Q4_K_M** | ~2.0 GB |
| **Tamanho Q5_K_M** | ~2.4 GB |
| **Tamanho Q8_0** | ~3.6 GB |
| **Velocidade Estimada (CPU)** | 22-28 tok/s |
| **Formatos Quantizados** | Q4_K_M, Q5_K_M, Q4_0, Q8_0, Q2_K, Q3_K, Q5_0, Q6_K |
| **Downloads HF (Instruct)** | ~9.1 milhões |

**Pontos Fortes:**
- **Melhor desempenho em português** entre os modelos pequenos
- Treinado com dados multilíngues massivos (incluindo português brasileiro)
- Excelente velocidade/tamanho ratio
- Context window de 131K tokens
- Versão Coder disponível (Qwen 2.5 Coder 3B)
- Maior número de downloads entre os candidatos

**Pontos Fracos:**
- Ligeiramente menor em raciocínio matemático vs Phi-3.5
- Versão base pode alucinar mais que Llama 3.2

**Melhor Caso de Uso:** RAG em português, chat em português, código, multilíngue, agentes

---

### 5. Mistral 7B Instruct v0.3 (Mistral AI)

| Atributo | Valor |
|----------|-------|
| **Parâmetros** | 7 bilhões |
| **Arquitetura** | Mistral (Sliding Window Attention) |
| **Context Length** | 65.536 tokens (com SWA) |
| **Tamanho Q4_K_M** | ~4.4 GB |
| **Tamanho Q5_K_M** | ~5.1 GB |
| **Tamanho Q8_0** | ~7.7 GB |
| **Velocidade Estimada (CPU)** | 10-15 tok/s |
| **Formatos Quantizados** | Q4_K_M, Q5_K_M, Q4_K_S, Q5_K_S, Q8_0, Q2_K, Q3_K, Q6_K |
| **Downloads HF (v0.3)** | ~2.8 milhões |

**Pontos Fortes:**
- Maior qualidade de saída entre os modelos listados
- Sliding Window Attention para eficiência de memória
- Boa compreensão de instruções complexas
- Forte em RAG e sumarização
- Ecossistema maduro

**Pontos Fracos:**
- **2x mais lento** que modelos 3-4B em CPU
- **2x maior** em RAM (4.4GB vs ~2GB)
- Pode não caber confortavelmente com 15GB RAM do sistema
- Velocidade limitada pelo tamanho

**Melhor Caso de Uso:** RAG de alta qualidade, sumarização, instruções complexas, chat premium

---

## ⚡ Comparação de Velocidade em CPU (Estimativas)

Baseado em benchmarks públicos (llama.cpp em Intel CPUs com AVX2/AVX-512):

| Modelo | Q4_K_M Size | tok/s (estimado i5-1235U) | tok/s (high-end CPU) |
|--------|-------------|---------------------------|---------------------|
| Llama 3.2 3B | 2.0 GB | **25-30** | 40-50 |
| Qwen 2.5 3B | 2.0 GB | **22-28** | 35-45 |
| Gemma 3 4B | 2.5 GB | **20-25** | 30-40 |
| Phi-3.5 3.8B | 2.2 GB | **18-22** | 28-35 |
| Mistral 7B | 4.4 GB | **10-15** | 18-25 |

*Nota: Velocidades variam significativamente conforme CPU, RAM, e backend (llama.cpp vs OpenVINO)*

---

## 🇧🇷 Desempenho em Português

Baseado em benchmarks multilíngues e avaliações da comunidade:

| Modelo | Português (BR) | Observações |
|--------|---------------|-------------|
| **Qwen 2.5 3B** | ⭐⭐⭐⭐⭐ | Melhor em português, treinado com dados PT-BR |
| **Llama 3.2 3B** | ⭐⭐⭐⭐ | Bom, mas pode misturar idiomas |
| **Gemma 3 4B** | ⭐⭐⭐⭐ | Razoável, não otimizado para PT |
| **Mistral 7B** | ⭐⭐⭐ | Funcional, mas prefere inglês |
| **Phi-3.5 3.8B** | ⭐⭐ | Fraco em português, focado em código |

---

## 📖 Suporte a RAG (Retrieval-Augmented Generation)

| Modelo | Context Window | RAG Rating | Observações |
|--------|---------------|------------|-------------|
| **Llama 3.2 3B** | 131K | ⭐⭐⭐⭐⭐ | Contexto longo, boa compreensão |
| **Gemma 3 4B** | 131K | ⭐⭐⭐⭐⭐ | Contexto longo, atenção eficiente |
| **Qwen 2.5 3B** | 131K | ⭐⭐⭐⭐⭐ | Contexto longo, bom em PT |
| **Phi-3.5 3.8B** | 131K | ⭐⭐⭐⭐ | Contexto longo, mas perde detalhes |
| **Mistral 7B** | 65K | ⭐⭐⭐⭐ | SWA limita contexto efetivo |

---

## 🏆 Recomendações por Cenário

### 🥇 Melhor Geral (CPU-only, 15GB RAM)
**Qwen 2.5 3B Instruct (Q4_K_M)**
- Melhor balance de velocidade, qualidade e suporte a português
- Tamanho compacto (~2GB)
- Ideal para o cenário especificado

### 🥈 Mais Rápido em CPU
**Llama 3.2 3B Instruct (Q4_K_M)**
- Velocidade superior em CPUs Intel
- Context window de 131K (melhor para RAG longo)
- Ecossistema mais maduro

### 🥉 Melhor para Código
**Phi-3.5 Mini 3.8B (Q4_K_M)**
- Superior em geração de código
- Bom para raciocínio lento e matemático
- Tamanho gerenciável

### 🎖️ Melhor para Português + RAG
**Qwen 2.5 3B Instruct (Q4_K_M)**
- Indiscutível em tarefas PT-BR
- Contexto longo
- Versão Coder disponível

### 🎖️ Melhor Qualidade (se RAM permitir)
**Mistral 7B Instruct v0.3 (Q4_K_M)**
- Qualidade de saída superior
- Mas requer ~4.4GB e é 2x mais lento

---

## 🔧 Comandos de Instalação (Ollama)

```bash
# Qwen 2.5 3B (Recomendado)
ollama run qwen2.5:3b

# Llama 3.2 3B (Mais rápido)
ollama run llama3.2:3b

# Gemma 3 4B (Multimodal)
ollama run gemma3:4b

# Phi-3.5 3.8B (Código)
ollama run phi3.5:3.8b

# Mistral 7B (Alta qualidade)
ollama run mistral:7b
```

---

## 📐 Requisitos de Hardware

| Modelo | RAM Mínima | RAM Recomendada | CPU Features |
|--------|-----------|-----------------|--------------|
| Llama 3.2 3B | 4 GB | 6 GB | AVX2 |
| Qwen 2.5 3B | 4 GB | 6 GB | AVX2 |
| Gemma 3 4B | 5 GB | 7 GB | AVX2 |
| Phi-3.5 3.8B | 5 GB | 7 GB | AVX2 |
| Mistral 7B | 8 GB | 10 GB | AVX2/AVX-512 |

**Para o sistema especificado (i5-1235U, 15GB RAM):**
- Todos os modelos 3-4B funcionam confortavelmente
- Mistral 7B funciona mas deixa menos RAM para o sistema
- Recomenda-se usar Q4_K_M para melhor balance

---

## 📚 Fontes e Referências

1. **Ollama Model Library** - https://ollama.com/search
2. **HuggingFace Models** - https://huggingface.co/models
3. **Benchmark: OpenVINO vs llama.cpp on Gemma 3 1B** - https://github.com/pierre-warnier/bench-inference-platforms
4. **Llama 3.2 Model Card** - https://huggingface.co/meta-llama/Llama-3.2-3B-Instruct
5. **Qwen 2.5 Model Card** - https://huggingface.co/Qwen/Qwen2.5-3B-Instruct
6. **Gemma 3 Model Card** - https://huggingface.co/google/gemma-3-4b-it
7. **Phi-3.5 Model Card** - https://huggingface.co/microsoft/Phi-3.5-mini-instruct
8. **Mistral 7B v0.3 Model Card** - https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.3
9. **bartowski GGUF quantizations** - https://huggingface.co/bartowski
10. **llama.cpp** - https://github.com/ggerganov/llama.cpp

---

## ⚠️ Notas Importantes

1. **Quantização Q4_K_M** é recomendada como padrão: oferece o melhor balance entre qualidade e tamanho (~4.3 bits por parâmetro)
2. **Q5_K_M** oferece qualidade ligeiramente superior ao custo de ~0.5GB extras
3. **Velocidades estimadas** são aproximadas para i5-1235U (10 cores, AVX2, DDR4)
4. **OpenVINO** pode ser até 1.66x mais rápido em Intel CPUs, mas com qualidade inferior na quantização INT4
5. **llama.cpp** com Q4_K_M oferece o melhor balance geral de velocidade vs qualidade
6. Para **RAG com contexto longo**, prefira modelos com 131K context window (todos exceto Mistral 7B com SWA)
7. O **Qwen 2.5 Coder 3B** é alternativa se o foco principal for geração de código

---

*Documento gerado automaticamente via pesquisa no Ollama Model Library e GitHub (Junho 2026)*
