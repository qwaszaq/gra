import os, asyncio, httpx, pytest
from helpers_ws import ws_connect, ws_send_action, ws_wait_for

WS_URL = os.getenv("WS_URL","ws://localhost:65432/ws")
GS_BASE = os.getenv("GS_BASE","http://localhost:65432")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN","dev_admin_token_123")
VISION_BASE = os.getenv("PUBLIC_VISION_BASE","http://localhost:8004")

@pytest.mark.asyncio
async def test_admin_override_broadcast(session_id):
    w1 = await ws_connect(WS_URL, "AdminA", session_id)
    w2 = await ws_connect(WS_URL, "AdminB", session_id)
    # Szybka tura, by mieć kontekst tury 1
    await ws_send_action(w1, "AdminA", session_id, "Przesłuchuję świadka")
    await ws_send_action(w2, "AdminB", session_id, "Sprawdzam miejsce zbrodni")
    await ws_wait_for(w1, "narrative_update")

    # override image (turn=1)
    new_img = f"{VISION_BASE}/assets/images/case_zero/turn2.png"
    r = httpx.post(f"{GS_BASE}/override",
                   headers={"X-Admin-Token":ADMIN_TOKEN, "Content-Type":"application/json"},
                   json={"session_id":session_id,"turn":1,"image":new_img}, timeout=10)
    assert r.status_code == 200

    # obaj klienci powinni dostać override_update
    ov1 = await ws_wait_for(w1, "override_update")
    ov2 = await ws_wait_for(w2, "override_update")
    assert ov1["image"] == new_img and ov2["image"] == new_img

    await w1.close(); await w2.close()
