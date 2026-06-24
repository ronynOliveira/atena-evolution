#!/usr/bin/env python3
"""Lesson Loop — lições aprendidas em sessão. Anexa no final do arquivo."""
import sys, os, json
LESSONS = os.path.join(os.path.dirname(__file__), "..", "lessons.jsonl")
LESSONS = os.path.abspath(LESSONS)

with open(LESSONS, "a") as f:
    f.write(json.dumps({
        "event": "tts_powershell_mp3_bug",
        "date": "2025-05-25",
        "summary": "PowerShell Media.SoundPlayer não toca MP3 — edge-tts CLI caía para SAPI5 (voz robótica)",
        "fix": "Adicionar conversão MP3→WAV via ffmpeg no Tier 1 do tts_koldi.py. Reordenar tiers: edge-tts CLI primeiro, SAPI5 como fallback.",
        "file": "scripts/tts_koldi.py"
    }) + "\n")
print("✅ Lição salva")
