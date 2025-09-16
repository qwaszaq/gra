import asyncio
import json
import websockets

async def ws_connect(url: str, player: str, session_id: str):
    ws = await websockets.connect(url)
    await ws.send(json.dumps({"type":"login","player":player,"session_id":session_id}))
    return ws

async def ws_connect_login(url: str, login_payload: dict):
    ws = await websockets.connect(url)
    await ws.send(json.dumps(login_payload))
    return ws

async def ws_send_action(ws, player: str, session_id: str, text: str):
    await ws.send(json.dumps({"type":"action","player":player,"session_id":session_id,"turn_id":0,"text_raw":text}))

async def ws_wait_for(ws, msg_type: str, timeout=30):
    while True:
        raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
        data = json.loads(raw)
        if data.get("type") == msg_type:
            return data
