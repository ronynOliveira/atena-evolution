# nome do arquivo: atena_rpa_engine_avancado.py
# Versão: 2.0 - Cognitive Web Interaction
"""
Este arquivo representa o motor de RPA avançado da Atena, integrando
análise de conteúdo web, detecção contextual de elementos, processamento
de linguagem natural com LLMs locais e um orquestrador de automação.
"""

# --- Imports Essenciais ---
import logging
import os
import uuid
import re
import time
import json
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional, Any
from enum import Enum
from pathlib import Path

# --- Imports de Terceiros ---
import yaml
from pydantic import BaseModel, Field as PydanticField
from bs4 import BeautifulSoup

# --- Imports do Playwright ---
from playwright.sync_api import sync_playwright, Page, ElementHandle, Browser, Playwright

# --- Configuração do Logger ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(module)s:%(funcName)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.FileHandler('atena_rpa_engine.log', mode='w'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ==============================================================================
# SEÇÃO 1: CONFIGURAÇÃO E CONTEXTO DE EXECUÇÃO
# ==============================================================================

class ConfigManager:
    """Gerenciador centralizado de configurações."""
    def __init__(self, config_path: str = "rpa_config.yaml"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self._validate_config()

    def _load_config(self) -> Dict[str, Any]:
        default_config = {
            "browser": {"timeout": 30000, "retry_attempts": 3, "headless": False},
            "llm": {"model_path": "models/llama-2-7b-chat.Q4_0.gguf", "executable_path": "./llama.cpp/main"},
            "monitoring": {"log_level": "INFO"},
            "security": {"token_expiry": 3600}
        }
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                file_config = yaml.safe_load(f)
                if file_config:
                    # Deep merge logic could be added here if needed
                    default_config.update(file_config)
        return default_config

    def _validate_config(self):
        if "browser" not in self.config or "timeout" not in self.config["browser"]:
            raise ValueError("Configuração 'browser.timeout' é obrigatória.")
        if "llm" not in self.config or "model_path" not in self.config["llm"]:
            raise ValueError("Configuração 'llm.model_path' é obrigatória.")

    def get(self, key_path: str, default: Any = None) -> Any:
        path = key_path.split('.')
        value = self.config
        try:
            for key in path:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default

class ExecutionContext(BaseModel):
    """Contexto de execução com metadados completos."""
    session_id: str = PydanticField(default_factory=lambda: str(uuid.uuid4()))
    user_id: Optional[str] = None
    ai_type: str
    timestamp: datetime = PydanticField(default_factory=datetime.now)
    
    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


# ==============================================================================
# SEÇÃO 2: GERENCIAMENTO DE SESSÃO DO NAVEGADOR
# ==============================================================================

class BrowserSessionManager:
    """Gerencia o ciclo de vida de uma instância de navegador Playwright."""
    def __init__(self, config: ConfigManager):
        self.config = config
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        logger.info("BrowserSessionManager inicializado.")

    def start_session(self) -> Page:
        """Inicia o Playwright, lança um navegador e retorna uma nova página."""
        if self.browser and self.browser.is_connected():
            logger.info("Reutilizando sessão de navegador existente.")
            return self.browser.new_page()

        try:
            self.playwright = sync_playwright().start()
            browser_config = self.config.get('browser', {})
            self.browser = self.playwright.chromium.launch(
                headless=browser_config.get('headless', False),
                timeout=browser_config.get('timeout', 30000)
            )
            logger.info("Nova sessão de navegador iniciada com sucesso.")
            return self.browser.new_page()
        except Exception as e:
            logger.critical(f"Falha crítica ao iniciar a sessão do navegador: {e}")
            raise

    def close_session(self):
        """Fecha o navegador e o Playwright de forma segura."""
        if self.browser and self.browser.is_connected():
            self.browser.close()
            self.browser = None
        if self.playwright:
            self.playwright.stop()
            self.playwright = None
        logger.info("Sessão do navegador finalizada.")


# ==============================================================================
# SEÇÃO 3: ANÁLISE WEB INTELIGENTE (SEM LLM)
# ==============================================================================

class WebContentAnalyzer:
    """Análise inteligente de conteúdo web sem LLM externo."""
    
    def analyze_page_structure(self, page: Page) -> Dict[str, Any]:
        """Analisa a estrutura da página e identifica elementos interativos."""
        try:
            html_content = page.content()
            soup = BeautifulSoup(html_content, 'html.parser')
            
            interactive_elements = {
                'forms': self._analyze_forms(soup),
                'buttons': self._analyze_buttons(soup),
                'links': self._analyze_links(soup),
                'inputs': self._analyze_inputs(soup)
            }
            
            return {
                'interactive_elements': interactive_elements,
                'page_type': self._infer_page_type(soup)
            }
        except Exception as e:
            logger.error(f"Erro ao analisar a estrutura da página: {e}")
            return {}

    def _analyze_forms(self, soup: BeautifulSoup) -> List[Dict]:
        forms = []
        for form in soup.find_all('form'):
            form_data = {'action': form.get('action', ''), 'method': form.get('method', 'get'), 'fields': []}
            for field in form.find_all(['input', 'textarea', 'select']):
                form_data['fields'].append({
                    'type': field.get('type', field.name), 'name': field.get('name', ''),
                    'placeholder': field.get('placeholder', ''), 'label': self._find_label_for_field(field, soup),
                    'selector': self._generate_selector(field)
                })
            forms.append(form_data)
        return forms

    def _analyze_buttons(self, soup: BeautifulSoup) -> List[Dict]:
        buttons = []
        for button in soup.find_all('button'):
            buttons.append({'text': button.get_text(strip=True), 'selector': self._generate_selector(button)})
        return buttons

    def _analyze_links(self, soup: BeautifulSoup) -> List[Dict]:
        links = []
        for link in soup.find_all('a', href=True):
            links.append({'text': link.get_text(strip=True), 'href': link['href'], 'selector': self._generate_selector(link)})
        return links

    def _analyze_inputs(self, soup: BeautifulSoup) -> List[Dict]:
        inputs = []
        for inp in soup.find_all('input'):
            inputs.append({
                'type': inp.get('type', 'text'), 'name': inp.get('name', ''),
                'placeholder': inp.get('placeholder', ''), 'label': self._find_label_for_field(inp, soup),
                'selector': self._generate_selector(inp)
            })
        return inputs

    def _find_label_for_field(self, field, soup) -> str:
        field_id = field.get('id')
        if field_id:
            label = soup.find('label', {'for': field_id})
            if label: return label.get_text(strip=True)
        parent_label = field.find_parent('label')
        if parent_label: return parent_label.get_text(strip=True)
        return ""

    def _generate_selector(self, element) -> str:
        if element.get('id'): return f"#{element['id']}"
        if element.get('name'): return f"{element.name}[name='{element['name']}']"
        if element.get('class'): return f"{element.name}.{'.'.join(element['class'])}"
        return element.name

    def _infer_page_type(self, soup: BeautifulSoup) -> str:
        if soup.find('form', {'id': 'login_form'}) or soup.find('form', action=re.compile(r'login')): return "login_page"
        if soup.find('input', {'name': 'q'}) or soup.find('input', {'type': 'search'}): return "search_page"
        if soup.find('main') and soup.find('article'): return "article_page"
        return "generic"


class ContextualElementDetector:
    """Detecta elementos baseado no contexto e intenção do usuário."""
    def __init__(self):
        self.intent_patterns = {
            'search_box': ['input[type="search"]', 'input[name*="q"]', 'textarea[name*="q"]', 'input[aria-label*="search" i]', 'input[title*="search" i]'],
            'search_button': ['button[type="submit"]', 'input[type="submit"]', 'button[aria-label*="search" i]'],
            'login_user': ['input[type="email"]', 'input[type="text"][name*="user"]'],
            'login_pass': ['input[type="password"]'],
        }

    def find_element_by_intent(self, page: Page, intent_key: str, context_description: str) -> Optional[str]:
        """Encontra elemento baseado na intenção (chave) e descrição de fallback."""
        if intent_key in self.intent_patterns:
            for selector in self.intent_patterns[intent_key]:
                try:
                    element = page.query_selector(selector)
                    if element and element.is_visible():
                        logger.info(f"Elemento para intenção '{intent_key}' encontrado com seletor: {selector}")
                        return selector
                except Exception:
                    continue
        
        logger.warning(f"Nenhum seletor padrão encontrado para '{intent_key}'. Usando fallback de texto: '{context_description}'")
        return f"text=/{context_description}/i"


# ==============================================================================
# SEÇÃO 4: AGENTE RPA APRIMORADO
# ==============================================================================

class EnhancedAtenaRPAAgent:
    """Versão aprimorada do agente RPA com capacidades avançadas."""
    def __init__(self, config: ConfigManager):
        self.config = config
        self.session_manager = BrowserSessionManager(config)
        self.content_analyzer = WebContentAnalyzer()
        self.element_detector = ContextualElementDetector()
        
        self.page: Optional[Page] = None
        self.execution_context: Optional[ExecutionContext] = None
        self.page_context: Dict[str, Any] = {}
        logger.info("Agente EnhancedAtenaRPA inicializado.")

    def initialize_session(self, context: ExecutionContext):
        self.page = self.session_manager.start_session()
        self.execution_context = context
        logger.info(f"Sessão RPA iniciada com ID: {context.session_id}")

    def analyze_current_page(self) -> Dict[str, Any]:
        """Analisa a página atual e armazena contexto."""
        if not self.page: return {}
        
        content_analysis = self.content_analyzer.analyze_page_structure(self.page)
        self.page_context = {
            'url': self.page.url, 'title': self.page.title(),
            'content_analysis': content_analysis,
            'timestamp': datetime.now().isoformat()
        }
        return self.page_context
    
    def smart_interaction(self, intent: str, target_description: str, value: Optional[str] = None) -> Dict[str, Any]:
        """Interação inteligente baseada em intenção e contexto."""
        if not self.page: return {"success": False, "error": "Página não está disponível."}
        
        try:
            selector = self.element_detector.find_element_by_intent(self.page, target_description, target_description)
            if not selector:
                return {"success": False, "error": f"Elemento não pôde ser determinado para: {target_description}"}

            if intent == 'type' and value:
                self.page.fill(selector, value)
                logger.info(f"Texto '{value}' inserido em '{selector}' (descrição: {target_description})")
            elif intent == 'click':
                self.page.click(selector)
                logger.info(f"Clicou em elemento '{selector}' (descrição: {target_description})")
            elif intent == 'extract':
                extracted_text = self.page.text_content(selector)
                return {"success": True, "extracted_text": extracted_text}
            else:
                return {"success": False, "error": f"Intenção de interação '{intent}' não suportada."}
            
            return {"success": True, "action": intent, "target_selector": selector}
        except Exception as e:
            logger.error(f"Erro na interação inteligente ('{intent}' em '{target_description}'): {e}")
            return {"success": False, "error": str(e)}

    def cleanup(self):
        self.session_manager.close_session()
        self.page = None
        logger.info("Sessão do Agente AtenaRPA finalizada.")

    async def execute_task(self, task_description: str) -> Dict[str, Any]:
        """
        Executa uma tarefa RPA completa baseada em uma descrição de texto.
        Usa o LLM local para interpretar a intenção e planejar as ações.
        """
        logger.info(f"Executando tarefa RPA: {task_description}")
        
        # 1. Processar a descrição da tarefa com o LLM local
        local_llm_processor = LocalLLMProcessor(self.config)
        parsed_intent = local_llm_processor.process_user_input(task_description)
        
        if not parsed_intent.action_plan:
            logger.warning(f"Nenhum plano de ação gerado para a tarefa: {task_description}")
            return {"success": False, "error": "Nenhum plano de ação gerado."}

        # 2. Inicializar a sessão do navegador se ainda não estiver ativa
        if not self.page:
            # Em um cenário real, o ExecutionContext viria do contexto da requisição.
            # Para este método, criamos um contexto dummy.
            dummy_context = ExecutionContext(session_id=str(uuid.uuid4()), ai_type="rpa_task_execution")
            self.initialize_session(dummy_context)
            
        # 3. Executar o plano de ação
        action_planner = ActionPlanner(self) # Passa a própria instância do RPA Agent
        execution_result = action_planner.execute_action_plan(parsed_intent)
        
        # 4. Limpar a sessão do navegador após a execução
        self.cleanup()

        return {
            "success": execution_result.get("success", False),
            "details": execution_result.get("results", []),
            "parsed_intent": asdict(parsed_intent) # Converte ParsedIntent para dict
        }


# ==============================================================================
# SEÇÃO 5: NLU COM LLM LOCAL E PLANEJAMENTO DE AÇÕES
# ==============================================================================

class IntentType(Enum):
    WEB_SEARCH = "web_search"
    WEB_NAVIGATION = "web_navigation"
    FORM_FILLING = "form_filling"
    DATA_EXTRACTION = "data_extraction"
    TASK_AUTOMATION = "task_automation"

@dataclass
class ParsedIntent:
    intent: IntentType
    entities: Dict[str, Any]
    confidence: float
    raw_text: str
    action_plan: List[Dict[str, Any]] = field(default_factory=list)

class LocalLLMProcessor:
    """Processador de linguagem natural usando LLMs locais."""
    def __init__(self, config: ConfigManager):
        self.model_path = config.get("llm.model_path")
        self.executable_path = config.get("llm.executable_path")
        self.system_prompt = self._load_system_prompt()
        
    def _load_system_prompt(self) -> str:
        return """
Você é um assistente especializado em interpretar comandos de usuário e convertê-los em ações programáticas para automação web.

Sua tarefa é analisar o texto do usuário e retornar APENAS um JSON válido com:
- "intent": tipo de intenção (ex: "web_search", "web_navigation").
- "entities": entidades extraídas (ex: {"search_term": "...", "website": "google"}).
- "confidence": sua confiança na interpretação (0.0 a 1.0).
- "action_plan": uma lista de passos sequenciais. Cada passo é um dicionário com "action", "target" e opcionalmente "value".

Exemplos:
Entrada: "Pesquise por receitas de bolo no Google"
Saída: {"intent": "web_search", "entities": {"search_term": "receitas de bolo", "search_engine": "google"}, "confidence": 0.95, "action_plan": [{"action": "navigate", "url": "https://www.google.com"}, {"action": "type", "target": "search_box", "value": "receitas de bolo"}, {"action": "click", "target": "search_button"}]}

Entrada: "Vá para o site da Amazon e procure por livros de Python"
Saída: {"intent": "web_navigation", "entities": {"website": "amazon", "search_term": "livros de Python"}, "confidence": 0.9, "action_plan": [{"action": "navigate", "url": "https://www.amazon.com"}, {"action": "type", "target": "search_box", "value": "livros de Python"}, {"action": "click", "target": "search_button"}]}

Responda APENAS com o JSON, sem explicações adicionais.
"""

    def process_user_input(self, user_text: str) -> ParsedIntent:
        full_prompt = f"{self.system_prompt}\n\nEntrada: \"{user_text}\"\nSaída:"
        llm_output = self._call_local_llm(full_prompt)
        
        try:
            # Limpa a saída do LLM para garantir que seja um JSON válido
            json_str = llm_output[llm_output.find('{'):llm_output.rfind('}')+1]
            parsed = json.loads(json_str)
            return ParsedIntent(
                intent=IntentType(parsed['intent']),
                entities=parsed['entities'],
                confidence=parsed['confidence'],
                raw_text=user_text,
                action_plan=parsed['action_plan']
            )
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Erro ao parsear resposta do LLM: {e}. Saída recebida: '{llm_output}'")
            return self._fallback_interpretation(user_text)

    def _call_local_llm(self, prompt: str) -> str:
        """Chama LLM local. Inclui MOCK para testes sem o executável."""
        if not Path(self.executable_path).exists():
            logger.warning(f"Executável do LLM não encontrado em '{self.executable_path}'. Usando resposta MOCK.")
            return self._get_mock_response(prompt)
        
        try:
            cmd = [self.executable_path, "-m", self.model_path, "-p", prompt, "-n", "512", "--temp", "0.1"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, check=True)
            return result.stdout.strip()
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError) as e:
            logger.error(f"Erro ao chamar LLM local: {e}")
            return ""

    def _get_mock_response(self, prompt: str) -> str:
        """Fornece uma resposta JSON simulada para fins de teste."""
        if "automação com Python" in prompt:
            return json.dumps({
                "intent": "web_search",
                "entities": {"search_term": "automação com Python", "search_engine": "google"},
                "confidence": 0.98,
                "action_plan": [
                    {"action": "navigate", "url": "https://www.google.com"},
                    {"action": "type", "target": "search_box", "value": "automação com Python"},
                    {"action": "click", "target": "search_button"}
                ]
            })
        return "{}"

    def _fallback_interpretation(self, user_text: str) -> ParsedIntent:
        """Interpretação de fallback baseada em regras simples."""
        text_lower = user_text.lower()
        if any(word in text_lower for word in ['pesquisar', 'buscar', 'procurar']):
            term = re.sub(r'(pesquisar|buscar|procurar)\s*(por)?\s*', '', text_lower, 1).strip()
            return ParsedIntent(
                intent=IntentType.WEB_SEARCH,
                entities={"search_term": term}, confidence=0.6, raw_text=user_text,
                action_plan=[
                    {"action": "navigate", "url": "https://www.google.com"},
                    {"action": "type", "target": "search_box", "value": term},
                    {"action": "click", "target": "search_button"}
                ]
            )
        return ParsedIntent(
            intent=IntentType.WEB_SEARCH,
            entities={"search_term": user_text},
            confidence=0.4, # Lower confidence as it's a fallback
            raw_text=user_text,
            action_plan=[
                {"action": "navigate", "url": "https://www.google.com"},
                {"action": "type", "target": "search_box", "value": user_text},
                {"action": "click", "target": "search_button"}
            ]
        )

