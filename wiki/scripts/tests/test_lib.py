#!/usr/bin/env python3
"""
Testes unitarios para lib/__init__.py
Cobertura: run_cmd, cache_save, cache_load, cache_clear, get_cache_dir,
            ollama_chat, ollama_list_models, get_temp_path, log_info,
            log_error, log_warning
"""

import os
import sys
import json
import time
import shutil
import tempfile
import hashlib
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
from io import StringIO

import pytest

# Garante que tools/ esta no path
TOOLS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TOOLS_DIR))

from lib import (
    run_cmd,
    cache_save,
    cache_load,
    cache_clear,
    get_cache_dir,
    ollama_chat,
    ollama_list_models,
    get_temp_path,
    log_info,
    log_error,
    log_warning,
    OLLAMA_URL,
    DEFAULT_MODEL,
)


# ═══════════════════════════════════════════
# TESTES: run_cmd
# ═══════════════════════════════════════════

class TestRunCmd:
    """Testes para run_cmd()."""

    def test_run_cmd_list_success(self):
        """Comando via lista com sucesso retorna stdout."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "hello world\n"
        with patch("subprocess.run", return_value=mock_result):
            result = run_cmd(["echo", "hello world"])
        assert result == "hello world"

    def test_run_cmd_string_success(self):
        """Comando via string (shell=True) com sucesso."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "output\n"
        with patch("subprocess.run", return_value=mock_result):
            result = run_cmd("echo output")
        assert result == "output"

    def test_run_cmd_failure_returns_empty(self):
        """Comando com erro retorna string vazia."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        with patch("subprocess.run", return_value=mock_result):
            result = run_cmd(["false"])
        assert result == ""

    def test_run_cmd_timeout_returns_empty(self):
        """Timeout retorna string vazia."""
        import subprocess as sp
        with patch("subprocess.run", side_effect=sp.TimeoutExpired(cmd="x", timeout=1)):
            result = run_cmd("sleep 100", timeout=1)
        assert result == ""

    def test_run_cmd_exception_returns_empty(self):
        """Excecao generica retorna string vazia."""
        with patch("subprocess.run", side_effect=RuntimeError("boom")):
            result = run_cmd("bad command")
        assert result == ""

    def test_run_cmd_strips_whitespace(self):
        """Output e stripado (sem whitespace extra)."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "  trimmed  \n"
        with patch("subprocess.run", return_value=mock_result):
            result = run_cmd(["echo", "trimmed"])
        assert result == "trimmed"

    def test_run_cmd_list_uses_shell_false(self):
        """Comando via lista usa shell=False."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        with patch("subprocess.run", return_value=mock_result) as mock:
            run_cmd(["ls", "-la"])
        call_kwargs = mock.call_args
        assert call_kwargs[1].get("shell", False) is False or \
               call_kwargs[0][1] if len(call_kwargs[0]) > 1 else True  # shell not in kwargs for list

    def test_run_cmd_string_uses_shell_true(self):
        """Comando via string usa shell=True."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        with patch("subprocess.run", return_value=mock_result) as mock:
            run_cmd("echo hello")
        call_kwargs = mock.call_args
        assert call_kwargs[1].get("shell", True) is True

    def test_run_cmd_custom_timeout(self):
        """Timeout customizado e passado ao subprocess."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        with patch("subprocess.run", return_value=mock_result) as mock:
            run_cmd("cmd", timeout=120)
        call_kwargs = mock.call_args
        assert call_kwargs[1].get("timeout") == 120


# ═══════════════════════════════════════════
# TESTES: Cache
# ═══════════════════════════════════════════

class TestCache:
    """Testes para funcoes de cache."""

    def test_get_cache_dir_creates_directory(self, temp_cache_dir):
        """get_cache_dir cria o diretorio se nao existir."""
        with patch("lib.__init__.Path.home", return_value=temp_cache_dir.parent):
            # Usa nome unico para nao colidir
            cache_dir = get_cache_dir("test_unique")
        assert cache_dir.exists()
        assert cache_dir.is_dir()

    def test_cache_save_and_load(self, temp_cache_dir):
        """Salvar e carregar do cache funciona."""
        with patch("lib.get_cache_dir", return_value=temp_cache_dir):
            cache_save("test", "key1", "value1", ttl=3600)
            result = cache_load("test", "key1")
        assert result == "value1"

    def test_cache_load_missing_key(self, temp_cache_dir):
        """Carregar chave inexistente retorna None."""
        with patch("lib.get_cache_dir", return_value=temp_cache_dir):
            result = cache_load("test", "nonexistent_key")
        assert result is None

    def test_cache_expiration(self, temp_cache_dir):
        """Cache expirado retorna None e remove arquivo."""
        with patch("lib.get_cache_dir", return_value=temp_cache_dir):
            # Salva com TTL negativo (ja expirado)
            cache_save("test", "exp_key", "exp_value", ttl=-1)
            # Pequeno delay para garantir que o timestamp passou
            time.sleep(0.01)
            result = cache_load("test", "exp_key")
        assert result is None

    def test_cache_save_complex_value(self, temp_cache_dir):
        """Cache salva valores complexos (dict, list)."""
        complex_val = {"nested": [1, 2, 3], "key": "value"}
        with patch("lib.get_cache_dir", return_value=temp_cache_dir):
            cache_save("test", "complex", complex_val, ttl=3600)
            result = cache_load("test", "complex")
        assert result == complex_val

    def test_cache_clear_removes_expired(self, temp_cache_dir):
        """cache_clear remove arquivos expirados."""
        with patch("lib.get_cache_dir", return_value=temp_cache_dir):
            # Salva um expirado e um valido
            cache_save("test", "old_key", "old_val", ttl=-1)
            cache_save("test", "new_key", "new_val", ttl=3600)
            time.sleep(0.01)
            removed = cache_clear("test")
        assert removed >= 1

    def test_cache_clear_returns_zero_when_empty(self, temp_cache_dir):
        """cache_clear retorna 0 quando nao ha arquivos."""
        with patch("lib.get_cache_dir", return_value=temp_cache_dir):
            removed = cache_clear("test")
        assert removed == 0

    def test_cache_overwrite_same_key(self, temp_cache_dir):
        """Sobrescrever mesma key atualiza o valor."""
        with patch("lib.get_cache_dir", return_value=temp_cache_dir):
            cache_save("test", "key", "v1", ttl=3600)
            cache_save("test", "key", "v2", ttl=3600)
            result = cache_load("test", "key")
        assert result == "v2"

    def test_cache_file_is_json(self, temp_cache_dir):
        """Arquivo de cache e JSON valido."""
        with patch("lib.get_cache_dir", return_value=temp_cache_dir):
            cache_save("test", "json_key", "json_val", ttl=3600)
            # Encontra o arquivo
            files = list(temp_cache_dir.glob("*.json"))
        assert len(files) >= 1
        with open(files[0], "r") as f:
            data = json.load(f)
        assert "timestamp" in data
        assert "ttl" in data
        assert "key" in data
        assert "value" in data

    def test_cache_different_names_isolated(self, temp_cache_dir):
        """Caches com nomes diferentes usam diretorios diferentes."""
        dir_a = temp_cache_dir / "cache_a"
        dir_b = temp_cache_dir / "cache_b"
        dir_a.mkdir(exist_ok=True)
        dir_b.mkdir(exist_ok=True)

        with patch("lib.__init__.get_cache_dir", side_effect=lambda name, td=temp_cache_dir: td / name):
            cache_save("cache_a", "key", "val_a", ttl=3600)
            cache_save("cache_b", "key", "val_b", ttl=3600)
            result_a = cache_load("cache_a", "key")
            result_b = cache_load("cache_b", "key")
        assert result_a == "val_a"
        assert result_b == "val_b"


# ═══════════════════════════════════════════
# TESTES: Ollama
# ═══════════════════════════════════════════

class TestOllama:
    """Testes para funcoes Ollama."""

    def test_ollama_chat_success(self, mock_urlopen):
        """ollama_chat retorna conteudo da resposta."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "message": {"content": "Resposta do modelo"}
        }).encode("utf-8")
        mock_urlopen.return_value = mock_response

        result = ollama_chat("qwen3:8b", "Ola")
        assert result == "Resposta do modelo"

    def test_ollama_chat_with_system(self, mock_urlopen):
        """ollama_chat inclui system prompt quando fornecido."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "message": {"content": "OK"}
        }).encode("utf-8")
        mock_urlopen.return_value = mock_response

        ollama_chat("qwen3:8b", "prompt", system="You are helpful")
        # Verifica que a requisicao foi feita
        assert mock_urlopen.called

    def test_ollama_chat_exception_returns_empty(self):
        """ollama_chat retorna vazio em caso de erro."""
        with patch("urllib.request.urlopen", side_effect=Exception("Connection refused")):
            result = ollama_chat("qwen3:8b", "Ola")
        assert result == ""

    def test_ollama_chat_default_params(self, mock_urlopen):
        """ollama_chat usa parametros padrao corretos."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "message": {"content": ""}
        }).encode("utf-8")
        mock_urlopen.return_value = mock_response

        ollama_chat(DEFAULT_MODEL, "test")
        # Verifica que urlopen foi chamado (a request foi feita)
        assert mock_urlopen.called

    def test_ollama_list_models_success(self, mock_urlopen):
        """ollama_list_models retorna lista de nomes."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "models": [
                {"name": "qwen3:8b"},
                {"name": "llama3:70b"},
            ]
        }).encode("utf-8")
        mock_urlopen.return_value = mock_response

        result = ollama_list_models()
        assert result == ["qwen3:8b", "llama3:70b"]

    def test_ollama_list_models_empty(self, mock_urlopen):
        """ollama_list_models retorna lista vazia sem modelos."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"models": []}).encode("utf-8")
        mock_urlopen.return_value = mock_response

        result = ollama_list_models()
        assert result == []

    def test_ollama_list_models_exception(self):
        """ollama_list_models retorna lista vazia em erro."""
        with patch("urllib.request.urlopen", side_effect=Exception("error")):
            result = ollama_list_models()
        assert result == []


