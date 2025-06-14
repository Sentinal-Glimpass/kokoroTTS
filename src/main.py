# src/main.py
import logging
import io

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field
from typing import Optional
import soundfile as sf
import numpy as np

from .valid_options import (
    VALID_LANG_VOICES,
    MIN_SPEED,
    MAX_SPEED,
    DEFAULT_SPEED,
    SUPPORTED_API_LANG_CODES
)
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

# --- Configuration ---
SERVER_API_KEY = "f65a86f5ad86f5d86f4ad86f4a8f58asf58as56fa8" # TODO: IMPORTANT! Change this key and load from env var/secrets manager for production!

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
    lang_code: Optional[str] = Field(DEFAULT_LANG_CODE,
                                     description=f"Short language code for the voice. Supported: {', '.join(SUPPORTED_API_LANG_CODES)}. Defaults to configured service language.")
    voice: str = Field(..., description="Voice model name (e.g., 'hf_beta', 'af_heart'). Must be valid for the specified lang_code.")
    speed: float = Field(DEFAULT_SPEED, ge=MIN_SPEED, le=MAX_SPEED,
                         description=f"Speech speed. Min: {MIN_SPEED}, Max: {MAX_SPEED}, Default: {DEFAULT_SPEED}")
    api_key: str = Field(..., description="API key for accessing the service.")


@app.post("/synthesize", 
            responses={
                200: {
                    "content": {"audio/wav": {}},
                    "description": "Successful synthesis, returns WAV audio data."
                },
                400: {"description": "Bad Request (e.g., empty text)"},
                401: {"description": "Unauthorized (e.g., invalid API key)"},
                500: {"description": "Internal Server Error (e.g., synthesis failed)"},
                503: {"description": "Service Unavailable (e.g., TTS components not initialized)"}
            },
            summary="Synthesize Speech",
            description="Takes text and an optional voice, returns synthesized speech as a WAV audio file."
)
async def synthesize_speech_endpoint(request: TTSRequest):
    global tts_service, tts_pipeline_manager # Added tts_pipeline_manager to global for consistency

    # --- API Key Check ---
    if request.api_key != SERVER_API_KEY:
        logger.warning(f"Invalid API key attempt. Provided key prefix: {request.api_key[:4]}...") # Log prefix for security
        raise HTTPException(status_code=401, detail="Invalid API Key")
    # --- End API Key Check ---
    if not tts_service or not tts_pipeline_manager:
        logger.error("TTS service or manager not available. Check startup logs.")
        raise HTTPException(status_code=503, detail="TTS service is not available. Please check server logs.")

    if not request.text.strip():
        logger.warning("Received empty text for synthesis.")
        raise HTTPException(status_code=400, detail="Text cannot be empty.")

    # Validate lang_code
    requested_api_lang_code = request.lang_code if request.lang_code else DEFAULT_LANG_CODE
    if requested_api_lang_code not in VALID_LANG_VOICES:
        raise HTTPException(status_code=400, detail=f"Unsupported lang_code: '{requested_api_lang_code}'. Supported codes: {', '.join(SUPPORTED_API_LANG_CODES)}")

    # Check compatibility with the initialized pipeline manager's language
    # This is a limitation of the current single-language pool manager.
    if tts_pipeline_manager.lang_code != requested_api_lang_code:
        logger.error(f"Requested lang_code '{requested_api_lang_code}' is not compatible with service's initialized KPipeline lang '{tts_pipeline_manager.lang_code}'.")
        raise HTTPException(status_code=400, 
                            detail=f"Language '{requested_api_lang_code}' is not supported by this service instance which is configured for language '{tts_pipeline_manager.lang_code}'.")

    # Voice validation against a predefined list for the lang_code is now removed.
    # The provided 'voice' string will be passed directly to the KPipeline.
    # It's assumed KPipeline will handle invalid voice strings for its configured language.

    # Speed is validated by Pydantic (ge, le)
    logger.info(f"Received synthesis request: Lang='{requested_api_lang_code}', Voice='{request.voice}', Speed='{request.speed}', Text='{request.text[:50]}...'")
    
    audio_data, sample_rate = await run_in_threadpool(tts_service.synthesize_speech, text=request.text, voice=request.voice, speed=request.speed)

    if audio_data is None or sample_rate is None:
        logger.error(f"Synthesis failed for text: '{request.text[:50]}...'")
        raise HTTPException(status_code=500, detail="Speech synthesis failed.")

    # Ensure audio_data is 16-bit PCM
    # If kokoro outputs float, it needs conversion. Assuming it's already int16 based on previous WAV write.
    # If not, an explicit conversion like: audio_data = (audio_data * 32767).astype(np.int16) would be needed if it was float in [-1, 1]
    try:
        # Convert NumPy array directly to bytes
        # This assumes audio_data is a 1D NumPy array of dtype int16 (PCM16)
        # If kokoro's KPipeline or TTSService changes output format, this needs adjustment.
        if audio_data.dtype != np.int16:
            logger.warning(f"Audio data is not int16, it is {audio_data.dtype}. Attempting conversion.")
            # Example: if float32, scale and convert
            if np.issubdtype(audio_data.dtype, np.floating):
                audio_data = np.clip(audio_data, -1.0, 1.0) # Ensure data is in [-1, 1] range for floats
                audio_data = (audio_data * 32767).astype(np.int16)
            else:
                # For other integer types, just ensure it's int16
                audio_data = audio_data.astype(np.int16)
        
        pcm_data = audio_data.tobytes()
        logger.info(f"Successfully converted audio to raw PCM bytes. Size: {len(pcm_data)} bytes. Sample rate: {sample_rate} Hz.")
        # Assuming mono channel audio, which is typical for TTS.
        # The media type 'audio/L16' implies 16-bit linear PCM.
        # 'rate' specifies the sample rate.
        # 'channels' specifies the number of audio channels.
        media_type = f"audio/L16;rate={sample_rate};channels=1"
        return Response(content=pcm_data, media_type=media_type)

    except Exception as e:
        logger.error(f"Failed to convert audio to PCM bytes: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to process audio data into PCM.")

@app.get("/health", 
         summary="Health Check",
         description="Returns the health status of the TTS service, including pipeline manager status.")
async def health_check():
    global tts_pipeline_manager, tts_service # Added tts_service for consistency
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
