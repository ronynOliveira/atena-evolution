# atena_servidor_unified.py
# Versão 5.2 - Roteadores Unificados

import os
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional, List
from pathlib import Path
import time
import uuid

# Frameworks do Servidor e Dados
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# --- Módulo Orquestrador Principal da Atena ---
from atena_integrated_cognitive_system import AtenaIntegratedCognitiveSystem
from atena_config import AtenaConfig
from atena_web_fasAPI import search_router
from atena_psique import router as psique_router
from voice_api import router as voice_router # API de Voz

# --- Configuração de Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(name)s] - [%(levelname)s] - %(message)s')
logger = logging.getLogger("AtenaEcossistema")

# --- Estado da Aplicação ---
atena_system: Dict[str, Any] = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gerencia o ciclo de vida da aplicação, inicializando e finalizando
    o sistema cognitivo integrado da Atena.
    """
    logger.info("Iniciando ciclo de vida do Ecossistema Atena v5.2 (Consolidado)...")
    
    try:
        # Instanciar a configuração centralizada
        config = AtenaConfig()
        
        # Instanciar e inicializar o Sistema Cognitivo Integrado (Orquestrador)
        logger.info("Instanciando o Sistema Cognitivo Integrado (Orquestrador)...")
        cognitive_system = AtenaIntegratedCognitiveSystem(config)
        await cognitive_system.start()
        
        atena_system["cognitive_system"] = cognitive_system
        atena_system["is_ready"] = True
        
        logger.info("====== ATENA ONLINE E OPERACIONAL ======")

    except Exception as e:
        logger.critical(f"FALHA CRÍTICA DURANTE A INICIALIZAÇÃO: {e}", exc_info=True)
        atena_system["is_ready"] = False
        atena_system["error"] = str(e)
    
    finally:
        # O yield deve estar fora do try/except principal, mas dentro do async context manager
        # para garantir que o shutdown ocorra.
        pass # Nenhuma ação necessária aqui, o código de shutdown está abaixo do yield.

    yield

    logger.info("Finalizando ciclo de vida da aplicação Atena...")
    if atena_system.get("is_ready"):
        cognitive_system: AtenaIntegratedCognitiveSystem = atena_system["cognitive_system"]
        await cognitive_system.shutdown()
    logger.info("====== ATENA OFFLINE ======")

# --- Inicialização da Aplicação FastAPI ---
app = FastAPI(title="Servidor do Ecossistema Atena", version="5.2.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(search_router, prefix="/api")
app.include_router(psique_router, prefix="/api")
app.include_router(voice_router, prefix="/api", tags=["Voz"]) # Roteador da API de Voz

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Log das requisições
    """
    start_time = time.time()
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    
    logger.info(f"Request: {request.method} {request.url.path} - Status: {response.status_code} - Time: {process_time:.3f}s")
    
    return response

# --- Modelos de Dados da API (Pydantic) ---
class InteractionRequest(BaseModel):
    text: str
    user_id: str = "Senhor Robério"
    session_id: Optional[str] = None
    contexts: List[str] = []

class InteractionResponse(BaseModel):
    response_text: str
    session_id: str
    status: str
    details: Optional[Any] = None

# ==============================================================================
# SEÇÃO DE API
# ==============================================================================

@app.get("/healthz", tags=["Sistema"])
async def health_check():
    if not atena_system.get("is_ready", False):
        return JSONResponse(status_code=503, content={"status": "unhealthy", "error": atena_system.get("error")})
    return {
        "status": "ok",
        "version": "5.2.0",
        "message": "Sistema Cognitivo Integrado está operacional."
    }

@app.get("/api/status", tags=["Sistema"])
async def get_system_status():
    """
    Retorna o status atual dos principais componentes do sistema.
    """
    is_ready = atena_system.get("is_ready", False)
    
    status = {
        "iaLocal": "online" if is_ready else "offline",
        "memoria": "online" if is_ready else "offline",
        "tts": "online" if is_ready else "offline"
    }
            
    return JSONResponse(content=status)

@app.post("/api/v1/interact", response_model=InteractionResponse, tags=["Orquestrador Principal"])
async def handle_interaction(request: InteractionRequest):
    """Processa a interação do usuário através do Sistema Cognitivo Integrado."""
    if not atena_system.get("is_ready"):
        raise HTTPException(status_code=503, detail="Sistema Cognitivo da Atena não está operacional.")
    
    start_time = time.time()
    cognitive_system: AtenaIntegratedCognitiveSystem = atena_system["cognitive_system"]
    
    try:
        # Adicionar os contextos à requisição
        context_data = {}
        if "memory" in request.contexts:
            context_data["use_memory"] = True
        if "web" in request.contexts:
            context_data["use_web_search"] = True
        if "user" in request.contexts:
            context_data["use_user_model"] = True
            
        result = await cognitive_system.process_user_request(
            request_text=request.text,
            user_id=request.user_id,
            context_data=context_data
        )
        
        session_id = request.session_id or str(uuid.uuid4())

        response_text = result.get("response", "Não foi possível gerar uma resposta.")
        if result.get("code_solution"):
             response_text += f"\n\nSolução de código gerada:\n```python\n{result['code_solution']}\n```"
        
        return InteractionResponse(
            response_text=response_text,
            session_id=session_id,
            status=result.get("status", "failed"),
            details=result
        )

    except Exception as e:
        logger.error(f"Erro no endpoint de interação: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro interno no orquestrador: {e}")

