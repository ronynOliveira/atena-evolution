"""
Módulo de Visão Computacional
═══════════════════════════════════════════════════════════════
Integra gemma4 (via Ollama), EasyOCR e OpenCV para análise
de imagens, extração de texto, detecção de objetos e mais.

Autor: OWL (Batedor da Nuvem)
Data: 2026-05-20
"""

from __future__ import annotations

import os
import sys
import json
import tempfile
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

from lib import log_info, log_error, get_temp_path

# ═══════════════════════════════════════════════════════════════
# IMPORTS OPCIONAIS — carregados sob demanda
# ═══════════════════════════════════════════════════════════════

_easyocr_reader = None


def _get_easyocr_reader(idioma: str = "pt"):
    """Lazy-init do EasyOCR reader (custo alto de carregamento)."""
    global _easyocr_reader
    if _easyocr_reader is None:
        import easyocr
        log_info(f"EasyOCR: inicializando reader para idioma '{idioma}'...")
        idiomas = [idioma]
        if idioma != "en":
            idiomas.append("en")
        _easyocr_reader = easyocr.Reader(idiomas, gpu=True, verbose=False)
        log_info("EasyOCR: reader inicializado com sucesso.")
    return _easyocr_reader


def _check_file(caminho: str) -> Path:
    """Valida que o arquivo de imagem existe e é legível."""
    p = Path(caminho)
    if not p.exists():
        raise FileNotFoundError(f"Imagem não encontrada: {caminho}")
    if not p.is_file():
        raise ValueError(f"Caminho não é um arquivo: {caminho}")
    return p


def _image_to_base64(caminho: str) -> str:
    """Converte imagem para base64 (necessário para Ollama)."""
    import base64
    with open(caminho, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _ollama_vision(prompt: str, image_b64: str, modelo: str = "gemma3:e4b") -> str:
    """Chama Ollama com imagem em base64 e retorna resposta."""
    import ollama
    try:
        resposta = ollama.chat(
            model=modelo,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                    "images": [image_b64],
                }
            ],
            options={"temperature": 0.2, "num_predict": 1024},
        )
        return resposta["message"]["content"].strip()
    except Exception as e:
        log_error(f"Ollama vision falhou: {e}")
        raise


# ═══════════════════════════════════════════════════════════════
# 1. ANÁLISE COM GEMMA4
# ═══════════════════════════════════════════════════════════════

def ler_imagem_com_gemma4(
    caminho_imagem: str,
    pergunta: str,
    modelo: str = "gemma3:e4b",
) -> str:
    """
    Usa Ollama gemma3:e4b para analisar uma imagem com uma pergunta.

    Args:
        caminho_imagem: Path absoluto para o arquivo de imagem.
        pergunta: Pergunta sobre a imagem (ex: "O que está escrito?").
        modelo: Modelo Ollama a usar (padrão: gemma3:e4b).

    Returns:
        Resposta textual do modelo de visão.

    Raises:
        FileNotFoundError: Se a imagem não existir.
        RuntimeError: Se o Ollama não responder.

    Exemplo:
        >>> resp = ler_imagem_com_gemma4("/tmp/foto.jpg", "Quantas pessoas há?")
        >>> print(resp)
        'Há 3 pessoas na imagem.'
    """
    _check_file(caminho_imagem)
    log_info(f"Gemma4: analisando '{caminho_imagem}' — pergunta: {pergunta[:60]}...")

    try:
        b64 = _image_to_base64(caminho_imagem)
        resposta = _ollama_vision(pergunta, b64, modelo)
        log_info(f"Gemma4: resposta obtida ({len(resposta)} chars).")
        return resposta
    except Exception as e:
        log_error(f"Gemma4: falha ao analisar imagem: {e}")
        raise RuntimeError(f"Falha na análise com Gemma4: {e}") from e


# ═══════════════════════════════════════════════════════════════
# 2. OCR COM EASYOCR
# ═══════════════════════════════════════════════════════════════

