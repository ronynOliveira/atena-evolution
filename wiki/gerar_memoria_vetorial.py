import os
import json
import time
import logging
from logging.handlers import RotatingFileHandler
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.cluster import KMeans, DBSCAN, AgglomerativeClustering
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
import pickle
import asyncio
import aiofiles
from typing import List, Dict, Tuple, Optional, Union, Any
from dataclasses import dataclass, field
from collections import defaultdict, Counter
import re
import threading
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import multiprocessing as mp
from functools import lru_cache
import hashlib
import uuid
from datetime import datetime, timedelta
import torch
import transformers
from transformers import AutoTokenizer, AutoModel, pipeline
import spacy
import networkx as nx
from itertools import combinations
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from scipy import sparse
from scipy.spatial.distance import pdist, squareform
from scipy.cluster.hierarchy import linkage, fcluster
import umap
from openai import OpenAI  # Para GPT-4 integration
import anthropic  # Para Claude integration
from groq import Groq  # Para modelos Llama/Mixtral
import cohere  # Para embeddings avançados
import voyageai  # Para embeddings especializados
from rank_bm25 import BM25Okapi
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.stem import PorterStemmer
import textstat
from textblob import TextBlob
import gensim
from gensim.models import Word2Vec, Doc2Vec, LdaModel
from gensim.corpora import Dictionary
import psutil
import redis
from elasticsearch import Elasticsearch
import chromadb
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
import pinecone
from atena_config import AtenaConfig
from typing_extensions import Annotated
from prometheus_client import Counter, Histogram, Gauge, start_http_server

# Configurações avançadas


# Métricas Prometheus
CONSOLIDATION_COUNTER = Counter('memory_consolidations_total', 'Total consolidations performed')
PROCESSING_TIME = Histogram('consolidation_processing_seconds', 'Time spent processing consolidations')
MEMORY_USAGE = Gauge('memory_usage_bytes', 'Current memory usage in bytes')
CHUNK_COUNT = Gauge('total_chunks', 'Total number of chunks in memory')

@dataclass
class EnhancedChunk:
    """Chunk aprimorado com metadados avançados"""
    id: str
    text: str
    embedding: np.ndarray
    metadata: Dict[str, Any]
    
    # Novos campos
    language: str = "pt"
    quality_score: float = 0.0
    semantic_fingerprint: str = ""
    topics: List[str] = field(default_factory=list)
    entities: List[Dict] = field(default_factory=list)
    sentiment: Dict[str, float] = field(default_factory=dict)
    readability_score: float = 0.0
    creation_timestamp: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 0
    
    def __post_init__(self):
        if not self.semantic_fingerprint:
            self.semantic_fingerprint = self._generate_fingerprint()
    
    def _generate_fingerprint(self) -> str:
        """Gera uma impressão digital semântica única"""
        text_hash = hashlib.md5(self.text.encode()).hexdigest()
        embedding_hash = hashlib.md5(self.embedding.tobytes()).hexdigest()
        return f"{text_hash}_{embedding_hash[:8]}"

class AdvancedEmbeddingManager:
    """Gerenciador avançado de embeddings com múltiplos modelos"""
    
    def __init__(self, config: AtenaConfig):
        self.config = config
        self.models = {}
        self.tokenizers = {}
        self.device = torch.device("cuda" if config.use_gpu else "cpu")
        self._load_models()
    
    def _load_models(self):
        """Carrega múltiplos modelos de embedding"""
        models_to_load = [
            self.config.primary_embedding_model,
            self.config.multilingual_model,
            self.config.domain_specific_model
        ]
        
        for model_name in models_to_load:
            try:
                self.models[model_name] = SentenceTransformer(model_name, device=self.device)
                logging.info(f"Modelo carregado: {model_name}")
            except Exception as e:
                logging.error(f"Erro ao carregar modelo {model_name}: {e}")
    
    def get_embeddings(self, texts: List[str], model_name: str = None) -> np.ndarray:
        """Gera embeddings usando modelo especificado"""
        model_name = model_name or self.config.primary_embedding_model
        model = self.models.get(model_name)
        
        if not model:
            raise ValueError(f"Modelo {model_name} não disponível")
        
        return model.encode(texts, batch_size=self.config.batch_size, show_progress_bar=True)
    
    def get_ensemble_embeddings(self, texts: List[str]) -> np.ndarray:
        """Gera embeddings ensemble usando múltiplos modelos"""
        all_embeddings = []
        
        for model_name, model in self.models.items():
            embeddings = model.encode(texts, batch_size=self.config.batch_size)
            all_embeddings.append(embeddings)
        
        # Concatenar ou fazer média dos embeddings
        if len(all_embeddings) > 1:
            return np.concatenate(all_embeddings, axis=1)
        return all_embeddings[0]

class SemanticAnalyzer:
    """Analisador semântico avançado para chunks"""
    
    def __init__(self, config: AtenaConfig):
        self.config = config
        self.nlp = None
        self.sentiment_analyzer = None
        self.topic_model = None
        self._initialize_analyzers()
    
    def _initialize_analyzers(self):
        """Inicializa analisadores NLP"""
        try:
            # SpaCy para análise linguística
            self.nlp = spacy.load("pt_core_news_sm")
        except OSError:
            logging.warning("Modelo SpaCy português não encontrado. Usando modelo básico.")
            self.nlp = spacy.load("pt_core_news_sm", disable=["parser", "ner"])
        
        # Analisador de sentimento
        self.sentiment_analyzer = pipeline(
            "sentiment-analysis", 
            model="neuralmind/bert-base-portuguese-cased",
            device=0 if self.config.use_gpu else -1
        )
    
    def analyze_chunk(self, chunk: EnhancedChunk) -> EnhancedChunk:
        """Analisa um chunk e adiciona metadados semânticos"""
        text = chunk.text
        
        # Análise de qualidade
        chunk.quality_score = self._calculate_quality_score(text)
        
        # Análise de entidades
        chunk.entities = self._extract_entities(text)
        
        # Análise de sentimento
        chunk.sentiment = self._analyze_sentiment(text)
        
        # Análise de legibilidade
        chunk.readability_score = self._calculate_readability(text)
        
        # Extração de tópicos
        chunk.topics = self._extract_topics(text)
        
        return chunk
    
    def _calculate_quality_score(self, text: str) -> float:
        """Calcula score de qualidade do texto"""
        if not text or len(text.strip()) < 10:
            return 0.0
        
        # Múltiplos critérios de qualidade
        scores = []
        
        # Comprimento adequado
        length_score = min(1.0, len(text) / 500)
        scores.append(length_score)
        
        # Diversidade de palavras
        words = text.lower().split()
        unique_words = set(words)
        diversity_score = len(unique_words) / len(words) if words else 0
        scores.append(diversity_score)
        
        # Presença de pontuação (estrutura)
        punct_score = min(1.0, text.count('.') + text.count('!') + text.count('?')) / 10
        scores.append(punct_score)
        
        # Score composto
        return np.mean(scores)
    
    def _extract_entities(self, text: str) -> List[Dict]:
        """Extrai entidades nomeadas do texto"""
        if not self.nlp:
            return []
        
        doc = self.nlp(text)
        entities = []
        
        for ent in doc.ents:
            entities.append({
                "text": ent.text,
                "label": ent.label_,
                "start": ent.start_char,
                "end": ent.end_char,
                "confidence": getattr(ent, "_.confidence", 1.0)
            })
        
        return entities
    
    def _analyze_sentiment(self, text: str) -> Dict[str, float]:
        """Analisa sentimento do texto"""
        if not self.sentiment_analyzer:
            return {"score": 0.0, "label": "neutral"}
        
        try:
            result = self.sentiment_analyzer(text[:512])  # Limite de tokens
            return {
                "score": result[0]["score"],
                "label": result[0]["label"]
            }
        except:
            return {"score": 0.0, "label": "neutral"}
    
    def _calculate_readability(self, text: str) -> float:
        """Calcula score de legibilidade"""
        if not text:
            return 0.0
        
        try:
            # Flesch Reading Ease adaptado para português
            return textstat.flesch_reading_ease(text) / 100.0
        except:
            return 0.5  # Score neutro em caso de erro
    
    def _extract_topics(self, text: str) -> List[str]:
        """Extrai tópicos principais do texto"""
        if not text:
            return []
        
        # Implementação simples com palavras-chave
        words = word_tokenize(text.lower())
        words = [w for w in words if w.isalpha() and len(w) > 3]
        
        # Contar frequência
        word_freq = Counter(words)
        top_words = [word for word, count in word_freq.most_common(5)]
        
        return top_words

