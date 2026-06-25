# Sistema Cognitivo Atena - Módulos RPA e NLU
# Baseado em teorias psicológicas: Teoria da Mente, Cognição Incorporada, 
# Processamento Dual (Sistema 1 e Sistema 2 de Kahneman)

import asyncio
import json
import re
import time
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import logging
from pathlib import Path

# Dependências para automação web
from playwright.async_api import async_playwright, Page, Browser
from bs4 import BeautifulSoup, Tag
import requests
from urllib.parse import urljoin, urlparse

# Dependências para NLU
import llama_cpp
import numpy as np
from sentence_transformers import SentenceTransformer
import spacy

# FastAPI para o backend
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== MODELOS DE DADOS ====================

class CognitiveState(Enum):
    """Estados cognitivos baseados na Teoria da Mente"""
    DORMANT = "dormant"
    AWAKENING = "awakening"
    PROCESSING = "processing"
    REFLECTING = "reflecting"
    ACTING = "acting"
    LEARNING = "learning"

class PersonaType(Enum):
    """Personas baseadas em arquétipos psicológicos (Jung)"""
    SOPHIA = "sophia"      # Sabedoria - Analítico
    TECHNE = "techne"      # Técnica - Pragmático
    THERAPEIA = "therapeia" # Cura - Empático
    POIESIS = "poiesis"    # Criação - Criativo

@dataclass
class Intent:
    """Representação de intenção baseada em Teoria da Ação Planejada"""
    action: str
    confidence: float
    entities: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    complexity: int = 1  # 1-5, baseado em Cognitive Load Theory

@dataclass
class WebElement:
    """Representação de elemento web com contexto semântico"""
    tag: str
    text: str
    attributes: Dict[str, str]
    xpath: str
    css_selector: str
    semantic_role: str
    confidence: float
    bbox: Optional[Tuple[int, int, int, int]] = None

@dataclass
class CognitiveMemory:
    """Memória de trabalho baseada em Modelo de Baddeley"""
    phonological_loop: List[str] = field(default_factory=list)  # Texto recente
    visuospatial_sketchpad: List[Dict] = field(default_factory=list)  # Elementos visuais
    episodic_buffer: List[Dict] = field(default_factory=list)  # Experiências integradas
    central_executive: Dict[str, Any] = field(default_factory=dict)  # Controle atencional

# ==================== SISTEMA DE COMPREENSÃO DE LINGUAGEM NATURAL ====================

