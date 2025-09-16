import httpx
import os
import pytest

ADMIN_BASE = os.getenv("ADMIN_BASE", "http://localhost:8002")
VISION_BASE = os.getenv("PUBLIC_VISION_BASE", "http://localhost:8004")
TTS_BASE    = os.getenv("PUBLIC_TTS_BASE", "http://localhost:8001")
AI_BASE     = os.getenv("PUBLIC_AI_BASE", "http://localhost:8003")
GS_BASE     = os.getenv("GS_BASE", "http://localhost:65432")
SUP_BASE    = os.getenv("SUP_BASE", "http://localhost:8005")
WEB_CLIENT_ORIGIN = os.getenv("WEB_CLIENT_ORIGIN", "http://localhost:5173")

def _check_health(url):
    r = httpx.get(url, timeout=5)
    assert r.status_code == 200
    return r.json() if r.headers.get("content-type","").startswith("application/json") else {}

@pytest.mark.cors
def test_health_and_cors_headers():
    for url in [f"{ADMIN_BASE}/health", f"{VISION_BASE}/health", f"{TTS_BASE}/health", f"{AI_BASE}/health", f"{GS_BASE}/health", f"{SUP_BASE}/health"]:
        _check_health(url)
        # Preflight OPTIONS
        r = httpx.options(url, headers={
            "Origin": WEB_CLIENT_ORIGIN,
            "Access-Control-Request-Method": "GET"
        }, timeout=5)
        assert r.status_code in (200, 204), f"OPTIONS failed for {url}"
