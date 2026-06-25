# atena_solution_agent.py
# Versão 2.0 - Módulo de Solução Autônoma (MSA) com Integração Direta Hugging Face

import logging
import re
import asyncio
import ast
from typing import Optional, Dict, Any

# Bibliotecas de IA Hugging Face
import torch
from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM

# Configuração de logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(name)s:%(lineno)d - %(message)s")
logger = logging.getLogger("SolutionAgent_HF")

class HuggingFaceCodeGenerator:
    """
    Carrega e executa um Modelo de Linguagem Grande (LLM) do Hugging Face
    diretamente no ambiente local, otimizado para CPU.
    """
    def __init__(self, model_name: str = "microsoft/phi-1_5"):
        self.model_name = model_name
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.generator_pipeline = None
        
        logger.info(f"Preparando para carregar o modelo '{self.model_name}' no dispositivo: {self.device}")
        self._initialize_pipeline()

    def _initialize_pipeline(self):
        """
        Inicializa o pipeline de geração de texto do Hugging Face.
        Esta operação pode ser demorada e consumir memória na primeira execução.
        """
        try:
            logger.info("Iniciando o download e carregamento do modelo. Isso pode levar alguns minutos...")
            # Carregar o modelo com o tipo de dado recomendado para CPU para evitar problemas de memória
            # torch_dtype="auto" ou torch.bfloat16 se suportado, senão o padrão float32.
            tokenizer = AutoTokenizer.from_pretrained(self.model_name, trust_remote_code=True)
            model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                trust_remote_code=True,
                torch_dtype="auto" # Deixa a biblioteca escolher o melhor dtype
            )
            
            self.generator_pipeline = pipeline(
                "text-generation",
                model=model,
                tokenizer=tokenizer,
                device=self.device
            )
            logger.info(f"Modelo '{self.model_name}' carregado com sucesso no dispositivo '{self.device}'.")
        except Exception as e:
            logger.error(f"Erro CRÍTICO ao inicializar o pipeline do Hugging Face: {e}", exc_info=True)
            logger.error("O sistema de geração de código não funcionará. Verifique a instalação do PyTorch e Transformers.")
            self.generator_pipeline = None

    def generate_code(self, prompt: str, max_new_tokens: int = 400, temperature: float = 0.1) -> Optional[str]:
        """Gera código usando o pipeline local do Hugging Face."""
        if not self.generator_pipeline:
            logger.error("Pipeline de geração de código não está inicializado. Impossível gerar código.")
            return None

        try:
            logger.info("Enviando prompt para o modelo Hugging Face local...")
            
            # Gerar a saída
            outputs = self.generator_pipeline(
                prompt,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                do_sample=True,
                pad_token_id=self.generator_pipeline.tokenizer.eos_token_id
            )
            
            # Extrair apenas o texto gerado (excluindo o prompt de entrada)
            generated_text = outputs[0]['generated_text']
            # O prompt pode ser incluído no início da resposta, então removemos
            if generated_text.startswith(prompt):
                 content = generated_text[len(prompt):].strip()
            else:
                 content = generated_text
            
            if content:
                # Extrai o bloco de código da resposta
                code_blocks = re.findall(r'```python\n(.*?)```', content, re.DOTALL)
                return code_blocks[0].strip() if code_blocks else content.strip()
            return None

        except Exception as e:
            logger.error(f"Erro inesperado ao gerar código com o modelo Hugging Face: {e}", exc_info=True)
            return None

class AdvancedAutoCodeGenerator:
    """
    Agente unificado que gera, valida e otimiza código de automação.
    Agora utiliza um gerador Hugging Face local.
    """
    def __init__(self):
        # O modelo aqui pode ser alterado para qualquer outro compatível com a tarefa de geração de código.
        # "microsoft/phi-1_5" é uma boa escolha para começar em termos de balanço entre tamanho e capacidade.
        self.code_generator_hf = HuggingFaceCodeGenerator(model_name="microsoft/phi-1_5")

    async def generate_automation_code(self, description: str, target_url: str, html_content: Optional[str] = None) -> Dict[str, Any]:
        """
        Função principal para gerar e validar o código de automação.
        """
        logger.info(f"Iniciando geração de código para: '{description}'")

        # 1. Construção do Prompt
        prompt = self._build_prompt(description, target_url, html_content)

        # 2. Geração de Código via Loop de Eventos (para não bloquear)
        loop = asyncio.get_running_loop()
        generated_code = await loop.run_in_executor(
            None, # Usa o executor padrão
            self.code_generator_hf.generate_code,
            prompt
        )

        if not generated_code:
            logger.error("Falha na geração de código pelo modelo Hugging Face.")
            return {"success": False, "error": "Modelo local não retornou código."}

        # 3. Validação
        is_valid, validation_errors = self._validate_syntax(generated_code)

        if not is_valid:
            return {"success": False, "error": "Código gerado com erro de sintaxe.", "details": validation_errors}

        return {
            "success": True,
            "code": generated_code,
            "explanation": "Código gerado com sucesso usando um modelo Hugging Face local.",
            "validation_status": "Sintaxe OK"
        }

    def _build_prompt(self, description: str, target_url: str, html_content: Optional[str]) -> str:
        # A lógica de construção de prompt permanece a mesma, é excelente.
        html_preview = (html_content[:1500] + "...") if html_content and len(html_content) > 1500 else html_content
            
        prompt = f"""
<|user|>
**Tarefa de Automação com Playwright**

**Objetivo:** {description}
**URL Alvo:** {target_url}

**Contexto da Página (HTML Snippet):**
```html
{html_preview or "Nenhum HTML fornecido."}
```

Gere um script Python completo e funcional usando Playwright assíncrono para realizar a tarefa. O script deve ser auto-contido. Retorne APENAS o código Python dentro de um bloco ```python.
<|end|>
<|assistant|>
```python
"""
        return prompt

    def _validate_syntax(self, code: str) -> tuple[bool, Optional[str]]:
        """Valida a sintaxe do código Python gerado."""
        try:
            ast.parse(code)
            return True, None
        except SyntaxError as e:
            return False, f"Erro de sintaxe na linha {e.lineno}: {e.msg}"
