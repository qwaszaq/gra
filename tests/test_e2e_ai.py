import asyncio, json, os, time, httpx, pytest, websockets

WS_URL = os.getenv("WS_URL","ws://localhost:65432/ws")
GS_HEALTH = "http://localhost:65432/health"
AI_HEALTH = "http://localhost:8003/health"
VIS_HEALTH = "http://localhost:8004/health"

def wait(url, t=30):
    st=time.time()
    while time.time()-st<t:
        try:
            if httpx.get(url, timeout=3).status_code==200: return
        except: pass
        time.sleep(1)
    raise TimeoutError(url)

@pytest.mark.asyncio
async def test_e2e_ai_mode():
    wait(GS_HEALTH,40); wait(AI_HEALTH,40); wait(VIS_HEALTH,40)
    session_id="t-ai"
    async with websockets.connect(WS_URL) as w1, websockets.connect(WS_URL) as w2:
        await w1.send(json.dumps({"type":"login","player":"Marlow","session_id":session_id}))
        await w2.send(json.dumps({"type":"login","player":"Spade","session_id":session_id}))
        await w1.send(json.dumps({"type":"action","player":"Marlow","session_id":session_id,"turn_id":0,"text_raw":"Przesłuchuję świadka"}))
        await w2.send(json.dumps({"type":"action","player":"Spade","session_id":session_id,"turn_id":0,"text_raw":"Sprawdzam miejsce zbrodni"}))

        async def recv_update(ws):
            while True:
                raw = await asyncio.wait_for(ws.recv(), timeout=20)
                d = json.loads(raw)
                if d.get("type")=="narrative_update":
                    return d
        # Wait for narrative_update from either client
        d = await asyncio.wait_for(recv_update(w1), timeout=25)
        assert d["type"]=="narrative_update"
        # AI mode generuje noir narration, nie "Tura X"
        assert len(d["text"]) > 10  # Sprawdź czy jest jakiś tekst
        assert d["image"].startswith("http://")
        if d.get("voice_audio"):
            assert httpx.get(d["voice_audio"], timeout=10).status_code==200
