import os, pytest, json, websockets, time
from helpers_ws import ws_wait_for

WS_URL = os.getenv("WS_URL","ws://localhost:65432/ws")

@pytest.mark.asyncio
@pytest.mark.sp
async def test_single_player_no_timer_wait_needed():
    session = "sp-timer-" + os.urandom(3).hex()
    ws = await websockets.connect(WS_URL)
    await ws.send(json.dumps({"type":"login","player":"Solo","session_id":session,"single_player":True}))
    t0 = time.time()
    await ws.send(json.dumps({"type":"action","player":"Solo","session_id":session,"turn_id":0,"text_raw":"Sprawdzam miejsce zbrodni"}))
    data = await ws_wait_for(ws, "narrative_update", timeout=30)
    dt = time.time() - t0
    # powinno domknąć turę znacznie szybciej niż TURN_TIMEOUT_SECONDS (np. < 5s)
    assert dt < 5.0
    await ws.close()
