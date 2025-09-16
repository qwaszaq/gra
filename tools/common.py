# tools/common.py
import os, time, uuid, httpx

ADMIN_BASE = os.getenv("ADMIN_BASE", "http://localhost:8002")
VISION_BASE = os.getenv("PUBLIC_VISION_BASE", "http://localhost:8004")
TTS_BASE = os.getenv("PUBLIC_TTS_BASE", "http://localhost:8001")
AI_BASE = os.getenv("PUBLIC_AI_BASE", "http://localhost:8003")
GS_BASE = os.getenv("GS_BASE", "http://localhost:65432")
SUP_BASE = os.getenv("SUP_BASE", "http://localhost:8005")

LOCAL_IMAGE_URL = os.getenv("LOCAL_IMAGE_URL", "http://host.docker.internal:8501/generate")

ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "dev_admin_token_123")

OUT_IMAGES_DIR = os.getenv("OUT_IMAGES_DIR", "data/images/generated")

def wait_health(url: str, timeout=45):
    start = time.time()
    last = None
    while time.time() - start < timeout:
        try:
            r = httpx.get(url, timeout=5)
            if r.status_code == 200:
                return
        except Exception as e:
            last = e
        time.sleep(1)
    raise RuntimeError(f"Service not healthy: {url} last={last}")

def wait_all():
    for url in [
        f"{VISION_BASE}/health",
        f"{TTS_BASE}/health",
        f"{AI_BASE}/health",
        f"{GS_BASE}/health",
        f"{SUP_BASE}/health",
        f"{ADMIN_BASE}/health",
    ]:
        wait_health(url, 60)

def new_session(prefix="seed"):
    return f"{prefix}-{uuid.uuid4().hex[:6]}"

def admin_headers():
    return {"X-Admin-Token": ADMIN_TOKEN}
