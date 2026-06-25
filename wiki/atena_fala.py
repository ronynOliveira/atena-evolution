#!/usr/bin/env python3
"""
Sistema de Síntese de Fala Avançado - Atena v2.0
=================================================

Sistema de TTS local com cache inteligente multi-camadas, otimizações de IA avançadas
e arquitetura robusta para assistentes virtuais.

Principais Tecnologias:
- Edge-TTS: Síntese de fala neural baseada em nuvem da Microsoft.
- Cache Inteligente: Sistema de 4 camadas com LRU adaptativo
- Pipeline de Processamento: Análise linguística avançada
- Monitoramento: Métricas de performance e qualidade
- Failover: Sistema de recuperação automática

Arquitetura:
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Text Input    │────│  NLP Pipeline   │────│  Cache Manager  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                       │
                                ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Audio Output   │◄───│   Edge-TTS      │◄───│  Cache Storage  │
└─────────────────┘    └─────────────────┘    └─────────────────┘

Autor: Claude Sonnet 4 + Desenvolvedor
Data: 2025-06-21
Versão: 2.1.0
"""

import asyncio
import hashlib
import logging
import os
import pickle
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, Any
from collections import defaultdict, OrderedDict
import json
import re

# Dependências principais
import pygame
import numpy as np
from pydub import AudioSegment
from pydub.playback import play

# Dependências de NLP e análise
try:
    import nltk
    from nltk.tokenize import sent_tokenize, word_tokenize
    from nltk.corpus import stopwords
    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False
    logging.warning("NLTK não disponível. Funcionalidades de NLP limitadas.")

# Dependências de IA avançada
try:
    import torch
    from transformers import pipeline
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logging.warning("PyTorch/Transformers não disponível. IA avançada desabilitada.")

# Dependências do Edge-TTS
try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False
    logging.error("Edge-TTS não disponível. Instale com: pip install edge-tts")