def extrair_texto_com_easyocr(
    caminho_imagem: str,
    idioma: str = "pt",
) -> List[Dict[str, Any]]:
    """
    Usa EasyOCR para extrair texto de imagens.

    Args:
        caminho_imagem: Path absoluto para o arquivo de imagem.
        idioma: Idioma do texto (padrão: 'pt' para português).
                Exemplos: 'pt', 'en', 'es', 'fr'.

    Returns:
        Lista de dicionários com chaves:
            - 'texto': str — texto detectado
            - 'confianca': float — confiança 0.0–1.0
            - 'bbox': list — bounding box [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]

    Raises:
        FileNotFoundError: Se a imagem não existir.
        RuntimeError: Se o EasyOCR falhar.

    Exemplo:
        >>> resultados = extrair_texto_com_easyocr("/tmp/doc.png")
        >>> for r in resultados:
        ...     print(f"{r['texto']} ({r['confianca']:.1%})")
    """
    _check_file(caminho_imagem)
    log_info(f"EasyOCR: extraindo texto de '{caminho_imagem}' (idioma={idioma})...")

    try:
        import cv2
        reader = _get_easyocr_reader(idioma)
        imagem_cv = cv2.imread(str(caminho_imagem))
        if imagem_cv is None:
            raise ValueError(f"OpenCV não conseguiu ler: {caminho_imagem}")

        raw = reader.readtext(imagem_cv)
        resultados = []
        for (bbox, texto, conf) in raw:
            resultados.append({
                "texto": texto.strip(),
                "confianca": round(float(conf), 4),
                "bbox": [[int(c[0]), int(c[1])] for c in bbox],
            })

        log_info(f"EasyOCR: {len(resultados)} regiões de texto detectadas.")
        return resultados
    except Exception as e:
        log_error(f"EasyOCR: falha ao extrair texto: {e}")
        raise RuntimeError(f"Falha no OCR: {e}") from e


def extrair_texto_completo(caminho_imagem: str, idioma: str = "pt") -> str:
    """
    Extrai todo o texto de uma imagem como string única.

    Args:
        caminho_imagem: Path para a imagem.
        idioma: Idioma do texto.

    Returns:
        Texto completo extraído, com quebras de linha entre regiões.
    """
    resultados = extrair_texto_com_easyocr(caminho_imagem, idioma)
    linhas = [r["texto"] for r in resultados if r["texto"]]
    return "\n".join(linhas)


# ═══════════════════════════════════════════════════════════════
# 3. DETECÇÃO DE OBJETOS COM OPENCV
# ═══════════════════════════════════════════════════════════════

