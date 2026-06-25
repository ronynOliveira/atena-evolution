#!/usr/bin/env python3
"""
TTS v3 - Otimizado para velocidade.
Usa edge-tts com cache e reprodução direta via ffplay.

Uso: python tts_rapido.py "texto para falar"
"""

import subprocess
import sys
import os
import tempfile
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

# Cache de áudio para frases repetidas
_CACHE_DIR = Path(tempfile.gettempdir()) / "tts_cache"
_CACHE_DIR.mkdir(exist_ok=True)


def falar(texto: str, background: bool = False):
    """Fala um texto em voz alta de forma otimizada."""
    if not texto or not texto.strip():
        return
    
    # Limita texto para ser rápido
    words = texto.split()
    if len(words) > 150:
        texto = " ".join(words[:150]) + "."
    
    # Verificar cache
    import hashlib
    cache_key = hashlib.md5(f"{VOICE}:{texto}".encode()).hexdigest()[:12]
    mp3_file = _CACHE_DIR / f"{cache_key}.mp3"
    
    # Gerar áudio se não estiver em cache
    if not mp3_file.exists():
        subprocess.run(
            [EDGE_TTS, "--voice", VOICE, "--text", texto,
             "--write-media", str(mp3_file)],
            capture_output=True, timeout=15
        )
    
    if not mp3_file.exists():
        print(f"[TTS] Erro: áudio não gerado", file=sys.stderr)
        return
    
    # Reproduzir diretamente com ffplay (mais rápido que PowerShell)
    if background:
        subprocess.Popen(
            [FFPLAY, "-nodisp", "-autoexit", "-loglevel", "quiet", str(mp3_file)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    else:
        subprocess.run(
            [FFPLAY, "-nodisp", "-autoexit", "-loglevel", "quiet", str(mp3_file)],
            capture_output=True, timeout=60
        )


def limpar_cache():
    """Limpa o cache de áudio."""
    import glob
    for f in glob.glob(str(_CACHE_DIR / "*.mp3")):
        try:
            os.unlink(f)
        except:
            pass
    print(f"Cache limpo: {_CACHE_DIR}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--limpar":
            limpar_cache()
        else:
            texto = " ".join(sys.argv[1:])
            falar(texto)
    else:
        print("Uso: python tts_rapido.py \"texto para falar\"")
        print("       python tts_rapido.py --limpar  (limpa cache)")
