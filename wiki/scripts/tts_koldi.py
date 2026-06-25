#!/usr/bin/env python3
"""
tts_koldi.py — Guaranteed Fallback-Chain TTS for Windows CLI

Fallback chain:
  1. edge-tts  (--volume +100%, --rate +0%)
  2. SAPI5 SpVoice via PowerShell
  3. SAPI5 SpVoice via VBScript (cscript.exe)

ALWAYS returns True (never fails silently).
Logs every attempt/fallback to stderr.

Usage:
    tts_koldi.py "text to speak"
    echo "text" | tts_koldi.py
"""

import asyncio
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path


# ── configuration ──────────────────────────────────────────────────────────

VOICE = "pt-BR-FranciscaNeural"  # fallback voice for edge-tts
RATE = "+0%"
VOLUME = "+100%"

EDGE_TTS_TIMEOUT = 30
PS_TIMEOUT = 20
VBS_TIMEOUT = 15

HERMES_VENV = Path.home() / "AppData/Local/hermes/hermes-agent/venv"
EDGE_TTS_EXE = HERMES_VENV / "Scripts" / "edge-tts.exe"

# Use the venv Python – it has edge-tts installed
HERMES_PYTHON = HERMES_VENV / "Scripts" / "python.exe"


# ── helpers ────────────────────────────────────────────────────────────────

def _log(msg: str, level: str = "WARN") -> None:
    """Log a message to stderr with a uniform prefix."""
    print(f"[tts_koldi] [{level}] {msg}", file=sys.stderr, flush=True)


def _chromium_mp3_path() -> str:
    """Return a unique temporary MP3 path."""
    ts = str(int(time.time() * 1000000))
    return os.path.join(tempfile.gettempdir(), f"tts_koldi_{ts}.mp3")


# ── tier 1: edge-tts CLI (most reliable) ─────────────────────────────────

def _try_edge_tts_cli(text: str) -> bool:
    """Speak via edge-tts CLI tool (edge-tts.exe) with WAV conversion."""
    try:
        ts = str(int(time.time() * 1000000))
        mp3 = os.path.join(tempfile.gettempdir(), f"koldi_{ts}.mp3")
        wav = os.path.join(tempfile.gettempdir(), f"koldi_{ts}.wav")
        _log("Tier 1: edge-tts CLI...", "INFO")

        # Generate MP3
        r = subprocess.run(
            [str(EDGE_TTS_EXE), "--voice", VOICE, "--rate", RATE,
             "--text", text, "--write-media", mp3],
            timeout=EDGE_TTS_TIMEOUT, capture_output=True,
        )
        if r.returncode != 0 or not os.path.exists(mp3) or os.path.getsize(mp3) == 0:
            _log(f"edge-tts CLI failed (rc={r.returncode})")
            return False

        # Convert to WAV via ffmpeg (PowerShell can't play MP3 reliably)
        ffmpeg_found = False
        for candidate in ["C:/Users/dell-/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-8.1.1-full_build/bin/ffmpeg.exe",
                          "C:/Users/dell-/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-8.1-full_build/bin/ffmpeg.exe",
                          "ffmpeg.exe"]:
            if os.path.exists(candidate) or candidate == "ffmpeg.exe":
                r2 = subprocess.run(
                    [candidate, "-y", "-i", mp3, "-acodec", "pcm_s16le", "-ar", "22050", "-ac", "1", wav],
                    timeout=15, capture_output=True,
                )
                if r2.returncode == 0 and os.path.exists(wav):
                    ffmpeg_found = True
                    break

        audio = wav if ffmpeg_found else mp3  # fallback to MP3 if ffmpeg fails

        # Play via PowerShell
        _log("Playing via PowerShell...", "INFO")
        ps_cmd = f"$p = New-Object Media.SoundPlayer '{audio}'; $p.PlaySync()"
        r3 = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            timeout=EDGE_TTS_TIMEOUT, capture_output=True,
        )
        if r3.returncode == 0:
            _log("Tier 1: edge-tts CLI OK", "OK")
            return True
        _log(f"Playback failed (rc={r3.returncode})")
        return False
    except Exception as exc:
        _log(f"edge-tts CLI exception: {exc}")
        return False
    finally:
        for f in [mp3, wav]:
            try:
                if os.path.exists(f): os.remove(f)
            except: pass


# ── tier 1b: edge-tts direct Python import (fallback, gets 403 sometimes) ─
def _try_edge_tts_direct(text: str) -> bool:
    """Speak via edge-tts Python package directly."""
    import asyncio
    async def _inner():
        try:
            import edge_tts
            mp3 = _chromium_mp3_path()
            communicate = edge_tts.Communicate(text, VOICE, rate=RATE, volume=VOLUME)
            await communicate.save(mp3)
            if not os.path.exists(mp3) or os.path.getsize(mp3) == 0:
                return False
            ps_cmd = f"$p = New-Object Media.SoundPlayer '{mp3}'; $p.PlaySync()"
            r = subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd],
                               timeout=EDGE_TTS_TIMEOUT, capture_output=True)
            return r.returncode == 0
        except: return False
        finally:
            try:
                if os.path.exists(mp3): os.remove(mp3)
            except: pass
    try:
        return asyncio.run(_inner())
    except:
        return False


