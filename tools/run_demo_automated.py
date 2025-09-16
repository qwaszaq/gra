# tools/run_demo_automated.py
import os, asyncio, json, time, httpx, websockets
from pathlib import Path

ADMIN_BASE = os.getenv("ADMIN_BASE","http://localhost:8002")
VISION_BASE= os.getenv("PUBLIC_VISION_BASE","http://localhost:8004")
TTS_BASE   = os.getenv("PUBLIC_TTS_BASE","http://localhost:8001")
AI_BASE    = os.getenv("PUBLIC_AI_BASE","http://localhost:8003")
GS_BASE    = os.getenv("GS_BASE","http://localhost:65432")
SUP_BASE   = os.getenv("SUP_BASE","http://localhost:8005")
WS_URL     = os.getenv("WS_URL","ws://localhost:65432/ws")
ADMIN_TOKEN= os.getenv("ADMIN_TOKEN","dev_admin_token_123")
WEB_CLIENT = os.getenv("WEB_CLIENT_ORIGIN","http://localhost:5173")

def wait(url: str, timeout=60):
    st=time.time()
    while time.time()-st<timeout:
        try:
            r = httpx.get(url, timeout=3)
            if r.status_code==200: return
        except: pass
        time.sleep(1)
    raise RuntimeError("Service not healthy: "+url)

async def ws_wait_for(ws, msg_type: str, timeout=30):
    while True:
        raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
        data = json.loads(raw)
        if data.get("type")==msg_type:
            return data

async def single_player_demo():
    session = "demo-sp"
    async with websockets.connect(WS_URL) as ws:
        await ws.send(json.dumps({"type":"login","player":"Solo","session_id":session,"single_player":True,"bot_style":"ostrożny śledczy"}))
        await ws.send(json.dumps({"type":"action","player":"Solo","session_id":session,"turn_id":0,"text_raw":"Sprawdzam miejsce zbrodni"}))
        data = await ws_wait_for(ws, "narrative_update", timeout=30)
        print("[SP] Narrative:", data["text"][:80], "...")
        print("[SP] Image:", data.get("image"))
        print("[SP] Voice:", data.get("voice_audio"))
        print("[SP] Music:", data.get("music"))

async def multi_player_demo():
    session = "demo-mp"
    w1 = await websockets.connect(WS_URL)
    w2 = await websockets.connect(WS_URL)
    await w1.send(json.dumps({"type":"login","player":"Marlow","session_id":session}))
    await w2.send(json.dumps({"type":"login","player":"Spade","session_id":session}))
    await w1.send(json.dumps({"type":"action","player":"Marlow","session_id":session,"turn_id":0,"text_raw":"Przesłuchuję świadka"}))
    await w2.send(json.dumps({"type":"action","player":"Spade","session_id":session,"turn_id":0,"text_raw":"Sprawdzam miejsce zbrodni"}))
    data = await ws_wait_for(w1, "narrative_update", timeout=30)
    print("[MP] Narrative:", data["text"][:80], "...")
    print("[MP] Image:", data.get("image"))
    await w1.close(); await w2.close()
    return session

def admin_override(session_id: str, turn: int=1):
    new_img = f"{VISION_BASE}/assets/images/case_zero/turn2.png"
    r = httpx.post(f"{GS_BASE}/override",
                   headers={"X-Admin-Token":ADMIN_TOKEN,"Content-Type":"application/json"},
                   json={"session_id":session_id,"turn":turn,"image":new_img}, timeout=10)
    print("[OVERRIDE]", r.status_code, new_img)

def admin_pdf():
    r = httpx.get(f"{ADMIN_BASE}/report/pdf", headers={"X-Admin-Token":ADMIN_TOKEN}, timeout=30)
    r.raise_for_status()
    Path("Runbook_Demo_Report.pdf").write_bytes(r.content)
    print("[PDF] zapisano Runbook_Demo_Report.pdf")

async def main():
    print("Czekam na health…")
    for url in [f"{VISION_BASE}/health", f"{TTS_BASE}/health", f"{AI_BASE}/health",
                f"{GS_BASE}/health", f"{SUP_BASE}/health", f"{ADMIN_BASE}/health"]:
        wait(url, 60)
    # Single Player tura
    await single_player_demo()
    # Multi Player tura
    sid = await multi_player_demo()
    # Override tury 1 (broadcast)
    admin_override(sid, 1)
    # Raport PDF
    admin_pdf()
    print("DONE – demo przeszło (SP+MP+Override+PDF).")

if __name__ == "__main__":
    asyncio.run(main())
