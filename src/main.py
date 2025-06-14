# src/main.py
import logging
import io

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import soundfile as sf
import uvicorn

from .config import (
    DEFAULT_LANG_CODE,
    DEFAULT_VOICE,
    API_HOST,
    API_PORT,
    LOG_LEVEL
)
from .pipeline_manager import TTSPipelineManager
from .tts_service import TTSService, SAMPLE_RATE

logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="kokoroTTS Service",
    description="A high-performance Text-to-Speech service using kokoro and FastAPI.",
    version="0.1.0"
)

# --- Global instances --- #
# These will be initialized on startup
tts_pipeline_manager: TTSPipelineManager | None = None
tts_service: TTSService | None = None

@app.on_event("startup")
async def startup_event():
    """Initialize TTS Pipeline Manager and Service on application startup."""
    global tts_pipeline_manager, tts_service
    logger.info("Application startup: Initializing TTSPipelineManager...")
    try:
        tts_pipeline_manager = TTSPipelineManager(lang_code=DEFAULT_LANG_CODE)
        logger.info("TTSPipelineManager initialized successfully.")
        logger.info(f"Initial pipeline status: {tts_pipeline_manager.get_status()}")
        
        tts_service = TTSService(pipeline_manager=tts_pipeline_manager)
        logger.info("TTSService initialized successfully.")
    except Exception as e:
        logger.critical(f"Failed to initialize TTS components during startup: {e}", exc_info=True)
        # Depending on the severity, you might want to prevent the app from starting
        # or handle this in a way that the app starts but reports itself as unhealthy.
        # For now, we log critical and it will likely fail on first request.
        tts_pipeline_manager = None # Ensure it's None if failed
        tts_service = None

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on application shutdown."""
    global tts_pipeline_manager
    if tts_pipeline_manager:
        logger.info("Application shutdown: Shutting down TTSPipelineManager...")
        tts_pipeline_manager.shutdown()
        logger.info("TTSPipelineManager shut down successfully.")

class TTSRequest(BaseModel):
    text: str
    voice: str = DEFAULT_VOICE

@app.post("/synthesize", 
            responses={
                200: {
                    "content": {"audio/wav": {}},
                    "description": "Successful synthesis, returns WAV audio data."
                },
                400: {"description": "Bad Request (e.g., empty text)"},
                500: {"description": "Internal Server Error (e.g., synthesis failed)"},
                503: {"description": "Service Unavailable (e.g., TTS components not initialized)"}
            },
            summary="Synthesize Speech",
            description="Takes text and an optional voice, returns synthesized speech as a WAV audio file."
)
async def synthesize_speech_endpoint(request: TTSRequest):
    global tts_service
    if not tts_service or not tts_pipeline_manager:
        logger.error("TTS service or manager not available. Check startup logs.")
        raise HTTPException(status_code=503, detail="TTS service is not available. Please check server logs.")

    if not request.text.strip():
        logger.warning("Received empty text for synthesis.")
        raise HTTPException(status_code=400, detail="Text cannot be empty.")

    logger.info(f"Received synthesis request: Text='{request.text[:50]}...', Voice='{request.voice}'")
    
    audio_data, sample_rate = tts_service.synthesize_speech(text=request.text, voice=request.voice)

    if audio_data is None or sample_rate is None:
        logger.error(f"Synthesis failed for text: '{request.text[:50]}...'")
        raise HTTPException(status_code=500, detail="Speech synthesis failed.")

    # Convert numpy array to WAV bytes
    wav_io = io.BytesIO()
    try:
        sf.write(wav_io, audio_data, sample_rate, format='WAV', subtype='PCM_16')
        wav_io.seek(0)
        logger.info(f"Successfully converted audio to WAV format. Size: {wav_io.getbuffer().nbytes} bytes.")
    except Exception as e:
        logger.error(f"Failed to write WAV audio to BytesIO: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to process audio data.")

    return StreamingResponse(wav_io, media_type="audio/wav")

@app.get("/health", 
         summary="Health Check",
         description="Returns the health status of the TTS service, including pipeline manager status.")
async def health_check():
    global tts_pipeline_manager
    if tts_pipeline_manager and tts_service:
        manager_status = tts_pipeline_manager.get_status()
        return {
            "status": "ok",
            "message": "TTS Service is running.",
            "pipeline_manager_status": manager_status
        }
    else:
        return {
            "status": "error",
            "message": "TTS Service is not properly initialized. Check logs.",
            "pipeline_manager_status": None
        }

if __name__ == "__main__":
    # This is for direct execution (e.g., python -m src.main)
    # For production, use a command like: uvicorn src.main:app --host 0.0.0.0 --port 8000
    logger.info(f"Starting Uvicorn server on {API_HOST}:{API_PORT}")
    uvicorn.run(app, host=API_HOST, port=API_PORT, log_level=LOG_LEVEL.lower())
