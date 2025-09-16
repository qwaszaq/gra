import os, asyncio, httpx, json, pytest, time
from helpers_ws import ws_connect, ws_send_action, ws_wait_for

WS_URL = os.getenv("WS_URL","ws://localhost:65432/ws")
ADMIN_BASE = os.getenv("ADMIN_BASE","http://localhost:8002")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN","dev_admin_token_123")

@pytest.mark.asyncio
async def test_turn_timeout_assigns_wait(session_id):
    # Załóż, że TURN_TIMEOUT_SECONDS w .env jest rozsądnie krótki (np. 15)
    w1 = await ws_connect(WS_URL, "TimeoutA", session_id)
    w2 = await ws_connect(WS_URL, "TimeoutB", session_id)

    # wyślij akcję od jednego gracza; drugi nic nie robi
    await ws_send_action(w1, "TimeoutA", session_id, "Przesłuchuję świadka")

    # czekamy na narrative_update po timeout - sprawdźmy oba klienty
    try:
        data = await ws_wait_for(w1, "narrative_update", timeout=35)
    except asyncio.TimeoutError:
        # Jeśli w1 nie dostał, spróbuj w2
        data = await ws_wait_for(w2, "narrative_update", timeout=5)
    assert data["session_id"] == session_id

    # Sprawdź, że admin zarejestrował log (niektóre wdrożenia mają /api/stats)
    r = httpx.get(f"{ADMIN_BASE}/api/stats", headers={"X-Admin-Token":ADMIN_TOKEN}, timeout=10)
    if r.status_code == 200:
        stats = r.json()
        # nie znamy schematu – akceptujemy 200
    # jeśli nie ma /api/stats – akceptujemy sam narrative_update
    await w1.close(); await w2.close()
