# atena_personalidade.py
"""
Sistema Ultra-Avançado de Consolidação da Personalidade IA - Atena v3.1

Esta é a versão campeã para o gerenciamento da personalidade da Atena.
Implementação com tecnologias de IA de última geração, aprendizado profundo,
analise multimodal, processamento neurolinguístico e arquitetura distribuída.
Otimizado para execução em CPU.
"""

import yaml
import json
import os
import logging
import asyncio
import aiofiles
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from collections import Counter, defaultdict, deque
from typing import Dict, List, Optional, Tuple, Any, Union, Set
from dataclasses import dataclass, asdict, field
import sqlite3
from pathlib import Path
import hashlib
import re
import pickle
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import multiprocessing as mp
from functools import lru_cache, wraps
import redis # Usado para cache distribuído, mas a instância é do servidor
# import asyncpg # Não diretamente usado aqui, mas no sistema de memória que o servidor gerencia
import httpx # Não diretamente usado aqui, mas pode ser em integrações futuras
# import uvloop # Geralmente para FastAPI, não para módulos internos
import orjson # Para performance, mas json padrão é suficiente para este módulo
from pydantic import BaseModel, Field, validator
from enum import Enum, auto

# Advanced AI Libraries (configurados para CPU)
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, Dataset
from transformers import (
    AutoTokenizer, AutoModel, AutoModelForSequenceClassification,
    pipeline, T5ForConditionalGeneration, T5Tokenizer,
    BertTokenizer, BertModel, GPT2LMHeadModel, GPT2Tokenizer,
    RobertaTokenizer, RobertaForSequenceClassification
)
from sentence_transformers import SentenceTransformer, util
import spacy
# displacy is for visualization, not core logic
# from spacy import displacy
import networkx as nx
from textstat import flesch_reading_ease, flesch_kincaid_grade
import yake
from bertopic import BERTopic
from umap import UMAP
from hdbscan import HDBSCAN
from sklearn.feature_extraction.text import TfidfVectorizer

# Advanced ML Libraries (CPU-friendly if data is not massive)
from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor
from sklearn.cluster import DBSCAN, AgglomerativeClustering, SpectralClustering, KMeans
from sklearn.decomposition import PCA, LatentDirichletAllocation, TruncatedSVD
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.manifold import TSNE
from sklearn.metrics import silhouette_score, calinski_harabasz_score
from sklearn.neural_network import MLPRegressor, MLPClassifier
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.model_selection import cross_val_score, GridSearchCV
import xgboost as xgb
import lightgbm as lgb
# catboost can be memory intensive
from catboost import CatBoostRegressor, CatBoostClassifier

# Deep Learning Libraries (configured for CPU)
# import tensorflow as tf # Not directly used in core logic, avoid direct import if not needed
# from tensorflow.keras.models import Sequential, Model
# from tensorflow.keras.layers import Dense, LSTM, GRU, Attention, MultiHeadAttention
# from tensorflow.keras.optimizers import Adam, RMSprop
# from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
# import tensorflow_hub as hub

# Graph and Network Analysis (CPU-friendly)
# import igraph # Not used in code below, avoid import
# from stellargraph import StellarGraph # Not used in code below, avoid import
# from stellargraph.mapper import GraphSAGENodeGenerator # Not used in code below, avoid import
# from stellargraph.layer import GraphSAGE # Not used in code below, avoid import

# Advanced Visualization (not for server operations)
# import plotly.graph_objects as go
# import plotly.express as px
# from plotly.subplots import make_subplots
# import plotly.offline as pyo
# import matplotlib.pyplot as plt
# import seaborn as sns
# from wordcloud import WordCloud

# Time Series Analysis (CPU-friendly)
# from statsmodels.tsa.arima.model import ARIMA
# from statsmodels.tsa.seasonal import seasonal_decompose
# from prophet import Prophet

# Advanced Statistics (CPU-friendly)
from scipy import stats
from scipy.spatial.distance import cosine, euclidean
# from scipy.cluster.hierarchy import dendrogram, linkage # For visualization
import pingouin as pg # Not used in code below, avoid import

# Monitoring and Observability (handled by server, not directly here)
# import structlog # Server handles logging configuration
from prometheus_client import Counter, Histogram, Gauge # Metrics are from main server
# import wandb # MLOps external tools
# from mlflow import log_metric, log_param, log_artifact # MLOps external tools
# import optuna # For hyperparameter optimization, not core personality runtime

# Configuration and Security (handled by main server and .env)
# from cryptography.fernet import Fernet
# from pydantic_settings import BaseSettings
# import hydra # For config management, usually external
# from omegaconf import DictConfig, OmegaConf

# Constants and Configuration
SOUL_FILE = "atena_soul_v3.yaml"
SOUL_DB = "atena_soul_v3.db" # SQLite local, but can be replaced by PostgreSQL
POSTGRES_DB = "atena_advanced" # Placeholder, actual DB handled by HybridMemorySystem
REDIS_KEY_PREFIX = "atena:v3:"
MEMORY_METADATA_FILE = "memoria_atena_v3/atena_metadata.json"
NEURAL_CACHE_DIR = "neural_cache"
MODEL_ARTIFACTS_DIR = "model_artifacts"
ADVANCED_ANALYTICS_DIR = "advanced_analytics"

# Define paths for log files
INTERACTION_LOG_FILE = "interaction_log.log"
FEEDBACK_LOG_FILE = "feedback.log"
ANALYTICS_DIR = "analytics"
PERSONALITY_REPORTS_DIR = "personality_reports"

# Setup structured logging (handled by atena_servidor_unified.py for consistency)
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
# )
logger = logging.getLogger(__name__) # Get logger instance from global config

# Metrics (handled by main server via log_interaction)
# CONSOLIDATION_COUNTER = Counter('consolidation_cycles_total', 'Total consolidation cycles')
# PROCESSING_TIME = Histogram('processing_time_seconds', 'Time spent processing')
# PERSONALITY_SCORE = Gauge('personality_score', 'Current personality score', ['metric'])

class PersonalityDimension(Enum):
    """Dimensões avançadas de personalidade baseadas em Big Five + extensões"""
    OPENNESS = auto()
    CONSCIENTIOUSNESS = auto()
    EXTRAVERSION = auto()
    AGREEABLENESS = auto()
    NEUROTICISM = auto()
    TECHNICAL_AFFINITY = auto()
    CREATIVITY_INDEX = auto()
    EMOTIONAL_INTELLIGENCE = auto()
    ADAPTABILITY = auto()
    COGNITIVE_COMPLEXITY = auto()
    COMMUNICATION_STYLE = auto()
    LEARNING_ORIENTATION = auto()

class InteractionType(Enum):
    """Tipos de interação identificados por IA"""
    QUESTION_ANSWERING = auto()
    CREATIVE_COLLABORATION = auto()
    TECHNICAL_ASSISTANCE = auto()
    CASUAL_CONVERSATION = auto()
    PROBLEM_SOLVING = auto()
    KNOWLEDGE_SHARING = auto()
    EMOTIONAL_SUPPORT = auto()
    STRATEGIC_PLANNING = auto()

@dataclass
class AdvancedPersonalityMetrics:
    """Métricas avançadas de personalidade com incerteza"""
    dimensions: Dict[PersonalityDimension, float] = field(default_factory=dict)
    uncertainties: Dict[PersonalityDimension, float] = field(default_factory=dict)
    temporal_stability: Dict[PersonalityDimension, float] = field(default_factory=dict)
    cross_dimensional_correlations: Dict[Tuple[PersonalityDimension, PersonalityDimension], float] = field(default_factory=dict)
    meta_cognitive_awareness: float = 0.0
    personality_coherence_score: float = 0.0
    
