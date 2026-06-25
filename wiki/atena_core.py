# nome do arquivo: atena_core.py
"""
Core do sistema Atena - Gerenciamento unificado de memória e otimização
Centraliza toda a lógica de consolidação, otimização e manutenção da memória
"""

import logging
import asyncio
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

from atena_config import AtenaConfig, settings

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - [%(module)s:%(funcName)s:%(lineno)d] - %(message)s')
logger = logging.getLogger(__name__)

# --- CLASSES DE DADOS E ENUMS ---

class OptimizationLevel(Enum):
    LIGHT = "light"
    MODERATE = "moderate"
    DEEP = "deep"

@dataclass
class MemoryMetrics:
    total_memories: int = 0
    active_memories: int = 0
    memory_size_mb: float = 0.0
    fragmentation_ratio: float = 0.0
    last_optimization: Optional[datetime] = None

# --- CLASSES ESPECIALISTAS (Departamentos) ---

class MemoryManager:
    def __init__(self, config: AtenaConfig): self.config = config
    async def cleanup_expired_memories(self):
        logger.info("Executando limpeza de memórias expiradas...")
        await asyncio.sleep(0.1)
        return {"cleaned_memories": 15}

    async def count_total_memories(self) -> int: return 1000
    async def count_active_memories(self) -> int: return 750
    async def calculate_total_size(self) -> float: return 856.7
    async def get_access_statistics(self) -> Dict: return {}

class MemoryConsolidator:
    def __init__(self, config: AtenaConfig): self.config = config
    async def consolidate_similar_memories(self):
        logger.info("Consolidando memórias similares...")
        await asyncio.sleep(0.2)
        return {"consolidated_groups": 8}
    async def remove_duplicates(self):
        logger.info("Removendo memórias duplicadas...")
        await asyncio.sleep(0.1)
        return {"duplicates_removed": 12}

class MemoryOptimizer:
    def __init__(self, config: AtenaConfig): self.config = config
    async def optimize_memory_structure(self):
        logger.info("Otimizando estrutura de memórias...")
        await asyncio.sleep(0.3)
        return {"structures_optimized": 156}
    async def reorganize_memory_hierarchy(self):
        logger.info("Reorganizando hierarquia de memórias...")
        await asyncio.sleep(0.2)
        return {"hierarchies_rebuilt": 5}
    async def update_memory_indices(self):
        logger.info("Atualizando índices de memória...")
        await asyncio.sleep(0.15)
        return {"indices_updated": 23}
    async def calculate_fragmentation(self) -> float: return 0.23

# --- CLASSE PRINCIPAL (O Cérebro / CEO) ---

class AtenaCore:
    def __init__(self, config: AtenaConfig):
        self.config = config
        self.metrics = MemoryMetrics()
        self.is_optimizing = False
        self._initialize_components()

    def _initialize_components(self):
        logger.info("Inicializando componentes do Atena Core...")
        self._memory_manager = MemoryManager(self.config)
        self._consolidator = MemoryConsolidator(self.config)
        self._optimizer = MemoryOptimizer(self.config)
        logger.info("Componentes do Atena Core inicializados com sucesso")

    async def run_memory_optimization(self, level_str: str = "moderate", force: bool = False) -> Dict[str, Any]:
        if self.is_optimizing and not force:
            return {"status": "skipped", "reason": "optimization_in_progress"}
        
        try:
            level = OptimizationLevel(level_str)
        except ValueError:
            logger.warning(f"Nível de otimização '{level_str}' inválido. Usando padrão.")
            level = OptimizationLevel(self.config.optimization_default_level)

        self.is_optimizing = True
        logger.info(f"Iniciando otimização de memória - Nível: {level.value}")
        
        try:
            initial_metrics = await self._collect_metrics()
            await self._execute_optimization(level)
            final_metrics = await self._collect_metrics()
            
            result = {
                "status": "completed",
                "improvement": self._calculate_improvement(initial_metrics, final_metrics)
            }
            self.metrics.last_optimization = datetime.now()
            logger.info(f"Otimização concluída - Melhorias: {result['improvement']}")
            return result
        except Exception as e:
            logger.error(f"Erro durante otimização: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}
        finally:
            self.is_optimizing = False

    async def _execute_optimization(self, level: OptimizationLevel):
        tasks = []
        if level in [OptimizationLevel.LIGHT, OptimizationLevel.MODERATE, OptimizationLevel.DEEP]:
            tasks.append(self._memory_manager.cleanup_expired_memories())
        if level in [OptimizationLevel.MODERATE, OptimizationLevel.DEEP]:
            tasks.append(self._consolidator.consolidate_similar_memories())
        if level == OptimizationLevel.DEEP:
            tasks.append(self._optimizer.reorganize_memory_hierarchy())
        
        await asyncio.gather(*tasks)

    async def get_system_status(self) -> Dict[str, Any]:
        return {
            "is_optimizing": self.is_optimizing,
            "last_optimization": self.metrics.last_optimization.isoformat() if self.metrics.last_optimization else None,
            "current_metrics": await self._collect_metrics()
        }

    async def schedule_optimization(self, level_str: str, delay_seconds: int = 0):
        async def delayed_optimization():
            if delay_seconds > 0:
                await asyncio.sleep(delay_seconds)
            await self.run_memory_optimization(level_str)
        
        asyncio.create_task(delayed_optimization())
        logger.info(f"Otimização {level_str} agendada para daqui a {delay_seconds}s")
    
    async def _collect_metrics(self) -> dict:
        return {
            "total_memories": await self._memory_manager.count_total_memories(),
            "active_memories": await self._memory_manager.count_active_memories(),
            "memory_size_mb": await self._memory_manager.calculate_total_size(),
            "fragmentation_ratio": await self._optimizer.calculate_fragmentation(),
        }
        
    def _calculate_improvement(self, initial: Dict, final: Dict) -> dict:
        return {
            "memory_reduced_mb": initial.get("memory_size_mb", 0) - final.get("memory_size_mb", 0),
            "memories_cleaned": initial.get("total_memories", 0) - final.get("total_memories", 0)
        }

# --- Padrão Singleton para o Core ---
_atena_core_instance = None
_atena_core_lock = threading.Lock()

def get_core(config: Optional[AtenaConfig] = None) -> AtenaCore:
    """Retorna a instância única do AtenaCore, criando se necessário."""
    global _atena_core_instance
    if _atena_core_instance is None:
        with _atena_core_lock:
            if _atena_core_instance is None:
                _atena_core_instance = AtenaCore(config or settings)
    return _atena_core_instance
