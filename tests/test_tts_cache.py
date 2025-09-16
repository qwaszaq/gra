import httpx, os, re

TTS_BASE = os.getenv("PUBLIC_TTS_BASE", "http://localhost:8001")

def test_tts_cache_hash_filename():
    text = "Deszcz bębni o szyby."
    req = {"text": text, "turn_id": 1, "session_id": "t-cache"}
    r1 = httpx.post(f"{TTS_BASE}/speak", json=req, timeout=15)
    r2 = httpx.post(f"{TTS_BASE}/speak", json=req, timeout=15)
    assert r1.status_code == 200 and r2.status_code == 200
    u1 = r1.json().get("audio_url"); u2 = r2.json().get("audio_url")
    assert u1 == u2
    # plik dostępny
    h = httpx.get(u1, timeout=10)
    assert h.status_code == 200
    assert re.search(r"\.(wav|mp3)$", u1) is not None
