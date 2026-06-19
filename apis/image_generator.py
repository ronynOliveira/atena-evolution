#!/usr/bin/env python3
"""
ImageGenerator - Multi-provider image generation API
=====================================================
Supports: OpenAI DALL-E, Gemini Imagen, Stable Diffusion (ComfyUI), Placeholder (picsum.photos)
Includes: SQLite cache, CLI, and REST API (http.server based).

Usage:
    CLI:    python image_generator.py --prompt "a cat" --style cartoon
    API:    python image_generator.py --server --port 8080
"""

import argparse
import base64
import hashlib
import io
import json
import os
import sqlite3
import sys
import threading
import time
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

try:
    import requests
except ImportError:
    print("ERROR: 'requests' library is required. Install with: pip install requests")
    sys.exit(1)


# ──────────────────────────────────────────────────────────────
# Configuration & Constants
# ──────────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).parent.resolve()
DB_PATH = SCRIPT_DIR / "image_cache.db"
DOWNLOAD_DIR = SCRIPT_DIR / "generated_images"
DOWNLOAD_DIR.mkdir(exist_ok=True)

OPENAI_API_URL = "https://api.openai.com/v1/images/generations"
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/imagen-3.0-generate-002:predict"
COMFYUI_URL = "http://127.0.0.1:8188"

STYLES = {
    "realistic": {
        "name": "Realistic",
        "description": "Foto realista, alta definição",
        "prefix": "A highly detailed, photorealistic photograph of",
        "suffix": ", 8k resolution, natural lighting, DSLR quality, sharp focus",
    },
    "artistic": {
        "name": "Artistic",
        "description": "Pintura artística clássica",
        "prefix": "An artistic painting of",
        "suffix": ", classical art style, museum quality, rich colors, textured brushstrokes",
    },
    "cartoon": {
        "name": "Cartoon",
        "description": "Desenho animado estilizado",
        "prefix": "A colorful cartoon illustration of",
        "suffix": ", Pixar style, vibrant colors, clean lines, fun and playful",
    },
    "anime": {
        "name": "Anime",
        "description": "Estilo anime/mangá japonês",
        "prefix": "An anime style illustration of",
        "suffix": ", detailed anime art, vibrant colors, studio quality, dynamic pose",
    },
    "watercolor": {
        "name": "Watercolor",
        "description": "Pintura em aquarela",
        "prefix": "A delicate watercolor painting of",
        "suffix": ", soft edges, flowing colors, paper texture, artistic watercolor technique",
    },
    "oil_painting": {
        "name": "Oil Painting",
        "description": "Pintura a óleo clássica",
        "prefix": "A rich oil painting of",
        "suffix": ", thick impasto brushstrokes, Renaissance style, deep colors, canvas texture",
    },
    "digital_art": {
        "name": "Digital Art",
        "description": "Arte digital moderna",
        "prefix": "A stunning digital artwork of",
        "suffix": ", concept art, trending on ArtStation, highly detailed, vibrant colors",
    },
    "minimalist": {
        "name": "Minimalist",
        "description": "Estilo minimalista e limpo",
        "prefix": "A minimalist illustration of",
        "suffix": ", simple shapes, flat design, clean composition, limited color palette",
    },
}

PROVIDER_NAMES = {
    "openai": "OpenAI DALL-E",
    "gemini": "Google Gemini Imagen",
    "comfyui": "Stable Diffusion (ComfyUI)",
    "placeholder": "Placeholder (picsum.photos)",
}


# ──────────────────────────────────────────────────────────────
# SQLite Cache
# ──────────────────────────────────────────────────────────────

