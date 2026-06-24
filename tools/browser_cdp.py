#!/usr/bin/env python3
"""
Koldi Browser Control — Chrome CDP Client
==========================================
Controla o Chrome do Senhor Robério via Chrome DevTools Protocol (CDP).

Uso:
    python browser_cdp.py connect          # Testa conexão com Chrome
    python browser_cdp.py list             # Lista abas abertas
    python browser_cdp.py url URL          # Navega para URL
    python browser_cdp.py html             # Extrai HTML da página atual
    python browser_cdp.py text             # Extrai texto visível
    python browser_cdp.py title            # Título da página
    python browser_cdp.py screenshot       # Screenshot (PNG)
    python browser_cdp.py js "CODIGO"      # Executa JavaScript
    python browser_cdp.py click "seletor"  # Clica em elemento (CSS selector)
    python browser_cdp.py type "sel" "txt"  # Digita texto em campo
    python browser_cdp.py new              # Abre nova aba
    python browser_cdp.py close            # Fecha aba atual (se não for a última)
    python browser_cdp.py new-tab URL      # Abre URL em nova aba
    python browser_cdp.py search QUERY     # Pesquisa no Google
    python browser_cdp.py scroll n         # Scroll (px, positivo = para baixo)
    python browser_cdp.py wait N           # Espera N segundos
    python browser_cdp.py back             # Voltar página
    python browser_cdp.py forward          # Avançar página
    python browser_cdp.py refresh          # Recarregar página
    python browser_cdp.py cookies          # Listar cookies
    python browser_cdp.py interactive      # Modo interativo REPL
    python browser_cdp.py daemon           # Modo servidor (aceita comandos via pipe)
"""

import json, sys, os, time, base64, re, urllib.request
from typing import Optional

# ─── CONFIGURAÇÃO ────────────────────────────────────────────────────────────

CDP_PORT = 9222
CDP_HOST = "localhost"

# ─── CLIENTE CDP ─────────────────────────────────────────────────────────────

