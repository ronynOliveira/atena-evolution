#!/usr/bin/env python3
"""TTS helper - fala texto em voz alta no Windows."""
import subprocess, sys, os, tempfile, time
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
    if not texto or not texto.strip():
        return
    mp3 = os.path.join(tempfile.gettempdir(), f"tts_{int(time.time())}.mp3")
    wav = os.path.join(tempfile.gettempdir(), f"tts_{int(time.time())}.wav")
    try:
        subprocess.run([EDGE_TTS, "--voice", VOICE, "--text", texto, "--write-media", mp3], timeout=30, capture_output=True)
        subprocess.run([FFMPEG, "-y", "-i", mp3, "-acodec", "pcm_s16le", "-ar", "22050", "-ac", "1", wav], timeout=15, capture_output=True)
        subprocess.run(["powershell", "-Command", f"(New-Object Media.SoundPlayer '{wav}').PlaySync()"], timeout=30)
    except Exception as e:
        print(f"TTS Error: {e}", file=sys.stderr)
    finally:
        for f in [mp3, wav]:
            try:
                os.remove(f)
            except:
                pass

if __name__ == "__main__":
    texto = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else sys.stdin.read()
    falar(texto)
