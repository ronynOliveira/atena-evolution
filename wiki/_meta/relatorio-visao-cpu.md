---
title: Relatório de Visão Computacional — Alternativas para CPU
created: 2026-05-20
updated: 2026-05-20
type: query
tags: [visao-computacional, cpu, ollama, huggingface, alternativas]
sources: []
confidence: high
---

# Relatório de Visão Computacional — Alternativas para CPU

## Data: 20/05/2026

## Modelos Testados e Funcionando

### ✅ Já instalados e funcionando:

| Modelo | Tipo | Tempo CPU | Status |
|---|---|---|---|
| **BLIP-base** | Image Captioning | ~8s | ✅ Funcionando |
| **EasyOCR** | OCR | ~4s | ✅ Funcionando |
| **YOLOv8n** | Detecção Objetos | ~140ms | ✅ Funcionando |
| **gemma4:e4b** | Visão+Linguagem | Lento | ✅ Funcionando |
| **OpenCV** | Processamento | Instantâneo | ✅ Funcionando |

## Alternativas Pesquisadas (Gemini + Opencode)

### 1. Image Captioning Mais Leve que BLIP

**microsoft/git-base-coco**
- Mais leve que BLIP-base
- Arquitetura GIT (Generative Image Transformer)
- Bom equilíbrio tamanho/velocidade/qualidade
- Instalação: `pip install transformers torch accelerate`

**Moondream (GGUF)**
- Modelo extremamente pequeno para edge/CPU
- Formato GGUF via llama-cpp-python
- Instalação: `pip install llama-cpp-python`
- Download: ~5GB do Hugging Face

### 2. OCR Alternativo ao EasyOCR

**PaddleOCR**
- Mais rápido que EasyOCR em CPU
- Suporte robusto para português
- Já instalado (problema de compatibilidade com oneDNN)
- Instalação: `pip install paddleocr paddlepaddle`

### 3. Detecção de Objetos Mais Leve que YOLO

**RT-DETR (Real-Time Detection Transformer)**
- Melhor performance em CPU que YOLO
- Arquitetura Transformer otimizada
- Via ultralytics: `pip install ultralytics`

### 4. Modelos GGUF para Visão

**Moondream**
- Modelo visão+linguagem em formato GGUF
- Roda via llama-cpp-python
- Ideal para CPU

**LLaVA-1.5 (GGUF)**
- Mais poderoso que Moondream
- Também disponível em GGUF

### 5. Otimizações para BLIP em CPU

**Quantização Dinâmica (PyTorch)**
```python
import torch
model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")
quantized_model = torch.quantization.quantize_dynamic(
    model, {torch.nn.Linear}, dtype=torch.qint8
)
```

**ONNX + Optimum**
```bash
pip install optimum[onnxruntime]
```
```python
from optimum.onnxruntime import ORTModelForVision2Seq
model = ORTModelForVision2Seq.from_pretrained("Salesforce/blip-image-captioning-base", export=True)
model.save_pretrained("blip-onnx")
```

## Recomendação Final

Para nossa máquina (i5-1235U, 15.7GB RAM, sem GPU):

1. **Image Captioning**: Continuar com BLIP-base (já instalado)
   - Opcional: testar GIT-base quando download completar
   - Opcional: BLIP quantizado com ONNX para velocidade

2. **OCR**: EasyOCR (já funcionando)
   - PaddleOCR como alternativa (já instalado, precisa corrigir oneDNN)

3. **Detecção de Objetos**: YOLOv8n (já funcionando, ~140ms)
   - RT-DETR como alternativa futura

4. **Visão + Linguagem**: gemma4:e4b via Ollama (já instalado)
   - Moondream GGUF como alternativa mais leve

## Arquivos Criados

- `lib/visao.py` — Módulo de visão (gemma4 + EasyOCR + OpenCV)
- `lib/visao_hf.py` — Módulo de visão (BLIP + YOLO + EasyOCR)
- `tests/test_visao.py` — Testes unitários
- `analisar_pdf.py` — Análise de PDFs com visão
- `comparar_modelos_visao.py` — Script de comparação

## Ver também
- [[capacidade-visao]]
- [[hermes-agent]]
- [[plano-contingencia]]
