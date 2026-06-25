#!/usr/bin/env python3
"""
Testes unitários para o módulo de visão computacional.
Cobertura: gemma4 visão, EasyOCR, OpenCV, análise de documentos.

Uso: pytest tests/test_visao.py -v
"""

import pytest
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
from PIL import Image, ImageDraw, ImageFont

# Adiciona tools/ ao path
sys.path.insert(0, str(Path.home() / "AppData" / "Local" / "hermes" / "tools"))

from lib import visao


# ═══════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════

@pytest.fixture
def imagem_teste():
    """Cria uma imagem de teste com texto."""
    img = Image.new('RGB', (400, 200), color='white')
    draw = ImageDraw.Draw(img)
    draw.text((50, 80), 'Teste de Visao OWL', fill='black')
    draw.rectangle([50, 50, 150, 150], fill='red', outline='black')
    
    tmp = Path(tempfile.gettempdir()) / 'teste_visao.png'
    img.save(tmp)
    yield tmp
    # Cleanup
    try:
        tmp.unlink(missing_ok=True)
    except (OSError, PermissionError):
        pass


@pytest.fixture
def imagem_teste2():
    """Cria uma segunda imagem de teste (diferente)."""
    img = Image.new('RGB', (400, 200), color='blue')
    draw = ImageDraw.Draw(img)
    draw.text((50, 80), 'Imagem Diferente', fill='white')
    
    tmp = Path(tempfile.gettempdir()) / 'teste_visao2.png'
    img.save(tmp)
    yield tmp
    try:
        tmp.unlink(missing_ok=True)
    except (OSError, PermissionError):
        pass


@pytest.fixture
def mock_ollama():
    """Mock para o cliente Ollama."""
    with patch('lib.visao.ollama') as mock:
        mock.chat.return_value = {
            'message': {
                'content': 'Esta é uma imagem de teste com texto "Teste de Visao OWL" e um quadrado vermelho.'
            }
        }
        yield mock


# ═══════════════════════════════════════════
# TESTES: descrever_imagem
# ═══════════════════════════════════════════

class TestDescreverImagem:
    def test_descrever_imagem_basico(self, imagem_teste, mock_ollama):
        """Testa descrição básica de imagem."""
        resultado = visao.descrever_imagem(str(imagem_teste))
        assert resultado is not None
        assert isinstance(resultado, str)
        assert len(resultado) > 0

    def test_descrever_imagem_detalhado(self, imagem_teste, mock_ollama):
        """Testa descrição detalhada de imagem."""
        resultado = visao.descrever_imagem(str(imagem_teste), detalhado=True)
        assert resultado is not None
        assert isinstance(resultado, str)

    def test_descrever_imagem_inexistente(self):
        """Testa com arquivo inexistente."""
        resultado = visao.descrever_imagem('/caminho/inexistente.png')
        assert resultado is None

    def test_descrever_imagem_texto_vazio(self, mock_ollama):
        """Testa quando Ollama retorna texto vazio."""
        mock_ollama.chat.return_value = {'message': {'content': ''}}
        img = Image.new('RGB', (100, 100), color='white')
        tmp = Path(tempfile.gettempdir()) / 'teste_vazio.png'
        img.save(tmp)
        try:
            resultado = visao.descrever_imagem(str(tmp))
            # Deve retornar None ou string vazia
            assert resultado is None or resultado == ''
        finally:
            tmp.unlink(missing_ok=True)


# ═══════════════════════════════════════════
# TESTES: extrair_texto_com_easyocr
# ═══════════════════════════════════════════