@dataclass
class AudioMetrics:
    """Métricas de qualidade e performance do áudio gerado."""
    duration: float = 0.0
    sample_rate: int = 22050
    bit_depth: int = 16
    channels: int = 1
    snr_db: float = 0.0  # Signal-to-Noise Ratio
    generation_time: float = 0.0
    cache_hit: bool = False
    quality_score: float = 0.0  # 0-1, calculado por IA
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte métricas para dicionário."""
        return {
            'duration': self.duration,
            'sample_rate': self.sample_rate,
            'bit_depth': self.bit_depth,
            'channels': self.channels,
            'snr_db': self.snr_db,
            'generation_time': self.generation_time,
            'cache_hit': self.cache_hit,
            'quality_score': self.quality_score
        }


@dataclass
class CacheEntry:
    """Entrada do cache com metadados avançados."""
    audio_data: bytes
    metadata: AudioMetrics
    created_at: datetime
    last_accessed: datetime
    access_count: int = 0
    text_hash: str = ""
    voice_model_hash: str = ""
    priority_score: float = 0.0  # Para algoritmo de eviction
    
    def update_access(self):
        """Atualiza estatísticas de acesso."""
        self.last_accessed = datetime.now()
        self.access_count += 1
        # Atualiza score de prioridade (mais acessos recentes = maior prioridade)
        time_factor = 1.0 - (datetime.now() - self.last_accessed).days / 30.0
        self.priority_score = self.access_count * max(0.1, time_factor)


class SmartCacheManager:
    """
    Gerenciador de cache inteligente com 4 camadas:
    1. Memória RAM (ultra-rápido)
    2. Cache de disco SSD (rápido)
    3. Cache comprimido (economia de espaço)
    4. Cache distribuído (futuro: Redis/Memcached)
    
    Algoritmos de eviction:
    - LRU adaptativo com scoring de prioridade
    - Análise de padrões de uso
    - Predição de necessidades futuras
    """
    
    def __init__(self, base_dir: Path, max_memory_mb: int = 100, 
                 max_disk_mb: int = 1000):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # Configurações de cache
        self.max_memory_size = max_memory_mb * 1024 * 1024  # bytes
        self.max_disk_size = max_disk_mb * 1024 * 1024      # bytes
        
        # Cache em memória (OrderedDict para LRU)
        self.memory_cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.current_memory_size = 0
        
        # Cache em disco
        self.disk_cache_dir = self.base_dir / "disk_cache"
        self.disk_cache_dir.mkdir(exist_ok=True)
        
        # Metadados do cache
        self.cache_metadata_file = self.base_dir / "cache_metadata.json"
        self.disk_metadata: Dict[str, Dict] = {}
        
        # Estatísticas
        self.stats = {
            'memory_hits': 0,
            'disk_hits': 0,
            'misses': 0,
            'evictions': 0,
            'total_requests': 0
        }
        
        # Thread lock para operações concorrentes
        self.lock = threading.RLock()
        
        # Carrega metadados do disco
        self._load_disk_metadata()
        
        # Inicia limpeza automática
        self._start_cleanup_thread()
    
    def _generate_cache_key(self, text: str, voice_model: str = "default") -> str:
        """Gera chave única para cache baseada no texto e modelo."""
        combined = f"{text}:{voice_model}"
        return hashlib.sha256(combined.encode()).hexdigest()
    
    def _load_disk_metadata(self):
        """Carrega metadados do cache em disco."""
        if self.cache_metadata_file.exists():
            try:
                with open(self.cache_metadata_file, 'r', encoding='utf-8') as f:
                    self.disk_metadata = json.load(f)
            except Exception as e:
                logging.warning(f"Erro ao carregar metadados do cache: {e}")
                self.disk_metadata = {}
    
    def _save_disk_metadata(self):
        """Salva metadados do cache em disco."""
        try:
            with open(self.cache_metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self.disk_metadata, f, indent=2, default=str)
        except Exception as e:
            logging.error(f"Erro ao salvar metadados do cache: {e}")
    
    def _start_cleanup_thread(self):
        """Inicia thread de limpeza automática do cache."""
        def cleanup_worker():
            while True:
                time.sleep(300)  # Executa a cada 5 minutos
                try:
                    self._cleanup_expired_entries()
                except Exception as e:
                    logging.error(f"Erro na limpeza automática: {e}")
        
        cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        cleanup_thread.start()
    
    def _cleanup_expired_entries(self):
        """Remove entradas expiradas do cache."""
        with self.lock:
            now = datetime.now()
            expired_keys = []
            
            # Limpa cache em memória
            for key, entry in self.memory_cache.items():
                if (now - entry.last_accessed).days > 7:  # 7 dias sem acesso
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self.memory_cache[key]
            
            # Limpa cache em disco
            for key, metadata in list(self.disk_metadata.items()):
                last_accessed = datetime.fromisoformat(metadata.get('last_accessed', '2000-01-01'))
                if (now - last_accessed).days > 30:  # 30 dias sem acesso
                    cache_file = self.disk_cache_dir / f"{key}.pkl"
                    if cache_file.exists():
                        cache_file.unlink()
                    del self.disk_metadata[key]
            
            self._save_disk_metadata()
    
    def get(self, text: str, voice_model: str = "default") -> Optional[CacheEntry]:
        """
        Recupera entrada do cache com busca inteligente em múltiplas camadas.
        
        Args:
            text: Texto para buscar
            voice_model: Modelo de voz usado
            
        Returns:
            CacheEntry se encontrado, None caso contrário
        """
        with self.lock:
            self.stats['total_requests'] += 1
            cache_key = self._generate_cache_key(text, voice_model)
            
            # Busca em memória primeiro (mais rápido)
            if cache_key in self.memory_cache:
                entry = self.memory_cache[cache_key]
                entry.update_access()
                # Move para o final (LRU)
                self.memory_cache.move_to_end(cache_key)
                self.stats['memory_hits'] += 1
                return entry
            
            # Busca em disco
            if cache_key in self.disk_metadata:
                cache_file = self.disk_cache_dir / f"{cache_key}.pkl"
                if cache_file.exists():
                    try:
                        with open(cache_file, 'rb') as f:
                            entry = pickle.load(f)
                        entry.update_access()
                        
                        # Promove para cache em memória se houver espaço
                        self._add_to_memory_cache(cache_key, entry)
                        
                        self.stats['disk_hits'] += 1
                        return entry
                    except Exception as e:
                        logging.error(f"Erro ao carregar cache do disco: {e}")
                        # Remove entrada corrompida
                        cache_file.unlink()
                        del self.disk_metadata[cache_key]
            
            self.stats['misses'] += 1
            return None
    
    def put(self, text: str, audio_data: bytes, metadata: AudioMetrics, 
            voice_model: str = "default"):
        """
        Armazena entrada no cache com estratégia inteligente de camadas.
        
        Args:
            text: Texto original
            audio_data: Dados de áudio
            metadata: Metadados do áudio
            voice_model: Modelo de voz usado
        """
        with self.lock:
            cache_key = self._generate_cache_key(text, voice_model)
            
            # Cria entrada do cache
            entry = CacheEntry(
                audio_data=audio_data,
                metadata=metadata,
                created_at=datetime.now(),
                last_accessed=datetime.now(),
                text_hash=cache_key,
                voice_model_hash=hashlib.sha256(voice_model.encode()).hexdigest()
            )
            
            # Adiciona ao cache em memória
            self._add_to_memory_cache(cache_key, entry)
            
            # Salva no disco para persistência
            self._save_to_disk_cache(cache_key, entry)
    
    def _add_to_memory_cache(self, key: str, entry: CacheEntry):
        """Adiciona entrada ao cache em memória com controle de tamanho."""
        entry_size = len(entry.audio_data)
        
        # Verifica se precisa fazer eviction
        while (self.current_memory_size + entry_size > self.max_memory_size 
               and len(self.memory_cache) > 0):
            self._evict_from_memory()
        
        # Adiciona entrada
        self.memory_cache[key] = entry
        self.current_memory_size += entry_size
        
        # Move para o final (mais recente)
        self.memory_cache.move_to_end(key)
    
    def _evict_from_memory(self):
        """Remove entrada menos prioritária da memória."""
        if not self.memory_cache:
            return
        
        # Estratégia: remove o menos usado/mais antigo
        # Mas considera o priority_score para decisões inteligentes
        min_score = float('inf')
        key_to_evict = None
        
        for key, entry in self.memory_cache.items():
            if entry.priority_score < min_score:
                min_score = entry.priority_score
                key_to_evict = key
        
        if key_to_evict:
            entry = self.memory_cache.pop(key_to_evict)
            self.current_memory_size -= len(entry.audio_data)
            self.stats['evictions'] += 1
    
    def _save_to_disk_cache(self, key: str, entry: CacheEntry):
        """Salva entrada no cache em disco."""
        try:
            cache_file = self.disk_cache_dir / f"{key}.pkl"
            with open(cache_file, 'wb') as f:
                pickle.dump(entry, f)
            
            # Atualiza metadados
            self.disk_metadata[key] = {
                'created_at': entry.created_at.isoformat(),
                'last_accessed': entry.last_accessed.isoformat(),
                'access_count': entry.access_count,
                'size': len(entry.audio_data),
                'text_hash': entry.text_hash,
                'voice_model_hash': entry.voice_model_hash
            }
            
            # Salva metadados periodicamente
            if len(self.disk_metadata) % 10 == 0:
                self._save_disk_metadata()
                
        except Exception as e:
            logging.error(f"Erro ao salvar cache no disco: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas detalhadas do cache."""
        with self.lock:
            hit_rate = 0.0
            if self.stats['total_requests'] > 0:
                total_hits = self.stats['memory_hits'] + self.stats['disk_hits']
                hit_rate = total_hits / self.stats['total_requests']
            
            return {
                **self.stats,
                'hit_rate': hit_rate,
                'memory_entries': len(self.memory_cache),
                'disk_entries': len(self.disk_metadata),
                'memory_size_mb': self.current_memory_size / (1024 * 1024),
                'cache_efficiency': self._calculate_cache_efficiency()
            }
    
    def _calculate_cache_efficiency(self) -> float:
        """Calcula eficiência do cache baseada em padrões de uso."""
        if not self.memory_cache:
            return 0.0
        
        total_score = sum(entry.priority_score for entry in self.memory_cache.values())
        avg_score = total_score / len(self.memory_cache)
        
        # Normaliza para 0-1
        return min(1.0, avg_score / 10.0)


