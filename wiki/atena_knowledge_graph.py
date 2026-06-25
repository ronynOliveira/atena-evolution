# atena_knowledge_graph.py

import json
import os
import hashlib
import logging
from collections import defaultdict
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger("AtenaKnowledgeGraph")
KNOWLEDGE_GRAPH_FILE = "memoria_atena_v3/knowledge_graph.json"
model_emb = None # Será injetado

class KnowledgeGraph:
    """Gerencia um grafo de conhecimento para relacionar conceitos."""
    def __init__(self):
        self.graph = self._load_knowledge_graph()
        self.concept_embeddings = {}
        self._initialize_concept_embeddings()

    def _load_knowledge_graph(self) -> dict:
        if os.path.exists(KNOWLEDGE_GRAPH_FILE):
            try:
                with open(KNOWLEDGE_GRAPH_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Erro ao carregar grafo de conhecimento: {e}")
        return {'nodes': {}, 'edges': {}, 'contexts': {}, 'concept_contexts': {}}

    def _initialize_concept_embeddings(self):
        if not self.graph.get('nodes') or not model_emb: return
        try:
            concepts = [node['name'] for node in self.graph['nodes'].values()]
            if concepts:
                embeddings = model_emb.encode(concepts)
                for i, concept_id in enumerate(self.graph['nodes'].keys()):
                    self.concept_embeddings[concept_id] = embeddings[i]
        except Exception as e:
            logger.error(f"Erro ao inicializar embeddings de conceitos: {e}")
            
    def analyze_context(self, prompt: str) -> dict:
        if not model_emb or not self.graph.get('nodes'):
            return {'dominant_context': None, 'related_concepts': []}
        
        try:
            prompt_embedding = model_emb.encode([prompt])[0]
            if not self.concept_embeddings: return {'dominant_context': None, 'related_concepts': []}

            similarities = {cid: cosine_similarity([prompt_embedding], [c_emb])[0][0] for cid, c_emb in self.concept_embeddings.items()}
            top_concepts = sorted(similarities.items(), key=lambda x: x[1], reverse=True)[:5]
            
            context_scores = defaultdict(float)
            related_concepts = []
            for concept_id, similarity in top_concepts:
                if similarity > 0.3:
                    concept_name = self.graph['nodes'][concept_id]['name']
                    related_concepts.append((concept_name, similarity))
                    for context in self.graph['concept_contexts'].get(concept_id, []):
                        context_scores[context] += similarity
            
            dominant_context = max(context_scores, key=context_scores.get) if context_scores else None
            return {'dominant_context': dominant_context, 'related_concepts': related_concepts}
        except Exception as e:
            logger.error(f"Erro na análise do grafo: {e}")
            return {'dominant_context': None, 'related_concepts': []}