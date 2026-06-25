#!/usr/bin/env python3
"""
analisar_pdf.py - Script de análise de PDFs com imagens usando visão computacional.

Extrai texto e imagens de PDFs, analisa imagens com modelo de visão (Ollama),
realiza OCR com EasyOCR e gera relatório consolidado em Markdown.

Uso:
    python analisar_pdf.py caminho/do/arquivo.pdf [--modelo gemma3:4b] [--ocr pt] [--saida relatorio.md]

Dependências:
    pip install PyMuPDF ollama easyocr Pillow
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF
import ollama
from PIL import Image

# ---------------------------------------------------------------------------
# Configurações padrão
# ---------------------------------------------------------------------------
DEFAULT_MODEL = "gemma3:4b"
DEFAULT_OCR_LANGS = ["pt", "en"]
DEFAULT_OUTPUT_DIR = Path.home() / ".hermes" / "pdf_analysis"
MAX_IMAGE_SIZE = 1024  # lado maior máximo para enviar ao modelo de visão
JPEG_QUALITY = 85


# ---------------------------------------------------------------------------
# Utilidades gerais
# ---------------------------------------------------------------------------

def ensure_dir(path: Path) -> Path:
    """Garante que o diretório existe, criando-o se necessário."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def now_ts() -> str:
    """Retorna timestamp formatado."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def md5_bytes(data: bytes) -> str:
    """Retorna hash MD5 de bytes."""
    return hashlib.md5(data).hexdigest()[:12]


# ---------------------------------------------------------------------------
# Extração de texto do PDF
# ---------------------------------------------------------------------------

def extrair_texto_pdf(caminho_pdf: Path) -> list[dict[str, Any]]:
    """
    Extrai texto de cada página do PDF.

    Args:
        caminho_pdf: Caminho para o arquivo PDF.

    Returns:
        Lista de dicionários com 'pagina' (int) e 'texto' (str).

    Raises:
        FileNotFoundError: Se o PDF não existir.
        ValueError: Se o arquivo não for um PDF válido.
    """
    if not caminho_pdf.exists():
        raise FileNotFoundError(f"PDF não encontrado: {caminho_pdf}")

    paginas: list[dict[str, Any]] = []

    try:
        doc = fitz.open(str(caminho_pdf))
    except Exception as exc:
        raise ValueError(f"Erro ao abrir PDF: {exc}") from exc

    for num, page in enumerate(doc, start=1):
        texto = page.get_text("text").strip()
        paginas.append({"pagina": num, "texto": texto})

    doc.close()
    return paginas


# ---------------------------------------------------------------------------
# Extração de imagens do PDF
# ---------------------------------------------------------------------------

def extrair_imagens_pdf(
    caminho_pdf: Path, saida_dir: Path
) -> list[dict[str, Any]]:
    """
    Extrai imagens embutidas no PDF e salva em disco.

    Args:
        caminho_pdf: Caminho para o arquivo PDF.
        saida_dir: Diretório onde as imagens serão salvas.

    Returns:
        Lista de dicionários com metadados de cada imagem extraída:
        - pagina (int)
        - indice (int) — índice da imagem na página
        - nome_arquivo (str)
        - caminho (Path)
        - largura (int)
        - altura (int)
        - formato (str)
        - tamanho_bytes (int)
    """
    ensure_dir(saida_dir)
    imagens: list[dict[str, Any]] = []
    doc = fitz.open(str(caminho_pdf))

    for num_pagina, page in enumerate(doc, start=1):
        image_list = page.get_images(full=True)

        for img_idx, img_info in enumerate(image_list):
            xref = img_info[0]
            try:
                base_image = doc.extract_image(xref)
            except Exception:
                continue  # pula imagens corrompidas

            if base_image is None:
                continue

            image_bytes = base_image["image"]
            ext = base_image.get("ext", "png")
            largura: int = base_image.get("width", 0)
            altura: int = base_image.get("height", 0)

            nome = f"pag{num_pagina:03d}_img{img_idx:03d}_{md5_bytes(image_bytes)}.{ext}"
            caminho_img = saida_dir / nome

            # Salvar imagem
            try:
                with open(caminho_img, "wb") as f:
                    f.write(image_bytes)
            except OSError:
                continue

            imagens.append(
                {
                    "pagina": num_pagina,
                    "indice": img_idx,
                    "nome_arquivo": nome,
                    "caminho": caminho_img,
                    "largura": largura,
                    "altura": altura,
                    "formato": ext,
                    "tamanho_bytes": len(image_bytes),
                }
            )

    doc.close()
    return imagens


# ---------------------------------------------------------------------------
# Análise de imagem com modelo de visão (Ollama)
# ---------------------------------------------------------------------------

def analisar_imagem_visao(
    caminho_img: Path,
    modelo: str = DEFAULT_MODEL,
    prompt: str | None = None,
) -> str:
    """
    Analisa uma imagem usando modelo de visão via Ollama.

    Args:
        caminho_img: Caminho para o arquivo de imagem.
        modelo: Nome do modelo Ollama (ex: 'gemma3:4b').
        prompt: Prompt customizado. Se None, usa prompt padrão.

    Returns:
        Descrição textual da imagem gerada pelo modelo.
    """
    if prompt is None:
        prompt = (
            "Descreva esta imagem em português de forma detalhada. "
            "Inclua: tipo de imagem (foto, gráfico, diagrama, tabela, etc.), "
            "elementos visíveis principais, cores predominantes, "
            "texto visível (se houver) e contexto geral."
        )

    try:
        # Redimensionar se necessário para economizar tokens
        img = Image.open(caminho_img)
        img.thumbnail((MAX_IMAGE_SIZE, MAX_IMAGE_SIZE), Image.LANCZOS)

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=JPEG_QUALITY)
        img_bytes = buf.getvalue()

        response = ollama.chat(
            model=modelo,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                    "images": [img_bytes],
                }
            ],
            options={"temperature": 0.2},
        )
        return response["message"]["content"].strip()

    except ollama.ResponseError as exc:
        return f"[ERRO OLLAMA] Modelo '{modelo}' não disponível: {exc}"
    except Exception as exc:
        return f"[ERRO VISÃO] {type(exc).__name__}: {exc}"


# ---------------------------------------------------------------------------
# OCR com EasyOCR
# ---------------------------------------------------------------------------

def ocr_imagem(
    caminho_img: Path,
    idiomas: list[str] | None = None,
) -> str:
    """
    Extrai texto de uma imagem usando EasyOCR.

    Args:
        caminho_img: Caminho para o arquivo de imagem.
        idiomas: Lista de códigos de idioma (ex: ['pt', 'en']).

    Returns:
        Texto extraído da imagem, uma linha por detecção.
    """
    if idiomas is None:
        idiomas = DEFAULT_OCR_LANGS

    try:
        import easyocr

        reader = easyocr.Reader(idiomas, gpu=True, verbose=False)
        resultados = reader.readtext(str(caminho_img), detail=0, paragraph=True)
        return "\n".join(resultados).strip() if resultados else ""
    except Exception as exc:
        return f"[ERRO OCR] {type(exc).__name__}: {exc}"


# ---------------------------------------------------------------------------
# Geração do relatório Markdown
# ---------------------------------------------------------------------------

def gerar_relatorio(
    caminho_pdf: Path,
    paginas: list[dict[str, Any]],
    imagens: list[dict[str, Any]],
    analises_visao: list[dict[str, Any]],
    resultados_ocr: list[dict[str, Any]],
    modelo_visao: str,
    idiomas_ocr: list[str],
    tempo_total: float,
    saida_path: Path,
) -> Path:
    """
    Gera relatório consolidado em Markdown.

    Args:
        caminho_pdf: Caminho do PDF analisado.
        paginas: Texto extraído por página.
        imagens: Metadados das imagens extraídas.
        analises_visao: Resultados da análise de visão.
        resultados_ocr: Resultados do OCR.
        modelo_visao: Nome do modelo de visão usado.
        idiomas_ocr: Idiomas usados no OCR.
        tempo_total: Tempo total de análise em segundos.
        saida_path: Caminho do arquivo de saída.

    Returns:
        Caminho do relatório gerado.
    """
    lines: list[str] = []

    def add(s: str = "") -> None:
        lines.append(s)

    # Cabeçalho
    add("# 📄 Relatório de Análise de PDF")
    add()
    add(f"- **Arquivo:** `{caminho_pdf.name}`")
    add(f"- **Caminho completo:** `{caminho_pdf}`")
    add(f"- **Data da análise:** {now_ts()}")
    add(f"- **Modelo de visão:** `{modelo_visao}`")
    add(f"- **Idiomas OCR:** {', '.join(idiomas_ocr)}")
    add(f"- **Tempo total:** {tempo_total:.1f}s")
    add()
    add("---")
    add()

    # Resumo
    total_paginas = len(paginas)
    total_imagens = len(imagens)
    total_chars = sum(len(p["texto"]) for p in paginas)

    add("## 📊 Resumo")
    add()
    add(f"| Métrica | Valor |")
    add(f"|---------|-------|")
    add(f"| Total de páginas | {total_paginas} |")
    add(f"| Total de imagens extraídas | {total_imagens} |")
    add(f"| Total de caracteres de texto | {total_chars:,} |")
    add()

    # Análise geral do documento
    add("## 🔍 Análise Geral do Documento")
    add()

    if total_chars > 0:
        # Montar amostra de texto para análise
        amostra = "\n\n".join(
            f"[Pág. {p['pagina']}]\n{p['texto'][:500]}" for p in paginas[:5]
        )
        try:
            resp = ollama.chat(
                model=modelo_visao,
                messages=[
                    {
                        "role": "user",
                        "content": (
                            "Analise o conteúdo deste documento PDF e forneça em português:\n"
                            "1. Tipo de documento (relatório, artigo, contrato, etc.)\n"
                            "2. Tema principal\n"
                            "3. Pontos-chave (bullet points)\n"
                            "4. Resumo executivo (máximo 5 linhas)\n\n"
                            f"Texto do documento:\n{amostra}"
                        ),
                    }
                ],
                options={"temperature": 0.3},
            )
            analise_geral = resp["message"]["content"].strip()
            add(analise_geral)
        except Exception as exc:
            add(f"*Não foi possível gerar análise geral: {exc}*")
    else:
        add("*O PDF não contém texto extraível (possivelmente é um scan).*")

    add()
    add("---")
    add()

    # Texto extraído por página
    add("## 📝 Texto Extraído por Página")
    add()
    for p in paginas:
        add(f"### Página {p['pagina']}")
        add()
        if p["texto"]:
            add("```")
            add(p["texto"])
            add("```")
        else:
            add("*Sem texto extraível nesta página.*")
        add()

    add("---")
    add()

    # Imagens
    add("## 🖼️ Imagens Extraídas")
    add()

    if not imagens:
        add("*Nenhuma imagem encontrada no PDF.*")
    else:
        for i, img_meta in enumerate(imagens):
            add(f"### Imagem {i + 1} — Página {img_meta['pagina']}")
            add()
            add(f"- **Arquivo:** `{img_meta['nome_arquivo']}`")
            add(f"- **Dimensões:** {img_meta['largura']}×{img_meta['altura']} px")
            add(f"- **Formato:** {img_meta['formato']}")
            add(f"- **Tamanho:** {img_meta['tamanho_bytes']:,} bytes")
            add()

            # Descrição da visão
            if i < len(analises_visao):
                add("**Descrição (visão computacional):**")
                add()
                add(analises_visao[i].get("descricao", "*Sem descrição*"))
                add()

            # Texto OCR
            if i < len(resultados_ocr):
                ocr_texto = resultados_ocr[i].get("texto", "")
                add("**Texto OCR:**")
                add()
                if ocr_texto and not ocr_texto.startswith("[ERRO"):
                    add("```")
                    add(ocr_texto)
                    add("```")
                else:
                    add(f"*{ocr_texto or 'Nenhum texto detectado na imagem.'}*")
                add()

            add("---")
            add()

    # Salvar relatório
    ensure_dir(saida_path.parent)
    saida_path.write_text("\n".join(lines), encoding="utf-8")
    return saida_path


# ---------------------------------------------------------------------------
# Orquestração principal
# ---------------------------------------------------------------------------

def analisar_pdf(
    caminho_pdf: str | Path,
    modelo: str = DEFAULT_MODEL,
    idiomas_ocr: list[str] | None = None,
    saida: str | Path | None = None,
    extrair_imgs: bool = True,
    analisar_visao: bool = True,
    executar_ocr: bool = True,
) -> Path:
    """
    Função principal: analisa um PDF completo e gera relatório.

    Args:
        caminho_pdf: Caminho para o arquivo PDF.
        modelo: Modelo Ollama de visão.
        idiomas_ocr: Idiomas para OCR.
        saida: Caminho do relatório de saída (Markdown).
        extrair_imgs: Se True, extrai imagens do PDF.
        analisar_visao: Se True, analisa imagens com modelo de visão.
        executar_ocr: Se True, executa OCR nas imagens.

    Returns:
        Caminho do relatório gerado.
    """
    caminho_pdf = Path(caminho_pdf).resolve()
    if idiomas_ocr is None:
        idiomas_ocr = DEFAULT_OCR_LANGS

    # Diretório de trabalho para este PDF
    pdf_stem = caminho_pdf.stem
    work_dir = ensure_dir(DEFAULT_OUTPUT_DIR / pdf_stem)
    imgs_dir = ensure_dir(work_dir / "imagens")

    if saida is None:
        saida = work_dir / f"relatorio_{pdf_stem}.md"
    saida = Path(saida).resolve()

    t0 = time.time()

    print(f"📄 Analisando: {caminho_pdf}")
    print(f"   Modelo visão: {modelo}")
    print(f"   OCR idiomas: {idiomas_ocr}")
    print(f"   Saída: {saida}")
    print()

    # 1. Extrair texto
    print("📝 Extraindo texto do PDF...")
    paginas = extrair_texto_pdf(caminho_pdf)
    print(f"   → {len(paginas)} página(s) processada(s)")

    # 2. Extrair imagens
    imagens: list[dict[str, Any]] = []
    if extrair_imgs:
        print("🖼️  Extraindo imagens...")
        imagens = extrair_imagens_pdf(caminho_pdf, imgs_dir)
        print(f"   → {len(imagens)} imagem(ns) extraída(s)")

    # 3. Análise de visão
    analises_visao: list[dict[str, Any]] = []
    if analisar_visao and imagens:
        print(f"🔍 Analisando {len(imagens)} imagem(ns) com {modelo}...")
        for i, img in enumerate(imagens, start=1):
            print(f"   [{i}/{len(imagens)}] {img['nome_arquivo']}...", end=" ", flush=True)
            descricao = analisar_imagem_visao(img["caminho"], modelo=modelo)
            analises_visao.append({"descricao": descricao})
            print("✓")

    # 4. OCR
    resultados_ocr: list[dict[str, Any]] = []
    if executar_ocr and imagens:
        print(f"🔤 Executando OCR em {len(imagens)} imagem(ns)...")
        for i, img in enumerate(imagens, start=1):
            print(f"   [{i}/{len(imagens)}] {img['nome_arquivo']}...", end=" ", flush=True)
            texto = ocr_imagem(img["caminho"], idiomas=idiomas_ocr)
            resultados_ocr.append({"texto": texto})
            print("✓")

    # 5. Gerar relatório
    print("📋 Gerando relatório...")
    tempo_total = time.time() - t0
    relatorio_path = gerar_relatorio(
        caminho_pdf=caminho_pdf,
        paginas=paginas,
        imagens=imagens,
        analises_visao=analises_visao,
        resultados_ocr=resultados_ocr,
        modelo_visao=modelo,
        idiomas_ocr=idiomas_ocr,
        tempo_total=tempo_total,
        saida_path=saida,
    )

    print()
    print(f"✅ Análise concluída em {tempo_total:.1f}s")
    print(f"   Relatório: {relatorio_path}")
    print(f"   Imagens:   {imgs_dir}")

    return relatorio_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    """Ponto de entrada da linha de comando."""
    parser = argparse.ArgumentParser(
        description="Analisa PDFs com imagens usando visão computacional e OCR.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Exemplos:
  python analisar_pdf.py documento.pdf
  python analisar_pdf.py doc.pdf --modelo gemma3:4b --ocr pt en
  python analisar_pdf.py doc.pdf --saida meu_relatorio.md
  python analisar_pdf.py doc.pdf --sem-visao --sem-ocr
        """,
    )
    parser.add_argument("pdf", help="Caminho para o arquivo PDF.")
    parser.add_argument(
        "--modelo",
        default=DEFAULT_MODEL,
        help=f"Modelo Ollama de visão (padrão: {DEFAULT_MODEL}).",
    )
    parser.add_argument(
        "--ocr",
        nargs="+",
        default=DEFAULT_OCR_LANGS,
        help=f"Idiomas para OCR (padrão: {' '.join(DEFAULT_OCR_LANGS)}).",
    )
    parser.add_argument(
        "--saida",
        default=None,
        help="Caminho do relatório de saída (Markdown).",
    )
    parser.add_argument(
        "--sem-visao",
        action="store_true",
        help="Desativa análise de imagens com modelo de visão.",
    )
    parser.add_argument(
        "--sem-ocr",
        action="store_true",
        help="Desativa OCR nas imagens.",
    )
    parser.add_argument(
        "--sem-imagens",
        action="store_true",
        help="Desativa extração de imagens do PDF.",
    )

    args = parser.parse_args()

    try:
        analisar_pdf(
            caminho_pdf=args.pdf,
            modelo=args.modelo,
            idiomas_ocr=args.ocr,
            saida=args.saida,
            extrair_imgs=not args.sem_imagens,
            analisar_visao=not args.sem_visao,
            executar_ocr=not args.sem_ocr,
        )
    except FileNotFoundError as exc:
        print(f"❌ {exc}", file=sys.stderr)
        sys.exit(1)
    except ValueError as exc:
        print(f"❌ {exc}", file=sys.stderr)
        sys.exit(2)
    except KeyboardInterrupt:
        print("\n⚠️  Análise interrompida pelo usuário.")
        sys.exit(130)


if __name__ == "__main__":
    main()
