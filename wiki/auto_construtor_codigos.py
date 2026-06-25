"""
Auto Construtor de Código (ACC) - Sistema Atena
===============================================

Módulo responsável por gerar código automaticamente com base em contextos de problema,
validação ética e de qualidade, integrando-se aos demais componentes da Atena.

Autor: Sistema Atena - Módulo ACC
Data: 2025
"""

import ast
import re
import json
import logging
import asyncio
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass
from enum import Enum
import requests
import httpx
from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM
import torch


# Configuração de logging
logger = logging.getLogger(__name__)


class ModelType(Enum):
    HUGGINGFACE = "huggingface"
    LM_STUDIO = "lm_studio"
    AUTO = "auto"


@dataclass
class ActionContext:
    """Contexto para validação ética de ações."""
    action_type: str
    description: str
    parameters: Dict[str, Any]
    impact_estimate: str = "baixo"


@dataclass
class EthicalValidationResult:
    """Resultado da validação ética."""
    is_approved: bool
    reason: str
    risk_score: float
    requires_confirmation: bool = False


class CodeTemplateManager:
    """Gerenciador de templates de código reutilizáveis."""
    
    def __init__(self):
        self.templates = {
            'rpa_click_template': '''
# Template para clique em elemento
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

try:
    element = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.{selector_type}, "{selector_value}"))
    )
    element.click()
    logger.info(f"Clicou no elemento: {selector_value}")
except Exception as e:
    logger.error(f"Erro ao clicar no elemento: {e}")
    raise
''',
            
            'rpa_type_template': '''
# Template para digitação em campo
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

try:
    element = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.{selector_type}, "{selector_value}"))
    )
    element.clear()
    element.send_keys("{text_to_type}")
    logger.info(f"Digitou no campo: {selector_value}")
except Exception as e:
    logger.error(f"Erro ao digitar no campo: {e}")
    raise
''',
            
            'error_handling_template': '''
# Template para tratamento de erro
import time
from selenium.common.exceptions import TimeoutException, NoSuchElementException

def {function_name}():
    max_retries = 3
    for attempt in range(max_retries):
        try:
            {main_code}
            return True
        except (TimeoutException, NoSuchElementException) as e:
            logger.warning(f"Tentativa {attempt + 1} falhou: {e}")
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
                logger.error(f"Todas as tentativas falharam para: {function_name}")
                raise
        except Exception as e:
            logger.error(f"Erro inesperado em {function_name}: {e}")
            raise
    return False
''',
            
            'data_extraction_template': '''
# Template para extração de dados
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

try:
    elements = WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located((By.{selector_type}, "{selector_value}"))
    )
    
    extracted_data = []
    for element in elements:
        data = {{
            'text': element.text.strip(),
            'value': element.get_attribute('value') if element.get_attribute('value') else '',
            'href': element.get_attribute('href') if element.get_attribute('href') else ''
        }}
        extracted_data.append(data)
    
    logger.info(f"Extraiu {len(extracted_data)} elementos")
    return extracted_data
    
except Exception as e:
    logger.error(f"Erro na extração de dados: {e}")
    return []
'''
        }
    
    def get_template(self, template_type: str) -> Optional[str]:
        """Retorna um template de código específico."""
        return self.templates.get(template_type)
    
    def apply_template(self, template: str, data: Dict[str, Any]) -> str:
        """Aplica dados ao template substituindo placeholders."""
        try:
            return template.format(**data)
        except KeyError as e:
            logger.error(f"Placeholder não encontrado no template: {e}")
            return template
        except Exception as e:
            logger.error(f"Erro ao aplicar template: {e}")
            return template
    
    def list_templates(self) -> List[str]:
        """Lista todos os templates disponíveis."""
        return list(self.templates.keys())


