#!/usr/bin/env python3
"""
TTS Otimizado - edge-tts com reprodução não-bloqueante
Voz: pt-BR-FranciscaNeural (alta qualidade)
Cache: disco para frases repetidas
Fallback: gTTS se edge-tts falhar
"""

import os
import sys
import asyncio
import hashlib
import tempfile
import subprocess
import threading
import time
from pathlib import Path
from functools import lru_cache

# ── Configurações ──────────────────────────────────────────────
VOICE = "pt-BR-FranciscaNeural"
RATE = "+0%"        # velocidade: -50% a +100%
VOLUME = "+0%"      # volume: -100% a +100%
PITCH = "+0Hz"      # pitch: -50Hz a +50Hz

CACHE_DIR = Path(tempfile.gettempdir()) / "tts_cache"
CACHE_DIR.mkdir(exist_ok=True)

FFPLAY_PATH = r"C:\Users\dell-\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffplay.exe"

# ── Cache de áudio ─────────────────────────────────────────────
def _cache_key(text: str, voice: str = VOICE) -> str:
    """Gera hash única para texto+voz."""
    raw = f"{voice}:{text}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]

def _get_cached_path(text: str, voice: str = VOICE) -> Path | None:
    """Retorna caminho do cache se existir, senão None."""
    key = _cache_key(text, voice)
    path = CACHE_DIR / f"{key}.mp3"
    if path.exists() and path.stat().st_size > 0:
        return path
    return None

def _save_to_cache(text: str, audio_data: bytes, voice: str = VOICE) -> Path:
    """Salva áudio no cache e retorna o caminho."""
    key = _cache_key(text, voice)
    path = CACHE_DIR / f"{key}.mp3"
    path.write_bytes(audio_data)
    return path

# ── Geradores de áudio ─────────────────────────────────────────
async def _generate_edge_tts(text: str, voice: str = VOICE) -> bytes:
    """Gera áudio usando edge-tts (alta qualidade)."""
    import edge_tts
    communicate = edge_tts.Communicate(text, voice, rate=RATE, volume=VOLUME, pitch=PITCH)
    chunks = []
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            chunks.append(chunk["data"])
    return b"".join(chunks)

def _generate_gtts(text: str, lang: str = "pt-br") -> bytes:
    """Fallback: gera áudio usando gTTS."""
    from gtts import gTTS
    from io import BytesIO
    tts = gTTS(text=text, lang=lang, slow=False)
    buf = BytesIO()
    tts.write_to_fp(buf)
    return buf.getvalue()

# ── Reprodução não-bloqueante ─────────────────────────────────
def _play_with_ffplay(audio_path: Path) -> subprocess.Popen:
    """Toca áudio com ffplay em background (não-bloqueante)."""
    cmd = [
        FFPLAY_PATH,
        "-nodisp",          # sem janela de vídeo
        "-autoexit",        # sai ao terminar
        "-loglevel", "quiet",  # sem output
        str(audio_path)
    ]
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    )
    return proc

def _play_with_pygame(audio_path: Path) -> None:
    """Toca áudio com pygame em thread separada."""
    import pygame
    def _play():
        try:
            pygame.mixer.init(frequency=24000)
            pygame.mixer.music.load(str(audio_path))
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
            pygame.mixer.quit()
        except Exception as e:
            print(f"[TTS] Erro pygame: {e}", file=sys.stderr)
    t = threading.Thread(target=_play, daemon=True)
    t.start()

def _play_with_simpleaudio(audio_path: Path) -> None:
    """Toca áudio com simpleaudio em thread separada."""
    import simpleaudio as sa
    def _play():
        try:
            wave_obj = sa.WaveObject.from_wave_file(str(audio_path))
            play_obj = wave_obj.play()
            play_obj.wait_done()
        except Exception as e:
            # simpleaudio só lê WAV; se falhar, usa ffplay
            _play_with_ffplay(audio_path)
    t = threading.Thread(target=_play, daemon=True)
    t.start()

