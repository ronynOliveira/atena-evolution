# nome do arquivo: rpa_core.py (v3.0 - Async Playwright Architecture)
import re
import asyncio
from typing import List, Dict, Optional, Any
from playwright.async_api import Page, ElementHandle, TimeoutError as PlaywrightTimeoutError, async_playwright, Browser
import time
import os
import logging
from datetime import datetime

# Configuração do Logger
logger = logging.getLogger(__name__)

# --- Classes de Gerenciamento e Utilitários ---

class IntelligentBrowserManager:
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.context = None
        self.page: Optional[Page] = None
        self.playwright = None

    async def initialize_browser(self, **kwargs) -> Page:
        if self.playwright is None:
            self.playwright = await async_playwright().start()
        if self.browser is None:
            self.browser = await self.playwright.chromium.launch(headless=False, **kwargs)
        if self.context is None:
            self.context = await self.browser.new_context()
        if self.page is None:
            self.page = await self.context.new_page()
        return self.page

    async def navigate_safely(self, url: str, wait_for_load: bool = True) -> bool:
        if self.page:
            try:
                await self.page.goto(url, wait_until='domcontentloaded' if wait_for_load else 'commit')
                return True
            except Exception as e:
                logger.error(f"Falha ao navegar para {url}: {e}")
                return False
        return False

    async def cleanup(self):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

class AdvancedSmartElementFinder:
    async def find_element(self, page: Page, ai_type: str, element_type: str, timeout_ms: int) -> Optional[ElementHandle]:
        selectors = {
            'campo_prompt': ['textarea[data-id="root"]', 'textarea[placeholder*="Message"]', 'textarea'],
            'ultima_mensagem_ia': ['div[data-testid*="conversation-turn"]:last-of-type .prose', 'div[data-message-author-role="assistant"]:last-of-type', 'div.markdown']
        }
        for selector in selectors.get(element_type, []):
            try:
                element = await page.wait_for_selector(selector, timeout=timeout_ms/len(selectors.get(element_type, [1])))
                if element:
                    return element
            except PlaywrightTimeoutError:
                continue
        return None

class SmartElementInteraction:
    async def safe_type(self, page: Page, element: ElementHandle, text: str, clear_first: bool = True) -> bool:
        try:
            if clear_first:
                await element.fill("")
            await element.type(text)
            return True
        except Exception as e:
            logger.error(f"Falha ao digitar no elemento: {e}")
            return False

class IntelligentResponseMonitor:
    async def wait_for_complete_response(self, page: Page, ai_type: str, response_element: ElementHandle, timeout_s: int) -> str:
        await asyncio.sleep(2) # Simula espera pela resposta
        return await response_element.inner_text() if response_element else "Resposta não encontrada"

class IntelligentAdaptiveTimeout:
    def get_timeout(self) -> int: return 20000
    def record_success(self, duration: float): pass
    def record_failure(self, f_type: str): pass

# Instâncias globais
smart_finder = AdvancedSmartElementFinder()
smart_interaction = SmartElementInteraction()
response_monitor = IntelligentResponseMonitor()
adaptive_timeout = IntelligentAdaptiveTimeout()

# --- Framework Principal do Executor de IA ---

class AIExecutorFramework:
    """
    Framework base para todos os executores de IA.
    Inclui coleta de evidências e lógica de inicialização robusta.
    """
    def __init__(self, ai_type: str):
        self.ai_type = ai_type
        self.browser_manager = IntelligentBrowserManager()
        self.page: Optional[Page] = None
        self.execution_metrics = {}

    async def execute_prompt(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Framework principal para execução de prompts com coleta de evidências."""
        start_time = time.time()
        try:
            logger.info(f"AIExecutor[{self.ai_type}]: Iniciando execução do prompt.")

            if not self.page:
                logger.info(f"AIExecutor[{self.ai_type}]: Página não existe. Inicializando novo navegador.")
                self.page = await self.browser_manager.initialize_browser(**kwargs.get('browser_config', {}))

            if not await self._is_on_correct_page():
                logger.info(f"AIExecutor[{self.ai_type}]: Não está na página correta. Navegando...")
                if not await self._navigate_to_ai_page():
                    raise Exception("Falha ao navegar para a página da IA")
            else:
                logger.info(f"AIExecutor[{self.ai_type}]: Já está na página correta. Prosseguindo.")

            prompt_field = await smart_finder.find_element(
                self.page, self.ai_type, 'campo_prompt',
                timeout_ms=adaptive_timeout.get_timeout()
            )
            if not prompt_field:
                raise Exception(f"Campo de prompt para '{self.ai_type}' não encontrado.")

            if not await smart_interaction.safe_type(self.page, prompt_field, prompt):
                raise Exception("Falha ao inserir prompt no campo.")

            await self._submit_prompt()

            response = await self._wait_and_extract_response()

            execution_time = time.time() - start_time
            self._update_metrics(True, execution_time)

            return {
                'success': True,
                'response': response,
                'execution_time_s': execution_time,
                'ai_type': self.ai_type,
                'prompt': prompt
            }
        except Exception as e:
            execution_time = time.time() - start_time
            self._update_metrics(False, execution_time)
            logger.error(f"AIExecutor[{self.ai_type}]: Erro durante execução: {e}", exc_info=True)

            failure_evidence = await self.collect_failure_evidence(e)

            return {
                'success': False,
                'error': str(e),
                'execution_time_s': execution_time,
                'ai_type': self.ai_type,
                'prompt': prompt,
                'failure_evidence': failure_evidence
            }

    async def collect_failure_evidence(self, error: Exception) -> dict:
        """Coleta evidências no momento da falha para diagnóstico."""
        if not self.page:
             logger.error("Não foi possível coletar evidências: a página (page) não está inicializada.")
             return {
                 "timestamp": datetime.now().isoformat(),
                 "error_type": type(error).__name__,
                 "error_message": f"Página não inicializada. Erro original: {error}",
                 "collection_error": "Page object was None."
             }
        try:
            timestamp = datetime.now().isoformat()
            screenshot_folder = "screenshots"
            os.makedirs(screenshot_folder, exist_ok=True)

            safe_timestamp = timestamp.replace(':', '-').replace('.', '_')
            screenshot_path = os.path.join(screenshot_folder, f"failure_{self.ai_type}_{safe_timestamp}.png")

            await self.page.screenshot(path=screenshot_path)
            html_content = await self.page.content()

            evidence = {
                "timestamp": timestamp,
                "error_type": type(error).__name__,
                "error_message": str(error),
                "screenshot_path": screenshot_path,
                "html_content": html_content
            }
            logger.info(f"Evidências da falha coletadas e salvas em {screenshot_path}")
            return evidence
        except Exception as e_collect:
            logger.error(f"Erro CRÍTICO ao coletar evidências da falha: {e_collect}", exc_info=True)
            return {
                "timestamp": datetime.now().isoformat(),
                "error_type": type(error).__name__,
                "error_message": str(error),
                "collection_error": str(e_collect)
            }

    async def cleanup(self):
        """Limpeza de recursos do browser."""
        if self.browser_manager:
            await self.browser_manager.cleanup()

    def _update_metrics(self, success: bool, execution_time: float):
        """Atualiza métricas de execução."""
        pass

    # --- Métodos a serem implementados pelas classes filhas ---
    async def _is_on_correct_page(self) -> bool:
        raise NotImplementedError
    async def _navigate_to_ai_page(self) -> bool:
        raise NotImplementedError
    async def _submit_prompt(self):
        await self.page.keyboard.press('Enter')
    async def _wait_and_extract_response(self) -> str:
        raise NotImplementedError