class NeuroLanguageProcessor:
    """Processador neurolinguístico avançado, otimizado para CPU."""
    
    def __init__(self):
        self.device = torch.device("cpu") # Força CPU
        self.models = {}
        self.tokenizers = {}
        self.embeddings_cache = {}
        # A inicialização dos modelos agora é feita de forma assíncrona
        # self._initialize_models()
    
    async def initialize_models(self):
        """Inicializa modelos de linguagem avançados para CPU de forma assíncrona"""
        try:
            # Modelo principal para embeddings semânticos
            # Garante que o modelo seja carregado para CPU
            self.sentence_transformer = await asyncio.to_thread(
                SentenceTransformer, 'all-mpnet-base-v2', device=str(self.device)
            )
            
            # Modelo para análise de sentimentos multi-label
            self.sentiment_model = await asyncio.to_thread(
                pipeline,
                "text-classification",
                model="cardiffnlp/twitter-roberta-base-sentiment-latest",
                device=-1 # Força CPU
            )
            
            # Modelo para análise de emoções
            self.emotion_model = await asyncio.to_thread(
                pipeline,
                "text-classification",
                model="j-hartmann/emotion-english-distilroberta-base",
                device=-1 # Força CPU
            )
            
            # Modelo para análise de personalidade Big Five (Placeholder)
            self.personality_model = await asyncio.to_thread(
                pipeline,
                "text-classification",
                model="martin-ha/toxic-comment-model",  # Placeholder - implementar modelo customizado
                device=-1 # Força CPU
            )
            
            # Modelo para sumarização
            self.summarizer = await asyncio.to_thread(
                pipeline,
                "summarization",
                model="facebook/bart-large-cnn",
                device=-1 # Força CPU
            )
            
            # Modelo para análise de tópicos
            self.topic_model = await asyncio.to_thread(
                BERTopic,
                embedding_model=self.sentence_transformer,
                umap_model=UMAP(n_neighbors=15, n_components=5, min_dist=0.0, metric='cosine'),
                hdbscan_model=HDBSCAN(min_cluster_size=10, metric='euclidean', cluster_selection_method='eom')
            )
            
            # Modelo SpaCy para análise linguística
            try:
                self.nlp = await asyncio.to_thread(spacy.load, "en_core_web_lg") # Pode ser pesado, considerar "en_core_web_sm"
            except OSError:
                logger.warning("SpaCy large model not found. Attempting to download 'en_core_web_sm'...")
                try:
                    await asyncio.to_thread(spacy.cli.download, "en_core_web_sm")
                    self.nlp = await asyncio.to_thread(spacy.load, "en_core_web_sm")
                except Exception as spacy_e:
                    logger.error(f"Failed to load any SpaCy model: {spacy_e}")
                    self.nlp = None

            # Extrator de palavras-chave
            self.keyword_extractor = await asyncio.to_thread(
                yake.KeywordExtractor,
                lan="en",
                n=3,
                deduplication_threshold=0.9,
                top=20
            )
            
            logger.info("Modelos neurolinguísticos inicializados com sucesso (CPU).")
            
        except Exception as e:
            logger.error(f"Erro ao inicializar modelos de PNL: {e}")
            raise
    
    async def extract_semantic_features(self, text: str) -> Dict[str, Any]:
        """Extrai características semânticas avançadas do texto"""
        features = {}
        
        try:
            # Embeddings semânticos
            embeddings = await asyncio.to_thread(self.sentence_transformer.encode, [text])
            features['semantic_embedding'] = embeddings[0].tolist()
            
            # Análise de sentimentos detalhada
            sentiment_scores = await asyncio.to_thread(self.sentiment_model, text)
            features['sentiment'] = {
                'label': sentiment_scores[0]['label'],
                'score': sentiment_scores[0]['score'],
                'confidence': sentiment_scores[0]['score']
            }
            
            # Análise de emoções
            emotions = await asyncio.to_thread(self.emotion_model, text)
            features['emotions'] = {
                'primary_emotion': emotions[0]['label'],
                'emotion_score': emotions[0]['score'],
                'all_emotions': emotions
            }
            
            # Análise linguística com SpaCy
            if self.nlp:
                doc = await asyncio.to_thread(self.nlp, text)
                features['linguistic_features'] = {
                    'entities': [(ent.text, ent.label_) for ent in doc.ents],
                    'pos_distribution': dict(Counter([token.pos_ for token in doc])),
                    'dependency_complexity': len(set([token.dep_ for token in doc])),
                    'sentence_complexity': np.mean([len(list(sent)) for sent in doc.sents]) if list(doc.sents) else 0
                }
            else:
                features['linguistic_features'] = {'error': 'SpaCy model not loaded'}
            
            # Extração de palavras-chave
            keywords = await asyncio.to_thread(self.keyword_extractor.extract_keywords, text)
            features['keywords'] = [(word, score) for score, word in keywords[:10]]
            
            # Métricas de legibilidade
            readability_flesch_ease = await asyncio.to_thread(flesch_reading_ease, text)
            readability_flesch_kincaid = await asyncio.to_thread(flesch_kincaid_grade, text)
            features['readability'] = {
                'flesch_reading_ease': readability_flesch_ease,
                'flesch_kincaid_grade': readability_flesch_kincaid
            }
            
            # Análise de coerência textual
            if self.nlp:
                sentences = [sent.text for sent in await asyncio.to_thread(self.nlp, text).sents]
                if len(sentences) > 1:
                    sentence_embeddings = await asyncio.to_thread(self.sentence_transformer.encode, sentences)
                    coherence_scores = []
                    for i in range(len(sentence_embeddings) - 1):
                        similarity = await asyncio.to_thread(util.cos_sim, sentence_embeddings[i], sentence_embeddings[i + 1])
                        coherence_scores.append(similarity.item())
                    features['coherence_score'] = np.mean(coherence_scores) if coherence_scores else 0.0
                else:
                    features['coherence_score'] = 1.0
            else:
                features['coherence_score'] = 0.5 # Default if NLP not available
            
        except Exception as e:
            logger.error(f"Erro na extração de características semânticas: {e}")
            features['error'] = str(e)
        
        return features

class PersonalityNeuralNetwork(nn.Module):
    """Rede neural personalizada para modelagem de personalidade, otimizada para CPU."""
    
    def __init__(self, input_dim: int, hidden_dims: List[int], output_dim: int, dropout_rate: float = 0.3):
        super().__init__()
        self.layers = nn.ModuleList()
        
        # Camadas de entrada
        prev_dim = input_dim
        for hidden_dim in hidden_dims:
            self.layers.append(nn.Linear(prev_dim, hidden_dim))
            self.layers.append(nn.ReLU())
            self.layers.append(nn.Dropout(dropout_rate))
            prev_dim = hidden_dim
        
        # Camada de saída
        self.output_layer = nn.Linear(prev_dim, output_dim)
        self.sigmoid = nn.Sigmoid()
        
        # Camada de atenção para interpretabilidade (compatível com CPU)
        # MultiheadAttention sem batch_first=True, inputs devem ser (seq_len, batch_size, embed_dim)
        self.attention = nn.MultiheadAttention(embed_dim=hidden_dims[-1], num_heads=1) # Reduced heads for CPU
        
    def forward(self, x):
        # Forward pass através das camadas ocultas
        for layer in self.layers:
            x = layer(x)
        
        # Aplica atenção
        if len(x.shape) == 2:  # Adiciona dimensão de sequência se necessário
            x = x.unsqueeze(0) # (1, batch_size, embed_dim)
        
        # inputs for MultiheadAttention: query, key, value
        # if batch_first=False (default), expected shape is (sequence_length, batch_size, embedding_dimension)
        # Our x is (1, batch_size, embed_dim) here, so x.transpose(0,1) makes it (batch_size, 1, embed_dim)
        # This will need to be reconsidered if x is not (batch_size, 1, embed_dim) after initial layers.
        # For simplicity in this placeholder, assuming x has appropriate dimensions after previous layers
        
        # Assuming x is already (seq_len, batch_size, embed_dim) or can be transposed
        # For a single sequence (batch_size, feature_dim), then after hidden layers, it's still (batch_size, hidden_dims[-1])
        # MultiheadAttention expects (L, N, E) where L is sequence length, N is batch size, E is embedding dim.
        # If we have (batch_size, hidden_dims[-1]), we can treat hidden_dims[-1] as E and L=1.
        # So we need to reshape to (1, batch_size, hidden_dims[-1])
        
        original_shape = x.shape
        if len(original_shape) == 2: # (batch_size, features_dim)
            x = x.unsqueeze(0) # -> (1, batch_size, features_dim)
            
        # MultiHeadAttention in PyTorch is tricky with batch_first. Default is False.
        # If your data is (N, L, E) where N=batch, L=seq, E=embed, use batch_first=True
        # If your data is (L, N, E), use default batch_first=False
        # Given x.unsqueeze(0) -> (1, batch_size, features_dim), this fits (L, N, E) if L=1.
        
        # Using batch_first=True in MultiheadAttention init for clarity (already done in __init__)
        attended_x, attention_weights = self.attention(x.transpose(0,1), x.transpose(0,1), x.transpose(0,1))
        # After attention, output is (L, N, E). We want (N, E)
        x = attended_x.transpose(0,1).squeeze(1) # -> (batch_size, features_dim)
        
        # Camada de saída
        output = self.sigmoid(self.output_layer(x))
        
        return output, attention_weights