def _play_with_pydub(audio_path: Path) -> None:
    """Toca áudio com pydub em thread separada."""
    from pydub import AudioSegment
    from pydub.playback import play
    def _play():
        try:
            audio = AudioSegment.from_file(str(audio_path))
            play(audio)
        except Exception as e:
            print(f"[TTS] Erro pydub: {e}", file=sys.stderr)
            _play_with_ffplay(audio_path)
    t = threading.Thread(target=_play, daemon=True)
    t.start()

# ── Motor principal ────────────────────────────────────────────
class TTSEngine:
    """Motor TTS com cache e reprodução não-bloqueante."""

    def __init__(self, voice: str = VOICE, engine: str = "auto"):
        self.voice = voice
        self.engine = engine  # "auto", "edge", "gtts"
        self._player_proc: subprocess.Popen | None = None
        self._lock = threading.Lock()

    def speak(self, text: str, block: bool = False, player: str = "ffplay") -> Path:
        """
        Fala o texto. Retorna o caminho do arquivo de áudio.

        Args:
            text: Texto para falar
            block: Se True, bloqueia até terminar
            player: "ffplay", "pygame", "pydub", "simpleaudio"
        """
        t0 = time.perf_counter()

        if not text.strip():
            return Path()

        # 1. Verifica cache
        cached = _get_cached_path(text, self.voice)
        if cached:
            print(f"[TTS] Cache hit: {cached.name}")
            audio_path = cached
        else:
            # 2. Gera áudio
            audio_data = self._generate(text)
            if not audio_data:
                print("[TTS] Falha ao gerar áudio", file=sys.stderr)
                return Path()
            audio_path = _save_to_cache(text, audio_data, self.voice)
            print(f"[TTS] Gerado e cacheado: {audio_path.name}")

        # 3. Reproduz sem bloquear
        self._play(audio_path, player, block)

        elapsed = (time.perf_counter() - t0) * 1000
        print(f"[TTS] Tempo total: {elapsed:.0f}ms")
        return audio_path

    def _generate(self, text: str) -> bytes:
        """Gera áudio com edge-tts ou fallback gTTS."""
        # Tenta edge-tts
        if self.engine in ("auto", "edge"):
            try:
                print(f"[TTS] Gerando com edge-tts (voz: {self.voice})...")
                data = asyncio.run(_generate_edge_tts(text, self.voice))
                if data:
                    return data
            except Exception as e:
                print(f"[TTS] edge-tts falhou: {e}", file=sys.stderr)
                if self.engine == "edge":
                    return b""

        # Fallback: gTTS
        if self.engine in ("auto", "gtts"):
            try:
                print("[TTS] Fallback: gerando com gTTS...")
                return _generate_gtts(text)
            except Exception as e:
                print(f"[TTS] gTTS falhou: {e}", file=sys.stderr)

        return b""

    def _play(self, audio_path: Path, player: str, block: bool):
        """Reproduz áudio com o player escolhido."""
        players = {
            "ffplay": _play_with_ffplay,
            "pygame": _play_with_pygame,
            "pydub": _play_with_pydub,
            "simpleaudio": _play_with_simpleaudio,
        }

        play_fn = players.get(player, _play_with_ffplay)

        if player == "ffplay":
            # ffplay retorna Popen; podemos esperar ou não
            self._player_proc = play_fn(audio_path)
            if block:
                self._player_proc.wait()
        else:
            # Outros players usam threads daemon
            play_fn(audio_path)
            if block:
                # Estimativa grosseira: ~150 palavras/min
                time.sleep(0.5)  # mínimo

    def stop(self):
        """Para a reprodução atual."""
        if self._player_proc and self._player_proc.poll() is None:
            self._player_proc.terminate()
            self._player_proc = None

    def clear_cache(self):
        """Limpa o cache de áudio."""
        count = 0
        for f in CACHE_DIR.glob("*.mp3"):
            f.unlink()
            count += 1
        print(f"[TTS] Cache limpo: {count} arquivos removidos")

