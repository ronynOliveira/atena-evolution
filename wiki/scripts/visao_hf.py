#!/usr/bin/env python3
"""
Módulo de Visão Computacional do OWL - Versão HuggingFace.
Usa modelos gratuitos do HuggingFace para:
- Image captioning (BLIP)
- OCR (EasyOCR)
- Detecção de objetos (YOLO via ultralytics)
- Análise de documentos

Autor: OWL (Batedor da Nuvem)
Data: 2026-05-20
"""

import subprocess
import sys
import os
import json
import tempfile
import base64
from pathlib import Path
from typing import Optional, Dict, List, Any
from PIL import Image, ImageDraw

from lib import log_info, log_error, get_temp_path

# ═══════════════════════════════════════════
# IMAGE COM HUGGINGFACE (BLIP)
# ═══════════════════════════════════════════

def gerar_caption_blip(caminho_imagem: str, modelo: str = "Salesforce/blip-image-captioning-base") -> Optional[str]:
    """Gera descrição de imagem usando BLIP do HuggingFace."""
    try:
        from transformers import pipeline
        
        log_info(f"BLIP: gerando caption para {caminho_imagem}")
        captioner = pipeline('image-to-text', model=modelo, device=-1)
        resultado = captioner(caminho_imagem, max_new_tokens=50)
        
        if resultado and len(resultado) > 0:
            texto = resultado[0].get('generated_text', '')
            log_info(f"BLIP: caption gerada: {texto[:100]}")
            return texto
        return None
    except ImportError:
        log_error("BLIP: transformers não instalado. Execute: pip install transformers torch")
        return None
    except Exception as e:
        log_error(f"BLIP: erro: {e}")
        return None


def responder_pergunta_sobre_imagem(caminho_imagem: str, pergunta: str) -> Optional[str]:
    """Responde uma pergunta específica sobre uma imagem usando VQA."""
    try:
        from transformers import pipeline
        
        log_info(f"VQA: respondendo '{pergunta[:50]}...' sobre {caminho_imagem}")
        vqa = pipeline('visual-question-answering', model='Salesforce/blip-vqa-base', device=-1)
        
        resultado = vqa(caminho_imagem, pergunta, top_k=1)
        if resultado and len(resultado) > 0:
            resposta = resultado[0].get('answer', '')
            score = resultado[0].get('score', 0)
            log_info(f"VQA: resposta: {resposta} (confiança: {score:.2f})")
            return resposta
        return None
    except ImportError:
        log_error("VQA: transformers não instalado")
        return None
    except Exception as e:
        log_error(f"VQA: erro: {e}")
        return None


# ═══════════════════════════════════════════
# OCR COM EASYOCR
# ═══════════════════════════════════════════

def extrair_texto_ocr(caminho_imagem: str, idiomas: List[str] = None) -> List[Dict]:
    """Extrai texto de imagem usando EasyOCR."""
    if idiomas is None:
        idiomas = ['pt', 'en']
    
    try:
        import easyocr
        
        log_info(f"EasyOCR: extraindo texto de {caminho_imagem}")
        
        # Lazy init do reader
        if not hasattr(extrair_texto_ocr, '_reader'):
            extrair_texto_ocr._reader = easyocr.Reader(idiomas, gpu=False)
        
        resultados = extrair_texto_ocr._reader.readtext(caminho_imagem)
        
        textos = []
        for (bbox, texto, confianca) in resultados:
            textos.append({
                'texto': texto,
                'confianca': confianca,
                'bbox': bbox
            })
        
        log_info(f"EasyOCR: {len(textos)} regiões de texto detectadas")
        return textos
    except ImportError:
        log_error("EasyOCR: não instalado. Execute: pip install easyocr")
        return []
    except Exception as e:
        log_error(f"EasyOCR: erro: {e}")
        return []


# ═══════════════════════════════════════════
# DETECÇÃO DE OBJETOS COM YOLO
# ═══════════════════════════════════════════

def detectar_objetos_yolo(caminho_imagem: str, confianca: float = 0.5) -> List[Dict]:
    """Detecta objetos em imagem usando YOLO."""
    try:
        from ultralytics import YOLO
        
        log_info(f"YOLO: detectando objetos em {caminho_imagem}")
        
        # Lazy init do modelo
        if not hasattr(detectar_objetos_yolo, '_model'):
            detectar_objetos_yolo._model = YOLO('yolov8n.pt')
        
        resultados = detectar_objetos_yolo._model(caminho_imagem, conf=confianca)
        
        objetos = []
        for resultado in resultados:
            for box in resultado.boxes:
                objetos.append({
                    'classe': resultado.names[int(box.cls)],
                    'confianca': float(box.conf),
                    'bbox': box.xyxy.tolist()[0]
                })
        
        log_info(f"YOLO: {len(objetos)} objetos detectados")
        return objetos
    except ImportError:
        log_error("YOLO: ultralytics não instalado. Execute: pip install ultralytics")
        return []
    except Exception as e:
        log_error(f"YOLO: erro: {e}")
        return []


