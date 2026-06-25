# nome do arquivo: rpa_agentes.py (v6.2 - Playwright Architecture Unificada)
"""
Módulo Central de Agentes RPA, agora usando exclusivamente o framework Playwright
do atena_rpa_core para máxima robustez e consistência.
"""

import logging
from urllib.parse import urlparse
from typing import Dict, Any, Optional

# --- Imports do nosso Ecossistema ---
from advanced_rpa_core import AdvancedAIExecutorFramework, IntelligentBrowserManager

# Logger para este módulo
logger = logging.getLogger(__name__)

# ==============================================================================
# CLASSES DE EXECUTORES (Baseadas em Playwright)
# ==============================================================================

class ChatGPTExecutor(AdvancedAIExecutorFramework):
    """Executor especializado para ChatGPT/OpenAI usando Playwright."""
    def __init__(self):
        super().__init__('chatgpt')
        self.current_url = 'https://chat.openai.com/' # Specific URL for ChatGPT
        logger.info("Instância do ChatGPTExecutor (Playwright) criada.")

    async def _navigate_to_ai_page(self) -> bool:
        return await self.browser_manager.navigate_safely(self.current_url, wait_for_load=True)

    async def _is_on_correct_page(self) -> bool:
        if not self.page: return False
        try:
            return "chat.openai.com" in self.page.url
        except Exception as e:
            logger.warning(f"ChatGPTExecutor: Erro ao verificar página: {e}")
            return False

class GeminiExecutor(AdvancedAIExecutorFramework):
    """Executor especializado para Google Gemini usando Playwright."""
    def __init__(self):
        super().__init__('gemini')
        self.current_url = 'https://gemini.google.com/app' # Specific URL for Gemini
        logger.info("Instância do GeminiExecutor (Playwright) criada.")

    async def _navigate_to_ai_page(self) -> bool:
        return await self.browser_manager.navigate_safely(self.current_url, wait_for_load=True)

    async def _is_on_correct_page(self) -> bool:
        if not self.page: return False
        try:
            return "gemini.google.com" in self.page.url
        except Exception as e:
            logger.warning(f"GeminiExecutor: Erro ao verificar página: {e}")
            return False

class ClaudeExecutor(AdvancedAIExecutorFramework):
    """Executor especializado para Claude usando Playwright."""
    def __init__(self):
        super().__init__('claude')
        self.current_url = 'https://claude.ai/chats' # Specific URL for Claude
        logger.info("Instância do ClaudeExecutor (Playwright) criada.")

    async def _is_on_correct_page(self) -> bool:
        if not self.page: return False
        try:
            return "claude.ai" in self.page.url
        except Exception as e:
            logger.warning(f"ClaudeExecutor: Erro ao verificar página: {e}")
            return False

    async def _navigate_to_ai_page(self) -> bool:
        return await self.browser_manager.navigate_safely(self.current_url, wait_for_load=True)


# ==============================================================================
# RPA MANAGER (O Coração da Orquestração)
# ==============================================================================

class RPAManager:
    """Gerencia o ciclo de vida e a execução de todos os agentes RPA."""
    def __init__(self):
        self._executor_classes = {
            "chatgpt-rpa": ChatGPTExecutor,
            "gemini-rpa": GeminiExecutor,
            "claude-rpa": ClaudeExecutor,
        }
        self._executor_instances: Dict[str, AdvancedAIExecutorFramework] = {}
        logger.info("RPAManager inicializado. Pronto para gerenciar agentes Playwright.")

    async def _get_executor_instance(self, ia_alvo: str) -> Optional[AdvancedAIExecutorFramework]:
        if ia_alvo not in self._executor_instances:
            logger.info(f"Primeira solicitação para '{ia_alvo}'. Criando nova instância do executor...")
            executor_class = self._executor_classes.get(ia_alvo)
            if executor_class:
                self._executor_instances[ia_alvo] = executor_class()
                # Initialize the executor's browser manager here
                await self._executor_instances[ia_alvo]._initialize_advanced_browser()
            else:
                logger.error(f"Nenhuma classe de executor encontrada para o alvo: {ia_alvo}")
                return None
        return self._executor_instances[ia_alvo]

    async def execute_on_ai_enhanced(self, ia_alvo: str, prompt: str, **kwargs) -> Dict[str, Any]:
        logger.info(f"RPAManager: Recebida tarefa para '{ia_alvo}'")
        executor = await self._get_executor_instance(ia_alvo)
        
        if not executor:
            return {"success": False, "error": f"IA alvo '{ia_alvo}' não é suportada."}

        try:
            # A chamada ao executor.execute_prompt_advanced agora é robusta e usa Playwright
            return await executor.execute_prompt_advanced(prompt, **kwargs)
        except Exception as e:
            logger.critical(f"Erro CRÍTICO na tarefa para '{ia_alvo}': {e}", exc_info=True)
            return {"success": False, "error": f"Erro fatal no RPAManager: {e}"}

    async def cleanup_all(self):
        logger.info("RPAManager: Iniciando limpeza de todos os recursos de RPA...")
        for nome, instancia in self._executor_instances.items():
            try:
                await instancia.cleanup()
            except Exception as e:
                logger.error(f"Erro ao limpar o executor '{nome}': {e}")
        logger.info("RPAManager: Limpeza concluída.")

    def get_available_agents(self) -> list:
        return list(self._executor_classes.keys())