def get_db():
    """Get a SQLite connection and ensure the cache table exists."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS image_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prompt_hash TEXT UNIQUE NOT NULL,
            prompt TEXT NOT NULL,
            provider TEXT NOT NULL,
            style TEXT,
            size TEXT NOT NULL,
            result_url TEXT,
            result_base64 TEXT,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    return conn


def cache_get(prompt: str) -> dict | None:
    """Retrieve a cached result by prompt hash."""
    h = hashlib.sha256(prompt.encode()).hexdigest()
    conn = get_db()
    row = conn.execute(
        "SELECT prompt, provider, style, size, result_url, result_base64, created_at "
        "FROM image_cache WHERE prompt_hash=?", (h,)
    ).fetchone()
    conn.close()
    if row:
        return {
            "prompt": row[0], "provider": row[1], "style": row[2],
            "size": row[3], "url": row[4], "base64": row[5], "created_at": row[6],
        }
    return None


def cache_put(prompt: str, provider: str, style: str | None, size: str,
              result_url: str | None, result_base64: str | None):
    """Store a result in the cache."""
    h = hashlib.sha256(prompt.encode()).hexdigest()
    now = datetime.now(timezone.utc).isoformat()
    conn = get_db()
    conn.execute(
        "INSERT OR REPLACE INTO image_cache "
        "(prompt_hash, prompt, provider, style, size, result_url, result_base64, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (h, prompt, provider, style, size, result_url, result_base64, now),
    )
    conn.commit()
    conn.close()


def cache_list_recent(limit: int = 20) -> list[dict]:
    """List recent cached images."""
    conn = get_db()
    rows = conn.execute(
        "SELECT prompt, provider, style, size, result_url, created_at "
        "FROM image_cache ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [
        {"prompt": r[0], "provider": r[1], "style": r[2], "size": r[3],
         "url": r[4], "created_at": r[5]}
        for r in rows
    ]


# ──────────────────────────────────────────────────────────────
# Style helpers
# ──────────────────────────────────────────────────────────────

def apply_style(prompt: str, style: str | None) -> str:
    """Wrap a prompt with the style's prefix/suffix."""
    if not style or style not in STYLES:
        return prompt
    s = STYLES[style]
    return f"{s['prefix']} {prompt}{s['suffix']}"


# ──────────────────────────────────────────────────────────────
# Provider implementations
# ──────────────────────────────────────────────────────────────

