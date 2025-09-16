import os, pytest, httpx, json, websockets
from helpers_ws import ws_wait_for

WS_URL    = os.getenv("WS_URL","ws://localhost:65432/ws")
GS_BASE   = os.getenv("GS_BASE","http://localhost:65432")
VISION    = os.getenv("PUBLIC_VISION_BASE","http://localhost:8004")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN","dev_admin_token_123")

@pytest.mark.asyncio
@pytest.mark.sp
async def test_single_player_admin_override_image():
    session = "sp-ov-" + os.urandom(3).hex()
    ws = await websockets.connect(WS_URL)
    await ws.send(json.dumps({"type":"login","player":"Solo","session_id":session,"single_player":True}))
    # domknij turę 1: jedna akcja + bot
    await ws.send(json.dumps({"type":"action","player":"Solo","session_id":session,"turn_id":0,"text_raw":"Sprawdzam miejsce zbrodni"}))
    await ws_wait_for(ws, "narrative_update", timeout=30)

    # override turn 1 obrazem
    new_img = f"{VISION}/assets/images/case_zero/turn2.png"
    r = httpx.post(f"{GS_BASE}/override", headers={"X-Admin-Token":ADMIN_TOKEN},
                   json={"session_id":session,"turn":1,"image":new_img}, timeout=10)
    assert r.status_code == 200
    ov = await ws_wait_for(ws, "override_update", timeout=15)
    assert ov["image"] == new_img
    await ws.close()
