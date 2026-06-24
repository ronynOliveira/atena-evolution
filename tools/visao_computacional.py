#!/usr/bin/env python3
"""
visao_computacional.py — Sistema de Visão Computacional para o Koldi

Capacidades:
- Scroll incremental com captura de snapshots
- Screenshot com OCR para texto completo
- Captura de toda a página (mesmo com lazy loading)
- Extração de texto da árvore de acessibilidade
- Combinação de múltiplas fontes para informação completa

Rotas:
A) Scroll + Snapshot incremental (Kimi WebBridge)
B) Screenshot + OCR (EasyOCR local)
C) Avaliação JS para extração de texto DOM
"""

import urllib.request, json, time, re, os, sys
from pathlib import Path
from typing import Optional


class KimiVision:
    """Sistema de visão via Kimi WebBridge."""
    
    def __init__(self, kimi_url="http://127.0.0.1:10086", session="koldi-vision"):
        self.kimi_url = kimi_url
        self.session = session
    
    def _request(self, action, args=None):
        payload = {"action": action, "session": self.session}
        if args:
            payload["args"] = args
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.kimi_url}/command",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:
            return {"error": str(e), "success": False}
    
    def navigate(self, url):
        """Navega para uma URL."""
        return self._request("navigate", {"url": url, "newTab": True})
    
    def evaluate(self, code):
        """Executa JavaScript na página."""
        return self._request("evaluate", {"code": code})
    
    def snapshot(self, full=False):
        """Captura a árvore de acessibilidade."""
        args = {"full": True} if full else {}
        return self._request("snapshot", args)
    
    def screenshot(self, format="png"):
        """Tira screenshot da página."""
        return self._request("screenshot", {"format": format})
    
    def scroll_to(self, y):
        """Scrolla para uma posição Y específica."""
        return self.evaluate(f"window.scrollTo(0, {y}); return 'scrolled'")
    
    def scroll_by(self, delta_y):
        """Scrolla por um delta Y."""
        return self.evaluate(f"window.scrollBy(0, {delta_y}); return 'scrolled'")
    
    def get_page_info(self):
        """Retorna informações sobre a página atual."""
        js = "JSON.stringify({scrollY: window.scrollY, innerHeight: window.innerHeight, bodyHeight: document.body.scrollHeight, url: location.href, title: document.title})"
        r = self.evaluate(js)
        val = r.get("data", {}).get("value", "{}")
        try:
            return json.loads(val)
        except:
            return {}
    
    # ── ROTA A: Scroll + Snapshot Incremental ──────────────────────────
    
    def capture_full_page(self, scroll_ratio=0.7, delay=1.5, max_scrolls=100):
        """
        ROTA A: Captura a página inteira fazendo scroll incremental.
        
        A cada scroll:
        1. Scrolla por scroll_ratio * innerHeight
        2. Aguarda delay para lazy loading
        3. Captura snapshot
        4. Extrai textos novos
        5. Repete até chegar ao fim ou max_scrolls
        
        Retorna dict com:
        - all_texts: lista de todos os textos únicos encontrados
        - snapshots: lista de snapshots crus
        - page_info: informações da página
        - total_scrolls: número de scrolls executados
        """
        print("[Rota A] Iniciando captura full page...")
        
        info = self.get_page_info()
        body_height = info.get("bodyHeight", 0)
        inner_height = info.get("innerHeight", 0)
        
        if body_height == 0:
            print("[Rota A] ERRO: bodyHeight = 0")
            return {"error": "bodyHeight zero", "all_texts": [], "snapshots": []}
        
        scroll_step = int(inner_height * scroll_ratio)
        total_scrolls_needed = max(1, body_height // scroll_step)
        
        print(f"[Rota A] Body: {body_height}px, Step: {scroll_step}px, Scrolls necessários: {total_scrolls_needed}")
        
        all_texts = set()
        snapshots = []
        current_scroll = 0
        scroll_count = 0
        last_text_count = 0
        
        while current_scroll < body_height and scroll_count < max_scrolls:
            # Scroll
            self.scroll_to(current_scroll)
            time.sleep(delay)
            
            # Snapshot
            r = self.snapshot(full=True)
            tree = r.get("data", {}).get("tree", [])
            
            # Extrair textos
            texts = self._extract_texts_from_tree(tree)
            new_texts = set(texts) - all_texts
            all_texts.update(texts)
            
            snapshots.append({
                "scroll_y": current_scroll,
                "total_elements": self._count_elements(tree),
                "new_texts": len(new_texts),
                "total_texts": len(all_texts),
            })
            
            print(f"[Rota A] Scroll {scroll_count+1}: y={current_scroll}, elementos={self._count_elements(tree)}, novos={len(new_texts)}, total={len(all_texts)}")
            
            # Se não há novos textos há 3 scrolls seguidos, parar
            if len(new_texts) == 0:
                last_text_count += 1
                if last_text_count >= 3:
                    print("[Rota A] Sem novos textos por 3 scrolls. Parando.")
                    break
            else:
                last_text_count = 0
            
            current_scroll += scroll_step
            scroll_count += 1
        
        # Scroll de volta para o topo
        self.scroll_to(0)
        
        result = {
            "all_texts": list(all_texts),
            "snapshots": snapshots,
            "page_info": info,
            "total_scrolls": scroll_count,
            "total_texts": len(all_texts),
        }
        
        print(f"[Rota A] Completo! {len(all_texts)} textos únicos em {scroll_count} scrolls")
        return result
    
    # ── ROTA B: Screenshot + OCR ───────────────────────────────────────
    
    def capture_with_ocr(self, scroll_ratio=0.7, delay=1.5, max_scrolls=100):
        """
        ROTA B: Captura screenshots e usa OCR para extrair texto.
        
        Usa EasyOCR para reconhecer texto nas imagens.
        Melhor para páginas com texto em imagens ou canvas.
        
        Retorna dict com:
        - all_texts: textos extraídos via OCR
        - screenshots: lista de caminhos dos screenshots
        - page_info: informações da página
        """
        print("[Rota B] Iniciando captura com OCR...")
        
        info = self.get_page_info()
        body_height = info.get("bodyHeight", 0)
        inner_height = info.get("innerHeight", 0)
        
        if body_height == 0:
            return {"error": "bodyHeight zero"}
        
        scroll_step = int(inner_height * scroll_ratio)
        
        screenshot_dir = Path.home() / ".hermes" / "vision_screenshots"
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        
        all_texts = []
        screenshots = []
        current_scroll = 0
        scroll_count = 0
        
        while current_scroll < body_height and scroll_count < max_scrolls:
            # Scroll
            self.scroll_to(current_scroll)
            time.sleep(delay)
            
            # Screenshot
            r = self.screenshot(format="png")
            data = r.get("data", {})
            
            if data.get("success") and data.get("dataLength", 0) > 0:
                # Salvar screenshot
                screenshot_path = screenshot_dir / f"screenshot_{scroll_count:04d}.png"
                
                # Decodificar base64 se necessário
                img_data = data.get("data", "")
                if isinstance(img_data, str) and len(img_data) > 100:
                    import base64
                    try:
                        img_bytes = base64.b64decode(img_data)
                        with open(screenshot_path, "wb") as f:
                            f.write(img_bytes)
                        screenshots.append(str(screenshot_path))
                        print(f"[Rota B] Screenshot {scroll_count+1} salvo: {screenshot_path}")
                    except Exception as e:
                        print(f"[Rota B] Erro ao salvar screenshot: {e}")
            
            current_scroll += scroll_step
            scroll_count += 1
        
        # Scroll para o topo
        self.scroll_to(0)
        
        # OCR nos screenshots
        ocr_texts = []
        if screenshots:
            ocr_texts = self._ocr_screenshots(screenshots)
        
        result = {
            "all_texts": ocr_texts,
            "screenshots": screenshots,
            "page_info": info,
            "total_scrolls": scroll_count,
        }
        
        print(f"[Rota B] Completo! {len(screenshots)} screenshots, {len(ocr_texts)} textos via OCR")
        return result
    
    def _ocr_screenshots(self, screenshot_paths):
        """Executa OCR nos screenshots usando EasyOCR."""
        texts = []
        try:
            import easyocr
            reader = easyocr.Reader(["pt", "en"], gpu=False)
            
            for path in screenshot_paths:
                try:
                    results = reader.readtext(path)
                    for (bbox, text, conf) in results:
                        if conf > 0.3 and len(text.strip()) > 2:
                            texts.append(text.strip())
                except Exception as e:
                    print(f"  OCR erro em {path}: {e}")
        except ImportError:
            print("  EasyOCR não instalado. Pulando OCR.")
        
        return texts
    
    # ── ROTA C: Extração DOM via JavaScript ────────────────────────────
    
    def capture_via_dom(self, scroll_ratio=0.7, delay=1.5, max_scrolls=100):
        """
        ROTA C: Usa JavaScript para extrair todo o texto do DOM.
        
        Mais rápido que OCR e mais completo que snapshot.
        Percorre todos os elementos de texto no DOM.
        
        Retorna dict com:
        - full_text: texto completo da página
        - structured: texto estruturado por elemento
        - page_info: informações da página
        """
        print("[Rota C] Iniciando captura via DOM...")
        
        info = self.get_page_info()
        body_height = info.get("bodyHeight", 0)
        inner_height = info.get("innerHeight", 0)
        
        if body_height == 0:
            return {"error": "bodyHeight zero"}
        
        scroll_step = int(inner_height * scroll_ratio)
        
        all_text_blocks = []
        seen_texts = set()
        current_scroll = 0
        scroll_count = 0
        
        while current_scroll < body_height and scroll_count < max_scrolls:
            # Scroll
            self.scroll_to(current_scroll)
            time.sleep(delay)
            
            # Extrair texto via JS
            js = """
            (function() {
                var texts = [];
                var walker = document.createTreeWalker(
                    document.body,
                    NodeFilter.SHOW_TEXT,
                    null,
                    false
                );
                var node;
                while (node = walker.nextNode()) {
                    var t = node.textContent.trim();
                    if (t.length > 3) {
                        var rect = node.parentElement ? node.parentElement.getBoundingClientRect() : null;
                        texts.push({
                            text: t,
                            tag: node.parentElement ? node.parentElement.tagName : '',
                            visible: rect ? (rect.top >= -100 && rect.top <= window.innerHeight + 100) : true
                        });
                    }
                }
                return JSON.stringify(texts);
            })()
            """
            r = self.evaluate(js)
            val = r.get("data", {}).get("value", "[]")
            
            try:
                blocks = json.loads(val)
                new_count = 0
                for block in blocks:
                    text = block.get("text", "")
                    if text not in seen_texts and len(text) > 3:
                        seen_texts.add(text)
                        all_text_blocks.append(block)
                        new_count += 1
                
                print(f"[Rota C] Scroll {scroll_count+1}: y={current_scroll}, novos={new_count}, total={len(all_text_blocks)}")
            except Exception as e:
                print(f"[Rota C] Erro ao parsear: {e}")
            
            current_scroll += scroll_step
            scroll_count += 1
        
        # Scroll para o topo
        self.scroll_to(0)
        
        # Montar texto completo
        full_text = "\n".join(b["text"] for b in all_text_blocks)
        
        result = {
            "full_text": full_text,
            "structured": all_text_blocks,
            "page_info": info,
            "total_scrolls": scroll_count,
            "total_texts": len(all_text_blocks),
        }
        
        print(f"[Rota C] Completo! {len(all_text_blocks)} blocos de texto")
        return result
    
    # ── Utilidades ─────────────────────────────────────────────────────
    
    def _extract_texts_from_tree(self, tree):
        """Extrai todos os textos da árvore de acessibilidade."""
        texts = []
        
        def walk(obj):
            if isinstance(obj, dict):
                name = obj.get("name", "")
                if isinstance(name, str) and len(name) > 3:
                    texts.append(name)
                for v in obj.values():
                    walk(v)
            elif isinstance(obj, list):
                for item in obj:
                    walk(item)
        
        walk(tree)
        return texts
    
    def _count_elements(self, tree):
        """Conta elementos na árvore."""
        count = 0
        
        def walk(obj):
            nonlocal count
            if isinstance(obj, dict):
                count += 1
                for v in obj.values():
                    walk(v)
            elif isinstance(obj, list):
                for item in obj:
                    walk(item)
        
        walk(tree)
        return count
    
    # ── Captura Combinada (A + B + C) ──────────────────────────────────
    
    def capture_complete(self, url=None, method="all"):
        """
        Captura completa da página usando múltiplos métodos.
        
        method: "a" (snapshot), "b" (ocr), "c" (dom), "all" (todos)
        
        Retorna dict com todos os resultados combinados.
        """
        if url:
            self.navigate(url)
            time.sleep(5)
        
        info = self.get_page_info()
        print(f"\n=== CAPTURA COMPLETA ===")
        print(f"URL: {info.get('url', '?')}")
        print(f"Title: {info.get('title', '?')}")
        print(f"Body height: {info.get('bodyHeight', 0)}px")
        print(f"Method: {method}\n")
        
        results = {"page_info": info}
        
        if method in ("a", "all"):
            print("--- ROTA A: Scroll + Snapshot ---")
            results["rota_a"] = self.capture_full_page()
        
        if method in ("c", "all"):
            print("\n--- ROTA C: Extração DOM ---")
            results["rota_c"] = self.capture_via_dom()
        
        if method in ("b", "all"):
            print("\n--- ROTA B: Screenshot + OCR ---")
            results["rota_b"] = self.capture_with_ocr()
        
        # Combinar todos os textos
        all_texts = set()
        for key in ("rota_a", "rota_b", "rota_c"):
            if key in results and results[key]:
                if "all_texts" in results[key]:
                    all_texts.update(results[key]["all_texts"])
                if "full_text" in results[key]:
                    all_texts.add(results[key]["full_text"])
        
        results["combined_texts"] = list(all_texts)
        results["combined_count"] = len(all_texts)
        
        print(f"\n=== RESULTADO FINAL ===")
        print(f"Textos únicos combinados: {len(all_texts)}")
        
        return results


# ── CLI ──────────────────────────────────────────────────────────────────

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Visão Computacional do Koldi")
    parser.add_argument("command", choices=["capture", "test", "ocr", "dom"], help="Comando")
    parser.add_argument("--url", "-u", help="URL para capturar")
    parser.add_argument("--method", "-m", default="all", choices=["a", "b", "c", "all"], help="Método de captura")
    parser.add_argument("--output", "-o", help="Arquivo de saída")
    
    args = parser.parse_args()
    
    vision = KimiVision()
    
    if args.command == "test":
        print("=== TESTE DO SISTEMA DE VISÃO ===\n")
        
        # Teste 1: Navegar para Wikipedia
        print("1. Navegando para Wikipedia...")
        vision.navigate("https://pt.wikipedia.org/wiki/Inteligência_artificial")
        time.sleep(5)
        
        info = vision.get_page_info()
        print(f"   URL: {info.get('url', '?')}")
        print(f"   Body height: {info.get('bodyHeight', 0)}px")
        
        # Teste 2: Rota C (DOM) - mais rápido
        print("\n2. Testando Rota C (DOM extraction)...")
        result = vision.capture_via_dom(scroll_ratio=0.8, delay=1.0, max_scrolls=10)
        
        if result.get("full_text"):
            print(f"\n   Texto extraído: {len(result['full_text'])} chars")
            print(f"   Primeiros 500 chars:")
            print(f"   {result['full_text'][:500]}")
        
        # Salvar resultado
        output = args.output or str(Path.home() / ".hermes" / "vision_test.json")
        with open(output, "w", encoding="utf-8") as f:
            # Simplificar para JSON
            simple = {
                "page_info": result.get("page_info", {}),
                "total_texts": result.get("total_texts", 0),
                "total_scrolls": result.get("total_scrolls", 0),
                "full_text_preview": result.get("full_text", "")[:2000],
            }
            json.dump(simple, f, ensure_ascii=False, indent=2)
        print(f"\n   Resultado salvo em: {output}")
    
    elif args.command == "capture":
        url = args.url or "https://pt.wikipedia.org/wiki/Inteligência_artificial"
        result = vision.capture_complete(url=url, method=args.method)
        
        output = args.output or str(Path.home() / ".hermes" / "vision_capture.json")
        with open(output, "w", encoding="utf-8") as f:
            simple = {
                "page_info": result.get("page_info", {}),
                "combined_count": result.get("combined_count", 0),
                "full_text": " ".join(result.get("combined_texts", []))[:5000],
            }
            json.dump(simple, f, ensure_ascii=False, indent=2)
        print(f"\nResultado salvo em: {output}")
    
    elif args.command == "dom":
        url = args.url or "https://pt.wikipedia.org/wiki/Inteligência_artificial"
        if url:
            vision.navigate(url)
            time.sleep(5)
        result = vision.capture_via_dom()
        
        output = args.output or str(Path.home() / ".hermes" / "vision_dom.txt")
        with open(output, "w", encoding="utf-8") as f:
            f.write(result.get("full_text", ""))
        print(f"Texto salvo em: {output}")
        print(f"Total: {result.get('total_texts', 0)} blocos, {len(result.get('full_text', ''))} chars")
    
    elif args.command == "ocr":
        url = args.url or "https://pt.wikipedia.org/wiki/Inteligência_artificial"
        if url:
            vision.navigate(url)
            time.sleep(5)
        result = vision.capture_with_ocr(max_scrolls=5)
        
        output = args.output or str(Path.home() / ".hermes" / "vision_ocr.txt")
        with open(output, "w", encoding="utf-8") as f:
            f.write("\n".join(result.get("all_texts", [])))
        print(f"Texto OCR salvo em: {output}")


if __name__ == "__main__":
    main()
