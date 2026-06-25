---
title: Capacidade de Visão e Multimodal do OWL
created: 2026-05-20
updated: 2026-05-20
type: concept
tags: [visao, multimodal, imagem, pdf, audio, video, ollama]
sources: []
confidence: high
---

# Capacidade de Visão e Multimodal do OWL

## Estado Atual

### O que JÁ temos instalado e funcionando:

| Ferramenta | Status | Uso |
|---|---|---|
| **gemma4:e4b** | ✅ Instalado | Multimodal (texto+imagem+áudio+vídeo) |
| **gemma4:e2b** | ✅ Instalado | Multimodal (texto+imagem+áudio+vídeo) |
| **faster-whisper** | ✅ Instalado | Transcrição de áudio |
| **openai-whisper** | ✅ Instalado | Transcrição de áudio |
| **opencv-python** | ✅ Instalado | Processamento de imagem/vídeo |
| **pillow** | ✅ Instalado | Manipulação de imagem |
| **PyMuPDF** | ✅ Instalado | Processamento de PDF |
| **pypdf** | ✅ Instalado | Leitura de PDF |
| **torchvision** | ✅ Instalado | Visão computacional |

### O que PODEMOS fazer agora:

1. **Imagens** — gemma4:e4b aceita imagens (vision capable)
2. **PDFs** — PyMuPDF e pypdf para extrair texto
3. **Áudio** — faster-whisper para transcrição
4. **Vídeo** — OpenCV para extrair frames + gemma4 para analisar

### Limitação atual:
- **Sem GPU dedicada** (Intel Iris Xe apenas)
- Modelos de visão são **muito lentos** em CPU
- gemma4:e4b com visão pode levar minutos para processar uma imagem

---

## Modelos de Visão Disponíveis para Instalação

### Leves (funcionam em CPU, mais lentos):
| Modelo | Tamanho | VRAM | CPU |
|---|---|---|---|
| **LLaVA 7B** | ~4.7GB | 4-6GB | Funciona, lento |
| **PaddleOCR-VL 0.9B** | ~1GB | 1GB | Rápido em CPU |

### Pesados (precisam GPU dedicada):
| Modelo | Tamanho | VRAM | Notas |
|---|---|---|---|
| **Llama 3.2-Vision 11B** | ~8GB | 8GB | Excelente para documentos |
| **LLaVA 34B** | ~20GB | 20GB | Melhor OCR |
| **Qwen 3.6-27B** | ~17GB | 17GB | SOTA local |

---

## Como Usar (quando funcionando)

### Imagens com gemma4:e4b:
```python
import ollama
resp = ollama.chat(
    model='gemma4:e4b',
    messages=[{
        'role': 'user',
        'content': 'Descreva esta imagem',
        'images': ['caminho/para/imagem.jpg']
    }]
)
print(resp['message']['content'])
```

### PDF com PyMuPDF:
```python
import fitz
doc = fitz.open("arquivo.pdf")
for page in doc:
    text = page.get_text()
    print(text)
```

### Áudio com Whisper:
```python
import whisper
model = whisper.load_model("base")
result = model.transcribe("audio.mp3")
print(result["text"])
```

### Vídeo com OpenCV:
```python
import cv2
cap = cv2.VideoCapture("video.mp4")
while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break
    # Processar frame
cap.release()
```

---

## Recomendações para o Arquiteto

### Opção 1: Usar o que já temos (gratuito, lento)
- gemma4:e4b para imagens (lento mas funcional)
- PyMuPDF para PDFs (rápido)
- faster-whisper para áudio (funcional)

### Opção 2: Instalar modelos mais leves (gratuito, mais rápido)
- PaddleOCR-VL 0.9B para OCR rápido em CPU
- LLaVA 7B para visão mais leve

### Opção 3: Adicionar GPU dedicada (custo)
- RTX 3060 12GB (~$300) — roda 7B-11B vision confortavelmente
- RTX 4090 24GB (~$1,100) — roda até 32B vision

---

## Ver também
- [[hermes-agent]]
- [[ambiente-tecnico]]
- [[plano-contingencia]]
