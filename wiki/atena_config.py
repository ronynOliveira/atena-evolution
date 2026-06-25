# src/atena_config.py
# Configuração centralizada para o Ecossistema Atena

from typing import Optional, List, Dict, Any
from pydantic import Field, HttpUrl, PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict

class AtenaConfig(BaseSettings):
    """
    Configurações unificadas e validadas para o Ecossistema Atena.
    As configurações podem ser carregadas de variáveis de ambiente (prefixo ATENA_)
    ou de um arquivo .env.
    """
    model_config = SettingsConfigDict(env_prefix='ATENA_', env_file='.env', extra='ignore')

    # Chave de segurança principal
    secret_key: str = Field("uma_chave_secreta_muito_segura_para_atena_exemplo_32_chars", min_length=32)

    # Configurações de Modelos e IA
    primary_embedding_model: str = "intfloat/multilingual-e5-large"
    multilingual_model: str = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
    domain_specific_model: str = "neuralmind/bert-base-portuguese-cased"
    llm_model: str = "gemini-pro"
    spacy_model: str = "pt_core_news_sm"
    device: str = "cpu"
    use_quantization: bool = True
    max_tokens_llm: int = 512
    temperature_llm: float = 0.7
    use_gpu: bool = False # Será sobrescrito se torch.cuda.is_available()

    # Configurações de Memória e Consolidação
    min_text_quality_score: float = 0.4
    consolidation_threshold: float = 0.85
    consolidation_interval_seconds: int = 3600
    clustering_algorithms: List[str] = ["kmeans", "dbscan", "hierarchical", "spectral"]
    similarity_thresholds: Dict[str, float] = {"high": 0.95, "medium": 0.85, "low": 0.75}
    use_llm_consolidation: bool = False
    llm_provider: str = "google" # openai, anthropic, groq, cohere

    # Configurações de Serviços Externos e Banco de Dados
    postgres_url: PostgresDsn = "postgresql+asyncpg://user:pass@localhost:5432/atena_memory"
    vector_db_url: HttpUrl = "http://localhost:6333"
    redis_url: Optional[RedisDsn] = None
    use_redis_cache: bool = False
    use_elasticsearch: bool = False
    use_chromadb: bool = False
    use_qdrant: bool = False

    # Chaves de API
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None
    cohere_api_key: Optional[str] = None
    huggingface_api_key: Optional[str] = None
    bing_api_key: Optional[str] = None # Adicionado para atena_web.py

    # Configurações de RPA
    rpa_browser_timeout: int = 30000
    rpa_stealth_mode: bool = True

    # Configurações de Monitoramento
    enable_metrics: bool = True
    prometheus_port: int = 8000

    # Configurações de Busca Web (de atena_web.py)
    cache_ttl_hours: int = 24
    max_results_per_source: int = 10
    timeout_seconds: int = 30
    retry_attempts: int = 3
    search_engines: Dict[str, Any] = Field(default_factory=lambda: {
        "duckduckgo": {"enabled": True, "priority": 1},
        "bing_api": {"enabled": False, "priority": 2, "api_key": ""},
        "google_scrape": {"enabled": True, "priority": 3},
        "startpage": {"enabled": True, "priority": 4}
    })
    local_search_enabled: bool = True
    local_search_index_path: str = "data/search_index.db"

    # Outras configurações gerais
    max_workers: int = 4 # Exemplo, pode ser ajustado
    batch_size: int = 1000
    enable_deduplication: bool = True
    enable_semantic_analysis: bool = True

    # Validação e ajustes pós-carregamento
    def __post_init__(self):
        import torch
        if torch.cuda.is_available():
            self.device = "cuda"
            self.use_gpu = True
        else:
            self.device = "cpu"
            self.use_gpu = False

        # Ajustar chaves de API para o provedor LLM selecionado
        if self.llm_provider == "openai" and self.openai_api_key:
            import os
            os.environ["OPENAI_API_KEY"] = self.openai_api_key
        elif self.llm_provider == "anthropic" and self.anthropic_api_key:
            import os
            os.environ["ANTHROPIC_API_KEY"] = self.anthropic_api_key
        elif self.llm_provider == "groq" and self.groq_api_key:
            import os
            os.environ["GROQ_API_KEY"] = self.groq_api_key
        elif self.llm_provider == "cohere" and self.cohere_api_key:
            import os
            os.environ["COHERE_API_KEY"] = self.cohere_api_key
        elif self.llm_provider == "google" and self.google_api_key:
            import google.generativeai as genai
            genai.configure(api_key=self.google_api_key)
        elif self.llm_provider == "local":
            if not self.llm_local_model_path:
                # Opcional: Adicionar um aviso ou um erro se o caminho não estiver definido
                print("AVISO: Provedor de LLM 'local' selecionado, mas 'llm_local_model_path' não está definido.")

        # Atualizar a chave da API do Bing no dicionário search_engines
        if self.bing_api_key:
            if "bing_api" in self.search_engines:
                self.search_engines["bing_api"]["api_key"] = self.bing_api_key
            else:
                self.search_engines["bing_api"] = {"enabled": True, "priority": 2, "api_key": self.bing_api_key}

# Instância global da configuração para fácil acesso
settings = AtenaConfig()