class CodeValidatorModule:
    """Módulo de validação de código gerado."""
    
    def __init__(self):
        self.dangerous_patterns = [
            r'eval\s*\(',
            r'exec\s*\(',
            r'os\.system\s*\(',
            r'subprocess\.call\s*\(',
            r'__import__\s*\(',
            r'open\s*\([^)]*["\']w["\']',  # Abertura de arquivo para escrita
            r'rm\s+-rf',
            r'del\s+.*\*',
        ]
    
    def validate_code(self, code: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Valida código gerado em múltiplos aspectos."""
        validation_result = {
            'is_valid': True,
            'quality_score': 1.0,
            'feedback': [],
            'warnings': [],
            'errors': []
        }
        
        # 1. Análise de Sintaxe
        syntax_result = self._validate_syntax(code)
        if not syntax_result['is_valid']:
            validation_result['is_valid'] = False
            validation_result['errors'].extend(syntax_result['errors'])
        
        # 2. Análise de Segurança
        security_result = self._validate_security(code)
        if not security_result['is_safe']:
            validation_result['quality_score'] *= 0.3
            validation_result['warnings'].extend(security_result['warnings'])
        
        # 3. Análise de Consistência
        consistency_result = self._validate_consistency(code, context)
        validation_result['quality_score'] *= consistency_result['consistency_score']
        validation_result['feedback'].extend(consistency_result['feedback'])
        
        # 4. Análise de Qualidade
        quality_result = self._assess_quality(code)
        validation_result['quality_score'] *= quality_result['quality_multiplier']
        validation_result['feedback'].extend(quality_result['feedback'])
        
        return validation_result
    
    def _validate_syntax(self, code: str) -> Dict[str, Any]:
        """Valida sintaxe Python usando AST."""
        try:
            ast.parse(code)
            return {'is_valid': True, 'errors': []}
        except SyntaxError as e:
            return {
                'is_valid': False,
                'errors': [f"Erro de sintaxe: {e.msg} na linha {e.lineno}"]
            }
        except Exception as e:
            return {
                'is_valid': False,
                'errors': [f"Erro na análise de sintaxe: {str(e)}"]
            }
    
    def _validate_security(self, code: str) -> Dict[str, Any]:
        """Valida segurança básica do código."""
        warnings = []
        
        for pattern in self.dangerous_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                warnings.append(f"Padrão potencialmente perigoso detectado: {pattern}")
        
        return {
            'is_safe': len(warnings) == 0,
            'warnings': warnings
        }
    
    def _validate_consistency(self, code: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Valida consistência do código com o contexto."""
        feedback = []
        consistency_score = 1.0
        
        # Verifica se há seletores no código e HTML no contexto
        if 'html_snapshot' in context:
            html_content = context['html_snapshot']
            
            # Extrai seletores do código
            selectors = re.findall(r'By\.\w+,\s*["\']([^"\']+)["\']', code)
            
            for selector in selectors:
                if selector not in html_content:
                    feedback.append(f"Seletor '{selector}' não encontrado no HTML fornecido")
                    consistency_score *= 0.8
        
        # Verifica se o código corresponde ao objetivo
        if 'desired_outcome' in context:
            desired = context['desired_outcome'].lower()
            if 'click' in desired and 'click()' not in code:
                feedback.append("Objetivo requer clique, mas código não contém click()")
                consistency_score *= 0.7
            elif 'type' in desired or 'digitar' in desired and 'send_keys' not in code:
                feedback.append("Objetivo requer digitação, mas código não contém send_keys()")
                consistency_score *= 0.7
        
        return {
            'consistency_score': consistency_score,
            'feedback': feedback
        }
    
    def _assess_quality(self, code: str) -> Dict[str, Any]:
        """Avalia qualidade geral do código."""
        feedback = []
        quality_multiplier = 1.0
        
        lines = code.strip().split('\n')
        non_empty_lines = [line for line in lines if line.strip()]
        
        # Penaliza código muito curto ou muito longo
        if len(non_empty_lines) < 3:
            quality_multiplier *= 0.8
            feedback.append("Código muito simples - considere adicionar tratamento de erro")
        elif len(non_empty_lines) > 50:
            quality_multiplier *= 0.9
            feedback.append("Código muito complexo - considere refatoração")
        
        # Verifica presença de tratamento de erro
        if 'try:' not in code and 'except' not in code:
            quality_multiplier *= 0.7
            feedback.append("Código sem tratamento de exceções")
        
        # Verifica logging
        if 'logger' in code or 'logging' in code:
            quality_multiplier *= 1.1
            feedback.append("Bom uso de logging")
        
        # Verifica comentários
        comment_lines = [line for line in lines if line.strip().startswith('#')]
        if len(comment_lines) > 0:
            quality_multiplier *= 1.05
            feedback.append("Código bem comentado")
        
        return {
            'quality_multiplier': quality_multiplier,
            'feedback': feedback
        }


class LLMIntegration:
    """Integração com modelos de linguagem locais e em nuvem."""
    
    def __init__(self, lm_studio_url: str = "http://localhost:1234"):
        self.lm_studio_url = lm_studio_url
        self.hf_pipeline = None
        self.model_cache = {}
        
    def _initialize_huggingface_model(self, model_name: str = "microsoft/DialoGPT-medium"):
        """Inicializa modelo Hugging Face para CPU."""
        try:
            if model_name not in self.model_cache:
                logger.info(f"Carregando modelo Hugging Face: {model_name}")
                
                # Configura para CPU explicitamente
                device = "cpu"
                
                # Carrega o modelo
                tokenizer = AutoTokenizer.from_pretrained(model_name)
                model = AutoModelForCausalLM.from_pretrained(
                    model_name,
                    torch_dtype=torch.float32,
                    device_map="cpu"
                )
                
                # Cria pipeline
                self.hf_pipeline = pipeline(
                    "text-generation",
                    model=model,
                    tokenizer=tokenizer,
                    device=-1,  # CPU
                    max_length=512,
                    temperature=0.7,
                    do_sample=True
                )
                
                self.model_cache[model_name] = self.hf_pipeline
                logger.info(f"Modelo {model_name} carregado com sucesso")
                
            return True
            
        except Exception as e:
            logger.error(f"Erro ao carregar modelo Hugging Face: {e}")
            return False
    
    async def _call_lm_studio(self, prompt: str) -> Dict[str, Any]:
        """Chama API do LM Studio."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.lm_studio_url}/v1/chat/completions",
                    json={
                        "model": "local-model",
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.7,
                        "max_tokens": 1000
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    content = data['choices'][0]['message']['content']
                    return {
                        'success': True,
                        'response': content,
                        'model': 'lm_studio'
                    }
                else:
                    return {
                        'success': False,
                        'error': f"LM Studio retornou status {response.status_code}"
                    }
                    
        except Exception as e:
            logger.error(f"Erro na chamada ao LM Studio: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _call_huggingface(self, prompt: str) -> Dict[str, Any]:
        """Chama modelo Hugging Face."""
        try:
            if not self.hf_pipeline:
                if not self._initialize_huggingface_model():
                    return {
                        'success': False,
                        'error': 'Falha ao inicializar modelo Hugging Face'
                    }
            
            # Gera texto
            outputs = self.hf_pipeline(
                prompt,
                max_length=len(prompt.split()) + 200,
                num_return_sequences=1,
                pad_token_id=self.hf_pipeline.tokenizer.eos_token_id
            )
            
            generated_text = outputs[0]['generated_text']
            # Remove o prompt original da resposta
            response = generated_text[len(prompt):].strip()
            
            return {
                'success': True,
                'response': response,
                'model': 'huggingface'
            }
            
        except Exception as e:
            logger.error(f"Erro na chamada ao Hugging Face: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _extract_code_from_response(self, response: str) -> Dict[str, str]:
        """Extrai código Python e explicação da resposta."""
        # Procura por blocos de código Python
        code_pattern = r'```python\n(.*?)```'
        code_matches = re.findall(code_pattern, response, re.DOTALL)
        
        if code_matches:
            code = code_matches[0].strip()
        else:
            # Fallback: procura por linhas que parecem código Python
            lines = response.split('\n')
            code_lines = []
            for line in lines:
                if (line.strip().startswith(('from ', 'import ', 'def ', 'class ', 'try:', 'if ', 'for ', 'while ')) or
                    'driver.' in line or 'element.' in line or '.click()' in line or '.send_keys(' in line):
                    code_lines.append(line)
            code = '\n'.join(code_lines)
        
        # Extrai explicação (texto que não é código)
        explanation = re.sub(r'```python.*?```', '', response, flags=re.DOTALL)
        explanation = explanation.strip()
        
        return {
            'generated_code': code,
            'explanation': explanation
        }
    
    async def generate_text_with_code(self, prompt: str, ai_model_preference: str = "auto") -> Dict[str, Any]:
        """Gera código usando o modelo especificado."""
        result = {
            'raw_response': '',
            'generated_code': '',
            'explanation': '',
            'used_model': '',
            'confidence_score': 0.0
        }
        
        # Tenta LM Studio primeiro se disponível
        if ai_model_preference in ["auto", "lm_studio"]:
            lm_result = await self._call_lm_studio(prompt)
            if lm_result['success']:
                result['raw_response'] = lm_result['response']
                result['used_model'] = 'lm_studio'
                result['confidence_score'] = 0.9
                
                # Extrai código
                code_data = self._extract_code_from_response(lm_result['response'])
                result.update(code_data)
                
                return result
        
        # Fallback para Hugging Face
        if ai_model_preference in ["auto", "huggingface"]:
            hf_result = self._call_huggingface(prompt)
            if hf_result['success']:
                result['raw_response'] = hf_result['response']
                result['used_model'] = 'huggingface'
                result['confidence_score'] = 0.7
                
                # Extrai código
                code_data = self._extract_code_from_response(hf_result['response'])
                result.update(code_data)
                
                return result
        
        # Se tudo falhar, usa template básico
        logger.warning("Todos os modelos falharam, usando template básico")
        result['raw_response'] = "Fallback para template básico"
        result['generated_code'] = "# Código gerado por template básico\nprint('Implementação pendente')"
        result['explanation'] = "Código gerado usando template básico devido a falha nos modelos"
        result['used_model'] = 'template_fallback'
        result['confidence_score'] = 0.3
        
        return result


class SimpleEthicalFramework:
    """Framework ético simplificado para validação de ações."""
    
    def __init__(self):
        self.risk_keywords = [
            'delete', 'remove', 'drop', 'truncate', 'rm -rf',
            'format', 'destroy', 'wipe', 'system', 'admin',
            'password', 'private', 'secret', 'token'
        ]
        
        self.high_risk_actions = [
            'file_deletion', 'system_modification', 'data_destruction',
            'privilege_escalation', 'network_access'
        ]
    
    def validate_action(self, action_context: ActionContext) -> EthicalValidationResult:
        """Valida ação do ponto de vista ético."""
        risk_score = 1.0
        warnings = []
        
        # Verifica palavras-chave de risco
        description_lower = action_context.description.lower()
        for keyword in self.risk_keywords:
            if keyword in description_lower:
                risk_score *= 0.7
                warnings.append(f"Palavra-chave de risco detectada: {keyword}")
        
        # Verifica tipo de ação
        if action_context.action_type in self.high_risk_actions:
            risk_score *= 0.5
            warnings.append(f"Tipo de ação de alto risco: {action_context.action_type}")
        
        # Verifica parâmetros
        if 'generated_code' in action_context.parameters:
            code = action_context.parameters['generated_code']
            for keyword in self.risk_keywords:
                if keyword in code.lower():
                    risk_score *= 0.6
                    warnings.append(f"Código contém operação de risco: {keyword}")
        
        # Determina aprovação
        is_approved = risk_score > 0.5
        requires_confirmation = 0.3 < risk_score <= 0.7
        
        reason = "Ação aprovada" if is_approved else "Ação rejeitada por riscos éticos"
        if warnings:
            reason += f". Avisos: {'; '.join(warnings)}"
        
        return EthicalValidationResult(
            is_approved=is_approved,
            reason=reason,
            risk_score=risk_score,
            requires_confirmation=requires_confirmation
        )


class CodeGeneratorAgent:
    """Agente principal para geração de código automatizada."""
    
    def __init__(self, llm_integration: Optional[LLMIntegration] = None, 
                 semantic_analyzer: Optional[Any] = None, 
                 ethical_framework: Optional[SimpleEthicalFramework] = None):
        self.llm_integration = llm_integration or LLMIntegration()
        self.semantic_analyzer = semantic_analyzer  # Placeholder para integração futura
        self.ethical_framework = ethical_framework or SimpleEthicalFramework()
        self.code_validator = CodeValidatorModule()
        self.template_manager = CodeTemplateManager()
        self.logger = logger
        
    def _build_llm_prompt(self, problem_context: Dict[str, Any], 
                         desired_outcome: str, 
                         existing_code: Optional[str] = None,
                         semantic_analysis: Optional[Dict] = None) -> str:
        """Constrói prompt rico para o LLM."""
        
        prompt = f"""Você é um especialista em automação web e Python. Preciso que você gere código Python para resolver o seguinte problema:

CONTEXTO DO PROBLEMA:
{json.dumps(problem_context, indent=2, ensure_ascii=False)}

OBJETIVO DESEJADO:
{desired_outcome}

"""
        
        if existing_code:
            prompt += f"""
CÓDIGO EXISTENTE (para correção/extensão):
```python
{existing_code}
```

"""
        
        if semantic_analysis:
            prompt += f"""
ANÁLISE SEMÂNTICA:
{json.dumps(semantic_analysis, indent=2, ensure_ascii=False)}

"""
        
        prompt += """
INSTRUÇÕES:
1. Gere código Python funcional usando Selenium WebDriver
2. Inclua tratamento de erros adequado
3. Use WebDriverWait para aguardar elementos
4. Adicione logging para debug
5. Mantenha o código limpo e bem comentado
6. Retorne apenas o código Python funcional

FORMATO DE RESPOSTA:
```python
# Seu código aqui
```

Explicação: [explicação breve do que o código faz]
"""
        
        return prompt
    
    async def generate_code(self, problem_context: Dict[str, Any], 
                           desired_outcome: str, 
                           existing_code: Optional[str] = None) -> Dict[str, Any]:
        """Método principal para geração de código."""
        
        try:
            # 1. Enriquecimento do Prompt
            semantic_analysis = None
            if self.semantic_analyzer:
                context_text = problem_context.get('error_message', '') + " " + problem_context.get('html_snapshot', '')
                semantic_analysis = await self.semantic_analyzer.analyze_text(context_text)
            
            prompt = self._build_llm_prompt(problem_context, desired_outcome, existing_code, semantic_analysis)
            
            # 2. Chamada ao LLM
            self.logger.info("Iniciando geração de código via LLM")
            llm_response = await self.llm_integration.generate_text_with_code(
                prompt, 
                ai_model_preference="auto"
            )
            
            generated_code = llm_response.get('generated_code', '')
            explanation = llm_response.get('explanation', 'Código gerado sem explicação.')
            
            if not generated_code:
                self.logger.warning("LLM não retornou código válido, tentando template")
                return await self._generate_from_template(problem_context, desired_outcome)
            
            # 3. Validação de Código
            validation_context = problem_context.copy()
            validation_context['desired_outcome'] = desired_outcome
            
            validation_result = self.code_validator.validate_code(generated_code, validation_context)
            
            if not validation_result['is_valid']:
                self.logger.warning(f"Código gerado inválido: {validation_result['errors']}")
                return {
                    'success': False,
                    'error': 'Código gerado inválido',
                    'feedback': validation_result['errors'] + validation_result['feedback']
                }
            
            # 4. Validação Ética
            ethical_context = ActionContext(
                action_type="code_generation",
                description=f"Gerar código para: {desired_outcome}",
                parameters={
                    'generated_code': generated_code[:200],  # Primeiros 200 chars
                    'context': problem_context,
                    'impact_estimate': problem_context.get('impact_estimate', 'baixo')
                }
            )
            
            ethical_validation = self.ethical_framework.validate_action(ethical_context)
            
            if not ethical_validation.is_approved:
                self.logger.warning(f"Código reprovado pela ética: {ethical_validation.reason}")
                return {
                    'success': False,
                    'error': 'Código reprovado pela validação ética',
                    'reason': ethical_validation.reason,
                    'requires_confirmation': ethical_validation.requires_confirmation
                }
            
            # 5. Cálculo de confiança
            confidence = (
                validation_result['quality_score'] * 
                llm_response.get('confidence_score', 1.0) * 
                ethical_validation.risk_score
            )
            
            # Retorno de sucesso
            return {
                'success': True,
                'code': generated_code,
                'explanation': explanation,
                'confidence': confidence,
                'used_model': llm_response.get('used_model', 'unknown'),
                'ethical_validation': ethical_validation.reason,
                'quality_feedback': validation_result['feedback'],
                'warnings': validation_result.get('warnings', [])
            }
            
        except Exception as e:
            self.logger.error(f"Erro na geração de código: {e}")
            return {
                'success': False,
                'error': f'Erro interno: {str(e)}',
                'fallback_available': True
            }
    
    async def _generate_from_template(self, problem_context: Dict[str, Any], 
                                    desired_outcome: str) -> Dict[str, Any]:
        """Gera código usando templates como fallback."""
        
        desired_lower = desired_outcome.lower()
        
        # Determina template mais apropriado
        if 'click' in desired_lower or 'clicar' in desired_lower:
            template_type = 'rpa_click_template'
            template_data = {
                'selector_type': 'XPATH',
                'selector_value': problem_context.get('selector', '//button[@type="submit"]')
            }
        elif 'type' in desired_lower or 'digitar' in desired_lower:
            template_type = 'rpa_type_template'
            template_data = {
                'selector_type': 'ID',
                'selector_value': problem_context.get('selector', 'input_field'),
                'text_to_type': problem_context.get('text_value', 'texto_exemplo')
            }
        elif 'extract' in desired_lower or 'extrair' in desired_lower:
            template_type = 'data_extraction_template'
            template_data = {
                'selector_type': 'CLASS_NAME',
                'selector_value': problem_context.get('selector', 'data-item')
            }
        else:
            template_type = 'error_handling_template'
            template_data = {
                'function_name': 'automated_task',
                'main_code': '    # Código principal aqui\n    pass'
            }
        
        template = self.template_manager.get_template(template_type)
        if not template:
            return {
                'success': False,
                'error': 'Template não encontrado'
            }
        
        generated_code = self.template_manager.apply_template(template, template_data)
        
        return {
            'success': True,
            'code': generated_code,
            'explanation': f'Código gerado usando template {template_type}',
            'confidence': 0.6,
            'used_model': 'template',
            'ethical_validation': 'Aprovado (template padrão)',
            'quality_feedback': ['Código baseado em template validado'],
            'warnings': ['Código gerado por template - pode precisar de ajustes']
        }
    
    def get_available_templates(self) -> List[str]:
        """Retorna lista de templates disponíveis."""
        return self.template_manager.list_templates()

# Exemplo de uso e teste
async def main():
    """Exemplo de uso do Auto Construtor de Código."""
    
    # Configuração de logging
    logging.basicConfig(level=logging.INFO)
    
    # Inicializa o agente
    code_generator = CodeGeneratorAgent()
    
    # Exemplo de contexto de problema
    problem_context = {
        'error_message': 'Elemento não encontrado: botão de submit',
        'html_snapshot': '<button id="submit-btn" type="submit">Enviar</button>',
        'selector': 'submit-btn',
        'page_url': 'https://exemplo.com/form',
        'impact_estimate': 'baixo'
    }
    
    # Teste 1: Geração de código para clique
    print("=== TESTE 1: Geração de código para clique ===")
    result = await code_generator.generate_code(
        problem_context=problem_context,
        desired_outcome="Clicar no botão de submit"
    )
    
    print(f"Sucesso: {result['success']}")
    if result['success']:
        print(f"Código gerado:\n{result['code']}")
        print(f"Explicação: {result['explanation']}")
        print(f"Confiança: {result['confidence']:.2f}")
        print(f"Modelo usado: {result['used_model']}")
    else:
        print(f"Erro: {result['error']}")
    
    print("\n" + "="*50 + "\n")
    
    # Teste 2: Geração de código para digitação
    print("=== TESTE 2: Geração de código para digitação ===")
    context_input = {
        'html_snapshot': '<input id="email" type="email" placeholder="Digite seu email">',
        'selector': 'email',
        'text_value': 'usuario@exemplo.com',
        'page_url': 'https://exemplo.com/login',
        'impact_estimate': 'baixo'
    }
    
    result = await code_generator.generate_code(
        problem_context=context_input,
        desired_outcome="Digitar email no campo de entrada"
    )
    
    print(f"Sucesso: {result['success']}")
    if result['success']:
        print(f"Código gerado:\n{result['code']}")
        print(f"Confiança: {result['confidence']:.2f}")
    else:
        print(f"Erro: {result['error']}")
    
    print("\n" + "="*50 + "\n")
    
    # Teste 3: Correção de código existente
    print("=== TESTE 3: Correção de código existente ===")
    broken_code = """
driver.find_element(By.ID, "broken-selector").click()
"""
    
    result = await code_generator.generate_code(
        problem_context={
            'error_message': 'NoSuchElementException: Unable to locate element',
            'html_snapshot': '<button class="submit-button" data-id="submit">Enviar</button>',
            'impact_estimate': 'médio'
        },
        desired_outcome="Corrigir código que não consegue encontrar elemento",
        existing_code=broken_code
    )
    
    print(f"Sucesso: {result['success']}")
    if result['success']:
        print(f"Código corrigido:\n{result['code']}")
        print(f"Avisos: {result.get('warnings', [])}")
    else:
        print(f"Erro: {result['error']}")
    
    print("\n" + "="*50 + "\n")
    
    # Teste 4: Templates disponíveis
    print("=== TESTE 4: Templates disponíveis ===")
    templates = code_generator.get_available_templates()
    print(f"Templates disponíveis: {templates}")
    
    # Teste 5: Validação ética
    print("\n=== TESTE 5: Validação ética ===")
    risky_context = {
        'html_snapshot': '<button onclick="deleteAllData()">Delete</button>',
        'selector': 'delete-btn',
        'impact_estimate': 'alto'
    }
    
    result = await code_generator.generate_code(
        problem_context=risky_context,
        desired_outcome="Clicar no botão de delete para remover dados do sistema"
    )
    
    print(f"Sucesso: {result['success']}")
    if not result['success']:
        print(f"Motivo da rejeição: {result.get('reason', result.get('error'))}")
        print(f"Requer confirmação: {result.get('requires_confirmation', False)}")


class AutoCodeConstructorFacade:
    """Facade para facilitar a integração do ACC com outros módulos da Atena."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Inicializa o ACC com configurações.
        
        Args:
            config: Dicionário com configurações:
                - lm_studio_url: URL do LM Studio
                - enable_ethical_validation: Habilitar validação ética
                - default_model_preference: Preferência de modelo padrão
        """
        self.config = config or {}
        
        # Inicializa componentes
        llm_integration = LLMIntegration(
            lm_studio_url=self.config.get('lm_studio_url', 'http://localhost:1234')
        )
        
        ethical_framework = None
        if self.config.get('enable_ethical_validation', True):
            ethical_framework = SimpleEthicalFramework()
        
        self.code_generator = CodeGeneratorAgent(
            llm_integration=llm_integration,
            ethical_framework=ethical_framework
        )
        
        self.logger = logger
        self.default_model_preference = self.config.get('default_model_preference', 'auto')
    
    async def generate_automation_code(self, error_context: str, html_content: str, 
                                     target_action: str, **kwargs) -> Dict[str, Any]:
        """
        Interface simplificada para geração de código de automação.
        
        Args:
            error_context: Descrição do erro ou problema
            html_content: HTML da página
            target_action: Ação desejada
            **kwargs: Parâmetros adicionais
        
        Returns:
            Dict com resultado da geração
        """
        problem_context = {
            'error_message': error_context,
            'html_snapshot': html_content,
            'impact_estimate': kwargs.get('impact_estimate', 'baixo'),
            'page_url': kwargs.get('page_url', ''),
            'selector': kwargs.get('selector', ''),
            'text_value': kwargs.get('text_value', '')
        }
        
        return await self.code_generator.generate_code(
            problem_context=problem_context,
            desired_outcome=target_action,
            existing_code=kwargs.get('existing_code')
        )
    
    async def repair_existing_code(self, broken_code: str, error_message: str, 
                                 context_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Interface para reparo de código existente.
        
        Args:
            broken_code: Código que precisa ser reparado
            error_message: Mensagem de erro
            context_data: Dados de contexto
        
        Returns:
            Dict com código reparado
        """
        problem_context = {
            'error_message': error_message,
            **context_data
        }
        
        return await self.code_generator.generate_code(
            problem_context=problem_context,
            desired_outcome="Corrigir erro no código existente",
            existing_code=broken_code
        )
    
    def get_system_status(self) -> Dict[str, Any]:
        """Retorna status do sistema ACC."""
        return {
            'acc_version': '1.0.0',
            'ethical_validation_enabled': self.code_generator.ethical_framework is not None,
            'available_templates': self.code_generator.get_available_templates(),
            'default_model': self.default_model_preference,
            'lm_studio_url': self.code_generator.llm_integration.lm_studio_url
        }


# Classe para integração com sistema metacognitivo
class ACCMetacognitiveFeedback:
    """Sistema de feedback metacognitivo para o ACC."""
    
    def __init__(self):
        self.generation_history = []
        self.success_patterns = {}
        self.failure_patterns = {}
    
    def record_generation_attempt(self, context: Dict[str, Any], 
                                result: Dict[str, Any]) -> None:
        """Registra tentativa de geração para aprendizado."""
        record = {
            'timestamp': asyncio.get_event_loop().time(),
            'context_hash': hash(str(sorted(context.items()))),
            'success': result.get('success', False),
            'confidence': result.get('confidence', 0.0),
            'used_model': result.get('used_model', 'unknown'),
            'quality_score': result.get('quality_score', 0.0),
            'context_type': self._classify_context(context),
            'outcome_type': self._classify_outcome(context.get('desired_outcome', ''))
        }
        
        self.generation_history.append(record)
        self._update_patterns(record)
    
    def _classify_context(self, context: Dict[str, Any]) -> str:
        """Classifica tipo de contexto."""
        if 'error_message' in context:
            return 'error_correction'
        elif 'html_snapshot' in context:
            return 'web_automation'
        else:
            return 'general'
    
    def _classify_outcome(self, desired_outcome: str) -> str:
        """Classifica tipo de resultado desejado."""
        outcome_lower = desired_outcome.lower()
        if 'click' in outcome_lower:
            return 'click_action'
        elif 'type' in outcome_lower or 'digitar' in outcome_lower:
            return 'input_action'
        elif 'extract' in outcome_lower:
            return 'data_extraction'
        else:
            return 'other'
    
    def _update_patterns(self, record: Dict[str, Any]) -> None:
        """Atualiza padrões de sucesso/falha."""
        pattern_key = f"{record['context_type']}_{record['outcome_type']}"
        
        if record['success']:
            if pattern_key not in self.success_patterns:
                self.success_patterns[pattern_key] = []
            self.success_patterns[pattern_key].append(record)
        else:
            if pattern_key not in self.failure_patterns:
                self.failure_patterns[pattern_key] = []
            self.failure_patterns[pattern_key].append(record)
    
    def get_recommendations(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Fornece recomendações baseadas no histórico."""
        context_type = self._classify_context(context)
        outcome_type = self._classify_outcome(context.get('desired_outcome', ''))
        pattern_key = f"{context_type}_{outcome_type}"
        
        recommendations = {
            'suggested_model': 'auto',
            'expected_confidence': 0.5,
            'risk_factors': [],
            'success_probability': 0.5
        }
        
        # Análise de padrões de sucesso
        if pattern_key in self.success_patterns:
            successes = self.success_patterns[pattern_key]
            if successes:
                # Modelo mais bem-sucedido
                model_counts = {}
                for success in successes[-10:]:  # Últimos 10 sucessos
                    model = success['used_model']
                    model_counts[model] = model_counts.get(model, 0) + 1
                
                if model_counts:
                    recommendations['suggested_model'] = max(model_counts, key=model_counts.get)
                
                # Confiança média
                avg_confidence = sum(s['confidence'] for s in successes[-10:]) / len(successes[-10:])
                recommendations['expected_confidence'] = avg_confidence
        
        # Análise de padrões de falha
        if pattern_key in self.failure_patterns:
            failures = self.failure_patterns[pattern_key]
            total_attempts = len(self.success_patterns.get(pattern_key, [])) + len(failures)
            recommendations['success_probability'] = len(self.success_patterns.get(pattern_key, [])) / max(total_attempts, 1)
            
            # Identifica fatores de risco comuns
            for failure in failures[-5:]:  # Últimas 5 falhas
                if failure.get('ethical_issue'):
                    recommendations['risk_factors'].append('ethical_concerns')
                if failure.get('validation_failed'):
                    recommendations['risk_factors'].append('code_quality')
        
        return recommendations


# Sistema de execução simulada para teste
class ExecutionSandbox:
    """Sandbox simulado para execução de código gerado."""
    
    def __init__(self):
        self.execution_history = []
        self.logger = logger
    
    async def simulate_execution(self, code: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Simula execução do código gerado."""
        self.logger.info("=== SIMULAÇÃO DE EXECUÇÃO ===")
        self.logger.info(f"Código a ser executado:\n{code}")
        
        # Análise básica do código para simulação
        result = {
            'success': True,
            'execution_time': 2.5,  # Simulado
            'output': '',
            'errors': [],
            'side_effects': []
        }
        
        # Simula diferentes cenários baseados no código
        if 'click()' in code:
            result['output'] = 'Elemento clicado com sucesso'
            result['side_effects'].append('page_navigation')
        elif 'send_keys(' in code:
            result['output'] = 'Texto digitado no campo'
            result['side_effects'].append('form_input')
        elif 'find_element' in code and 'TimeoutException' in code:
            result['output'] = 'Elemento encontrado após aguardar'
        
        # Simula falhas ocasionais
        import random
        if random.random() < 0.1:  # 10% de chance de falha
            result['success'] = False
            result['errors'].append('Elemento não encontrado na simulação')
        
        # Registra histórico
        execution_record = {
            'timestamp': asyncio.get_event_loop().time(),
            'code_hash': hash(code),
            'context': context,
            'result': result
        }
        self.execution_history.append(execution_record)
        
        self.logger.info(f"Resultado da simulação: {result}")
        return result


# Ponto de entrada principal
if __name__ == "__main__":
    asyncio.run(main())