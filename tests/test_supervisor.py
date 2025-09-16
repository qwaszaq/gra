import httpx
import os
import pytest
import time

SUP_BASE = os.getenv("SUP_BASE", "http://localhost:8005")

def test_supervisor_basic_mapping():
    r = httpx.post(f"{SUP_BASE}/validate", json={"player":"Marlow","input":"Przesłuchuję świadka"}, timeout=5)
    assert r.status_code == 200
    data = r.json()
    assert data["valid"] is True
    assert data["mapped_action"] == "interrogate"
    assert data["target"] == "witness"

def test_supervisor_blacklist():
    r = httpx.post(f"{SUP_BASE}/validate", json={"player":"Marlow","input":"Idę na kebab"}, timeout=5)
    assert r.json()["valid"] is False

def test_supervisor_rate_limit():
    # 3 szybkie żądania, ostatnie powinno dostać 429 przy twardym limicie
    ok = 0; err429 = 0
    for _ in range(5):
        r = httpx.post(f"{SUP_BASE}/validate", json={"player":"Rate","input":"Przesłuchuję świadka"}, timeout=5)
        if r.status_code == 429:
            err429 += 1
            break
        ok += 1
        time.sleep(0.05)
    assert err429 >= 1, "rate limit not enforced"