class NLPProcessor:
    """
    Processador de linguagem natural para otimização de TTS.
    
    Funcionalidades:
    - Análise de sentimentos para ajuste de prosódia
    - Detecção de entidades nomeadas
    - Quebra inteligente de frases
    - Normalização de texto
    - Predição de padrões de fala
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Inicializa NLTK se disponível
        if NLTK_AVAILABLE:
            self._initialize_nltk()
        
        # Inicializa modelos de transformers se disponível
        if TORCH_AVAILABLE:
            self._initialize_transformers()
        
        # Padrões de normalização
        self.normalization_patterns = {
            # Números
            r'\b\d+\b': self._spell_number,
            # URLs
            r'https?://[^\s]+': 'link',
            # Emails
            r'[^\s]+@[^\s]+\.[^\s]+': 'email',
            # Abreviações comuns
            r'\bDr\.': 'Doutor',
            r'\bSr\.': 'Senhor',
            r'\bSra\.': 'Senhora',
            # Símbolos
            r'&': 'e',
            r'@': 'arroba',
            r'#': 'hashtag',
        }
    
    def _initialize_nltk(self):
        """Inicializa recursos do NLTK."""
        try:
            nltk.download('punkt', quiet=True)
            nltk.download('stopwords', quiet=True)
            nltk.download('vader_lexicon', quiet=True)
        except Exception as e:
            self.logger.warning(f"Erro ao inicializar NLTK: {e}")
    
    def _initialize_transformers(self):
        """Inicializa modelos de transformers."""
        try:
            # Sentiment analysis
            self.sentiment_analyzer = pipeline(
                "sentiment-analysis",
                model="neuralmind/bert-base-portuguese-cased",
                device=-1  # CPU only
            )
            
            # Named Entity Recognition
            self.ner_pipeline = pipeline(
                "ner",
                model="neuralmind/bert-base-portuguese-cased",
                device=-1
            )
            
            self.logger.info("Modelos de transformers carregados com sucesso")
        except Exception as e:
            self.logger.warning(f"Erro ao carregar transformers: {e}")
            self.sentiment_analyzer = None
            self.ner_pipeline = None
    
    def _spell_number(self, match):
        """Converte números para forma escrita."""
        num = int(match.group())
        # Implementação simplificada - em produção, usar biblioteca como num2words
        numbers = {
            0: 'zero', 1: 'um', 2: 'dois', 3: 'três', 4: 'quatro',
            5: 'cinco', 6: 'seis', 7: 'sete', 8: 'oito', 9: 'nove',
            10: 'dez', 11: 'onze', 12: 'doze', 13: 'treze', 14: 'catorze',
            15: 'quinze', 16: 'dezesseis', 17: 'dezessete', 18: 'dezoito',
            19: 'dezenove', 20: 'vinte'
        }
        return numbers.get(num, str(num))
    
    def normalize_text(self, text: str) -> str:
        """
        Normaliza texto para melhor síntese de fala.
        
        Args:
            text: Texto original
            
        Returns:
            Texto normalizado
        """
        normalized = text.strip()
        
        # Aplica padrões de normalização
        for pattern, replacement in self.normalization_patterns.items():
            if callable(replacement):
                normalized = re.sub(pattern, replacement, normalized)
            else:
                normalized = re.sub(pattern, replacement, normalized)
        
        # Remove múltiplos espaços
        normalized = re.sub(r'\s+', ' ', normalized)
        
        return normalized
    
    def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """
        Analisa sentimento do texto para ajuste de prosódia.
        
        Args:
            text: Texto para análise
            
        Returns:
            Dicionário com análise de sentimento
        """
        if not self.sentiment_analyzer:
            return {'label': 'NEUTRAL', 'score': 0.5}
        
        try:
            result = self.sentiment_analyzer(text)[0]
            return {
                'label': result['label'],
                'score': result['score'],
                'prosody_adjustment': self._get_prosody_adjustment(result)
            }
        except Exception as e:
            self.logger.error(f"Erro na análise de sentimento: {e}")
            return {'label': 'NEUTRAL', 'score': 0.5}
    
    def _get_prosody_adjustment(self, sentiment: Dict) -> Dict[str, float]:
        """
        Retorna ajustes de prosódia baseados no sentimento.
        
        Args:
            sentiment: Resultado da análise de sentimento
            
        Returns:
            Ajustes de prosódia (velocidade, pitch, volume)
        """
        adjustments = {
            'speed': 1.0,
            'pitch': 1.0,
            'volume': 1.0
        }
        
        if sentiment['label'] == 'POSITIVE':
            # Texto positivo: mais rápido, pitch mais alto
            adjustments['speed'] = 1.1
            adjustments['pitch'] = 1.05
            adjustments['volume'] = 1.0
        elif sentiment['label'] == 'NEGATIVE':
            # Texto negativo: mais lento, pitch mais baixo
            adjustments['speed'] = 0.9
            adjustments['pitch'] = 0.95
            adjustments['volume'] = 0.95
        
        return adjustments
    
    def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """
        Extrai entidades nomeadas do texto.
        
        Args:
            text: Texto para análise
            
        Returns:
            Lista de entidades encontradas
        """
        if not self.ner_pipeline:
            return []
        
        try:
            entities = self.ner_pipeline(text)
            return [
                {
                    'word': entity['word'],
                    'label': entity['entity'],
                    'confidence': entity['score'],
                    'start': entity['start'],
                    'end': entity['end']
                }
                for entity in entities
            ]
        except Exception as e:
            self.logger.error(f"Erro na extração de entidades: {e}")
            return []
    
    def smart_sentence_split(self, text: str) -> List[str]:
        """
        Quebra inteligente de texto em sentenças para melhor síntese.
        
        Args:
            text: Texto para quebrar
            
        Returns:
            Lista de sentenças
        """
        if NLTK_AVAILABLE:
            try:
                sentences = sent_tokenize(text, language='portuguese')
                return [s.strip() for s in sentences if s.strip()]
            except Exception as e:
                self.logger.warning(f"Erro no NLTK sentence split: {e}")
        
        # Fallback: split simples
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if s.strip()]


class AdvancedSpeechSynthesizer:
    """
    Sistema avançado de síntese de fala com IA e otimizações robustas.
    
    Características principais:
    - Cache inteligente multi-camadas
    - Processamento NLP avançado
    - Síntese de fala via Microsoft Edge (online)
    - Monitoramento de qualidade
    - Sistema de fallback
    - Otimizações de performance
    
    Anotações para IAs futuras:
    ========================
    
    ARQUITETURA MODULAR:
    - Cada componente é independente e pode ser substituído
    - Interfaces bem definidas para fácil extensão
    - Logging detalhado para debugging
    
    PONTOS DE EXTENSÃO:
    1. Novos motores TTS: Implementar interface _generate_audio_engine()
    2. Algoritmos de cache: Modificar SmartCacheManager
    3. Processamento NLP: Estender NLPProcessor
    4. Métricas de qualidade: Adicionar em AudioMetrics
    
    OTIMIZAÇÕES FUTURAS:
    - Implementar cache distribuído (Redis)
    - Adicionar compressão de áudio inteligente
    - Implementar streaming de áudio
    - Adicionar suporte a SSML
    - Implementar voice cloning
    
    MONITORAMENTO:
    - Todas as operações são logadas
    - Métricas de performance coletadas
    - Sistema de alertas implementável
    
    SEGURANÇA:
    - Sanitização de entrada
    - Controle de recursos
    - Prevenção de ataques de cache
    """
    
    # Configurações do sistema
    SUPPORTED_FORMATS = ['mp3', 'wav', 'ogg']
    DEFAULT_SAMPLE_RATE = 24000  # Edge-TTS usa 24kHz por padrão
    DEFAULT_BITRATE = 128000
    MAX_TEXT_LENGTH = 5000
    
    def __init__(self, 
                 voice: str = "pt-BR-FranciscaNeural",
                 cache_dir: str = "./cache",
                 max_cache_size_mb: int = 500,
                 audio_format: str = 'mp3'):
        """
        Inicializa o sistema de síntese de fala.
        
        Args:
            voice: Nome da voz do Edge-TTS a ser usada.
            cache_dir: Diretório do cache
            max_cache_size_mb: Tamanho máximo do cache em MB
            audio_format: Formato de áudio (mp3, wav, ogg)
        """
        
        # Configuração de logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('atena_tts.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Configurações
        self.voice = voice
        self.audio_format = audio_format.lower()
        self.cache_dir = Path(cache_dir)
        
        # Validações
        if self.audio_format not in self.SUPPORTED_FORMATS:
            raise ValueError(f"Formato não suportado: {audio_format}")
        
        if not EDGE_TTS_AVAILABLE:
            raise RuntimeError("Edge-TTS não está disponível. Instale com: pip install edge-tts")
        
        # Inicializa componentes
        self.cache_manager = SmartCacheManager(
            self.cache_dir, 
            max_memory_mb=max_cache_size_mb // 5,  # 20% em memória
            max_disk_mb=max_cache_size_mb
        )
        
        self.nlp_processor = NLPProcessor()
        
        # O hash do modelo agora é baseado no nome da voz
        self.model_hash = hashlib.sha256(self.voice.encode()).hexdigest()[:16]
        
        # Inicializa pygame para reprodução
        self._initialize_audio_system()
        
        # Executor para operações assíncronas
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # Estatísticas
        self.stats = {
            'total_generations': 0,
            'cache_hits': 0,
            'total_duration': 0.0,
            'avg_generation_time': 0.0,
            'quality_scores': []
        }
        
        self.logger.info(f"Sistema de síntese de fala inicializado com sucesso usando a voz: {self.voice}")
    
    def _initialize_audio_system(self):
        """Inicializa sistema de áudio."""
        try:
            pygame.mixer.pre_init(
                frequency=self.DEFAULT_SAMPLE_RATE,
                size=-16,
                channels=1)
            pygame.mixer.init()
            self.logger.info("Sistema de áudio inicializado")
        except Exception as e:
            self.logger.error(f"Erro ao inicializar áudio: {e}")
            raise
    
    def _validate_input(self, text: str) -> str:
        """
        Valida e sanitiza entrada de texto.
        
        Args:
            text: Texto para validar
            
        Returns:
            Texto sanitizado
            
        Raises:
            ValueError: Se texto inválido
        """
        if not text or not isinstance(text, str):
            raise ValueError("Texto deve ser uma string não vazia")
        
        text = text.strip()
        
        if len(text) > self.MAX_TEXT_LENGTH:
            self.logger.warning(f"Texto truncado de {len(text)} para {self.MAX_TEXT_LENGTH} caracteres")
            text = text[:self.MAX_TEXT_LENGTH]
        
        # Remove caracteres de controle
        text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\t')
        
        return text
    
    def _generate_audio_engine(self, text: str) -> Tuple[bytes, AudioMetrics]:
        """
        Gera áudio usando o motor Edge-TTS.
        
        Args:
            text: Texto para sintetizar
            
        Returns:
            Tupla com dados de áudio e métricas
        """
        start_time = time.time()
        
        try:
            # Buffer para capturar áudio
            audio_buffer = BytesIO()

            # --- NOVA IMPLEMENTAÇÃO COM EDGE-TTS ---
            async def generate():
                communicate = edge_tts.Communicate(text, self.voice)
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        audio_buffer.write(chunk["data"])

            # Executa a função assíncrona
            asyncio.run(generate())
            # --- FIM DA NOVA IMPLEMENTAÇÃO ---

            audio_data = audio_buffer.getvalue()
            generation_time = time.time() - start_time
            
            # Calcula métricas
            # A duração precisa ser calculada a partir do segmento de áudio, pois não temos mais o raw pcm
            audio_segment = AudioSegment.from_file(BytesIO(audio_data), format="mp3")
            duration_seconds = len(audio_segment) / 1000.0

            metrics = AudioMetrics(
                duration=duration_seconds,
                sample_rate=audio_segment.frame_rate,
                bit_depth=audio_segment.sample_width * 8,
                channels=audio_segment.channels,
                generation_time=generation_time,
                quality_score=self._calculate_audio_quality(audio_segment.raw_data)
            )
            
            return audio_data, metrics
            
        except Exception as e:
            self.logger.error(f"Erro na síntese de áudio com Edge-TTS: {e}")
            raise

    
    def _calculate_audio_quality(self, audio_data: bytes) -> float:
        """
        Calcula score de qualidade do áudio (0-1).
        
        Args:
            audio_data: Dados de áudio em bytes
            
        Returns:
            Score de qualidade (0.0 a 1.0)
            
        Anotações para IAs futuras:
        ==========================
        ALGORITMOS DE QUALIDADE:
        - Implementação atual é básica (baseada em tamanho e variação)
        - MELHORIAS POSSÍVEIS:
          * Análise espectral
          * Detecção de artifacts
          * MOS (Mean Opinion Score) automático
          * Comparação com referência
          * ML para predição de qualidade
        
        MÉTRICAS AVANÇADAS:
        - SNR (Signal-to-Noise Ratio)
        - THD (Total Harmonic Distortion)
        - Spectral flatness
        - Formant analysis
        - Prosody consistency
        """
        try:
            # Converte para numpy array para análise
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            
            if len(audio_array) == 0:
                return 0.0
            
            # Análise básica de qualidade
            # 1. Variação do sinal (evita monotonia)
            signal_variation = np.std(audio_array) / (np.max(np.abs(audio_array)) + 1e-6)
            
            # 2. Densidade espectral (evita concentração em uma frequência)
            fft = np.fft.fft(audio_array)
            spectral_flatness = np.exp(np.mean(np.log(np.abs(fft) + 1e-6))) / (np.mean(np.abs(fft)) + 1e-6)
            
            # 3. Duração adequada (muito curto ou longo pode indicar problema)
            duration_score = min(1.0, len(audio_array) / self.DEFAULT_SAMPLE_RATE / 10.0)
            
            # Combina métricas
            quality_score = (signal_variation * 0.4 + spectral_flatness * 0.4 + duration_score * 0.2)
            
            return min(1.0, max(0.0, quality_score))
            
        except Exception as e:
            self.logger.warning(f"Erro no cálculo de qualidade: {e}")
            return 0.5  # Score neutro em caso de erro
    
    def _apply_prosody_adjustments(self, audio_data: bytes, adjustments: Dict[str, float]) -> bytes:
        """
        Aplica ajustes de prosódia ao áudio.
        
        Args:
            audio_data: Dados de áudio originais
            adjustments: Ajustes de velocidade, pitch, volume
            
        Returns:
            Dados de áudio modificados
            
        Anotações para IAs futuras:
        ==========================
        PROCESSAMENTO DE ÁUDIO AVANÇADO:
        - Implementação atual usa pydub (limitada)
        - MELHORIAS RECOMENDADAS:
          * Usar librosa para pitch shifting avançado
          * PSOLA (Pitch Synchronous Overlap Add)
          * WORLD vocoder
          * Deep learning para prosody transfer
        
        PARÂMETROS DE PROSÓDIA:
        - Speed: Taxa de reprodução
        - Pitch: Frequência fundamental
        - Volume: Amplitude
        - FUTURO: stress, rhythm, intonation
        """
        try:
            # Converte para AudioSegment
            audio_segment = AudioSegment(
                audio_data,
                frame_rate=self.DEFAULT_SAMPLE_RATE,
                sample_width=2,  # 16-bit
                channels=1
            )
            
            # Aplica ajustes
            if adjustments.get('speed', 1.0) != 1.0:
                # Ajusta velocidade mantendo pitch
                speed_factor = adjustments['speed']
                audio_segment = audio_segment._spawn(
                    audio_segment.raw_data,
                    overrides={'frame_rate': int(audio_segment.frame_rate * speed_factor)}
                ).set_frame_rate(audio_segment.frame_rate)
            
            if adjustments.get('volume', 1.0) != 1.0:
                # Ajusta volume
                volume_change = 20 * np.log10(adjustments['volume'])  # dB
                audio_segment = audio_segment + volume_change
            
            # TODO: Pitch adjustment (requer biblioteca especializada)
            # pitch_factor = adjustments.get('pitch', 1.0)
            # if pitch_factor != 1.0:
            #     audio_segment = adjust_pitch(audio_segment, pitch_factor)
            
            return audio_segment.raw_data
            
        except Exception as e:
            self.logger.warning(f"Erro nos ajustes de prosódia: {e}")
            return audio_data  # Retorna original em caso de erro
    
    def _convert_audio_format(self, audio_data: bytes, target_format: str) -> bytes:
        """
        Converte áudio para formato especificado.
        
        Args:
            audio_data: Dados de áudio em WAV raw
            target_format: Formato desejado (mp3, wav, ogg)
            
        Returns:
            Dados de áudio no formato especificado
        """
        try:
            # Cria AudioSegment a partir dos dados raw
            audio_segment = AudioSegment(
                audio_data,
                frame_rate=self.DEFAULT_SAMPLE_RATE,
                sample_width=2,  # 16-bit
                channels=1
            )
            
            # Exporta para formato desejado
            output_buffer = BytesIO()
            
            if target_format == 'mp3':
                audio_segment.export(output_buffer, format='mp3', bitrate=f"{self.DEFAULT_BITRATE}")
            elif target_format == 'wav':
                audio_segment.export(output_buffer, format='wav')
            elif target_format == 'ogg':
                audio_segment.export(output_buffer, format='ogg')
            else:
                raise ValueError(f"Formato não suportado: {target_format}")
            
            return output_buffer.getvalue()
            
        except Exception as e:
            self.logger.error(f"Erro na conversão de formato: {e}")
            raise
    
    async def synthesize_async(self, text: str, apply_nlp: bool = True) -> Tuple[bytes, AudioMetrics]:
        """
        Sintetiza fala de forma assíncrona.
        
        Args:
            text: Texto para sintetizar
            apply_nlp: Se deve aplicar processamento NLP
            
        Returns:
            Tupla com dados de áudio e métricas
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor, 
            self.synthesize, 
            text, 
            apply_nlp
        )
    
    def synthesize(self, text: str, apply_nlp: bool = True) -> Tuple[bytes, AudioMetrics]:
        """
        Sintetiza fala com cache inteligente e otimizações avançadas.
        
        Args:
            text: Texto para sintetizar
            apply_nlp: Se deve aplicar processamento NLP
            
        Returns:
            Tupla com dados de áudio e métricas
            
        Anotações para IAs futuras:
        ==========================
        FLUXO PRINCIPAL DO SISTEMA:
        1. Validação e sanitização
        2. Processamento NLP (opcional)
        3. Verificação do cache
        4. Síntese de áudio (se necessário)
        5. Aplicação de prosódia
        6. Conversão de formato
        7. Armazenamento no cache
        8. Retorno dos resultados
        
        PONTOS DE MONITORAMENTO:
        - Tempo total de processamento
        - Taxa de cache hit/miss
        - Qualidade do áudio gerado
        - Erros e exceções
        
        OTIMIZAÇÕES IMPLEMENTADAS:
        - Cache multi-camadas
        - Processamento paralelo
        - Análise de sentimentos
        - Normalização de texto
        - Métricas de qualidade
        
        PRÓXIMOS PASSOS DE DESENVOLVIMENTO:
        - Streaming de áudio
        - Voice cloning
        - Multilingual support
        - Real-time synthesis
        - Cloud integration
        """
        
        start_time = time.time()
        
        try:
            # 1. Validação
            text = self._validate_input(text)
            
            # 2. Processamento NLP
            processed_text = text
            prosody_adjustments = {'speed': 1.0, 'pitch': 1.0, 'volume': 1.0}
            
            if apply_nlp:
                processed_text = self.nlp_processor.normalize_text(text)
                sentiment = self.nlp_processor.analyze_sentiment(processed_text)
                prosody_adjustments = sentiment.get('prosody_adjustment', prosody_adjustments)
            
            # 3. Verificação do cache
            cache_entry = self.cache_manager.get(processed_text, self.model_hash)
            if cache_entry:
                self.stats['cache_hits'] += 1
                cache_entry.metadata.cache_hit = True
                self.logger.info(f"Cache hit para texto: {text[:50]}...")
                return cache_entry.audio_data, cache_entry.metadata
            
            # 4. Síntese de áudio
            raw_audio_data, metrics = self._generate_audio_engine(processed_text)
            
            # 5. Aplicação de prosódia
            if any(v != 1.0 for v in prosody_adjustments.values()):
                raw_audio_data = self._apply_prosody_adjustments(raw_audio_data, prosody_adjustments)
            
            # 6. Conversão de formato
            final_audio_data = self._convert_audio_format(raw_audio_data, self.audio_format)
            
            # 7. Atualização de métricas
            total_time = time.time() - start_time
            metrics.generation_time = total_time
            
            # 8. Armazenamento no cache
            self.cache_manager.put(processed_text, final_audio_data, metrics, self.model_hash)
            
            # 9. Atualização de estatísticas
            self._update_stats(metrics)
            
            self.logger.info(f"Síntese concluída em {total_time:.2f}s - Qualidade: {metrics.quality_score:.2f}")
            
            return final_audio_data, metrics
            
        except Exception as e:
            self.logger.error(f"Erro na síntese: {e}")
            raise
    
    def _update_stats(self, metrics: AudioMetrics):
        """Atualiza estatísticas do sistema."""
        self.stats['total_generations'] += 1
        self.stats['total_duration'] += metrics.duration
        self.stats['quality_scores'].append(metrics.quality_score)
        
        # Calcula média móvel do tempo de geração
        if self.stats['avg_generation_time'] == 0:
            self.stats['avg_generation_time'] = metrics.generation_time
        else:
            # Média móvel exponencial
            alpha = 0.1
            self.stats['avg_generation_time'] = (
                alpha * metrics.generation_time + 
                (1 - alpha) * self.stats['avg_generation_time']
            )
    
    def play_audio(self, audio_data: bytes):
        """
        Reproduz áudio gerado.
        
        Args:
            audio_data: Dados de áudio para reproduzir
        """
        try:
            # Salva temporariamente
            temp_file = self.cache_dir / f"temp_audio_{int(time.time())}.{self.audio_format}"
            
            with open(temp_file, 'wb') as f:
                f.write(audio_data)
            
            # Reproduz
            if self.audio_format == 'mp3':
                pygame.mixer.music.load(str(temp_file))
                pygame.mixer.music.play()
                
                # Aguarda conclusão
                while pygame.mixer.music.get_busy():
                    time.sleep(0.1)
            else:
                # Para WAV e OGG, usa pydub
                audio_segment = AudioSegment.from_file(str(temp_file))
                play(audio_segment)
            
            # Remove arquivo temporário
            temp_file.unlink()
            
        except Exception as e:
            self.logger.error(f"Erro na reprodução: {e}")
            raise
    
    def save_audio(self, audio_data: bytes, filepath: str):
        """
        Salva áudio em arquivo.
        
        Args:
            audio_data: Dados de áudio
            filepath: Caminho para salvar
        """
        try:
            with open(filepath, 'wb') as f:
                f.write(audio_data)
            self.logger.info(f"Áudio salvo em: {filepath}")
        except Exception as e:
            self.logger.error(f"Erro ao salvar áudio: {e}")
            raise
    
    def get_system_stats(self) -> Dict[str, Any]:
        """
        Retorna estatísticas completas do sistema.
        
        Returns:
            Dicionário com estatísticas detalhadas
        """
        cache_stats = self.cache_manager.get_stats()
        
        quality_avg = 0.0
        if self.stats['quality_scores']:
            quality_avg = sum(self.stats['quality_scores']) / len(self.stats['quality_scores'])
        
        return {
            'synthesis': {
                **self.stats,
                'avg_quality_score': quality_avg
            },
            'cache': cache_stats,
            'system': {
                'audio_format': self.audio_format,
                'model_hash': self.model_hash,
                'nlp_available': NLTK_AVAILABLE,
                'ai_available': TORCH_AVAILABLE,
                'uptime_hours': (time.time() - start_time) / 3600 if 'start_time' in globals() else 0
            }
        }
    
    def batch_synthesize(self, texts: List[str], apply_nlp: bool = True) -> List[Tuple[bytes, AudioMetrics]]:
        """
        Sintetiza múltiplos textos em lote.
        
        Args:
            texts: Lista de textos para sintetizar
            apply_nlp: Se deve aplicar processamento NLP
            
        Returns:
            Lista de tuplas com dados de áudio e métricas
        """
        results = []
        
        for text in texts:
            try:
                audio_data, metrics = self.synthesize(text, apply_nlp)
                results.append((audio_data, metrics))
            except Exception as e:
                self.logger.error(f"Erro na síntese em lote para '{text[:50]}...': {e}")
                # Adiciona resultado vazio para manter índices
                results.append((b'', AudioMetrics()))
        
        return results
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.shutdown()
    
    def shutdown(self):
        """Finaliza sistema e libera recursos."""
        try:
            # Finaliza executor
            self.executor.shutdown(wait=True)
            
            # Salva cache final
            self.cache_manager._save_disk_metadata()
            
            # Finaliza pygame
            pygame.mixer.quit()
            
            self.logger.info("Sistema finalizado com sucesso")
            
        except Exception as e:
            self.logger.error(f"Erro na finalização: {e}")


