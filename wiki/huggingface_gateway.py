# nome do arquivo: huggingface_gateway.py
"""
Gateway centralizado para interagir com a API e os modelos do Hugging Face.
Gerencia o carregamento, cache e execução de modelos para diferentes tarefas.
"""
import logging
from typing import Dict, List, Any
from transformers import pipeline
from diffusers import DiffusionPipeline
import torch

logger = logging.getLogger(__name__)

class HuggingFaceGateway:
    _instance = None
    _model_cache: Dict[str, Any] = {} # Cache para os modelos carregados

    def __new__(cls, *args, **kwargs):
        """Implementa o padrão Singleton para evitar recarregar modelos."""
        if not cls._instance:
            cls._instance = super(HuggingFaceGateway, cls).__new__(cls, *args, **kwargs)
            logger.info("Criando instância única do HuggingFaceGateway.")
        return cls._instance

    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"HuggingFaceGateway operando no dispositivo: {self.device}")

    def _load_pipeline(self, task: str, model: str):
        """Carrega um pipeline do Hugging Face, usando cache."""
        cache_key = f"{task}_{model}"
        if cache_key not in self._model_cache:
            logger.info(f"Carregando modelo '{model}' para a tarefa '{task}'... (Isso pode levar um tempo na primeira vez)")
            try:
                self._model_cache[cache_key] = pipeline(task, model=model, device=self.device)
                logger.info(f"Modelo '{model}' carregado e armazenado em cache.")
            except Exception as e:
                logger.error(f"Falha ao carregar o modelo '{model}': {e}")
                return None
        return self._model_cache[cache_key]
        
    def _load_diffusers_pipeline(self, model: str):
        """Carrega um pipeline de difusão, usando cache."""
        if model not in self._model_cache:
            logger.info(f"Carregando modelo de difusão '{model}'...")
            try:
                # Carrega o pipeline e move para o dispositivo correto
                pipe = DiffusionPipeline.from_pretrained(model)
                pipe = pipe.to(self.device)
                self._model_cache[model] = pipe
                logger.info(f"Modelo de difusão '{model}' carregado e armazenado em cache.")
            except Exception as e:
                logger.error(f"Falha ao carregar o modelo de difusão '{model}': {e}")
                return None
        return self._model_cache[model]

    def summarize_text(self, text: str, model: str = "facebook/bart-large-cnn") -> str:
        """Gera um resumo de um texto."""
        summarizer = self._load_pipeline("summarization", model)
        if not summarizer: return "Não foi possível gerar o resumo."
        
        try:
            # A biblioteca pode retornar uma lista, pegamos o primeiro elemento.
            summary = summarizer(text, max_length=150, min_length=30, do_sample=False)
            return summary[0]['summary_text']
        except Exception as e:
            logger.error(f"Erro ao sumarizar texto: {e}")
            return f"Erro na sumarização: {e}"

    def translate_text(self, text: str, target_language: str = "ja", model: str = "Helsinki-NLP/opus-mt-en-jap") -> str:
        """Traduz um texto para outro idioma."""
        translator = self._load_pipeline(f"translation_en_to_{target_language}", model)
        if not translator: return "Não foi possível traduzir."

        try:
            translation = translator(text)
            return translation[0]['translation_text']
        except Exception as e:
            logger.error(f"Erro ao traduzir texto: {e}")
            return f"Erro na tradução: {e}"

    def generate_image_from_text(self, prompt: str, model: str = "stabilityai/stable-diffusion-2-1-base"):
        """Gera uma imagem a partir de uma descrição textual."""
        image_generator = self._load_diffusers_pipeline(model)
        if not image_generator:
            logger.error("Modelo de geração de imagem não está disponível.")
            return None
            
        logger.info(f"Gerando imagem para o prompt: '{prompt[:50]}...'")
        try:
            # A geração de imagem pode consumir muita memória.
            # Em um sistema de produção, isso rodaria em um worker dedicado.
            with torch.no_grad():
                 image = image_generator(prompt).images[0]
            return image
        except Exception as e:
            logger.error(f"Erro ao gerar imagem: {e}")
            return None

# Ponto de entrada para teste
if __name__ == '__main__':
    # Exemplo de uso do gateway
    hf_gateway = HuggingFaceGateway()

    # Teste de Sumarização
    texto_para_resumir = """
    A inteligência artificial (IA) é um campo da ciência da computação que se dedica
    ao desenvolvimento de sistemas capazes de realizar tarefas que normalmente exigiriam
    inteligência humana. Isso inclui aprendizado, raciocínio, resolução de problemas,
    percepção e uso da linguagem. As abordagens da IA são variadas, indo desde o
    aprendizado de máquina, onde os sistemas aprendem a partir de dados, até a IA
    simbólica, que se baseia em regras lógicas.
    """
    resumo = hf_gateway.summarize_text(texto_para_resumir)
    print("--- Resumo Gerado ---")
    print(resumo)
    print("\n" + "="*50 + "\n")

    # Teste de Geração de Imagem
    prompt_imagem = "A ultra-high-resolution photo of a tranquil zen garden on Mars, with a Bonsai tree made of red crystals."
    imagem_gerada = hf_gateway.generate_image_from_text(prompt_imagem)

    if imagem_gerada:
        print("--- Imagem Gerada ---")
        imagem_gerada.save("arte_gerada_pela_atena.png")
        print("Imagem 'arte_gerada_pela_atena.png' salva com sucesso.")
    else:
        print("--- Falha na Geração da Imagem ---")