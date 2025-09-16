import os, httpx, pytest

AI_BASE = os.getenv("PUBLIC_AI_BASE","http://localhost:8003")

def _orc_req():
    return {
        "game_state": {"session_id":"ai-e2e", "turn_id":1, "players":["Marlow","Spade"], "history":[]},
        "actions": {"Marlow":"interrogate","Spade":"investigate"}
    }

def test_orchestrator_fallback():
    r = httpx.post(f"{AI_BASE}/orchestrate", json=_orc_req(), timeout=20)
    assert r.status_code == 200
    data = r.json()
    assert "narration" in data and isinstance(data["narration"], str)
    assert data["image"].startswith("http://")
    # music może być Suno lub fallback – sprawdzamy obecność pola
    assert "music" in data

@pytest.mark.llm
def test_orchestrator_with_llm_if_enabled():
    if os.getenv("LLM_ENABLED","0") != "1":
        pytest.skip("LLM not enabled")
    r = httpx.post(f"{AI_BASE}/orchestrate", json=_orc_req(), timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert len(data["narration"]) > 10