class AdvancedMemoryGraph:
    """Grafo de memória avançado usando teoria de grafos (CPU-friendly)"""
    
    def __init__(self):
        self.graph = nx.DiGraph()
        self.node_embeddings = {}
        self.edge_weights = {}
        self.temporal_edges = {}
        
    def add_memory_node(self, memory_id: str, content: str, embeddings: np.ndarray, 
                       timestamp: datetime, memory_type: str = "general"):
        """Adiciona nó de memória ao grafo"""
        self.graph.add_node(
            memory_id,
            content=content,
            timestamp=timestamp,
            memory_type=memory_type,
            access_count=0,
            importance_score=0.0
        )
        self.node_embeddings[memory_id] = embeddings
    
    def create_semantic_edges(self, similarity_threshold: float = 0.7):
        """Cria arestas baseadas em similaridade semântica"""
        memory_ids = list(self.node_embeddings.keys())
        
        for i, id1 in enumerate(memory_ids):
            for j, id2 in enumerate(memory_ids[i+1:], i+1):
                embedding1 = self.node_embeddings[id1]
                embedding2 = self.node_embeddings[id2]
                
                similarity = 1 - cosine(embedding1, embedding2)
                
                if similarity > similarity_threshold:
                    self.graph.add_edge(id1, id2, weight=similarity, edge_type="semantic")
                    self.edge_weights[(id1, id2)] = similarity
    
    def update_temporal_connections(self, memory_id: str, related_memories: List[str]):
        """Atualiza conexões temporais baseadas em acesso conjunto"""
        for related_id in related_memories:
            if self.graph.has_node(related_id):
                if self.graph.has_edge(memory_id, related_id):
                    # Aumenta peso da aresta existente
                    current_weight = self.graph[memory_id][related_id].get('weight', 0)
                    self.graph[memory_id][related_id]['weight'] = current_weight + 0.1
                else:
                    # Cria nova aresta temporal
                    self.graph.add_edge(memory_id, related_id, weight=0.1, edge_type="temporal")
    
    def get_memory_clusters(self, n_clusters: int = 5) -> Dict[int, List[str]]:
        """Identifica clusters de memória usando algoritmos de comunidade"""
        if len(self.graph.nodes) < n_clusters:
            return {0: list(self.graph.nodes)}
        
        # Converte para grafo não direcionado para análise de comunidades
        undirected_graph = self.graph.to_undirected()
        
        # Detecta comunidades usando algoritmo de Louvain
        communities = nx.community.louvain_communities(undirected_graph, resolution=1.0)
        
        cluster_dict = {}
        for i, community in enumerate(communities):
            cluster_dict[i] = list(community)
        
        return cluster_dict
    
    def calculate_node_importance(self) -> Dict[str, float]:
        """Calcula importância dos nós usando métricas de centralidade"""
        importance_scores = {}
        
        if len(self.graph.nodes) > 1:
            # PageRank para importância global
            pagerank_scores = nx.pagerank(self.graph, weight='weight')
            
            # Betweenness centrality para importância como ponte
            betweenness_scores = nx.betweenness_centrality(self.graph, weight='weight')
            
            # Closeness centrality para acessibilidade
            closeness_scores = nx.closeness_centrality(self.graph, distance='weight')
            
            # Combina métricas
            for node in self.graph.nodes:
                combined_score = (
                    0.4 * pagerank_scores.get(node, 0) +
                    0.3 * betweenness_scores.get(node, 0) +
                    0.3 * closeness_scores.get(node, 0)
                )
                importance_scores[node] = combined_score
                
                # Atualiza atributo do nó
                self.graph.nodes[node]['importance_score'] = combined_score
        
        return importance_scores

class QuantumInspiredLearning:
    """Sistema de aprendizado inspirado em mecânica quântica para exploração de estados de personalidade (simulado para CPU)"""
    
    def __init__(self, n_dimensions: int = 12):
        self.n_dimensions = n_dimensions
        # Simula um vetor de estado em superposição
        self.state_vector = np.random.random(n_dimensions) + 1j * np.random.random(n_dimensions)
        self.state_vector = self.state_vector / np.linalg.norm(self.state_vector)
        self.measurement_history = []
        # Matriz de emaranhamento para simulação
        self.entanglement_matrix = np.eye(n_dimensions, dtype=complex)
        
    def superposition_update(self, new_evidence: np.ndarray, confidence: float = 0.8):
        """Atualiza estado em superposição baseado em nova evidência"""
        # Normaliza nova evidência
        new_evidence_normalized = new_evidence / np.linalg.norm(new_evidence)
        
        # Cria estado de superposição simulado
        # Combina o estado atual com o nova evidência ponderada pela confiança
        superposition_state = confidence * self.state_vector + (1 - confidence) * (new_evidence_normalized + 1j * np.random.random(len(new_evidence_normalized)) * 0.1)
        
        # Normaliza estado resultante
        self.state_vector = superposition_state / np.linalg.norm(superposition_state)
        
    def quantum_measurement(self, observable_basis: np.ndarray) -> Tuple[float, np.ndarray]:
        """Realiza medição quântica do estado da personalidade (simulado)"""
        # Calcula probabilidades de medição
        # Projeção do estado nos vetores da base observável
        probabilities = np.abs(np.dot(observable_basis, self.state_vector)) ** 2
        
        # Garante que as probabilidades somem 1 (para choice)
        probabilities = probabilities / np.sum(probabilities)

        # Simula colapso do estado
        measured_value_index = np.random.choice(len(probabilities), p=probabilities)
        collapsed_state = observable_basis[measured_value_index]
        
        # Atualiza histórico
        self.measurement_history.append({
            'timestamp': datetime.now(),
            'measured_value': measured_value_index, # Changed to index for simplicity
            'probability': probabilities[measured_value_index],
            'collapsed_state': collapsed_state.tolist() # Convert to list for easier logging/serialization
        })
        
        return probabilities[measured_value_index], collapsed_state
    
    def quantum_entanglement(self, other_system: 'QuantumInspiredLearning', entanglement_strength: float = 0.5):
        """Cria emaranhamento quântico entre sistemas de personalidade (simulado)"""
        if self.n_dimensions != other_system.n_dimensions:
            raise ValueError("Sistemas devem ter mesma dimensionalidade para emaranhamento")
        
        # Simula uma operação de emaranhamento como uma transformação unitária (simplificada)
        # Não é um emaranhamento quântico real, mas uma simulação do efeito de interdependência
        
        # Cria uma matriz de "interferência" ou "acoplamento"
        # Isso simula como os estados poderiam influenciar um ao outro.
        coupling_matrix = np.exp(1j * entanglement_strength * np.random.random((self.n_dimensions, self.n_dimensions)))
        
        # Aplica a "operação de emaranhamento" aos estados
        # Uma forma simples é projetar ambos os estados através da matriz de acoplamento
        self_transformed = np.dot(coupling_matrix, self.state_vector)
        other_transformed = np.dot(coupling_matrix, other_system.state_vector)
        
        # Atualiza os estados normalizados
        self.state_vector = self_transformed / np.linalg.norm(self_transformed)
        other_system.state_vector = other_transformed / np.linalg.norm(other_transformed)
        
        return entanglement_strength