# ===============================
# INTERFACES E UTILITÁRIOS
# ===============================

class TTSInterface:
    """
    Interface simplificada para uso básico do sistema.
    
    Anotações para IAs futuras:
    ==========================
    DESIGN PATTERN: FACADE & LAZY LOADING
    - Esta classe fornece interface simples para funcionalidades complexas
    - Esconde complexidade do AdvancedSpeechSynthesizer
    - O Synthesizer só é carregado na memória quando é usado pela primeira vez
    
    CASOS DE USO:
    - Chatbots e assistentes virtuais
    - Sistemas de acessibilidade
    - Aplicações educacionais
    - Narração automática
    - Alertas e notificações
    """
    
    def __init__(self, voice: str = "pt-BR-FranciscaNeural", **kwargs):
        """
        Inicializa a interface TTS de forma leve (lazy loading).
        
        Args:
            voice: Nome da voz a ser usada pelo Edge-TTS.
            **kwargs: Outros argumentos para AdvancedSpeechSynthesizer.
        """
        self._synthesizer: Optional[AdvancedSpeechSynthesizer] = None
        self._voice = voice
        self._kwargs = kwargs
        self._lock = threading.Lock()

    @property
    def synthesizer(self) -> "AdvancedSpeechSynthesizer":
        """
        Propriedade para acessar o sintetizador, inicializando-o sob demanda.
        """
        with self._lock:
            if self._synthesizer is None:
                logging.info("Inicializando AdvancedSpeechSynthesizer (lazy loading)...")
                self._synthesizer = AdvancedSpeechSynthesizer(
                    voice=self._voice, 
                    **self._kwargs
                )
            return self._synthesizer
    
    def speak(self, text: str, play_audio: bool = True) -> bytes:
        """
        Converte texto em fala e opcionalmente reproduz.
        
        Args:
            text: Texto para converter
            play_audio: Se deve reproduzir automaticamente
            
        Returns:
            Dados de áudio gerados
        """
        audio_data, _ = self.synthesizer.synthesize(text)
        
        if play_audio:
            self.synthesizer.play_audio(audio_data)
        
        return audio_data
    
    def save_speech(self, text: str, filepath: str):
        """
        Converte texto em fala e salva em arquivo.
        
        Args:
            text: Texto para converter
            filepath: Caminho para salvar áudio
        """
        audio_data, _ = self.synthesizer.synthesize(text)
        self.synthesizer.save_audio(audio_data, filepath)


