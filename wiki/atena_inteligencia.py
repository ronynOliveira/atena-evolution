# atena_inteligencia.py
# Versão 4.3 - Integração com Servidor Central e Pydantic
# Este módulo agora é um componente, não um script autônomo.

import os
import asyncio
import logging
import time
import uuid
import hashlib
import json
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from contextlib import asynccontextmanager
from enum import Enum
from collections import deque

# --- Dependências Principais ---
import numpy as np
import torch
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline, BitsAndBytesConfig
import spacy
from textblob import TextBlob
import nltk
from sklearn.cluster import HDBSCAN
# from umap import UMAP # UMAP pode ser pesado, vamos usar PCA por padrão para CPU
from sklearn.decomposition import PCA
import asyncpg
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from atena_config import AtenaConfig
from pydantic import Field, HttpUrl, PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings

# --- Validação de Qdrant ---
try:
    from qdrant_client import QdrantClient, models
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False
    class QdrantClient: pass
    class models: pass



# O restante do arquivo (EnhancedChunk, Hypothesis, etc.) permanece o mesmo,
# mas as classes principais (EmbeddingManager, SemanticAnalyzer, AtenaCognitiveArchitecture)
# serão modificadas para aceitar o objeto `config` em seus construtores.

@dataclass
class EnhancedChunk:
    text: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    primary_embedding: Optional[np.ndarray] = field(default=None, repr=False)
    metadata: Dict[str, Any] = field(default_factory=dict)
    # ... (outros campos como na versão original) ...
    quality_score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result.pop('primary_embedding', None)
        return result

class EmbeddingManager:
    def __init__(self, config: AtenaConfig):
        self.config = config
        self.device = config.device # Usa o device da config central
        self._initialize_model()
        self.cache = {}

    def _initialize_model(self):
        try:
            # Força o uso do dispositivo definido na configuração
            self.model = SentenceTransformer(self.config.primary_embedding_model, device=self.device)
            logging.info(f"Modelo de embedding '{self.config.primary_embedding_model}' inicializado em '{self.device}'.")
        except Exception as e:
            logging.error(f"Falha ao carregar modelo de embedding: {e}")
            raise

    async def get_embedding(self, text: str) -> Optional[np.ndarray]:
        # ... (lógica de cache e embedding) ...
        # A lógica interna permanece a mesma
        pass

class SemanticAnalyzer:
    def __init__(self, config: AtenaConfig):
        self.config = config
        self._initialize_models()

    def _initialize_models(self):
        try:
            self.nlp = spacy.load(self.config.spacy_model)
        except OSError as e:
            logging.warning(f"Modelo SpaCy '{self.config.spacy_model}' não encontrado. Por favor, instale-o executando: python -m spacy download {self.config.spacy_model}")
            raise e
        # ... (resto da inicialização) ...

    async def analyze_chunk(self, chunk: EnhancedChunk) -> EnhancedChunk:
        # ... (lógica de análise permanece a mesma) ...
        pass

