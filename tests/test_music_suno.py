import os, pytest, httpx

AI_BASE = os.getenv("PUBLIC_AI_BASE","http://localhost:8003")

@pytest.mark.suno
def test_suno_music_generation_or_cache():
    if not os.getenv("SUNO_API_KEY"):
        pytest.skip("Suno not configured")
    payload = {
        "game_state": {"session_id":"suno-1", "turn_id":1, "players":["A","B"], "history":[]},
        "actions": {"A":"interrogate","B":"investigate"}
    }
    r = httpx.post(f"{AI_BASE}/orchestrate", json=payload, timeout=60)
    assert r.status_code == 200
    data = r.json()
    assert data.get("music") and data["music"].startswith("http://")
    # plik dostępny
    m = httpx.get(data["music"], timeout=30)
    assert m.status_code == 200