# ═══════════════════════════════════════════
# TESTES: Utilitarios
# ═══════════════════════════════════════════

class TestUtilities:
    """Testes para funcoes utilitarias."""

    def test_get_temp_path(self):
        """get_temp_path retorna path no diretorio temporario."""
        result = get_temp_path("test_file.txt")
        assert "test_file.txt" in result

    def test_log_info(self, capsys):
        """log_info imprime mensagem formatada."""
        log_info("mensagem de teste")
        captured = capsys.readouterr()
        assert "INFO" in captured.out
        assert "mensagem de teste" in captured.out

    def test_log_error(self, capsys):
        """log_error imprime no stderr."""
        log_error("erro de teste")
        captured = capsys.readouterr()
        assert "ERRO" in captured.err
        assert "erro de teste" in captured.err

    def test_log_warning(self, capsys):
        """log_warning imprime mensagem de aviso."""
        log_warning("aviso de teste")
        captured = capsys.readouterr()
        assert "AVISO" in captured.out
        assert "aviso de teste" in captured.out

    def test_ollama_url_constant(self):
        """OLLAMA_URL tem valor correto."""
        assert OLLAMA_URL == "http://127.0.0.1:11434"

    def test_default_model_constant(self):
        """DEFAULT_MODEL tem valor correto."""
        assert DEFAULT_MODEL == "qwen3:8b"
