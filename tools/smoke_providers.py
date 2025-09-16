# tools/smoke_providers.py
import os, httpx, json

ADMIN_BASE = os.getenv("ADMIN_BASE","http://localhost:8002")
VISION_BASE= os.getenv("PUBLIC_VISION_BASE","http://localhost:8004")
TTS_BASE   = os.getenv("PUBLIC_TTS_BASE","http://localhost:8001")
AI_BASE    = os.getenv("PUBLIC_AI_BASE","http://localhost:8003")

def ok(url):
    r = httpx.get(url, timeout=10)
    assert r.status_code==200, f"Health fail: {url}"

def tts_smoke():
    r = httpx.post(f"{TTS_BASE}/speak", json={"text":"Test noir","turn_id":1,"session_id":"smoke"}, timeout=30)
    r.raise_for_status()
    u = r.json().get("audio_url")
    print("TTS:", u)
    r2 = httpx.get(u, timeout=30)
    assert r2.status_code==200, "TTS file not accessible"

def orchestrate_smoke():
    payload = {"game_state":{"session_id":"smoke","turn_id":1,"players":["A","B"],"history":[]}, "actions":{"A":"investigate","B":"interrogate"}}
    r = httpx.post(f"{AI_BASE}/orchestrate", json=payload, timeout=120)
    r.raise_for_status()
    data = r.json()
    print("IMG:", data.get("image"))
    print("MUSIC:", data.get("music"))
    assert data.get("image","").startswith("http"), "Image URL missing"
    assert data.get("music","").startswith("http"), "Music URL missing"

def vision_list():
    r = httpx.get(f"{VISION_BASE}/list?collection=generated", timeout=10)
    r.raise_for_status()
    data = r.json()
    print("Generated:", len(data.get("images",[])))

if __name__ == "__main__":
    ok(f"{ADMIN_BASE}/health"); ok(f"{VISION_BASE}/health"); ok(f"{TTS_BASE}/health"); ok(f"{AI_BASE}/health")
    tts_smoke()
    orchestrate_smoke()
    vision_list()
    print("SMOKE OK")
