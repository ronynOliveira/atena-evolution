#!/usr/bin/env python3
"""
atena_api.py — API REST da Atena Evolução

FastAPI + WebSocket para interface de IA.

Endpoints:
- POST /api/chat — Chat com Atena
- POST /api/rag — Query RAG
- GET /api/status — Status do sistema
- WS /ws — WebSocket para chat em tempo real
- GET /api/metrics — Métricas de uso

Versão: 1.0.0
Data: 17/06/2026
"""

import logging
from typing import Dict, Any, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import asyncio
import time

logger = logging.getLogger("AtenaAPI")


# ── Models ──────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=8192)
    use_rag: bool = False
    use_free_apis: bool = False
    max_tokens: int = Field(default=512, gt=0, le=8192)
    temperature: float = Field(default=0.7, ge=0.0, le=1.5)


class ChatResponse(BaseModel):
    success: bool
    response: str
    provider: str
    latency_ms: float
    metrics: Dict[str, Any] = {}


class RAGRequest(BaseModel):
    query: str
    top_k: int = 5
    use_rerank: bool = True
    use_crag: bool = True


class RAGResponse(BaseModel):
    success: bool
    context: str
    chunks_found: int
    chunks_used: int
    crag_assessment: str
    metadata: Dict[str, Any] = {}


class StatusResponse(BaseModel):
    status: str
    version: str
    uptime_seconds: float
    providers: Dict[str, str]
    metrics: Dict[str, Any] = {}


# ── API App ─────────────────────────────────────────────────────────

def create_api(
    ai_broker=None,
    rag_engine=None,
    free_apis=None,
    safety_guard=None,
) -> FastAPI:
    """
    Cria a API FastAPI da Atena Evolução.
    
    Args:
        ai_broker: Instância do AtenaAIBroker
        rag_engine: Instância do RAGEngine
        free_apis: Instância do FreeAPIManager
        safety_guard: Instância do SafetyGuard
    """
    
    app = FastAPI(
        title="Atena Evolução API",
        description="API REST da Atena Evolução — IA Cognitiva Avançada",
        version="1.0.0",
    )
    
    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Estado
    start_time = time.time()
    connected_clients: Dict[str, WebSocket] = {}
    
    # ── Endpoints ─────────────────────────────────────────────────
    
    @app.get("/api/status", response_model=StatusResponse)
    async def get_status():
        """Status do sistema."""
        return StatusResponse(
            status="online",
            version="1.0.0",
            uptime_seconds=round(time.time() - start_time, 2),
            providers={
                "ai_broker": "active" if ai_broker else "inactive",
                "rag_engine": "active" if rag_engine else "inactive",
                "free_apis": "active" if free_apis else "inactive",
                "safety_guard": "active" if safety_guard else "inactive",
            },
            metrics={
                "connected_clients": len(connected_clients),
                "uptime_seconds": round(time.time() - start_time, 2),
            }
        )
    
    @app.post("/api/chat", response_model=ChatResponse)
    async def chat(request: ChatRequest):
        """Chat com a Atena."""
        if not ai_broker:
            raise HTTPException(status_code=503, detail="AI Broker não disponível")
        
        start = time.time()
        
        try:
            result = await ai_broker.generate_response(
                prompt=request.message,
                use_rag=request.use_rag,
                use_free_apis=request.use_free_apis,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
            )
            
            latency = (time.time() - start) * 1000
            
            return ChatResponse(
                success=result.get("success", True),
                response=result.get("content", ""),
                provider=result.get("provider", "unknown"),
                latency_ms=latency,
                metrics=result.get("metrics", {}),
            )
        except Exception as e:
            logger.error(f"Erro no chat: {e}")
            raise HTTPException(status_code=500, detail="Erro interno do servidor")
    
    @app.post("/api/rag", response_model=RAGResponse)
    async def rag_query(request: RAGRequest):
        """Query RAG."""
        if not rag_engine:
            raise HTTPException(status_code=503, detail="RAG Engine não disponível")
        
        try:
            from rag.rag_engine import RAGQuery
            
            rag_request = RAGQuery(
                text=request.query,
                top_k=request.top_k,
                use_rerank=request.use_rerank,
                use_crag=request.use_crag,
            )
            
            result = await rag_engine.query(rag_request)
            
            return RAGResponse(
                success=True,
                context=result.final_context,
                chunks_found=len(result.chunks),
                chunks_used=len(result.reranked_chunks),
                crag_assessment=result.crag_assessment,
                metadata=result.metadata,
            )
        except Exception as e:
            logger.error(f"Erro no RAG: {e}")
            raise HTTPException(status_code=500, detail="Erro interno do servidor")
    
    @app.get("/api/metrics")
    async def get_metrics():
        """Métricas de uso."""
        metrics = {}
        if ai_broker:
            metrics["ai_broker"] = ai_broker.get_metrics()
        return metrics
    
    # ── WebSocket ─────────────────────────────────────────────────
    
    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        """WebSocket para chat em tempo real."""
        await websocket.accept()
        client_id = f"client_{len(connected_clients)}"
        connected_clients[client_id] = websocket
        
        logger.info(f"WebSocket conectado: {client_id}")
        
        try:
            # Enviar mensagem de boas-vindas
            await websocket.send_json({
                "type": "welcome",
                "message": "Bem-vindo à Atena Evolução! Como posso ajudar?",
                "version": "1.0.0",
            })
            
            while True:
                data = await websocket.receive_json()
                
                message = data.get("message", "")
                use_rag = data.get("use_rag", False)
                
                if not message:
                    continue
                
                # Processar mensagem
                if ai_broker:
                    result = await ai_broker.generate_response(
                        prompt=message,
                        use_rag=use_rag,
                    )
                    
                    await websocket.send_json({
                        "type": "response",
                        "content": result.get("content", ""),
                        "provider": result.get("provider", ""),
                        "latency_ms": result.get("latency_ms", 0),
                    })
                else:
                    await websocket.send_json({
                        "type": "error",
                        "message": "AI Broker não disponível",
                    })
                    
        except WebSocketDisconnect:
            del connected_clients[client_id]
            logger.info(f"WebSocket desconectado: {client_id}")
        except Exception as e:
            logger.error(f"Erro no WebSocket: {e}")
            if client_id in connected_clients:
                del connected_clients[client_id]
    
    return app
