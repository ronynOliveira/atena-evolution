import logging
import time
import asyncio
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum
from protocols import BrowserAdapterProtocol
from intelligence import AtenaIntelligenceClient

logger = logging.getLogger(__name__)

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class TaskResult:
    success: bool
    duration_seconds: float
    steps_executed: int
    error: Optional[str] = None
    screenshots: Optional[List[bytes]] = None
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class ExecutionStep:
    action: str
    params: Dict[str, Any]
    description: str
    retry_count: int = 0
    max_retries: int = 3
    timeout: float = 30.0
    screenshot_after: bool = False

class AtenaRPAAgent:
    """
    Agente RPA avançado com recursos de recuperação, monitoramento e execução robusta.
    """
    
    def __init__(self, 
                 adapter: BrowserAdapterProtocol, 
                 intelligence_client: AtenaIntelligenceClient,
                 max_concurrent_tasks: int = 1,
                 global_timeout: float = 300.0,
                 screenshot_on_error: bool = True):
        self.adapter = adapter
        self.intelligence_client = intelligence_client
        self.max_concurrent_tasks = max_concurrent_tasks
        self.global_timeout = global_timeout
        self.screenshot_on_error = screenshot_on_error
        
        # Estado interno
        self.running_tasks = 0
        self.task_queue = asyncio.Queue()
        self.status = TaskStatus.PENDING
        self.current_task_id = None
        self.execution_metadata = {}
        
        # Callbacks para monitoramento
        self.on_step_start: Optional[Callable] = None
        self.on_step_complete: Optional[Callable] = None
        self.on_task_progress: Optional[Callable] = None

    async def execute_task(self, 
                          task_description: str, 
                          task_id: Optional[str] = None,
                          custom_steps: Optional[List[ExecutionStep]] = None,
                          context: Optional[Dict[str, Any]] = None) -> TaskResult:
        """
        Executa uma tarefa com recursos avançados de monitoramento e recuperação.
        """
        if self.running_tasks >= self.max_concurrent_tasks:
            raise RuntimeError(f"Limite de tarefas concorrentes atingido: {self.max_concurrent_tasks}")

        task_id = task_id or f"task_{int(time.time())}"
        self.current_task_id = task_id
        self.running_tasks += 1
        self.status = TaskStatus.RUNNING
        
        start_time = time.time()
        screenshots = []
        executed_steps = 0
        
        logger.info(f"Iniciando tarefa {task_id}", 
                   task_description=task_description, 
                   context=context)
        
        try:
            # Timeout global para a tarefa
            return await asyncio.wait_for(
                self._execute_task_internal(task_description, custom_steps, context, screenshots),
                timeout=self.global_timeout
            )
            
        except asyncio.TimeoutError:
            error_msg = f"Tarefa {task_id} excedeu o tempo limite de {self.global_timeout}s"
            logger.error(error_msg)
            return TaskResult(
                success=False,
                duration_seconds=time.time() - start_time,
                steps_executed=executed_steps,
                error=error_msg,
                screenshots=screenshots if self.screenshot_on_error else None
            )
            
        except Exception as e:
            error_msg = f"Erro crítico na tarefa {task_id}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            # Screenshot de erro se habilitado
            if self.screenshot_on_error:
                try:
                    error_screenshot = await self.adapter.screenshot()
                    screenshots.append(error_screenshot)
                except Exception as screenshot_error:
                    logger.warning(f"Falha ao capturar screenshot de erro: {screenshot_error}")
            
            return TaskResult(
                success=False,
                duration_seconds=time.time() - start_time,
                steps_executed=executed_steps,
                error=error_msg,
                screenshots=screenshots
            )
            
        finally:
            await self._cleanup_resources()
            self.running_tasks -= 1
            self.status = TaskStatus.COMPLETED if self.running_tasks == 0 else TaskStatus.PENDING

    async def _execute_task_internal(self, 
                                   task_description: str, 
                                   custom_steps: Optional[List[ExecutionStep]],
                                   context: Optional[Dict[str, Any]],
                                   screenshots: List[bytes]) -> TaskResult:
        """Execução interna da tarefa com lógica de decomposição e execução."""
        
        start_time = time.time()
        
        # Inicializar adapter
        await self.adapter.start()
        
        # Screenshot inicial
        initial_screenshot = await self.adapter.screenshot()
        screenshots.append(initial_screenshot)
        
        # Obter steps da IA ou usar custom steps
        if custom_steps:
            steps = custom_steps
        else:
            steps = await self._get_intelligence_steps(task_description, initial_screenshot, context)
        
        if not steps:
            raise ValueError("Nenhum passo foi gerado para a tarefa")
        
        # Executar steps com retry e monitoramento
        executed_steps = 0
        for i, step in enumerate(steps):
            step_start_time = time.time()
            
            # Callback de início de step
            if self.on_step_start:
                await self.on_step_start(step, i + 1, len(steps))
            
            try:
                await self._execute_step_with_retry(step, i + 1)
                executed_steps += 1
                
                # Screenshot após step se solicitado
                if step.screenshot_after:
                    post_step_screenshot = await self.adapter.screenshot()
                    screenshots.append(post_step_screenshot)
                
                # Callback de conclusão de step
                if self.on_step_complete:
                    step_duration = time.time() - step_start_time
                    await self.on_step_complete(step, i + 1, len(steps), step_duration)
                
                # Callback de progresso
                if self.on_task_progress:
                    progress = (i + 1) / len(steps) * 100
                    await self.on_task_progress(progress, executed_steps, len(steps))
                
            except Exception as step_error:
                logger.error(f"Falha no passo {i + 1}: {step_error}")
                
                # Screenshot de erro do step
                if self.screenshot_on_error:
                    try:
                        step_error_screenshot = await self.adapter.screenshot()
                        screenshots.append(step_error_screenshot)
                    except:
                        pass
                
                # Decidir se continua ou para
                if not await self._should_continue_after_error(step, step_error, i + 1):
                    raise step_error
        
        execution_time = time.time() - start_time
        
        # Screenshot final
        final_screenshot = await self.adapter.screenshot()
        screenshots.append(final_screenshot)
        
        logger.info(f"Tarefa concluída com sucesso", 
                   duration=f"{execution_time:.2f}s",
                   steps_executed=executed_steps)
        
        return TaskResult(
            success=True,
            duration_seconds=round(execution_time, 2),
            steps_executed=executed_steps,
            screenshots=screenshots,
            metadata=self.execution_metadata
        )

    async def _get_intelligence_steps(self, 
                                    task_description: str, 
                                    screenshot: bytes,
                                    context: Optional[Dict[str, Any]]) -> List[ExecutionStep]:
        """Obter steps decompostos pela IA."""
        
        intelligence_result = await self.intelligence_client.analyze_and_decompose(
            task_description, screenshot, context
        )
        
        raw_steps = intelligence_result.get("steps", [])
        
        # Converter para ExecutionStep objects
        steps = []
        for raw_step in raw_steps:
            step = ExecutionStep(
                action=raw_step.get("action"),
                params=raw_step.get("params", {}),
                description=raw_step.get("description", "N/A"),
                max_retries=raw_step.get("max_retries", 3),
                timeout=raw_step.get("timeout", 30.0),
                screenshot_after=raw_step.get("screenshot_after", False)
            )
            steps.append(step)
        
        return steps

    async def _execute_step_with_retry(self, step: ExecutionStep, step_number: int):
        """Executa um step com retry automático."""
        
        last_error = None
        
        for attempt in range(step.max_retries + 1):
            try:
                await asyncio.wait_for(
                    self._execute_single_step(step, step_number, attempt + 1),
                    timeout=step.timeout
                )
                return  # Sucesso
                
            except Exception as e:
                last_error = e
                step.retry_count = attempt + 1
                
                if attempt < step.max_retries:
                    wait_time = min(2 ** attempt, 10)  # Exponential backoff
                    logger.warning(f"Passo {step_number} falhou (tentativa {attempt + 1}), "
                                 f"tentando novamente em {wait_time}s: {str(e)}")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Passo {step_number} falhou após {step.max_retries + 1} tentativas")
                    raise last_error

    async def _execute_single_step(self, step: ExecutionStep, step_number: int, attempt: int):
        """Executa um único step."""
        
        logger.info(f"Executando passo {step_number} (tentativa {attempt})",
                   action=step.action,
                   description=step.description)
        
        action = step.action
        params = step.params
        
        # Lógica de execução aprimorada
        if action == "click":
            await self._execute_click_action(params)
        elif action == "type":
            await self._execute_type_action(params)
        elif action == "navigate":
            await self._execute_navigate_action(params)
        elif action == "wait":
            await self._execute_wait_action(params)
        elif action == "scroll":
            await self._execute_scroll_action(params)
        elif action == "smart_search_click":
            await self._execute_smart_search_click(params)
        elif action == "custom":
            await self._execute_custom_action(params)
        else:
            # Fallback para métodos do adapter
            action_method = getattr(self.adapter, action, None)
            if callable(action_method):
                await action_method(**params)
            else:
                raise ValueError(f"Ação desconhecida: {action}")

    async def _execute_click_action(self, params: Dict[str, Any]):
        """Executa ação de clique com diferentes estratégias."""
        
        selector = params.get("selector")
        if not selector:
            raise ValueError("Click action requer 'selector'")
        
        # Usar robust_click por padrão
        await self.adapter.robust_click(primary_selector=selector, **params)

    async def _execute_type_action(self, params: Dict[str, Any]):
        """Executa ação de digitação."""
        
        selector = params.get("selector")
        text = params.get("text")
        
        if not selector or text is None:
            raise ValueError("Type action requer 'selector' e 'text'")
        
        # Limpar campo antes de digitar se especificado
        if params.get("clear_before", True):
            await self.adapter.clear_field(selector)
        
        await self.adapter.type(selector=selector, text=text, **params)

    async def _execute_navigate_action(self, params: Dict[str, Any]):
        """Executa ação de navegação."""
        
        url = params.get("url")
        if not url:
            raise ValueError("Navigate action requer 'url'")
        
        await self.adapter.navigate(url=url, **params)

    async def _execute_wait_action(self, params: Dict[str, Any]):
        """Executa ação de espera."""
        
        duration = params.get("duration", 1.0)
        condition = params.get("condition")
        
        if condition:
            # Espera condicional
            await self.adapter.wait_for_condition(condition, **params)
        else:
            # Espera simples
            await asyncio.sleep(duration)

    async def _execute_scroll_action(self, params: Dict[str, Any]):
        """Executa ação de scroll."""
        
        direction = params.get("direction", "down")
        pixels = params.get("pixels", 300)
        
        if hasattr(self.adapter, 'scroll'):
            await self.adapter.scroll(direction=direction, pixels=pixels, **params)
        else:
            # Fallback usando JavaScript
            if direction == "down":
                await self.adapter.execute_script(f"window.scrollBy(0, {pixels})")
            elif direction == "up":
                await self.adapter.execute_script(f"window.scrollBy(0, -{pixels})")

    async def _execute_smart_search_click(self, params: Dict[str, Any]):
        """Executa ação de clique inteligente."""
        
        if hasattr(self.adapter, 'smart_search_click'):
            await self.adapter.smart_search_click(**params)
        else:
            # Fallback para robust_click
            await self.adapter.robust_click(**params)

    async def _execute_custom_action(self, params: Dict[str, Any]):
        """Executa ação customizada."""
        
        custom_function = params.get("function")
        custom_params = params.get("params", {})
        
        if custom_function and hasattr(self.adapter, custom_function):
            method = getattr(self.adapter, custom_function)
            await method(**custom_params)
        else:
            raise ValueError(f"Função customizada não encontrada: {custom_function}")

    async def _should_continue_after_error(self, 
                                         step: ExecutionStep, 
                                         error: Exception, 
                                         step_number: int) -> bool:
        """Decide se deve continuar após erro em um step."""
        
        # Configurações podem ser definidas no step ou globalmente
        continue_on_error = step.params.get("continue_on_error", False)
        
        # Log da decisão
        if continue_on_error:
            logger.warning(f"Continuando execução após erro no passo {step_number}")
        
        return continue_on_error

    async def _cleanup_resources(self):
        """Limpa recursos utilizados."""
        
        try:
            await self.adapter.close()
        except Exception as e:
            logger.warning(f"Erro ao limpar recursos: {e}")
        
        # Limpar metadata
        self.execution_metadata.clear()
        self.current_task_id = None

    async def cancel_current_task(self):
        """Cancela a tarefa atual."""
        
        if self.status == TaskStatus.RUNNING:
            self.status = TaskStatus.CANCELLED
            logger.info("Tarefa cancelada pelo usuário")
            await self._cleanup_resources()

    def set_callbacks(self, 
                     on_step_start: Optional[Callable] = None,
                     on_step_complete: Optional[Callable] = None,
                     on_task_progress: Optional[Callable] = None):
        """Define callbacks para monitoramento."""
        
        self.on_step_start = on_step_start
        self.on_step_complete = on_step_complete
        self.on_task_progress = on_task_progress

    def get_execution_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas de execução."""
        
        return {
            "status": self.status.value,
            "running_tasks": self.running_tasks,
            "current_task_id": self.current_task_id,
            "max_concurrent_tasks": self.max_concurrent_tasks,
            "global_timeout": self.global_timeout
        }