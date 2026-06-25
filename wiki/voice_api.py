# voice_api.py
# API Endpoints para o Motor de Voz da Atena

from fastapi import APIRouter, HTTPException, Request, UploadFile, File
from pydantic import BaseModel
from typing import Dict

# O orquestrador principal é acessado via `request.app.state`
# o que evita importações circulares e segue as boas práticas do FastAPI.

router = APIRouter()

class CorrectionRequest(BaseModel):
    """Modelo de dados para ensinar uma correção ao sistema."""
    raw_text: str
    corrected_text: str

@router.post(
    "/v1/voice/transcribe",
    summary="Transcreve áudio para texto",
    response_description="Um JSON contendo a transcrição crua do Whisper e a versão corrigida pelo léxico fonético."
)
async def transcribe_audio(request: Request, audio_file: UploadFile = File(...)) -> Dict[str, str]:
    """
    Recebe um arquivo de áudio, o transcreve usando o modelo Whisper,
    aplica a correção do léxico fonético e retorna ambos os textos.
    """
    if not hasattr(request.app.state, 'cognitive_system'):
        raise HTTPException(status_code=503, detail="Sistema cognitivo não está pronto.")

    cognitive_system = request.app.state.cognitive_system
    if not hasattr(cognitive_system, 'voice_motor'):
        raise HTTPException(status_code=503, detail="O motor de voz não está disponível.")

    try:
        audio_bytes = await audio_file.read()
        transcription_result = await cognitive_system.voice_motor.transcribe_audio(audio_bytes)
        return transcription_result
    except Exception as e:
        logger.error(f"Erro no endpoint de transcrição: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro interno durante a transcrição: {e}")


@router.post(
    "/v1/voice/learn_correction",
    summary="Ensina uma correção de voz ao sistema",
    response_description="Status da operação de aprendizado."
)
async def learn_correction(request: Request, correction_data: CorrectionRequest):
    """
    Recebe uma transcrição bruta (incorreta) e a versão corrigida
    pelo usuário para treinar e aprimorar o léxico fonético.
    """
    if not hasattr(request.app.state, 'cognitive_system'):
        raise HTTPException(status_code=503, detail="Sistema cognitivo não está pronto.")

    cognitive_system = request.app.state.cognitive_system
    if not hasattr(cognitive_system, 'voice_motor'):
        raise HTTPException(status_code=503, detail="O motor de voz não está disponível.")

    try:
        result = cognitive_system.voice_motor.learn_correction(
            raw_text=correction_data.raw_text,
            corrected_text=correction_data.corrected_text
        )
        return result
    except Exception as e:
        logger.error(f"Erro no endpoint de aprendizado: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro interno durante o aprendizado: {e}")