import os, json, asyncio
import httpx
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Body, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from game_state import GameState

app = FastAPI(title="Game Server", version="1.1.0")

# CORS
origins = [os.getenv("WEB_CLIENT_ORIGIN", "http://localhost:5173")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ENV
TTS_URL = os.getenv("TTS_URL", "http://tts_gateway:8001/speak")
ADMIN_URL = os.getenv("ADMIN_URL", "http://admin_service:8002/log")
AI_URL = os.getenv("AI_URL", "http://ai_orchestrator:8003/orchestrate")
AI_BOT_URL = os.getenv("AI_BOT_URL", "http://ai_orchestrator:8003/bot_action")
SUPERVISOR_URL = os.getenv("SUPERVISOR_URL", "http://supervisor_service:8005/validate")

STORY_MODE = os.getenv("STORY_MODE","0") == "1"
STORY_URL  = os.getenv("STORY_URL","http://ai_orchestrator:8003/story_step")
VISION_URL = os.getenv("VISION_URL","http://vision_selector:8004/match")

PUBLIC_TTS_BASE = os.getenv("PUBLIC_TTS_BASE", "http://localhost:8001")
PUBLIC_VISION_BASE = os.getenv("PUBLIC_VISION_BASE", "http://localhost:8004")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")

SCENARIO = os.getenv("SCENARIO", "case_zero")
SCENARIO_PATH = "/app/scenarios/case_zero/scenario.json"

TURN_TIMEOUT_SECONDS = float(os.getenv("TURN_TIMEOUT_SECONDS", "90"))

SINGLE_PLAYER_DEFAULT = os.getenv("SINGLE_PLAYER_DEFAULT", "0") == "1"
BOT_NAME = os.getenv("BOT_NAME", "PartnerBot")
BOT_THINK_MS = int(os.getenv("BOT_THINK_MS", "300"))
BOT_PERSONA = os.getenv("BOT_PERSONA", "ostrożny śledczy")

# Sesje i ich struktury pomocnicze
sessions: dict[str, GameState] = {}
session_locks: dict[str, asyncio.Lock] = {}
turn_timers: dict[str, asyncio.Task] = {}

case_zero_data = None

def load_case_zero():
    global case_zero_data
    try:
        with open(SCENARIO_PATH, "r", encoding="utf-8") as f:
            case_zero_data = json.load(f)
            print(f"[GameServer] Case Zero loaded, turns={len(case_zero_data.get('turns', []))}")
    except Exception as e:
        print(f"[GameServer] WARN: Cannot load scenario {SCENARIO_PATH}: {e}")

def build_public_image(url_or_path: str | None) -> str | None:
    if not url_or_path:
        return None
    if url_or_path.startswith("http://") or url_or_path.startswith("https://"):
        return url_or_path
    return f"{PUBLIC_VISION_BASE}{url_or_path}"

@app.on_event("startup")
async def on_startup():
    if SCENARIO == "case_zero":
        load_case_zero()

@app.get("/health")
def health():
    return {
        "status": "ok",
        "sessions": len(sessions),
        "scenario": SCENARIO,
        "turn_timers": len(turn_timers)
    }

@app.post("/override")
async def override(
    payload: dict = Body(...),
    admin_token: str = Header(default=None, alias="X-Admin-Token")
):
    """
    JSON body (wszystko opcjonalne poza session_id i turn):
    {
      "session_id": "demo-1",
      "turn": 1,
      "image": "http://.../assets/images/...",
      "voice_audio": "http://.../audio/...",
      "music": "http://.../music/...",
      "text": "nowa narracja (opcjonalnie)"
    }
    """
    if ADMIN_TOKEN and admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")

    session_id = payload.get("session_id")
    turn = payload.get("turn")
    if not session_id or turn is None:
        raise HTTPException(status_code=400, detail="session_id and turn required")

    state = sessions.get(session_id)
    if not state:
        # brak sesji – nadal logujemy do Admin i kończymy 200
        state = None

    # zbuduj override payload (tylko pola, które przyszły)
    ov = {
        "type": "override_update",
        "session_id": session_id,
        "turn_id": turn,
        "text": payload.get("text"),
        "image": payload.get("image"),
        "voice_audio": payload.get("voice_audio"),
        "music": payload.get("music"),
    }

    # broadcast tylko jeśli są gracze
    if state and state.players:
        await broadcast(state, ov)

    # log do Admin (jako techniczny log override)
    headers = {"X-Admin-Token": ADMIN_TOKEN} if ADMIN_TOKEN else {}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            await client.post(ADMIN_URL, headers=headers, json={
                "session_id": session_id,
                "turn": int(turn),
                "actions": {"override": True},
                "text": "[override] Admin updated media" + (f" image={payload.get('image')}" if payload.get('image') else ""),
                "image": payload.get("image",""),
                "audio": payload.get("voice_audio","")
            })
    except Exception:
        pass

    return {"status":"ok"}

@app.post("/image_update")
async def image_update(payload: dict = Body(...), admin_token: str = Header(default=None, alias="X-Admin-Token")):
    if ADMIN_TOKEN and admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")
    session_id = payload.get("session_id")
    turn = payload.get("turn")
    image = payload.get("image")
    if not session_id or turn is None or not image:
        raise HTTPException(status_code=400, detail="session_id, turn, image required")
    state = sessions.get(session_id)
    msg = {"type":"image_update", "session_id":session_id, "turn_id":turn, "image": image}
    if state and state.players:
        await broadcast(state, msg)
    return {"status":"ok"}

async def broadcast(state: GameState, payload: dict):
    dead = []
    for name, ws in state.players.items():
        try:
            await ws.send_text(json.dumps(payload))
        except Exception:
            dead.append(name)
    for name in dead:
        state.players.pop(name, None)

async def process_story_step(state, user_text: str, sup_result: dict | None = None):
    print(f"[GameServer] process_story_step: user_text='{user_text}', sup_result={sup_result}")
    # 1) LLM story step (z sup context)
    async with httpx.AsyncClient(timeout=30) as client:
        sr = await client.post(STORY_URL, json={
            "state": state.to_json(),
            "player_input": user_text,
            "supervisor": sup_result or {}
        })
        story = sr.json()

    # 2) TTS
    audio_url = None
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            tts = await client.post(TTS_URL, json={"text": story.get("text",""), "turn_id": state.turn_id, "session_id": state.session_id})
            audio_url = tts.json().get("audio_url")
    except Exception:
        audio_url = None

    # 3) Obraz (Vision /match po vision_query)
    image_url = None
    try:
        vision_query = story.get("vision_query") or story.get("text","")
        print(f"[GameServer] Vision query: {vision_query}")
        async with httpx.AsyncClient(timeout=10) as client:
            mr = await client.post(VISION_URL, json={"text": vision_query})
            image_rel = mr.json().get("image_url")
            print(f"[GameServer] Vision response: {image_rel}")
            image_url = f"{PUBLIC_VISION_BASE}{image_rel}" if image_rel and image_rel.startswith("/assets/") else image_rel
            print(f"[GameServer] Final image_url: {image_url}")
    except Exception as e:
        print(f"[GameServer] Vision error: {e}")
        image_url = None

    # 4) Zapis i broadcast
    state.apply_storystep(story)
    state.apply_narration(story.get("text",""))

    payload = {
        "type":"story_update",
        "session_id": state.session_id,
        "turn_id": state.turn_id,
        "text": story.get("text",""),
        "whispers": story.get("whispers",[]),
        "tags": story.get("tags",{}),
        "shot": story.get("shot"),
        "metrics": state.metrics,
        "metrics_delta": story.get("state_diff",{}).get("metrics_delta",{}),
        "inventory": state.inventory,
        "location": getattr(state, "location", "office"),
        "relations": state.relations,
        "casefile": state.casefile,
        "reframed": story.get("reframed", False),
        "reframed_from": story.get("reframed_from"),
        "reframed_to": story.get("reframed_to"),
        "image": image_url,
        "voice_audio": audio_url,
        "sfx": story.get("sfx_urls", [])
    }
    await broadcast(state, payload)
    state.next_turn()

def missing_players(state: GameState) -> list[str]:
    return [p for p in state.players.keys() if p not in state.actions]

def get_lock(session_id: str) -> asyncio.Lock:
    if session_id not in session_locks:
        session_locks[session_id] = asyncio.Lock()
    return session_locks[session_id]

def cancel_timer(session_id: str):
    task = turn_timers.get(session_id)
    if task and not task.done():
        task.cancel()
    turn_timers.pop(session_id, None)

def ensure_timer(state: GameState):
    # Uruchom timer tylko jeśli: 2 graczy jest w sesji, tura niezamknięta, timer nie istnieje
    if len(state.players) < 2:
        print(f"[GameServer] Timer not started: only {len(state.players)} players")
        return
    if state.session_id in turn_timers and not turn_timers[state.session_id].done():
        print(f"[GameServer] Timer already running for session {state.session_id}")
        return
    print(f"[GameServer] Starting timer for session {state.session_id}, turn {state.turn_id}, timeout {TURN_TIMEOUT_SECONDS}s")
    async def _timeout_task(sid: str, turn_at_start: int):
        try:
            print(f"[GameServer] Timer task started for session {sid}, turn {turn_at_start}")
            print(f"[GameServer] Sleeping for {TURN_TIMEOUT_SECONDS} seconds...")
            await asyncio.sleep(TURN_TIMEOUT_SECONDS)
            print(f"[GameServer] Timer expired for session {sid}, turn {turn_at_start}")
            # Po timeout'cie spróbuj zamknąć turę na locku
            lock = get_lock(sid)
            async with lock:
                cur_state = sessions.get(sid)
                if not cur_state:
                    print(f"[GameServer] Session {sid} no longer exists")
                    return
                print(f"[GameServer] Checking session {sid}: turn {cur_state.turn_id}, players {len(cur_state.players)}, actions {len(cur_state.actions)}")
                # Jeśli tura się nie zmieniła i nadal brakuje akcji -> dopisz "wait"
                if cur_state.turn_id == turn_at_start and len(cur_state.players) >= 2 and len(cur_state.actions) < len(cur_state.players):
                    print(f"[GameServer] Adding wait actions for missing players in session {sid}")
                    for p in missing_players(cur_state):
                        cur_state.actions[p] = "wait"
                    # UWAGA: tu wołamy wersję locked, bo trzymamy lock
                    await process_turn_locked(cur_state)
        except asyncio.CancelledError:
            print(f"[GameServer] Timer cancelled for session {sid}")
            pass
        except Exception as e:
            print(f"[GameServer] Timer error for session {sid}: {e}")
        finally:
            turn_timers.pop(sid, None)
            print(f"[GameServer] Timer task finished for session {sid}")

    task = asyncio.create_task(_timeout_task(state.session_id, state.turn_id))
    turn_timers[state.session_id] = task
    print(f"[GameServer] Created timer task {task} for session {state.session_id}")

def ensure_bot_present(state: GameState):
    if not state.single_player: return
    if state.bot_name and state.bot_name in state.players: return
    state.bot_name = state.bot_name or BOT_NAME
    state.players[state.bot_name] = None

async def maybe_bot_reply(state: GameState, last_human_mapped: str):
    print(f"[GameServer] maybe_bot_reply called: single_player={state.single_player}, bot_name={state.bot_name}")
    if not state.single_player or not state.bot_name: 
        print(f"[GameServer] maybe_bot_reply: not single player or no bot name")
        return
    if state.bot_name in state.actions: 
        print(f"[GameServer] maybe_bot_reply: bot already has action")
        return
    print(f"[GameServer] maybe_bot_reply: bot thinking for {BOT_THINK_MS}ms...")
    if BOT_THINK_MS > 0: await asyncio.sleep(BOT_THINK_MS/1000.0)
    text_suggestion = None
    try:
        print(f"[GameServer] maybe_bot_reply: calling AI_BOT_URL")
        async with httpx.AsyncClient(timeout=10) as client:
            text_suggestion = (await client.post(AI_BOT_URL, json={
                "game_state": state.to_json(), "last_human_action": last_human_mapped,
                "persona": state.bot_persona or BOT_PERSONA, "lang": "pl"
            })).json().get("text")
        print(f"[GameServer] maybe_bot_reply: bot suggested: {text_suggestion}")
    except Exception as e:
        print(f"[GameServer] maybe_bot_reply: AI_BOT_URL failed: {e}")
        text_suggestion = None
    mapped = "wait"
    try:
        print(f"[GameServer] maybe_bot_reply: validating bot action with supervisor")
        async with httpx.AsyncClient(timeout=10) as client:
            val = (await client.post(SUPERVISOR_URL, json={"player": state.bot_name, "input": text_suggestion or "Raportuję do komendanta"})).json()
            if val.get("valid"): mapped = val.get("mapped_action") or "wait"
        print(f"[GameServer] maybe_bot_reply: supervisor mapped to: {mapped}")
    except Exception as e:
        print(f"[GameServer] maybe_bot_reply: supervisor failed: {e}")
        mapped = "wait"
    state.actions[state.bot_name] = mapped
    print(f"[GameServer] maybe_bot_reply: actions={state.actions}, players={list(state.players.keys())}")
    if len(state.actions) == len(state.players):
        print(f"[GameServer] maybe_bot_reply: calling process_turn")
        await process_turn(state)
    else:
        print(f"[GameServer] maybe_bot_reply: not complete yet, waiting")

async def process_turn_locked(state: GameState):
    """
    Wykonuje zamknięcie tury. Zakłada, że lock dla tej sesji JEST już trzymany.
    Nie próbuje łapać locka ponownie.
    """
    print(f"[GameServer] process_turn_locked called for session {state.session_id}: turn {state.turn_id}, players {len(state.players)}, actions {len(state.actions)}")
    
    # jeśli nadal brak kompletu akcji, nic nie rób
    if len(state.players) >= 2 and len(state.actions) != len(state.players):
        print(f"[GameServer] process_turn_locked: not complete yet, returning")
        return

    text = "..."
    image_url = None
    music_url = None

    if SCENARIO == "case_zero" and case_zero_data:
        turn_data = next((t for t in case_zero_data.get("turns", []) if t.get("turn_id") == state.turn_id), None)
        if turn_data:
            text = turn_data.get("narration","...")
            image_url = turn_data.get("image")
            if image_url and image_url.startswith("/assets/"):
                image_url = f"{PUBLIC_VISION_BASE}{image_url}"
        else:
            text = f"Tura {state.turn_id}. Brak danych scenariusza."
    else:
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                res = (await client.post(AI_URL, json={"game_state": state.to_json(), "actions": state.actions})).json()
            text = res.get("narration","...")
            image_url = res.get("image")
            music_url = res.get("music")
        except Exception:
            text = f"Tura {state.turn_id}. Deszcz wciąż pada nad miastem."

    # TTS
    audio_url = None
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            tts = await client.post(TTS_URL, json={"text": text, "turn_id": state.turn_id, "session_id": state.session_id})
            audio_url = tts.json().get("audio_url")
    except Exception:
        audio_url = None

    # Log do Admin
    headers = {"X-Admin-Token": ADMIN_TOKEN} if ADMIN_TOKEN else {}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            await client.post(ADMIN_URL, headers=headers, json={
                "session_id": state.session_id,
                "turn": state.turn_id,
                "actions": state.actions,
                "text": text,
                "image": image_url,
                "audio": audio_url
            })
    except Exception:
        pass

    payload = {
        "type": "narrative_update",
        "session_id": state.session_id,
        "turn_id": state.turn_id,
        "text": text,
        "image": image_url,
        "voice_audio": audio_url,
        "music": music_url
    }
    await broadcast(state, payload)

    # zamknij timer i przejdź do następnej tury
    cancel_timer(state.session_id)
    state.apply_narration(text)
    state.next_turn()


async def process_turn(state: GameState):
    """
    Wrapper: łapie lock i woła process_turn_locked.
    Używaj tej funkcji wszędzie poza timeout taskiem (który sam trzyma lock).
    """
    print(f"[GameServer] process_turn wrapper called for session {state.session_id}")
    lock = get_lock(state.session_id)
    async with lock:
        await process_turn_locked(state)

@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    # oczekuj loginu
    try:
        login = json.loads(await ws.receive_text())
        print(f"[GameServer] Received login: {login}")
    except Exception:
        await ws.send_text(json.dumps({"type":"error","reason":"invalid_login"}))
        await ws.close()
        return

    if login.get("type") != "login":
        print(f"[GameServer] Expected login, got: {login.get('type')}")
        await ws.send_text(json.dumps({"type":"error","reason":"expected_login"}))
        await ws.close()
        return

    player = login.get("player")
    session_id = login.get("session_id", "default")
    if not player:
        await ws.send_text(json.dumps({"type":"error","reason":"missing_player"}))
        await ws.close()
        return

    # init session
    if session_id not in sessions:
        sessions[session_id] = GameState(session_id)
    state = sessions[session_id]

    single_flag = login.get("single_player", None)
    if single_flag is None: single_flag = SINGLE_PLAYER_DEFAULT
    state.single_player = bool(single_flag)
    print(f"[GameServer] Login: player={player}, session_id={session_id}, single_player={state.single_player}")
    state.bot_persona = login.get("bot_style") or state.bot_persona or BOT_PERSONA

    # rejoin -> podmień gniazdo
    if player in state.players:
        state.replace_player_ws(player, ws)
    else:
        state.add_player(player, ws)
    if state.single_player: ensure_bot_present(state)

    await ws.send_text(json.dumps({"type":"info","message":f"joined session {session_id}, turn {state.turn_id}"}))

    try:
        while True:
            raw = await ws.receive_text()
            print(f"[GameServer] Received message from {player}: {raw}")
            try:
                msg = json.loads(raw)
            except Exception as e:
                print(f"[GameServer] JSON parse error: {e}")
                await ws.send_text(json.dumps({"type":"error","reason":"invalid_payload"}))
                continue

            print(f"[GameServer] Parsed message: {msg}")
            if msg.get("type") != "action":
                print(f"[GameServer] Ignoring non-action message: {msg.get('type')}")
                continue

            text_raw = msg.get("text_raw", "")

            # walidacja u Supervisora
            try:
                async with httpx.AsyncClient(timeout=15) as client:
                    vr = await client.post(SUPERVISOR_URL, json={"player": player, "input": text_raw})
                    val = vr.json()
            except Exception:
                await ws.send_text(json.dumps({"type":"error","reason":"supervisor_unavailable"}))
                continue

            # Obsługa link i accuse w Story Mode
            if msg.get("type") == "link" and STORY_MODE and state.single_player:
                from_label = msg.get("from"); to_label = msg.get("to"); relation = msg.get("relation","implies")
                async with httpx.AsyncClient(timeout=15) as client:
                    lr = await client.post("http://ai_orchestrator:8003/link", json={
                        "state": state.to_json(),
                        "from_label": from_label, "to_label": to_label, "relation": relation
                    })
                    delta = lr.json()
                # scal do grafu i wyślij graph_update
                state._cg_merge(delta)
                payload = {"type":"graph_update","session_id": state.session_id,"turn_id": state.turn_id,"graph_delta": delta,"case_graph": state.case_graph}
                await broadcast(state, payload)
                continue

            if msg.get("type") == "accuse" and STORY_MODE and state.single_player:
                suspect_label = msg.get("suspect")
                async with httpx.AsyncClient(timeout=30) as client:
                    ar = await client.post("http://ai_orchestrator:8003/accuse", json={"state": state.to_json(),"suspect_label": suspect_label})
                    result = ar.json()
                # verdict_update (epilog)
                payload = {"type":"verdict_update","session_id": state.session_id,"turn_id": state.turn_id,
                           "verdict": result.get("verdict"), "epilogue": result.get("epilogue"), "sfx": result.get("sfx_urls", [])}
                await broadcast(state, payload)
                continue

            # W Story Mode Single Player - zawsze wywołuj process_story_step (reframe w Orchestrator)
            if STORY_MODE and state.single_player:
                print(f"[GameServer] Calling process_story_step: STORY_MODE={STORY_MODE}, single_player={state.single_player}")
                # użyj oryginalnego text_raw użytkownika jako wejście do sceny
                await process_story_step(state, text_raw, val)  # gdzie val to wynik SUPERVISOR /validate
                continue

            if not val.get("valid"):
                await ws.send_text(json.dumps({"type":"error","reason":val.get("reason","invalid_action")}))
                continue

            mapped = val.get("mapped_action") or "wait"
            state.actions[player] = mapped

            if not state.single_player:
                if len(state.players) < 2:
                    await ws.send_text(json.dumps({"type":"info","message":"Akcja przyjęta (oczekuje na partnera)."}))
                    continue
                if len(state.actions) < len(state.players):
                    ensure_timer(state)
                    await ws.send_text(json.dumps({"type":"info","message":"Akcja przyjęta. Czekamy na drugiego gracza."}))
                    continue
                await process_turn(state); continue

            # single player: bot domyka turę
            await maybe_bot_reply(state, mapped)

    except WebSocketDisconnect:
        # rejoin możliwy
        return