def detectar_objetos_com_opencv(
    caminho_imagem: str,
    limiar_confianca: float = 0.5,
) -> Dict[str, Any]:
    """
    Usa OpenCV para detectar objetos, bordas e contornos em uma imagem.

    Usa DNN com MobileNet-SSD (se disponível) ou fallback para
    detecção de contornos clássica.

    Args:
        caminho_imagem: Path absoluto para o arquivo de imagem.
        limiar_confiança: Limiar mínimo para detecções (0.0–1.0).

    Returns:
        Dicionário com:
            - 'largura': int — largura da imagem
            - 'altura': int — altura da imagem
            - 'canais': int — número de canais de cor
            - 'contornos': int — número de contornos detectados
            - 'bordas': int — número de pixels de borda (Canny)
            - 'objetos_dnn': list — detecções DNN (se modelo disponível)
            - 'cores_dominantes': list — top 5 cores dominantes (BGR)
            - 'brilho_medio': float — brilho médio (0–255)
            - 'contraste': float — desvio padrão de intensidade

    Raises:
        FileNotFoundError: Se a imagem não existir.
        RuntimeError: Se o OpenCV falhar.

    Exemplo:
        >>> info = detectar_objetos_com_opencv("/tmp/foto.jpg")
        >>> print(f"Dimensões: {info['largura']}x{info['altura']}")
        >>> print(f"Contornos: {info['contornos']}")
    """
    _check_file(caminho_imagem)
    log_info(f"OpenCV: analisando '{caminho_imagem}'...")

    try:
        import cv2
        import numpy as np

        img = cv2.imread(str(caminho_imagem))
        if img is None:
            raise ValueError(f"OpenCV não conseguiu ler: {caminho_imagem}")

        altura, largura = img.shape[:2]
        canais = img.shape[2] if len(img.shape) == 3 else 1

        # ── Análise de cor ──
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if canais == 3 else img
        brilho_medio = float(np.mean(gray))
        contraste = float(np.std(gray))

        # ── Cores dominantes (k-means simplificado) ──
        pixels = img.reshape(-1, 3).astype(np.float32)
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
        K = 5
        _, labels, centers = cv2.kmeans(pixels, K, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)
        contagens = [int((labels == i).sum()) for i in range(K)]
        cores_dominantes = []
        for cor, cnt in sorted(zip(centers.astype(int).tolist(), contagens), key=lambda x: -x[1]):
            cores_dominantes.append({"bgr": cor, "pixels": cnt})

        # ── Detecção de bordas (Canny) ──
        bordas_canny = cv2.Canny(gray, 50, 150)
        qtd_bordas = int(np.count_nonzero(bordas_canny))

        # ── Contornos ──
        contornos, _ = cv2.findContours(bordas_canny, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contornos_filtrados = [c for c in contornos if cv2.contourArea(c) > 100]

        # ── Tentativa DNN (MobileNet-SSD) ──
        objetos_dnn = []
        prototxt = get_temp_path("MobileNetSSD_deploy.prototxt")
        modelo_caffemodel = get_temp_path("MobileNetSSD_deploy.caffemodel")

        if os.path.exists(prototxt) and os.path.exists(modelo_caffemodel):
            CLASSES = [
                "background", "aeroplane", "bicycle", "bird", "boat",
                "bottle", "bus", "car", "cat", "chair", "cow",
                "diningtable", "dog", "horse", "motorbike", "person",
                "pottedplant", "sheep", "sofa", "train", "tvmonitor",
            ]
            net = cv2.dnn.readNetFromCaffe(prototxt, modelo_caffemodel)
            h, w = img.shape[:2]
            blob = cv2.dnn.blobFromImage(cv2.resize(img, (300, 300)), 0.007843, (300, 300), 127.5)
            net.setInput(blob)
            deteccoes = net.forward()

            for i in range(deteccoes.shape[2]):
                conf = float(deteccoes[0, 0, i, 2])
                if conf >= limiar_confianca:
                    idx = int(deteccoes[0, 0, i, 1])
                    classe = CLASSES[idx] if idx < len(CLASSES) else f"classe_{idx}"
                    box = deteccoes[0, 0, i, 3:7] * np.array([w, h, w, h])
                    x1, y1, x2, y2 = box.astype(int).tolist()
                    objetos_dnn.append({
                        "classe": classe,
                        "confianca": round(conf, 4),
                        "bbox": [x1, y1, x2, y2],
                    })
            log_info(f"OpenCV DNN: {len(objetos_dnn)} objetos detectados.")
        else:
            log_info("OpenCV DNN: modelo MobileNet-SSD não encontrado, usando contornos apenas.")

        resultado = {
            "largura": largura,
            "altura": altura,
            "canais": canais,
            "contornos": len(contornos_filtrados),
            "bordas": qtd_bordas,
            "objetos_dnn": objetos_dnn,
            "cores_dominantes": cores_dominantes,
            "brilho_medio": round(brilho_medio, 2),
            "contraste": round(contraste, 2),
        }

        log_info(
            f"OpenCV: {largura}x{altura}, {len(contornos_filtrados)} contornos, "
            f"{len(objetos_dnn)} objetos DNN, brilho={brilho_medio:.1f}"
        )
        return resultado

    except Exception as e:
        log_error(f"OpenCV: falha na detecção: {e}")
        raise RuntimeError(f"Falha na detecção OpenCV: {e}") from e


# ═══════════════════════════════════════════════════════════════
# 4. ANÁLISE DE DOCUMENTOS
# ═══════════════════════════════════════════════════════════════

def analisar_documento(
    caminho_imagem: str,
    idioma: str = "pt",
) -> Dict[str, Any]:
    """
    Combina OCR + visão para analisar documentos (PDFs escaneados,
    fotos de documentos, recibos, etc.).

    Pipeline:
        1. Pré-processamento (OpenCV: grayscale, threshold, deskew)
        2. OCR (EasyOCR)
        3. Análise semântica (Gemma4)

    Args:
        caminho_imagem: Path para a imagem do documento.
        idioma: Idioma do texto no documento.

    Returns:
        Dicionário com:
            - 'texto_ocr': str — texto bruto extraído
            - 'regioes_ocr': list — regiões detalhadas do OCR
            - 'tipo_documento': str — tipo identificado pela IA
            - 'resumo': str — resumo do conteúdo pela IA
            - 'entidades': dict — entidades extraídas (datas, valores, nomes)
            - 'imagem_preprocessada': str — path da imagem processada

    Raises:
        FileNotFoundError: Se a imagem não existir.
        RuntimeError: Se o pipeline falhar.

    Exemplo:
        >>> doc = analisar_documento("/tmp/recibo.jpg")
        >>> print(doc['tipo_documento'])
        'Recibo de pagamento'
        >>> print(doc['resumo'])
        'Recibo no valor de R$ 150,00 referente a...'
    """
    _check_file(caminho_imagem)
    log_info(f"Documento: analisando '{caminho_imagem}'...")

    try:
        import cv2
        import numpy as np

        # ── 1. Pré-processamento ──
        img = cv2.imread(str(caminho_imagem))
        if img is None:
            raise ValueError(f"Não foi possível ler: {caminho_imagem}")

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # Remoção de ruído
        denoised = cv2.fastNlMeansDenoising(gray, h=10)
        # Binarização adaptativa
        thresh = cv2.adaptiveThreshold(
            denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        # Salvar pré-processada
        preprocess_path = get_temp_path(f"doc_pp_{Path(caminho_imagem).stem}.png")
        cv2.imwrite(preprocess_path, thresh)
        log_info(f"Documento: pré-processada salva em '{preprocess_path}'")

        # ── 2. OCR ──
        regioes_ocr = extrair_texto_com_easyocr(preprocess_path, idioma)
        texto_completo = "\n".join(r["texto"] for r in regioes_ocr if r["texto"])

        if not texto_completo.strip():
            log_info("Documento: nenhum texto extraído via OCR, usando imagem original para visão.")
            texto_completo = "[Sem texto OCR — análise visual necessária]"

        # ── 3. Análise com Gemma4 ──
        b64 = _image_to_base64(caminho_imagem)

        # Identificar tipo de documento
        try:
            tipo = _ollama_vision(
                "Classifique o tipo deste documento em uma frase curta (ex: 'Nota fiscal', "
                "'Recibo de pagamento', 'Contrato', 'RG', 'CNH', 'Boleto bancário'). "
                "Responda APENAS com o tipo, sem explicações.",
                b64,
            )
        except Exception:
            tipo = "Tipo não identificado"

        # Resumir conteúdo
        try:
            resumo = _ollama_vision(
                f"Resuma o conteúdo deste documento em 2-3 frases em português. "
                f"Texto extraído pelo OCR:\n\n{texto_completo[:2000]}",
                b64,
            )
        except Exception:
            resumo = texto_completo[:500] if texto_completo else "Não foi possível resumir."

        # Extrair entidades
        try:
            entidades_raw = _ollama_vision(
                f"Extraia entidades deste documento em formato JSON válido com as chaves: "
                f"datas, valores_monetarios, nomes, cpf_cnpj, enderecos, telefones, emails. "
                f"Texto extraído:\n\n{texto_completo[:2000]}\n\n"
                f"Responda APENAS com o JSON, sem markdown ou explicações.",
                b64,
            )
            # Tentar parsear JSON
            entidades = json.loads(entidades_raw)
        except (json.JSONDecodeError, Exception):
            entidades = {"raw": texto_completo[:1000]}

        resultado = {
            "texto_ocr": texto_completo,
            "regioes_ocr": regioes_ocr,
            "tipo_documento": tipo,
            "resumo": resumo,
            "entidades": entidades,
            "imagem_preprocessada": preprocess_path,
        }

        log_info(f"Documento: análise completa — tipo='{tipo[:40]}', OCR={len(regioes_ocr)} regiões.")
        return resultado

    except Exception as e:
        log_error(f"Documento: falha na análise: {e}")
        raise RuntimeError(f"Falha na análise do documento: {e}") from e


# ═══════════════════════════════════════════════════════════════
# 5. DESCRIÇÃO DE IMAGENS
# ═══════════════════════════════════════════════════════════════

def descrever_imagem(
    caminho_imagem: str,
    detalhado: bool = False,
) -> str:
    """
    Descreve uma imagem em português usando gemma3:e4b.

    Args:
        caminho_imagem: Path absoluto para o arquivo de imagem.
        detalhado: Se True, pede descrição mais detalhada.

    Returns:
        Descrição textual da imagem em português.

    Raises:
        FileNotFoundError: Se a imagem não existir.
        RuntimeError: Se o Ollama falhar.

    Exemplo:
        >>> desc = descrever_imagem("/tmp/paisagem.jpg")
        >>> print(desc)
        'Uma paisagem montanhosa com céu azul e nuvens brancas...'
    """
    _check_file(caminho_imagem)
    log_info(f"Descrição: analisando '{caminho_imagem}' (detalhado={detalhado})...")

    if detalhado:
        prompt = (
            "Descreva esta imagem em português brasileiro de forma detalhada e completa. "
            "Inclua: objetos presentes, cores, iluminação, ambiente, pessoas (se houver), "
            "texto visível, e qualquer detalhe relevante. "
            "Escreva em parágrafos bem estruturados."
        )
    else:
        prompt = (
            "Descreva esta imagem em português brasileiro em 2-3 frases. "
            "Seja objetivo mas informativo."
        )

    try:
        b64 = _image_to_base64(caminho_imagem)
        resposta = _ollama_vision(prompt, b64)
        log_info(f"Descrição: gerada ({len(resposta)} chars).")
        return resposta
    except Exception as e:
        log_error(f"Descrição: falha: {e}")
        raise RuntimeError(f"Falha ao descrever imagem: {e}") from e


# ═══════════════════════════════════════════════════════════════
# 6. COMPARAÇÃO DE IMAGENS
# ═══════════════════════════════════════════════════════════════

def comparar_imagens(
    caminho1: str,
    caminho2: str,
) -> Dict[str, Any]:
    """
    Compara duas imagens e descreve diferenças visuais e semânticas.

    Usa:
        - OpenCV para comparação estrutural (SSIM, diff)
        - Gemma4 para comparação semântica

    Args:
        caminho1: Path para a primeira imagem.
        caminho2: Path para a segunda imagem.

    Returns:
        Dicionário com:
            - 'ssim': float — similaridade estrutural (0.0–1.0)
            - 'diferenca_percentual': float — % de pixels diferentes
            - 'descricao_diferencas': str — descrição textual das diferenças
            - 'sao_iguais': bool — True se visualmente idênticas

    Raises:
        FileNotFoundError: Se alguma imagem não existir.
        RuntimeError: Se a comparação falhar.

    Exemplo:
        >>> comp = comparar_imagens("/tmp/foto1.jpg", "/tmp/foto2.jpg")
        >>> print(f"SSIM: {comp['ssim']:.2%}")
        >>> print(comp['descricao_diferencas'])
    """
    p1 = _check_file(caminho1)
    p2 = _check_file(caminho2)
    log_info(f"Comparando: '{caminho1}' vs '{caminho2}'...")

    try:
        import cv2
        import numpy as np

        # ── Comparação estrutural (OpenCV) ──
        img1 = cv2.imread(str(p1))
        img2 = cv2.imread(str(p2))

        if img1 is None:
            raise ValueError(f"Não foi possível ler: {caminho1}")
        if img2 is None:
            raise ValueError(f"Não foi possível ler: {caminho2}")

        # Redimensionar img2 para o tamanho de img1 se necessário
        h1, w1 = img1.shape[:2]
        h2, w2 = img2.shape[:2]
        if (h1, w1) != (h2, w2):
            img2 = cv2.resize(img2, (w1, h1))
            log_info(f"Comparação: imagem 2 redimensionada para {w1}x{h1}")

        gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)

        # SSIM simplificado (usando normalized cross-correlation)
        try:
            from skimage.metrics import structural_similarity as ssim_func
            ssim_val, _ = ssim_func(gray1, gray2, full=True)
        except ImportError:
            # Fallback: correlação normalizada
            corr = cv2.matchTemplate(gray1, gray2, cv2.TM_CCOEFF_NORMED)
            ssim_val = float(corr[0][0])
            ssim_val = max(0.0, ssim_val)  # Normalizar para 0–1

        # Diferença de pixels
        diff = cv2.absdiff(gray1, gray2)
        _, thresh = cv2.threshold(diff, 30, 255, cv2.THRESH_BINARY)
        diff_pct = float(np.count_nonzero(thresh)) / float(gray1.size) * 100.0

        # Salvar imagem de diferença
        diff_path = get_temp_path("comparacao_diff.png")
        cv2.imwrite(diff_path, thresh)

        # ── Comparação semântica (Gemma4) ──
        b64_1 = _image_to_base64(caminho1)
        b64_2 = _image_to_base64(caminho2)

        try:
            descricao = _ollama_vision(
                "Compare estas duas imagens e descreva as principais diferenças entre elas "
                "em português brasileiro. Seja específico sobre o que mudou. "
                "Se forem idênticas, diga que são iguais.",
                b64_1,
            )
            # Enviar segunda imagem em mensagem separada
            descricao2 = _ollama_vision(
                "Agora considere esta segunda imagem. Descreva as diferenças entre a primeira "
                "e esta segunda imagem em português brasileiro.",
                b64_2,
            )
            descricao_completa = f"{descricao}\n\n{descricao2}"
        except Exception as e:
            log_error(f"Comparação semântica falhou: {e}")
            descricao_completa = f"[Comparação semântica indisponível — SSIM: {ssim_val:.4f}, Diferença: {diff_pct:.1f}%]"

        resultado = {
            "ssim": round(float(ssim_val), 4),
            "diferenca_percentual": round(diff_pct, 2),
            "descricao_diferencas": descricao_completa,
            "sao_iguais": ssim_val > 0.95 and diff_pct < 5.0,
            "imagem_diferenca": diff_path,
        }

        log_info(
            f"Comparação: SSIM={ssim_val:.4f}, diff={diff_pct:.1f}%, "
            f"iguais={resultado['sao_iguais']}"
        )
        return resultado

    except Exception as e:
        log_error(f"Comparação: falha: {e}")
        raise RuntimeError(f"Falha ao comparar imagens: {e}") from e


# ═══════════════════════════════════════════════════════════════
# FUNÇÕES UTILITÁRIAS
# ═══════════════════════════════════════════════════════════════

def preprocessar_imagem(
    caminho_imagem: str,
    operacao: str = "auto",
) -> str:
    """
    Aplica pré-processamento comum em imagens para melhorar OCR/detecção.

    Args:
        caminho_imagem: Path para a imagem.
        operacao: Tipo de pré-processamento:
            - 'auto': escolhe automaticamente
            - 'grayscale': converte para cinza
            - 'threshold': binarização
            - 'denoise': remoção de ruído
            - 'deskew': correção de inclinação
            - 'enhance': melhoria de contraste (CLAHE)

    Returns:
        Path para a imagem processada (em temp).

    Exemplo:
        >>> processada = preprocessar_imagem("/tmp/doc.jpg", "denoise")
    """
    _check_file(caminho_imagem)
    log_info(f"Pré-processamento: '{operacao}' em '{caminho_imagem}'...")

    import cv2
    import numpy as np

    img = cv2.imread(str(caminho_imagem))
    if img is None:
        raise ValueError(f"Não foi possível ler: {caminho_imagem}")

    resultado = img

    if operacao in ("auto", "grayscale"):
        resultado = cv2.cvtColor(resultado, cv2.COLOR_BGR2GRAY)

    if operacao in ("auto", "denoise"):
        if len(resultado.shape) == 3:
            resultado = cv2.fastNlMeansDenoisingColored(resultado, h=10, hColor=10)
        else:
            resultado = cv2.fastNlMeansDenoising(resultado, h=10)

    if operacao in ("auto", "enhance"):
        if len(resultado.shape) == 2:
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            resultado = clahe.apply(resultado)
        else:
            lab = cv2.cvtColor(resultado, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            l = clahe.apply(l)
            resultado = cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)

    if operacao in ("auto", "threshold"):
        if len(resultado.shape) == 3:
            resultado = cv2.cvtColor(resultado, cv2.COLOR_BGR2GRAY)
        resultado = cv2.adaptiveThreshold(
            resultado, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )

    if operacao == "deskwick":
        if len(resultado.shape) == 3:
            gray = cv2.cvtColor(resultado, cv2.COLOR_BGR2GRAY)
        else:
            gray = resultado
        coords = np.column_stack(np.where(gray < 128))
        if len(coords) > 0:
            angle = cv2.minAreaRect(coords)[-1]
            if angle < -45:
                angle = -(90 + angle)
            else:
                angle = -angle
            if abs(angle) > 0.5:
                h, w = gray.shape[:2]
                center = (w // 2, h // 2)
                M = cv2.getRotationMatrix2D(center, angle, 1.0)
                resultado = cv2.warpAffine(
                    resultado, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
                )

    # Salvar resultado
    out_path = get_temp_path(f"pp_{operacao}_{Path(caminho_imagem).name}")
    cv2.imwrite(out_path, resultado)
    log_info(f"Pré-processamento: salvo em '{out_path}'")
    return out_path


# ═══════════════════════════════════════════════════════════════
# MAIN — Teste rápido
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Módulo de Visão Computacional")
    parser.add_argument("comando", choices=[
        "descrever", "ocr", "detectar", "documento", "comparar", "preprocessar",
    ])
    parser.add_argument("imagem", help="Path da imagem")
    parser.add_argument("--imagem2", help="Segunda imagem (para comparar)")
    parser.add_argument("--pergunta", "-p", default="O que há nesta imagem?")
    parser.add_argument("--idioma", "-i", default="pt")
    parser.add_argument("--operacao", "-o", default="auto")
    parser.add_argument("--detalhado", "-d", action="store_true")

    args = parser.parse_args()

    if args.comando == "descrever":
        print(descrever_imagem(args.imagem, detalhado=args.detalhado))

    elif args.comando == "ocr":
        resultados = extrair_texto_com_easyocr(args.imagem, args.idioma)
        for r in resultados:
            print(f"  [{r['confianca']:.1%}] {r['texto']}")

    elif args.comando == "detectar":
        info = detectar_objetos_com_opencv(args.imagem)
        print(json.dumps(info, indent=2, ensure_ascii=False, default=str))

    elif args.comando == "documento":
        doc = analisar_documento(args.imagem, args.idioma)
        print(f"Tipo: {doc['tipo_documento']}")
        print(f"Resumo: {doc['resumo']}")
        print(f"Entidades: {json.dumps(doc['entidades'], indent=2, ensure_ascii=False)}")
        print(f"Texto OCR:\n{doc['texto_ocr']}")

    elif args.comando == "comparar":
        if not args.imagem2:
            print("ERRO: --imagem2 é necessário para comparar.")
            sys.exit(1)
        comp = comparar_imagens(args.imagem, args.imagem2)
        print(f"SSIM: {comp['ssim']:.4f}")
        print(f"Diferença: {comp['diferenca_percentual']:.1f}%")
        print(f"Iguais: {comp['sao_iguais']}")
        print(f"\nDescrição:\n{comp['descricao_diferencas']}")

    elif args.comando == "preprocessar":
        out = preprocessar_imagem(args.imagem, args.operacao)
        print(f"Imagem processada: {out}")