# ── tier 2: SAPI5 via PowerShell ─────────────────────────────────────────

def _try_sapi5_powershell(text: str) -> bool:
    """Speak via Windows SAPI5 SpVoice using one-liner PowerShell."""
    try:
        _log("Tier 2: SAPI5 SpVoice via PowerShell...", "INFO")

        # Escape single quotes in the text for PowerShell
        safe_text = text.replace("'", "''")

        ps_cmd = (
            "$v = New-Object -ComObject SAPI.SpVoice; "
            "$v.Rate = 0; "
            "$v.Volume = 100; "
            f"$v.Speak('{safe_text}')"
        )

        r = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
            timeout=PS_TIMEOUT,
            capture_output=True,
        )
        if r.returncode == 0:
            _log("Tier 2: SAPI5 PowerShell OK", "OK")
            return True
        else:
            stderr = r.stderr.decode("utf-8", errors="replace")[:300]
            _log(f"SAPI5 PowerShell failed (rc={r.returncode}): {stderr}")
            return False
    except Exception as exc:
        _log(f"SAPI5 PowerShell exception: {exc}")
        return False


# ── tier 3: SAPI5 via VBScript ────────────────────────────────────────────

def _try_sapi5_vbscript(text: str) -> bool:
    """Speak via SAPI5 SpVoice using a .vbs file executed by cscript.exe."""
    _log("Tier 3: SAPI5 SpVoice via VBScript...", "INFO")

    vbs_path = os.path.join(
        tempfile.gettempdir(),
        f"tts_koldi_{int(time.time() * 1000000)}.vbs",
    )

    # Escape double quotes for VBScript — double them up
    safe_text = text.replace('"', '""')

    vbs_content = f"""' tts_koldi.vbs — generated by tts_koldi.py
Dim voice
Set voice = CreateObject("SAPI.SpVoice")
voice.Rate = 0
voice.Volume = 100
voice.Speak "{safe_text}"
Set voice = Nothing
"""

    try:
        with open(vbs_path, "w", encoding="utf-8") as f:
            f.write(vbs_content)

        r = subprocess.run(
            ["cscript.exe", "/NoLogo", vbs_path],
            timeout=VBS_TIMEOUT,
            capture_output=True,
        )
        if r.returncode == 0:
            _log("Tier 3: VBScript SAPI5 OK", "OK")
            return True
        else:
            stderr = r.stderr.decode("utf-8", errors="replace")[:300]
            stdout = r.stdout.decode("utf-8", errors="replace")[:300]
            _log(
                f"VBScript failed (rc={r.returncode}): stderr={stderr} stdout={stdout}"
            )
            return False
    except subprocess.TimeoutExpired:
        _log("VBScript timed out")
        return False
    except Exception as exc:
        _log(f"VBScript exception: {exc}")
        return False
    finally:
        try:
            if os.path.exists(vbs_path):
                os.remove(vbs_path)
        except Exception:
            pass


# ── main TTS function ─────────────────────────────────────────────────────

def falar(texto: str) -> bool:
    """
    Speak `texto` using the fallback chain.
    ALWAYS returns True — even if every tier fails.
    Logs every attempt and fallback to stderr.
    """
    if not texto or not texto.strip():
        return True

    texto = texto.strip()

    _log(f"Speaking {len(texto)} chars: {texto[:80]}{'...' if len(texto) > 80 else ''}", "INFO")

    # ── Tier 1: edge-tts CLI (best quality, WAV converted) ──
    if _try_edge_tts_cli(texto):
        return True

    # ── Tier 2: edge-tts direct Python ──
    _log("⬇️  edge-tts CLI failed, trying direct...", "FALLBACK")
    if _try_edge_tts_direct(texto):
        return True

    # ── Tier 3: SAPI5 via PowerShell (lower quality but always works) ──
    _log("⬇️  Trying SAPI5 PowerShell...", "FALLBACK")
    if _try_sapi5_powershell(texto):
        return True

    # ── Tier 4: SAPI5 via VBScript (last resort) ──
    _log("⬇️  Falling back to VBScript...", "FALLBACK")

    if _try_sapi5_vbscript(texto):
        return True

    # ── All tiers failed — still return True ──
    _log(
        "⚠️  ALL THREE TIERS FAILED — returning True anyway (guaranteed no-fail)",
        "ERROR",
    )
    return True


# ── entry point ────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) > 1:
        text = " ".join(sys.argv[1:])
    else:
        text = sys.stdin.read()

    if not text.strip():
        print(__doc__, file=sys.stderr)
        sys.exit(0)

    falar(text)


if __name__ == "__main__":
    main()
