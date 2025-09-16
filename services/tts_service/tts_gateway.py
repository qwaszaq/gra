from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
import os, uuid, hashlib, subprocess, shlex, requests, wave, struct

app = FastAPI(title="TTS Gateway", version="1.1.0")

# CORS
origins = [os.getenv("WEB_CLIENT_ORIGIN", "http://localhost:5173")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

AUDIO_DIR = "audio"
os.makedirs(AUDIO_DIR, exist_ok=True)

# ENV
TTS_CACHE = os.getenv("TTS_CACHE", "1") == "1"
PIPER_BIN = os.getenv("PIPER_BIN", "")           # np. /app/bin/piper
PIPER_VOICE = os.getenv("PIPER_VOICE", "")       # np. /app/voices/pl_PL.onnx
ELEVEN_API_KEY = os.getenv("ELEVEN_API_KEY", "")
ELEVEN_VOICE_ID = os.getenv("ELEVEN_VOICE_ID", "")

PUBLIC_TTS_BASE = os.getenv("PUBLIC_TTS_BASE","http://localhost:8001")

class Req(BaseModel):
    text: str
    turn_id: int
    session_id: str

@app.get("/health")
def health():
    backend = "fallback"
    if ELEVEN_API_KEY and ELEVEN_VOICE_ID:
        backend = "elevenlabs"
    elif PIPER_BIN and PIPER_VOICE:
        backend = "piper"
    return {"status":"ok","backend":backend,"cache":TTS_CACHE}

def _hash_text(text: str) -> str:
    # Cache po treści narracji: globalny (nie per tura)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def _write_silence_wav(path: str, seconds=1, fr=22050):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with wave.open(path, 'w') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(fr)
        frames = int(fr*seconds)
        silence_frame = struct.pack('<h', 0)
        for _ in range(frames):
            w.writeframes(silence_frame)

def tts_with_piper(text: str, out_path: str) -> bool:
    # Wymaga PIPER_BIN i PIPER_VOICE
    if not (PIPER_BIN and PIPER_VOICE):
        return False
    try:
        cmd = f'{shlex.quote(PIPER_BIN)} -m {shlex.quote(PIPER_VOICE)} -f {shlex.quote(out_path)} -q'
        # Piper czyta tekst ze stdin
        proc = subprocess.run(shlex.split(cmd), input=text.encode("utf-8"), capture_output=True, timeout=30)
        return proc.returncode == 0 and os.path.exists(out_path) and os.path.getsize(out_path) > 44
    except Exception:
        return False

def tts_with_elevenlabs(text: str, out_path: str) -> bool:
    if not (ELEVEN_API_KEY and ELEVEN_VOICE_ID):
        return False
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVEN_VOICE_ID}/stream"
    headers = {"xi-api-key": ELEVEN_API_KEY, "accept": "audio/mpeg", "content-type":"application/json"}
    payload = {"text": text, "model_id": "eleven_multilingual_v2", "voice_settings": {"stability":0.35,"similarity_boost":0.75}}
    try:
        with requests.post(url, headers=headers, json=payload, stream=True, timeout=30) as r:
            r.raise_for_status()
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            with open(out_path, "wb") as f:
                for chunk in r.iter_content(8192):
                    f.write(chunk)
        return os.path.exists(out_path) and os.path.getsize(out_path) > 0
    except Exception:
        return False

@app.post("/speak")
def speak(req: Req):
    text = req.text.strip()
    if not text:
        text = "."

    # Plik docelowy z cache po tekście
    base = _hash_text(text)
    # Preferuj WAV dla Piper, MP3 dla ElevenLabs
    ext = ".wav" if (PIPER_BIN and PIPER_VOICE) else (".mp3" if ELEVEN_API_KEY and ELEVEN_VOICE_ID else ".wav")
    fname = f"{base}{ext}"
    fpath = os.path.join(AUDIO_DIR, fname)

    # Cache hit
    if TTS_CACHE and os.path.exists(fpath) and os.path.getsize(fpath) > 0:
        return {"audio_url": f"{PUBLIC_TTS_BASE}/audio/{fname}"}

    # Generuj wg dostępnych backendów
    ok = False
    if ELEVEN_API_KEY and ELEVEN_VOICE_ID:
        ok = tts_with_elevenlabs(text, fpath)
    if not ok and PIPER_BIN and PIPER_VOICE:
        # Jeśli poprzednio zapisał MP3 pod tą nazwą – usuń przed WAV
        if ext != ".wav" and os.path.exists(fpath):
            try: os.remove(fpath)
            except: pass
        fpath = os.path.join(AUDIO_DIR, f"{base}.wav")
        fname = f"{base}.wav"
        ok = tts_with_piper(text, fpath)

    # Fallback: cichy WAV (zachowuje UX i kontrakt)
    if not ok:
        fpath = os.path.join(AUDIO_DIR, f"{base}.wav")
        fname = f"{base}.wav"
        _write_silence_wav(fpath, 1)

    return {"audio_url": f"{PUBLIC_TTS_BASE}/audio/{fname}"}

# Serwuj audio
app.mount("/audio", StaticFiles(directory=AUDIO_DIR), name="audio")
