#!/usr/bin/env python3
"""
visao_engine.py — Engine de Visão Computacional Avançada

Melhorias sobre visao_computacional.py:
- Detecção inteligente de fim de conteúdo
- Scroll com detecção de novos elementos DOM
- Captura de páginas com lazy loading
- Extração estruturada (títulos, parágrafos, listas)
- Cache de screenshots para OCR incremental
"""

import urllib.request, json, time, re, os, sys, hashlib
from pathlib import Path
from typing import Optional, Dict, List


class VisaoEngine:
    """Engine de visão computacional via Kimi WebBridge."""
    
    def __init__(self, kimi_url="http://127.0.0.1:10086", session="koldi-visao"):
        self.kimi_url = kimi_url
        self.session = session
    
    def _req(self, action, args=None):
        payload = {"action": action, "session": self.session}
        if args: payload["args"] = args
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.kimi_url}/command", data=body,
            headers={"Content-Type": "application/json"}, method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:
            return {"error": str(e)}
    
    def nav(self, url):
        return self._req("navigate", {"url": url, "newTab": True})
    
    def js(self, code):
        return self._req("evaluate", {"code": code})
    
    def snap(self, full=False):
        args = {"full": True} if full else {}
        return self._req("snapshot", args)
    
    def shot(self, fmt="png"):
        return self._req("screenshot", {"format": fmt})
    
    def scroll(self, y):
        return self.js(f"window.scrollTo(0, {y}); 'ok'")
    
    def page_info(self):
        r = self.js("JSON.stringify({y:window.scrollY,h:window.innerHeight,b:document.body.scrollHeight,u:location.href,t:document.title})")
        v = r.get("data", {}).get("value", "{}")
        try: return json.loads(v)
        except: return {}
    
    # ═══════════════════════════════════════════════════════════════════
    # ROTA A: Scroll + Snapshot com detecção inteligente
    # ═══════════════════════════════════════════════════════════════════
    
    def rota_a(self, max_scrolls=50, delay=1.2, stale_limit=3):
        """
        Scroll incremental com snapshot.
        Para quando não há novos elementos por `stale_limit` scrolls.
        """
        print("[Rota A] Iniciando...")
        info = self.page_info()
        body_h = info.get("b", 0)
        inner_h = info.get("h", 0)
        step = int(inner_h * 0.75)
        
        all_texts = set()
        snapshots = []
        stale = 0
        y = 0
        
        for i in range(max_scrolls):
            self.scroll(y)
            time.sleep(delay)
            
            r = self.snap(full=True)
            tree = r.get("data", {}).get("tree", [])
            texts = self._extract_texts(tree)
            new = texts - all_texts
            all_texts.update(texts)
            
            snapshots.append({"y": y, "new": len(new), "total": len(all_texts)})
            print(f"  Scroll {i+1}: y={y}, novos={len(new)}, total={len(all_texts)}")
            
            if len(new) == 0:
                stale += 1
                if stale >= stale_limit:
                    print(f"  Sem novos textos por {stale_limit} scrolls. Fim.")
                    break
            else:
                stale = 0
            
            y += step
            if y > body_h:
                break
        
        self.scroll(0)
        return {"texts": list(all_texts), "snapshots": snapshots, "info": info}
    
    # ═══════════════════════════════════════════════════════════════════
    # ROTA B: Screenshot + OCR
    # ═══════════════════════════════════════════════════════════════════
    
    def rota_b(self, max_scrolls=50, delay=1.5):
        """
        Screenshots incrementais com OCR.
        """
        print("[Rota B] Iniciando...")
        info = self.page_info()
        body_h = info.get("b", 0)
        inner_h = info.get("h", 0)
        step = int(inner_h * 0.8)
        
        screenshot_dir = Path.home() / ".hermes" / "visao_shots"
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        
        shots = []
        y = 0
        
        for i in range(max_scrolls):
            self.scroll(y)
            time.sleep(delay)
            
            r = self.shot()
            data = r.get("data", {})
            
            if data.get("success"):
                img_data = data.get("data", "")
                if isinstance(img_data, str) and len(img_data) > 100:
                    import base64
                    try:
                        img_bytes = base64.b64decode(img_data)
                        path = screenshot_dir / f"shot_{i:04d}.png"
                        with open(path, "wb") as f:
                            f.write(img_bytes)
                        shots.append(str(path))
                        print(f"  Screenshot {i+1}: {path.name} ({len(img_bytes)} bytes)")
                    except Exception as e:
                        print(f"  Erro screenshot: {e}")
            
            y += step
            if y > body_h:
                break
        
        self.scroll(0)
        
        # OCR
        ocr_texts = self._ocr(shots)
        
        return {"texts": ocr_texts, "screenshots": shots, "info": info}
    
    def _ocr(self, paths):
        """OCR nos screenshots."""
        texts = []
        try:
            import easyocr
            reader = easyocr.Reader(["pt", "en"], gpu=False)
            for p in paths:
                try:
                    results = reader.readtext(p)
                    for (_, text, conf) in results:
                        if conf > 0.3 and len(text.strip()) > 2:
                            texts.append(text.strip())
                except Exception as e:
                    print(f"  OCR erro: {e}")
        except ImportError:
            print("  EasyOCR não instalado.")
        return texts
    
    # ═══════════════════════════════════════════════════════════════════
    # ROTA C: DOM Extraction (mais rápido e completo)
    # ═══════════════════════════════════════════════════════════════════
    
    def rota_c(self, max_scrolls=100, delay=1.0, stale_limit=3):
        """
        Extração de texto via DOM com scroll inteligente.
        Usa TreeWalker para percorrer todos os nós de texto.
        """
        print("[Rota C] Iniciando...")
        info = self.page_info()
        body_h = info.get("b", 0)
        inner_h = info.get("h", 0)
        step = int(inner_h * 0.7)
        
        seen_hashes = set()
        all_blocks = []
        stale = 0
        y = 0
        
        for i in range(max_scrolls):
            self.scroll(y)
            time.sleep(delay)
            
            # Extrair texto via DOM
            js = """
            (function() {
                var blocks = [];
                var walker = document.createTreeWalker(
                    document.body, NodeFilter.SHOW_TEXT, null, false
                );
                var node;
                while (node = walker.nextNode()) {
                    var t = node.textContent.trim();
                    if (t.length > 3) {
                        var el = node.parentElement;
                        var tag = el ? el.tagName : '';
                        var rect = el ? el.getBoundingClientRect() : null;
                        var visible = rect ? (rect.top >= -200 && rect.bottom <= window.innerHeight + 200) : true;
                        blocks.push({t: t, tag: tag, vis: visible});
                    }
                }
                return JSON.stringify(blocks);
            })()
            """
            r = self.js(js)
            val = r.get("data", {}).get("value", "[]")
            
            try:
                blocks = json.loads(val)
                new_count = 0
                for b in blocks:
                    text = b.get("t", "")
                    h = hashlib.md5(text.encode()).hexdigest()[:12]
                    if h not in seen_hashes:
                        seen_hashes.add(h)
                        all_blocks.append(b)
                        new_count += 1
                
                print(f"  Scroll {i+1}: y={y}, novos={new_count}, total={len(all_blocks)}")
                
                if new_count == 0:
                    stale += 1
                    if stale >= stale_limit:
                        print(f"  Sem novos textos por {stale_limit} scrolls. Fim.")
                        break
                else:
                    stale = 0
            except Exception as e:
                print(f"  Erro: {e}")
            
            y += step
            if y > body_h:
                break
        
        self.scroll(0)
        
        # Montar texto completo
        full_text = "\n".join(b["t"] for b in all_blocks)
        
        return {
            "full_text": full_text,
            "blocks": all_blocks,
            "info": info,
            "total_blocks": len(all_blocks),
        }
    
    # ═══════════════════════════════════════════════════════════════════
    # Captura Combinada
    # ═══════════════════════════════════════════════════════════════════
    
    def captura_completa(self, url=None, metodos=None):
        """
        Captura completa usando múltiplos métodos.
        
        metodos: lista de "a", "b", "c" ou None para todos
        """
        if metodos is None:
            metodos = ["c", "a"]  # C é mais rápido, A é backup
        
        if url:
            self.nav(url)
            time.sleep(5)
        
        info = self.page_info()
        print(f"\n{'='*60}")
        print(f"CAPTURA COMPLETA")
        print(f"URL: {info.get('u', '?')}")
        print(f"Title: {info.get('t', '?')}")
        print(f"Body: {info.get('b', 0)}px")
        print(f"Métodos: {metodos}")
        print(f"{'='*60}\n")
        
        results = {"info": info}
        
        for metodo in metodos:
            if metodo == "a":
                results["a"] = self.rota_a()
            elif metodo == "b":
                results["b"] = self.rota_b()
            elif metodo == "c":
                results["c"] = self.rota_c()
        
        # Combinar textos
        combined = set()
        for key in ("a", "b", "c"):
            if key in results:
                if "texts" in results[key]:
                    combined.update(results[key]["texts"])
                if "full_text" in results[key]:
                    for line in results[key]["full_text"].split("\n"):
                        if len(line.strip()) > 3:
                            combined.add(line.strip())
        
        results["combined"] = list(combined)
        results["combined_count"] = len(combined)
        
        print(f"\n{'='*60}")
        print(f"RESULTADO: {len(combined)} textos únicos combinados")
        print(f"{'='*60}")
        
        return results
    
    # ── Utilidades ─────────────────────────────────────────────────────
    
    def _extract_texts(self, tree):
        texts = set()
        def walk(obj):
            if isinstance(obj, dict):
                name = obj.get("name", "")
                if isinstance(name, str) and len(name) > 3:
                    texts.add(name)
                for v in obj.values():
                    walk(v)
            elif isinstance(obj, list):
                for item in obj:
                    walk(item)
        walk(tree)
        return texts