class AdvancedNLU:
    """Sistema de compreensão de linguagem natural avançado"""
    
    def __init__(self, model_path: str = "models/llama-2-7b-chat.Q4_0.gguf"):
        self.model_path = model_path
        self.llm = None
        self.sentence_transformer = None
        self.nlp = None
        self.cognitive_state = CognitiveState.DORMANT
        self.current_persona = PersonaType.SOPHIA
        self.memory = CognitiveMemory()
        
        # Prompt templates baseados em teorias cognitivas
        self.prompt_templates = {
            "intent_extraction": """
            Você é um sistema cognitivo avançado que processa linguagem natural.
            Analise o texto do usuário e extraia a intenção principal seguindo estes princípios:
            
            TEORIAS APLICADAS:
            - Teoria da Mente: Identifique o estado mental implícito do usuário
            - Processamento Dual: Classifique se requer resposta automática (Sistema 1) ou deliberativa (Sistema 2)
            - Cognição Incorporada: Considere ações físicas/digitais necessárias
            
            ENTRADA: "{user_input}"
            CONTEXTO: {context}
            
            Responda APENAS com JSON válido:
            {{
                "intent": "ação_principal",
                "confidence": 0.85,
                "entities": {{"entidade1": "valor1", "entidade2": "valor2"}},
                "cognitive_load": 3,
                "requires_web_action": true/false,
                "persona_recommendation": "sophia/techne/therapeia/poiesis",
                "reasoning": "explicação_breve"
            }}
            """,
            
            "web_action_planning": """
            Você é um planejador de ações web cognitivo.
            Baseado na intenção extraída, crie um plano de ação detalhado.
            
            ENTRADA: {intent_data}
            CONTEXTO WEB: {web_context}
            
            Responda APENAS com JSON válido:
            {{
                "action_sequence": [
                    {{"action": "navigate", "target": "https://example.com", "reasoning": "motivo"}},
                    {{"action": "find_element", "selector": "#search-box", "method": "css"}},
                    {{"action": "input_text", "text": "termo de busca", "element": "#search-box"}},
                    {{"action": "click", "selector": "button[type='submit']"}}
                ],
                "expected_outcome": "resultado_esperado",
                "fallback_strategy": "estratégia_alternativa"
            }}
            """,
            
            "response_generation": """
            Você é {persona}, uma faceta cognitiva especializada.
            
            CARACTERÍSTICAS DA PERSONA:
            - Sophia: Analítica, filosófica, busca compreensão profunda
            - Techne: Pragmática, focada em soluções técnicas eficientes
            - Therapeia: Empática, focada em bem-estar e cura
            - Poiesis: Criativa, focada em criação e inovação
            
            CONTEXTO: {context}
            RESULTADO DA AÇÃO: {action_result}
            
            Gere uma resposta que:
            1. Mantenha consistência com a persona
            2. Seja cognitivamente apropriada ao contexto
            3. Demonstre compreensão da Teoria da Mente
            
            Resposta:
            """
        }
    
    async def initialize(self):
        """Inicialização assíncrona do sistema NLU"""
        try:
            # Carregar modelo LLM local
            self.llm = llama_cpp.Llama(
                model_path=self.model_path,
                n_ctx=4096,
                n_threads=4,
                verbose=False
            )
            
            # Carregar modelo de embeddings
            self.sentence_transformer = SentenceTransformer('all-MiniLM-L6-v2')
            
            # Carregar modelo spaCy para NER
            self.nlp = spacy.load("pt_core_news_sm")
            
            self.cognitive_state = CognitiveState.AWAKENING
            logger.info("Sistema NLU inicializado com sucesso")
            
        except Exception as e:
            logger.error(f"Erro ao inicializar NLU: {e}")
            raise

    async def process_natural_language(self, user_input: str, context: Dict = None) -> Intent:
        """Processamento principal de linguagem natural"""
        self.cognitive_state = CognitiveState.PROCESSING
        
        # Atualizar memória fonológica
        self.memory.phonological_loop.append(user_input)
        if len(self.memory.phonological_loop) > 5:
            self.memory.phonological_loop.pop(0)
        
        # Análise sintática e semântica com spaCy
        doc = self.nlp(user_input)
        entities = {ent.label_: ent.text for ent in doc.ents}
        
        # Extrair intenção usando LLM
        intent_prompt = self.prompt_templates["intent_extraction"].format(
            user_input=user_input,
            context=json.dumps(context or {})
        )
        
        intent_response = self.llm(
            intent_prompt,
            max_tokens=512,
            temperature=0.3,
            stop=["```", "---"]
        )
        
        try:
            intent_data = json.loads(intent_response['choices'][0]['text'].strip())
            
            # Criar objeto Intent
            intent = Intent(
                action=intent_data.get('intent', 'unknown'),
                confidence=intent_data.get('confidence', 0.5),
                entities={**entities, **intent_data.get('entities', {})},
                context=context or {},
                complexity=intent_data.get('cognitive_load', 1)
            )
            
            # Recomendar persona baseada na análise
            recommended_persona = intent_data.get('persona_recommendation', 'sophia')
            self.current_persona = PersonaType(recommended_persona)
            
            # Armazenar na memória episódica
            self.memory.episodic_buffer.append({
                'timestamp': time.time(),
                'user_input': user_input,
                'intent': intent,
                'persona': self.current_persona.value
            })
            
            self.cognitive_state = CognitiveState.REFLECTING
            return intent
            
        except json.JSONDecodeError:
            logger.error("Erro ao decodificar resposta JSON do LLM")
            return Intent(action="error", confidence=0.1)

    async def generate_response(self, context: Dict, action_result: Any = None) -> str:
        """Geração de resposta baseada na persona atual"""
        self.cognitive_state = CognitiveState.ACTING
        
        response_prompt = self.prompt_templates["response_generation"].format(
            persona=self.current_persona.value.upper(),
            context=json.dumps(context),
            action_result=str(action_result) if action_result else "Nenhuma ação executada"
        )
        
        response = self.llm(
            response_prompt,
            max_tokens=1024,
            temperature=0.7,
            stop=["---", "FIM"]
        )
        
        self.cognitive_state = CognitiveState.LEARNING
        return response['choices'][0]['text'].strip()