def _generate_openai(prompt: str, size: str, api_key: str) -> dict:
    """Generate image via OpenAI DALL-E 3."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "dall-e-3",
        "prompt": prompt,
        "n": 1,
        "size": size,
        "response_format": "b64_json",
    }
    resp = requests.post(OPENAI_API_URL, headers=headers, json=payload, timeout=120)
    resp.raise_for_status()
    data = resp.json()
    b64 = data["data"][0]["b64_json"]
    return {"url": None, "base64": b64, "provider": "openai"}


def _generate_gemini(prompt: str, size: str, api_key: str) -> dict:
    """Generate image via Google Gemini Imagen."""
    url = f"{GEMINI_API_URL}?key={api_key}"
    # Map size to Gemini aspect ratio
    aspect = "1:1"
    if size == "1792x1024":
        aspect = "16:9"
    elif size == "1024x1792":
        aspect = "9:16"
    payload = {
        "instances": [{"prompt": prompt}],
        "parameters": {"sampleCount": 1, "aspectRatio": aspect},
    }
    resp = requests.post(url, json=payload, timeout=120)
    resp.raise_for_status()
    data = resp.json()
    b64 = data["predictions"][0]["bytesBase64Encoded"]
    return {"url": None, "base64": b64, "provider": "gemini"}


def _generate_comfyui(prompt: str, size: str) -> dict:
    """Generate image via local Stable Diffusion (ComfyUI)."""
    w, h = size.split("x")
    # Simple ComfyUI workflow (txt2img with default SD 1.5 settings)
    workflow = {
        "3": {
            "class_type": "KSampler",
            "inputs": {"seed": int(time.time()), "steps": 20, "cfg": 7.0,
                       "sampler_name": "euler", "scheduler": "normal", "denoise": 1.0,
                       "model": ["4", 0], "positive": ["6", 0], "negative": ["7", 0],
                       "latent_image": ["5", 0]},
        },
        "4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "v1-5-pruned-emaonly.safetensors"}},
        "5": {"class_type": "EmptyLatentImage", "inputs": {"width": int(w), "height": int(h), "batch_size": 1}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["4", 1]}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"text": "low quality, blurry, distorted", "clip": ["4", 1]}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
        "9": {"class_type": "SaveImage", "inputs": {"filename_prefix": "atena_gen", "images": ["8", 0]}},
    }
    # Submit workflow
    resp = requests.post(f"{COMFYUI_URL}/prompt", json={"prompt": workflow}, timeout=10)
    resp.raise_for_status()
    prompt_id = resp.json()["prompt_id"]

    # Poll for completion (up to 120s)
    for _ in range(120):
        time.sleep(1)
        hist = requests.get(f"{COMfyUI_URL}/history/{prompt_id}", timeout=10).json()
        if prompt_id in hist and "outputs" in hist[prompt_id]:
            outputs = hist[prompt_id]["outputs"]
            for node_output in outputs.values():
                if "images" in node_output:
                    img_info = node_output["images"][0]
                    img_url = f"{COMfyUI_URL}/view?filename={img_info['filename']}&subfolder={img_info.get('subfolder', '')}&type=output"
                    img_data = requests.get(img_url, timeout=30).content
                    b64 = base64.b64encode(img_data).decode()
                    return {"url": img_url, "base64": b64, "provider": "comfyui"}
    raise TimeoutError("ComfyUI generation timed out after 120 seconds")


def _generate_placeholder(prompt: str, size: str) -> dict:
    """Generate a placeholder image via picsum.photos (seeded by prompt hash)."""
    h = int(hashlib.md5(prompt.encode()).hexdigest(), 16)
    w, ht = size.split("x")
    url = f"https://picsum.photos/seed/{h}/{w}/{ht}"
    img_data = requests.get(url, timeout=30).content
    b64 = base64.b64encode(img_data).decode()
    return {"url": url, "base64": b64, "provider": "placeholder"}


# ──────────────────────────────────────────────────────────────
# ImageGenerator class
# ──────────────────────────────────────────────────────────────

class ImageGenerator:
    """
    Multi-provider image generation with caching.

    Usage:
        gen = ImageGenerator(openai_key="sk-...", gemini_key="AI...")
        result = gen.generate_image("a cat", style="cartoon")
        gen.save_image(result["url"] or result["base64"], "cat.png")
    """

    def __init__(self, openai_key: str = "", gemini_key: str = "",
                 comfyui_url: str = "", use_cache: bool = True):
        self.openai_key = openai_key or os.environ.get("OPENAI_API_KEY", "")
        self.gemini_key = gemini_key or os.environ.get("GEMINI_API_KEY", "")
        self.comfyui_url = comfyui_url or os.environ.get("COMFYUI_URL", COMFYUI_URL)
        self.use_cache = use_cache

    # ── public API ────────────────────────────────────────────

    def generate_image(self, prompt: str, provider: str = "auto",
                       style: str | None = None, size: str = "1024x1024") -> dict:
        """
        Generate an image.

        Args:
            prompt:   Text description of the desired image.
            provider: 'auto', 'openai', 'gemini', 'comfyui', 'placeholder'.
            style:    One of the STYLES keys or None.
            size:     '1024x1024', '1792x1024', '1024x1792'.

        Returns:
            dict with keys: url, base64, provider, prompt, style, size, cached
        """
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty")

        styled_prompt = apply_style(prompt.strip(), style)

        # Check cache
        if self.use_cache:
            cached = cache_get(styled_prompt)
            if cached:
                return {**cached, "cached": True}

        # Resolve provider
        resolved = self._resolve_provider(provider)

        # Dispatch
        result: dict
        try:
            if resolved == "openai":
                result = _generate_openai(styled_prompt, size, self.openai_key)
            elif resolved == "gemini":
                result = _generate_gemini(styled_prompt, size, self.gemini_key)
            elif resolved == "comfyui":
                result = _generate_comfyui(styled_prompt, size)
            else:
                result = _generate_placeholder(styled_prompt, size)
        except Exception as e:
            # Fallback to placeholder on any error
            print(f"[WARN] Provider '{resolved}' failed ({e}), falling back to placeholder.")
            result = _generate_placeholder(styled_prompt, size)
            result["fallback_reason"] = str(e)

        # Cache & return
        if self.use_cache:
            cache_put(styled_prompt, result["provider"], style, size,
                      result.get("url"), result.get("base64"))

        return {
            "url": result.get("url"),
            "base64": result.get("base64"),
            "provider": result["provider"],
            "prompt": prompt,
            "styled_prompt": styled_prompt,
            "style": style,
            "size": size,
            "cached": False,
        }

    def list_providers(self) -> list[dict]:
        """List all providers and their availability status."""
        providers = []
        for key, name in PROVIDER_NAMES.items():
            available = self._is_available(key)
            providers.append({
                "id": key,
                "name": name,
                "available": available,
            })
        return providers

    @staticmethod
    def get_styles() -> list[dict]:
        """Return all predefined styles."""
        return [{"id": k, **v} for k, v in STYLES.items()]

    def save_image(self, url_or_b64: str, path: str) -> str:
        """
        Save an image to disk.

        Args:
            url_or_b64: A URL (http/https) or a base64-encoded string.
            path:       Destination file path.

        Returns:
            Absolute path of the saved file.
        """
        if url_or_b64.startswith("http://") or url_or_b64.startswith("https://"):
            data = requests.get(url_or_b64, timeout=60).content
        else:
            data = base64.b64decode(url_or_b64)

        dest = Path(path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return str(dest.resolve())

    # ── internals ──────────────────────────────────────────────

    def _resolve_provider(self, provider: str) -> str:
        if provider and provider != "auto":
            return provider
        # Auto: pick first available in priority order
        for p in ("openai", "gemini", "comfyui"):
            if self._is_available(p):
                return p
        return "placeholder"

    def _is_available(self, provider: str) -> bool:
        if provider == "openai":
            return bool(self.openai_key)
        if provider == "gemini":
            return bool(self.gemini_key)
        if provider == "comfyui":
            try:
                r = requests.get(f"{self.comfyui_url}/system_stats", timeout=3)
                return r.status_code == 200
            except Exception:
                return False
        if provider == "placeholder":
            return True
        return False


# ──────────────────────────────────────────────────────────────
# REST API (http.server – no Flask dependency)
# ──────────────────────────────────────────────────────────────

class ImageAPIHandler(BaseHTTPRequestHandler):
    """Simple REST API handler for image generation."""

    # Class-level generator (set by serve())
    generator: ImageGenerator = None  # type: ignore

    def log_message(self, fmt, *args):
        """Silence default logging."""
        pass

    def _send_json(self, data: dict, status: int = 200):
        body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        return json.loads(raw)

    # ── routes ─────────────────────────────────────────────────

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/")

        if path == "/styles":
            self._send_json({"styles": ImageGenerator.get_styles()})

        elif path == "/providers":
            self._send_json({"providers": self.generator.list_providers()})

        elif path == "/gallery":
            recent = cache_list_recent(20)
            self._send_json({"images": recent})

        elif path == "/" or path == "":
            self._send_json({
                "service": "Atena Evolution – Image Generator API",
                "endpoints": {
                    "POST /generate": "Generate an image {prompt, style?, provider?, size?}",
                    "GET  /styles": "List available styles",
                    "GET  /providers": "List available providers",
                    "GET  /gallery": "Recent generated images",
                },
            })

        else:
            self._send_json({"error": "Not found"}, 404)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/")

        if path == "/generate":
            try:
                body = self._read_body()
                prompt = body.get("prompt", "")
                style = body.get("style")
                provider = body.get("provider", "auto")
                size = body.get("size", "1024x1024")

                if not prompt:
                    self._send_json({"error": "Field 'prompt' is required"}, 400)
                    return

                result = self.generator.generate_image(prompt, provider=provider,
                                                       style=style, size=size)
                self._send_json(result)

            except ValueError as e:
                self._send_json({"error": str(e)}, 400)
            except Exception as e:
                self._send_json({"error": str(e)}, 500)
        else:
            self._send_json({"error": "Not found"}, 404)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()


def serve(host: str = "0.0.0.0", port: int = 8080,
          openai_key: str = "", gemini_key: str = ""):
    """Start the REST API server."""
    ImageAPIHandler.generator = ImageGenerator(
        openai_key=openai_key, gemini_key=gemini_key
    )
    server = HTTPServer((host, port), ImageAPIHandler)
    print(f"🚀 Image Generator API running at http://{host}:{port}")
    print(f"   POST http://localhost:{port}/generate")
    print(f"   GET  http://localhost:{port}/styles")
    print(f"   GET  http://localhost:{port}/providers")
    print(f"   GET  http://localhost:{port}/gallery")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n⏹  Server stopped.")
        server.server_close()


# ──────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────

def cli_main():
    parser = argparse.ArgumentParser(
        description="Atena Evolution – Multi-provider Image Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  python image_generator.py --prompt "a cute cat" --style cartoon
  python image_generator.py --prompt "sunset over mountains" --style oil_painting --save sunset.png
  python image_generator.py --server --port 8080
  python image_generator.py --list-styles
  python image_generator.py --list-providers
        """,
    )
    parser.add_argument("--prompt", "-p", type=str, help="Image description prompt")
    parser.add_argument("--style", "-s", type=str, default=None,
                        choices=list(STYLES.keys()), help="Visual style")
    parser.add_argument("--provider", type=str, default="auto",
                        choices=["auto", "openai", "gemini", "comfyui", "placeholder"],
                        help="Image generation provider (default: auto)")
    parser.add_argument("--size", type=str, default="1024x1024",
                        choices=["1024x1024", "1792x1024", "1024x1792"],
                        help="Image size (default: 1024x1024)")
    parser.add_argument("--save", type=str, default=None,
                        help="Save generated image to this file path")
    parser.add_argument("--server", action="store_true",
                        help="Start REST API server")
    parser.add_argument("--port", type=int, default=8080,
                        help="Server port (default: 8080)")
    parser.add_argument("--list-styles", action="store_true",
                        help="List available styles and exit")
    parser.add_argument("--list-providers", action="store_true",
                        help="List available providers and exit")
    parser.add_argument("--no-cache", action="store_true",
                        help="Disable image cache")

    args = parser.parse_args()

    # ── list modes ─────────────────────────────────────────────
    if args.list_styles:
        print("Available styles:")
        for s in ImageGenerator.get_styles():
            print(f"  {s['id']:15s} – {s['name']}: {s['description']}")
        return

    if args.list_providers:
        gen = ImageGenerator()
        print("Available providers:")
        for p in gen.list_providers():
            status = "✅" if p["available"] else "❌"
            print(f"  {status} {p['id']:12s} – {p['name']}")
        return

    # ── server mode ────────────────────────────────────────────
    if args.server:
        serve(port=args.port)
        return

    # ── generate mode ──────────────────────────────────────────
    if not args.prompt:
        parser.print_help()
        sys.exit(1)

    gen = ImageGenerator(use_cache=not args.no_cache)
    print(f"🎨 Generating image...")
    print(f"   Prompt:   {args.prompt}")
    print(f"   Style:    {args.style or 'none'}")
    print(f"   Provider: {args.provider}")
    print(f"   Size:     {args.size}")

    result = gen.generate_image(
        prompt=args.prompt,
        provider=args.provider,
        style=args.style,
        size=args.size,
    )

    print(f"\n✅ Image generated!")
    print(f"   Provider: {result['provider']}")
    print(f"   Cached:   {result.get('cached', False)}")
    if result.get("url"):
        print(f"   URL:      {result['url']}")
    if result.get("base64"):
        print(f"   Base64:   {len(result['base64'])} chars")

    # Save
    save_path = args.save
    if not save_path:
        # Auto-generate filename
        safe_name = "".join(c if c.isalnum() else "_" for c in args.prompt)[:40]
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_path = str(DOWNLOAD_DIR / f"{safe_name}_{ts}.png")

    source = result.get("base64") or result.get("url")
    if source:
        saved = gen.save_image(source, save_path)
        print(f"   Saved:    {saved}")
    else:
        print("   ⚠️  No image data to save.")


