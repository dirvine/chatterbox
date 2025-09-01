#!/usr/bin/env python3
"""
ChatterBox TTS REST Service
A REST API service that accepts text and plays it through the Mac sound system
Can be used as a drop-in replacement for ElevenLabs API
"""

import os
import tempfile
import subprocess
import logging
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import uvicorn
import torchaudio as ta
from chatterbox.tts import ChatterboxTTS

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global model instance
model = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize model on startup, cleanup on shutdown."""
    global model
    logger.info("Loading ChatterBox TTS model...")
    try:
        model = ChatterboxTTS.from_pretrained(device="mps")
        logger.info("Model loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        raise
    yield
    # Cleanup
    model = None
    logger.info("Model unloaded")

# Create FastAPI app
app = FastAPI(
    title="ChatterBox TTS Service",
    description="Local TTS service for text-to-speech synthesis",
    version="1.0.0",
    lifespan=lifespan
)

class TTSRequest(BaseModel):
    """Request model for TTS synthesis."""
    text: str
    voice_id: Optional[str] = None  # For compatibility with ElevenLabs format
    audio_prompt_path: Optional[str] = None  # Path to voice sample
    play: bool = True  # Whether to play audio immediately
    return_audio: bool = False  # Whether to return audio file

class TTSResponse(BaseModel):
    """Response model for TTS synthesis."""
    success: bool
    message: str
    audio_file: Optional[str] = None

def cleanup_file(filepath: str):
    """Remove temporary file."""
    try:
        if os.path.exists(filepath):
            os.unlink(filepath)
    except Exception as e:
        logger.warning(f"Failed to cleanup {filepath}: {e}")

def play_audio(filepath: str) -> bool:
    """Play audio file using macOS afplay."""
    try:
        result = subprocess.run(
            ['afplay', filepath],
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode == 0:
            logger.info(f"Audio played successfully: {filepath}")
            return True
        else:
            logger.error(f"afplay failed: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        logger.error("Audio playback timed out")
        return False
    except FileNotFoundError:
        logger.error("afplay not found - are you on macOS?")
        return False
    except Exception as e:
        logger.error(f"Error playing audio: {e}")
        return False

@app.get("/")
async def root():
    """Root endpoint with service info."""
    return {
        "service": "ChatterBox TTS",
        "status": "running",
        "model_loaded": model is not None,
        "endpoints": {
            "synthesize": "/synthesize",
            "speak": "/speak",
            "health": "/health"
        }
    }

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "model_loaded": model is not None
    }

@app.post("/synthesize")
async def synthesize(request: TTSRequest, background_tasks: BackgroundTasks):
    """
    Synthesize text to speech.
    Compatible with ElevenLabs-style requests.
    """
    if not model:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    if not request.text:
        raise HTTPException(status_code=400, detail="Text is required")
    
    try:
        # Generate audio
        logger.info(f"Synthesizing: {request.text[:100]}...")
        
        if request.audio_prompt_path and os.path.exists(request.audio_prompt_path):
            wav = model.generate(request.text, audio_prompt_path=request.audio_prompt_path)
        else:
            wav = model.generate(request.text)
        
        # Save to temporary file
        temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        temp_path = temp_file.name
        temp_file.close()
        
        ta.save(temp_path, wav, model.sr)
        logger.info(f"Audio saved to: {temp_path}")
        
        # Play audio if requested
        if request.play:
            success = play_audio(temp_path)
            if not success:
                logger.warning("Failed to play audio")
        
        # Handle response
        if request.return_audio:
            # Return the audio file
            return FileResponse(
                temp_path,
                media_type="audio/wav",
                filename="synthesis.wav",
                background=background_tasks.add_task(cleanup_file, temp_path)
            )
        else:
            # Just return success status
            if not request.play:
                # If not playing, keep the file and return path
                return TTSResponse(
                    success=True,
                    message="Audio synthesized successfully",
                    audio_file=temp_path
                )
            else:
                # Clean up after playing
                background_tasks.add_task(cleanup_file, temp_path)
                return TTSResponse(
                    success=True,
                    message="Audio synthesized and played",
                    audio_file=None
                )
    
    except Exception as e:
        logger.error(f"Synthesis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/speak")
async def speak(request: TTSRequest, background_tasks: BackgroundTasks):
    """
    Simple endpoint that just speaks the text.
    Always plays audio and cleans up.
    """
    request.play = True
    request.return_audio = False
    return await synthesize(request, background_tasks)

@app.post("/v1/text-to-speech/{voice_id}")
async def elevenlabs_compatible(
    voice_id: str,
    request: dict,
    background_tasks: BackgroundTasks
):
    """
    ElevenLabs-compatible endpoint for drop-in replacement.
    Accepts ElevenLabs API format and returns audio.
    """
    try:
        # Extract text from ElevenLabs format
        text = request.get("text", "")
        if not text:
            raise HTTPException(status_code=400, detail="Text is required")
        
        # Create TTS request
        tts_request = TTSRequest(
            text=text,
            voice_id=voice_id,
            play=False,
            return_audio=True
        )
        
        # Generate and return audio
        if not model:
            raise HTTPException(status_code=503, detail="Model not loaded")
        
        logger.info(f"ElevenLabs-compatible synthesis for voice {voice_id}: {text[:100]}...")
        
        wav = model.generate(text)
        
        # Convert to MP3 for ElevenLabs compatibility
        temp_wav = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        temp_mp3 = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False)
        temp_wav_path = temp_wav.name
        temp_mp3_path = temp_mp3.name
        temp_wav.close()
        temp_mp3.close()
        
        ta.save(temp_wav_path, wav, model.sr)
        
        # Convert WAV to MP3 using ffmpeg
        try:
            result = subprocess.run(
                ['ffmpeg', '-i', temp_wav_path, '-acodec', 'mp3', '-y', temp_mp3_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode != 0:
                logger.warning(f"ffmpeg conversion failed, returning WAV: {result.stderr}")
                os.unlink(temp_mp3_path)
                # Return WAV if MP3 conversion fails
                return FileResponse(
                    temp_wav_path,
                    media_type="audio/wav",
                    background=background_tasks.add_task(cleanup_file, temp_wav_path)
                )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            logger.warning("ffmpeg not available, returning WAV")
            os.unlink(temp_mp3_path)
            # Return WAV if ffmpeg not available
            return FileResponse(
                temp_wav_path,
                media_type="audio/wav",
                background=background_tasks.add_task(cleanup_file, temp_wav_path)
            )
        
        # Clean up WAV, return MP3
        background_tasks.add_task(cleanup_file, temp_wav_path)
        return FileResponse(
            temp_mp3_path,
            media_type="audio/mpeg",
            background=background_tasks.add_task(cleanup_file, temp_mp3_path)
        )
    
    except Exception as e:
        logger.error(f"ElevenLabs-compatible synthesis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="ChatterBox TTS Service")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    
    args = parser.parse_args()
    
    uvicorn.run(
        "tts_service:app" if args.reload else app,
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info"
    )