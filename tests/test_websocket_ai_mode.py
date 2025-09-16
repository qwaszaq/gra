import os, pytest, asyncio
from helpers_ws import ws_connect, ws_send_action, ws_wait_for

WS_URL = os.getenv("WS_URL","ws://localhost:65432/ws")

@pytest.mark.asyncio
@pytest.mark.llm
async def test_ai_mode_ws_if_enabled():
    if os.getenv("LLM_ENABLED","0") != "1":
        pytest.skip("LLM not enabled")
    session = "ws-ai"
    w1 = await ws_connect(WS_URL, "ML1", session)
    w2 = await ws_connect(WS_URL, "ML2", session)
    await ws_send_action(w1, "ML1", session, "Przesłuchuję świadka")
    await ws_send_action(w2, "ML2", session, "Sprawdzam miejsce zbrodni")
    data = await ws_wait_for(w1, "narrative_update")
    assert "Tura" in data["text"] or len(data["text"]) > 10
    await w1.close(); await w2.close()
