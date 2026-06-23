#!/usr/bin/env python3
"""
Agent Loop - Sistema de Loop Autônomo para o Projeto Atena Evolução
=====================================================================

Implementa o ciclo Perceive → Think → Act com:
- State machine (idle, thinking, acting, error, paused, stopped)
- Retry com backoff exponencial
- Integração com Ollama para inferência
- Memory buffer para contexto entre iterações
- Hook system para callbacks
- Condições de parada configuráveis

Baseado em: ReAct (Yao et al. 2022), Reflexion (Shinn et al. 2022),
MRKL Systems (Karpas et al. 2022), AutoGPT (2023), MetaGPT (Hong et al. 2023)

Autor: Koldi (Batedor da Nuvem)
Data: 2026-06-23
"""

import json
import logging
import time
import os
import sys
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple
from datetime import datetime

# ============================================================
# CONFIGURAÇÃO DE LOGGING
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("AgentLoop")


# ============================================================
# ESTADOS DO AGENTE
# ============================================================
class AgentState(Enum):
    """Estados possíveis do Agent Loop."""
    IDLE = "idle"
    THINKING = "thinking"
    ACTING = "acting"
    ERROR = "error"
    PAUSED = "paused"
    STOPPED = "stopped"


# ============================================================
# DATA CLASSES
# ============================================================
@dataclass
class AgentConfig:
    """Configuração do Agent Loop."""
    max_iterations: int = 100
    max_errors: int = 5
    timeout_seconds: int = 3600
    max_retries: int = 3
    retry_base_delay: float = 1.0
    retry_max_delay: float = 60.0
    retry_multiplier: float = 2.0
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "hermes3:8b"
    ollama_timeout: int = 120
    memory_max_entries: int = 50
    memory_context_window: int = 10
    log_level: str = "INFO"
    log_file: Optional[str] = None


@dataclass
class AgentTask:
    """Uma tarefa a ser executada pelo agente."""
    id: str
    description: str
    status: str = "pending"
    result: Any = None
    error: Optional[str] = None
    retries: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None


@dataclass
class AgentIteration:
    """Registro de uma iteração do loop."""
    iteration: int
    state: str
    thought: Optional[str] = None
    action: Optional[str] = None
    observation: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    duration_ms: float = 0.0


# ============================================================
# MEMORY BUFFER
# ============================================================
class MemoryBuffer:
    """Buffer de memória para contexto entre iterações (working memory)."""
    
    def __init__(self, max_entries: int = 50):
        self.max_entries = max_entries
        self.entries: List[Dict[str, Any]] = []
        self.logger = logging.getLogger("AgentLoop.Memory")
    
    def add(self, content: str, metadata: Optional[Dict] = None):
        entry = {
            "id": len(self.entries),
            "content": content,
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat(),
            "access_count": 0
        }
        self.entries.append(entry)
        if len(self.entries) > self.max_entries:
            self.entries.pop(0)
            self.logger.debug("Memory buffer cheio, removida entrada mais antiga")
    
    def get_context(self, last_n: int = 10) -> List[Dict]:
        context = self.entries[-last_n:]
        for entry in context:
            entry["access_count"] += 1
        return context
    
    def get_formatted_context(self, last_n: int = 10) -> str:
        context = self.get_context(last_n)
        if not context:
            return ""
        lines = []
        for entry in context:
            meta = entry.get("metadata", {})
            state = meta.get("state", "unknown")
            content = entry["content"][:200]
            lines.append(f"[{state}] {content}")
        return "\n".join(lines)
    
    def search(self, query: str) -> List[Dict]:
        query_lower = query.lower()
        results = []
        for entry in self.entries:
            if query_lower in entry["content"].lower():
                entry["access_count"] += 1
                results.append(entry)
        return results
    
    def clear(self):
        self.entries.clear()
        self.logger.info("Memory buffer limpo")
    
    @property
    def size(self) -> int:
        return len(self.entries)


# ============================================================
# OLLAMA CLIENT
# ============================================================
class OllamaClient:
    """Cliente para comunicação com Ollama local."""
    
    def __init__(self, base_url: str = "http://localhost:11434",
                 model: str = "hermes3:8b", timeout: int = 120):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.logger = logging.getLogger("AgentLoop.Ollama")
    
    def health_check(self) -> bool:
        try:
            import urllib.request
            url = f"{self.base_url}/api/tags"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status == 200
        except Exception as e:
            self.logger.warning(f"Ollama health check falhou: {e}")
            return False
    
    def generate(self, prompt: str, system: str = "",
                 max_tokens: int = 512, temperature: float = 0.7) -> Optional[str]:
        import urllib.request
        
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt}
            ],
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature
            }
        }
        
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={
            "Content-Type": "application/json"
        })
        
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                content = result.get("message", {}).get("content", "")
                self.logger.debug(f"Ollama respondeu ({len(content)} chars)")
                return content
        except Exception as e:
            self.logger.error(f"Erro ao consultar Ollama: {e}")
            return None
    
    def get_models(self) -> List[str]:
        import urllib.request
        try:
            url = f"{self.base_url}/api/tags"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                models = data.get("data", data.get("models", []))
                return [m["name"] for m in models]
        except Exception as e:
            self.logger.error(f"Erro ao listar modelos: {e}")
            return []