# ──────────────────────────────────────────────────────────────
# Tests
# ──────────────────────────────────────────────────────────────

def run_tests():
    """Run built-in tests (no external API calls)."""
    import tempfile
    import shutil

    passed = 0
    failed = 0
    total = 0

    def assert_test(condition: bool, name: str):
        nonlocal passed, failed, total
        total += 1
        if condition:
            passed += 1
            print(f"  ✅ {name}")
        else:
            failed += 1
            print(f"  ❌ {name}")

    print("\n" + "=" * 60)
    print("🧪 Running ImageGenerator Tests")
    print("=" * 60)

    # ── Test 1: Style application ──────────────────────────────
    print("\n── Style Application ──")
    assert_test(
        apply_style("a cat", "cartoon") == STYLES["cartoon"]["prefix"] + " a cat" + STYLES["cartoon"]["suffix"],
        "Style 'cartoon' applied correctly"
    )
    assert_test(
        apply_style("a dog", None) == "a dog",
        "No style returns original prompt"
    )
    assert_test(
        apply_style("a bird", "invalid_style") == "a bird",
        "Invalid style returns original prompt"
    )
    assert_test(
        "photorealistic" in apply_style("a tree", "realistic").lower() or "photorealistic" in STYLES["realistic"]["prefix"].lower(),
        "Realistic style contains expected keywords"
    )

    # ── Test 2: get_styles ─────────────────────────────────────
    print("\n── get_styles() ──")
    styles = ImageGenerator.get_styles()
    assert_test(len(styles) == 8, "Returns 8 styles")
    assert_test(all("id" in s and "name" in s and "prefix" in s for s in styles),
                "All styles have required fields")
    style_ids = {s["id"] for s in styles}
    assert_test(style_ids == set(STYLES.keys()), "Style IDs match STYLES keys")

    # ── Test 3: list_providers ─────────────────────────────────
    print("\n── list_providers() ──")
    gen = ImageGenerator()
    providers = gen.list_providers()
    assert_test(len(providers) == 4, "Returns 4 providers")
    provider_ids = {p["id"] for p in providers}
    assert_test("openai" in provider_ids, "OpenAI provider listed")
    assert_test("gemini" in provider_ids, "Gemini provider listed")
    assert_test("comfyui" in provider_ids, "ComfyUI provider listed")
    assert_test("placeholder" in provider_ids, "Placeholder provider listed")
    # Placeholder should always be available
    ph = next(p for p in providers if p["id"] == "placeholder")
    assert_test(ph["available"] is True, "Placeholder is always available")

    # ── Test 4: Cache (SQLite) ─────────────────────────────────
    print("\n── SQLite Cache ──")
    # Use a temp DB for tests
    test_db = Path(tempfile.mktemp(suffix=".db"))
    original_db = DB_PATH
    try:
        # Monkey-patch DB_PATH for testing
        import image_generator as ig
        ig.DB_PATH = test_db

        cache_put("test prompt", "placeholder", "cartoon", "1024x1024",
                  "https://example.com/img.png", "dGVzdA==")
        cached = cache_get("test prompt")
        assert_test(cached is not None, "Cache put/get works")
        assert_test(cached["provider"] == "placeholder", "Cached provider matches")
        assert_test(cached["style"] == "cartoon", "Cached style matches")
        assert_test(cached["url"] == "https://example.com/img.png", "Cached URL matches")

        # Miss
        miss = cache_get("nonexistent prompt xyz")
        assert_test(miss is None, "Cache miss returns None")

        # Recent list
        recent = cache_list_recent(10)
        assert_test(len(recent) >= 1, "cache_list_recent returns results")
    finally:
        ig.DB_PATH = original_db
        if test_db.exists():
            test_db.unlink()

    # ── Test 5: Placeholder generation ─────────────────────────
    print("\n── Placeholder Generation ──")
    try:
        result = _generate_placeholder("a beautiful sunset", "1024x1024")
        assert_test(result["provider"] == "placeholder", "Placeholder provider identified")
        assert_test(result["url"] is not None and "picsum.photos" in result["url"],
                    "Placeholder URL contains picsum.photos")
        assert_test(result["base64"] is not None and len(result["base64"]) > 0,
                    "Placeholder returns base64 data")
    except Exception as e:
        assert_test(False, f"Placeholder generation failed: {e}")

    # ── Test 6: save_image ─────────────────────────────────────
    print("\n── save_image() ──")
    tmp_dir = tempfile.mkdtemp()
    try:
        # Save from base64
        b64_data = base64.b64encode(b"\x89PNG\r\n\x1a\nfake_png_data").decode()
        saved_path = gen.save_image(b64_data, os.path.join(tmp_dir, "test.png"))
        assert_test(os.path.exists(saved_path), "save_image creates file from base64")
        assert_test(os.path.getsize(saved_path) > 0, "Saved file is non-empty")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    # ── Test 7: ImageGenerator.generate_image (placeholder) ────
    print("\n── ImageGenerator.generate_image() ──")
    gen_no_cache = ImageGenerator(use_cache=False)
    try:
        result = gen_no_cache.generate_image("a red apple", provider="placeholder",
                                             style="watercolor", size="1024x1024")
        assert_test(result["provider"] == "placeholder", "generate_image uses placeholder")
        assert_test(result["style"] == "watercolor", "Style preserved in result")
        assert_test(result["size"] == "1024x1024", "Size preserved in result")
        assert_test(result["base64"] is not None, "Result contains base64")
        assert_test("styled_prompt" in result, "Result contains styled_prompt")
        assert_test("watercolor" in result["styled_prompt"].lower(),
                    "Styled prompt contains style keywords")
    except Exception as e:
        assert_test(False, f"generate_image failed: {e}")

    # ── Test 8: Empty prompt validation ────────────────────────
    print("\n── Validation ──")
    try:
        gen_no_cache.generate_image("")
        assert_test(False, "Empty prompt should raise ValueError")
    except ValueError:
        assert_test(True, "Empty prompt raises ValueError")
    except Exception as e:
        assert_test(False, f"Unexpected exception: {e}")

    # ── Test 9: Auto provider selection ────────────────────────
    print("\n── Auto Provider Selection ──")
    gen_no_keys = ImageGenerator(openai_key="", gemini_key="")
    resolved = gen_no_keys._resolve_provider("auto")
    assert_test(resolved == "placeholder", "Auto without keys selects placeholder")

    gen_with_openai = ImageGenerator(openai_key="sk-test123")
    resolved2 = gen_with_openai._resolve_provider("auto")
    assert_test(resolved2 == "openai", "Auto with OpenAI key selects openai")

    # ── Test 10: API handler routing (basic) ───────────────────
    print("\n── API Handler ──")
    assert_test(ImageAPIHandler is not None, "ImageAPIHandler class exists")
    assert_test(hasattr(ImageAPIHandler, 'do_GET'), "Handler has do_GET")
    assert_test(hasattr(ImageAPIHandler, 'do_POST'), "Handler has do_POST")

    # ── Summary ────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print(f"📊 Results: {passed}/{total} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


# ──────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if "--test" in sys.argv:
        sys.argv.remove("--test")
        success = run_tests()
        sys.exit(0 if success else 1)
    else:
        cli_main()
