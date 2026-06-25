#!/usr/bin/env python3
"""
TTS v2 - Script de Text-to-Speech do OWL.
Usa edge-tts + ffmpeg + PowerShell Media.SoundPlayer.

Uso: python tts.py "texto para falar"
"""

import subprocess
import sys
import os
import tempfile
import time
from pathlib import Path

VOICE = "pt-BR-FranciscaNeural"
FFMPEG = os.path.join(
    os.path.expanduser("~"), "AppData", "Local", "Microsoft", "WinGet",
    "Packages", "Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe",
    "ffmpeg-8.1.1-full_build", "bin", "ffmpeg.exe"
)
EDGE_TTS = os.path.join(
    os.path.expanduser("~"), "AppData", "Local", "hermes",
    "hermes-agent", "venv", "Scripts", "edge-tts"
)


def falar(texto):
    """Fala um texto em voz alta."""
    if not texto or not texto.strip():
        return
    
    # Limita texto
    words = texto.split()
    if len(words) > 200:
        texto = " ".join(words[:200]) + "."
    
    timestamp = int(time.time() * 1000)
    tmp_dir = Path(tempfile.gettempdir())
    mp3_file = tmp_dir / f"tts_{timestamp}.mp3"
    wav_file = tmp_dir / f"tts_{timestamp}.wav"
    
    try:
        # 1. Gera MP3 via edge-tts
        subprocess.run(
            [EDGE_TTS, "--voice", VOICE, "--text", texto,
             "--write-media", str(mp3_file)],
            capture_output=True, timeout=30
        )
        
        if not mp3_file.exists():
            print(f"[TTS] Erro: MP3 não gerado", file=sys.stderr)
            return
        
        # 2. Converte MP3 para WAV
        subprocess.run(
            [FFMPEG, "-y", "-i", str(mp3_file),
             "-ar", "44100", "-ac", "2", "-f", "wav", str(wav_file)],
            capture_output=True, timeout=15
        )
        
        if not wav_file.exists():
            print(f"[TTS] Erro: WAV não gerado", file=sys.stderr)
            return
        
        # 3. Toca via PowerShell
        ps_cmd = f"(New-Object Media.SoundPlayer '{wav_file}').PlaySync()"
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            capture_output=True, timeout=120
        )
        
    except subprocess.TimeoutExpired:
        print(f"[TTS] Timeout", file=sys.stderr)
    except Exception as e:
        print(f"[TTS] Erro: {e}", file=sys.stderr)
    finally:
        # Limpa arquivos
        try:
            mp3_file.unlink(missing_ok=True)
            wav_file.unlink(missing_ok=True)
        except:
            pass


if __name__ == "__main__":
    if len(sys.argv) > 1:
        texto = " ".join(sys.argv[1:])
        falar(texto)
    else:
        print("Uso: python tts.py \"texto para falar\"")
