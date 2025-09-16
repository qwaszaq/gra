import os, hashlib, base64
from typing import Optional
import httpx

REDIS_URL = os.getenv("REDIS_URL", "")
PUBLIC_VISION_BASE = os.getenv("PUBLIC_VISION_BASE", "http://localhost:8004")

IMAGE_PROVIDER = os.getenv("IMAGE_PROVIDER","none")   # local | google | banana | none
LOCAL_IMAGE_URL = os.getenv("LOCAL_IMAGE_URL","http://host.docker.internal:8501/generate")

BANANA_API_KEY = os.getenv("BANANA_API_KEY","")
BANANA_URL = os.getenv("BANANA_URL","")
BANANA_MODEL_KEY = os.getenv("BANANA_MODEL_KEY","")

DIFFUSERS_URL = os.getenv("DIFFUSERS_URL","http://image_gen:8502/generate")

GOOGLE_PROJECT = os.getenv("GOOGLE_PROJECT","")
GOOGLE_LOCATION = os.getenv("GOOGLE_LOCATION","us-central1")
GOOGLE_IMAGE_MODEL = os.getenv("GOOGLE_IMAGE_MODEL","imagegeneration@006")
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS","")

IMAGES_DIR = "/app/images/generated"
os.makedirs(IMAGES_DIR, exist_ok=True)

rdb = None
if REDIS_URL:
    try:
        import redis
        rdb = redis.Redis.from_url(REDIS_URL, decode_responses=True)
    except Exception:
        rdb = None

def _img_key(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()

def _cache_get(key: str) -> Optional[str]:
    if not rdb: return None
    try: return rdb.get(key)
    except Exception: return None

def _cache_set(key: str, value: str, ttl=3600):
    if not rdb: return
    try: rdb.set(key, value, ex=ttl)
    except Exception: pass

def _save_png_bytes(b: bytes, key: str) -> str:
    path = os.path.join(IMAGES_DIR, f"{key}.png")
    with open(path, "wb") as f: f.write(b)
    return f"{PUBLIC_VISION_BASE}/assets/images/generated/{key}.png"

def _save_b64_png(b64: str, key: str) -> str:
    import base64
    return _save_png_bytes(base64.b64decode(b64), key)

async def _provider_local(prompt: str) -> Optional[str]:
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(LOCAL_IMAGE_URL, json={"prompt": prompt, "steps": 4, "width": 640, "height": 360})
        r.raise_for_status()
        b64 = r.json().get("image_base64")
        if not b64: return None
        key = _img_key(prompt)
        return _save_b64_png(b64, key)

async def _provider_banana(prompt: str) -> Optional[str]:
    if not (BANANA_API_KEY and BANANA_URL and BANANA_MODEL_KEY): return None
    headers = {"Authorization": f"Bearer {BANANA_API_KEY}", "Content-Type": "application/json"}
    payload = {"modelKey": BANANA_MODEL_KEY, "prompt": prompt}
    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.post(BANANA_URL, headers=headers, json=payload)
        r.raise_for_status()
        data = r.json()

    # Obsłuż dwa warianty odpowiedzi
    b64 = data.get("image_base64") or data.get("image_b64")
    if b64:
        key = _img_key(prompt)
        return _save_b64_png(b64, key)

    url = data.get("image_url")
    if url:
        async with httpx.AsyncClient(timeout=120) as client:
            img = await client.get(url)
            img.raise_for_status()
        key = _img_key(prompt)
        return _save_png_bytes(img.content, key)

    return None

async def _provider_google(prompt: str) -> Optional[str]:
    # Wymaga GOOGLE_APPLICATION_CREDENTIALS (plik JSON SA)
    if not (GOOGLE_PROJECT and GOOGLE_LOCATION and GOOGLE_APPLICATION_CREDENTIALS):
        return None
    try:
        from google.oauth2 import service_account
        from google.auth.transport.requests import Request
    except Exception:
        return None

    scopes = ["https://www.googleapis.com/auth/cloud-platform"]
    creds = service_account.Credentials.from_service_account_file(GOOGLE_APPLICATION_CREDENTIALS, scopes=scopes)
    creds.refresh(Request())
    token = creds.token

    endpoint = f"https://{GOOGLE_LOCATION}-aiplatform.googleapis.com/v1/projects/{GOOGLE_PROJECT}/locations/{GOOGLE_LOCATION}/publishers/google/models/{GOOGLE_IMAGE_MODEL}:generate"
    body = {
        "instances": [
            {
                "prompt": { "text": prompt },
                "image": { "width": 1280, "height": 720 }
            }
        ],
        "parameters": { "sampleCount": 1 }
    }
    headers = {"Authorization": f"Bearer {token}", "Content-Type":"application/json"}

    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.post(endpoint, headers=headers, json=body)
        r.raise_for_status()
        data = r.json()

    # Szukamy base64 w odpowiedzi (różne modele, różne pola)
    b64 = None
    if "predictions" in data:
        pred = data["predictions"][0]
        b64 = pred.get("bytesBase64Encoded") or pred.get("imageBytes") or pred.get("image",{}).get("bytesBase64Encoded")

    if not b64: return None
    key = _img_key(prompt)
    return _save_b64_png(b64, key)

async def _provider_diffusers(prompt: str) -> Optional[str]:
    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.post(DIFFUSERS_URL, json={
            "prompt": prompt,
            "width": int(os.getenv("IMG_GEN_WIDTH","640")),
            "height": int(os.getenv("IMG_GEN_HEIGHT","360")),
            "steps": int(os.getenv("IMG_GEN_STEPS","4"))
        })
        r.raise_for_status()
        data = r.json()
    b64 = data.get("image_base64")
    if not b64: return None
    key = _img_key(prompt)
    return _save_b64_png(b64, key)

async def get_image_url(prompt: str) -> Optional[str]:
    """
    Zwraca publiczny URL PNG (hostowany przez Vision) lub None.
    """
    key = _img_key(prompt)
    cached = _cache_get(f"img:{key}")
    if cached:
        return cached

    url = None
    if IMAGE_PROVIDER == "local":
        url = await _provider_local(prompt)
    elif IMAGE_PROVIDER == "banana":
        url = await _provider_banana(prompt)
    elif IMAGE_PROVIDER == "google":
        url = await _provider_google(prompt)
    elif IMAGE_PROVIDER == "diffusers":
        url = await _provider_diffusers(prompt)
    else:
        url = None

    if url:
        _cache_set(f"img:{key}", url)
    return url