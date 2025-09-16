import os, asyncio, httpx, pytest, json
from helpers_ws import ws_connect, ws_send_action, ws_wait_for

WS_URL = os.getenv("WS_URL","ws://localhost:65432/ws")
ADMIN_BASE = os.getenv("ADMIN_BASE","http://localhost:8002")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN","dev_admin_token_123")

@pytest.mark.asyncio
async def test_case_zero_turn_and_pdf(session_id):
    # zakładamy SCENARIO=case_zero w serwerze
    w1 = await ws_connect(WS_URL, "Marlow", session_id)
    w2 = await ws_connect(WS_URL, "Spade", session_id)
    await ws_send_action(w1, "Marlow", session_id, "Przesłuchuję świadka")
    await ws_send_action(w2, "Spade",  session_id, "Sprawdzam miejsce zbrodni")

    data = await ws_wait_for(w1, "narrative_update")
    assert data["session_id"] == session_id
    assert data["image"].startswith("http://")
    if data.get("voice_audio"):
        assert httpx.get(data["voice_audio"], timeout=10).status_code == 200

    # PDF raport
    r = httpx.get(f"{ADMIN_BASE}/report/pdf", headers={"X-Admin-Token":ADMIN_TOKEN}, timeout=20)
    assert r.status_code == 200
    assert r.headers.get("content-type","").startswith("application/pdf")

    await w1.close(); await w2.close()
