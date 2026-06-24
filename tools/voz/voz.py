#!/usr/bin/env python3
"""Koldi's Voz — Wrapper do TTS com fallback em cadeia.
   Delega para tts_koldi.py (SAPI5 → edge-tts → VBScript).
   Uso: python voz.py "texto"
"""
import sys, subprocess

# Windows: CREATE_NO_WINDOW to prevent CMD flash
WIN_FLAGS = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
TTS = __import__('pathlib').Path.home() / "AppData/Local/hermes/scripts/tts_koldi.py"
if len(sys.argv) > 1:
    subprocess.run(["python", str(TTS)] + sys.argv[1:], timeout=30,
                       creationflags=WIN_FLAGS)
else:
    texto = sys.stdin.read()
    if texto.strip():
        subprocess.run(["python", str(TTS), texto.strip()], timeout=30,
                       creationflags=WIN_FLAGS)