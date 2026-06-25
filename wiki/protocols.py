from typing import Protocol, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from agent import ExecutionContext

class BrowserAdapterProtocol(Protocol):
    """Protocol para adaptadores de navegador."""
    
    async def initialize(self, config: Dict[str, Any]) -> bool:
        """Inicializa navegador."""
        ...
    
    async def execute_action(self, action: Dict[str, Any], context: "ExecutionContext") -> Any:
        """Executa ação no navegador."""
        ...
    
    async def cleanup(self) -> None:
        """Limpa recursos."""
        ...