class CDPClient:
    """Cliente WebSocket para Chrome DevTools Protocol."""

    def __init__(self, host: str = CDP_HOST, port: int = CDP_PORT, tab_id: str = None):
        self.host = host
        self.port = port
        self.ws_url = None
        self.ws = None
        self.tab_id = tab_id
        self.msg_id = 0

    def get_json(self, path: str) -> list | dict:
        """Faz GET HTTP para a API REST do CDP."""
        url = f"http://{self.host}:{self.port}{path}"
        try:
            with urllib.request.urlopen(url, timeout=5) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:
            raise ConnectionError(f"Falha ao conectar ao CDP: {e}")

    def connect(self, tab_id: str = None):
        """Conecta ao WebSocket de uma aba do Chrome."""
        tabs = self.get_json("/json/list")
        if not tabs:
            raise RuntimeError("Nenhuma aba aberta no Chrome")
        
        if tab_id:
            target = next((t for t in tabs if t["id"] == tab_id), None)
        elif self.tab_id:
            target = next((t for t in tabs if t["id"] == self.tab_id), None)
        else:
            # Pega a aba mais recente (última da lista)
            target = tabs[-1]
        
        if not target:
            raise RuntimeError(f"Aba {tab_id or self.tab_id} não encontrada")
        
        self.ws_url = target["webSocketDebuggerUrl"]
        self.tab_id = target["id"]
        
        # Conecta via WebSocket
        import websocket
        self.ws = websocket.create_connection(
            self.ws_url, timeout=30, enable_multithread=True
        )
        
        # Habilita domínios necessários
        self._send("Page.enable")
        self._send("DOM.enable")
        self._send("Runtime.enable")
        self._send("Network.enable")
        
        return {
            "tab_id": self.tab_id,
            "title": target.get("title", ""),
            "url": target.get("url", ""),
        }

    def _send(self, method: str, params: dict = None) -> dict:
        """Envia comando CDP e aguarda resposta."""
        self.msg_id += 1
        msg = {"id": self.msg_id, "method": method}
        if params:
            msg["params"] = params
        self.ws.send(json.dumps(msg))
        
        # Aguarda resposta correspondente
        while True:
            resp = json.loads(self.ws.recv())
            if resp.get("id") == self.msg_id:
                if "error" in resp:
                    raise RuntimeError(f"CDP Error: {resp['error']}")
                return resp.get("result", {})
            # Eventos não solicitados são ignorados

    def _recv_until(self, method: str, timeout: int = 10) -> dict:
        """Aguarda um evento específico."""
        import websocket
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                resp = json.loads(self.ws.recv())
                if resp.get("method") == method:
                    return resp.get("params", {})
            except websocket.WebSocketTimeoutException:
                raise TimeoutError(f"Timeout aguardando {method}")
        raise TimeoutError(f"Timeout aguardando {method}")

    def navigate(self, url: str) -> dict:
        """Navega para URL."""
        result = self._send("Page.navigate", {"url": url})
        if "errorText" in result:
            raise RuntimeError(f"Falha ao navegar: {result['errorText']}")
        return result

    def get_title(self) -> str:
        """Retorna o título da página."""
        result = self._send("Runtime.evaluate", {
            "expression": "document.title",
            "returnByValue": True,
        })
        return result.get("result", {}).get("value", "")

    def get_url(self) -> str:
        """Retorna a URL atual."""
        result = self._send("Runtime.evaluate", {
            "expression": "window.location.href",
            "returnByValue": True,
        })
        return result.get("result", {}).get("value", "")

    def get_html(self) -> str:
        """Retorna o HTML completo da página."""
        result = self._send("DOM.getDocument", {"depth": -1})
        root = result.get("root", {})
        node_id = root.get("nodeId", 0)
        result2 = self._send("DOM.getOuterHTML", {"nodeId": node_id})
        return result2.get("outerHTML", "")

    def get_text(self) -> str:
        """Extrai texto visível da página via JS."""
        result = self._send("Runtime.evaluate", {
            "expression": "document.body ? document.body.innerText : ''",
            "returnByValue": True,
        })
        return result.get("result", {}).get("value", "")

    def evaluate(self, js_code: str) -> dict:
        """Executa JavaScript na página."""
        result = self._send("Runtime.evaluate", {
            "expression": js_code,
            "returnByValue": True,
            "awaitPromise": True,
        })
        return result

    def click(self, selector: str) -> dict:
        """Clica em elemento por CSS selector."""
        # Primeiro encontra o elemento
        js = f"""
        (function() {{
            const el = document.querySelector({json.dumps(selector)});
            if (!el) return {{ error: 'Elemento não encontrado: ' + {json.dumps(selector)} }};
            const rect = el.getBoundingClientRect();
            return {{
                x: rect.left + rect.width / 2,
                y: rect.top + rect.height / 2,
                tag: el.tagName,
                text: (el.textContent || '').trim().substring(0, 100),
            }};
        }})()
        """
        result = self.evaluate(js)
        elem_info = result.get("result", {}).get("value", {})
        
        if "error" in elem_info:
            return {"success": False, "error": elem_info["error"]}
        if "x" not in elem_info:
            return {"success": False, "error": "Elemento invisível"}
        
        # Clica nas coordenadas
        self._send("Input.dispatchMouseEvent", {
            "type": "mousePressed",
            "x": elem_info["x"],
            "y": elem_info["y"],
            "button": "left",
            "clickCount": 1,
        })
        self._send("Input.dispatchMouseEvent", {
            "type": "mouseReleased",
            "x": elem_info["x"],
            "y": elem_info["y"],
            "button": "left",
            "clickCount": 1,
        })
        
        return {"success": True, "element": elem_info}

    def type_text(self, selector: str, text: str) -> dict:
        """Digita texto em um campo."""
        # Foca e limpa o campo
        js = f"""
        (function() {{
            const el = document.querySelector({json.dumps(selector)});
            if (!el) return {{ error: 'Elemento não encontrado' }};
            el.focus();
            el.value = '';
            el.dispatchEvent(new Event('input', {{ bubbles: true }}));
            el.dispatchEvent(new Event('change', {{ bubbles: true }}));
            return {{ tag: el.tagName, ok: true }};
        }})()
        """
        result = self.evaluate(js)
        info = result.get("result", {}).get("value", {})
        if "error" in info:
            return {"success": False, "error": info["error"]}
        
        # Digita caractere por caractere
        for char in text:
            self._send("Input.dispatchKeyEvent", {
                "type": "keyDown",
                "text": char,
                "key": char,
            })
            self._send("Input.dispatchKeyEvent", {
                "type": "keyUp",
                "key": char,
            })
        
        return {"success": True, "text": text}

    def press_key(self, key: str):
        """Pressiona tecla especial (Enter, Tab, Escape, etc)."""
        key_map = {
            "Enter": {"key": "Enter", "code": "Enter", "text": "\r"},
            "Tab": {"key": "Tab", "code": "Tab", "text": "\t"},
            "Escape": {"key": "Escape", "code": "Escape"},
            "Backspace": {"key": "Backspace", "code": "Backspace"},
            "Delete": {"key": "Delete", "code": "Delete"},
            "ArrowUp": {"key": "ArrowUp", "code": "ArrowUp"},
            "ArrowDown": {"key": "ArrowDown", "code": "ArrowDown"},
            "ArrowLeft": {"key": "ArrowLeft", "code": "ArrowLeft"},
            "ArrowRight": {"key": "ArrowRight", "code": "ArrowRight"},
        }
        k = key_map.get(key, {"key": key, "code": key})
        self._send("Input.dispatchKeyEvent", {"type": "keyDown", **k})
        self._send("Input.dispatchKeyEvent", {"type": "keyUp", **k})

    def screenshot(self) -> bytes:
        """Tira screenshot da página atual. Retorna bytes PNG."""
        result = self._send("Page.captureScreenshot", {"format": "png"})
        data = result.get("data", "")
        return base64.b64decode(data)

    def scroll(self, delta_y: int = 500):
        """Rola a página (px positivos = para baixo)."""
        self.evaluate(f"window.scrollBy(0, {delta_y})")

    def scroll_to(self, y: int = 0):
        """Rola para posição específica."""
        self.evaluate(f"window.scrollTo(0, {y})")

    def scroll_to_bottom(self):
        """Rola até o final da página."""
        self.evaluate("window.scrollTo(0, document.body.scrollHeight)")

    def scroll_to_top(self):
        """Rola para o topo."""
        self.evaluate("window.scrollTo(0, 0)")

    def back(self):
        """Voltar página."""
        self._send("Page.navigateToHistoryEntry", {"entryId": -1})

    def forward(self):
        """Avançar página."""
        self._send("Page.navigateToHistoryEntry", {"entryId": 1})

    def refresh(self):
        """Recarregar página."""
        self._send("Page.reload", {"ignoreCache": True})

    def get_cookies(self) -> list:
        """Retorna lista de cookies."""
        result = self._send("Network.getAllCookies")
        return result.get("cookies", [])

    def get_console_log(self) -> list:
        """Retorna logs do console."""
        result = self._send("Runtime.evaluate", {
            "expression": "console.logs = console.logs || []; JSON.stringify(console.logs)",
            "returnByValue": True,
        })
        return result.get("result", {}).get("value", [])

    def get_page_info(self) -> dict:
        """Info completa da página atual."""
        return {
            "title": self.get_title(),
            "url": self.get_url(),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

    def close(self):
        """Fecha conexão WebSocket."""
        if self.ws:
            try:
                self.ws.close()
            except:
                pass
            self.ws = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


# ─── COMANDOS CLI ────────────────────────────────────────────────────────────

def cmd_connect():
    """Testa conexão com o Chrome CDP."""
    with CDPClient() as cdp:
        info = cdp.connect()
        print(f"✅ Conectado ao Chrome!")
        print(f"  Aba: {info['title']}")
        print(f"  URL: {info['url']}")
        print(f"  ID:  {info['tab_id']}")

def cmd_list():
    """Lista abas abertas."""
    client = CDPClient()
    tabs = client.get_json("/json/list")
    if not tabs:
        print("Nenhuma aba aberta.")
        return
    for i, tab in enumerate(tabs):
        url = tab.get("url", "")
        title = tab.get("title", "")
        tid = tab.get("id", "")[:12]
        print(f"  [{i}] {title}")
        print(f"      URL: {url}")
        print(f"      ID:  {tid}")
        print()

def cmd_navigate(url):
    """Navega para URL."""
    with CDPClient() as cdp:
        info = cdp.connect()
        print(f"📍 Navegando para: {url}")
        cdp.navigate(url)
        time.sleep(1)
        page = cdp.get_page_info()
        print(f"   Título: {page['title']}")

def cmd_new_tab(url=None):
    """Abre nova aba."""
    client = CDPClient()
    if url:
        data = client.get_json(f"/json/new?{urllib.parse.quote(url, safe='')}")
    else:
        data = client.get_json("/json/new")
    print(f"✅ Nova aba criada: {data.get('title', '')}")
    print(f"   URL: {data.get('url', '')}")
    print(f"   ID:  {data.get('id', '')[:12]}")

def cmd_html():
    """Extrai HTML."""
    with CDPClient() as cdp:
        cdp.connect()
        html = cdp.get_html()
        print(html[:5000])
        if len(html) > 5000:
            print(f"\n... ({len(html)} bytes no total)")

def cmd_text():
    """Extrai texto visível."""
    with CDPClient() as cdp:
        cdp.connect()
        text = cdp.get_text()
        print(text[:5000])
        if len(text) > 5000:
            print(f"\n... ({len(text)} chars no total)")

def cmd_title():
    """Mostra título."""
    with CDPClient() as cdp:
        cdp.connect()
        info = cdp.get_page_info()
        print(f"📌 Título: {info['title']}")
        print(f"🔗 URL:    {info['url']}")

def cmd_screenshot():
    """Tira screenshot."""
    with CDPClient() as cdp:
        cdp.connect()
        png_data = cdp.screenshot()
        path = os.path.expanduser(f"~/screenshot_{int(time.time())}.png")
        with open(path, "wb") as f:
            f.write(png_data)
        print(f"📸 Screenshot salvo em: {path}")
        print(f"   Tamanho: {len(png_data)} bytes")

def cmd_js(js_code):
    """Executa JavaScript."""
    with CDPClient() as cdp:
        cdp.connect()
        result = cdp.evaluate(js_code)
        value = result.get("result", {}).get("value", "")
        print(json.dumps(value, indent=2, ensure_ascii=False))

def cmd_click(selector):
    """Clica em elemento."""
    with CDPClient() as cdp:
        cdp.connect()
        result = cdp.click(selector)
        if result["success"]:
            el = result["element"]
            print(f"🖱️ Clique em <{el.get('tag', '?')}>: {el.get('text', '')[:80]}")
        else:
            print(f"❌ {result['error']}")

def cmd_type(selector, text):
    """Digita texto."""
    with CDPClient() as cdp:
        cdp.connect()
        result = cdp.type_text(selector, text)
        if result["success"]:
            print(f"⌨️ Digitado: {text}")
        else:
            print(f"❌ {result['error']}")

def cmd_scroll(delta):
    """Rola página."""
    with CDPClient() as cdp:
        cdp.connect()
        cdp.scroll(delta)
        print(f"📜 Scroll: {delta:+d}px")

def cmd_back():
    with CDPClient() as cdp:
        cdp.connect()
        cdp.back()
        print("🔙 Voltando...")
        time.sleep(0.5)
        print(f"   {cdp.get_title()}")

def cmd_forward():
    with CDPClient() as cdp:
        cdp.connect()
        cdp.forward()
        print("🔜 Avançando...")
        time.sleep(0.5)
        print(f"   {cdp.get_title()}")

def cmd_refresh():
    with CDPClient() as cdp:
        cdp.connect()
        cdp.refresh()
        print("🔄 Recarregando...")
        time.sleep(1)
        print(f"   {cdp.get_title()}")

def cmd_wait(seconds):
    print(f"⏳ Aguardando {seconds}s...")
    time.sleep(seconds)
    print("   OK")

def cmd_cookies():
    with CDPClient() as cdp:
        cdp.connect()
        cookies = cdp.get_cookies()
        if not cookies:
            print("Nenhum cookie.")
            return
        for c in cookies:
            print(f"  🍪 {c['name']} = {c['value'][:60]}")
            print(f"     Domínio: {c['domain']} | Path: {c['path']}")

def cmd_search(query):
    """Pesquisa no Google."""
    import urllib.parse
    url = f"https://www.google.com/search?q={urllib.parse.quote_plus(query)}"
    cmd_navigate(url)

def cmd_interactive():
    """Modo interativo REPL."""
    import readline
    with CDPClient() as cdp:
        cdp.connect()
        print(f"🔌 Modo interativo CDP — Chrome conectado!")
        print(f"   Aba: {cdp.get_title()}")
        print(f"   Comandos: url, title, text, html, screenshot, js <code>,")
        print(f"             click <sel>, type <sel> <txt>, scroll <n>,")
        print(f"             back, forward, refresh, cookies, wait <n>,")
        print(f"             search <q>, help, exit")
        print()
        
        while True:
            try:
                cmd = input("cdp> ").strip()
                if not cmd:
                    continue
                if cmd == "exit" or cmd == "quit":
                    break
                if cmd == "help":
                    print("Comandos: url, title, text, html, screenshot, js <code>,")
                    print("          click <sel>, type <sel> <txt>, scroll <n>,")
                    print("          back, forward, refresh, cookies, wait <n>,")
                    print("          search <q>, source, info, help, exit")
                    continue
                
                parts = cmd.split(maxsplit=1)
                action = parts[0]
                arg = parts[1] if len(parts) > 1 else ""
                
                if action == "url":
                    if arg:
                        cdp.navigate(arg)
                        time.sleep(1)
                        print(cdp.get_page_info())
                    else:
                        print(cdp.get_url())
                elif action == "title":
                    print(cdp.get_title())
                elif action == "text":
                    print(cdp.get_text()[:2000])
                elif action == "html":
                    print(cdp.get_html()[:2000])
                elif action == "source":
                    h = cdp.get_html()
                    print(h[:3000])
                    if len(h) > 3000:
                        print(f"... ({len(h)} bytes)")
                elif action == "info":
                    print(json.dumps(cdp.get_page_info(), indent=2))
                elif action == "screenshot":
                    data = cdp.screenshot()
                    path = f"screenshot_{int(time.time())}.png"
                    with open(path, "wb") as f:
                        f.write(data)
                    print(f"📸 {path} ({len(data)} bytes)")
                elif action == "js":
                    if arg:
                        r = cdp.evaluate(arg)
                        print(json.dumps(r.get("result", {}).get("value", ""), indent=2, ensure_ascii=False))
                    else:
                        print("Uso: js <código>")
                elif action == "click":
                    if arg:
                        r = cdp.click(arg)
                        if r["success"]:
                            print(f"🖱️ OK: <{r['element'].get('tag')}>")
                        else:
                            print(f"❌ {r['error']}")
                    else:
                        print("Uso: click <seletor CSS>")
                elif action == "type":
                    parts2 = arg.split(maxsplit=1)
                    if len(parts2) == 2:
                        r = cdp.type_text(parts2[0], parts2[1])
                        print("✅ OK" if r["success"] else f"❌ {r['error']}")
                    else:
                        print("Uso: type <seletor> <texto>")
                elif action == "scroll":
                    try:
                        cdp.scroll(int(arg) if arg else 500)
                        print("📜 OK")
                    except:
                        print("Uso: scroll <px>")
                elif action == "back":
                    cdp.back(); time.sleep(0.5); print(f"🔙 {cdp.get_title()}")
                elif action == "forward":
                    cdp.forward(); time.sleep(0.5); print(f"🔜 {cdp.get_title()}")
                elif action == "refresh":
                    cdp.refresh(); time.sleep(1); print(f"🔄 {cdp.get_title()}")
                elif action == "cookies":
                    for c in cdp.get_cookies():
                        print(f"  {c['name']} = {c['value'][:50]}")
                elif action == "wait":
                    try:
                        time.sleep(int(arg) if arg else 2)
                        print("⏳ OK")
                    except:
                        print("Uso: wait <segundos>")
                elif action == "search":
                    if arg:
                        import urllib.parse
                        cdp.navigate(f"https://www.google.com/search?q={urllib.parse.quote_plus(arg)}")
                        time.sleep(1)
                        print(cdp.get_page_info())
                    else:
                        print("Uso: search <consulta>")
                else:
                    print(f"Comando desconhecido: {action}")
            except KeyboardInterrupt:
                print()
                break
            except Exception as e:
                print(f"Erro: {e}")

def cmd_daemon():
    """Modo servidor — lê comandos JSON do stdin e escreve resultados no stdout."""
    with CDPClient() as cdp:
        cdp.connect()
        
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                cmd = json.loads(line)
                action = cmd.get("action", "")
                args = cmd.get("args", {})
                
                result = {"status": "ok"}
                
                if action == "navigate":
                    cdp.navigate(args.get("url", ""))
                    time.sleep(0.5)
                    result["page"] = cdp.get_page_info()
                elif action == "title":
                    result["title"] = cdp.get_title()
                elif action == "url":
                    result["url"] = cdp.get_url()
                elif action == "text":
                    result["text"] = cdp.get_text()
                elif action == "html":
                    result["html"] = cdp.get_html()
                elif action == "info":
                    result["page"] = cdp.get_page_info()
                elif action == "click":
                    result["click"] = cdp.click(args.get("selector", ""))
                elif action == "type":
                    result["type"] = cdp.type_text(
                        args.get("selector", ""),
                        args.get("text", "")
                    )
                elif action == "scroll":
                    cdp.scroll(args.get("delta", 500))
                    result["scrolled"] = True
                elif action == "js":
                    r = cdp.evaluate(args.get("code", ""))
                    result["js_result"] = r.get("result", {})
                elif action == "screenshot":
                    data = cdp.screenshot()
                    path = os.path.expanduser(f"~/cdp_screenshot_{int(time.time())}.png")
                    with open(path, "wb") as f:
                        f.write(data)
                    result["screenshot_path"] = path
                elif action == "back":
                    cdp.back()
                    time.sleep(0.5)
                    result["page"] = cdp.get_page_info()
                elif action == "forward":
                    cdp.forward()
                    time.sleep(0.5)
                    result["page"] = cdp.get_page_info()
                elif action == "refresh":
                    cdp.refresh()
                    time.sleep(0.5)
                    result["page"] = cdp.get_page_info()
                elif action == "cookies":
                    result["cookies"] = cdp.get_cookies()
                elif action == "press":
                    cdp.press_key(args.get("key", "Enter"))
                    result["pressed"] = args.get("key", "Enter")
                elif action == "scroll_to":
                    cdp.scroll_to(args.get("y", 0))
                    result["scrolled_to"] = args.get("y", 0)
                elif action == "scroll_bottom":
                    cdp.scroll_to_bottom()
                    result["scrolled"] = "bottom"
                elif action == "scroll_top":
                    cdp.scroll_to_top()
                    result["scrolled"] = "top"
                elif action == "close":
                    result["status"] = "bye"
                elif action == "ping":
                    result["pong"] = True
                else:
                    result = {"status": "error", "message": f"Unknown action: {action}"}
                
                sys.stdout.write(json.dumps(result, ensure_ascii=False) + "\n")
                sys.stdout.flush()
                
                if action == "close":
                    break
                    
            except Exception as e:
                sys.stdout.write(json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False) + "\n")
                sys.stdout.flush()


