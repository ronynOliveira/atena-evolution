"""
Integração do Atena Web Search Engine com FastAPI
================================================
Rotas e endpoints para o motor de busca web
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import asyncio
from atena_web_search_engine import AtenaWebSearchEngine, SearchResult

# Modelos Pydantic para API
class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Termo de busca")
    max_results: int = Field(20, ge=1, le=100, description="Número máximo de resultados")
    sources: Optional[List[str]] = Field(None, description="Fontes específicas para buscar")

class SearchResponse(BaseModel):
    query: str
    total_results: int
    execution_time: float
    results: List[Dict[str, Any]]
    cache_hit: bool
    sources_used: List[str]

class PageContentRequest(BaseModel):
    url: str = Field(..., description="URL da página para extrair conteúdo")

class PageContentResponse(BaseModel):
    url: str
    content: str
    success: bool
    error_message: Optional[str] = None

class CacheStatsResponse(BaseModel):
    total_cached_queries: int
    recent_queries_24h: int
    cache_ttl_hours: int
    last_updated: datetime

# Router para rotas de busca
search_router = APIRouter(prefix="/search", tags=["web-search"])

# Instância global do motor de busca
search_engine = None

def get_search_engine():
    """Retorna instância do motor de busca"""
    global search_engine
    if search_engine is None:
        search_engine = AtenaWebSearchEngine()
    return search_engine

@search_router.post("/web", response_model=SearchResponse)
async def search_web(request: SearchRequest):
    """
    Busca na web usando múltiplas fontes
    """
    try:
        engine = get_search_engine()
        start_time = asyncio.get_event_loop().time()
        
        # Verificar se há cache
        cached_results = engine._get_cached_results(request.query)
        cache_hit = cached_results is not None
        
        # Realizar busca
        results = await engine.search(request.query, request.max_results)
        
        end_time = asyncio.get_event_loop().time()
        execution_time = end_time - start_time
        
        # Converter resultados para dict
        results_dict = []
        sources_used = set()
        
        for result in results:
            result_dict = {
                "title": result.title,
                "url": result.url,
                "snippet": result.snippet,
                "source": result.source,
                "timestamp": result.timestamp.isoformat(),
                "relevance_score": result.relevance_score,
                "metadata": result.metadata
            }
            results_dict.append(result_dict)
            sources_used.add(result.source)
        
        return SearchResponse(
            query=request.query,
            total_results=len(results),
            execution_time=execution_time,
            results=results_dict,
            cache_hit=cache_hit,
            sources_used=list(sources_used)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro na busca: {str(e)}")

@search_router.post("/content", response_model=PageContentResponse)
async def get_page_content(request: PageContentRequest):
    """
    Extrai conteúdo de uma página web específica
    """
    try:
        engine = get_search_engine()
        content = await engine.get_page_content(request.url)
        
        if content:
            return PageContentResponse(
                url=request.url,
                content=content,
                success=True
            )
        else:
            return PageContentResponse(
                url=request.url,
                content="",
                success=False,
                error_message="Não foi possível extrair conteúdo da página"
            )
            
    except Exception as e:
        return PageContentResponse(
            url=request.url,
            content="",
            success=False,
            error_message=str(e)
        )

@search_router.get("/cache/stats", response_model=CacheStatsResponse)
async def get_cache_stats():
    """
    Retorna estatísticas do cache de buscas
    """
    try:
        engine = get_search_engine()
        stats = engine.get_cache_stats()
        
        return CacheStatsResponse(
            total_cached_queries=stats["total_cached_queries"],
            recent_queries_24h=stats["recent_queries_24h"],
            cache_ttl_hours=stats["cache_ttl_hours"],
            last_updated=datetime.now()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao obter estatísticas do cache: {str(e)}")

@search_router.delete("/cache/clear")
async def clear_cache():
    """
    Limpa todo o cache de buscas
    """
    try:
        engine = get_search_engine()
        engine.clear_cache()
        
        return {"message": "Cache limpo com sucesso", "timestamp": datetime.now().isoformat()}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao limpar cache: {str(e)}")

@search_router.get("/sources")
async def get_available_sources():
    """
    Retorna lista de fontes de busca disponíveis e suas configurações
    """
    try:
        engine = get_search_engine()
        sources = engine.config.get("search_engines", {})
        
        available_sources = []
        for source_name, source_config in sources.items():
            available_sources.append({
                "name": source_name,
                "enabled": source_config.get("enabled", False),
                "priority": source_config.get("priority", 999),
                "requires_api_key": "api_key" in source_config
            })
        
        return {
            "sources": sorted(available_sources, key=lambda x: x["priority"]),
            "total_sources": len(available_sources),
            "enabled_sources": len([s for s in available_sources if s["enabled"]])
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao obter fontes: {str(e)}")

@search_router.get("/health")
async def health_check():
    """
    Verifica saúde do sistema de busca
    """
    try:
        engine = get_search_engine()
        
        # Teste simples de busca
        test_results = await engine.search("test", max_results=1)
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "cache_enabled": True,
            "test_search_successful": len(test_results) > 0,
            "version": "1.0"
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "version": "1.0"
        }



# Tarefas em background
async def periodic_cache_cleanup():
    """
    Limpeza periódica do cache (executar em background)
    """
    engine = get_search_engine()
    
    # Limpar entradas antigas do cache
    cursor = engine.cache_db.execute("""
        DELETE FROM search_cache 
        WHERE datetime(timestamp) < datetime('now', '-7 days')
    """)
    
    deleted_count = cursor.rowcount
    engine.cache_db.commit()
    
    print(f"Cache cleanup: removidas {deleted_count} entradas antigas")

@search_router.post("/maintenance/cleanup")
async def trigger_cache_cleanup(background_tasks: BackgroundTasks):
    """
    Dispara limpeza do cache em background
    """
    background_tasks.add_task(periodic_cache_cleanup)
    
    return {
        "message": "Limpeza do cache iniciada em background",
        "timestamp": datetime.now().isoformat()
    }

# Exemplo de integração completa com FastAPI
"""
Para usar este router em sua aplicação FastAPI:

from fastapi import FastAPI
from search_api import search_router

app = FastAPI(title="Atena Web Search API", version="1.0.0")
app.include_router(search_router)

# Exemplos de uso:
# POST /search/web
# {
#   "query": "Python FastAPI tutorial",
#   "max_results": 10
# }

# GET /search/cache/stats
# GET /search/sources
# DELETE /search/cache/clear
# POST /search/content
# {
#   "url": "https://example.com"
# }
"""