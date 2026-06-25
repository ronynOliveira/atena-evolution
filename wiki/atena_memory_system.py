#atena_memory_system

# nome do arquivo: atena_memory_system.py

import logging
import numpy as np
from datetime import datetime, timedelta
from collections import defaultdict
from typing import List, Dict, Any

from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer

# Supondo que a dataclass EnhancedChunk esteja definida no atena_core para acesso global
# Se não, ela precisaria ser definida aqui ou em um arquivo de tipos comum.
# from atena_core import EnhancedChunk 

logger = logging.getLogger("AtenaMemorySystem")

# Esta é uma dependência que precisa ser injetada, assim como o modelo de embedding
# Para este exemplo, vamos assumir que está disponível globalmente após a inicialização.
semantic_analyzer = None

class MemoryQualityAnalyzer:
    """Analisa e avalia a qualidade das memórias para otimização."""
    def evaluate_memory_quality(self, memory: Dict[str, Any]) -> float:
        """Avalia a qualidade de uma memória."""
        try:
            scores = {}
            access_count = memory.get('metadata', {}).get('access_count', 0)
            scores['relevance'] = min(access_count / 10.0, 1.0)
            
            uniqueness = memory.get('metadata', {}).get('uniqueness_score', 0.5)
            scores['uniqueness'] = uniqueness
            
            content_length = len(memory.get('content', ''))
            scores['completeness'] = min(content_length / 500.0, 1.0)
            
            last_access = memory.get('metadata', {}).get('last_access_time')
            recency = 0.5
            if last_access:
                try:
                    days_ago = (datetime.now() - datetime.fromisoformat(last_access)).days
                    recency = max(0, 1 - (days_ago / 30.0))
                except (ValueError, TypeError): pass
            scores['recency'] = recency
            
            total_score = sum(scores.values()) / len(scores)
            return total_score
        except Exception as e:
            logger.error(f"Erro ao avaliar qualidade da memória: {e}")
            return 0.5

class IntelligentMemoryManager:
    """Gerenciador inteligente de memória com otimização e consolidação autônoma."""
    def __init__(self, all_memories: List[Dict], all_embeddings: np.ndarray, model_instance: SentenceTransformer):
        self.all_memories = all_memories
        self.all_embeddings = all_embeddings
        self.model_emb = model_instance
        self.quality_analyzer = MemoryQualityAnalyzer()
        self.memory_clusters = {}
    
    def get_optimized_memory(self) -> (List[Dict], np.ndarray):
        """Executa o pipeline completo de otimização e retorna a memória resultante."""
        logger.info("Iniciando otimização inteligente de memória...")
        
        memories_to_keep, embeddings_to_keep = self._prune_low_quality_memories()
        if not memories_to_keep or len(memories_to_keep) < 2:
            logger.warning("Não há memórias suficientes para clustering após poda.")
            return memories_to_keep, embeddings_to_keep

        clusters = self._cluster_similar_memories(embeddings_to_keep)
        
        final_memories, final_embeddings = self._consolidate_clusters(memories_to_keep, embeddings_to_keep, clusters)
        
        logger.info(f"Otimização concluída. De {len(self.all_memories)} para {len(final_memories)} memórias.")
        return final_memories, final_embeddings

    def _prune_low_quality_memories(self) -> (List[Dict], np.ndarray):
        """Remove memórias de baixa qualidade ou muito antigas e não utilizadas."""
        if not self.all_memories:
            return [], np.array([])
            
        scored_memories = []
        for i, memory in enumerate(self.all_memories):
            score = self.quality_analyzer.evaluate_memory_quality(memory)
            scored_memories.append({'index': i, 'score': score, 'memory': memory})
            
        # Define um limiar de corte de qualidade
        quality_threshold = 0.2
        
        # Mantém apenas memórias acima do limiar
        high_quality_memories = [m for m in scored_memories if m['score'] >= quality_threshold]
        
        indices_to_keep = [m['index'] for m in high_quality_memories]
        
        memories_to_keep = [self.all_memories[i] for i in indices_to_keep]
        embeddings_to_keep = self.all_embeddings[indices_to_keep]
        
        logger.info(f"{len(self.all_memories) - len(memories_to_keep)} memórias de baixa qualidade podadas.")
        return memories_to_keep, embeddings_to_keep
        
    def _cluster_similar_memories(self, embeddings: np.ndarray) -> Dict[int, List[int]]:
        """Agrupa memórias similares para otimização usando KMeans."""
        if len(embeddings) < 10:
            return {}
            
        num_clusters = min(len(embeddings) // 5, 50) # Heurística para definir o número de clusters
        if num_clusters < 2: return {}
        
        kmeans = KMeans(n_clusters=num_clusters, random_state=42, n_init='auto')
        labels = kmeans.fit_predict(embeddings)
        
        clusters = defaultdict(list)
        for i, label in enumerate(labels):
            clusters[label].append(i)
            
        # Filtra clusters que são muito pequenos para serem consolidados
        return {k: v for k, v in clusters.items() if len(v) > 1}

    def _consolidate_clusters(self, memories: List[Dict], embeddings: np.ndarray, clusters: Dict[int, List[int]]) -> (List[Dict], np.ndarray):
        """Consolida os clusters, substituindo múltiplos chunks por um só."""
        indices_to_remove = set()
        new_memories = []
        
        for cluster_id, indices in clusters.items():
            # Seleciona o chunk de maior qualidade como representante
            cluster_memories = [memories[i] for i in indices]
            best_chunk = max(cluster_memories, key=lambda m: m.get('metadata', {}).get('quality_score', 0))
            
            # Cria um novo conteúdo consolidado (lógica de resumo pode ser aprimorada)
            all_content = " ".join([m['content'] for m in cluster_memories])
            consolidated_content = f"[CONSOLIDADO] {best_chunk['content']}" # Simplificação
            
            # Atualiza o chunk representante com o conteúdo consolidado
            best_chunk['content'] = consolidated_content
            best_chunk['metadata']['is_consolidated'] = True
            best_chunk['metadata']['source_chunks'] = [m['id'] for m in cluster_memories]
            
            # Recalcula o embedding para o novo conteúdo
            new_embedding = self.model_emb.encode([consolidated_content])[0]
            
            # Adiciona o novo chunk consolidado à lista de novas memórias
            new_memories.append({'memory': best_chunk, 'embedding': new_embedding})
            
            # Marca os chunks originais do cluster para remoção
            indices_to_remove.update(indices)

        # Constrói a lista final de memórias e embeddings
        final_memories = []
        final_embeddings = []
        
        # Adiciona os chunks não clusterizados
        for i in range(len(memories)):
            if i not in indices_to_remove:
                final_memories.append(memories[i])
                final_embeddings.append(embeddings[i])
                
        # Adiciona os novos chunks consolidados
        for item in new_memories:
            final_memories.append(item['memory'])
            final_embeddings.append(item['embedding'])
            
        return final_memories, np.array(final_embeddings) if final_embeddings else np.array([])


















