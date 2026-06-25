#!/usr/bin/env python3
"""
Conftest - Fixtures compartilhados para testes do OWL.
"""

import os
import sys
import json
import time
import shutil
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Adiciona o diretorio tools/ ao path para importar lib
TOOLS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TOOLS_DIR))


@pytest.fixture
def temp_cache_dir():
    """Cria um diretorio de cache temporario e limpa ao final."""
    tmp = Path(tempfile.mkdtemp(prefix="owl_test_cache_"))
    yield tmp
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture
def mock_subprocess():
    """Mock para subprocess.run."""
    with patch("subprocess.run") as mock_run:
        yield mock_run


@pytest.fixture
def mock_subprocess_popen():
    """Mock para subprocess.Popen."""
    with patch("subprocess.Popen") as mock_popen:
        yield mock_popen


@pytest.fixture
def mock_urlopen():
    """Mock para urllib.request.urlopen."""
    with patch("urllib.request.urlopen") as mock:
        yield mock


@pytest.fixture
def sample_text():
    """Texto de exemplo para testes TTS."""
    return "Ola, Senhor Roberio. Este e um teste."


@pytest.fixture
def sample_long_text():
    """Texto longo para testes de chunking."""
    words = ["palavra"] * 500
    return " ".join(words)


@pytest.fixture
def empty_text():
    """Texto vazio."""
    return ""


@pytest.fixture
def whitespace_text():
    """Texto so com espacos."""
    return "   \t\n  "
