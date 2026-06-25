#!/usr/bin/env python3
"""
TTS v3 - Otimizado com cache inteligente.
Usa edge-tts com cache de áudio e reprodução direta.

Uso: python tts3.py "texto para falar"
"""

import subprocess
import sys
import os
import tempfile
import hashlib
import time
from pathlib import Path

VOICE = "pt-BR-FranciscaNeural"
EDGE_TTS = os.path.join(
    os.path.expanduser("~"), "AppData", "Local", "hermes",
    "hermes-agent", "venv", "Scripts", "edge-tts"
)
FFPLAY = os.path.join(
    os.path.expanduser("~"), "AppData", "Local", "Microsoft", "WinGet",
    "Packages", "Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe",
    "ffmpeg-8.1.1-full_build", "bin", "ffplay.exe"
)

_CACHE_DIR = Path(tempfile.gettempdir()) / "tts_cache_v3"
_CACHE_DIR.mkdir(exist_ok=True)


def falar(texto: str, background: bool = False):
    """Fala um texto em voz alta de forma otimizada."""
    if not texto or not texto.strip():
        return
    
    # Limita texto
    words = texto.split()
    if len(words) > 150:
        texto = " ".join(words[:150]) + "."
    
    # Cache
    cache_key = hashlib.md5(f"{VOICE}:{texto}".encode()).hexdigest()[:16]
    wav_file = _CACHE_DIR / f"{cache_key}.wav"
    
    if not wav_file.exists():
        # Gerar MP3
        mp3_file = _CACHE_DIR / f"{cache_key}.mp3"
        subprocess.run(
            [EDGE_TTS, "--voice", VOICE, "--text", texto, "--write-media", str(mp3_file)],
            capture_output=True, timeout=15
        )
        
        if mp3_file.exists():
            # Converter para WAV
            subprocess.run(
                ["ffmpeg", "-y", "-i", str(mp3_file), "-ar", "22050", "-ac", "1", "-f", "wav", str(wav_file)],
                capture_output=True, timeout=10
            )
            mp3_file.unlink(missing_ok=True)
    
    if wav_file.exists():
        cmd = [FFPLAY, "-nodisp", "-autoexit", "-loglevel", "quiet", str(wav_file)]
        if background:
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            subprocess.run(cmd, capture_output=True, timeout=60)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        falar(" ".join(sys.argv[1:]))
    else:
        print("Uso: python tts3.py \"texto\"")