# ─── MAIN ────────────────────────────────────────────────────────────────────

def main():
    import urllib.parse  # para new_tab

    if len(sys.argv) < 2:
        print(__doc__)
        return

    action = sys.argv[1]

    try:
        if action == "connect":
            cmd_connect()
        elif action == "list":
            cmd_list()
        elif action == "url" or action == "navigate" or action == "go":
            if len(sys.argv) < 3:
                print("Uso: browser_cdp.py url <URL>")
                return
            cmd_navigate(sys.argv[2])
        elif action == "new" or action == "new-tab" or action == "newtab":
            url = sys.argv[2] if len(sys.argv) > 2 else None
            cmd_new_tab(url)
        elif action == "html":
            cmd_html()
        elif action == "text":
            cmd_text()
        elif action == "title":
            cmd_title()
        elif action == "screenshot" or action == "ss" or action == "screen":
            cmd_screenshot()
        elif action == "js" or action == "eval" or action == "evaluate":
            if len(sys.argv) < 3:
                print("Uso: browser_cdp.py js <código>")
                return
            cmd_js(" ".join(sys.argv[2:]))
        elif action == "click":
            if len(sys.argv) < 3:
                print("Uso: browser_cdp.py click <seletor CSS>")
                return
            cmd_click(" ".join(sys.argv[2:]))
        elif action == "type":
            if len(sys.argv) < 4:
                print("Uso: browser_cdp.py type <seletor> <texto>")
                return
            cmd_type(sys.argv[2], " ".join(sys.argv[3:]))
        elif action == "scroll":
            delta = int(sys.argv[2]) if len(sys.argv) > 2 else 500
            cmd_scroll(delta)
        elif action == "back":
            cmd_back()
        elif action == "forward":
            cmd_forward()
        elif action == "refresh" or action == "reload":
            cmd_refresh()
        elif action == "wait":
            seconds = int(sys.argv[2]) if len(sys.argv) > 2 else 3
            cmd_wait(seconds)
        elif action == "cookies":
            cmd_cookies()
        elif action == "search":
            if len(sys.argv) < 3:
                print("Uso: browser_cdp.py search <consulta>")
                return
            cmd_search(" ".join(sys.argv[2:]))
        elif action == "interactive" or action == "repl":
            cmd_interactive()
        elif action == "daemon" or action == "serve":
            cmd_daemon()
        elif action == "enter":
            with CDPClient() as cdp:
                cdp.connect()
                cdp.press_key("Enter")
                print("✅ Enter pressionado")
        elif action == "tab":
            with CDPClient() as cdp:
                cdp.connect()
                cdp.press_key("Tab")
                print("✅ Tab pressionado")
        elif action == "escape":
            with CDPClient() as cdp:
                cdp.connect()
                cdp.press_key("Escape")
                print("✅ Escape pressionado")
        else:
            print(f"Comando desconhecido: {action}")
            print(__doc__)
    except ConnectionError as e:
        print(f"\n❌ ERRO DE CONEXÃO: {e}")
        print("\n   Para resolver:")
        print(f"   1. Execute: C:\\Users\\dell-\\chrome_cdp.bat")
        print("   2. Aguarde o Chrome abrir")
        print("   3. Tente novamente\n")
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()