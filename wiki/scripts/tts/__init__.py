#!/usr/bin/env python3
"""
Módulo TTS consolidado do OWL.
Unifica as funcionalidades de tts_fala.py, tts_rapido.py, tts_streaming.py, tts_fix.py, tts_play.py.

Uso:
  from lib.tts import falar, falar_chunked, speak_streaming
  falar("Olá, Senhor Robério")
  falar_chunked("Texto longo aqui...")

Autor: OWL (Batedor da Nuvem)
Data: 2026-05-20
"""

import subprocess
import sys
import os
import asyncio
import tempfile
import time
import re
from pathlib import Path
from typing import Optional

# ═══════════════════════════════════════════
# CONFIGURAÇÃO
# ═══════════════════════════════════════════

VOICE = "pt-BR-FranciscaNeural"
OUTPUT_DIR = Path.home() / "AppData" / "Local" / "hermes" / "audio_cache"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

EDGE_TTS = os.path.join(
    os.path.expanduser("~"), "AppData", "Local", "hermes",
    "hermes-agent", "venv", "Scripts", "edge-tts"
)

FFMPEG = os.path.join(
    os.path.expanduser("~"), "AppData", "Local", "Microsoft", "WinGet",
    "Packages", "Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe",
    "ffmpeg-8.1.1-full_build", "bin", "ffmpeg.exe"
)

POWERSHELL = "powershell"


# ═══════════════════════════════════════════
# LIMPEZA
# ═══════════════════════════════════════════

def limpar_cache(max_age: int = 3600) -> int:
    """Remove arquivos de áudio antigos do cache. Retorna quantidade removida."""
    removed = 0
    try:
        now = time.time()
        for f in OUTPUT_DIR.glob("tts_*"):
            try:
                if now - f.stat().st_mtime > max_age:
                    f.unlink()
                    removed += 1
            except (OSError, PermissionError):
                pass
    except Exception:
        pass
    return removed


# ═══════════════════════════════════════════
# GERAÇÃO DE ÁUDIO
# ═══════════════════════════════════════════

async def _gerar_audio(texto: str, output_file: Path) -> bool:
    """Gera áudio via Edge TTS (async)."""
    try:
        import edge_tts
        communicate = edge_tts.Communicate(texto, VOICE)
        await communicate.save(str(output_file))
        return output_file.exists()
    except ImportError:
        return False
    except Exception:
        return False


def gerar_audio(texto: str, output_file: Optional[Path] = None) -> Optional[Path]:
    """Gera áudio via Edge TTS (sync wrapper)."""
    if not texto.strip():
        return None

    if output_file is None:
        timestamp = int(time.time() * 1000)
        output_file = OUTPUT_DIR / f"tts_{timestamp}.mp3"

    try:
        asyncio.run(_gerar_audio(texto.strip(), output_file))
        if output_file.exists():
            return output_file
    except Exception:
        pass
    return None


def gerar_audio_cli(texto: str, output_file: Path) -> bool:
    """Gera áudio via edge-tts CLI (fallback)."""
    try:
        result = subprocess.run(
            [EDGE_TTS, "--voice", VOICE, "--text", texto,
             "--write-media", str(output_file)],
            capture_output=True, timeout=30
        )
        return output_file.exists()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
    except Exception:
        return False


# ═══════════════════════════════════════════
# REPRODUÇÃO
# ═══════════════════════════════════════════

