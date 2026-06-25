# config_atena.py
# Configuração centralizada para o ambiente de desenvolvimento da Atena

# Este dicionário contém todas as configurações e chaves necessárias
# para os diferentes módulos da Atena.
DEVELOPMENT_CONFIG = {
    # Chave de segurança principal (ex: para JWT ou validação interna)
    "secret_key": "uma_chave_secreta_muito_segura_para_atena_exemplo_32_chars",

    # Configurações de Modelos e IA
    "primary_embedding_model": "intfloat/multilingual-e5-large",
    "llm_model": "microsoft/DialoGPT-medium",
    "spacy_model": "pt_core_news_sm", # Usar 'sm' para ser mais leve
    "device": "cpu", # Força o uso de CPU para todos os modelos
    "use_quantization": True, # Otimização para CPU
    "max_tokens_llm": 512,
    "temperature_llm": 0.7,

    # Configurações de Memória
    "min_text_quality_score": 0.4,
    "consolidation_threshold": 0.85,
    "consolidation_interval_seconds": 3600,  # 1 hora

    # Configurações de Serviços Externos e Banco de Dados
    "postgres_url": "postgresql+asyncpg://user:pass@localhost:5432/atena_memory",
    "vector_db_url": "http://localhost:6333",
    
    # Adicionamos placeholders para outras chaves que podem ser necessárias
    "redis_url": "redis://localhost:6379",
    "openai_api_key": "sk-SEU_OPENAI_KEY_AQUI",
    "huggingface_api_key": "hf_SEU_HF_KEY_AQUI",

    # Configurações de RPA
    "rpa_browser_timeout": 30000,
    "rpa_stealth_mode": True
}
