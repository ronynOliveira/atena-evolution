# soul_consolidator_v2.py
"""
Sistema Avançado de Consolidação da Personalidade e Diretrizes da Atena
Versão 2.0 - Com recursos de IA, análise de sentimentos e aprendizado adaptativo
"""

import yaml
import json
import os
import logging
import asyncio
import aiofiles
import numpy as np
from datetime import datetime, timedelta
from collections import Counter, defaultdict
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
import sqlite3
from pathlib import Path
import hashlib
import re
from textblob import TextBlob
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_similarity
import matplotlib.pyplot as plt
import seaborn as sns
from transformers import pipeline, AutoTokenizer, AutoModel
import torch
import schedule
import time
from threading import Thread
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configuração de Paths
SOUL_FILE = "atena_soul.yaml"
SOUL_DB = "atena_soul.db"
MEMORY_METADATA_FILE = "memoria_atena_v3/atena_metadata.json"
FEEDBACK_LOG_FILE = "feedback.log"
INTERACTION_LOG_FILE = "interactions.log"
ANALYTICS_DIR = "analytics"
PERSONALITY_REPORTS_DIR = "personality_reports"

# Configuração do Logger Avançado
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('soul_consolidator.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("AdvancedSoulConsolidator")

@dataclass
class PersonalityMetrics:
    """Métricas de personalidade extraídas por IA"""
    emotional_stability: float
    openness: float
    extraversion: float
    agreeableness: float
    conscientiousness: float
    creativity_index: float
    technical_affinity: float
    communication_style_score: float
    adaptability_score: float
    
@dataclass
class InteractionPattern:
    """Padrão de interação identificado"""
    pattern_type: str
    frequency: int
    success_rate: float
    context_triggers: List[str]
    optimal_response_style: str
    
@dataclass
class LearningInsight:
    """Insights de aprendizado extraídos"""
    insight_type: str
    confidence_score: float
    description: str
    actionable_changes: List[str]
    evidence_count: int

class AIEnhancedSoulConsolidator:
    def __init__(self, soul_template_path: str):
        self.soul_template_path = soul_template_path
        self.current_soul = self._load_soul()
        self.db_path = SOUL_DB
        self.sentiment_analyzer = None
        self.personality_model = None
        self.embedding_model = None
        self.vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
        self._initialize_ai_models()
        self._initialize_database()
        self._create_directories()
        
    def _initialize_ai_models(self):
        """Inicializa modelos de IA para análise"""
        try:
            # Análise de sentimentos
            self.sentiment_analyzer = pipeline(
                "sentiment-analysis",
                model="cardiffnlp/twitter-roberta-base-sentiment-latest",
                return_all_scores=True
            )
            
            # Modelo para embeddings de texto
            self.embedding_model = pipeline(
                "feature-extraction",
                model="sentence-transformers/all-MiniLM-L6-v2"
            )
            
            logger.info("Modelos de IA inicializados com sucesso")
        except Exception as e:
            logger.warning(f"Erro ao inicializar modelos de IA: {e}")
            # Fallback para modelos mais simples
            self.sentiment_analyzer = pipeline("sentiment-analysis")
    
    def _initialize_database(self):
        """Inicializa banco de dados SQLite para armazenamento estruturado"""
        with sqlite3.connect(self.db_path) as conn:
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
    
    def _create_directories(self):
        """Cria diretórios necessários"""
        for directory in [ANALYTICS_DIR, PERSONALITY_REPORTS_DIR]:
            Path(directory).mkdir(exist_ok=True)
    
    def _load_soul(self) -> dict:
        """Carrega o arquivo da alma com validação avançada"""
        if os.path.exists(SOUL_FILE):
            logger.info(f"Carregando genoma existente de {SOUL_FILE}")
            with open(SOUL_FILE, 'r', encoding='utf-8') as f:
                soul = yaml.safe_load(f)
                return self._validate_and_upgrade_soul(soul)
        elif os.path.exists(self.soul_template_path):
            logger.info(f"Genoma não encontrado. Carregando template de {self.soul_template_path}")
            with open(self.soul_template_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        else:
            logger.error("Nenhum genoma ou template encontrado. Criando um genoma avançado padrão.")
            return self._create_advanced_default_soul()
    
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
        
        tasks = [
            self._analyze_sentiment_patterns(),
            self._analyze_interaction_patterns(),
            self._extract_personality_insights(),
            self._analyze_memory_advanced(),
            self._generate_learning_insights(),
            self._update_personality_metrics(),
            self._analyze_feedback_advanced()
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Processa resultados
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Erro na tarefa {i}: {result}")
        
        await self._save_soul_async()
        await self._generate_analytics_report()
        
        logger.info("Consolidação avançada concluída com sucesso!")
    
    async def _analyze_sentiment_patterns(self):
        """Analisa padrões de sentimento nas interações"""
        if not self.sentiment_analyzer:
            return
        
        try:
            if os.path.exists(INTERACTION_LOG_FILE):
                async with aiofiles.open(INTERACTION_LOG_FILE, 'r', encoding='utf-8') as f:
                    interactions = await f.read()
                
                sentiment_scores = []
                for line in interactions.split('\n'):
                    if line.strip():
                        try:
                            interaction = json.loads(line)
                            text = interaction.get('user_input', '') + ' ' + interaction.get('ai_response', '')
                            
                            if text.strip():
                                sentiment = self.sentiment_analyzer(text[:512])  # Limite por tokens
                                if isinstance(sentiment, list) and len(sentiment) > 0:
                                    sentiment_scores.append(sentiment[0]['score'])
                        except:
                            continue
                
                if sentiment_scores:
                    avg_sentiment = np.mean(sentiment_scores)
                    sentiment_stability = 1.0 - np.std(sentiment_scores)
                    
                    self.current_soul['ai_enhanced_features']['emotional_intelligence_score'] = avg_sentiment
                    self.current_soul['personality_metrics']['emotional_stability'] = sentiment_stability
                    
                    logger.info(f"Padrões de sentimento analisados: Avg={avg_sentiment:.3f}, Stability={sentiment_stability:.3f}")
        
        except Exception as e:
            logger.error(f"Erro na análise de sentimentos: {e}")
    
    async def _analyze_interaction_patterns(self):
        """Analisa padrões de interação usando clustering"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT user_input, ai_response, context_type, sentiment_score, engagement_score
                    FROM interactions
                    WHERE timestamp > datetime('now', '-30 days')
                """)
                interactions = cursor.fetchall()
            
            if len(interactions) < 5:
                return
            
            # Prepara dados para clustering
            interaction_texts = [f"{user_input} {ai_response}" for user_input, ai_response, _, _, _ in interactions]
            
            # TF-IDF Vectorization
            tfidf_matrix = self.vectorizer.fit_transform(interaction_texts)
            
            # Clustering
            n_clusters = min(5, len(interactions) // 2)
            kmeans = KMeans(n_clusters=n_clusters, random_state=42)
            clusters = kmeans.fit_predict(tfidf_matrix)
            
            # Analisa padrões por cluster
            patterns = {}
            for i in range(n_clusters):
                cluster_interactions = [interactions[j] for j in range(len(interactions)) if clusters[j] == i]
                
                if cluster_interactions:
                    contexts = [inter[2] for inter in cluster_interactions if inter[2]]
                    avg_sentiment = np.mean([inter[3] for inter in cluster_interactions if inter[3] is not None])
                    avg_engagement = np.mean([inter[4] for inter in cluster_interactions if inter[4] is not None])
                    
                    patterns[f"pattern_{i}"] = {
                        'size': len(cluster_interactions),
                        'dominant_contexts': Counter(contexts).most_common(3),
                        'avg_sentiment': float(avg_sentiment) if not np.isnan(avg_sentiment) else 0.0,
                        'avg_engagement': float(avg_engagement) if not np.isnan(avg_engagement) else 0.0
                    }
            
            self.current_soul['interaction_patterns'] = patterns
            logger.info(f"Identificados {len(patterns)} padrões de interação")
            
        except Exception as e:
            logger.error(f"Erro na análise de padrões de interação: {e}")
    
    async def _extract_personality_insights(self):
        """Extrai insights de personalidade usando análise de texto"""
        try:
            # Coleta textos de resposta da IA
            ai_responses = []
            if os.path.exists(INTERACTION_LOG_FILE):
                async with aiofiles.open(INTERACTION_LOG_FILE, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    
                for line in content.split('\n'):
                    if line.strip():
                        try:
                            interaction = json.loads(line)
                            response = interaction.get('ai_response', '')
                            if response:
                                ai_responses.append(response)
                        except:
                            continue
            
            if not ai_responses:
                return
            
            # Análise de características linguísticas
            total_text = ' '.join(ai_responses)
            blob = TextBlob(total_text)
            
            # Métricas básicas
            avg_sentence_length = len(total_text.split()) / max(len(blob.sentences), 1)
            polarity = blob.sentiment.polarity
            subjectivity = blob.sentiment.subjectivity
            
            # Análise de vocabulário técnico
            technical_terms = self._count_technical_terms(total_text)
            technical_ratio = len(technical_terms) / max(len(total_text.split()), 1)
            
            # Atualiza métricas
            self.current_soul['personality_metrics'].update({
                'openness': min(1.0, subjectivity + 0.2),
                'conscientiousness': min(1.0, technical_ratio * 2),
                'agreeableness': max(0.0, polarity + 0.5),
                'technical_affinity': min(1.0, technical_ratio * 3),
                'communication_effectiveness': min(1.0, avg_sentence_length / 20)
            })
            
            self.current_soul['learned_preferences']['writing_style_analysis'].update({
                'avg_sentence_length': avg_sentence_length,
                'lexical_diversity': len(set(total_text.lower().split())) / max(len(total_text.split()), 1),
                'technical_vocabulary_level': technical_ratio,
                'emotional_tone_distribution': {
                    'positive': max(0, polarity),
                    'negative': max(0, -polarity),
                    'neutral': 1 - abs(polarity)
                }
            })
            
            logger.info("Insights de personalidade extraídos com sucesso")
            
        except Exception as e:
            logger.error(f"Erro na extração de insights de personalidade: {e}")
    
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
    
    async def _analyze_memory_advanced(self):
        """Análise avançada de memória com embedding similarity"""
        if not os.path.exists(MEMORY_METADATA_FILE):
            return
        
        try:
            async with aiofiles.open(MEMORY_METADATA_FILE, 'r', encoding='utf-8') as f:
                content = await f.read()
                metadata = json.loads(content)
            
            if not metadata:
                return
            
            # Análise de tópicos com clustering
            texts = []
            for item in metadata:
                text_content = item.get('content', '') or item.get('text', '')
                if text_content:
                    texts.append(text_content[:500])  # Limita tamanho
            
            if len(texts) >= 3:
                # TF-IDF para identificar tópicos
                tfidf_matrix = self.vectorizer.fit_transform(texts)
                
                # Clustering de tópicos
                n_clusters = min(5, len(texts) // 2)
                kmeans = KMeans(n_clusters=n_clusters, random_state=42)
                clusters = kmeans.fit_predict(tfidf_matrix)
                
                # Identifica tópicos principais
                topic_keywords = []
                for i in range(n_clusters):
                    cluster_center = kmeans.cluster_centers_[i]
                    top_indices = cluster_center.argsort()[-5:][::-1]
                    feature_names = self.vectorizer.get_feature_names_out()
                    cluster_keywords = [feature_names[idx] for idx in top_indices]
                    topic_keywords.append(cluster_keywords)
                
                self.current_soul['core_memories']['critical_knowledge_areas'] = topic_keywords
                
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
            
            logger.info(f"Análise avançada de memória concluída: {len(topic_keywords)} tópicos identificados")
            
        except Exception as e:
            logger.error(f"Erro na análise avançada de memória: {e}")
    
    async def _generate_learning_insights(self):
        """Gera insights de aprendizado baseados em padrões identificados"""
        insights = []
        
        try:
            # Insight sobre frequência de interação
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) as daily_interactions,
                           AVG(sentiment_score) as avg_sentiment,
                           AVG(engagement_score) as avg_engagement
                    FROM interactions
                    WHERE timestamp > datetime('now', '-7 days')
                    GROUP BY date(timestamp)
                """)
                daily_stats = cursor.fetchall()
            
            if daily_stats:
                avg_daily_interactions = np.mean([stat[0] for stat in daily_stats])
                avg_sentiment = np.mean([stat[1] for stat in daily_stats if stat[1] is not None])
                avg_engagement = np.mean([stat[2] for stat in daily_stats if stat[2] is not None])
                
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
                    })
                
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
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                for insight in insights:
                    cursor.execute("""
                        INSERT INTO learning_insights (insight_type, description, confidence_score)
                        VALUES (?, ?, ?)
                    """, (insight['type'], insight['description'], insight['confidence']))
                conn.commit()
            
            logger.info(f"Gerados {len(insights)} insights de aprendizado")
            
        except Exception as e:
            logger.error(f"Erro na geração de insights: {e}")
    
    async def _update_personality_metrics(self):
        """Atualiza métricas de personalidade baseadas em dados recentes"""
        try:
            # Calcula métricas baseadas em interações recentes
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT sentiment_score, engagement_score, context_type
                    FROM interactions
                    WHERE timestamp > datetime('now', '-7 days')
                    AND sentiment_score IS NOT NULL
                """)
                recent_interactions = cursor.fetchall()
            
            if not recent_interactions:
                return
            
            sentiments = [row[0] for row in recent_interactions if row[0] is not None]
            engagements = [row[1] for row in recent_interactions if row[1] is not None]
            contexts = [row[2] for row in recent_interactions if row[2] is not None]
            
            # Calcula métricas
            emotional_stability = 1.0 - np.std(sentiments) if sentiments else 0.0
            avg_engagement = np.mean(engagements) if engagements else 0.0
            context_diversity = len(set(contexts)) / max(len(contexts), 1) if contexts else 0.0
            
            # Atualiza métricas
            self.current_soul['personality_metrics'].update({
                'emotional_stability': min(1.0, max(0.0, emotional_stability)),
                'adaptability_score': min(1.0, max(0.0, context_diversity)),
                'communication_effectiveness': min(1.0, max(0.0, avg_engagement))
            })
            
            # Salva evolução das métricas
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO personality_evolution (personality_metrics, confidence_score, version_number)
                    VALUES (?, ?, ?)
                """, (
                    json.dumps(self.current_soul['personality_metrics']),
                    0.8,
                    self.current_soul['core_identity']['version']
                ))
                conn.commit()
            
            logger.info("Métricas de personalidade atualizadas")
            
        except Exception as e:
            logger.error(f"Erro na atualização de métricas: {e}")
    
    async def _analyze_feedback_advanced(self):
        """Análise avançada de feedback com processamento de linguagem natural"""
        if not os.path.exists(FEEDBACK_LOG_FILE):
            return
        
        try:
            feedback_data = []
            async with aiofiles.open(FEEDBACK_LOG_FILE, 'r', encoding='utf-8') as f:
                content = await f.read()
                
            for line in content.split('\n'):
                if line.strip():
                    try:
                        entry = json.loads(line)
                        feedback_data.append(entry)
                    except:
                        continue
            
            if not feedback_data:
                return
            
            # Análise de sentimento do feedback
            positive_feedback = []
            negative_feedback = []
            
            for entry in feedback_data:
                feedback_text = entry.get('feedback_text', '')
                rating = entry.get('rating', 0)
                
                if rating >= 4 or 'positivo' in entry.get('feedback', '').lower():
                    positive_feedback.append(entry)
                elif rating <= 2 or 'negativo' in entry.get('feedback', '').lower():
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
                    feedback_text = fb.get('feedback_text', '')
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
                ratings = [entry.get('rating', 3) for entry in feedback_data if entry.get('rating')]
                avg_rating = np.mean(ratings) if ratings else 3.0
                satisfaction_score = min(1.0, avg_rating / 5.0)
                
                self.current_soul['ai_enhanced_features']['emotional_intelligence_score'] = satisfaction_score
            
            logger.info(f"Análise de feedback concluída: {len(positive_feedback)} positivos, {len(negative_feedback)} negativos")
            
        except Exception as e:
            logger.error(f"Erro na análise avançada de feedback: {e}")
    
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
            if os.path.exists(SOUL_FILE):
                backup_name = f"{SOUL_FILE}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                os.rename(SOUL_FILE, backup_name)
                logger.info(f"Backup da alma anterior salvo como {backup_name}")
            
            # Atualiza metadados
            self.current_soul['core_identity']['last_consolidation'] = datetime.now().isoformat()
            self.current_soul['core_identity']['total_interactions'] += 1
            self.current_soul['core_identity']['learning_cycles_completed'] += 1
            
            # Salva nova versão
            async with aiofiles.open(SOUL_FILE, 'w', encoding='utf-8') as f:
                await f.write(yaml.dump(self.current_soul, default_flow_style=False, allow_unicode=True, sort_keys=False))
            
            logger.info(f"Genoma da Atena salvo com sucesso em {SOUL_FILE}")
            
        except Exception as e:
            logger.error(f"Erro ao salvar genoma: {e}")
    
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
            report_filename = f"{ANALYTICS_DIR}/consolidation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            async with aiofiles.open(report_filename, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(report_data, indent=2, ensure_ascii=False))
            
            # Gera visualizações se houver dados suficientes
            await self._generate_personality_charts()
            
            logger.info(f"Relatório analítico salvo em {report_filename}")
            
        except Exception as e:
            logger.error(f"Erro na geração do relatório: {e}")
    
    async def _generate_personality_charts(self):
        """Gera gráficos de evolução da personalidade"""
        try:
            # Coleta dados históricos de personalidade
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT timestamp, personality_metrics, confidence_score
                    FROM personality_evolution
                    ORDER BY timestamp
                """)
                evolution_data = cursor.fetchall()
            
            if len(evolution_data) < 2:
                return
            
            # Prepara dados para visualização
            timestamps = []
            metrics_over_time = defaultdict(list)
            
            for timestamp, metrics_json, confidence in evolution_data:
                try:
                    metrics = json.loads(metrics_json)
                    timestamps.append(datetime.fromisoformat(timestamp))
                    
                    for metric, value in metrics.items():
                        if isinstance(value, (int, float)):
                            metrics_over_time[metric].append(value)
                except:
                    continue
            
            # Cria gráfico de evolução
            plt.figure(figsize=(15, 10))
            
            # Subplot para métricas principais
            plt.subplot(2, 2, 1)
            main_metrics = ['emotional_stability', 'adaptability_score', 'communication_effectiveness']
            for metric in main_metrics:
                if metric in metrics_over_time and len(metrics_over_time[metric]) == len(timestamps):
                    plt.plot(timestamps, metrics_over_time[metric], marker='o', label=metric.replace('_', ' ').title())
            
            plt.title('Evolução das Métricas Principais de Personalidade')
            plt.xlabel('Tempo')
            plt.ylabel('Score (0-1)')
            plt.legend()
            plt.xticks(rotation=45)
            plt.grid(True, alpha=0.3)
            
            # Subplot para métricas técnicas
            plt.subplot(2, 2, 2)
            tech_metrics = ['technical_affinity', 'creativity_index', 'openness']
            for metric in tech_metrics:
                if metric in metrics_over_time and len(metrics_over_time[metric]) == len(timestamps):
                    plt.plot(timestamps, metrics_over_time[metric], marker='s', label=metric.replace('_', ' ').title())
            
            plt.title('Evolução das Métricas Técnicas')
            plt.xlabel('Tempo')
            plt.ylabel('Score (0-1)')
            plt.legend()
            plt.xticks(rotation=45)
            plt.grid(True, alpha=0.3)
            
            # Heatmap de correlações (subplot 3)
            plt.subplot(2, 2, 3)
            current_metrics = self.current_soul['personality_metrics']
            metric_values = [v for v in current_metrics.values() if isinstance(v, (int, float))]
            metric_names = [k.replace('_', ' ').title() for k, v in current_metrics.items() if isinstance(v, (int, float))]
            
            if metric_values:
                # Cria uma matriz simples para visualização
                metric_matrix = np.array(metric_values).reshape(1, -1)
                sns.heatmap(metric_matrix, xticklabels=metric_names, yticklabels=['Current'], 
                           annot=True, fmt='.2f', cmap='viridis')
                plt.title('Estado Atual das Métricas')
            
            # Gráfico de barras para insights (subplot 4)
            plt.subplot(2, 2, 4)
            insights = self.current_soul.get('learning_insights', [])
            if insights:
                insight_types = [insight.get('type', 'unknown') for insight in insights]
                insight_counts = Counter(insight_types)
                
                plt.bar(range(len(insight_counts)), list(insight_counts.values()))
                plt.xticks(range(len(insight_counts)), 
                          [t.replace('_', ' ').title() for t in insight_counts.keys()], 
                          rotation=45)
                plt.title('Distribuição de Insights de Aprendizado')
                plt.ylabel('Quantidade')
            
            plt.tight_layout()
            
            # Salva gráfico
            chart_filename = f"{PERSONALITY_REPORTS_DIR}/personality_evolution_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            plt.savefig(chart_filename, dpi=300, bbox_inches='tight')
            plt.close()
            
            logger.info(f"Gráficos de personalidade salvos em {chart_filename}")
            
        except Exception as e:
            logger.error(f"Erro na geração de gráficos: {e}")
    
    def log_interaction(self, user_input: str, ai_response: str, context_type: str = None, 
                       session_id: str = None, feedback_rating: int = None):
        """Registra interação no banco de dados"""
        try:
            # Análise de sentimento da interação
            sentiment_score = None
            engagement_score = None
            
            if self.sentiment_analyzer and user_input:
                try:
                    sentiment_result = self.sentiment_analyzer(user_input[:512])
                    if isinstance(sentiment_result, list) and len(sentiment_result) > 0:
                        sentiment_score = sentiment_result[0]['score']
                except:
                    pass
            
            # Score de engajamento baseado no comprimento e complexidade da resposta
            if ai_response:
                word_count = len(ai_response.split())
                sentence_count = len([s for s in ai_response.split('.') if s.strip()])
                engagement_score = min(1.0, (word_count / 100) * (sentence_count / 10))
            
            # Salva no banco
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
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
                f.write(json.dumps(interaction_entry, ensure_ascii=False) + '\n')
            
        except Exception as e:
            logger.error(f"Erro ao registrar interação: {e}")
    
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
        """Agenda consolidação automática"""
        def run_consolidation():
            try:
                asyncio.run(self.consolidate_async())
            except Exception as e:
                logger.error(f"Erro na consolidação automática: {e}")
        
        # Agenda a consolidação
        schedule.every(interval_hours).hours.do(run_consolidation)
        
        def scheduler_worker():
            while True:
                schedule.run_pending()
                time.sleep(60)  # Verifica a cada minuto
        
        # Executa o scheduler em thread separada
        scheduler_thread = Thread(target=scheduler_worker, daemon=True)
        scheduler_thread.start()
        
        logger.info(f"Consolidação automática agendada para cada {interval_hours} horas")

# Classe para análise de padrões comportamentais avançados
class BehavioralPatternAnalyzer:
    def __init__(self, consolidator: AIEnhancedSoulConsolidator):
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
            'avg_response_length': np.mean(response_lengths) if response_lengths else 0,
            'response_length_consistency': 1.0 - (np.std(response_lengths) / max(np.mean(response_lengths), 1)) if response_lengths else 0,
            'topic_transition_frequency': len(topic_transitions) / max(len(conversation_history), 1),
            'question_response_patterns': question_patterns,
            'conversation_engagement_score': self._calculate_engagement_score(conversation_history)
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

# Função utilitária para execução do consolidador
async def run_advanced_consolidation(soul_template_path: str = "atena_template.yaml"):
    """Executa consolidação avançada completa"""
    consolidator = AIEnhancedSoulConsolidator(soul_template_path)
    
    try:
        await consolidator.consolidate_async()
        
        # Gera resumo da personalidade
        personality_summary = consolidator.get_personality_summary()
        print("\n=== RESUMO DA PERSONALIDADE ATENA ===")
        print(f"Traços Dominantes: {', '.join(personality_summary['dominant_personality_traits'])}")
        print(f"Ciclos de Aprendizado Completados: {personality_summary['learning_cycles_completed']}")
        print(f"Nível de Inteligência Emocional: {personality_summary['emotional_intelligence_level']:.2f}")
        print(f"Padrões de Interação Identificados: {len(personality_summary['key_interaction_patterns'])}")
        print(f"Insights Recentes: {personality_summary['recent_insights_count']}")
        
        return consolidator
        
    except Exception as e:
        logger.error(f"Erro na execução da consolidação avançada: {e}")
        raise

# Exemplo de uso com análise comportamental
async def run_with_behavioral_analysis(soul_template_path: str = "atena_template.yaml"):
    """Executa consolidação com análise comportamental"""
    consolidator = AIEnhancedSoulConsolidator(soul_template_path)
    behavioral_analyzer = BehavioralPatternAnalyzer(consolidator)
    
    # Simula histórico de conversação para análise
    sample_conversation = [
        {"user_input": "Como posso melhorar meu código Python?", "ai_response": "Existem várias práticas que podem ajudar..."},
        {"user_input": "O que são design patterns?", "ai_response": "Design patterns são soluções reutilizáveis..."},
        {"user_input": "Você pode me dar um exemplo prático?", "ai_response": "Claro! Vou mostrar o padrão Singleton..."}
    ]
    
    # Análise comportamental
    flow_analysis = await behavioral_analyzer.analyze_conversation_flow(sample_conversation)
    
    # Consolidação com insights comportamentais
    await consolidator.consolidate_async()
    
    print("\n=== ANÁLISE DE PADRÕES COMPORTAMENTAIS ===")
    print(f"Comprimento Médio de Resposta: {flow_analysis.get('avg_response_length', 0):.1f} palavras")
    print(f"Consistência de Resposta: {flow_analysis.get('response_length_consistency', 0):.2f}")
    print(f"Score de Engajamento: {flow_analysis.get('conversation_engagement_score', 0):.2f}")
    
    return consolidator, behavioral_analyzer

if __name__ == "__main__":
    import sys
    
    # Permite diferentes modos de execução
    if len(sys.argv) > 1 and sys.argv[1] == "--behavioral":
        asyncio.run(run_with_behavioral_analysis())
    elif len(sys.argv) > 1 and sys.argv[1] == "--schedule":
        consolidator = asyncio.run(run_advanced_consolidation())
        consolidator.schedule_automated_consolidation(interval_hours=12)
        print("Consolidação automática agendada. Pressione Ctrl+C para interromper.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nConsolidação automática interrompida.")
    else:
        asyncio.run(run_advanced_consolidation())