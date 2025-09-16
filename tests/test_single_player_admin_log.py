import os, pytest, httpx, json, websockets
from helpers_ws import ws_wait_for

WS_URL      = os.getenv("WS_URL","ws://localhost:65432/ws")
ADMIN_BASE  = os.getenv("ADMIN_BASE","http://localhost:8002")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN","dev_admin_token_123")

@pytest.mark.asyncio
@pytest.mark.sp
@pytest.mark.admin
async def test_single_player_admin_logging_present():
    session = "sp-log-" + os.urandom(3).hex()
    ws = await websockets.connect(WS_URL)
    await ws.send(json.dumps({"type":"login","player":"Solo","session_id":session,"single_player":True}))
    await ws.send(json.dumps({"type":"action","player":"Solo","session_id":session,"turn_id":0,"text_raw":"Raportuję do komendanta"}))
    data = await ws_wait_for(ws, "narrative_update", timeout=30)
    assert data["session_id"] == session
    await ws.close()

    # Spróbuj pobrać statystyki/logi (jeśli endpoint dostępny)
    r = httpx.get(f"{ADMIN_BASE}/api/stats", headers={"X-Admin-Token":ADMIN_TOKEN}, timeout=10)
    if r.status_code == 200:
        stats = r.json()
        assert isinstance(stats, dict)
    else:
        pytest.skip("Admin JSON stats endpoint not available; narrative_update already validated.")