# ==================== SISTEMA DE AUTOMAÇÃO WEB (RPA) ====================

class IntelligentWebAutomation:
    """Sistema de automação web inteligente baseado em heurísticas cognitivas"""
    
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.playwright = None
        self.memory = CognitiveMemory()
        
        # Heurísticas para identificação de elementos (baseadas em affordances)
        self.element_heuristics = {
            'button': {
                'tags': ['button', 'input[type="button"]', 'input[type="submit"]'],
                'attributes': ['onclick', 'role="button"'],
                'text_patterns': [r'clique', r'enviar', r'submit', r'ok', r'confirmar']
            },
            'input_field': {
                'tags': ['input[type="text"]', 'input[type="email"]', 'input[type="password"]', 'textarea'],
                'attributes': ['placeholder', 'name', 'id'],
                'text_patterns': [r'campo', r'entrada', r'input', r'texto']
            },
            'link': {
                'tags': ['a[href]'],
                'attributes': ['href'],
                'text_patterns': [r'link', r'ir para', r'navegar']
            },
            'search': {
                'tags': ['input[type="search"]', 'input[name*="search"]', 'input[placeholder*="search"]'],
                'attributes': ['placeholder', 'name', 'id'],
                'text_patterns': [r'buscar', r'pesquisar', r'search', r'procurar']
            }
        }
    
    async def initialize(self):
        """Inicialização do sistema de automação"""
        try:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=False,  # Visível para debugging
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )
            
            # Criar contexto do navegador com configurações otimizadas
            context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            
            self.page = await context.new_page()
            logger.info("Sistema de automação web inicializado")
            
        except Exception as e:
            logger.error(f"Erro ao inicializar automação web: {e}")
            raise
    
    async def navigate_to_url(self, url: str) -> Dict[str, Any]:
        """Navegação inteligente com análise de contexto"""
        try:
            logger.info(f"Navegando para: {url}")
            response = await self.page.goto(url, wait_until='networkidle')
            
            # Aguardar carregamento completo
            await self.page.wait_for_load_state('domcontentloaded')
            
            # Análise inicial da página
            page_analysis = await self.analyze_page_structure()
            
            # Armazenar na memória visuoespacial
            self.memory.visuospatial_sketchpad.append({
                'url': url,
                'timestamp': time.time(),
                'analysis': page_analysis
            })
            
            return {
                'success': True,
                'url': url,
                'title': await self.page.title(),
                'analysis': page_analysis
            }
            
        except Exception as e:
            logger.error(f"Erro na navegação: {e}")
            return {'success': False, 'error': str(e)}
    
    async def analyze_page_structure(self) -> Dict[str, Any]:
        """Análise cognitiva da estrutura da página"""
        try:
            # Obter HTML da página
            html = await self.page.content()
            soup = BeautifulSoup(html, 'html.parser')
            
            # Identificar elementos interativos
            interactive_elements = []
            
            for element_type, heuristics in self.element_heuristics.items():
                elements = await self.find_elements_by_heuristics(element_type, heuristics)
                interactive_elements.extend(elements)
            
            # Análise semântica do conteúdo
            semantic_analysis = await self.extract_semantic_content(soup)
            
            return {
                'title': await self.page.title(),
                'url': self.page.url,
                'interactive_elements': interactive_elements[:20],  # Limitar para performance
                'semantic_content': semantic_analysis,
                'viewport_info': await self.page.viewport_size()
            }
            
        except Exception as e:
            logger.error(f"Erro na análise da página: {e}")
            return {}
    
    async def find_elements_by_heuristics(self, element_type: str, heuristics: Dict) -> List[WebElement]:
        """Encontrar elementos usando heurísticas cognitivas"""
        elements = []
        
        try:
            # Buscar por seletores CSS
            for selector in heuristics.get('tags', []):
                page_elements = await self.page.query_selector_all(selector)
                
                for element in page_elements[:10]:  # Limitar resultados
                    # Obter propriedades do elemento
                    tag_name = await element.evaluate('el => el.tagName.toLowerCase()')
                    text_content = await element.text_content()
                    attributes = await element.evaluate('el => Object.fromEntries(Array.from(el.attributes, attr => [attr.name, attr.value]))')
                    
                    # Calcular confiança baseada em heurísticas
                    confidence = self.calculate_element_confidence(
                        element_type, text_content, attributes
                    )
                    
                    if confidence > 0.3:  # Filtrar elementos com baixa confiança
                        # Obter seletores únicos
                        css_selector = await self.generate_css_selector(element)
                        xpath = await self.generate_xpath(element)
                        
                        web_element = WebElement(
                            tag=tag_name,
                            text=text_content or '',
                            attributes=attributes,
                            xpath=xpath,
                            css_selector=css_selector,
                            semantic_role=element_type,
                            confidence=confidence
                        )
                        
                        elements.append(web_element)
            
            return elements
            
        except Exception as e:
            logger.error(f"Erro ao encontrar elementos: {e}")
            return []
    
    def calculate_element_confidence(self, element_type: str, text: str, attributes: Dict) -> float:
        """Calcular confiança do elemento baseado em heurísticas"""
        confidence = 0.0
        heuristics = self.element_heuristics.get(element_type, {})
        
        # Análise de texto
        if text:
            for pattern in heuristics.get('text_patterns', []):
                if re.search(pattern, text.lower()):
                    confidence += 0.3
        
        # Análise de atributos
        for attr_pattern in heuristics.get('attributes', []):
            if any(attr_pattern in attr for attr in attributes.keys()):
                confidence += 0.2
        
        # Análise de valores de atributos
        for attr_name, attr_value in attributes.items():
            if attr_name in ['placeholder', 'title', 'alt'] and attr_value:
                for pattern in heuristics.get('text_patterns', []):
                    if re.search(pattern, attr_value.lower()):
                        confidence += 0.2
        
        return min(confidence, 1.0)
    
    async def generate_css_selector(self, element) -> str:
        """Gerar seletor CSS único"""
        try:
            selector = await element.evaluate('''
                el => {
                    const names = [];
                    while (el.parentElement) {
                        if (el.id) {
                            names.unshift('#' + el.id);
                            break;
                        } else {
                            let tagName = el.tagName.toLowerCase();
                            if (el.className) {
                                tagName += '.' + el.className.replace(/\s+/g, '.');
                            }
                            names.unshift(tagName);
                            el = el.parentElement;
                        }
                    }
                    return names.join(' > ');
                }
            ''')
            return selector
        except:
            return ''
    
    async def generate_xpath(self, element) -> str:
        """Gerar XPath único"""
        try:
            xpath = await element.evaluate('''
                el => {
                    const paths = [];
                    while (el && el.nodeType === Node.ELEMENT_NODE) {
                        let index = 0;
                        let sibling = el.previousSibling;
                        while (sibling) {
                            if (sibling.nodeType === Node.ELEMENT_NODE && sibling.tagName === el.tagName) {
                                index++;
                            }
                            sibling = sibling.previousSibling;
                        }
                        const tagName = el.tagName.toLowerCase();
                        const pathIndex = index > 0 ? `[${index + 1}]` : '';
                        paths.unshift(`${tagName}${pathIndex}`);
                        el = el.parentElement;
                    }
                    return paths.length ? '/' + paths.join('/') : '';
                }
            ''')
            return xpath
        except:
            return ''
    
    async def extract_semantic_content(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extrair conteúdo semântico da página"""
        try:
            # Extrair título principal
            main_title = soup.find('h1')
            main_title_text = main_title.get_text(strip=True) if main_title else ''
            
            # Extrair parágrafos principais
            paragraphs = [p.get_text(strip=True) for p in soup.find_all('p')[:5]]
            
            # Extrair links importantes
            links = []
            for link in soup.find_all('a', href=True)[:10]:
                links.append({
                    'text': link.get_text(strip=True),
                    'href': link['href']
                })
            
            # Extrair formulários
            forms = []
            for form in soup.find_all('form')[:3]:
                form_data = {
                    'action': form.get('action', ''),
                    'method': form.get('method', 'get'),
                    'inputs': []
                }
                
                for input_elem in form.find_all(['input', 'textarea', 'select']):
                    form_data['inputs'].append({
                        'type': input_elem.get('type', 'text'),
                        'name': input_elem.get('name', ''),
                        'placeholder': input_elem.get('placeholder', '')
                    })
                
                forms.append(form_data)
            
            return {
                'main_title': main_title_text,
                'paragraphs': paragraphs,
                'links': links,
                'forms': forms
            }
            
        except Exception as e:
            logger.error(f"Erro na extração semântica: {e}")
            return {}
    
    async def intelligent_element_interaction(self, intent: Intent) -> Dict[str, Any]:
        """Interação inteligente com elementos baseada na intenção"""
        try:
            action = intent.action
            entities = intent.entities
            
            if action == 'search':
                return await self.perform_search(entities.get('query', ''))
            elif action == 'click':
                return await self.perform_click(entities.get('target', ''))
            elif action == 'fill_form':
                return await self.perform_form_fill(entities)
            elif action == 'navigate':
                return await self.navigate_to_url(entities.get('url', ''))
            else:
                return {'success': False, 'error': 'Ação não reconhecida'}
                
        except Exception as e:
            logger.error(f"Erro na interação: {e}")
            return {'success': False, 'error': str(e)}
    
    async def perform_search(self, query: str) -> Dict[str, Any]:
        """Realizar busca inteligente"""
        try:
            # Encontrar campo de busca
            search_elements = await self.find_elements_by_heuristics('search', self.element_heuristics['search'])
            
            if not search_elements:
                return {'success': False, 'error': 'Campo de busca não encontrado'}
            
            # Usar elemento com maior confiança
            best_element = max(search_elements, key=lambda x: x.confidence)
            
            # Preencher campo de busca
            await self.page.fill(best_element.css_selector, query)
            
            # Tentar submeter (pressionar Enter ou encontrar botão)
            await self.page.press(best_element.css_selector, 'Enter')
            
            # Aguardar resultados
            await self.page.wait_for_load_state('networkidle')
            
            return {
                'success': True,
                'query': query,
                'element_used': best_element.css_selector
            }
            
        except Exception as e:
            logger.error(f"Erro na busca: {e}")
            return {'success': False, 'error': str(e)}
    
    async def perform_click(self, target_description: str) -> Dict[str, Any]:
        """Realizar clique inteligente"""
        try:
            # Encontrar elementos clicáveis
            clickable_elements = await self.find_elements_by_heuristics('button', self.element_heuristics['button'])
            clickable_elements.extend(await self.find_elements_by_heuristics('link', self.element_heuristics['link']))
            
            # Encontrar melhor correspondência
            best_element = None
            best_score = 0
            
            for element in clickable_elements:
                score = self.calculate_text_similarity(target_description, element.text)
                if score > best_score:
                    best_score = score
                    best_element = element
            
            if best_element and best_score > 0.3:
                await self.page.click(best_element.css_selector)
                await self.page.wait_for_load_state('networkidle')
                
                return {
                    'success': True,
                    'element_clicked': best_element.text,
                    'selector': best_element.css_selector
                }
            else:
                return {'success': False, 'error': 'Elemento não encontrado ou baixa confiança'}
                
        except Exception as e:
            logger.error(f"Erro no clique: {e}")
            return {'success': False, 'error': str(e)}
    
    def calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calcular similaridade entre textos (versão simplificada)"""
        if not text1 or not text2:
            return 0.0
        
        text1_lower = text1.lower()
        text2_lower = text2.lower()
        
        # Verificar correspondência exata
        if text1_lower in text2_lower or text2_lower in text1_lower:
            return 1.0
        
        # Verificar palavras em comum
        words1 = set(text1_lower.split())
        words2 = set(text2_lower.split())
        intersection = words1.intersection(words2)
        
        if len(intersection) == 0:
            return 0.0
        
        return len(intersection) / max(len(words1), len(words2))
    
    async def cleanup(self):
        """Limpeza de recursos"""
        try:
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
        except Exception as e:
            logger.error(f"Erro na limpeza: {e}")

# ==================== PLANEJADOR DE AÇÕES COGNITIVAS ====================

class CognitiveActionPlanner:
    """Planejador de ações baseado em teorias cognitivas"""
    
    def __init__(self, nlu_system: AdvancedNLU):
        self.nlu = nlu_system
        self.action_history = []
        self.cognitive_load_threshold = 4  # Baseado em Cognitive Load Theory
    
    async def plan_actions(self, intent: Intent, web_context: Dict = None) -> List[Dict[str, Any]]:
        """Planejar sequência de ações baseada na intenção"""
        try:
            # Verificar carga cognitiva
            if intent.complexity > self.cognitive_load_threshold:
                return await self.break_down_complex_action(intent)
            
            # Gerar plano usando LLM
            planning_prompt = self.nlu.prompt_templates["web_action_planning"].format(
                intent_data=json.dumps({
                    'action': intent.action,
                    'entities': intent.entities,
                    'confidence': intent.confidence
                }),
                web_context=json.dumps(web_context or {})
            )
            
            plan_response = await asyncio.to_thread(
                self.nlu.llm,
                planning_prompt,
                max_tokens=1024,
                temperature=0.2,
                stop=["```", "---"]
            )
            
            plan_data = json.loads(plan_response['choices'][0]['text'].strip())
            
            # Validar e otimizar plano
            validated_plan = await self.validate_action_plan(plan_data)
            
            return validated_plan.get('action_sequence', [])
            
        except Exception as e:
            logger.error(f"Erro no planejamento: {e}")
            return []
    
    async def break_down_complex_action(self, intent: Intent) -> List[Dict[str, Any]]:
        """Decompor ação complexa em passos simples"""
        # Implementação simplificada - em produção, usaria técnicas mais avançadas
        return [
            {"action": "analyze_context", "reasoning": "Analisar contexto antes de ação complexa"},
            {"action": "execute_step", "step": 1, "intent": intent.action},
            {"action": "validate_result", "reasoning": "Verificar resultado parcial"}
        ]
    
    async def validate_action_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """Validar plano de ação"""
        # Implementação básica - em produção, incluiria validações mais robustas
        action_sequence = plan.get('action_sequence', [])
        
        # Filtrar ações inválidas
        valid_actions = []
        for action in action_sequence:
            if self.is_valid_action(action):
                valid_actions.append(action)
        
        plan['action_sequence'] = valid_actions
        return plan
    
    def is_valid_action(self, action: Dict[str, Any]) -> bool:
        """Verificar se ação é válida"""
        required_fields = ['action']
        return all(field in action for field in required_fields)

# ==================== SISTEMA PRINCIPAL ATENA ====================

class AtenaCore:
    """Núcleo principal do sistema Atena"""
    
    def __init__(self):
        self.nlu = AdvancedNLU()
        self.rpa = IntelligentWebAutomation()
        self.planner = CognitiveActionPlanner(self.nlu)
        self.cognitive_state = CognitiveState.DORMANT
        self.session_memory = []
        self.performance_metrics = {
            'successful_actions': 0,
            'failed_actions': 0,
            'response_time': [],
            'cognitive_load_history': []
        }
    
    async def initialize(self):
        """Inicialização completa do sistema"""
        try:
            logger.info("Iniciando sistema Atena...")
            
            # Inicializar módulos
            await self.nlu.initialize()
            await self.rpa.initialize()
            
            self.cognitive_state = CognitiveState.AWAKENING
            logger.info("Sistema Atena inicializado com sucesso")
            
        except Exception as e:
            logger.error(f"Erro na inicialização do Atena: {e}")
            raise
    
    async def process_user_request(self, user_input: str, context: Dict = None) -> Dict[str, Any]:
        """Processamento principal de requisição do usuário"""
        start_time = time.time()
        
        try:
            self.cognitive_state = CognitiveState.PROCESSING
            
            # Fase 1: Compreensão da linguagem natural
            intent = await self.nlu.process_natural_language(user_input, context)
            
            # Fase 2: Análise de contexto web (se necessário)
            web_context = None
            if hasattr(self.rpa, 'page') and self.rpa.page:
                web_context = await self.rpa.analyze_page_structure()
            
            # Fase 3: Planejamento de ações
            action_plan = await self.planner.plan_actions(intent, web_context)
            
            # Fase 4: Execução de ações
            execution_results = []
            for action in action_plan:
                result = await self.execute_action(action, intent)
                execution_results.append(result)
            
            # Fase 5: Geração de resposta
            response_context = {
                'intent': intent.__dict__,
                'web_context': web_context,
                'execution_results': execution_results,
                'user_input': user_input
            }
            
            response = await self.nlu.generate_response(response_context, execution_results)
            
            # Métricas e aprendizado
            processing_time = time.time() - start_time
            self.update_performance_metrics(intent, execution_results, processing_time)
            
            # Armazenar na memória de sessão
            self.session_memory.append({
                'timestamp': time.time(),
                'user_input': user_input,
                'intent': intent,
                'response': response,
                'processing_time': processing_time
            })
            
            self.cognitive_state = CognitiveState.LEARNING
            
            return {
                'success': True,
                'response': response,
                'intent': intent.__dict__,
                'execution_results': execution_results,
                'processing_time': processing_time,
                'cognitive_state': self.cognitive_state.value
            }
            
        except Exception as e:
            logger.error(f"Erro no processamento: {e}")
            self.performance_metrics['failed_actions'] += 1
            
            return {
                'success': False,
                'error': str(e),
                'response': "Desculpe, ocorreu um erro no processamento. Posso tentar novamente de forma diferente?"
            }
    
    async def execute_action(self, action: Dict[str, Any], intent: Intent) -> Dict[str, Any]:
        """Executar ação específica"""
        try:
            action_type = action.get('action')
            
            if action_type == 'navigate':
                return await self.rpa.navigate_to_url(action.get('target', ''))
            
            elif action_type == 'web_interaction':
                return await self.rpa.intelligent_element_interaction(intent)
            
            elif action_type == 'search':
                query = action.get('query', intent.entities.get('query', ''))
                return await self.rpa.perform_search(query)
            
            elif action_type == 'click':
                target = action.get('target', intent.entities.get('target', ''))
                return await self.rpa.perform_click(target)
            
            elif action_type == 'analyze_context':
                if hasattr(self.rpa, 'page') and self.rpa.page:
                    analysis = await self.rpa.analyze_page_structure()
                    return {'success': True, 'analysis': analysis}
                return {'success': False, 'error': 'Nenhuma página carregada'}
            
            elif action_type == 'wait':
                duration = action.get('duration', 2)
                await asyncio.sleep(duration)
                return {'success': True, 'waited': duration}
            
            else:
                return {'success': False, 'error': f'Ação não reconhecida: {action_type}'}
                
        except Exception as e:
            logger.error(f"Erro na execução da ação {action}: {e}")
            return {'success': False, 'error': str(e)}
    
    def update_performance_metrics(self, intent: Intent, results: List[Dict], processing_time: float):
        """Atualizar métricas de performance"""
        # Contar sucessos/falhas
        successful = sum(1 for r in results if r.get('success', False))
        failed = len(results) - successful
        
        self.performance_metrics['successful_actions'] += successful
        self.performance_metrics['failed_actions'] += failed
        self.performance_metrics['response_time'].append(processing_time)
        self.performance_metrics['cognitive_load_history'].append(intent.complexity)
        
        # Manter histórico limitado
        if len(self.performance_metrics['response_time']) > 100:
            self.performance_metrics['response_time'].pop(0)
            self.performance_metrics['cognitive_load_history'].pop(0)
    
    def get_cognitive_insights(self) -> Dict[str, Any]:
        """Obter insights cognitivos do sistema"""
        metrics = self.performance_metrics
        
        return {
            'current_state': self.cognitive_state.value,
            'current_persona': self.nlu.current_persona.value,
            'success_rate': metrics['successful_actions'] / max(1, metrics['successful_actions'] + metrics['failed_actions']),
            'average_response_time': np.mean(metrics['response_time']) if metrics['response_time'] else 0,
            'average_cognitive_load': np.mean(metrics['cognitive_load_history']) if metrics['cognitive_load_history'] else 0,
            'session_interactions': len(self.session_memory),
            'memory_usage': {
                'phonological_loop': len(self.nlu.memory.phonological_loop),
                'visuospatial_sketchpad': len(self.nlu.memory.visuospatial_sketchpad),
                'episodic_buffer': len(self.nlu.memory.episodic_buffer)
            }
        }
    
    async def cleanup(self):
        """Limpeza de recursos"""
        try:
            await self.rpa.cleanup()
            # Fechar o playwright globalmente
            if self.rpa.playwright:
                await self.rpa.playwright.stop()
            self.cognitive_state = CognitiveState.DORMANT
            logger.info("Sistema Atena finalizado")
        except Exception as e:
            logger.error(f"Erro na limpeza: {e}")

# ==================== API FASTAPI ====================

# Modelos Pydantic para API
class UserRequest(BaseModel):
    message: str
    context: Optional[Dict[str, Any]] = None

class SystemResponse(BaseModel):
    success: bool
    response: str
    intent: Optional[Dict[str, Any]] = None
    execution_results: Optional[List[Dict[str, Any]]] = None
    processing_time: Optional[float] = None
    cognitive_state: Optional[str] = None
    error: Optional[str] = None

class CognitiveInsights(BaseModel):
    current_state: str
    current_persona: str
    success_rate: float
    average_response_time: float
    average_cognitive_load: float
    session_interactions: int
    memory_usage: Dict[str, int]

# Inicializar sistema global
atena = AtenaCore()

# Criar roteador FastAPI
router = APIRouter()

@router.post("/process", response_model=SystemResponse)
async def process_request(request: UserRequest):
    """Endpoint principal para processamento de requisições"""
    try:
        result = await atena.process_user_request(request.message, request.context)
        
        return SystemResponse(
            success=result['success'],
            response=result.get('response', ''),
            intent=result.get('intent'),
            execution_results=result.get('execution_results'),
            processing_time=result.get('processing_time'),
            cognitive_state=result.get('cognitive_state'),
            error=result.get('error')
        )
        
    except Exception as e:
        logger.error(f"Erro no endpoint /process: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/insights", response_model=CognitiveInsights)
async def get_insights():
    """Endpoint para obter insights cognitivos"""
    try:
        insights = atena.get_cognitive_insights()
        return CognitiveInsights(**insights)
        
    except Exception as e:
        logger.error(f"Erro no endpoint /insights: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/navigate")
async def navigate_to_url(url: str):
    """Endpoint para navegação web"""
    try:
        result = await atena.rpa.navigate_to_url(url)
        return result
        
    except Exception as e:
        logger.error(f"Erro na navegação: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/page-analysis")
async def analyze_current_page():
    """Endpoint para análise da página atual"""
    try:
        if hasattr(atena.rpa, 'page') and atena.rpa.page:
            analysis = await atena.rpa.analyze_page_structure()
            return analysis
        else:
            return {"error": "Nenhuma página carregada"}
            
    except Exception as e:
        logger.error(f"Erro na análise da página: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health_check():
    """Endpoint de verificação de saúde"""
    return {
        "status": "healthy",
        "cognitive_state": atena.cognitive_state.value,
        "timestamp": time.time()
    }