# ── CLI ──────────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("cmd", choices=["test", "capture", "dom", "ocr", "snapshot"])
    parser.add_argument("--url", "-u", default="https://pt.wikipedia.org/wiki/Inteligência_artificial")
    parser.add_argument("--output", "-o")
    args = parser.parse_args()
    
    v = VisaoEngine()
    
    if args.cmd == "test":
        print("=== TESTE COMPLETO ===\n")
        v.nav(args.url)
        time.sleep(5)
        
        # Rota C
        r = v.rota_c(max_scrolls=20, delay=0.8)
        print(f"\nRota C: {r['total_blocks']} blocos, {len(r['full_text'])} chars")
        
        # Salvar
        out = args.output or str(Path.home() / ".hermes" / "visao_test.txt")
        with open(out, "w", encoding="utf-8") as f:
            f.write(r["full_text"])
        print(f"Salvo em: {out}")
        
        # Preview
        print(f"\n--- Preview (primeiros 800 chars) ---")
        print(r["full_text"][:800])
    
    elif args.cmd == "capture":
        r = v.captura_completa(url=args.url)
        out = args.output or str(Path.home() / ".hermes" / "visao_capture.txt")
        with open(out, "w", encoding="utf-8") as f:
            f.write("\n".join(r["combined"]))
        print(f"Salvo em: {out}")
    
    elif args.cmd == "dom":
        v.nav(args.url)
        time.sleep(5)
        r = v.rota_c()
        out = args.output or str(Path.home() / ".hermes" / "visao_dom.txt")
        with open(out, "w", encoding="utf-8") as f:
            f.write(r["full_text"])
        print(f"Salvo: {out} ({len(r['full_text'])} chars)")
    
    elif args.cmd == "ocr":
        v.nav(args.url)
        time.sleep(5)
        r = v.rota_b(max_scrolls=5)
        print(f"OCR: {len(r['texts'])} textos em {len(r['screenshots'])} screenshots")
    
    elif args.cmd == "snapshot":
        v.nav(args.url)
        time.sleep(5)
        r = v.snap(full=True)
        tree = r.get("data", {}).get("tree", [])
        texts = v._extract_texts(tree)
        print(f"Snapshot: {len(texts)} textos únicos")
        for t in list(texts)[:20]:
            print(f"  - {t[:100]}")


if __name__ == "__main__":
    main()
