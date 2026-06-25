
# nome do arquivo: atena_visao.py
"""
Módulo de Visão da Atena - Permite que a assistente "veja" a tela do usuário.
"""
import os
import io
import logging
import asyncio
from typing import Optional
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# --- Dependências de Terceiros ---
import google.generativeai as genai
from PIL import Image
import pyautogui

# Configuração do Logger
logger = logging.getLogger(__name__)

class AtenaVisionSystem:
    """
    Sistema que encapsula a capacidade da Atena de analisar o conteúdo visual da tela.
    """
    def __init__(self):
        """
        Inicializa o sistema de visão, configurando a API do Google Gemini.
        """
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            logger.critical("A variável de ambiente GOOGLE_API_KEY não foi definida. O módulo de visão não funcionará.")
            raise ValueError("API Key do Google não encontrada.")
        
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-pro-vision')
        logger.info("Sistema de Visão da Atena inicializado com o modelo Gemini Pro Vision.")

    async def _take_screenshot(self) -> Image.Image:
        """
        Tira uma screenshot da tela de forma assíncrona.
        """
        loop = asyncio.get_event_loop()
        # pyautogui.screenshot() é síncrono, então o executamos em um executor de thread
        # para não bloquear o loop de eventos principal da aplicação.
        screenshot = await loop.run_in_executor(None, pyautogui.screenshot)
        return screenshot

    async def see_and_assist(self, prompt: str) -> str:
        """
        Captura a tela, envia para o modelo de visão junto com um prompt e retorna a análise.

        Args:
            prompt: A pergunta do usuário sobre o que está na tela.

        Returns:
            A resposta de texto gerada pelo modelo de IA.
        """
        if not self.api_key:
            return "Erro: A chave da API do Google não foi configurada. Não consigo usar minha visão."

        logger.info(f"Recebido prompt visual: '{prompt}'")
        
        try:
            # 1. Capturar a tela
            logger.info("Capturando a tela...")
            screenshot = await self._take_screenshot()
            
            # 2. Preparar a imagem para a API sem salvar em disco
            img_byte_arr = io.BytesIO()
            screenshot.save(img_byte_arr, format='PNG')
            
            # A API do Gemini espera um objeto PIL.Image, então podemos usar a screenshot diretamente
            image_part = screenshot

            # 3. Enviar para a API do Gemini
            logger.info("Enviando imagem e prompt para o Gemini Vision...")
            # O prompt para o modelo é uma lista contendo o texto e a imagem
            response = await self.model.generate_content_async([prompt, image_part])
            
            # 4. Processar e retornar a resposta
            logger.info("Resposta recebida do Gemini Vision.")
            return response.text

        except Exception as e:
            logger.error(f"Ocorreu um erro no sistema de visão: {e}", exc_info=True)
            return f"Desculpe, ocorreu um erro enquanto eu tentava analisar a tela: {e}"

# Exemplo de como usar (para testes diretos)
async def main():
    print("--- Teste do Módulo de Visão da Atena ---")
    # Para este teste funcionar, defina a variável de ambiente GOOGLE_API_KEY
    if not os.getenv("GOOGLE_API_KEY"):
        print("Por favor, defina a variável de ambiente GOOGLE_API_KEY para executar o teste.")
        return
        
    vision_system = AtenaVisionSystem()
    try:
        # Dê um tempo para você mudar para a tela que quer analisar
        print("Você tem 5 segundos para ir para a tela que deseja analisar...")
        await asyncio.sleep(5)
        
        analysis = await vision_system.see_and_assist("Descreva o que você vê nesta tela.")
        print("\n--- Análise da Tela ---")
        print(analysis)
        print("""-----------------------
""")
        
    except ValueError as e:
        print(f"Erro de configuração: {e}")
    except Exception as e:
        print(f"Um erro inesperado ocorreu: {e}")

if __name__ == "__main__":
    # Para executar este teste:
    # 1. Instale as dependências: pip install google-generativeai pillow pyautogui
    # 2. Defina a sua chave de API: export GOOGLE_API_KEY='SUA_CHAVE_AQUI' (no Linux/macOS)
    #    ou set GOOGLE_API_KEY=SUA_CHAVE_AQUI (no Windows)
    # 3. Execute o script: python atena_visao.py
    asyncio.run(main())