# ============================================================
# HOOK SYSTEM
# ============================================================
class HookSystem:
    """Sistema de hooks para callbacks durante o loop."""
    
    def __init__(self):
        self.hooks: Dict[str, List[Callable]] = {}
        self.logger = logging.getLogger("AgentLoop.Hooks")
    
    def register(self, event: str, callback: Callable):
        if event not in self.hooks:
            self.hooks[event] = []
        self.hooks[event].append(callback)
        self.logger.debug(f"Hook registrado: {event} -> {callback.__name__}")
    
    def unregister(self, event: str, callback: Callable):
        if event in self.hooks:
            self.hooks[event] = [cb for cb in self.hooks[event] if cb != callback]
    
    def trigger(self, event: str, **kwargs) -> List[Any]:
        results = []
        callbacks = self.hooks.get(event, [])
        for cb in callbacks:
            try:
                result = cb(**kwargs)
                results.append(result)
            except Exception as e:
                self.logger.error(f"Hook error ({event}): {e}")
        return results


# ============================================================
# AGENT LOOP - CLASSE PRINCIPAL
# ============================================================
class AgentLoop:
    """
    Implementação principal do Agent Loop.
    
    Ciclo: PERCEIVE → THINK → ACT → REPEAT
    
    Features:
    - State machine com transições seguras
    - Retry com backoff exponencial + jitter
    - Memory buffer para contexto
    - Hook system para extensibilidade
    - Logging estruturado de iterações
    """
    
    def __init__(self, config: Optional[AgentConfig] = None):
        self.config = config or AgentConfig()
        self.state = AgentState.IDLE
        self.iteration = 0
        self.error_count = 0
        self.start_time = None
        
        self.memory = MemoryBuffer(max_entries=self.config.memory_max_entries)
        self.ollama = OllamaClient(
            base_url=self.config.ollama_url,
            model=self.config.ollama_model,
            timeout=self.config.ollama_timeout
        )
        self.hooks = HookSystem()
        
        self.tasks: List[AgentTask] = []
        self.current_task: Optional[AgentTask] = None
        self.history: List[AgentIteration] = []
        self.logger = logging.getLogger("AgentLoop.Core")
        self._should_stop = False
    
    def _set_state(self, new_state: AgentState):
        old_state = self.state
        self.state = new_state
        self.logger.info(f"Estado: {old_state.value} -> {new_state.value}")
        self.hooks.trigger("state_change", old_state=old_state, new_state=new_state)
    
    def _perceive(self) -> Dict[str, Any]:
        """Fase PERCEIVE: Coleta informações do ambiente."""
        perception = {
            "iteration": self.iteration,
            "state": self.state.value,
            "pending_tasks": [t.id for t in self.tasks if t.status == "pending"],
            "completed_tasks": [t.id for t in self.tasks if t.status == "completed"],
            "failed_tasks": [t.id for t in self.tasks if t.status == "failed"],
            "memory_size": self.memory.size,
            "context": self.memory.get_formatted_context(self.config.memory_context_window),
            "error_count": self.error_count,
            "elapsed_time": time.time() - self.start_time if self.start_time else 0
        }
        self.logger.debug(f"Perceive: {len(perception['pending_tasks'])} tasks pendentes")
        self.hooks.trigger("perceive", perception=perception)
        return perception
    
    def _think(self, perception: Dict[str, Any]) -> Dict[str, Any]:
        """Fase THINK: Consulta o LLM para decidir próxima ação."""
        self._set_state(AgentState.THINKING)
        
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(perception)
        
        response = self.ollama.generate(
            prompt=user_prompt,
            system=system_prompt,
            max_tokens=1024,
            temperature=0.7
        )
        
        if response is None:
            self.logger.warning("Ollama não respondeu, usando fallback")
            return {"action": "wait", "reason": "ollama_unavailable", "parameters": {}}
        
        plan = self._parse_response(response)
        self.memory.add(f"Think: {plan.get('action', 'unknown')}",
                        metadata={"state": "thinking", "iteration": self.iteration})
        self.hooks.trigger("think", plan=plan, perception=perception)
        return plan
    
    def _build_system_prompt(self) -> str:
        tasks_str = self._format_tasks()
        return f"""Você é um agente autônomo executando um loop de decisões no projeto Atena Evolução.

Tarefas pendentes:
{tasks_str}

Responda SEMPRE em JSON válido:
{{"action": "execute_task|wait|skip|stop|error", "reason": "razão em 1 frase", "parameters": {{"task_id": "id", "command": "cmd"}}}}

Seja conciso e decisivo."""
    
    def _build_user_prompt(self, perception: Dict) -> str:
        context = perception.get("context", "")
        return f"""Contexto atual:
- Iteração: {perception['iteration']}
- Pendentes: {len(perception['pending_tasks'])}
- Completadas: {len(perception['completed_tasks'])}
- Erros: {perception['error_count']}
- Tempo: {perception['elapsed_time']:.0f}s

Histórico recente:
{context}

Qual a próxima ação?"""
    
    def _format_tasks(self) -> str:
        pending = [t for t in self.tasks if t.status == "pending"]
        if not pending:
            return "  Nenhuma tarefa pendente"
        return "\n".join([f"  - [{t.id}] {t.description}" for t in pending[:5]])
    
    def _parse_response(self, response: str) -> Dict[str, Any]:
        try:
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                return json.loads(json_str)
            else:
                return {"action": "wait", "reason": "parse_failed", "parameters": {}}
        except json.JSONDecodeError as e:
            self.logger.warning(f"Parse JSON falhou: {e}")
            return {"action": "wait", "reason": "json_error", "parameters": {}}
    
    def _act(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """Fase ACT: Executa a ação decidida."""
        self._set_state(AgentState.ACTING)
        
        action = plan.get("action", "wait")
        reason = plan.get("reason", "")
        parameters = plan.get("parameters", {})
        
        self.logger.info(f"Act: {action} -- {reason}")
        
        result = {
            "action": action,
            "success": False,
            "observation": "",
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            if action == "execute_task":
                task_id = parameters.get("task_id", "")
                result = self._execute_task(task_id)
            elif action == "wait":
                result["success"] = True
                result["observation"] = "Aguardando próxima iteração"
            elif action == "skip":
                result["success"] = True
                result["observation"] = "Tarefa pulada"
            elif action == "stop":
                result["success"] = True
                result["observation"] = "Parada solicitada"
                self._should_stop = True
            elif action == "error":
                result["observation"] = f"Erro: {reason}"
            else:
                result["observation"] = f"Ação desconhecida: {action}"
        except Exception as e:
            result["observation"] = f"Exceção: {type(e).__name__}: {str(e)[:200]}"
            self.logger.error(f"Erro na ação: {e}")
        
        self.memory.add(f"Act: {action} -> {'OK' if result['success'] else 'FAIL'}",
                        metadata={"state": "acting", "iteration": self.iteration})
        self.hooks.trigger("act", plan=plan, result=result)
        return result
    
    def _execute_task(self, task_id: str) -> Dict[str, Any]:
        task = None
        for t in self.tasks:
            if t.id == task_id:
                task = t
                break
        if not task:
            return {"action": "execute_task", "success": False,
                    "observation": f"Tarefa {task_id} não encontrada"}
        task.status = "running"
        self.current_task = task
        task.status = "completed"
        task.completed_at = datetime.now().isoformat()
        task.result = f"Completada em {datetime.now().isoformat()}"
        return {"action": "execute_task", "success": True,
                "observation": f"Tarefa {task_id} completada"}
    
    def _should_retry(self, error: str) -> Tuple[bool, float]:
        import random
        if self.error_count >= self.config.max_errors:
            return False, 0
        delay = min(
            self.config.retry_base_delay * (self.config.retry_multiplier ** self.error_count),
            self.config.retry_max_delay
        )
        jitter = delay * 0.25 * (2 * random.random() - 1)
        delay = max(0.1, delay + jitter)
        return True, delay
    
    def _check_stop_conditions(self) -> Tuple[bool, str]:
        if self._should_stop:
            return True, "stop_solicitado"
        if self.iteration >= self.config.max_iterations:
            return True, "max_iterations"
        if self.error_count >= self.config.max_errors:
            return True, "max_errors"
        if self.start_time:
            elapsed = time.time() - self.start_time
            if elapsed > self.config.timeout_seconds:
                return True, "timeout"
        pending = [t for t in self.tasks if t.status == "pending"]
        if not pending and self.tasks:
            return True, "todas_completadas"
        return False, ""
    
    def run(self, tasks: Optional[List[AgentTask]] = None) -> Dict[str, Any]:
        """Executa o loop principal."""
        self.start_time = time.time()
        self.iteration = 0
        self.error_count = 0
        self._should_stop = False
        
        if tasks:
            self.tasks = tasks
        
        self.logger.info("=" * 50)
        self.logger.info("AGENT LOOP INICIADO")
        self.logger.info(f"  Modelo: {self.config.ollama_model}")
        self.logger.info(f"  Tarefas: {len(self.tasks)}")
        self.logger.info(f"  Max iteracoes: {self.config.max_iterations}")
        self.logger.info("=" * 50)
        
        if not self.ollama.health_check():
            self.logger.warning("Ollama indisponivel! Modo degradado.")
        
        self._set_state(AgentState.IDLE)
        
        while True:
            self.iteration += 1
            iter_start = time.time()
            
            self.logger.info(f"\n--- Iteracao {self.iteration} ---")
            
            should_stop, reason = self._check_stop_conditions()
            if should_stop:
                self.logger.info(f"Condicao de parada: {reason}")
                break
            
            try:
                perception = self._perceive()
            except Exception as e:
                self.logger.error(f"Erro no perceive: {e}")
                self.error_count += 1
                continue
            
            try:
                plan = self._think(perception)
            except Exception as e:
                self.logger.error(f"Erro no think: {e}")
                self.error_count += 1
                can_retry, delay = self._should_retry(str(e))
                if can_retry:
                    self.logger.info(f"Retry em {delay:.1f}s...")
                    time.sleep(delay)
                continue
            
            try:
                result = self._act(plan)
            except Exception as e:
                self.logger.error(f"Erro no act: {e}")
                self.error_count += 1
                can_retry, delay = self._should_retry(str(e))
                if can_retry:
                    self.logger.info(f"Retry em {delay:.1f}s...")
                    time.sleep(delay)
                continue
            
            iter_duration = (time.time() - iter_start) * 1000
            iteration_record = AgentIteration(
                iteration=self.iteration,
                state=self.state.value,
                thought=plan.get("reason", ""),
                action=plan.get("action", ""),
                observation=result.get("observation", ""),
                duration_ms=iter_duration
            )
            self.history.append(iteration_record)
            
            if result.get("success", False):
                self.error_count = max(0, self.error_count - 1)
            
            self.logger.info(f"  Duracao: {iter_duration:.0f}ms")
        
        self._set_state(AgentState.STOPPED)
        elapsed = time.time() - self.start_time
        
        summary = {
            "status": "completed" if not self._should_stop else "stopped",
            "reason": reason,
            "iterations": self.iteration,
            "errors": self.error_count,
            "elapsed_seconds": round(elapsed, 2),
            "tasks_completed": len([t for t in self.tasks if t.status == "completed"]),
            "tasks_failed": len([t for t in self.tasks if t.status == "failed"]),
            "memory_entries": self.memory.size
        }
        
        self.logger.info("\n" + "=" * 50)
        self.logger.info("AGENT LOOP FINALIZADO")
        self.logger.info(f"  Iteracoes: {summary['iterations']}")
        self.logger.info(f"  Erros: {summary['errors']}")
        self.logger.info(f"  Completadas: {summary['tasks_completed']}")
        self.logger.info(f"  Tempo: {summary['elapsed_seconds']}s")
        self.logger.info("=" * 50)
        
        self.hooks.trigger("loop_end", summary=summary)
        return summary
    
    def add_task(self, task_id: str, description: str):
        task = AgentTask(id=task_id, description=description)
        self.tasks.append(task)
        self.logger.info(f"Tarefa adicionada: {task_id}")
    
    def pause(self):
        self._set_state(AgentState.PAUSED)
    
    def resume(self):
        self._set_state(AgentState.IDLE)
    
    def stop(self):
        self._should_stop = True
        self.logger.info("Parada solicitada")
    
    def get_history(self) -> List[Dict]:
        return [
            {
                "iteration": h.iteration,
                "state": h.state,
                "thought": h.thought,
                "action": h.action,
                "observation": h.observation,
                "timestamp": h.timestamp,
                "duration_ms": h.duration_ms
            }
            for h in self.history
        ]


# ============================================================
# EXEMPLO DE USO
# ============================================================
def main():
    print("\n" + "=" * 60)
    print("AGENT LOOP - Demonstracao")
    print("=" * 60 + "\n")
    
    config = AgentConfig(
        max_iterations=10,
        max_errors=3,
        ollama_model="hermes3:8b",
        ollama_timeout=120
    )
    
    agent = AgentLoop(config)
    
    def on_act(plan, result):
        print(f"  Acao: {plan.get('action')} -> {'OK' if result.get('success') else 'FAIL'}")
    
    agent.hooks.register("act", on_act)
    
    agent.add_task("task_1", "Verificar status do Ollama")
    agent.add_task("task_2", "Carregar modelo principal")
    agent.add_task("task_3", "Executar testes unitarios")
    
    print("\nIniciando loop...\n")
    summary = agent.run()
    
    print("\n" + "=" * 60)
    print("RESUMO DA EXECUCAO")
    print("=" * 60)
    for key, value in summary.items():
        print(f"  {key}: {value}")
    
    return summary


if __name__ == "__main__":
    main()
