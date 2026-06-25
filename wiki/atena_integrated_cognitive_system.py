# atena_integrated_cognitive_system.py
# Versão: 1.1 - Busca Web Integrada

import asyncio
import logging
from typing import Dict, Any, Optional
import numpy as np
import json

# --- Importação dos Módulos Principais da Atena ---
from atena_etica import AtenaEthicalFramework, ActionContext
from atena_integridade_cognitiva import ProtocoloDeIntegridadeCognitiva
from atena_inteligencia import AtenaCognitiveArchitecture
from atena_rpa_engine import EnhancedAtenaRPAAgent as AtenaRPAAgent, ConfigManager as RPAConfigManager
from auto_gerador_codigos_V2 import AutoCodeConstructorFacade, ProblemContext
from atena_web import AtenaWebSearchEngine
from atena_config import AtenaConfig
from atena_langchain_core import AtenaLangChainManager
from atena_user_model import UserBehaviorTracker
from atena_motor_voz import AtenaVoiceMotor # Adicionado para integração de voz

# Configuração de logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(name)s: %(message)s")
logger = logging.getLogger("AtenaCognitiveSystem")

class AtenaIntegratedCognitiveSystem:
    """
    Sistema Cognitivo Integrado da Atena.
    Orquestra as interações entre todos os módulos, agora com busca web.
    """

    def __init__(self, config: AtenaConfig):
        self.config = config
        self._langchain_manager: Optional[AtenaLangChainManager] = None # NOVO: Inicializa como None para lazy loading
        self._initialize_components()
        logger.info("Sistema Cognitivo Integrado da Atena (v1.1) inicializado com sucesso.")

    def _initialize_components(self):
        """Inicializa todas as instâncias dos módulos da Atena."""
        logger.info("Inicializando componentes do ecossistema Atena...")

        # Camada de Governança
        self.ethical_framework = AtenaEthicalFramework()
        self.cognitive_integrity_protocol = ProtocoloDeIntegridadeCognitiva()

        # Camada de Inteligência Cognitiva (O Cérebro)
        self.cognitive_architecture = AtenaCognitiveArchitecture(self.config)
        
        # Camada de Ação e Geração (As Mãos)
        self.rpa_config_manager = RPAConfigManager()
        self.rpa_agent = AtenaRPAAgent(self.rpa_config_manager)
        self.code_generator = AutoCodeConstructorFacade()

        # --- NOVO COMPONENTE: Motor de Busca Web ---
        self.web_search_engine = AtenaWebSearchEngine(self.config)
        logger.info("Motor de Busca Web instanciado.")

        # --- Modelo de Usuário ---
        self.user_model = UserBehaviorTracker()
        logger.info("Modelo de Comportamento do Usuário instanciado.")

        # --- Motor de Voz (STT/Correção) ---
        self.voice_motor = AtenaVoiceMotor()
        logger.info("Motor de Voz (STT/Correção) instanciado.")

    @property
    def langchain_manager(self) -> AtenaLangChainManager:
        """Carrega o AtenaLangChainManager sob demanda."""
        if self._langchain_manager is None:
            logger.info("Inicializando AtenaLangChainManager (lazy loading)...")
            langchain_config = {
                "atena_config_instance": self.config,
                "rpa_config_manager_instance": self.rpa_config_manager,
                "cognitive_architecture_instance": self.cognitive_architecture # NOVO: Passa a instância da arquitetura cognitiva
            }
            self._langchain_manager = AtenaLangChainManager(config=langchain_config)
        return self._langchain_manager

    async def process_user_request(self, request_text: str, user_id: str = "Senhor Robério", context_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Orquestra o fluxo de processamento cognitivo completo, incluindo busca web.
        """
        logger.info(f"Processando requisição de '{user_id}': '{request_text[:100]}...'")
        
        # Inicializar context_data se não fornecido
        if context_data is None:
            context_data = {}

        # Extrair o ID da IA selecionada do início do request_text
        selected_ai = "atena-local" # Default
        original_request_text = request_text
        import re
        match = re.match(r"^\[(.*?)\]\\s*(.*)", request_text)
        if match:
            selected_ai = match.group(1)
            request_text = match.group(2).strip() # Remove o prefixo e espaços
            logger.info(f"IA selecionada: {selected_ai}. Texto do prompt: '{request_text[:100]}...'")
        else:
            logger.warning(f"Formato de prompt inesperado. Usando IA padrão: {selected_ai}. Prompt original: '{original_request_text[:100]}...'")

        # --- Lógica de roteamento baseada na IA selecionada ---
        if selected_ai == "rpa_executar_tarefa":
            logger.info("Acionando RPA para execução de tarefa...")
            # Aqui você precisaria de uma forma de extrair a URL e a descrição da tarefa
            # Por enquanto, vamos simular com um exemplo simples
            task_description = request_text
            try:
                rpa_result = await self.rpa_agent.execute_task(task_description)
                return {
                    "status": "success",
                    "response": f"RPA executado com sucesso: {rpa_result}",
                    "details": {"source": "rpa_engine"}
                }
            except Exception as e:
                logger.error(f"Erro ao executar RPA: {e}", exc_info=True)
                return {"status": "failed", "reason": "rpa_execution_error", "details": str(e)}

        elif selected_ai == "openai-gpt4" or selected_ai == "google-gemini":
            logger.info(f"Encaminhando para LLM externo ({selected_ai})...")
            # Aqui você integraria com a API da OpenAI ou Google Gemini
            # Por enquanto, vamos simular uma resposta
            return {
                "status": "success",
                "response": f"Simulação de resposta de {selected_ai} para: '{request_text}'",
                "details": {"source": selected_ai}
            }

        elif selected_ai == "langchain-agent":
            logger.info("Requisição detectada para usar LangChain. Acionando...")
            try:
                langchain_response = await self.langchain_manager.run_agent_task(request_text)
                return {
                    "status": "success",
                    "response": f"Resposta via LangChain: {langchain_response}",
                    "details": {"source": "langchain_agent"}
                }
            except NotImplementedError as e:
                logger.warning(f"Funcionalidade LangChain solicitada, mas não implementada: {e}")
                return {"status": "failed", "reason": "langchain_not_implemented", "details": str(e)}
            except Exception as e:
                logger.error(f"Erro ao usar LangChain: {e}", exc_info=True)
                return {"status": "failed", "reason": "langchain_error", "details": str(e)}
        else: # Este bloco será executado se nenhuma IA específica for selecionada
            # 1. Validação Ética Preliminar
            action_context = ActionContext(action_type="user_request", description=request_text, parameters={"user_id": user_id})
            ethical_validation_result = self.ethical_framework.validate_action(action_context)
            
            if not ethical_validation_result.is_approved:
                logger.warning(f"Requisição bloqueada eticamente: {ethical_validation_result.reason}")
                return {"status": "blocked", "reason": "ethical_violation", "details": ethical_validation_result.reason}

            # 2. Processamento Cognitivo e Geração da Resposta
            use_memory = context_data.get("use_memory", True)  # Por padrão, usa memória
            use_web_search = context_data.get("use_web_search", False)  # Por padrão, não usa busca web
            use_user_model = context_data.get("use_user_model", False)  # Por padrão, não usa modelo de usuário
            
            relevant_knowledge = ""
            cognitive_context = {"prompt": request_text, "chunks_memoria": []}
            
            # Busca na memória se solicitado
            if use_memory:
                logger.info("Buscando conhecimento relevante na memória interna...")
                memory_results = await self.cognitive_architecture.search_memory(request_text)
                relevant_knowledge = "\n".join([chunk.text for chunk in memory_results])
                cognitive_context["chunks_memoria"] = [chunk.text for chunk in memory_results]

            # Gerar resposta com base no conhecimento encontrado ou buscar na web
            if relevant_knowledge:
                logger.info("Conhecimento encontrado na memória interna.")
                generated_response_text = f"Com base no meu conhecimento sobre o assunto, encontrei o seguinte: {relevant_knowledge}"
            elif use_web_search:
                logger.info("Nenhum conhecimento relevante na memória interna. Acionando busca web.")
                try:
                    web_results = await self.web_search_engine.search(request_text, max_results=3)
                    if web_results:
                        snippets = [f"- {res.title}: {res.snippet}" for res in web_results]
                        formatted_web_results = "\n".join(snippets)
                        generated_response_text = f"Não encontrei informações em minha memória, mas realizei uma busca na web e encontrei o seguinte:\n{formatted_web_results}"
                        cognitive_context["web_search_results"] = [res.to_dict() for res in web_results]
                    else:
                        generated_response_text = f"Não possuo informações diretas sobre '{request_text}' e não encontrei resultados na busca web."
                except Exception as e:
                    logger.error(f"Erro durante a busca web: {e}", exc_info=True)
                    generated_response_text = f"Tentei buscar na web, mas ocorreu um erro. Não posso responder sobre '{request_text}' no momento."
            else:
                generated_response_text = f"Não possuo informações diretas sobre '{request_text}' e a busca web não foi solicitada."
            
            # Aplicar modelo de usuário se solicitado
            if use_user_model and hasattr(self, "user_model"):
                try:
                    user_insights = self.user_model.analyze_request(request_text)
                    generated_response_text += f"\n\nBaseado no seu histórico de interações, notei que você tem interesse em {user_insights.get('preferred_context', 'tópicos variados')}."
                except Exception as e:
                    logger.error(f"Erro ao aplicar modelo de usuário: {e}", exc_info=True)
            
            # Simulação de logprobs para o Protocolo de Integridade
            generated_response_logprobs = [-0.1 * (i + 1) for i in range(len(generated_response_text.split()))]

            # 3. Validação de Integridade Cognitiva
            logger.info("Validando integridade da resposta gerada...")
            integrity_result = self.cognitive_integrity_protocol.validar_resposta(
                {"texto": generated_response_text, "logprobs": generated_response_logprobs},
                cognitive_context
            )
            
            if integrity_result.decisao_final == "REJEITADA":
                logger.warning(f"Resposta gerada rejeitada por baixa integridade: {integrity_result.nivel_integridade}")
                return {"status": "failed", "reason": "low_cognitive_integrity", "details": integrity_result.nivel_integridade}
            
            logger.info("Resposta validada com sucesso. Verificando ações específicas...")

            # 4. Ação Específica (RPA / Geração de Código)
            if "automatizar" in request_text.lower() or "gerar código" in request_text.lower():
                logger.info("Requisição de automação/código detectada. Acionando gerador.")
                problem_context = ProblemContext(
                    description=f"Ação solicitada: {request_text}",
                    html_snapshot="<html><body><p>Contexto HTML a ser fornecido em um cenário real.</p></body></html>", # Simulação
                    target_url="Não especificado"
                )
                
                code_solution = await self.code_generator.generate_automation_code(
                    error_context="Nova solicitação de automação.",
                    html_content=problem_context.html_snapshot,
                    target_action=request_text
                )
                
                return {
                    "status": "success", 
                    "response": generated_response_text, 
                    "code_solution": code_solution,
                    "integrity_report": integrity_result.relatorio_fatos
                }

            # 5. Resposta ao Usuário (sem ação específica)
            logger.info("Retornando resposta padrão ao usuário.")
            return {
                "status": "success",
                "response": generated_response_text,
                "integrity_report": integrity_result.relatorio_fatos
            }

    async def start(self):
        """Inicia os componentes de fundo, como a arquitetura cognitiva."""
        await self.cognitive_architecture.start()

    async def shutdown(self):
        """Finaliza os componentes de fundo de forma graciosa."""
        logger.info("Encerrando o Sistema Cognitivo Integrado da Atena.")
        await self.cognitive_architecture.stop()
        if hasattr(self.rpa_agent, 'cleanup'):
            self.rpa_agent.cleanup()
        if hasattr(self.web_search_engine, 'close'):
            await self.web_search_engine.close()
        if hasattr(self, 'voice_motor'):
            self.voice_motor.shutdown()

