import httpx, os, pytest

VISION_BASE = os.getenv("PUBLIC_VISION_BASE", "http://localhost:8004")

def test_vision_health_embeddings():
    r = httpx.get(f"{VISION_BASE}/health", timeout=10)
    assert r.status_code == 200
    data = r.json()
    assert "images" in data

def test_vision_match_and_topk_with_scores():
    payload = {"text":"ciemna alejka, świadek w cieniu", "k":3}
    r = httpx.post(f"{VISION_BASE}/match", json={"text":payload["text"]}, timeout=10)
    assert r.status_code == 200
    one = r.json()
    assert "image_url" in one

    r2 = httpx.post(f"{VISION_BASE}/match_topk", json=payload, timeout=10)
    assert r2.status_code == 200
    topk = r2.json()
    assert "images" in topk and len(topk["images"]) >= 1

@pytest.mark.slow
def test_vision_reindex():
    # jeśli endpoint dostępny, wywołaj
    r = httpx.post(f"{VISION_BASE}/reindex", timeout=60)
    assert r.status_code in (200, 404)
