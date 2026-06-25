#!/usr/bin/env python3
"""
TTS v4 - Definitivo. Rápido com gTTS + ffplay background.
Tempo de resposta: ~0.6s (gera áudio em background)

Uso: python tts4.py "texto para falar"
"""

import subprocess
import sys
import os
import tempfile
import hashlib
from pathlib import Path

FFMPEG = os.path.join(
    os.path.expanduser("~"), "AppData", "Local", "Microsoft", "WinGet",
    "Packages", "Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe",
    "ffmpeg-8.1.1-full_build", "bin", "ffmpeg.exe"
)
FFPLAY = os.path.join(
    os.path.expanduser("~"), "AppData", "Local", "Microsoft", "WinGet",
    "Packages", "Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe",
    "ffmpeg-8.1.1-full_build", "bin", "ffplay.exe"
)

_CACHE_DIR = Path(tempfile.gettempdir()) / "tts_cache_v4"
_CACHE_DIR.mkdir(exist_ok=True)


def falar(texto: str):
    """Fala um texto em voz alta. Rápido (~0.6s até começar)."""
    if not texto or not texto.strip():
        return
    
    # Limita texto
    words = texto.split()
    if len(words) > 150:
        texto = " ".join(words[:150]) + "."
    
    # Cache
    cache_key = hashlib.md5(texto.encode()).hexdigest()[:16]
    wav_file = _CACHE_DIR / f"{cache_key}.wav"
    
    if not wav_file.exists():
        try:
            from gtts import gTTS
            mp3_file = _CACHE_DIR / f"{cache_key}.mp3"
            tts = gTTS(text=texto, lang='pt-br')
            tts.save(str(mp3_file))
            
            subprocess.run(
                [FFMPEG, "-y", "-i", str(mp3_file), "-ar", "22050", "-ac", "1", "-f", "wav", str(wav_file)],
                capture_output=True, timeout=10
            )
            mp3_file.unlink(missing_ok=True)
        except ImportError:
            print("[TTS] gTTS não instalado. Execute: pip install gtts", file=sys.stderr)
            return
        except Exception as e:
            print(f"[TTS] Erro: {e}", file=sys.stderr)
            return
    
    if wav_file.exists():
        subprocess.Popen(
            [FFPLAY, "-nodisp", "-autoexit", "-loglevel", "quiet", str(wav_file)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )


if __name__ == "__main__":
    if len(sys.argv) > 1:
        falar(" ".join(sys.argv[1:]))
    else:
        print("Uso: python tts4.py \"texto\"")