class TestExtrairTexto:
    def test_extrair_texto_basico(self, imagem_teste):
        """Testa extração de texto básico."""
        resultado = visao.extrair_texto_com_easyocr(str(imagem_teste))
        assert isinstance(resultado, list)

    def test_extrair_texto_completo(self, imagem_teste):
        """Testa extração de texto como string única."""
        resultado = visao.extrair_texto_completo(str(imagem_teste))
        assert isinstance(resultado, str)

    def test_extrair_texto_inexistente(self):
        """Testa com arquivo inexistente."""
        resultado = visao.extrair_texto_com_easyocr('/caminho/inexistente.png')
        assert resultado == []

    def test_extrair_texto_idioma_en(self, imagem_teste):
        """Testa extração em inglês."""
        resultado = visao.extrair_texto_com_easyocr(str(imagem_teste), idioma='en')
        assert isinstance(resultado, list)


# ═══════════════════════════════════════════
# TESTES: detectar_objetos_com_opencv
# ═══════════════════════════════════════════

class TestDetectarObjetos:
    def test_detectar_objetos_basico(self, imagem_teste):
        """Testa detecção básica de objetos."""
        resultado = visao.detectar_objetos_com_opencv(str(imagem_teste))
        assert isinstance(resultado, dict)
        assert 'dimensoes' in resultado
        assert 'total_contornos' in resultado

    def test_detectar_objetos_inexistente(self):
        """Testa com arquivo inexistente."""
        resultado = visao.detectar_objetos_com_opencv('/caminho/inexistente.png')
        assert 'erro' in resultado

    def test_detectar_objetos_limiar(self, imagem_teste):
        """Testa com limiar personalizado."""
        resultado = visao.detectar_objetos_com_opencv(str(imagem_teste), limiar=0.3)
        assert isinstance(resultado, dict)


# ═══════════════════════════════════════════
# TESTES: comparar_imagens
# ═══════════════════════════════════════════

class TestCompararImagens:
    def test_comparar_imagens_iguais(self, imagem_teste):
        """Testa comparação de imagens iguais."""
        resultado = visao.comparar_imagens(str(imagem_teste), str(imagem_teste))
        assert isinstance(resultado, dict)
        assert 'ssim' in resultado

    def test_comparar_imagens_diferentes(self, imagem_teste, imagem_teste2):
        """Testa comparação de imagens diferentes."""
        resultado = visao.comparar_imagens(str(imagem_teste), str(imagem_teste2))
        assert isinstance(resultado, dict)

    def test_comparar_imagens_inexistente(self):
        """Testa com arquivo inexistente."""
        resultado = visao.comparar_imagens('/inexistente1.png', '/inexistente2.png')
        assert 'erro' in resultado


# ═══════════════════════════════════════════
# TESTES: preprocessar_imagem
# ═══════════════════════════════════════════

class TestPreprocessarImagem:
    def test_preprocessar_grayscale(self, imagem_teste):
        """Testa pré-processamento grayscale."""
        resultado = visao.preprocessar_imagem(str(imagem_teste), operacao='grayscale')
        assert resultado is not None
        assert Path(resultado).exists()

    def test_preprocessar_auto(self, imagem_teste):
        """Testa pré-processamento automático."""
        resultado = visao.preprocessar_imagem(str(imagem_teste), operacao='auto')
        assert resultado is not None

    def test_preprocessar_inexistente(self):
        """Testa com arquivo inexistente."""
        resultado = visao.preprocessar_imagem('/inexistente.png')
        assert resultado is None


# ═══════════════════════════════════════════
# TESTES: ler_imagem_com_gemma4
# ═══════════════════════════════════════════

class TestLerImagemGemma4:
    def test_ler_imagem_basico(self, imagem_teste, mock_ollama):
        """Testa leitura de imagem com gemma4."""
        resultado = visao.ler_imagem_com_gemma4(str(imagem_teste), 'O que você vê?')
        assert resultado is not None
        assert isinstance(resultado, str)

    def test_ler_imagem_inexistente(self):
        """Testa com arquivo inexistente."""
        resultado = visao.ler_imagem_com_gemma4('/inexistente.png', 'O que você vê?')
        assert resultado is None


# ═══════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
