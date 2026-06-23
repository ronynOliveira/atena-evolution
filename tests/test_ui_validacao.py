"""
Atena UI Validacao — Testes Automatizados da UI Web (HTML, CSS, JS e Integracao)
Este script valida a estrutura, o design e o comportamento logico do index.html e style.css.
Utiliza apenas bibliotecas padrao do Python (unittest, html.parser, re, json, os).
"""
import os
import re
import json
import unittest
import html.parser

# Caminhos absolutos para os arquivos do projeto
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML_PATH = os.path.join(BASE_DIR, "web", "index.html")
CSS_PATH = os.path.join(BASE_DIR, "web", "style.css")


class AtenaHTMLParser(html.parser.HTMLParser):
    """
    Parser HTML especializado para coletar elementos, IDs, classes,
    labels, botões, imagens e inputs para validação detalhada.
    """
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.classes = set()
        self.labels = []      # list of dicts: {'for': str, 'text': str}
        self.buttons = []     # list of dicts: {'id': str, 'text': str, 'attrs': dict}
        self.images = []      # list of dicts: {'id': str, 'alt': str, 'attrs': dict}
        self.inputs = []      # list of dicts: {'id': str, 'type': str, 'attrs': dict}
        self.sections = []    # list of dicts: {'tag': str, 'id': str, 'class': str}
        self.interactive_elements = []  # list of dicts: {'tag': str, 'id': str, 'attrs': dict}
        self.script_content = ""
        
        self._tag_stack = []
        self._in_script = False

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        element_id = attrs_dict.get("id")
        element_class = attrs_dict.get("class")
        
        if tag == "script":
            self._in_script = True
            
        if element_id:
            self.ids.add(element_id)
            
        if element_class:
            for cls in element_class.split():
                self.classes.add(cls)

        # Rastreia seções e containers importantes
        if tag in ["div", "section", "aside", "main", "nav", "header"]:
            self.sections.append({
                "tag": tag,
                "id": element_id,
                "class": element_class
            })
            
        # Coleta elementos interativos
        if tag in ["button", "input", "select", "textarea", "a"]:
            self.interactive_elements.append({
                "tag": tag,
                "id": element_id,
                "attrs": attrs_dict
            })

        # Processamento imediato para void elements (auto-fechados no HTML5)
        if tag == "img":
            self.images.append({
                "id": element_id,
                "alt": attrs_dict.get("alt"),
                "attrs": attrs_dict
            })
        elif tag == "input":
            self.inputs.append({
                "id": element_id,
                "type": attrs_dict.get("type", "text"),
                "attrs": attrs_dict
            })
        else:
            # Para outros elementos, empilha no stack para pegar o texto interno no fechamento
            self.tags_entry = {
                "tag": tag,
                "attrs": attrs_dict,
                "text": ""
            }
            self._tag_stack.append(self.tags_entry)

    def handle_startendtag(self, tag, attrs):
        # Chama handlers apropriados para tags com fechamento explicito inline (ex: <img />)
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_data(self, data):
        if self._in_script:
            self.script_content += data
        elif self._tag_stack:
            self._tag_stack[-1]["text"] += data

    def handle_endtag(self, tag):
        if tag == "script":
            self._in_script = False
            
        # Ignora tags void que ja foram processadas no starttag
        if tag in ["input", "img"]:
            return
            
        if self._tag_stack:
            for i in range(len(self._tag_stack) - 1, -1, -1):
                if self._tag_stack[i]["tag"] == tag:
                    el = self._tag_stack.pop(i)
                    el_text = el["text"].strip()
                    
                    # Propaga o texto do elemento filho para o pai imediato se houver um pai no stack.
                    # Isso simula o comportamento do textContent do DOM para tags aninhadas (ex: button > span > text)
                    if i > 0:
                        self._tag_stack[i - 1]["text"] += " " + el["text"]
                        
                    # Salva nas listas de especialidade no fechamento da tag
                    if tag == "label":
                        self.labels.append({
                            "for": el["attrs"].get("for"),
                            "text": el_text
                        })
                    elif tag == "button":
                        self.buttons.append({
                            "id": el["attrs"].get("id"),
                            "text": el_text,
                            "attrs": el["attrs"]
                        })
                    elif tag in ["textarea", "select"]:
                        self.inputs.append({
                            "id": el["attrs"].get("id"),
                            "type": tag,
                            "attrs": el["attrs"]
                        })
                    break


