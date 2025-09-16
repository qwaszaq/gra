import os, pytest, json, websockets
from helpers_ws import ws_wait_for

WS_URL = os.getenv("WS_URL","ws://localhost:65432/ws")

@pytest.mark.asyncio
@pytest.mark.sp
@pytest.mark.llm
async def test_single_player_llm_mode():
    if os.getenv("LLM_ENABLED","0") != "1":
        pytest.skip("LLM not enabled")
    session = "sp-llm-" + os.urandom(3).hex()
    ws = await websockets.connect(WS_URL)
    await ws.send(json.dumps({"type":"login","player":"SoloLLM","session_id":session,"single_player":True,"bot_style":"ostrożny śledczy"}))
    await ws.send(json.dumps({"type":"action","player":"SoloLLM","session_id":session,"turn_id":0,"text_raw":"Przesłuchuję świadka"}))
    data = await ws_wait_for(ws, "narrative_update", timeout=30)
    assert len(data.get("text","")) > 10
    await ws.close()