class LLMManager:
    """Gerencia o carregamento e a inferência do Large Language Model (LLM)."""
    def __init__(self, config: AtenaConfig):
        self.config = config
        self.tokenizer = None
        self.model = None
        self.text_generator = None
        self._initialize_llm()

    def _initialize_llm(self):
        try:
            logging.info(f"Carregando LLM: {self.config.llm_model} no dispositivo: {self.config.device}")
            if self.config.llm_provider == "ollama":
                from ollama import Client
                self.client = Client(host='http://localhost:11434')
                self.text_generator = self._ollama_text_generator
                logging.info(f"LLM Ollama '{self.config.llm_model}' inicializado com sucesso.")
            else:
                self.tokenizer = AutoTokenizer.from_pretrained(self.config.llm_model)
                
                quantization_config = None
                if self.config.use_quantization:
                    quantization_config = BitsAndBytesConfig(
                        load_in_4bit=True,
                        bnb_4bit_quant_type="nf4",
                        bnb_4bit_compute_dtype=torch.bfloat16
                    )

                self.model = AutoModelForCausalLM.from_pretrained(
                    self.config.llm_model,
                    device_map=self.config.device,
                    quantization_config=quantization_config
                )
                self.model.eval() # Coloca o modelo em modo de avaliação

                self.text_generator = pipeline(
                    "text-generation",
                    model=self.model,
                    tokenizer=self.tokenizer,
                    device=0 if self.config.device == "cuda" else -1 # 0 para GPU, -1 para CPU
                )
                logging.info(f"LLM '{self.config.llm_model}' inicializado com sucesso.")
        except Exception as e:
            logging.error(f"Falha ao carregar LLM: {e}")
            self.text_generator = None # Garante que não tentará usar um LLM falho

    async def _ollama_text_generator(self, prompt: str) -> str:
        try:
            response = await self.client.chat(
                model=self.config.llm_model,
                messages=[{"role": "user", "content": prompt}]
            )
            return response['message']['content']
        except Exception as e:
            logging.error(f"Erro ao gerar texto com Ollama: {e}")
            return "Desculpe, ocorreu um erro ao processar sua solicitação com o modelo de linguagem Ollama."

    async def generate_text(self, prompt: str, max_new_tokens: Optional[int] = None) -> str:
        if not self.text_generator:
            logging.warning("LLM não inicializado. Retornando resposta padrão.")
            return "Desculpe, não consigo gerar uma resposta no momento. O modelo de linguagem não está disponível."

        try:
            if self.config.llm_provider == "ollama":
                return await self.text_generator(prompt)
            else:
                # Usar max_new_tokens da configuração se não for especificado
                tokens_to_generate = max_new_tokens if max_new_tokens is not None else self.config.max_tokens_llm

                # A pipeline de text-generation já lida com a maioria dos parâmetros
                # Para modelos de chat, pode ser necessário formatar o prompt como uma conversa
                # Exemplo simplificado para modelos de texto genéricos
                outputs = self.text_generator(
                    prompt,
                    max_new_tokens=tokens_to_generate,
                    num_return_sequences=1,
                    temperature=self.config.temperature_llm,
                    do_sample=True, # Habilita amostragem para temperatura
                    pad_token_id=self.tokenizer.eos_token_id # Evita warnings para modelos sem pad_token
                )
                return outputs[0]['generated_text']
        except Exception as e:
            logging.error(f"Erro ao gerar texto com LLM: {e}")
            return "Desculpe, ocorreu um erro ao processar sua solicitação com o modelo de linguagem."


class AtenaCognitiveArchitecture:
    """O cérebro da Atena, gerenciando memória e cognição."""
    def __init__(self, config: AtenaConfig):
        self.config = config
        self.embedding_manager = EmbeddingManager(config)
        self.semantic_analyzer = SemanticAnalyzer(config)
        self.llm_manager = LLMManager(config) # Novo: Gerenciador de LLM
        # ... (outros componentes como VectorMemory, RelationalMemory) ...
        self.is_initialized = False
        logging.info("Arquitetura Cognitiva da Atena instanciada.")

    @property
    def sentence_transformer_model(self):
        """Retorna a instância do SentenceTransformer."""
        return self.embedding_manager.model

    async def initialize(self):
        """Inicializa conexões com bancos de dados e outros serviços."""
        if self.is_initialized:
            return
        # ... (lógica para conectar ao PostgreSQL, Qdrant/FAISS, etc.) ...
        logging.info("Arquitetura Cognitiva inicializada e conectada aos bancos de dados.")
        self.is_initialized = True

    async def start(self):
        """Inicia a arquitetura cognitiva e seus componentes."""
        await self.initialize()
        logging.info("Arquitetura Cognitiva iniciada.")

    async def process_text(self, text: str) -> str:
        """Processa um texto, busca na memória e gera uma resposta."""
        logging.info(f"Processando texto com LLM: '{text[:50]}...'")
        
        # Exemplo simplificado: usar o LLM para gerar uma resposta
        # Em um cenário real, você integraria busca na memória, análise, etc.
        response = await self.llm_manager.generate_text(prompt=text)
        
        return response

    async def shutdown(self):
        """Fecha conexões de forma graciosa."""
        # ... (lógica para fechar pools de conexão) ...
        logging.info("Arquitetura Cognitiva finalizada.")

    async def stop(self):
        """Para a arquitetura cognitiva e seus componentes."""
        await self.shutdown()
        logging.info("Arquitetura Cognitiva parada.")