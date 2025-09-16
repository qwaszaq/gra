import os, hashlib, asyncio
from typing import Optional
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

REDIS_URL = os.getenv("REDIS_URL", "")
SUNO_API_KEY = os.getenv("SUNO_API_KEY", "")
SUNO_API_URL = os.getenv("SUNO_API_URL", "")
PUBLIC_AI_BASE = os.getenv("PUBLIC_AI_BASE", "http://localhost:8003")
MUSIC_DIR = "/app/music"
MUSIC_CACHE_TTL = int(os.getenv("MUSIC_CACHE_TTL", "3600"))

os.makedirs(MUSIC_DIR, exist_ok=True)

rdb = None
if REDIS_URL:
    try:
        import redis
        rdb = redis.Redis.from_url(REDIS_URL, decode_responses=True)
    except Exception:
        rdb = None

def _music_key(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()

def _cache_get(key: str) -> Optional[str]:
    if not rdb: return None
    try:
        return rdb.get(key)
    except Exception:
        return None

def _cache_set(key: str, value: str, ttl=MUSIC_CACHE_TTL):
    if not rdb: return
    try:
        rdb.set(key, value, ex=ttl)
    except Exception:
        pass

async def _download_to_file(url: str, out_path: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            async with client.stream("GET", url) as r:
                r.raise_for_status()
                with open(out_path, "wb") as f:
                    async for chunk in r.aiter_bytes():
                        f.write(chunk)
        return True
    except Exception:
        return False

async def _suno_start_job(prompt: str) -> str:
    """
    TODO: Dopasuj do oficjalnego Suno API.
    Przykładowy schemat:
      POST {SUNO_API_URL}/v1/generate
      body: {"prompt": prompt, "style":"dark noir jazz", ...}
      headers: {"Authorization": f"Bearer {SUNO_API_KEY}"}
      -> {"job_id":"..."}
    """
    if not (SUNO_API_URL and SUNO_API_KEY):
        raise RuntimeError("SUNO not configured")
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            f"{SUNO_API_URL}/v1/generate",
            headers={"Authorization": f"Bearer {SUNO_API_KEY}", "Content-Type": "application/json"},
            json={"prompt": prompt}
        )
        r.raise_for_status()
        data = r.json()
        return data.get("job_id") or data.get("id")  # dopasuj pod API

@retry(stop=stop_after_attempt(10), wait=wait_exponential(multiplier=1, min=1, max=8))
async def _suno_poll_job(job_id: str) -> str:
    """
    TODO: Dopasuj do oficjalnego Suno API.
    Przykład:
      GET {SUNO_API_URL}/v1/result/{job_id}
      -> {"status":"completed","audio_url":"https://.../track.mp3"}
    """
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(f"{SUNO_API_URL}/v1/result/{job_id}",
                             headers={"Authorization": f"Bearer {SUNO_API_KEY}"})
        r.raise_for_status()
        data = r.json()
        status = data.get("status") or data.get("state")
        if status not in ("completed", "ready", "succeeded"):
            raise RuntimeError(f"not ready: {status}")
        return data.get("audio_url") or data.get("url")

async def generate_music_via_suno(prompt: str) -> Optional[str]:
    job_id = await _suno_start_job(prompt)
    audio_url = await _suno_poll_job(job_id)
    if not audio_url:
        return None
    # zapisz lokalnie do /app/music/<hash>.mp3
    key = _music_key(prompt)
    fname = f"{key}.mp3"
    fpath = os.path.join(MUSIC_DIR, fname)
    ok = await _download_to_file(audio_url, fpath)
    if not ok:
        return None
    local_url = f"{PUBLIC_AI_BASE}/music/{fname}"
    _cache_set(f"music:{key}", local_url)
    return local_url

async def get_music_url(prompt: str, deterministic_fallback_name: Optional[str] = None) -> str:
    """
    Zwraca publiczny URL do muzyki:
    - jeśli Suno skonfigurowane i jest cache → zwróć z cache
    - jeśli Suno działa → wygeneruj, zapisz i zwróć
    - inaczej → fallback (np. PUBLIC_AI_BASE/music/track_*.mp3)
    """
    key = _music_key(prompt)
    cached = _cache_get(f"music:{key}")
    if cached:
        return cached

    if SUNO_API_URL and SUNO_API_KEY:
        try:
            url = await generate_music_via_suno(prompt)
            if url:
                return url
        except Exception:
            pass

    # fallback
    if deterministic_fallback_name:
        return f"{PUBLIC_AI_BASE}/music/{deterministic_fallback_name}"
    # ostateczny ratunek
    return f"{PUBLIC_AI_BASE}/music/track_1.mp3"