# ── API simples (módulo-level) ─────────────────────────────────
_default_engine: TTSEngine | None = None

def _get_engine() -> TTSEngine:
    global _default_engine
    if _default_engine is None:
        _default_engine = TTSEngine()
    return _default_engine

def speak(text: str, block: bool = False, player: str = "ffplay") -> Path:
    """Fala o texto (API simples)."""
    return _get_engine().speak(text, block, player)

def stop():
    """Para a reprodução."""
    _get_engine().stop()

def clear_cache():
    """Limpa o cache."""
    _get_engine().clear_cache()

# ── CLI ────────────────────────────────────────────────────────
def main():
    import argparse
    parser = argparse.ArgumentParser(description="TTS Otimizado - pt-BR-FranciscaNeural")
    parser.add_argument("text", nargs="*", help="Texto para falar")
    parser.add_argument("--voice", "-v", default=VOICE, help="Voz a usar")
    parser.add_argument("--player", "-p", default="ffplay",
                        choices=["ffplay", "pygame", "pydub", "simpleaudio"])
    parser.add_argument("--engine", "-e", default="auto",
                        choices=["auto", "edge", "gtts"])
    parser.add_argument("--block", "-b", action="store_true", help="Bloqueia até terminar")
    parser.add_argument("--clear-cache", action="store_true", help="Limpa o cache")
    parser.add_argument("--interactive", "-i", action="store_true", help="Modo interativo")
    parser.add_argument("--benchmark", action="store_true", help="Teste de desempenho")
    args = parser.parse_args()

    if args.clear_cache:
        TTSEngine().clear_cache()
        return

    engine = TTSEngine(voice=args.voice, engine=args.engine)

    if args.benchmark:
        _benchmark(engine, args.player)
        return

    if args.interactive:
        print("=== TTS Interativo (pt-BR-FranciscaNeural) ===")
        print("Digite 'sair' para encerrar, 'parar' para interromper")
        while True:
            try:
                text = input("\n🗣️  > ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if text.lower() in ("sair", "exit", "quit"):
                break
            if text.lower() == "parar":
                engine.stop()
                continue
            if text:
                engine.speak(text, block=False, player=args.player)
        return

    # Texto da CLI
    text = " ".join(args.text) if args.text else None
    if not text:
        # Demo
        text = "Olá! Este é um teste do sistema de texto para fala em português do Brasil."
        print(f"[Demo] {text}")

    engine.speak(text, block=args.block, player=args.player)

def _benchmark(engine: TTSEngine, player: str):
    """Teste de desempenho."""
    print("=== Benchmark TTS ===\n")
    frases = [
        "Olá, tudo bem?",
        "Este é um teste de desempenho do sistema de texto para fala.",
        "O Brasil é um país com grande diversidade cultural e natural.",
        "A inteligência artificial está transformando a maneira como interagimos com tecnologia.",
    ]

    for i, frase in enumerate(frases, 1):
        print(f"--- Frase {i}/{len(frases)} ---")
        print(f"Texto: {frase[:60]}...")
        t0 = time.perf_counter()
        engine.speak(frase, block=False, player=player)
        elapsed = (time.perf_counter() - t0) * 1000
        print(f"Tempo (não-bloqueante): {elapsed:.0f}ms\n")

    # Teste com cache
    print("--- Teste com cache (repetindo frase 1) ---")
    t0 = time.perf_counter()
    engine.speak(frases[0], block=False, player=player)
    elapsed = (time.perf_counter() - t0) * 1000
    print(f"Tempo com cache: {elapsed:.0f}ms\n")

    print("=== Cache ===")
    files = list(CACHE_DIR.glob("*.mp3"))
    total = sum(f.stat().st_size for f in files)
    print(f"Arquivos: {len(files)} | Tamanho total: {total/1024:.1f} KB")

if __name__ == "__main__":
    main()