class TestAtenaUIValidacao(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        # Verifica se os arquivos realmente existem antes de iniciar os testes
        if not os.path.exists(HTML_PATH):
            raise FileNotFoundError(f"Arquivo HTML nao encontrado em: {HTML_PATH}")
        if not os.path.exists(CSS_PATH):
            raise FileNotFoundError(f"Arquivo CSS nao encontrado em: {CSS_PATH}")
            
        # Carrega o HTML
        with open(HTML_PATH, "r", encoding="utf-8") as f:
            cls.html_content = f.read()
            
        # Carrega o CSS
        with open(CSS_PATH, "r", encoding="utf-8") as f:
            cls.css_content = f.read()
            
        # Analisa o HTML utilizando o parser customizado
        cls.parser = AtenaHTMLParser()
        cls.parser.feed(cls.html_content)

    # ═══════════════════════════════════════════════════════════
    # 1. TESTES DE ESTRUTURA HTML
    # ═══════════════════════════════════════════════════════════
    
    def test_html_sections_exist(self):
        """1.1 Verifica se todas as secoes estruturais principais estao no HTML."""
        # Seções cruciais para a arquitetura da Atena
        expected_sections = [
            ("aside", "sidebar"),
            ("div", "sidebarOverlay"),
            ("div", "toastContainer"),
            ("nav", None), # Tab navigation
            ("div", "tab-chat"),
            ("div", "tab-images"),
            ("div", "tab-config"),
            ("div", "imagePreviewModal"),
            ("div", "confirmModal")
        ]
        
        for tag, element_id in expected_sections:
            found = False
            for sec in self.parser.sections:
                if sec["tag"] == tag:
                    if element_id is None or sec["id"] == element_id:
                        found = True
                        break
            self.assertTrue(
                found, 
                f"Secao obrigatoria tag='{tag}' com id='{element_id}' nao foi encontrada no HTML."
            )

    def test_html_ids_correct(self):
        """1.2 Verifica se os IDs essenciais referenciados nos scripts existem no DOM."""
        essential_ids = {
            "sidebar", "sidebarOverlay", "sidebarToggle",
            "ollamaStatusDot", "ollamaStatusText", "ollamaVersion",
            "apiStatusDot", "apiStatusText", "apiLatency",
            "modelSelect", "refreshModelsBtn", "temperatureSlider", "temperatureValue",
            "maxTokensSlider", "maxTokensValue", "chatMessages", "chatInput", "sendBtn",
            "welcomeMessage", "imagePromptInput", "generateImageBtn", "clearImagePromptBtn",
            "imageGallery", "galleryEmpty", "configOllamaUrl", "configApiUrl", "configModel",
            "configTemperature", "configMaxTokens", "saveAllSettingsBtn", "resetSettingsBtn",
            "historyList", "clearHistoryBtn", "newChatBtn", "exportChatBtn", "themeBtn",
            "imagePreviewModal", "closePreviewModal", "closePreviewBtn", "previewImage",
            "previewModalTitle", "downloadPreviewBtn", "confirmModal", "confirmModalTitle",
            "confirmModalText", "confirmModalCancel", "confirmModalOk", "toastContainer",
            "attachBtn", "micBtn"
        }
        
        missing_ids = essential_ids - self.parser.ids
        self.assertEqual(
            len(missing_ids), 0, 
            f"Os seguintes IDs essenciais estao faltando no HTML: {missing_ids}"
        )

    def test_html_forms_and_fields(self):
        """1.3 Verifica se os campos de input e forms possuem os tipos e atributos corretos."""
        # Mapeamento de IDs esperados e seus tipos de controle correspondentes
        expected_inputs = {
            "temperatureSlider": "range",
            "maxTokensSlider": "range",
            "ollamaUrl": "text",
            "apiLocalUrl": "text",
            "geminiKey": "password",
            "openaiKey": "password",
            "anthropicKey": "password",
            "chatInput": "textarea",
            "imagePromptInput": "textarea",
            "configOllamaUrl": "text",
            "configApiUrl": "text",
            "configModel": "select",
            "configTemperature": "range",
            "configMaxTokens": "range",
            "configGeminiKey": "password",
            "configOpenaiKey": "password",
            "configAnthropicKey": "password"
        }
        
        found_inputs = {inp["id"]: inp["type"] for inp in self.parser.inputs if inp["id"]}
        
        for inp_id, expected_type in expected_inputs.items():
            self.assertIn(inp_id, found_inputs, f"Campo de entrada '{inp_id}' nao encontrado no DOM.")
            self.assertEqual(
                found_inputs[inp_id], expected_type,
                f"O campo '{inp_id}' deveria ser do tipo '{expected_type}', mas e '{found_inputs[inp_id]}'."
            )

    def test_html_buttons_and_texts(self):
        """1.4 Verifica se os botoes principais existem e possuem textos corretos ou indicativos."""
        # Alguns botões possuem texto, outros ícones do FontAwesome. 
        # Para botões com ícones, validamos que possuem atributos descritivos ou title/tooltip.
        button_validations = [
            ("refreshModelsBtn", "Atualizar Modelos"),
            ("saveApiKeysBtn", "Salvar"),
            ("testConnectionsBtn", "Testar"),
            ("saveAllSettingsBtn", "Salvar Configurações"),
            ("resetSettingsBtn", "Restaurar Padrões"),
            ("generateImageBtn", "Gerar Imagem"),
            ("confirmModalCancel", "Cancelar"),
            ("confirmModalOk", "Confirmar"),
            ("closePreviewBtn", "Fechar"),
            ("downloadPreviewBtn", "Download")
        ]
        
        buttons_dict = {btn["id"]: btn for btn in self.parser.buttons if btn["id"]}
        
        for btn_id, expected_text in button_validations:
            self.assertIn(btn_id, buttons_dict, f"Botao '{btn_id}' nao encontrado.")
            btn_obj = buttons_dict[btn_id]
            btn_text_clean = re.sub(r'\s+', ' ', btn_obj["text"]).strip()
            
            # O texto pode estar dentro de tags extras ou conter icones, entao verificamos substring/tooltip
            self.assertTrue(
                expected_text in btn_text_clean or expected_text in btn_obj["attrs"].get("title", "") or expected_text in btn_obj["attrs"].get("data-tooltip", ""),
                f"Botao '{btn_id}' deveria conter o texto/tooltip '{expected_text}', mas tem: Text='{btn_text_clean}', Attrs={btn_obj['attrs']}"
            )

    def test_html_accessibility(self):
        """1.5 Valida a acessibilidade basica dos elementos do HTML (alt, labels, titles)."""
        # A. Validação de Imagens (devem possuir alt)
        for img in self.parser.images:
            alt_text = img["alt"]
            self.assertIsNotNone(alt_text, f"A imagem com id='{img['id']}' e attrs='{img['attrs']}' nao possui o atributo 'alt'.")
            self.assertTrue(len(alt_text.strip()) > 0, f"O atributo 'alt' da imagem '{img['id']}' nao pode estar em branco.")
            
        # B. Validação de Labels (devem apontar para IDs existentes)
        for label in self.parser.labels:
            target_id = label["for"]
            if target_id: # Se tiver 'for', deve referenciar um elemento existente
                self.assertIn(
                    target_id, self.parser.ids, 
                    f"O <label> com texto '{label['text']}' aponta para um id inexistente: 'for=\"{target_id}\"'."
                )

        # C. Validação de Botões Interativos Sem Texto (devem ter title, aria-label ou data-tooltip)
        for item in self.parser.interactive_elements:
            if item["tag"] == "button":
                btn_attrs = item["attrs"]
                btn_id = item["id"]
                
                # Procura se o botao correspondente tem texto interno no parser
                btn_in_list = [b for b in self.parser.buttons if b["id"] == btn_id] if btn_id else []
                # Caso nao ache pelo ID, busca em todos os botoes comparando a referencia de atributos
                btn_text = ""
                if btn_in_list:
                    btn_text = btn_in_list[0]["text"]
                else:
                    # Tenta encontrar no parser de botoes pelo atributo 'class' correspondente
                    classes = btn_attrs.get("class", "")
                    for b in self.parser.buttons:
                        if b["attrs"].get("class") == classes and b["attrs"].get("data-tab") == btn_attrs.get("data-tab") and b["attrs"].get("data-panel") == btn_attrs.get("data-panel"):
                            btn_text = b["text"]
                            break
                
                if not btn_text.strip():
                    has_acc = any(k in btn_attrs for k in ["aria-label", "title", "data-tooltip", "data-tooltext", "aria-labelledby"])
                    self.assertTrue(
                        has_acc, 
                        f"Botao interativo sem texto visivel (id={btn_id}, attrs={btn_attrs}) precisa de um atributo de acessibilidade (aria-label, title ou tooltip)."
                    )

    # ═══════════════════════════════════════════════════════════
    # 2. TESTES DE ESTILOS CSS
    # ═══════════════════════════════════════════════════════════
    
    def test_css_variables_defined(self):
        """2.1 Verifica se as variaveis de design system CSS estao declaradas no :root."""
        # Variaveis CSS fundamentais solicitadas e esperadas
        required_vars = [
            "--bg-primary", "--bg-secondary", "--bg-tertiary", "--bg-card", "--bg-input", "--bg-sidebar",
            "--accent-blue", "--accent-purple", "--accent-pink", "--accent-cyan", "--accent-green", "--accent-red",
            "--text-primary", "--text-secondary", "--text-muted",
            "--border-color", "--border-hover",
            "--font-main", "--font-mono"
        ]
        
        for var_name in required_vars:
            self.assertIn(
                var_name, self.css_content,
                f"Variavel de estilo CSS essencial '{var_name}' nao encontrada no arquivo style.css."
            )

    def test_css_main_classes_exist(self):
        """2.2 Verifica se as classes CSS de layout e de componentes principais estao no arquivo."""
        required_classes = [
            ".app-container", ".sidebar", ".sidebar-header", ".sidebar-logo", ".sidebar-brand",
            ".sidebar-nav", ".sidebar-nav-btn", ".sidebar-content", ".sidebar-section",
            ".status-card", ".status-indicator", ".status-dot", ".form-group",
            ".main-content", ".main-header", ".tab-nav", ".tab-btn", ".tab-content", ".tab-pane",
            ".chat-messages", ".message", ".message-avatar", ".message-body", ".message-bubble",
            ".welcome-message", ".chat-input-area", ".chat-input-container", ".image-gen-container",
            ".modal-overlay", ".modal", ".toast-container", ".toast"
        ]
        
        # Faz uma busca por classes no CSS. 
        # Usamos uma expressao regular simples e flexivel com limite de palavra (\b) para tolerar classes combinadas/aninhadas
        for cls in required_classes:
            escaped_cls = re.escape(cls)
            pattern = rf"{escaped_cls}\b"
            match = re.search(pattern, self.css_content)
            self.assertIsNotNone(
                match, 
                f"A classe CSS principal '{cls}' nao foi encontrada no arquivo style.css."
            )

    def test_css_animations_defined(self):
        """2.3 Verifica se as animacoes chave (@keyframes) estao devidamente declaradas."""
        expected_animations = [
            "orbFloat", "fadeIn", "pulse", "welcomePulse",
            "messageIn", "typingBounce", "toastIn", "toastOut",
            "modalFadeIn", "modalSlideIn", "spin"
        ]
        
        for anim in expected_animations:
            pattern = rf"@keyframes\s+{re.escape(anim)}\b"
            match = re.search(pattern, self.css_content)
            self.assertIsNotNone(
                match, 
                f"A animacao @keyframes '{anim}' nao foi declarada no arquivo style.css."
            )

    def test_css_responsiveness_media_queries(self):
        """2.4 Verifica se ha suporte a responsividade atraves de diretivas @media."""
        # Procuramos por diretivas @media estruturadas
        self.assertIn("@media", self.css_content, "O style.css nao possui nenhuma diretiva @media de responsividade.")
        
        # Verifica breakpoints comuns definidos no style.css
        breakpoints = ["1024px", "768px", "480px"]
        for bp in breakpoints:
            self.assertTrue(
                re.search(rf"@media\s*\(max-width:\s*{bp}\)", self.css_content) is not None,
                f"Breakpoint responsivo max-width: {bp} nao foi encontrado no style.css."
            )

    def test_css_dark_mode_colors(self):
        """2.5 Verifica se as definicoes de cores primarias pertencem a uma paleta Dark UI Premium."""
        # O Atena deve rodar em modo Dark (preto, azul escuro, roxo escuro). 
        # Vamos encontrar os valores atribuídos a cores de fundo chave.
        bg_primary_match = re.search(r'--bg-primary\s*:\s*([^;]+);', self.css_content)
        bg_sidebar_match = re.search(r'--bg-sidebar\s*:\s*([^;]+);', self.css_content)
        
        self.assertIsNotNone(bg_primary_match, "Nao foi possivel extrair o valor da variavel --bg-primary no CSS.")
        self.assertIsNotNone(bg_sidebar_match, "Nao foi possivel extrair o valor da variavel --bg-sidebar no CSS.")
        
        bg_primary_val = bg_primary_match.group(1).strip().lower()
        bg_sidebar_val = bg_sidebar_match.group(1).strip().lower()
        
        # Validamos se as cores principais sao escuras. Em geral, hexadecimais iniciam com #0 ou #1, 
        # ou contem valores rgb muito baixos, caracterizando tons pretos/grafites/azul escuro.
        is_dark_primary = bg_primary_val.startswith('#0') or bg_primary_val.startswith('#1') or 'rgb(' in bg_primary_val
        is_dark_sidebar = bg_sidebar_val.startswith('#0') or bg_sidebar_val.startswith('#1') or 'rgb(' in bg_sidebar_val
        
        self.assertTrue(
            is_dark_primary, 
            f"A cor de background principal '--bg-primary: {bg_primary_val}' nao parece ser escura (Dark Mode)."
        )
        self.assertTrue(
            is_dark_sidebar, 
            f"A cor de background do sidebar '--bg-sidebar: {bg_sidebar_val}' nao parece ser escura (Dark Mode)."
        )

    # ═══════════════════════════════════════════════════════════
    # 3. TESTES DE FUNCIONALIDADES JAVASCRIPT
    # ═══════════════════════════════════════════════════════════
    
    def test_js_functions_exist(self):
        """3.1 Verifica se as funcoes Javascript essenciais estao definidas no escopo."""
        script_code = self.parser.script_content
        self.assertTrue(len(script_code) > 0, "Nenhum script JS inline foi encontrado dentro do index.html.")
        
        required_functions = [
            "checkOllamaStatus",
            "checkApiStatus",
            "fetchModels",
            "populateModelSelects",
            "sendMessage",
            "appendMessageBubble",
            "formatMessage",
            "showTypingIndicator",
            "removeTypingIndicator",
            "scrollToBottom",
            "generateImage",
            "renderImageGallery",
            "showConfirm",
            "saveConversation",
            "renderHistory"
        ]
        
        for func in required_functions:
            # Procura por definicoes normais: 'function nome(' ou 'async function nome('
            pattern = rf"(?:async\s+)?function\s+{re.escape(func)}\b"
            match = re.search(pattern, script_code)
            self.assertIsNotNone(
                match, 
                f"Funcao essencial JS '{func}' nao encontrada ou nao definida sob sintaxe 'function {func}'."
            )

    def test_js_local_storage_usage(self):
        """3.2 Verifica se as chaves corretas de localStorage estao configuradas para persistencia."""
        script_code = self.parser.script_content
        
        # As chaves de persistencia da Atena
        expected_keys = [
            "atena_ollamaUrl",
            "atena_apiUrl",
            "atena_model",
            "atena_temperature",
            "atena_maxTokens",
            "atena_conversations",
            "atena_images"
        ]
        
        for key in expected_keys:
            # Verifica se ha operacao de getItem ou setItem com a chave
            self.assertTrue(
                key in script_code,
                f"A chave do LocalStorage '{key}' nao esta sendo utilizada no script JS para persistencia."
            )

    def test_js_event_listeners_configured(self):
        """3.3 Verifica se os hooks e ouvintes de eventos do JS estao configurados corretamente."""
        script_code = self.parser.script_content
        
        # A. Verifica o registro via addEventListener
        # Deve ter registros de cliques em elementos do DOM
        self.assertIn("addEventListener", script_code, "O codigo JS nao registra nenhum listener via addEventListener.")
        
        # B. Verifica se ha hooks de botoes chave
        confirm_cancel_listener = re.search(r'confirmModalCancel\.addEventListener', script_code)
        confirm_ok_listener = re.search(r'confirmModalOk\.addEventListener', script_code)
        
        self.assertIsNotNone(
            confirm_cancel_listener, 
            "Event listener para acao 'confirmModalCancel' nao registrado no Javascript."
        )
        self.assertIsNotNone(
            confirm_ok_listener, 
            "Event listener para acao 'confirmModalOk' nao registrado no Javascript."
        )
        
        # C. Valida event handlers inline no HTML (e.g. onclick na mensagem para copiar/regenerar)
        self.assertIn("onclick=\"copyMessage(this)\"", self.html_content)
        self.assertIn("onclick=\"regenerateMessage(this)\"", self.html_content)

    # ═══════════════════════════════════════════════════════════
    # 4. TESTES DE INTEGRACAO E FALLBACK
    # ═══════════════════════════════════════════════════════════
    
    def test_integration_urls(self):
        """4.1 Verifica as configuracoes de URLs para integracao Ollama e API local."""
        script_code = self.parser.script_content
        
        # Ollama local por padrao roda em localhost:11434
        self.assertTrue(
            "localhost:11434" in script_code or "127.0.0.1:11434" in script_code,
            "A URL do Ollama padrao (localhost:11434) nao esta definida no script JS."
        )
        
        # API Local por padrao roda em localhost:8000
        self.assertTrue(
            "localhost:8000" in script_code or "127.0.0.1:8000" in script_code,
            "A URL da API Local padrao (localhost:8000) nao esta definida no script JS."
        )

    def test_integration_api_ollama_fallback(self):
        """4.2 Verifica a logica de fallback da API local para o Ollama quando offline."""
        script_code = self.parser.script_content
        
        # No JS, a funcao sendMessage deve inspecionar se state.apiOnline esta ativo.
        # Se sim, chama f"{state.apiUrl}/api/chat", caso contrario fallback f"{state.ollamaUrl}/api/chat".
        self.assertIn(
            "state.apiOnline", script_code, 
            "A propriedade state.apiOnline nao e verificada para controle de fluxo da API."
        )
        
        # Validação do fluxo condicional (se contem ambos os endpoints de envio de chat)
        self.assertTrue(
            "/api/chat" in script_code,
            "O script nao realiza chamadas ao endpoint de chat (/api/chat)."
        )
        
        # Verifica se o endpoint de fallback do Ollama e a API local estao descritos no fluxo
        self.assertIn("state.apiUrl", script_code, "A URL de integracao 'state.apiUrl' nao e referenciada.")
        self.assertIn("state.ollamaUrl", script_code, "A URL de fallback 'state.ollamaUrl' nao e referenciada.")


if __name__ == "__main__":
    unittest.main()