# ═══════════════════════════════════════════
# ANÁLISE DE DOCUMENTOS
# ═══════════════════════════════════════════

def analisar_documento_completo(caminho: str) -> Dict[str, Any]:
    """Análise completa de um documento (imagem ou PDF)."""
    resultado = {
        'caminho': caminho,
        'tipo': None,
        'texto_ocr': [],
        'caption': None,
        'objetos': [],
        'erro': None
    }
    
    try:
        # Verificar se é PDF
        if caminho.lower().endswith('.pdf'):
            resultado['tipo'] = 'pdf'
            # Extrair imagens do PDF
            try:
                import fitz
                doc = fitz.open(caminho)
                imagens = []
                for i, page in enumerate(doc):
                    pix = page.get_pixmap()
                    img_path = get_temp_path(f'pdf_page_{i}.png')
                    pix.save(img_path)
                    imagens.append(img_path)
                doc.close()
                resultado['imagens_extraidas'] = len(imagens)
                
                # Analisar primeira imagem
                if imagens:
                    resultado['texto_ocr'] = extrair_texto_ocr(imagens[0])
                    resultado['caption'] = gerar_caption_blip(imagens[0])
            except ImportError:
                log_error("PyMuPDF não instalado para análise de PDF")
        else:
            # É imagem
            resultado['tipo'] = 'imagem'
            resultado['texto_ocr'] = extrair_texto_ocr(caminho)
            resultado['caption'] = gerar_caption_blip(caminho)
            resultado['objetos'] = detectar_objetos_yolo(caminho)
        
        log_info(f"Documento analisado: {resultado['tipo']}")
        return resultado
    except Exception as e:
        resultado['erro'] = str(e)
        log_error(f"Erro na análise do documento: {e}")
        return resultado


# ═══════════════════════════════════════════
# TESTE COMPLETO
# ═══════════════════════════════════════════

def testar_visao():
    """Testa todas as funcionalidades de visão."""
    print("=" * 60)
    print("TESTE DO MÓDULO DE VISÃO COMPUTACIONAL")
    print("=" * 60)
    
    # Criar imagem de teste
    img = Image.new('RGB', (400, 200), color='white')
    draw = ImageDraw.Draw(img)
    draw.text((50, 80), 'Teste de Visao OWL', fill='black')
    draw.rectangle([50, 50, 150, 150], fill='red', outline='black')
    img.save('/tmp/teste_visao_hf.png')
    
    print("\n[1/4] Testando BLIP (image captioning)...")
    caption = gerar_caption_blip('/tmp/teste_visao_hf.png')
    if caption:
        print(f"  OK: {caption}")
    else:
        print("  FALHA")
    
    print("\n[2/4] Testando EasyOCR...")
    textos = extrair_texto_ocr('/tmp/teste_visao_hf.png')
    if textos:
        print(f"  OK: {len(textos)} regiões detectadas")
        for t in textos[:3]:
            print(f"    - {t['texto']} ({t['confianca']:.2f})")
    else:
        print("  Nenhum texto detectado")
    
    print("\n[3/4] Testando YOLO (detecção de objetos)...")
    objetos = detectar_objetos_yolo('/tmp/teste_visao_hf.png')
    if objetos:
        print(f"  OK: {len(objetos)} objetos detectados")
        for o in objetos[:3]:
            print(f"    - {o['classe']} ({o['confianca']:.2f})")
    else:
        print("  Nenhum objeto detectado")
    
    print("\n[4/4] Testando análise completa...")
    resultado = analisar_documento_completo('/tmp/teste_visao_hf.png')
    print(f"  Tipo: {resultado['tipo']}")
    print(f"  Caption: {resultado['caption'][:50] if resultado['caption'] else 'N/A'}...")
    print(f"  OCR: {len(resultado['texto_ocr'])} regiões")
    print(f"  Objetos: {len(resultado['objetos'])} detectados")
    
    print("\n" + "=" * 60)
    print("TESTE CONCLUÍDO")
    print("=" * 60)


if __name__ == '__main__':
    testar_visao()
