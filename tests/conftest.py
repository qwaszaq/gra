import os
import time
import uuid
import httpx
import pytest

ADMIN_BASE = os.getenv("ADMIN_BASE", "http://localhost:8002")
VISION_BASE = os.getenv("PUBLIC_VISION_BASE", "http://localhost:8004")
TTS_BASE    = os.getenv("PUBLIC_TTS_BASE", "http://localhost:8001")
AI_BASE     = os.getenv("PUBLIC_AI_BASE", "http://localhost:8003")
GS_BASE     = os.getenv("GS_BASE", "http://localhost:65432")
WS_URL      = os.getenv("WS_URL", "ws://localhost:65432/ws")
SUP_BASE    = os.getenv("SUP_BASE", "http://localhost:8005")

ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "dev_admin_token_123")
WEB_CLIENT_ORIGIN = os.getenv("WEB_CLIENT_ORIGIN", "http://localhost:5173")

def wait_health(url: str, timeout=45):
    start = time.time()
    last_err = None
    while time.time() - start < timeout:
        try:
            r = httpx.get(url, timeout=3)
            if r.status_code == 200:
                return
        except Exception as e:
            last_err = e
        time.sleep(1)
    raise RuntimeError(f"Service not healthy: {url} last_err={last_err}")

@pytest.fixture(scope="session", autouse=True)
def wait_all_services():
    # Podnieś wszystkie kluczowe usługi
    wait_health(f"{ADMIN_BASE}/health")
    wait_health(f"{VISION_BASE}/health")
    wait_health(f"{GS_BASE}/health")
    wait_health(f"{TTS_BASE}/health")
    wait_health(f"{SUP_BASE}/health")
    wait_health(f"{AI_BASE}/health")
    return True

@pytest.fixture
def session_id():
    return f"t-{uuid.uuid4().hex[:8]}"

@pytest.fixture
def admin_headers():
    return {"X-Admin-Token": ADMIN_TOKEN}

@pytest.fixture
def origins():
    return [WEB_CLIENT_ORIGIN]