class ActionPlanner:
    """Planeja e executa ações baseadas na intenção interpretada."""
    def __init__(self, rpa_agent: EnhancedAtenaRPAAgent):
        self.rpa_agent = rpa_agent
        self.action_mapping = {
            'navigate': self._execute_navigation,
            'type': self._execute_typing,
            'click': self._execute_click,
        }

    def execute_action_plan(self, parsed_intent: ParsedIntent) -> Dict[str, Any]:
        results = []
        for step in parsed_intent.action_plan:
            action_type = step.get('action')
            if action_type in self.action_mapping:
                result = self.action_mapping[action_type](step)
                results.append(result)
                if not result.get('success', False):
                    logger.error(f"Plano de ação interrompido devido a falha no passo: {step}")
                    break
            else:
                logger.warning(f"Ação não reconhecida no plano: {action_type}")
                results.append({'success': False, 'error': f'Ação não reconhecida: {action_type}'})

        return {
            'success': all(r.get('success', False) for r in results),
            'results': results
        }

    def _execute_navigation(self, step: Dict) -> Dict[str, Any]:
        url = step.get('url')
        if not url or not self.rpa_agent.page:
            return {'success': False, 'error': 'URL não especificada ou página indisponível'}
        try:
            self.rpa_agent.page.goto(url, wait_until="domcontentloaded")
            return {'success': True, 'action': 'navigate', 'url': url}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _execute_typing(self, step: Dict) -> Dict[str, Any]:
        return self.rpa_agent.smart_interaction('type', step.get('target', ''), step.get('value', ''))

    def _execute_click(self, step: Dict) -> Dict[str, Any]:
        return self.rpa_agent.smart_interaction('click', step.get('target', ''))


