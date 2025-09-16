import os, pytest, json, websockets
from helpers_ws import ws_wait_for

WS_URL = os.getenv("WS_URL","ws://localhost:65432/ws")

@pytest.mark.asyncio
@pytest.mark.sp
async def test_single_player_llm_bot_basic():
    session = "sp-" + os.urandom(3).hex()
    ws = await websockets.connect(WS_URL)
    # login z single_player
    await ws.send(json.dumps({"type":"login","player":"Solo","session_id":session,"single_player":True,"bot_style":"ostrożny śledczy"}))
    # jedna akcja – bot powinien domknąć turę
    await ws.send(json.dumps({"type":"action","player":"Solo","session_id":session,"turn_id":0,"text_raw":"Przesłuchuję świadka"}))
    data = await ws_wait_for(ws, "narrative_update", timeout=30)
    assert data["session_id"] == session
    assert isinstance(data.get("text",""), str) and len(data["text"]) > 0
    assert "turn_id" in data
    await ws.close()
