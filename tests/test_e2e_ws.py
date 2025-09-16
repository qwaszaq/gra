import asyncio
import json
import os
import time

import httpx
import pytest
import websockets

WS_URL = os.getenv("WS_URL", "ws://localhost:65432/ws")
ADMIN_HEALTH = os.getenv("ADMIN_HEALTH", "http://localhost:8002/health")
SUP_HEALTH = os.getenv("SUP_HEALTH", "http://localhost:8005/health")
VIS_HEALTH = os.getenv("VIS_HEALTH", "http://localhost:8004/health")
GS_HEALTH  = os.getenv("GS_HEALTH",  "http://localhost:65432/health")

def wait_for_health(url: str, timeout=30):
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = httpx.get(url, timeout=3)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(1)
    raise TimeoutError(f"Service not healthy: {url}")

@pytest.mark.asyncio
async def test_e2e_case_zero_turn():
    # 1) poczekaj na serwisy
    wait_for_health(ADMIN_HEALTH, 45)
    wait_for_health(SUP_HEALTH, 45)
    wait_for_health(VIS_HEALTH, 45)
    wait_for_health(GS_HEALTH, 45)

    # 2) połącz 2 klientów
    session_id = "t-e2e"
    async with websockets.connect(WS_URL) as w1, websockets.connect(WS_URL) as w2:
        await w1.send(json.dumps({"type":"login","player":"Marlow","session_id":session_id}))
        await w2.send(json.dumps({"type":"login","player":"Spade","session_id":session_id}))

        # 3) wyślij akcje
        await w1.send(json.dumps({"type":"action","player":"Marlow","session_id":session_id,"turn_id":0,"text_raw":"Przesłuchuję świadka"}))
        await w2.send(json.dumps({"type":"action","player":"Spade" ,"session_id":session_id,"turn_id":0,"text_raw":"Sprawdzam miejsce zbrodni"}))

        # 4) odbierz narrative_update (z timeoutem)
        async def recv_update(ws):
            while True:
                raw = await asyncio.wait_for(ws.recv(), timeout=15)
                data = json.loads(raw)
                if data.get("type") == "narrative_update":
                    return data

        # Wait for narrative_update from either client
        data = await asyncio.wait_for(recv_update(w1), timeout=20)

        # 5) asercje kontraktu
        assert data["type"] == "narrative_update"
        assert data["session_id"] == session_id
        assert isinstance(data["turn_id"], int)
        assert isinstance(data["text"], str) and len(data["text"]) > 0
        assert "image" in data
        assert "voice_audio" in data

        # 6) sprawdź dostępność mediów
        if data.get("image"):
            r = httpx.get(data["image"], timeout=10)
            assert r.status_code == 200
        if data.get("voice_audio"):
            r = httpx.get(data["voice_audio"], timeout=10)
            assert r.status_code == 200