def reproduzir_wav(wav_path: str) -> bool:
    """Reproduz arquivo WAV via PowerShell Media.SoundPlayer (bloqueante)."""
    try:
        ps_cmd = f"(New-Object Media.SoundPlayer '{wav_path}').PlaySync()"
        result = subprocess.run(
            [POWERSHELL, "-NoProfile", "-Command", ps_cmd],
            capture_output=True, timeout=120
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        return False
    except Exception:
        return False


def converter_para_wav(mp3_path: str, wav_path: str) -> bool:
    """Converte MP3 para WAV via ffmpeg."""
    try:
        result = subprocess.run(
            [FFMPEG, "-y", "-i", mp3_path,
             "-ar", "44100", "-ac", "-f", "wav", wav_path],
            capture_output=True, timeout=15
        )
        return os.path.exists(wav_path)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
    except Exception:
        return False


# ═══════════════════════════════════════════
# FUNÇÕES PRINCIPAIS
# ═══════════════════════════════════════════

def falar(texto: str, background: bool = False) -> Optional[str]:
    """
    Converte texto em fala e reproduz.
    
    Args:
        texto: Texto para falar
        background: Se True, não bloqueia (usando ffplay)
    
    Returns:
        Caminho do arquivo WAV ou None se falhou
    """
    if not texto or not texto.strip():
        return None

    # Limita texto para ser rápido (máx ~15 segundos)
    words = texto.split()
    if len(words) > 200:
        texto = " ".join(words[:200]) + "."

    # Gera MP3
    timestamp = int(time.time() * 1000)
    mp3_file = OUTPUT_DIR / f"tts_{timestamp}.mp3"
    wav_file = OUTPUT_DIR / f"tts_{timestamp}.wav"

    audio = gerar_audio(texto, mp3_file)
    if not audio:
        # Fallback: usar CLI
        if not gerar_audio_cli(texto, mp3_file):
            return None

    if not mp3_file.exists():
        return None

    # Converte para WAV
    if not converter_para_wav(str(mp3_file), str(wav_file)):
        return None

    # Reproduz
    if background:
        # Usa ffplay em background (não bloqueia)
        try:
            subprocess.Popen(
                ["ffplay", "-nodisp", "-autoexit", str(wav_file)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except FileNotFoundError:
            # Fallback: PowerShell em background
            try:
                subprocess.Popen(
                    [POWERSHELL, "-NoProfile", "-Command",
                     f"(New-Object Media.SoundPlayer '{wav_file}').PlaySync()"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            except Exception:
                pass
    else:
        # Bloqueante: usa PowerShell
        reproduzir_wav(str(wav_file))

    # Limpa MP3
    try:
        mp3_file.unlink(missing_ok=True)
    except (OSError, PermissionError):
        pass

    return str(wav_file) if wav_file.exists() else None


def falar_chunked(texto: str, chunk_size: int = 100):
    """
    Para textos longos: fala em chunks.
    Reduz a latência percebida.
    """
    if not texto or not texto.strip():
        return

    words = texto.split()
    chunks = []
    for i in range(0, len(words), chunk_size):
        chunks.append(" ".join(words[i:i + chunk_size]))

    # Fala o primeiro chunk imediatamente (bloqueante)
    if chunks:
        falar(chunks[0], background=False)

    # Processa o resto em background
    if len(chunks) > 1:
        for chunk in chunks[1:]:
            falar(chunk, background=True)


def speak_streaming():
    """
    Lê texto do stdin e fala frase por frase.
    Uso: echo "texto" | python -m lib.tts
    """
    buffer = ""
    chunk_index = 0

    for line in sys.stdin:
        buffer += line
        sentences = _split_sentences(buffer)
        if len(sentences) > 1:
            for sentence in sentences[:-1]:
                falar(sentence, background=True)
                chunk_index += 1
            buffer = sentences[-1]

    if buffer.strip():
        falar(buffer.strip(), background=False)


def _split_sentences(text: str) -> list:
    """Divide texto em frases."""
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sentences if s.strip()]


# ═══════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="TTS do OWL")
    parser.add_argument("texto", nargs="?", help="Texto para falar")
    parser.add_argument("--chunked", action="store_true", help="Falar em chunks")
    parser.add_argument("--background", action="store_true", help="Não bloquear")
    parser.add_argument("--stdin", action="store_true", help="Ler do stdin")
    parser.add_argument("--limpar", action="store_true", help="Limpar cache")

    args = parser.parse_args()

    if args.limpar:
        removed = limpar_cache()
        print(f"Cache limpo: {removed} arquivos removidos.")
    elif args.stdin:
        speak_streaming()
    elif args.chunked and args.texto:
        falar_chunked(args.texto)
    elif args.texto:
        falar(args.texto, background=args.background)
    else:
        parser.print_help()