class AdvancedClusteringEngine:
    """Motor de clustering avançado com múltiplos algoritmos"""
    
    def __init__(self, config: AtenaConfig):
        self.config = config
        self.algorithms = {
            "kmeans": self._kmeans_clustering,
            "dbscan": self._dbscan_clustering,
            "hierarchical": self._hierarchical_clustering,
            "spectral": self._spectral_clustering,
            "gaussian_mixture": self._gaussian_mixture_clustering
        }
    
    def find_optimal_clusters(self, embeddings: np.ndarray, 
                            algorithm: str = "kmeans") -> List[List[int]]:
        """Encontra clusters ótimos usando algoritmo especificado"""
        if algorithm not in self.algorithms:
            raise ValueError(f"Algoritmo {algorithm} não suportado")
        
        return self.algorithms[algorithm](embeddings)
    
    def _kmeans_clustering(self, embeddings: np.ndarray) -> List[List[int]]:
        """Clustering K-means com determinação automática de K"""
        # Determinar K ótimo usando método do cotovelo
        max_k = min(50, len(embeddings) // 10)
        if max_k < 2:
            return []
        
        inertias = []
        K_range = range(2, max_k + 1)
        
        for k in K_range:
            kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
            kmeans.fit(embeddings)
            inertias.append(kmeans.inertia_)
        
        # Encontrar cotovelo (método simples)
        optimal_k = self._find_elbow(inertias) + 2
        
        # Clustering final
        kmeans = KMeans(n_clusters=optimal_k, random_state=42, n_init=10)
        labels = kmeans.fit_predict(embeddings)
        
        return self._labels_to_clusters(labels)
    
    def _dbscan_clustering(self, embeddings: np.ndarray) -> List[List[int]]:
        """Clustering DBSCAN"""
        # Estimar eps usando k-distance
        eps = self._estimate_eps(embeddings)
        
        dbscan = DBSCAN(eps=eps, min_samples=3, metric='cosine')
        labels = dbscan.fit_predict(embeddings)
        
        return self._labels_to_clusters(labels, ignore_noise=True)
    
    def _hierarchical_clustering(self, embeddings: np.ndarray) -> List[List[int]]:
        """Clustering hierárquico"""
        # Usar distância cosseno
        distances = pdist(embeddings, metric='cosine')
        linkage_matrix = linkage(distances, method='ward')
        
        # Determinar número de clusters
        n_clusters = min(20, len(embeddings) // 5)
        labels = fcluster(linkage_matrix, n_clusters, criterion='maxclust')
        
        return self._labels_to_clusters(labels - 1)  # Ajustar para base 0
    
    def _spectral_clustering(self, embeddings: np.ndarray) -> List[List[int]]:
        """Clustering espectral"""
        from sklearn.cluster import SpectralClustering
        
        n_clusters = min(15, len(embeddings) // 8)
        spectral = SpectralClustering(
            n_clusters=n_clusters, 
            affinity='cosine',
            random_state=42
        )
        labels = spectral.fit_predict(embeddings)
        
        return self._labels_to_clusters(labels)
    
    def _gaussian_mixture_clustering(self, embeddings: np.ndarray) -> List[List[int]]:
        """Clustering Gaussian Mixture Model"""
        from sklearn.mixture import GaussianMixture
        
        # Determinar número ótimo de componentes usando BIC
        n_components_range = range(2, min(20, len(embeddings) // 5))
        bic_scores = []
        
        for n_components in n_components_range:
            gmm = GaussianMixture(n_components=n_components, random_state=42)
            gmm.fit(embeddings)
            bic_scores.append(gmm.bic(embeddings))
        
        optimal_components = n_components_range[np.argmin(bic_scores)]
        
        # Clustering final
        gmm = GaussianMixture(n_components=optimal_components, random_state=42)
        labels = gmm.fit_predict(embeddings)
        
        return self._labels_to_clusters(labels)
    
    def _find_elbow(self, values: List[float]) -> int:
        """Encontra o ponto de cotovelo em uma curva"""
        if len(values) < 3:
            return 0
        
        # Método da segunda derivada
        diffs = np.diff(values)
        second_diffs = np.diff(diffs)
        
        return np.argmax(second_diffs)
    
    def _estimate_eps(self, embeddings: np.ndarray, k: int = 3) -> float:
        """Estima eps para DBSCAN usando k-distance"""
        from sklearn.neighbors import NearestNeighbors
        
        nbrs = NearestNeighbors(n_neighbors=k, metric='cosine')
        nbrs.fit(embeddings)
        distances, _ = nbrs.kneighbors(embeddings)
        
        # Usar o 95º percentil das distâncias
        return np.percentile(distances[:, -1], 95)
    
    def _labels_to_clusters(self, labels: np.ndarray, ignore_noise: bool = False) -> List[List[int]]:
        """Converte labels para listas de clusters"""
        clusters = defaultdict(list)
        
        for idx, label in enumerate(labels):
            if ignore_noise and label == -1:
                continue
            clusters[label].append(idx)
        
        # Filtrar clusters muito pequenos ou muito grandes
        valid_clusters = []
        for cluster in clusters.values():
            if 2 <= len(cluster) <= 20:  # Limites configuráveis
                valid_clusters.append(cluster)
        
        return valid_clusters

class LLMConsolidator:
    """Consolidador inteligente usando LLMs"""
    
    def __init__(self, config: AtenaConfig):
        self.config = config
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Inicializa cliente LLM"""
        if not self.config.use_llm_consolidation:
            return
        
        try:
            if self.config.llm_provider == "openai":
                self.client = OpenAI()
            elif self.config.llm_provider == "anthropic":
                self.client = anthropic.Anthropic()
            elif self.config.llm_provider == "groq":
                self.client = Groq()
            elif self.config.llm_provider == "cohere":
                self.client = cohere.Client()
            elif self.config.llm_provider == "ollama":
                from ollama import Client
                self.client = Client(host='http://localhost:11434')
        except Exception as e:
            logging.error(f"Erro ao inicializar cliente LLM: {e}")
            self.config.use_llm_consolidation = False
    
    async def intelligent_consolidation(self, chunks: List[EnhancedChunk]) -> str:
        """Consolida chunks usando IA avançada"""
        if not self.config.use_llm_consolidation or not self.client:
            return self._fallback_consolidation(chunks)
        
        # Preparar prompt
        texts = [chunk.text for chunk in chunks]
        prompt = self._create_consolidation_prompt(texts)
        
        try:
            if self.config.llm_provider == "openai":
                response = await self._openai_consolidate(prompt)
            elif self.config.llm_provider == "anthropic":
                response = await self._anthropic_consolidate(prompt)
            elif self.config.llm_provider == "ollama":
                response = await self._ollama_consolidate(prompt)
            else:
                response = self._fallback_consolidation(chunks)
            
            return response
        except Exception as e:
            logging.error(f"Erro na consolidação LLM: {e}")
            return self._fallback_consolidation(chunks)
    
    def _create_consolidation_prompt(self, texts: List[str]) -> str:
        """Cria prompt para consolidação inteligente"""
        context = "\n\n---\n\n".join(texts)
        
        return f"""
Você é um especialista em consolidação de texto. Sua tarefa é analisar os textos abaixo e criar uma versão consolidada que:

1. Preserva todas as informações importantes
2. Remove redundâncias desnecessárias
3. Mantém coerência e fluidez
4. Organiza o conteúdo de forma lógica
5. Preserva o contexto original

Textos para consolidar:
{context}

Por favor, forneça uma versão consolidada que seja clara, concisa e completa:
"""
    
    async def _openai_consolidate(self, prompt: str) -> str:
        """Consolida usando OpenAI GPT"""
        response = await self.client.chat.completions.create(
            model=self.config.llm_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=2000
        )
        return response.choices[0].message.content
    
    async def _anthropic_consolidate(self, prompt: str) -> str:
        """Consolida usando Anthropic Claude"""
        response = await self.client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text

    async def _ollama_consolidate(self, prompt: str) -> str:
        """Consolida usando Ollama"""
        response = await self.client.chat(
            model=self.config.llm_model,
            messages=[{"role": "user", "content": prompt}]
        )
        return response['message']['content']
    
    def _fallback_consolidation(self, chunks: List[EnhancedChunk]) -> str:
        """Consolidação de fallback sem LLM"""
        # Implementação básica de consolidação
        texts = [chunk.text for chunk in chunks]
        
        # Dividir em sentenças e remover duplicatas
        all_sentences = []
        for text in texts:
            sentences = sent_tokenize(text)
            all_sentences.extend(sentences)
        
        # Remover sentenças muito similares
        unique_sentences = self._remove_similar_sentences(all_sentences)
        
        return " ".join(unique_sentences)
    
    def _remove_similar_sentences(self, sentences: List[str], threshold: float = 0.8) -> List[str]:
        """Remove sentenças similares"""
        if len(sentences) <= 1:
            return sentences
        
        # Embedding simples usando TF-IDF
        from sklearn.feature_extraction.text import TfidfVectorizer
        
        vectorizer = TfidfVectorizer()
        tfidf_matrix = vectorizer.fit_transform(sentences)
        
        # Calcular similaridades
        similarities = cosine_similarity(tfidf_matrix)
        
        # Marcar sentenças para remoção
        to_remove = set()
        for i in range(len(sentences)):
            for j in range(i + 1, len(sentences)):
                if similarities[i][j] > threshold:
                    # Manter a sentença mais longa
                    if len(sentences[i]) < len(sentences[j]):
                        to_remove.add(i)
                    else:
                        to_remove.add(j)
        
        return [sent for idx, sent in enumerate(sentences) if idx not in to_remove]

class AdvancedMemoryConsolidation:
    """Sistema avançado de consolidação de memória vetorial"""
    
    def __init__(self, memory_dir: str, config: AtenaConfig = None):
        self.memory_dir = memory_dir
        self.config = config or AtenaConfig()
        
        # Componentes avançados
        self.embedding_manager = AdvancedEmbeddingManager(self.config)
        self.semantic_analyzer = SemanticAnalyzer(self.config)
        self.clustering_engine = AdvancedClusteringEngine(self.config)
        self.llm_consolidator = LLMConsolidator(self.config)
        
        # Estado da memória
        self.chunks: List[EnhancedChunk] = []
        self.faiss_index = None
        self.metadata = {}
        
        # Cache e storage externo
        self.redis_client = None
        self.elasticsearch_client = None
        self.chromadb_client = None
        
        # Logging e métricas
        self.logger = self._setup_advanced_logging()
        self.metrics_enabled = self.config.enable_metrics
        
        if self.metrics_enabled:
            start_http_server(self.config.prometheus_port)
        
        # Inicializar componentes externos
        self._initialize_external_storage()
    
    def _setup_advanced_logging(self) -> logging.Logger:
        """Configura logging avançado"""
        logger = logging.getLogger("AdvancedMemoryConsolidation")
        logger.setLevel(logging.DEBUG)
        
        # Formatador estruturado
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
        
        # Console handler com cores
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # File handler rotativo
        file_handler = RotatingFileHandler(
            os.path.join(self.memory_dir, "advanced_consolidation.log"),
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # JSON handler para análise
        json_handler = RotatingFileHandler(
            os.path.join(self.memory_dir, "consolidation_events.jsonl"),
            maxBytes=50*1024*1024,  # 50MB
            backupCount=3
        )
        json_formatter = logging.Formatter('{"timestamp": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s", "module": "%(name)s"}')
        json_handler.setFormatter(json_formatter)
        logger.addHandler(json_handler)
        
        return logger
    
    def _initialize_external_storage(self):
        """Inicializa storage externo opcional"""
        try:
            if self.config.use_redis_cache:
                self.redis_client = redis.Redis(host='localhost', port=6379, db=0)
                self.logger.info("Redis cache inicializado")
            
            if self.config.use_elasticsearch:
                self.elasticsearch_client = Elasticsearch(['localhost:9200'])
                self.logger.info("Elasticsearch inicializado")
            
            if self.config.use_chromadb:
                self.chromadb_client = chromadb.Client()
                self.logger.info("ChromaDB inicializado")
                
        except Exception as e:
            self.logger.warning(f"Erro ao inicializar storage externo: {e}")
    
    @PROCESSING_TIME.time()
    async def perform_advanced_consolidation(self) -> Dict[str, Any]:
        """Executa consolidação avançada completa"""
        start_time = time.time()
        
        try:
            self.logger.info("=== Iniciando Consolidação Avançada ===")
            
            # Métricas iniciais
            if self.metrics_enabled:
                MEMORY_USAGE.set(psutil.Process().memory_info().rss)
            
            # Carregar e analisar memória
            await self._load_and_analyze_memory()
            
            # Consolidação multi-algoritmo
            consolidation_results = await self._multi_algorithm_consolidation()
            
            # Validação e otimização
            await self._validate_and_optimize_results(consolidation_results)
            
            # Salvar resultados
            await self._save_consolidated_memory(consolidation_results)
            
            # Relatório final
            report = self._generate_comprehensive_report(consolidation_results, start_time)
            
            if self.metrics_enabled:
                CONSOLIDATION_COUNTER.inc()
                CHUNK_COUNT.set(len(consolidation_results.get('final_chunks', [])))
            
            self.logger.info("=== Consolidação Avançada Concluída ===")
            return report
            
        except Exception as e:
            self.logger.error(f"Erro na consolidação avançada: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}
    
    async def _load_and_analyze_memory(self):
        """Carrega e analisa a memória existente"""
        self.logger.info("Carregando e analisando memória...")
        
        # Carregar arquivos base
        faiss_file = os.path.join(self.memory_dir, "atena_index.faiss")
        metadata_file = os.path.join(self.memory_dir, "atena_metadata.json")
        
        if not os.path.exists(faiss_file) or not os.path.exists(metadata_file):
            raise FileNotFoundError("Arquivos de memória não encontrados")
        
        # Carregar FAISS index
        self.faiss_index = faiss.read_index(faiss_file)
        
        # Carregar metadados
        async with aiofiles.open(metadata_file, 'r', encoding='utf-8') as f:
            content = await f.read()
            raw_metadata = json.loads(content)
        
        # Converter para EnhancedChunks com análise semântica
        self.chunks = []
        for chunk_data in raw_metadata.get('chunks', []):
            # Criar chunk base
            chunk = EnhancedChunk(
                id=chunk_data.get('id', str(uuid.uuid4())),
                text=chunk_data['text'],
                embedding=np.array(chunk_data['embedding']),
                metadata=chunk_data.get('metadata', {})
            )
            
            # Análise semântica completa
            chunk = self.semantic_analyzer.analyze_chunk(chunk)
            
            # Filtrar por qualidade se configurado
            if chunk.quality_score >= self.config.min_text_quality_score:
                self.chunks.append(chunk)
            else:
                self.logger.debug(f"Chunk {chunk.id} removido por baixa qualidade: {chunk.quality_score}")
        
        self.logger.info(f"Carregados {len(self.chunks)} chunks válidos para análise")
    
    async def _multi_algorithm_consolidation(self) -> Dict[str, Any]:
        """Executa consolidação usando múltiplos algoritmos"""
        self.logger.info("Executando consolidação multi-algoritmo...")
        
        if len(self.chunks) < 2:
            return {"final_chunks": self.chunks, "clusters": [], "algorithm_results": {}}
        
        # Preparar embeddings
        embeddings = np.array([chunk.embedding for chunk in self.chunks])
        
        # Executar múltiplos algoritmos de clustering
        algorithm_results = {}
        all_clusters = []
        
        for algorithm in self.config.clustering_algorithms:
            try:
                self.logger.info(f"Executando clustering {algorithm}...")
                clusters = self.clustering_engine.find_optimal_clusters(embeddings, algorithm)
                algorithm_results[algorithm] = {
                    "clusters": clusters,
                    "num_clusters": len(clusters),
                    "coverage": sum(len(cluster) for cluster in clusters) / len(self.chunks)
                }
                all_clusters.extend(clusters)
                self.logger.info(f"{algorithm}: {len(clusters)} clusters encontrados")
                
            except Exception as e:
                self.logger.error(f"Erro no algoritmo {algorithm}: {e}")
                algorithm_results[algorithm] = {"error": str(e)}
        
        # Consensus clustering - encontrar clusters consistentes
        consensus_clusters = self._find_consensus_clusters(all_clusters)
        
        # Consolidação inteligente dos clusters
        consolidated_chunks = []
        consolidation_tasks = []
        
        for cluster in consensus_clusters:
            cluster_chunks = [self.chunks[i] for i in cluster]
            
            # Decidir se consolidar baseado em critérios avançados
            if self._should_consolidate_cluster(cluster_chunks):
                task = self._consolidate_cluster_intelligent(cluster_chunks)
                consolidation_tasks.append(task)
            else:
                # Manter chunks separados mas com metadados atualizados
                for chunk in cluster_chunks:
                    chunk.metadata['cluster_id'] = f"cluster_{len(consolidated_chunks)}"
                    consolidated_chunks.append(chunk)
        
        # Executar consolidações em paralelo
        if consolidation_tasks:
            consolidated_results = await asyncio.gather(*consolidation_tasks, return_exceptions=True)
            
            for result in consolidated_results:
                if isinstance(result, Exception):
                    self.logger.error(f"Erro na consolidação: {result}")
                elif result:
                    consolidated_chunks.append(result)
        
        # Adicionar chunks não clusterizados
        clustered_indices = set()
        for cluster in consensus_clusters:
            clustered_indices.update(cluster)
        
        for i, chunk in enumerate(self.chunks):
            if i not in clustered_indices:
                chunk.metadata['cluster_id'] = 'singleton'
                consolidated_chunks.append(chunk)
        
        return {
            "final_chunks": consolidated_chunks,
            "clusters": consensus_clusters,
            "algorithm_results": algorithm_results,
            "consolidation_stats": {
                "original_count": len(self.chunks),
                "final_count": len(consolidated_chunks),
                "reduction_ratio": 1 - (len(consolidated_chunks) / len(self.chunks)),
                "clusters_formed": len(consensus_clusters)
            }
        }
    
    def _find_consensus_clusters(self, all_clusters: List[List[int]]) -> List[List[int]]:
        """Encontra clusters consensuais entre diferentes algoritmos"""
        self.logger.info("Calculando consensus clustering...")
        
        # Contar co-ocorrências de pares de elementos
        co_occurrence = defaultdict(int)
        total_algorithms = len(self.config.clustering_algorithms)
        
        for cluster in all_clusters:
            for i, j in combinations(cluster, 2):
                pair = tuple(sorted([i, j]))
                co_occurrence[pair] += 1
        
        # Construir grafo de consenso
        G = nx.Graph()
        G.add_nodes_from(range(len(self.chunks)))
        
        # Adicionar arestas baseadas em consenso
        consensus_threshold = max(1, total_algorithms // 2)  # Maioria simples
        
        for (i, j), count in co_occurrence.items():
            if count >= consensus_threshold:
                G.add_edge(i, j, weight=count / total_algorithms)
        
        # Encontrar componentes conectados
        consensus_clusters = list(nx.connected_components(G))
        consensus_clusters = [list(cluster) for cluster in consensus_clusters if len(cluster) >= 2]
        
        self.logger.info(f"Consensus clustering: {len(consensus_clusters)} clusters consensuais")
        return consensus_clusters
    
    def _should_consolidate_cluster(self, cluster_chunks: List[EnhancedChunk]) -> bool:
        """Decide se um cluster deve ser consolidado"""
        if len(cluster_chunks) < 2:
            return False
        
        # Critérios múltiplos para consolidação
        
        # 1. Similaridade semântica alta
        embeddings = np.array([chunk.embedding for chunk in cluster_chunks])
        similarities = cosine_similarity(embeddings)
        avg_similarity = np.mean(similarities[np.triu_indices_from(similarities, k=1)])
        
        if avg_similarity < self.config.similarity_thresholds['medium']:
            return False
        
        # 2. Qualidade dos chunks
        avg_quality = np.mean([chunk.quality_score for chunk in cluster_chunks])
        if avg_quality < self.config.min_text_quality_score:
            return False
        
        # 3. Tamanho do cluster (não muito grande para manter contexto)
        if len(cluster_chunks) > 10:
            return False
        
        # 4. Análise de tópicos (chunks devem ter tópicos similares)
        all_topics = set()
        for chunk in cluster_chunks:
            all_topics.update(chunk.topics)
        
        topic_overlap = 0
        for chunk in cluster_chunks:
            chunk_topics = set(chunk.topics)
            if chunk_topics:
                overlap = len(chunk_topics.intersection(all_topics)) / len(chunk_topics)
                topic_overlap += overlap
        
        avg_topic_overlap = topic_overlap / len(cluster_chunks) if cluster_chunks else 0
        
        return avg_topic_overlap > 0.3  # Pelo menos 30% de sobreposição de tópicos
    
    async def _consolidate_cluster_intelligent(self, cluster_chunks: List[EnhancedChunk]) -> EnhancedChunk:
        """Consolida um cluster de forma inteligente"""
        self.logger.debug(f"Consolidando cluster com {len(cluster_chunks)} chunks")
        
        # Consolidação usando LLM se disponível
        consolidated_text = await self.llm_consolidator.intelligent_consolidation(cluster_chunks)
        
        # Criar novo embedding para o texto consolidado
        new_embedding = self.embedding_manager.get_embeddings([consolidated_text])[0]
        
        # Agregar metadados
        consolidated_metadata = self._aggregate_metadata(cluster_chunks)
        
        # Criar chunk consolidado
        consolidated_chunk = EnhancedChunk(
            id=f"consolidated_{uuid.uuid4().hex[:8]}",
            text=consolidated_text,
            embedding=new_embedding,
            metadata=consolidated_metadata
        )
        
        # Análise semântica do resultado
        consolidated_chunk = self.semantic_analyzer.analyze_chunk(consolidated_chunk)
        
        # Adicionar informações de consolidação
        consolidated_chunk.metadata.update({
            'is_consolidated': True,
            'source_chunks': [chunk.id for chunk in cluster_chunks],
            'consolidation_timestamp': time.time(),
            'consolidation_method': 'intelligent_llm' if self.config.use_llm_consolidation else 'rule_based'
        })
        
        return consolidated_chunk
    
    def _aggregate_metadata(self, chunks: List[EnhancedChunk]) -> Dict[str, Any]:
        """Agrega metadados de múltiplos chunks"""
        aggregated = {
            'source_count': len(chunks),
            'original_ids': [chunk.id for chunk in chunks],
            'creation_timestamps': [chunk.creation_timestamp for chunk in chunks],
            'languages': list(set(chunk.language for chunk in chunks)),
            'avg_quality_score': np.mean([chunk.quality_score for chunk in chunks]),
            'total_access_count': sum(chunk.access_count for chunk in chunks),
            'combined_topics': list(set().union(*[chunk.topics for chunk in chunks])),
            'entities': []
        }
        
        # Agregar entidades únicas
        all_entities = []
        for chunk in chunks:
            all_entities.extend(chunk.entities)
        
        # Deduplicar entidades por texto
        unique_entities = {}
        for entity in all_entities:
            key = (entity['text'], entity['label'])
            if key not in unique_entities:
                unique_entities[key] = entity
            else:
                # Manter a confiança mais alta
                if entity.get('confidence', 0) > unique_entities[key].get('confidence', 0):
                    unique_entities[key] = entity
        
        aggregated['entities'] = list(unique_entities.values())
        
        # Agregar sentimentos (média ponderada)
        sentiments = [chunk.sentiment for chunk in chunks if chunk.sentiment]
        if sentiments:
            scores = [s.get('score', 0) for s in sentiments]
            labels = [s.get('label', 'neutral') for s in sentiments]
            
            aggregated['sentiment'] = {
                'score': np.mean(scores),
                'label': max(set(labels), key=labels.count),  # Moda
                'confidence': np.std(scores)  # Usar std como medida de consenso
            }
        
        return aggregated
    
    async def _validate_and_optimize_results(self, consolidation_results: Dict[str, Any]):
        """Valida e otimiza os resultados da consolidação"""
        self.logger.info("Validando e otimizando resultados...")
        
        final_chunks = consolidation_results['final_chunks']
        
        # Validação de qualidade
        quality_issues = []
        for chunk in final_chunks:
            if chunk.quality_score < self.config.min_text_quality_score:
                quality_issues.append(chunk.id)
        
        if quality_issues:
            self.logger.warning(f"Chunks com baixa qualidade detectados: {len(quality_issues)}")
        
        # Detecção de duplicatas semânticas restantes
        if self.config.enable_deduplication:
            await self._final_deduplication(final_chunks)
        
        # Otimização de embeddings (re-computar se necessário)
        await self._optimize_embeddings(final_chunks)
        
        # Validação de integridade
        self._validate_chunk_integrity(final_chunks)
    
    async def _final_deduplication(self, chunks: List[EnhancedChunk]):
        """Deduplicação final baseada em múltiplos critérios"""
        self.logger.info("Executando deduplicação final...")
        
        if len(chunks) < 2:
            return
        
        # Calcular similaridades
        embeddings = np.array([chunk.embedding for chunk in chunks])
        similarities = cosine_similarity(embeddings)
        
        # Encontrar pares altamente similares
        high_similarity_pairs = []
        threshold = self.config.similarity_thresholds['high']
        
        for i in range(len(chunks)):
            for j in range(i + 1, len(chunks)):
                if similarities[i][j] > threshold:
                    high_similarity_pairs.append((i, j, similarities[i][j]))
        
        # Decidir quais chunks remover
        chunks_to_remove = set()
        
        for i, j, similarity in high_similarity_pairs:
            if i in chunks_to_remove or j in chunks_to_remove:
                continue
            
            chunk_i, chunk_j = chunks[i], chunks[j]
            
            # Critérios para decidir qual manter
            keep_i = False
            
            # 1. Preferir qualidade mais alta
            if chunk_i.quality_score != chunk_j.quality_score:
                keep_i = chunk_i.quality_score > chunk_j.quality_score
            # 2. Preferir texto mais longo (mais informativo)
            elif len(chunk_i.text) != len(chunk_j.text):
                keep_i = len(chunk_i.text) > len(chunk_j.text)
            # 3. Preferir mais acessado
            elif chunk_i.access_count != chunk_j.access_count:
                keep_i = chunk_i.access_count > chunk_j.access_count
            # 4. Preferir mais recente
            else:
                keep_i = chunk_i.creation_timestamp > chunk_j.creation_timestamp
            
            if keep_i:
                chunks_to_remove.add(j)
            else:
                chunks_to_remove.add(i)
        
        # Remover chunks duplicados
        if chunks_to_remove:
            self.logger.info(f"Removendo {len(chunks_to_remove)} chunks duplicados")
            chunks[:] = [chunk for idx, chunk in enumerate(chunks) if idx not in chunks_to_remove]
    
    async def _optimize_embeddings(self, chunks: List[EnhancedChunk]):
        """Otimiza embeddings dos chunks finais"""
        self.logger.info("Otimizando embeddings...")
        
        # Re-computar embeddings para chunks consolidados usando ensemble
        consolidated_chunks = [chunk for chunk in chunks if chunk.metadata.get('is_consolidated', False)]
        
        if consolidated_chunks:
            texts = [chunk.text for chunk in consolidated_chunks]
            new_embeddings = self.embedding_manager.get_ensemble_embeddings(texts)
            
            for chunk, new_embedding in zip(consolidated_chunks, new_embeddings):
                chunk.embedding = new_embedding
                chunk.metadata['embedding_optimized'] = True
    
    def _validate_chunk_integrity(self, chunks: List[EnhancedChunk]):
        """Valida integridade dos chunks"""
        self.logger.info("Validando integridade dos chunks...")
        
        issues = []
        
        for chunk in chunks:
            # Verificar campos obrigatórios
            if not chunk.id or not chunk.text:
                issues.append(f"Chunk {chunk.id}: campos obrigatórios ausentes")
            
            # Verificar embedding válido
            if chunk.embedding is None or len(chunk.embedding) == 0:
                issues.append(f"Chunk {chunk.id}: embedding inválido")
            
            # Verificar qualidade mínima
            if chunk.quality_score < 0 or chunk.quality_score > 1:
                issues.append(f"Chunk {chunk.id}: score de qualidade inválido")
            
            # Verificar metadados essenciais
            if not isinstance(chunk.metadata, dict):
                issues.append(f"Chunk {chunk.id}: metadados inválidos")
        
        if issues:
            self.logger.error(f"Problemas de integridade encontrados: {len(issues)}")
            for issue in issues[:10]:  # Mostrar apenas os primeiros 10
                self.logger.error(f"  - {issue}")
        else:
            self.logger.info("Validação de integridade concluída com sucesso")
    
    async def _save_consolidated_memory(self, consolidation_results: Dict[str, Any]):
        """Salva a memória consolidada"""
        self.logger.info("Salvando memória consolidada...")
        
        final_chunks = consolidation_results['final_chunks']
        
        # Criar novo índice FAISS
        if final_chunks:
            embeddings = np.array([chunk.embedding for chunk in final_chunks])
            
            # Criar índice otimizado
            dimension = embeddings.shape[1]
            
            # Usar índice IVF para melhor performance com muitos vetores
            if len(final_chunks) > 1000:
                nlist = min(100, len(final_chunks) // 10)
                quantizer = faiss.IndexFlatIP(dimension)
                index = faiss.IndexIVFFlat(quantizer, dimension, nlist)
                index.train(embeddings.astype('float32'))
            else:
                index = faiss.IndexFlatIP(dimension)
            
            index.add(embeddings.astype('float32'))
            
            # Salvar índice
            faiss.write_index(index, os.path.join(self.memory_dir, "atena_index_consolidated.faiss"))
        
        # Preparar metadados para salvamento
        metadata_to_save = {
            'chunks': [],
            'consolidation_info': {
                'timestamp': time.time(),
                'algorithm_results': consolidation_results.get('algorithm_results', {}),
                'stats': consolidation_results.get('consolidation_stats', {}),
                'config': {
                    'similarity_thresholds': self.config.similarity_thresholds,
                    'clustering_algorithms': self.config.clustering_algorithms,
                    'use_llm_consolidation': self.config.use_llm_consolidation
                }
            }
        }
        
        # Converter chunks para formato serializável
        for chunk in final_chunks:
            chunk_data = {
                'id': chunk.id,
                'text': chunk.text,
                'embedding': chunk.embedding.tolist(),
                'metadata': chunk.metadata,
                'language': chunk.language,
                'quality_score': chunk.quality_score,
                'semantic_fingerprint': chunk.semantic_fingerprint,
                'topics': chunk.topics,
                'entities': chunk.entities,
                'sentiment': chunk.sentiment,
                'readability_score': chunk.readability_score,
                'creation_timestamp': chunk.creation_timestamp,
                'last_accessed': chunk.last_accessed,
                'access_count': chunk.access_count
            }
            metadata_to_save['chunks'].append(chunk_data)
        
        # Salvar metadados
        metadata_file = os.path.join(self.memory_dir, "atena_metadata_consolidated.json")
        async with aiofiles.open(metadata_file, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(metadata_to_save, indent=2, ensure_ascii=False))
        
        # Backup da versão anterior
        original_faiss = os.path.join(self.memory_dir, "atena_index.faiss")
        original_metadata = os.path.join(self.memory_dir, "atena_metadata.json")
        
        if os.path.exists(original_faiss):
            backup_dir = os.path.join(self.memory_dir, "backup", datetime.now().strftime("%Y%m%d_%H%M%S"))
            os.makedirs(backup_dir, exist_ok=True)
            
            import shutil
            shutil.copy2(original_faiss, os.path.join(backup_dir, "atena_index.faiss"))
            shutil.copy2(original_metadata, os.path.join(backup_dir, "atena_metadata.json"))
        
        # Salvar em storage externo se configurado
        await self._save_to_external_storage(final_chunks)
        
        self.logger.info(f"Memória consolidada salva: {len(final_chunks)} chunks")
    
    async def _save_to_external_storage(self, chunks: List[EnhancedChunk]):
        """Salva em sistemas de storage externos"""
        
        # ChromaDB
        if self.chromadb_client:
            try:
                collection = self.chromadb_client.get_or_create_collection("atena_consolidated")
                
                embeddings = [chunk.embedding.tolist() for chunk in chunks]
                documents = [chunk.text for chunk in chunks]
                metadatas = [chunk.metadata for chunk in chunks]
                ids = [chunk.id for chunk in chunks]
                
                collection.add(
                    embeddings=embeddings,
                    documents=documents,  
                    metadatas=metadatas,
                    ids=ids
                )
                self.logger.info("Dados salvos no ChromaDB")
            except Exception as e:
                self.logger.error(f"Erro ao salvar no ChromaDB: {e}")
        
        # Elasticsearch  
        if self.elasticsearch_client:
            try:
                for chunk in chunks:
                    doc = {
                        'text': chunk.text,
                        'embedding': chunk.embedding.tolist(),
                        'metadata': chunk.metadata,
                        'quality_score': chunk.quality_score,
                        'topics': chunk.topics,
                        'timestamp': chunk.creation_timestamp
                    }
                    
                    await self.elasticsearch_client.index(
                        index='atena_consolidated',
                        id=chunk.id,
                        body=doc
                    )
                self.logger.info("Dados salvos no Elasticsearch")
            except Exception as e:
                self.logger.error(f"Erro ao salvar no Elasticsearch: {e}")
    
    def _generate_comprehensive_report(self, consolidation_results: Dict[str, Any], start_time: float) -> Dict[str, Any]:
        """Gera relatório abrangente da consolidação"""
        end_time = time.time()
        processing_time = end_time - start_time
        
        stats = consolidation_results.get('consolidation_stats', {})
        algorithm_results = consolidation_results.get('algorithm_results', {})
        final_chunks = consolidation_results.get('final_chunks', [])
        
        # Estatísticas detalhadas
        report = {
            'status': 'success',
            'timestamp': datetime.now().isoformat(),
            'processing_time_seconds': round(processing_time, 2),
            
            # Estatísticas principais
            'consolidation_stats': {
                'original_chunks': stats.get('original_count', 0),
                'final_chunks': len(final_chunks),
                'reduction_count': stats.get('original_count', 0) - len(final_chunks),
                'reduction_percentage': round(stats.get('reduction_ratio', 0) * 100, 2),
                'clusters_formed': stats.get('clusters_formed', 0)
            },
            
            # Resultados por algoritmo
            'algorithm_performance': {},
            
            # Análise de qualidade
            'quality_analysis': self._analyze_final_quality(final_chunks),
            
            # Estatísticas semânticas
            'semantic_stats': self._analyze_semantic_distribution(final_chunks),
            
            # Métricas de sistema
            'system_metrics': {
                'memory_usage_mb': round(psutil.Process().memory_info().rss / 1024 / 1024, 2),
                'cpu_percent': psutil.cpu_percent(),
                'chunks_per_second': round(len(final_chunks) / processing_time, 2) if processing_time > 0 else 0
            },
            
            # Configurações utilizadas
            'configuration': {
                'clustering_algorithms': self.config.clustering_algorithms,
                'similarity_thresholds': self.config.similarity_thresholds,
                'llm_consolidation_enabled': self.config.use_llm_consolidation,
                'quality_threshold': self.config.min_text_quality_score
            }
        }
        
        # Analisar performance dos algoritmos
        for algo, results in algorithm_results.items():
            if 'error' not in results:
                report['algorithm_performance'][algo] = {
                    'clusters_found': results.get('num_clusters', 0),
                    'coverage_percentage': round(results.get('coverage', 0) * 100, 2),
                    'status': 'success'
                }
            else:
                report['algorithm_performance'][algo] = {
                    'status': 'failed',
                    'error': results['error']
                }
        
        # Recomendações baseadas nos resultados
        report['recommendations'] = self._generate_recommendations(report)
        
        self.logger.info(f"Relatório gerado: {stats.get('reduction_ratio', 0)*100:.1f}% redução em {processing_time:.2f}s")
        
        return report
    
    def _analyze_final_quality(self, chunks: List[EnhancedChunk]) -> Dict[str, Any]:
        """Analisa a qualidade dos chunks finais"""
        if not chunks:
            return {}
        
        quality_scores = [chunk.quality_score for chunk in chunks]
        readability_scores = [chunk.readability_score for chunk in chunks]
        
        return {
            'average_quality_score': round(np.mean(quality_scores), 3),
            'quality_std': round(np.std(quality_scores), 3),
            'quality_distribution': {
                'high_quality': len([s for s in quality_scores if s >= 0.8]),
                'medium_quality': len([s for s in quality_scores if 0.6 <= s < 0.8]),
                'low_quality': len([s for s in quality_scores if s < 0.6])
            },
            'average_readability': round(np.mean(readability_scores), 3),
            'consolidated_chunks': len([c for c in chunks if c.metadata.get('is_consolidated', False)])
        }
    
    def _analyze_semantic_distribution(self, chunks: List[EnhancedChunk]) -> Dict[str, Any]:
        """Analisa a distribuição semântica dos chunks finais"""
        if not chunks:
            return {}
        
        # Análise de tópicos
        all_topics = []
        for chunk in chunks:
            all_topics.extend(chunk.topics)
        
        topic_counter = Counter(all_topics)
        
        # Análise de entidades
        all_entities = []
        for chunk in chunks:
            all_entities.extend([e['text'] for e in chunk.entities])
        
        entity_counter = Counter(all_entities)
        
        # Análise de sentimentos
        sentiments = [chunk.sentiment.get('label', 'neutral') for chunk in chunks if chunk.sentiment]
        sentiment_counter = Counter(sentiments)
        
        # Análise de idiomas
        languages = [chunk.language for chunk in chunks]
        language_counter = Counter(languages)
        
        return {
            'top_topics': topic_counter.most_common(10),
            'top_entities': entity_counter.most_common(10),
            'sentiment_distribution': dict(sentiment_counter),
            'language_distribution': dict(language_counter),
            'unique_topics': len(topic_counter),
            'unique_entities': len(entity_counter)
        }
    
    def _generate_recommendations(self, report: Dict[str, Any]) -> List[str]:
        """Gera recomendações baseadas nos resultados"""
        recommendations = []
        
        stats = report.get('consolidation_stats', {})
        quality = report.get('quality_analysis', {})
        
        # Recomendações baseadas na redução
        reduction_pct = stats.get('reduction_percentage', 0)
        if reduction_pct < 10:
            recommendations.append("Baixa redução detectada. Considere ajustar os thresholds de similaridade ou usar algoritmos mais agressivos.")
        elif reduction_pct > 50:
            recommendations.append("Alta redução detectada. Verifique se informações importantes não foram perdidas.")
        
        # Recomendações baseadas na qualidade
        avg_quality = quality.get('average_quality_score', 0)
        if avg_quality < 0.7:
            recommendations.append("Qualidade média baixa. Considere aumentar o threshold mínimo de qualidade.")
        
        low_quality_count = quality.get('quality_distribution', {}).get('low_quality', 0)
        if low_quality_count > 0:
            recommendations.append(f"{low_quality_count} chunks de baixa qualidade detectados. Considere revisão manual.")
        
        # Recomendações baseadas na performance
        processing_time = report.get('processing_time_seconds', 0)
        if processing_time > 300:  # 5 minutos
            recommendations.append("Tempo de processamento alto. Considere usar paralelização ou reduzir o dataset.")
        
        # Recomendações baseadas nos algoritmos
        algo_performance = report.get('algorithm_performance', {})
        failed_algos = [algo for algo, result in algo_performance.items() if result.get('status') == 'failed']
        if failed_algos:
            recommendations.append(f"Algoritmos falharam: {', '.join(failed_algos)}. Verifique dependências e configurações.")
        
        return recommendations

# Função principal para execução
async def main():
    """Função principal para executar consolidação avançada"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Sistema Avançado de Consolidação de Memória Vetorial')
    parser.add_argument('--memory-dir', required=True, help='Diretório da memória')
    parser.add_argument('--config', help='Arquivo de configuração YAML')
    parser.add_argument('--enable-llm', action='store_true', help='Habilitar consolidação com LLM')
    parser.add_argument('--algorithms', nargs='+', choices=['kmeans', 'dbscan', 'hierarchical', 'spectral'], 
                       default=['kmeans', 'dbscan'], help='Algoritmos de clustering')
    
    args = parser.parse_args()
    
    # Carregar configuração
    if args.config:
        config = ConsolidationConfig()
        if os.path.exists(args.config):
            with open(args.config, 'r') as f:
                config_data = yaml.safe_load(f)
                for key, value in config_data.items():
                    if hasattr(config, key):
                        setattr(config, key, value)
    else:
        config = ConsolidationConfig()
    
    # Aplicar argumentos da linha de comando
    config.use_llm_consolidation = args.enable_llm
    config.clustering_algorithms = args.algorithms
    
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(os.path.join(args.memory_dir, 'consolidation.log')),
            logging.StreamHandler()
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info("Iniciando consolidação avançada de memória vetorial")
    
    try:
        # Inicializar consolidador
        consolidator = AdvancedMemoryConsolidator(args.memory_dir, config)
        
        # Executar consolidação
        success = await consolidator.consolidate_memory()
        
        if success:
            logger.info("Consolidação concluída com sucesso!")
            return 0
        else:
            logger.error("Consolidação falhou!")
            return 1
            
    except Exception as e:
        logger.error(f"Erro durante a consolidação: {e}")
        return 1

# Classes auxiliares para análise semântica
class SemanticAnalyzer:
    """Analisador semântico avançado para chunks"""
    
    def __init__(self, config: AtenaConfig):
        self.config = config
        self.nlp = None
        self.sentiment_analyzer = None
        self.topic_model = None
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Inicializar componentes
        self._initialize_components()
    
    def _initialize_components(self):
        """Inicializa componentes de análise semântica"""
        try:
            # SpaCy para NER e análise linguística
            import spacy
            try:
                self.nlp = spacy.load("pt_core_news_sm")
            except OSError:
                self.logger.warning("Modelo português do spaCy não encontrado, usando inglês")
                self.nlp = spacy.load("en_core_web_sm")
            
            # Analisador de sentimentos
            from transformers import pipeline
            self.sentiment_analyzer = pipeline(
                "sentiment-analysis",
                model="neuralmind/bert-base-portuguese-cased",
                device=0 if torch.cuda.is_available() else -1
            )
            
            # Modelo de tópicos
            from bertopic import BERTopic
            from sentence_transformers import SentenceTransformer
            
            sentence_model = SentenceTransformer("neuralmind/bert-base-portuguese-cased")
            self.topic_model = BERTopic(
                embedding_model=sentence_model,
                min_topic_size=5,
                nr_topics=50
            )
            
        except Exception as e:
            self.logger.error(f"Erro ao inicializar componentes semânticos: {e}")
    
    def analyze_chunk(self, chunk: EnhancedChunk) -> EnhancedChunk:
        """Realiza análise semântica completa do chunk"""
        try:
            # Análise linguística
            doc = self.nlp(chunk.text)
            
            # Extrair entidades
            chunk.entities = [
                {
                    'text': ent.text,
                    'label': ent.label_,
                    'start': ent.start_char,
                    'end': ent.end_char,
                    'confidence': 0.9  # SpaCy não fornece score direto
                }
                for ent in doc.ents
            ]
            
            # Detectar idioma
            chunk.language = doc.lang_
            
            # Análise de sentimento
            if self.sentiment_analyzer:
                sentiment_result = self.sentiment_analyzer(chunk.text[:512])  # Limite do modelo
                chunk.sentiment = {
                    'label': sentiment_result[0]['label'],
                    'score': sentiment_result[0]['score']
                }
            
            # Calcular score de legibilidade
            chunk.readability_score = self._calculate_readability(chunk.text)
            
            # Calcular score de qualidade geral
            chunk.quality_score = self._calculate_quality_score(chunk)
            
            # Gerar fingerprint semântico
            chunk.semantic_fingerprint = self._generate_semantic_fingerprint(chunk)
            
        except Exception as e:
            self.logger.error(f"Erro na análise semântica do chunk {chunk.id}: {e}")
            chunk.quality_score = 0.5  # Score neutro em caso de erro
        
        return chunk
    
    def _calculate_readability(self, text: str) -> float:
        """Calcula score de legibilidade do texto"""
        try:
            # Métricas simples de legibilidade
            sentences = text.split('.')
            words = text.split()
            
            if not sentences or not words:
                return 0.0
            
            avg_sentence_length = len(words) / len(sentences)
            avg_word_length = sum(len(word) for word in words) / len(words)
            
            # Fórmula simplificada (adaptada do Flesch Reading Ease)
            readability = 100 - (1.015 * avg_sentence_length) - (84.6 * avg_word_length / 4.7)
            
            # Normalizar entre 0 e 1
            return max(0.0, min(1.0, readability / 100))
            
        except Exception:
            return 0.5
    
    def _calculate_quality_score(self, chunk: EnhancedChunk) -> float:
        """Calcula score de qualidade geral do chunk"""
        scores = []
        
        # Score baseado no comprimento (textos muito curtos ou longos são penalizados)
        length_score = self._score_text_length(len(chunk.text))
        scores.append(length_score)
        
        # Score baseado na legibilidade
        scores.append(chunk.readability_score)
        
        # Score baseado na presença de entidades
        entity_score = min(1.0, len(chunk.entities) / 5)  # Normalizar para até 5 entidades
        scores.append(entity_score)
        
        # Score baseado na diversidade lexical
        words = chunk.text.lower().split()
        if words:
            unique_words = set(words)
            lexical_diversity = len(unique_words) / len(words)
            scores.append(lexical_diversity)
        
        # Score baseado na estrutura (presença de pontuação, parágrafos)
        structure_score = self._score_text_structure(chunk.text)
        scores.append(structure_score)
        
        return np.mean(scores) if scores else 0.5
    
    def _score_text_length(self, length: int) -> float:
        """Score baseado no comprimento do texto"""
        if length < 50:
            return 0.3  # Muito curto
        elif length < 200:
            return 0.7  # Curto mas aceitável
        elif length < 1000:
            return 1.0  # Comprimento ideal
        elif length < 2000:
            return 0.8  # Um pouco longo
        else:
            return 0.6  # Muito longo
    
    def _score_text_structure(self, text: str) -> float:
        """Score baseado na estrutura do texto"""
        score = 0.0
        
        # Presença de pontuação
        if any(p in text for p in '.!?'):
            score += 0.3
        
        # Presença de vírgulas (estrutura de frases)
        if ',' in text:
            score += 0.2
        
        # Presença de parágrafos
        if '\n' in text:
            score += 0.2
        
        # Capitalização adequada
        sentences = text.split('.')
        capitalized_sentences = sum(1 for s in sentences if s.strip() and s.strip()[0].isupper())
        if sentences and capitalized_sentences / len(sentences) > 0.5:
            score += 0.3
        
        return min(1.0, score)
    
    def _generate_semantic_fingerprint(self, chunk: EnhancedChunk) -> str:
        """Gera fingerprint semântico único para o chunk"""
        # Combinar elementos semânticos chave
        elements = []
        
        # Entidades principais
        main_entities = sorted([e['text'].lower() for e in chunk.entities[:3]])
        elements.extend(main_entities)
        
        # Tópicos principais (se disponível)
        if hasattr(chunk, 'topics') and chunk.topics:
            elements.extend(sorted(chunk.topics[:3]))
        
        # Sentimento
        if chunk.sentiment:
            elements.append(chunk.sentiment['label'])
        
        # Comprimento normalizado
        length_bucket = "short" if len(chunk.text) < 200 else "medium" if len(chunk.text) < 1000 else "long"
        elements.append(length_bucket)
        
        # Gerar hash
        fingerprint_str = "|".join(elements)
        return hashlib.md5(fingerprint_str.encode()).hexdigest()[:16]

class ClusteringEngine:
    """Engine de clustering com múltiplos algoritmos"""
    
    def __init__(self, config: AtenaConfig):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def find_optimal_clusters(self, embeddings: np.ndarray, algorithm: str) -> List[List[int]]:
        """Encontra clusters ótimos usando o algoritmo especificado"""
        
        if algorithm == 'kmeans':
            return self._kmeans_clustering(embeddings)
        elif algorithm == 'dbscan':
            return self._dbscan_clustering(embeddings)
        elif algorithm == 'hierarchical':
            return self._hierarchical_clustering(embeddings)
        elif algorithm == 'spectral':
            return self._spectral_clustering(embeddings)
        else:
            raise ValueError(f"Algoritmo desconhecido: {algorithm}")
    
    def _kmeans_clustering(self, embeddings: np.ndarray) -> List[List[int]]:
        """Clustering K-means com número ótimo de clusters"""
        from sklearn.cluster import KMeans
        from sklearn.metrics import silhouette_score
        
        # Encontrar número ótimo de clusters
        max_k = min(20, len(embeddings) // 2)
        best_k = 2
        best_score = -1
        
        for k in range(2, max_k + 1):
            kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
            labels = kmeans.fit_predict(embeddings)
            
            if len(set(labels)) > 1:  # Mais de um cluster
                score = silhouette_score(embeddings, labels)
                if score > best_score:
                    best_score = score
                    best_k = k
        
        # Clustering final
        kmeans = KMeans(n_clusters=best_k, random_state=42, n_init=10)
        labels = kmeans.fit_predict(embeddings)
        
        # Converter para formato de clusters
        clusters = {}
        for idx, label in enumerate(labels):
            if label not in clusters:
                clusters[label] = []
            clusters[label].append(idx)
        
        return [cluster for cluster in clusters.values() if len(cluster) >= 2]
    
    def _dbscan_clustering(self, embeddings: np.ndarray) -> List[List[int]]:
        """Clustering DBSCAN"""
        from sklearn.cluster import DBSCAN
        
        # Calcular eps baseado na distância média
        distances = cosine_distances(embeddings)
        avg_distance = np.mean(distances[np.triu_indices_from(distances, k=1)])
        eps = avg_distance * 0.8  # 80% da distância média
        
        dbscan = DBSCAN(eps=eps, min_samples=2, metric='cosine')
        labels = dbscan.fit_predict(embeddings)
        
        # Converter para formato de clusters (ignorar ruído, label=-1)
        clusters = {}
        for idx, label in enumerate(labels):
            if label >= 0:  # Ignorar ruído
                if label not in clusters:
                    clusters[label] = []
                clusters[label].append(idx)
        
        return [cluster for cluster in clusters.values() if len(cluster) >= 2]
    
    def _hierarchical_clustering(self, embeddings: np.ndarray) -> List[List[int]]:
        """Clustering hierárquico"""
        from sklearn.cluster import AgglomerativeClustering
        from scipy.cluster.hierarchy import dendrogram, linkage, fcluster
        from scipy.spatial.distance import pdist
        
        # Calcular linkage
        distances = pdist(embeddings, metric='cosine')
        linkage_matrix = linkage(distances, method='ward')
        
        # Encontrar número ótimo de clusters baseado na distância
        max_d = np.mean(linkage_matrix[:, 2]) + np.std(linkage_matrix[:, 2])
        labels = fcluster(linkage_matrix, max_d, criterion='distance')
        
        # Converter para formato de clusters
        clusters = {}
        for idx, label in enumerate(labels):
            if label not in clusters:
                clusters[label] = []
            clusters[label].append(idx)
        
        return [cluster for cluster in clusters.values() if len(cluster) >= 2]
    
    def _spectral_clustering(self, embeddings: np.ndarray) -> List[List[int]]:
        """Clustering espectral"""
        from sklearn.cluster import SpectralClustering
        from sklearn.metrics import silhouette_score
        
        # Encontrar número ótimo de clusters
        max_k = min(15, len(embeddings) // 2)
        best_k = 2
        best_score = -1
        
        for k in range(2, max_k + 1):
            try:
                spectral = SpectralClustering(
                    n_clusters=k,
                    affinity='cosine',
                    random_state=42
                )
                labels = spectral.fit_predict(embeddings)
                
                if len(set(labels)) > 1:
                    score = silhouette_score(embeddings, labels)
                    if score > best_score:
                        best_score = score
                        best_k = k
            except Exception:
                continue
        
        # Clustering final
        spectral = SpectralClustering(
            n_clusters=best_k,
            affinity='cosine',
            random_state=42
        )
        labels = spectral.fit_predict(embeddings)
        
        # Converter para formato de clusters
        clusters = {}
        for idx, label in enumerate(labels):
            if label not in clusters:
                clusters[label] = []
            clusters[label].append(idx)
        
        return [cluster for cluster in clusters.values() if len(cluster) >= 2]

class LLMConsolidator:
    """Consolidador usando LLM para síntese inteligente"""
    
    def __init__(self, config: AtenaConfig):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.client = None
        
        # Inicializar cliente LLM se habilitado
        if config.use_llm_consolidation:
            self._initialize_llm_client()
    
    def _initialize_llm_client(self):
        """Inicializa cliente do LLM"""
        try:
            # Usar OpenAI API como exemplo
            import openai
            self.client = openai.OpenAI()
        except Exception as e:
            self.logger.error(f"Erro ao inicializar LLM: {e}")
            self.client = None
    
    async def intelligent_consolidation(self, chunks: List[EnhancedChunk]) -> str:
        """Consolida chunks usando LLM para síntese inteligente"""
        
        if not self.client or not self.config.use_llm_consolidation:
            return self._rule_based_consolidation(chunks)
        
        try:
            # Preparar contexto para o LLM
            context = self._prepare_llm_context(chunks)
            
            # Prompt para consolidação
            prompt = f"""
            Você é um especialista em análise e síntese de informações. Sua tarefa é consolidar os seguintes textos relacionados em uma única passagem coerente e informativa.

            INSTRUÇÕES:
            1. Mantenha TODAS as informações importantes dos textos originais
            2. Elimine redundâncias e repetições
            3. Organize as informações de forma lógica e fluida
            4. Preserve dados específicos, números, datas e nomes
            5. Mantenha o tom e estilo consistentes
            6. A síntese deve ser clara e bem estruturada

            TEXTOS PARA CONSOLIDAR:
            {context}

            TEXTO CONSOLIDADO:
            """
            
            response = await self._call_llm(prompt)
            
            if response and len(response.strip()) > 50:
                return response.strip()
            else:
                self.logger.warning("Resposta do LLM inválida, usando consolidação baseada em regras")
                return self._rule_based_consolidation(chunks)
                
        except Exception as e:
            self.logger.error(f"Erro na consolidação com LLM: {e}")
            return self._rule_based_consolidation(chunks)
    
    def _prepare_llm_context(self, chunks: List[EnhancedChunk]) -> str:
        """Prepara contexto para o LLM"""
        context_parts = []
        
        for i, chunk in enumerate(chunks, 1):
            # Incluir informações relevantes do chunk
            chunk_info = f"TEXTO {i}:\n{chunk.text}\n"
            
            # Adicionar metadados relevantes se disponíveis
            if chunk.topics:
                chunk_info += f"Tópicos: {', '.join(chunk.topics[:3])}\n"
            
            if chunk.entities:
                entities = [e['text'] for e in chunk.entities[:5]]
                chunk_info += f"Entidades: {', '.join(entities)}\n"
            
            chunk_info += "\n" + "="*50 + "\n"
            context_parts.append(chunk_info)
        
        return "\n".join(context_parts)
    
    async def _call_llm(self, prompt: str) -> str:
        """Chama o LLM com o prompt"""
        try:
            response = await self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Você é um especialista em análise e síntese de textos."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2000,
                temperature=0.3
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            self.logger.error(f"Erro na chamada do LLM: {e}")
            return ""
    
    def _rule_based_consolidation(self, chunks: List[EnhancedChunk]) -> str:
        """Consolidação baseada em regras quando LLM não está disponível"""
        
        # Ordenar chunks por qualidade
        sorted_chunks = sorted(chunks, key=lambda x: x.quality_score, reverse=True)
        
        # Começar com o chunk de maior qualidade
        consolidated_text = sorted_chunks[0].text
        
        # Adicionar informações dos outros chunks
        for chunk in sorted_chunks[1:]:
            # Verificar se há informações novas para adicionar
            if self._has_new_information(consolidated_text, chunk.text):
                # Adicionar com transição suave
                consolidated_text += f"\n\nAlém disso, {chunk.text}"
        
        return consolidated_text
    
    def _has_new_information(self, existing_text: str, new_text: str) -> bool:
        """Verifica se o novo texto tem informações não presentes no existente"""
        # Simplificação: verificar se há palavras-chave únicas
        existing_words = set(existing_text.lower().split())
        new_words = set(new_text.lower().split())
        
        unique_words = new_words - existing_words
        
        # Se há mais de 30% de palavras únicas, considera como nova informação
        return len(unique_words) / len(new_words) > 0.3 if new_words else False

if __name__ == "__main__":
    asyncio.run(main())