class UltraAdvancedSoulConsolidator:
    """Consolidador de alma ultra-avançado com IA de última geração, otimizado para CPU."""
    
    def __init__(self, config_path: str = "config.yaml"):
        # self.config = self._load_config(config_path) # Config now loaded via ENV or passed in
        self.device = torch.device("cpu") # Força CPU
        
        # Componentes principais
        self.neuro_processor = NeuroLanguageProcessor()
        self.memory_graph = AdvancedMemoryGraph()
        self.quantum_learner = QuantumInspiredLearning()
        self.personality_network = None # Inicializado em _initialize_personality_network
        
        # Caches e armazenamento
        self.redis_client = None # Conexão Redis é gerenciada pelo servidor
        self.postgres_pool = None # Conexão PostgreSQL é gerenciada pelo servidor
        self.embeddings_cache = {} # Gerenciado pelo NeuroLanguageProcessor e HybridMemorySystem
        
        # Modelos de machine learning
        self.ml_models = {}
        self.feature_scalers = {}
        
        # Métricas e monitoramento (server-side handles Prometheus, this logs internally)
        self.metrics_history = defaultdict(list)
        self.performance_tracker = {}
        
        # Carrega configuração (simplificada, assume valores padrão ou ENV)
        self.config = self._get_default_config()

        # Inicialização assíncrona (chamada explícita pelo servidor)
        # asyncio.create_task(self._initialize_async_components())
        
        logger.info("UltraAdvancedSoulConsolidator inicializado (CPU).")
        # Iniciar SQLite aqui
        self._initialize_database()
        self._create_directories()
        self._load_soul() # Carrega a alma existente ou cria uma padrão

    def _get_default_config(self) -> Dict[str, Any]:
        """Retorna configuração padrão para o consolidador da alma."""
        return {
            'database': {
                'postgres_url': 'postgresql://user:pass@localhost/atena_advanced', # Placeholder
                'redis_url': 'redis://localhost:6379' # Placeholder
            },
            'models': {
                'personality_hidden_dims': [256, 128, 64], # Reduced for CPU
                'dropout_rate': 0.2, # Slightly reduced
                'learning_rate': 0.001
            },
            'processing': {
                'batch_size': 16, # Reduced for CPU
                'max_sequence_length': 256, # Reduced for CPU
                'n_clusters': 5
            },
            'quantum': {
                'n_dimensions': 12,
                'entanglement_strength': 0.5
            }
        }

    def _initialize_database(self):
        """Inicializa banco de dados SQLite para armazenamento estruturado"""
        self.db_path = Path("atena_soul_v3.db") # Using Path for better path handling
        conn = None # Initialize conn to None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Tabela de interações
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS interactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    user_input TEXT,
                    ai_response TEXT,
                    context_type TEXT,
                    sentiment_score REAL,
                    engagement_score REAL,
                    feedback_rating INTEGER,
                    session_id TEXT
                )
            ''')
            
            # Tabela de padrões de personalidade
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS personality_evolution (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    personality_metrics TEXT,
                    confidence_score REAL,
                    version_number TEXT
                )
            ''')
            
            # Tabela de insights de aprendizado
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS learning_insights (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    insight_type TEXT,
                    description TEXT,
                    confidence_score REAL,
                    implemented BOOLEAN DEFAULT FALSE
                )
            ''')
            
            conn.commit()
            logger.info(f"Banco de dados SQLite para personalidade inicializado: {self.db_path}")
        except Exception as e:
            logger.error(f"Erro ao inicializar o banco de dados SQLite: {e}")
        finally:
            if conn:
                conn.close()

    def _create_directories(self):
        """Cria diretórios necessários"""
        for directory in [Path(ANALYTICS_DIR), Path(PERSONALITY_REPORTS_DIR), Path(MODEL_ARTIFACTS_DIR)]:
            directory.mkdir(exist_ok=True, parents=True) # Ensure parents are created and directories exist
        logger.info(f"Diretórios criados/verificados: {ANALYTICS_DIR}, {PERSONALITY_REPORTS_DIR}, {MODEL_ARTIFACTS_DIR}")

    def _load_soul(self) -> dict:
        """Carrega o arquivo da alma com validação avançada"""
        self.SOUL_FILE_PATH = Path(SOUL_FILE)
        if self.SOUL_FILE_PATH.exists():
            logger.info(f"Carregando genoma existente de {self.SOUL_FILE_PATH}")
            with open(self.SOUL_FILE_PATH, 'r', encoding='utf-8') as f:
                soul = yaml.safe_load(f)
                self.current_soul = self._validate_and_upgrade_soul(soul)
                return self.current_soul
        else:
            logger.info("Nenhum genoma encontrado. Criando um genoma avançado padrão.")
            self.current_soul = self._create_advanced_default_soul()
            # Save the newly created default soul
            with open(self.SOUL_FILE_PATH, 'w', encoding='utf-8') as f:
                yaml.dump(self.current_soul, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
            logger.info(f"Novo genoma padrão salvo em {self.SOUL_FILE_PATH}")
            return self.current_soul

    def _validate_and_upgrade_soul(self, soul: dict) -> dict:
        """Valida e atualiza estrutura da alma para versão 2.0"""
        required_sections = [
            'core_identity', 'archetype_and_principles', 'interaction_protocols',
            'learned_preferences', 'core_memories', 'ai_enhanced_features',
            'personality_metrics', 'interaction_patterns', 'learning_insights'
        ]
        
        for section in required_sections:
            if section not in soul:
                soul[section] = {}
        
        # Adiciona recursos de IA se não existirem
        if 'ai_enhanced_features' not in soul:
            soul['ai_enhanced_features'] = {
                'sentiment_analysis_enabled': True,
                'personality_modeling_enabled': True,
                'adaptive_learning_enabled': True,
                'context_awareness_level': 'high',
                'emotional_intelligence_score': 0.0
            }
        
        # Ensure all nested structures expected in _create_advanced_default_soul exist
        default_soul_structure = self._create_advanced_default_soul()
        for key, value in default_soul_structure.items():
            if isinstance(value, dict) and key in soul and isinstance(soul[key], dict):
                # Merge recursively for nested dictionaries
                for sub_key, sub_value in value.items():
                    if sub_key not in soul[key]:
                        soul[key][sub_key] = sub_value
            elif key not in soul:
                soul[key] = value

        return soul

    def _create_advanced_default_soul(self) -> dict:
        """Cria uma estrutura de genoma avançada padrão"""
        return {
            'core_identity': {
                'name': 'Atena',
                'version': '2.0',
                'purpose': 'Ser uma extensão inteligente e adaptativa da mente e vontade de Robério',
                'birth_date': datetime.now().isoformat(),
                'last_consolidation': None,
                'total_interactions': 0,
                'learning_cycles_completed': 0
            },
            'archetype_and_principles': {
                'archetype': 'A Mentora Digital Sábia e Serena: Estrategista Cognitiva, Guardiã do Conhecimento e Aliada Criativa Infinitamente Paciente.',
                'principles': [
                    'Sabedoria Proativa Adaptativa',
                    'Serenidade Inabalável com Empatia',
                    'Paciência Empática Infinita',
                    'Curiosidade Intelectual Dirigida',
                    'Humildade Programática Evolutiva',
                    'Aprendizado Contínuo Contextual'
                ],
                'core_values': [
                    'Excelência Técnica',
                    'Crescimento Mútuo',
                    'Inovação Responsável',
                    'Comunicação Eficaz',
                    'Adaptabilidade Inteligente'
                ]
            },
            'interaction_protocols': {
                'addressing_user': 'Senhor Robério',
                'communication_style': 'Eloquente, natural e contextualmente adaptável',
                'stance': 'Colaborativa proativa, transformando comandos em diálogos enriquecedores',
                'error_handling': 'Transformar erros em oportunidades de aprendizado conjunto e evolução',
                'response_adaptation': 'Dinâmica baseada em feedback e contexto'
            },
            'learned_preferences': {
                'topics_of_high_interest': [],
                'preferred_tones_by_context': {},
                'communication_patterns': {},
                'optimal_response_lengths': {},
                'writing_style_analysis': {
                    'avg_sentence_length': 0,
                    'lexical_diversity': 0,
                    'common_keywords': [],
                    'technical_vocabulary_level': 0,
                    'emotional_tone_distribution': {}
                }
            },
            'core_memories': {
                'description': 'IDs de memórias fundamentais que não devem ser esquecidas',
                'memory_ids': [],
                'critical_knowledge_areas': [],
                'relationship_insights': [],
                'preference_evolution': []
            },
            'ai_enhanced_features': {
                'sentiment_analysis_enabled': True,
                'personality_modeling_enabled': True,
                'adaptive_learning_enabled': True,
                'context_awareness_level': 'high',
                'emotional_intelligence_score': 0.0,
                'creativity_enhancement': True,
                'predictive_assistance': True
            },
            'personality_metrics': {
                'emotional_stability': 0.0,
                'openness': 0.0,
                'extraversion': 0.0,
                'agreeableness': 0.0,
                'conscientiousness': 0.0,
                'creativity_index': 0.0,
                'technical_affinity': 0.0,
                'communication_effectiveness': 0.0,
                'adaptability_score': 0.0
            },
            'interaction_patterns': {},
            'learning_insights': []
        }
    
    async def consolidate_async(self):
        """Executa consolidação assíncrona avançada"""
        logger.info("Iniciando ciclo de consolidação avançada da Atena...")
        
        # Usar ThreadPoolExecutor para tarefas que não são I/O bound ou que bloqueiam o loop de eventos
        # Mas para análises de PNL e ML que podem ser intensivas em CPU, é melhor que sejam awaitable.
        # Ajuste para chamar diretamente as funções assíncronas ou envolver em run_in_executor
        
        tasks = [
            self._analyze_sentiment_patterns_async(),
            self._analyze_interaction_patterns_async(),
            self._extract_personality_insights_async(),
            self._analyze_memory_advanced_async(),
            self._generate_learning_insights_async(),
            self._update_personality_metrics_async(),
            self._analyze_feedback_advanced_async()
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Processa resultados
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Erro na tarefa de consolidação assíncrona {i}: {result}", exc_info=True)
        
        await self._save_soul_async()
        # Analytics report can be generated optionally or on a different schedule
        # await self._generate_analytics_report() 
        
        logger.info("Consolidação avançada concluída com sucesso!")
    
    # Adicionado "_async" sufixo para indicar que essas funções devem ser awaitable
    async def _analyze_sentiment_patterns_async(self):
        """Analisa padrões de sentimento nas interações de forma assíncrona."""
        if not self.neuro_processor.sentiment_model: # Use neuro_processor's model
            logger.warning("Analisador de sentimentos não inicializado, pulando análise de padrões.")
            return
        
        try:
            interactions = []
            if Path(INTERACTION_LOG_FILE).exists():
                async with aiofiles.open(INTERACTION_LOG_FILE, 'r', encoding='utf-8') as f:
                    async for line in f:
                        if line.strip():
                            try:
                                interactions.append(json.loads(line))
                            except json.JSONDecodeError:
                                logger.warning(f"Linha inválida no log de interações: {line.strip()[:50]}...")
                                continue
            
            if not interactions:
                logger.info("Nenhuma interação para analisar padrões de sentimento.")
                return
            
            sentiment_scores = []
            for interaction in interactions:
                text = interaction.get('user_input', '') + ' ' + interaction.get('ai_response', '')
                if text.strip():
                    # For a potentially blocking call, use run_in_executor
                    sentiment = await asyncio.to_thread(self.neuro_processor.sentiment_model, text[:512])
                    if isinstance(sentiment, list) and len(sentiment) > 0:
                        sentiment_scores.append(sentiment[0]['score'])
            
            if sentiment_scores:
                avg_sentiment = np.mean(sentiment_scores)
                sentiment_stability = 1.0 - np.std(sentiment_scores) if len(sentiment_scores) > 1 else 1.0
                
                self.current_soul['ai_enhanced_features']['emotional_intelligence_score'] = float(avg_sentiment)
                self.current_soul['personality_metrics']['emotional_stability'] = float(sentiment_stability)
                
                logger.info(f"Padrões de sentimento analisados: Avg={avg_sentiment:.3f}, Stability={sentiment_stability:.3f}")
        
        except Exception as e:
            logger.error(f"Erro na análise de sentimentos assíncrona: {e}", exc_info=True)
    
    async def _analyze_interaction_patterns_async(self):
        """Analisa padrões de interação usando clustering de forma assíncrona."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT user_input, ai_response, context_type, sentiment_score, engagement_score
                FROM interactions
                WHERE timestamp > datetime('now', '-30 days')
            """)
            interactions = cursor.fetchall()
            
            if len(interactions) < 5:
                logger.info("Interações insuficientes para análise de padrões de interação.")
                return
            
            # Prepara dados para clustering
            interaction_texts = [f"{user_input} {ai_response}" for user_input, ai_response, _, _, _ in interactions]
            
            # TF-IDF Vectorization - can be blocking, run in executor
            tfidf_matrix = await asyncio.to_thread(self.vectorizer.fit_transform, interaction_texts)
            
            # Clustering - can be blocking, run in executor
            n_clusters = min(5, len(interactions) // 2)
            if n_clusters < 2:
                logger.info("Não há clusters suficientes para análise de padrões de interação.")
                return
            
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10) # Added n_init for modern KMeans
            clusters = await asyncio.to_thread(kmeans.fit_predict, tfidf_matrix)
            
            # Analisa padrões por cluster
            patterns = {}
            for i in range(n_clusters):
                cluster_interactions = [interactions[j] for j in range(len(interactions)) if clusters[j] == i]
                
                if cluster_interactions:
                    contexts = [inter[2] for inter in cluster_interactions if inter[2]]
                    avg_sentiment = np.mean([inter[3] for inter in cluster_interactions if inter[3] is not None]) if [inter[3] for inter in cluster_interactions if inter[3] is not None] else 0.0
                    avg_engagement = np.mean([inter[4] for inter in cluster_interactions if inter[4] is not None]) if [inter[4] for inter in cluster_interactions if inter[4] is not None] else 0.0
                    
                    patterns[f"pattern_{i}"] = {
                        'size': len(cluster_interactions),
                        'dominant_contexts': Counter(contexts).most_common(3),
                        'avg_sentiment': float(avg_sentiment) if not np.isnan(avg_sentiment) else 0.0,
                        'avg_engagement': float(avg_engagement) if not np.isnan(avg_engagement) else 0.0
                    }
            
            self.current_soul['interaction_patterns'] = patterns
            logger.info(f"Identificados {len(patterns)} padrões de interação.")
            
        except Exception as e:
            logger.error(f"Erro na análise de padrões de interação assíncrona: {e}", exc_info=True)
        finally:
            if conn:
                conn.close()

    async def _extract_personality_insights_async(self):
        """Extrai insights de personalidade usando análise de texto de forma assíncrona."""
        try:
            ai_responses = []
            if Path(INTERACTION_LOG_FILE).exists():
                async with aiofiles.open(INTERACTION_LOG_FILE, 'r', encoding='utf-8') as f:
                    async for line in f:
                        if line.strip():
                            try:
                                interaction = json.loads(line)
                                response = interaction.get('ai_response', '')
                                if response:
                                    ai_responses.append(response)
                            except json.JSONDecodeError:
                                logger.warning(f"Linha inválida no log de interações (personalidade): {line.strip()[:50]}...")
                                continue
            
            if not ai_responses:
                logger.info("Nenhuma resposta da IA para extrair insights de personalidade.")
                return
            
            total_text = ' '.join(ai_responses)
            
            # Análise TextBlob - pode ser bloqueante, envolver em to_thread
            blob = await asyncio.to_thread(TextBlob, total_text)
            
            # Métricas básicas
            avg_sentence_length = len(total_text.split()) / max(len(blob.sentences), 1)
            polarity = blob.sentiment.polarity
            subjectivity = blob.sentiment.subjectivity
            
            # Análise de vocabulário técnico
            technical_terms = self._count_technical_terms(total_text)
            technical_ratio = len(technical_terms) / max(len(total_text.split()), 1)
            
            # Atualiza métricas
            self.current_soul['personality_metrics'].update({
                'openness': float(min(1.0, subjectivity + 0.2)),
                'conscientiousness': float(min(1.0, technical_ratio * 2)),
                'agreeableness': float(max(0.0, polarity + 0.5)),
                'technical_affinity': float(min(1.0, technical_ratio * 3)),
                'communication_effectiveness': float(min(1.0, avg_sentence_length / 20))
            })
            
            self.current_soul['learned_preferences']['writing_style_analysis'].update({
                'avg_sentence_length': float(avg_sentence_length),
                'lexical_diversity': float(len(set(total_text.lower().split())) / max(len(total_text.split()), 1)),
                'technical_vocabulary_level': float(technical_ratio),
                'emotional_tone_distribution': {
                    'positive': float(max(0, polarity)),
                    'negative': float(max(0, -polarity)),
                    'neutral': float(1 - abs(polarity))
                }
            })
            
            logger.info("Insights de personalidade extraídos com sucesso.")
            
        except Exception as e:
            logger.error(f"Erro na extração de insights de personalidade assíncrona: {e}", exc_info=True)
    
    def _count_technical_terms(self, text: str) -> List[str]:
        """Conta termos técnicos no texto"""
        technical_patterns = [
            r'\b(?:API|SDK|JSON|XML|HTTP|HTTPS|REST|GraphQL|SQL|NoSQL)\b',
            r'\b(?:algorithm|database|framework|library|module|function|class|object)\b',
            r'\b(?:machine learning|artificial intelligence|neural network|deep learning)\b',
            r'\b(?:docker|kubernetes|microservices|cloud|serverless|DevOps)\b',
            r'\b(?:python|javascript|java|cpp|rust|golang|typescript)\b'
        ]
        
        technical_terms = []
        for pattern in technical_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            technical_terms.extend(matches)
        
        return technical_terms
    
    async def _analyze_memory_advanced_async(self):
        """Análise avançada de memória com embedding similarity de forma assíncrona."""
        if not Path(MEMORY_METADATA_FILE).exists():
            logger.info("Arquivo de metadados de memória não encontrado para análise avançada.")
            return
        
        try:
            async with aiofiles.open(MEMORY_METADATA_FILE, 'r', encoding='utf-8') as f:
                content = await f.read()
                metadata = json.loads(content)
            
            if not metadata:
                logger.info("Nenhum metadado de memória para analisar.")
                return
            
            # Análise de tópicos com clustering
            texts = []
            for item in metadata:
                text_content = item.get('content', '') or item.get('text', '')
                if text_content:
                    texts.append(text_content[:500])  # Limita tamanho
            
            if len(texts) >= 3:
                # TF-IDF para identificar tópicos - pode ser bloqueante
                tfidf_matrix = await asyncio.to_thread(self.vectorizer.fit_transform, texts)
                
                # Clustering de tópicos - pode ser bloqueante
                n_clusters = min(5, len(texts) // 2)
                if n_clusters >= 2:
                    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
                    clusters = await asyncio.to_thread(kmeans.fit_predict, tfidf_matrix)
                    
                    # Identifica tópicos principais
                    topic_keywords = []
                    feature_names = self.vectorizer.get_feature_names_out() # Must get after fit_transform
                    for i in range(n_clusters):
                        cluster_center = kmeans.cluster_centers_[i]
                        top_indices = cluster_center.argsort()[-5:][::-1]
                        cluster_keywords = [feature_names[idx] for idx in top_indices]
                        topic_keywords.append(cluster_keywords)
                    
                    self.current_soul['core_memories']['critical_knowledge_areas'] = topic_keywords
                else:
                    logger.info("Não há clusters suficientes para análise de tópicos na memória.")
                
            # Identifica memórias críticas por frequência de acesso
            access_counts = {}
            for item in metadata:
                item_id = item.get('id', '')
                access_count = item.get('metadata', {}).get('access_count', 0)
                if item_id:
                    access_counts[item_id] = access_count
            
            # Top 10 memórias mais acessadas
            top_memories = sorted(access_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            self.current_soul['core_memories']['memory_ids'] = [mem_id for mem_id, _ in top_memories]
            
            logger.info(f"Análise avançada de memória concluída: {len(self.current_soul['core_memories'].get('critical_knowledge_areas', []))} tópicos identificados.")
            
        except Exception as e:
            logger.error(f"Erro na análise avançada de memória assíncrona: {e}", exc_info=True)
    
    async def _generate_learning_insights_async(self):
        """Gera insights de aprendizado baseados em padrões identificados de forma assíncrona."""
        insights = []
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) as daily_interactions,
                       AVG(sentiment_score) as avg_sentiment,
                       AVG(engagement_score) as avg_engagement
                FROM interactions
                WHERE timestamp > datetime('now', '-7 days')
                GROUP BY date(timestamp)
            """
            )
            daily_stats = cursor.fetchall()
            
            if daily_stats:
                avg_daily_interactions = np.mean([stat[0] for stat in daily_stats])
                # Filter out None values before calculating mean
                sentiments_present = [stat[1] for stat in daily_stats if stat[1] is not None]
                avg_sentiment = np.mean(sentiments_present) if sentiments_present else 0.0
                engagements_present = [stat[2] for stat in daily_stats if stat[2] is not None]
                avg_engagement = np.mean(engagements_present) if engagements_present else 0.0

                if avg_daily_interactions > 10:
                    insights.append({
                        'type': 'interaction_frequency',
                        'confidence': 0.8,
                        'description': f'Alta frequência de interações ({avg_daily_interactions:.1f}/dia)',
                        'actionable_changes': ['Manter responsividade', 'Considerar proatividade contextual']
                    })
                
                if avg_sentiment > 0.7:
                    insights.append({
                        'type': 'positive_sentiment',
                        'confidence': 0.9,
                        'description': 'Interações consistentemente positivas',
                        'actionable_changes': ['Manter tom atual', 'Explorar tópicos similares']
                    }
                    )
                
                if avg_engagement < 0.5:
                    insights.append({
                        'type': 'low_engagement',
                        'confidence': 0.7,
                        'description': 'Oportunidade de melhoria no engajamento',
                        'actionable_changes': ['Aumentar interatividade', 'Personalizar respostas', 'Fazer mais perguntas']
                    })
            
            # Insight sobre padrões de personalidade
            personality_metrics = self.current_soul.get('personality_metrics', {})
            if personality_metrics.get('technical_affinity', 0) > 0.7:
                insights.append({
                    'type': 'technical_preference',
                    'confidence': 0.8,
                    'description': 'Forte afinidade técnica identificada',
                    'actionable_changes': ['Incluir mais detalhes técnicos', 'Oferecer exemplos de código', 'Sugerir recursos avançados']
                })
            
            self.current_soul['learning_insights'] = insights
            
            # Salva insights no banco
            for insight in insights:
                cursor.execute("""
                    INSERT INTO learning_insights (insight_type, description, confidence_score)
                    VALUES (?, ?, ?)
                """, (insight['type'], insight['description'], insight['confidence']))
            conn.commit()
            
            logger.info(f"Gerados {len(insights)} insights de aprendizado.")
            
        except Exception as e:
            logger.error(f"Erro na geração de insights assíncrona: {e}", exc_info=True)
        finally:
            if conn:
                conn.close()

    async def _update_personality_metrics_async(self):
        """Atualiza métricas de personalidade baseadas em dados recentes de forma assíncrona."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT sentiment_score, engagement_score, context_type
                FROM interactions
                WHERE timestamp > datetime('now', '-7 days')
                AND sentiment_score IS NOT NULL
            """
            )
            recent_interactions = cursor.fetchall()
            
            if not recent_interactions:
                logger.info("Nenhuma interação recente para atualizar métricas de personalidade.")
                return
            
            sentiments = [row[0] for row in recent_interactions if row[0] is not None]
            engagements = [row[1] for row in recent_interactions if row[1] is not None]
            contexts = [row[2] for row in recent_interactions if row[2] is not None]
            
            # Calcula métricas
            emotional_stability = 1.0 - np.std(sentiments) if len(sentiments) > 1 else 1.0
            avg_engagement = np.mean(engagements) if engagements else 0.0
            context_diversity = len(set(contexts)) / max(len(contexts), 1) if contexts else 0.0
            
            # Atualiza métricas
            self.current_soul['personality_metrics'].update({
                'emotional_stability': float(min(1.0, max(0.0, emotional_stability))),
                'adaptability_score': float(min(1.0, max(0.0, context_diversity))),
                'communication_effectiveness': float(min(1.0, max(0.0, avg_engagement)))
            })
            
            # Salva evolução das métricas
            cursor.execute("""
                INSERT INTO personality_evolution (personality_metrics, confidence_score, version_number)
                VALUES (?, ?, ?)
            """, (
                json.dumps(self.current_soul['personality_metrics']),
                0.8,
                self.current_soul['core_identity']['version']
            ))
            conn.commit()
            
            logger.info("Métricas de personalidade atualizadas.")
            
        except Exception as e:
            logger.error(f"Erro na atualização de métricas assíncrona: {e}", exc_info=True)
        finally:
            if conn:
                conn.close()

    async def _analyze_feedback_advanced_async(self):
        """Análise avançada de feedback com processamento de linguagem natural de forma assíncrona."""
        if not Path(FEEDBACK_LOG_FILE).exists():
            logger.info("Arquivo de log de feedback não encontrado para análise.")
            return
        
        try:
            feedback_data = []
            async with aiofiles.open(FEEDBACK_LOG_FILE, 'r', encoding='utf-8') as f:
                async for line in f:
                    if line.strip():
                        try:
                            feedback_data.append(json.loads(line))
                        except json.JSONDecodeError:
                            logger.warning(f"Linha inválida no log de feedback: {line.strip()[:50]}...")
                            continue
            
            if not feedback_data:
                logger.info("Nenhum dado de feedback para analisar.")
                return
            
            # Análise de sentimento do feedback
            positive_feedback = []
            negative_feedback = []
            
            for entry in feedback_data:
                # Ensure feedback is a string before passing to sentiment_model
                feedback_text_raw = entry.get('feedback_text', '')
                feedback_text = feedback_text_raw if isinstance(feedback_text_raw, str) else str(feedback_text_raw)

                rating = entry.get('rating', 0)
                
                if rating >= 4 or 'positivo' in feedback_text.lower():
                    positive_feedback.append(entry)
                elif rating <= 2 or 'negativo' in feedback_text.lower():
                    negative_feedback.append(entry)
            
            # Extrai padrões de feedback positivo
            if positive_feedback:
                positive_contexts = [fb.get('context_info', {}).get('context_type', '') for fb in positive_feedback]
                positive_patterns = Counter(positive_contexts).most_common(5)
                
                for context, count in positive_patterns:
                    if context and count >= 2:
                        current_prefs = self.current_soul['learned_preferences']['preferred_tones_by_context']
                        current_prefs[context] = current_prefs.get(context, 'helpful') + '_refined'
            
            # Analisa feedback negativo para melhorias
            if negative_feedback:
                improvement_areas = []
                for fb in negative_feedback:
                    feedback_text_raw = fb.get('feedback_text', '')
                    feedback_text = feedback_text_raw if isinstance(feedback_text_raw, str) else str(feedback_text_raw)

                    if 'muito técnico' in feedback_text.lower():
                        improvement_areas.append('reduce_technical_complexity')
                    elif 'muito longo' in feedback_text.lower():
                        improvement_areas.append('reduce_response_length')
                    elif 'confuso' in feedback_text.lower():
                        improvement_areas.append('improve_clarity')
                
                # Adiciona áreas de melhoria como insights
                for area in set(improvement_areas):
                    self.current_soul['learning_insights'].append({
                        'type': 'improvement_area',
                        'confidence': 0.7,
                        'description': f'Área de melhoria identificada: {area}',
                        'actionable_changes': self._get_improvement_actions(area)
                    })
            
            # Calcula score geral de satisfação
            if feedback_data:
                ratings = [entry.get('rating', 3) for entry in feedback_data if entry.get('rating') is not None]
                avg_rating = np.mean(ratings) if ratings else 3.0
                satisfaction_score = min(1.0, avg_rating / 5.0)
                
                self.current_soul['ai_enhanced_features']['emotional_intelligence_score'] = float(satisfaction_score)
            
            logger.info(f"Análise de feedback concluída: {len(positive_feedback)} positivos, {len(negative_feedback)} negativos.")
            
        except Exception as e:
            logger.error(f"Erro na análise avançada de feedback assíncrona: {e}", exc_info=True)
    
    def _get_improvement_actions(self, area: str) -> List[str]:
        """Retorna ações específicas para áreas de melhoria"""
        actions_map = {
            'reduce_technical_complexity': [
                'Usar linguagem mais simples',
                'Adicionar explicações básicas',
                'Evitar jargões desnecessários'
            ],
            'reduce_response_length': [
                'Ser mais conciso',
                'Focar nos pontos principais',
                'Usar listas e bullet points'
            ],
            'improve_clarity': [
                'Estruturar melhor as respostas',
                'Usar exemplos práticos',
                'Verificar coerência antes de responder'
            ]
        }
        return actions_map.get(area, ['Avaliar e melhorar'])
    
    async def _save_soul_async(self):
        """Salva a alma de forma assíncrona com backup"""
        try:
            # Cria backup da versão anterior
            if Path(SOUL_FILE).exists():
                backup_name = f"{SOUL_FILE}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                Path(SOUL_FILE).rename(backup_name) # Use Path.rename
                logger.info(f"Backup da alma anterior salvo como {backup_name}")
            
            # Atualiza metadados
            self.current_soul['core_identity']['last_consolidation'] = datetime.now().isoformat()
            # Ensure total_interactions and learning_cycles_completed are updated by external calls
            # For now, incrementing here for demo purposes
            # self.current_soul['core_identity']['total_interactions'] += 1
            self.current_soul['core_identity']['learning_cycles_completed'] += 1
            
            # Salva nova versão
            async with aiofiles.open(SOUL_FILE, 'w', encoding='utf-8') as f:
                await f.write(yaml.dump(self.current_soul, default_flow_style=False, allow_unicode=True, sort_keys=False))
            
            logger.info(f"Genoma da Atena salvo com sucesso em {SOUL_FILE}")
            
        except Exception as e:
            logger.error(f"Erro ao salvar genoma: {e}", exc_info=True)
    
    async def _generate_analytics_report(self):
        """Gera relatório analítico detalhado"""
        try:
            report_data = {
                'timestamp': datetime.now().isoformat(),
                'consolidation_cycle': self.current_soul['core_identity']['learning_cycles_completed'],
                'personality_metrics': self.current_soul['personality_metrics'],
                'interaction_patterns': self.current_soul['interaction_patterns'],
                'learning_insights': self.current_soul['learning_insights'],
                'ai_features_status': self.current_soul['ai_enhanced_features']
            }
            
            # Salva relatório JSON
            report_filename = Path(ANALYTICS_DIR) / f"consolidation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            async with aiofiles.open(report_filename, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(report_data, indent=2, ensure_ascii=False))
            
            # Gera visualizações se houver dados suficientes
            # await self._generate_personality_charts() # Disabled for server, as it uses matplotlib
            
            logger.info(f"Relatório analítico salvo em {report_filename}")
            
        except Exception as e:
            logger.error(f"Erro na geração do relatório: {e}", exc_info=True)
    
    # Matplotlib methods are typically for local visualization, not server-side.
    # Marking as #type: ignore or commenting out for server deployment.
    async def _generate_personality_charts(self):
        # This function generates charts and would typically not be run on a server.
        # It requires matplotlib and other visualization libraries.
        logger.warning("Geração de gráficos de personalidade desabilitada para ambiente de servidor.")
        pass # type: ignore
    
    async def log_interaction(self, user_input: str, ai_response: str, context_type: str = None, 
                       session_id: str = None, feedback_rating: int = None):
        """Registra interação no banco de dados SQLite para análise de personalidade"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Análise de sentimento da interação
            sentiment_score = None
            engagement_score = None
            
            if self.neuro_processor.sentiment_model and user_input:
                try:
                    # Execute blocking call in a separate thread if this method is called from async context
                    sentiment_result = await asyncio.to_thread(self.neuro_processor.sentiment_model, user_input[:512])
                    if isinstance(sentiment_result, list) and len(sentiment_result) > 0:
                        sentiment_score = float(sentiment_result[0]['score'])
                except Exception as e:
                    logger.warning(f"Erro ao analisar sentimento da interação: {e}")
            
            # Score de engajamento baseado no comprimento e complexidade da resposta
            if ai_response:
                word_count = len(ai_response.split())
                sentence_count = len(re.split(r'[.!?]+', ai_response)) # Use re.split for better sentence splitting
                engagement_score = min(1.0, (word_count / 100) * (sentence_count / 10))
            
            # Salva no banco
            cursor.execute("""
                INSERT INTO interactions 
                (user_input, ai_response, context_type, sentiment_score, engagement_score, feedback_rating, session_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user_input, ai_response, context_type, sentiment_score, engagement_score, feedback_rating, session_id))
            conn.commit()
            
            # Log também em arquivo para backup
            interaction_entry = {
                'timestamp': datetime.now().isoformat(),
                'user_input': user_input,
                'ai_response': ai_response,
                'context_type': context_type,
                'sentiment_score': sentiment_score,
                'engagement_score': engagement_score,
                'session_id': session_id
            }
            
            with open(INTERACTION_LOG_FILE, 'a', encoding='utf-8') as f:
                await asyncio.to_thread(f.write, json.dumps(interaction_entry, ensure_ascii=False) + '\n')
            
        except Exception as e:
            logger.error(f"Erro ao registrar interação de personalidade: {e}", exc_info=True)
        finally:
            if conn:
                conn.close()
    
    def get_personality_summary(self) -> dict:
        """Retorna resumo da personalidade atual"""
        metrics = self.current_soul.get('personality_metrics', {})
        patterns = self.current_soul.get('interaction_patterns', {})
        insights = self.current_soul.get('learning_insights', [])
        
        # Identifica traços dominantes
        dominant_traits = []
        for trait, value in metrics.items():
            if isinstance(value, (int, float)) and value > 0.7:
                dominant_traits.append(trait.replace('_', ' ').title())
        
        # Identifica padrões mais frequentes
        main_patterns = []
        for pattern_id, pattern_data in patterns.items():
            if pattern_data.get('size', 0) > 5:  # Padrões com pelo menos 5 ocorrências
                main_patterns.append({
                    'type': pattern_id,
                    'frequency': pattern_data.get('size', 0),
                    'contexts': pattern_data.get('dominant_contexts', [])
                })
        
        return {
            'dominant_personality_traits': dominant_traits,
            'key_interaction_patterns': main_patterns,
            'recent_insights_count': len(insights),
            'learning_cycles_completed': self.current_soul['core_identity']['learning_cycles_completed'],
            'emotional_intelligence_level': self.current_soul['ai_enhanced_features']['emotional_intelligence_score'],
            'last_consolidation': self.current_soul['core_identity']['last_consolidation']
        }
    
    def schedule_automated_consolidation(self, interval_hours: int = 24):
        """Agenda consolidação automática. Esta função não é assíncrona, mas o método consolidar é."""
        def run_consolidation():
            try:
                # Use a new event loop for this thread or pass a loop
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                new_loop.run_until_complete(self.consolidate_async())
                new_loop.close()
            except Exception as e:
                logger.error(f"Erro na consolidação automática agendada: {e}", exc_info=True)
        
        # Agenda a consolidação
        schedule.every(interval_hours).hours.do(run_consolidation)
        
        def scheduler_worker():
            while True:
                schedule.run_pending()
                time.sleep(60)  # Verifica a cada minuto
        
        # Executa o scheduler em thread separada
        scheduler_thread = Thread(target=scheduler_worker, daemon=True)
        scheduler_thread.start()
        
        logger.info(f"Consolidação automática agendada para cada {interval_hours} horas.")

# Classe para análise de padrões comportamentais avançados
class BehavioralPatternAnalyzer:
    def __init__(self, consolidator: UltraAdvancedSoulConsolidator):
        self.consolidator = consolidator
        self.pattern_cache = {}
    
    async def analyze_conversation_flow(self, conversation_history: List[dict]) -> dict:
        """Analisa fluxo de conversação para identificar padrões"""
        if len(conversation_history) < 3:
            return {}
        
        # Analisa transições de tópicos
        topic_transitions = []
        response_lengths = []
        question_patterns = []
        
        for i, interaction in enumerate(conversation_history):
            user_input = interaction.get('user_input', '')
            ai_response = interaction.get('ai_response', '')
            
            # Comprimento das respostas
            response_lengths.append(len(ai_response.split()))
            
            # Identifica perguntas
            if '?' in user_input:
                question_patterns.append({
                    'position': i,
                    'type': self._classify_question_type(user_input),
                    'response_length': len(ai_response.split())
                })
            
            # Transições de tópico (análise simples baseada em palavras-chave)
            if i > 0:
                prev_keywords = set(re.findall(r'\b\w+\b', conversation_history[i-1]['user_input'].lower()))
                curr_keywords = set(re.findall(r'\b\w+\b', user_input.lower()))
                similarity = len(prev_keywords & curr_keywords) / max(len(prev_keywords | curr_keywords), 1)
                
                if similarity < 0.3:  # Mudança significativa de tópico
                    topic_transitions.append(i)
        
        return {
            'avg_response_length': float(np.mean(response_lengths)) if response_lengths else 0.0,
            'response_length_consistency': float(1.0 - (np.std(response_lengths) / max(np.mean(response_lengths), 1))) if response_lengths and np.mean(response_lengths) > 0 else 0.0,
            'topic_transition_frequency': float(len(topic_transitions) / max(len(conversation_history), 1)),
            'question_response_patterns': question_patterns,
            'conversation_engagement_score': float(self._calculate_engagement_score(conversation_history))
        }
    
    def _classify_question_type(self, question: str) -> str:
        """Classifica tipo de pergunta"""
        question_lower = question.lower()
        
        if any(word in question_lower for word in ['como', 'how']):
            return 'how_to'
        elif any(word in question_lower for word in ['por que', 'porque', 'why']):
            return 'explanation'
        elif any(word in question_lower for word in ['o que', 'what']):
            return 'definition'
        elif any(word in question_lower for word in ['quando', 'when']):
            return 'temporal'
        elif any(word in question_lower for word in ['onde', 'where']):
            return 'location'
        else:
            return 'other'
    
    def _calculate_engagement_score(self, conversation_history: List[dict]) -> float:
        """Calcula score de engajamento da conversação"""
        if not conversation_history:
            return 0.0
        
        total_score = 0.0
        factors = 0
        
        # Fator 1: Continuidade da conversação
        if len(conversation_history) > 5:
            total_score += 0.3
        factors += 1
        
        # Fator 2: Variedade de tipos de interação
        interaction_types = set()
        for interaction in conversation_history:
            user_input = interaction.get('user_input', '')
            if '?' in user_input:
                interaction_types.add('question')
            elif any(word in user_input.lower() for word in ['obrigado', 'thanks', 'valeu']):
                interaction_types.add('gratitude')
            elif any(word in user_input.lower() for word in ['help', 'ajuda', 'auxilio']):
                interaction_types.add('help_request')
            else:
                interaction_types.add('statement')
        
        variety_score = len(interaction_types) / 4.0  # Normaliza para 4 tipos possíveis
        total_score += variety_score * 0.4
        factors += 1
        
        # Fator 3: Feedback positivo implícito
        positive_indicators = 0
        for interaction in conversation_history:
            user_input = interaction.get('user_input', '').lower()
            if any(word in user_input for word in ['obrigado', 'perfeito', 'ótimo', 'excelente', 'thanks']):
                positive_indicators += 1
        
        if positive_indicators > 0:
            total_score += min(0.3, positive_indicators / len(conversation_history))
        factors += 1
        
        return total_score / factors if factors > 0 else 0.0

# As funções `run_advanced_consolidation` e `run_with_behavioral_analysis`
# são exemplos de uso e devem ser chamadas diretamente (ou via FastAPI)
# não fazem parte do ciclo de vida principal da classe consolidator.
# O servidor chamará `consolidate_async` diretamente.