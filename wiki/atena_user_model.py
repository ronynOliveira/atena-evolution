# atena_user_model

import json
import os
import re
import logging
import numpy as np
from datetime import datetime
from collections import defaultdict
from sklearn.metrics.pairwise import cosine_similarity
from pathlib import Path
from typing import Dict

logger = logging.getLogger("AtenaUserModel")

# Define o caminho para a pasta de memória do usuário de forma robusta
MEMORIA_DIR = Path('./memoria_do_usuario')
MEMORIA_DIR.mkdir(exist_ok=True) # Garante que a pasta exista
USER_BEHAVIOR_FILE = MEMORIA_DIR / "perfil_comportamental.json"
model_emb = None # Será injetado pelo atena_core

class UserBehaviorTracker:
    """Rastreia e analisa padrões de comportamento do usuário"""
    def __init__(self):
        self.behavior_data = self._load_behavior_data()
        self.session_data = {'requests': [], 'contexts': [], 'timestamps': [], 'satisfaction_scores': []}
    
    def _load_behavior_data(self) -> Dict:
        if os.path.exists(USER_BEHAVIOR_FILE):
            try:
                with open(USER_BEHAVIOR_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Erro ao carregar dados de comportamento: {e}")
        return {'context_preferences': {}, 'time_patterns': {}, 'topic_interests': {}}

    def analyze_request(self, prompt: str, history: list = None) -> dict:
        current_time = datetime.now()
        return {
            'time_pattern': self._analyze_time_pattern(current_time),
            'topic_analysis': self._analyze_topic_progression(prompt, history or []),
            'preferred_context': self._determine_preferred_context(),
        }

    def _analyze_time_pattern(self, current_time: datetime) -> dict:
        hour = current_time.hour
        period = "morning" if 5 <= hour < 12 else "afternoon" if 12 <= hour < 18 else "evening"
        return {'period': period, 'hour': hour, 'day_of_week': current_time.weekday()}

    def _analyze_topic_progression(self, prompt: str, history: list) -> dict:
        if not history:
            return {'topic_shift': 'new_conversation', 'coherence': 1.0}
        
        try:
            if self.sentence_transformer:
                recent_prompts = history[-3:] + [prompt]
                embeddings = self.sentence_transformer.encode(recent_prompts)
                sim = cosine_similarity([embeddings[-2]], [embeddings[-1]])[0][0]
                return {'coherence': float(sim), 'conversation_depth': len(history)}
        except Exception as e:
            logger.error(f"Erro na análise de progressão de tópicos: {e}")
        return {'topic_shift': 'unknown', 'coherence': 0.5}

    def _determine_preferred_context(self) -> str:
        prefs = self.behavior_data.get('context_preferences', {})
        if not prefs: return "geral"
        return max(prefs, key=prefs.get)

    def update_behavior(self, prompt: str, analysis: dict):
        context = analysis.get('context_type', 'geral')
        prefs = self.behavior_data.setdefault('context_preferences', {})
        prefs[context] = prefs.get(context, 0) + 1
        self._update_topic_interests(prompt)
        if len(self.session_data['requests']) % 5 == 0: self._save_behavior_data()

    def _update_topic_interests(self, prompt: str):
        words = re.findall(r'\b\w{4,}\b', prompt.lower()) # Palavras com 4+ letras
        interests = self.behavior_data.setdefault('topic_interests', {})
        for word in words: interests[word] = interests.get(word, 0) + 0.1

    def _save_behavior_data(self):
        try:
            with open(USER_BEHAVIOR_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.behavior_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Erro ao salvar dados de comportamento: {e}")