# nome do arquivo: rpa_chatgpt_com_br_executor.py
"""
Executor RPA especializado para interagir com o site chatgpt.com.br,
usando o framework do rpa_core.
"""

import logging
from rpa_core import AIExecutorFramework, smart_finder, response_monitor, adaptive_timeout

logger = logging.getLogger(__name__)

class ChatGPTComBrExecutor(AIExecutorFramework):
    """Executor que sabe os detalhes de como interagir com chatgpt.com.br."""
    
    def __init__(self):
        # O 'ai_type' aqui é crucial, ele será usado pelo smart_finder
        super().__init__('chatgpt_com_br')
        self.url = "https://chatgpt.com.br/"
        logger.info("Instância do ChatGPTComBrExecutor (Playwright) criada.")

    def _is_on_correct_page(self) -> bool:
        if not self.page: return False
        try:
            return "chatgpt.com.br" in self.page.url
        except Exception as e:
            logger.warning(f"{self.ai_type} Executor: Erro ao verificar página: {e}")
            return False

    def _navigate_to_ai_page(self) -> bool:
        return self.browser_manager.navigate_safely(self.url, wait_for_load=True)

    def _wait_and_extract_response(self) -> str:
        """
        Lógica de espera e extração específica para o chatgpt.com.br.
        Ele espera por uma nova mensagem da IA e monitora sua estabilização.
        """
        logger.info(f"Aguardando resposta de {self.ai_type}...")

        # Aguarda um novo elemento de mensagem da IA aparecer no DOM
        # O seletor para isso está no rpa_core -> AdvancedSmartElementFinder
        response_element = smart_finder.find_element(
            self.page, self.ai_type, 'ultima_mensagem_ia', 
            timeout_ms=adaptive_timeout.get_timeout()
        )
        
        if not response_element:
            raise Exception("Elemento de resposta da IA não foi encontrado na página.")
            
        # Usa o monitor inteligente para esperar a resposta completa (streaming)
        response_text = response_monitor.wait_for_complete_response(
            self.page, self.ai_type, response_element, 
            timeout_s=180 # Timeout de 3 minutos
        )
        
        return response_text

def enviar_prompt_chat_com_br_sync(prompt: str, **kwargs) -> dict:
    """Função pública para ser chamada pelo RPAManager."""
    executor = ChatGPTComBrExecutor()
    return executor.execute_prompt(prompt, **kwargs)