# Novo endpoint para listar provedores de IA disponíveis
@app.get("/api/v1/ai_providers", tags=["Provedores de IA"])
async def list_ai_providers():
    """Lista os provedores de IA disponíveis."""
    providers = [
        {
            "id": "atena-local",
            "nome_exibicao": "Atena Local",
            "descricao": "Modelo local otimizado para performance"
        },
        {
            "id": "openai-gpt4",
            "nome_exibicao": "OpenAI GPT-4",
            "descricao": "Modelo avançado da OpenAI"
        },
        {
            "id": "google-gemini",
            "nome_exibicao": "Google Gemini",
            "descricao": "Modelo multimodal do Google"
        },
        {
            "id": "rpa_executar_tarefa",
            "nome_exibicao": "ChatGPT RPA",
            "descricao": "Automação de tarefas via RPA"
        }
    ]
    return {"providers": providers}

# Novo endpoint para busca na memória
@app.get("/api/v1/memory_search", tags=["Memória"])
async def search_memory(query: str):
    """Busca na memória da Atena."""
    if not atena_system.get("is_ready"):
        raise HTTPException(status_code=503, detail="Sistema Cognitivo da Atena não está operacional.")
    
    cognitive_system: AtenaIntegratedCognitiveSystem = atena_system["cognitive_system"]
    
    try:
        memory_results = await cognitive_system.cognitive_architecture.search_memory(query)
        results = []
        
        for chunk in memory_results:
            results.append({
                "content": chunk.text,
                "score": float(chunk.score) if hasattr(chunk, 'score') else 0.0,
                "date": datetime.now().strftime("%Y-%m-%d")
            })
            
        return {"results": results}
    except Exception as e:
        logger.error(f"Erro na busca de memória: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro na busca de memória: {e}")

# Novo endpoint para status cognitivo
@app.get("/api/v1/cognitive_status", tags=["Status Cognitivo"])
async def get_cognitive_status():
    """Obtém o status cognitivo atual da Atena."""
    if not atena_system.get("is_ready"):
        raise HTTPException(status_code=503, detail="Sistema Cognitivo da Atena não está operacional.")
    
    # Simulação de status cognitivo - em uma implementação real, isso viria do sistema cognitivo
    status = {
        "cognitive_load": 0.65,
        "uncertainty": 0.30,
        "focus": "Análise de Dados",
        "hypotheses": [
            "O usuário está buscando informações sobre análise de dados.",
            "O usuário pode precisar de ajuda com visualização."
        ],
        "insights": [
            "Recomendação: Oferecer recursos de visualização de dados.",
            "Sugestão: Verificar conhecimento prévio sobre estatística."
        ]
    }
    
    return status

# Novo endpoint para registrar interações do usuário
@app.post("/api/v1/log_interaction", tags=["Interações"])
async def log_user_interaction(interaction_data: dict):
    """Registra interações do usuário para análise comportamental."""
    try:
        # Em uma implementação real, isso seria processado pelo modelo de usuário
        logger.info(f"Interação do usuário registrada: {interaction_data}")
        return {"status": "success", "message": "Interação registrada com sucesso"}
    except Exception as e:
        logger.error(f"Erro ao registrar interação: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro ao registrar interação: {e}")

# --- Rotas de Frontend (Comentadas para focar no backend) ---
# O código abaixo foi comentado pois a estrutura de frontend não existe neste projeto.
# Define o caminho para a pasta do frontend (um nível acima de 'backend')
# FRONTEND_DIR = Path(__file__).parent.parent.parent / "frontend"

# Monta a pasta do frontend como um diretório estático
# app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

# @app.get("/", response_class=HTMLResponse, include_in_schema=False)
# async def read_root(request: Request):
#     """Serve o painel principal da Atena."""
#     painel_path = FRONTEND_DIR / "painel_bolhas.html"
#     if not painel_path.exists():
#         return HTMLResponse(content=f"<h1>Erro 500: Arquivo do Painel não encontrado.</h1><p>Caminho procurado: {painel_path}</p>", status_code=500)
#     return FileResponse(painel_path)

