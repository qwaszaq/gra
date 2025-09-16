import os, asyncio, pytest
from helpers_ws import ws_connect, ws_send_action, ws_wait_for

WS_URL = os.getenv("WS_URL","ws://localhost:65432/ws")

@pytest.mark.asyncio
async def test_two_sessions_isolation():
    s1, s2 = "iso-1", "iso-2"
    a1 = await ws_connect(WS_URL, "A1", s1)
    b1 = await ws_connect(WS_URL, "B1", s1)
    a2 = await ws_connect(WS_URL, "A2", s2)
    b2 = await ws_connect(WS_URL, "B2", s2)

    await ws_send_action(a1, "A1", s1, "Przesłuchuję świadka")
    await ws_send_action(b1, "B1", s1, "Sprawdzam miejsce zbrodni")
    d1 = await ws_wait_for(a1, "narrative_update")

    await ws_send_action(a2, "A2", s2, "Przesłuchuję świadka")
    await ws_send_action(b2, "B2", s2, "Sprawdzam miejsce zbrodni")
    d2 = await ws_wait_for(a2, "narrative_update")

    assert d1["session_id"] == s1
    assert d2["session_id"] == s2

    await a1.close(); await b1.close(); await a2.close(); await b2.close()