# ==============================================================================
# SEÇÃO 6: ORQUESTRADOR PRINCIPAL E PONTO DE ENTRADA
# ==============================================================================

class AtenaOrchestrator:
    """Orquestrador principal que conecta todos os módulos."""
    def __init__(self):
        self.config = ConfigManager()
        self.nlp_processor = LocalLLMProcessor(self.config)
        self.active_sessions: Dict[str, EnhancedAtenaRPAAgent] = {}

    def process_user_request(self, user_text: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Processa requisição do usuário de ponta a ponta."""
        # 1. Processa linguagem natural para obter plano de ação
        parsed_intent = self.nlp_processor.process_user_input(user_text)
        
        # 2. Obtém ou cria sessão RPA
        session_id = session_id or str(uuid.uuid4())
        if session_id not in self.active_sessions:
            rpa_agent = EnhancedAtenaRPAAgent(self.config)
            context = ExecutionContext(ai_type="user_request", session_id=session_id)
            rpa_agent.initialize_session(context)
            self.active_sessions[session_id] = rpa_agent
        
        rpa_agent = self.active_sessions[session_id]
        
        # 3. Executa plano de ação
        action_planner = ActionPlanner(rpa_agent)
        execution_result = action_planner.execute_action_plan(parsed_intent)
        
        # 4. Prepara resposta
        return {
            'session_id': session_id,
            'understood_intent': parsed_intent.intent.value,
            'confidence': parsed_intent.confidence,
            'entities_extracted': parsed_intent.entities,
            'action_plan': parsed_intent.action_plan,
            'execution_summary': execution_result
        }

    def cleanup_session(self, session_id: str):
        if session_id in self.active_sessions:
            self.active_sessions[session_id].cleanup()
            del self.active_sessions[session_id]
            logger.info(f"Sessão {session_id} finalizada e removida.")


if __name__ == '__main__':
    logger.info("--- INICIANDO TESTE DO MOTOR COGNITIVO RPA DA ATENA ---")
    
    orchestrator = AtenaOrchestrator()
    session_id = None
    
    try:
        # Simula uma requisição de usuário
        user_command = "Vá para o Google e pesquise por 'automação com Python'"
        logger.info(f"\n[COMANDO DO USUÁRIO]: \"{user_command}\"\n")
        
        # Processa a requisição com o orquestrador
        response = orchestrator.process_user_request(user_command)
        session_id = response.get('session_id')
        
        # Imprime a resposta de forma legível
        print("\n" + "="*50)
        print("      RESPOSTA DO ORQUESTRADOR DA ATENA")
        print("="*50)
        print(f"ID da Sessão: {response.get('session_id')}")
        print(f"Intenção Compreendida: {response.get('understood_intent')} (Confiança: {response.get('confidence')})")
        print(f"Entidades Extraídas: {json.dumps(response.get('entities_extracted'), indent=2)}")
        print("\n--- Plano de Ação Gerado ---")
        for i, step in enumerate(response.get('action_plan', []), 1):
            print(f"  Passo {i}: {step}")
        
        print("\n--- Resumo da Execução ---")
        summary = response.get('execution_summary', {})
        print(f"  Sucesso Geral: {summary.get('success')}")
        for i, result in enumerate(summary.get('results', []), 1):
            print(f"  Resultado Passo {i}: {result}")
        print("="*50)

        # Mantém o navegador aberto por alguns segundos para visualização
        if summary.get('success'):
            logger.info("\nTarefa executada. O navegador permanecerá aberto por 10 segundos.")
            time.sleep(10)
        
    except Exception as e:
        logger.critical(f"Ocorreu um erro fatal no teste: {e}", exc_info=True)
    finally:
        # Garante que a sessão seja encerrada
        if session_id:
            orchestrator.cleanup_session(session_id)
        logger.info("--- TESTE FINALIZADO ---")
