from fastapi import FastAPI
from pydantic import BaseModel
import os
import uuid

app = FastAPI(title="TTS Service", version="1.0.0")

PUBLIC_TTS_BASE = os.getenv("PUBLIC_TTS_BASE", "http://localhost:8001")

class TTSRequest(BaseModel):
    text: str
    turn_id: int
    session_id: str

@app.get("/health")
def health():
    return {"status": "ok", "service": "tts"}

@app.post("/speak")
def speak(request: TTSRequest):
    # Stub implementation - just return a placeholder audio URL
    audio_filename = f"audio_{request.session_id}_{request.turn_id}_{uuid.uuid4().hex[:8]}.mp3"
    audio_url = f"{PUBLIC_TTS_BASE}/audio/{audio_filename}"
    
    return {
        "audio_url": audio_url,
        "text": request.text,
        "turn_id": request.turn_id,
        "session_id": request.session_id
    }
