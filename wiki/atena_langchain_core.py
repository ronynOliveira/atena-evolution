import logging
from typing import Optional, Dict, Any
from threading import Lock

# Importações do LangChain (serão carregadas sob demanda)
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
# from langchain_community.chat_models import ChatOpenAI # Exemplo, pode ser Gemini, etc.
from langchain.agents import AgentExecutor, create_react_agent
from langchain.tools import Tool
from langchain.chains import RetrievalQA
# from langchain_community.vectorstores import Chroma # Exemplo de VectorStore

# Importações para as ferramentas
from atena_web import AtenaWebSearchEngine, SearchResult
from atena_rpa_engine import EnhancedAtenaRPAAgent, ConfigManager as RPAConfigManager, ExecutionContext
from atena_config import AtenaConfig # Importar AtenaConfig aqui para evitar circular dependency

logger = logging.getLogger(__name__)

class AtenaLangChainManager:
    """
    Gerencia a inicialização e o acesso aos componentes do LangChain
    com carregamento sob demanda (lazy loading).
    """
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self._config = config if config is not None else {}
        self._llm: Optional[Any] = None
        self._vectorstore: Optional[Any] = None
        self._agent_executor: Optional[Any] = None
        self._lock = Lock()
        logger.info("AtenaLangChainManager inicializado (componentes LangChain em lazy loading).")

    @property
    def llm(self) -> Any:
        """Carrega o modelo de linguagem (LLM) sob demanda."""
        with self._lock:
            if self._llm is None:
                logger.info("Carregando LLM do LangChain...")
                # Exemplo: Carregar um modelo OpenAI ou Gemini
                # self._llm = ChatOpenAI(model="gpt-4", temperature=0.7)
                # Ou para Gemini:
                # import google.generativeai as genai
                # genai.configure(api_key=self._config.get("GEMINI_API_KEY"))
                # self._llm = genai.GenerativeModel('gemini-pro')
                import google.generativeai as genai
                genai.configure(api_key=self._config.get("GEMINI_API_KEY"))
                self._llm = genai.GenerativeModel('gemini-pro')
            return self._llm

    @property
    def vectorstore(self) -> Any:
        """Carrega o VectorStore (ChromaDB, etc.) sob demanda."""
        with self._lock:
            if self._vectorstore is None:
                logger.info("Carregando VectorStore do LangChain...")
                provider = self._config.get("llm_provider", "google")
                embedding_function = None

                if provider == "local":
                    try:
                        from langchain_community.embeddings import HuggingFaceEmbeddings
                        embedding_function = HuggingFaceEmbeddings(
                            model_name="sentence-transformers/all-MiniLM-L6-v2",
                            model_kwargs={'device': self._config.get('device', 'cpu')}
                        )
                    except ImportError:
                        raise ImportError("sentence-transformers não está instalado. Execute 'pip install sentence-transformers'.")
                else:
                    # Fallback para OpenAIEmbeddings como placeholder para outros provedores
                    from langchain_community.embeddings import OpenAIEmbeddings
                    embedding_function = OpenAIEmbeddings()

                from langchain_community.vectorstores import Chroma
                self._vectorstore = Chroma(
                    persist_directory="./data/chroma_db", 
                    embedding_function=embedding_function
                )
            return self._vectorstore

    @property
    def agent_executor(self) -> Any:
        """Carrega o AgentExecutor sob demanda."""
        with self._lock:
            if self._agent_executor is None:
                logger.info("Carregando AgentExecutor do LangChain...")
                # Exemplo: Criar um agente ReAct
                # from langchain.agents import AgentExecutor, create_react_agent
                # from langchain.tools import Tool
                # tools = [
                #     Tool(
                #         name="WebSearch",
                #         func=lambda q: "Resultado da busca na web para " + q, # Substituir por função real de busca
                #         description="Útil para responder perguntas sobre eventos atuais."
                #     )
                # ]
                # prompt = ChatPromptTemplate.from_messages([
                #     ("system", "Você é um assistente útil."),
                
                # ])
                # agent = create_react_agent(self.llm, tools, prompt)
                # self._agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
                # Instanciar AtenaWebSearchEngine e EnhancedAtenaRPAAgent
                # Assumindo que self._config contém as instâncias ou dados para criá-las
                atena_config_instance = self._config.get("atena_config_instance")
                if not atena_config_instance:
                    logger.warning("AtenaConfig instance not found in LangChainManager config. Creating a default one.")
                    atena_config_instance = AtenaConfig() # Fallback to default if not provided

                rpa_config_manager_instance = self._config.get("rpa_config_manager_instance")
                if not rpa_config_manager_instance:
                    logger.warning("RPAConfigManager instance not found in LangChainManager config. Creating a default one.")
                    rpa_config_manager_instance = RPAConfigManager() # Fallback to default if not provided

                web_search_engine = AtenaWebSearchEngine(atena_config_instance)
                # rpa_agent = EnhancedAtenaRPAAgent(rpa_config_manager_instance) # RPA Agent agora é gerenciado pelas funções wrapper

                tools = [
                    Tool(
                        name="WebSearch",
                        func=web_search_engine.search,
                        description="Útil para responder perguntas sobre eventos atuais ou buscar informações na web. Recebe uma query de busca e retorna uma lista de resultados."
                    ),
                    Tool(
                        name="GetPageContent",
                        func=web_search_engine.get_page_content,
                        description="Útil para extrair o conteúdo textual de uma URL específica. Recebe uma URL e retorna o texto da página."
                    ),
                    Tool(
                        name="SearchMemory", # NOVO
                        func=self._search_memory_tool, # Usa o wrapper assíncrono
                        description="Útil para buscar informações na memória interna da Atena. Recebe uma query de busca e retorna conhecimento relevante."
                    ),
                    Tool(
                        name="RPAInitializeSession",
                        func=self._initialize_rpa_session, # Usa o wrapper
                        description="Inicializa uma nova sessão de navegador para o RPA. Deve ser chamado antes de qualquer interação RPA. Recebe 'session_id' (string única), 'user_id' (opcional, string), 'ai_type' (opcional, string)."
                    ),
                    Tool(
                        name="RPAInteraction",
                        func=self._rpa_interaction, # Usa o wrapper
                        description="Útil para interagir com elementos em páginas web (digitar, clicar, extrair). Recebe 'session_id' (string), 'intent' (type, click, extract), 'target_description' (descrição do elemento) e opcionalmente 'value' para 'type'."
                    ),
                    Tool(
                        name="RPAAnalyzePage",
                        func=self._rpa_analyze_page, # Usa o wrapper
                        description="Analisa a estrutura da página web atual e retorna informações sobre elementos interativos. Recebe 'session_id' (string)."
                    ),
                    Tool(
                        name="RPACleanup",
                        func=self._cleanup_rpa_session, # Usa o wrapper
                        description="Fecha a sessão do navegador RPA e limpa recursos. Deve ser chamado após a conclusão das tarefas RPA. Recebe 'session_id' (string)."
                    )
                ]

                # O prompt para o agente
                prompt = ChatPromptTemplate.from_messages([
                    ("system", "Você é um assistente útil e pode usar ferramentas para interagir com a web e automatizar tarefas."),
                    ("human", "{input}"),
                    ("placeholder", "{agent_scratchpad}")
                ])

                # Criar o agente
                agent = create_react_agent(self.llm, tools, prompt)
                self._agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
            return self._agent_executor

    def process_query_with_rag(self, query: str) -> str:
        """
        Processa uma consulta usando RAG (Retrieval-Augmented Generation).
        O VectorStore e o LLM serão carregados sob demanda.
        """
        logger.info(f"Processando consulta com RAG: {query}")
        retriever = self.vectorstore.as_retriever()
        qa_chain = RetrievalQA.from_chain_type(self.llm, chain_type="stuff", retriever=retriever)
        response = qa_chain.run(query)
        return response

    async def run_agent_task(self, task: str) -> str:
        """
        Executa uma tarefa usando o agente do LangChain.
        O AgentExecutor e o LLM serão carregados sob demanda.
        """
        logger.info(f"Executando tarefa do agente: {task}")
        # Exemplo:
        # response = await self.agent_executor.ainvoke({"input": task})
        # return response["output"]
        response = await self.agent_executor.ainvoke({"input": task})
        return response["output"]

    def _get_rpa_agent(self, session_id: str) -> EnhancedAtenaRPAAgent:
        """Retorna a instância do RPA Agent para o session_id fornecido."""
        agent = self._rpa_agents.get(session_id)
        if not agent:
            raise ValueError(f"Nenhuma sessão RPA ativa encontrada para o ID: {session_id}")
        return agent

    def _initialize_rpa_session(self, session_id: str, user_id: Optional[str] = None, ai_type: str = "langchain_rpa_agent") -> str:
        """Inicializa uma nova sessão RPA e a armazena."""
        with self._lock:
            if session_id in self._rpa_agents:
                logger.warning(f"Sessão RPA com ID {session_id} já existe. Reutilizando.")
                return session_id

            rpa_config_manager_instance = self._config.get("rpa_config_manager_instance")
            if not rpa_config_manager_instance:
                logger.warning("RPAConfigManager instance not found. Creating a default one.")
                rpa_config_manager_instance = RPAConfigManager()

            rpa_agent = EnhancedAtenaRPAAgent(rpa_config_manager_instance)
            context = ExecutionContext(session_id=session_id, user_id=user_id, ai_type=ai_type)
            rpa_agent.initialize_session(context)
            self._rpa_agents[session_id] = rpa_agent
            logger.info(f"Nova sessão RPA inicializada com ID: {session_id}")
            return session_id

    def _cleanup_rpa_session(self, session_id: str) -> str:
        """Limpa e remove uma sessão RPA."""
        with self._lock:
            agent = self._rpa_agents.pop(session_id, None)
            if agent:
                agent.cleanup()
                logger.info(f"Sessão RPA com ID {session_id} finalizada e removida.")
                return f"Sessão RPA {session_id} finalizada."
            else:
                logger.warning(f"Tentativa de limpar sessão RPA inexistente: {session_id}")
                return f"Sessão RPA {session_id} não encontrada."

    def _rpa_interaction(self, session_id: str, intent: str, target_description: str, value: Optional[str] = None) -> Dict[str, Any]:
        """Wrapper para smart_interaction do RPA Agent."""
        agent = self._get_rpa_agent(session_id)
        return agent.smart_interaction(intent, target_description, value)

    def _rpa_analyze_page(self, session_id: str) -> Dict[str, Any]:
        """Wrapper para analyze_current_page do RPA Agent."""
        agent = self._get_rpa_agent(session_id)
        return agent.analyze_current_page()

    async def _search_memory_tool(self, query: str) -> str:
        """
        Ferramenta para o LangChain buscar na memória interna da Atena.
        """
        if not self._cognitive_architecture:
            return "Erro: Arquitetura Cognitiva não disponível para busca na memória."
        
        logger.info(f"Agente LangChain solicitou busca na memória para: {query}")
        try:
            memory_results = await self._cognitive_architecture.search_memory(query)
            if memory_results:
                # Formatar os resultados para o agente
                formatted_results = []
                for chunk in memory_results:
                    formatted_results.append(f"Conteúdo: {chunk.text[:200]}... (Score: {chunk.relevance_score:.2f})")
                return "Resultados da memória:\n" + "\n".join(formatted_results)
            else:
                return "Nenhum resultado encontrado na memória interna."
        except Exception as e:
            logger.error(f"Erro ao buscar na memória via ferramenta LangChain: {e}", exc_info=True)
            return f"Erro ao buscar na memória: {str(e)}"

    # Adicione outros métodos conforme necessário para expor funcionalidades do LangChain