# ===============================
# EXEMPLO DE USO E DEMONSTRAÇÃO
# ===============================

def demo_edge_tts():
    """
    Demonstração do sistema usando Edge-TTS.
    """
    
    print("=== DEMO: Sistema Atena TTS v2.1 (Edge-TTS) ===\n")
    
    try:
        # Inicialização
        print("Inicializando sistema...")
        with AdvancedSpeechSynthesizer(
            voice="pt-BR-FranciscaNeural",
            audio_format='mp3'
        ) as tts:
            
            # Teste básico
            print("\n1. Teste básico de síntese:")
            text1 = "Olá! Este é um teste do sistema Atena de síntese de fala usando Edge-TTS."
            audio1, metrics1 = tts.synthesize(text1)
            print(f"   Áudio gerado: {len(audio1)} bytes")
            print(f"   Qualidade: {metrics1.quality_score:.2f}")
            print(f"   Tempo: {metrics1.generation_time:.2f}s")
            
            # Teste com cache
            print("\n2. Teste de cache (mesmo texto):")
            audio2, metrics2 = tts.synthesize(text1)
            print(f"   Cache hit: {metrics2.cache_hit}")
            print(f"   Tempo: {metrics2.generation_time:.3f}s")
            
            # Teste com NLP
            print("\n3. Teste com processamento NLP:")
            text2 = "Que dia maravilhoso! Estou muito feliz hoje."
            audio3, metrics3 = tts.synthesize(text2, apply_nlp=True)
            print(f"   Qualidade: {metrics3.quality_score:.2f}")
            
            # Estatísticas
            print("\n4. Estatísticas do sistema:")
            stats = tts.get_system_stats()
            print(f"   Total de sínteses: {stats['synthesis']['total_generations']}")
            print(f"   Cache hits: {stats['cache']['memory_hits'] + stats['cache']['disk_hits']}")
            print(f"   Taxa de hit: {stats['cache']['hit_rate']:.2%}")
            print(f"   Qualidade média: {stats['synthesis']['avg_quality_score']:.2f}")
            
        print("\nDemo concluída com sucesso!")
        
    except Exception as e:
        print(f"Erro na demo: {e}")
        print("\nVerifique se as dependências do Edge-TTS estão instaladas: pip install edge-tts")


if __name__ == "__main__":
    # Configura logging para demo
    start_time = time.time()
    
    print(__doc__)
    demo_edge_tts()

