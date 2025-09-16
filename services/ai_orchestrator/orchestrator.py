from fastapi import FastAPI, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import os, httpx, hashlib, re, json, asyncio
from fastapi.staticfiles import StaticFiles

from llm_client import generate_narrative_llm, generate_text_llm  # NEW
from audio_client import get_music_url  # NEW
from image_client import get_image_url   # NEW
from shot_planner import plan_shot  # NEW
import asyncio

# SFX configuration
ENABLE_SFX = os.getenv("ENABLE_SFX","0") == "1"
SFX_BASE = os.getenv("SFX_BASE","http://localhost:8003/sfx")
SFX_CONFIG_PATH = os.getenv("SFX_CONFIG_PATH","/app/config/sfx.json")

_sfx_map = {}
try:
    with open(SFX_CONFIG_PATH,"r",encoding="utf-8") as f:
        _sfx_map = json.load(f)
except Exception as e:
    print("[Orchestrator] WARN sfx map:", e)

def map_sfx_keys(keys: List[str]) -> List[str]:
    out = []
    for k in keys or []:
        fn = _sfx_map.get(k)
        if not fn: continue
        out.append(f"{SFX_BASE}/{fn}")
    return out

async def _reframe_input_to_noir(state: dict, user_text: str, suggestion: str = "") -> str:
    """
    Prosi LLM o reinterpretację inputu na zgodny z domeną noir zamiar/komendę (krótkie zdanie).
    """
    if not LLM_ENABLED:
        # heurystyczny fallback
        return "Przesłuchuję świadka w ciemnej alejce."
    prompt = (
        "Zinterpretuj poniższy tekst użytkownika tak, aby pasował do sceny detektywistycznej noir. "
        "Zwróć JEDNĄ krótką komendę po polsku, np.: 'Przesłuchuję świadka', 'Sprawdzam miejsce zbrodni', 'Idę na posterunek', 'Raportuję do komendanta'.\n"
        f"Input: {user_text}\n"
        f"Wskazówka: {suggestion or 'intencje: investigate/interrogate/move/report'}"
    )
    try:
        txt = await generate_text_llm(prompt)
        line = txt.split("\n")[0].split(".")[0].strip()
        if len(line) < 4:
            return "Sprawdzam miejsce zbrodni"
        return line
    except Exception:
        return "Sprawdzam miejsce zbrodni"

app = FastAPI(title="AI Orchestrator", version="1.2.0")

# CORS
origins = [os.getenv("WEB_CLIENT_ORIGIN", "http://localhost:5173")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# serwuj statycznie SFX (pliki w /app/sfx)
if os.path.isdir("/app/sfx"):
    app.mount("/sfx", StaticFiles(directory="/app/sfx"), name="sfx")

# Bardzo prosty „store" grafów (na MVP w pamięci procesu)
_GRAPH: Dict[str, Dict[str, Any]] = {}  # session_id -> {"nodes":[], "edges":[]}

def _graph_get(sid: str) -> Dict[str, Any]:
    g = _GRAPH.get(sid)
    if not g:
        g = {"nodes": [], "edges": []}  # nodes: {id,type,label}, edges:{from,to,label,confidence}
        _GRAPH[sid] = g
    return g

def _node_id(label: str) -> str:
    return hashlib.sha1(label.strip().lower().encode("utf-8")).hexdigest()[:10]

def _ensure_node(g: Dict[str,Any], node_type: str, label: str) -> Dict[str,Any]:
    nid = _node_id(label)
    for n in g["nodes"]:
        if n["id"] == nid:
            return n
    n = {"id": nid, "type": node_type, "label": label}
    g["nodes"].append(n)
    return n

def _add_edge(g: Dict[str,Any], src: str, dst: str, label: str, confidence: float = 0.6) -> Dict[str,Any]:
    e = {"from": src, "to": dst, "label": label, "confidence": float(confidence)}
    g["edges"].append(e)
    return e

PUBLIC_VISION_BASE = os.getenv("PUBLIC_VISION_BASE", "http://localhost:8004")
VISION_URL = os.getenv("VISION_URL", "http://vision_selector:8004/match")
TTS_URL = os.getenv("TTS_URL", "http://tts_service:8001/speak")
REDIS_URL = os.getenv("REDIS_URL", "")
MUSIC_BASE = os.getenv("PUBLIC_AI_BASE", "http://localhost:8003")
MUSIC_DIR = "/app/music"
LLM_ENABLED = os.getenv("LLM_ENABLED", "0") == "1"

GS_INTERNAL_BASE = os.getenv("GS_INTERNAL_BASE","http://game_server:65432")
ENABLE_BG_IMAGE_SWAP = os.getenv("ENABLE_BG_IMAGE_SWAP","0") == "1"

# Prosty cache (opcjonalny Redis)
rdb = None
if REDIS_URL:
    try:
        import redis
        rdb = redis.Redis.from_url(REDIS_URL, decode_responses=True)
    except Exception:
        rdb = None

# Jeżeli nie masz realnych plików, możesz wstawić placeholdery .wav/.mp3 do data/music i zamapować w compose
def pick_music_key(session_id: str, turn_id: int) -> str:
    h = int(hashlib.sha256(f"{session_id}:{turn_id}".encode()).hexdigest(), 16)
    return f"track_{(h % 5) + 1}.mp3"

def build_music_prompt(gs: dict, actions: dict, narration: str) -> str:
    turn = gs.get("turn_id", 0)
    # Prompt muzyczny pod noir; możesz dopasować tempo i instrumentarium
    return (
        f"Noir dark jazz, rain ambience, slow tempo ~70bpm, double bass, saxophone, vinyl crackle, "
        f"moody, cinematic, minimal, scene turn {turn}. "
        f"Story cue: {narration[:140]}"
    )

class OrchestrateReq(BaseModel):
    game_state: dict
    actions: dict

class BotReq(BaseModel):
    game_state: dict
    last_human_action: str

class WorldState(BaseModel):
    turn_id: int
    session_id: str
    history: List[Dict[str, Any]] = []
    metrics: Dict[str, int] = {"time": 20, "suspicion": 0, "reputation": 0}
    casefile: Dict[str, Any] = {"clues": [], "suspects": []}
    inventory: Dict[str, Any] = {"pistol_loaded": False, "ammo": 0, "cigarettes": 0, "matches": 0}
    location: str = "office"

class StoryReq(BaseModel):
    state: Dict[str, Any]           # bieżący stan świata
    player_input: str               # dowolny, NL
    supervisor: Optional[Dict[str, Any]] = None  # adnotacje domeny (opcjonalnie)

class LinkReq(BaseModel):
    state: Dict[str,Any]
    from_label: str
    to_label: str
    relation: str = "implies"  # implies|contradicts|found_at|seen_with

class AccuseReq(BaseModel):
    state: Dict[str,Any]
    suspect_label: str

def _nl_story_prompt(state: dict, user_text: str) -> str:
    """
    Prośba do LLM: zinterpretuj naturalny język użytkownika, odegraj scenę (60–120 słów)
    i zwróć ustrukturyzowany diff stanu. Unikaj proceduralnych instrukcji – opowiadaj skutki,
    emocje, decyzje i konsekwencje. Styl: Sin City / Max Payne / Disco Elysium.
    """
    turn = state.get("turn_id", 1)
    hist = state.get("history", [])[-2:]
    recap = " | ".join([h.get("text","")[:160] for h in hist]) or "Brak."
    inv = state.get("inventory", {})
    loc = state.get("location", "office")

    return (
        "Napisz scenę noir po polsku (60–120 słów) w pierwszej lub trzeciej osobie, styl: Sin City/Max Payne/Disco Elysium.\n"
        "Nie podawaj porad technicznych ani instrukcji jak coś wykonać; skutek i nastrój są ważniejsze niż procedura.\n"
        "Zinterpretuj intencję gracza naturalnie w świecie gry.\n"
        f"Tura: {turn}\n"
        f"Lokalizacja: {loc}\n"
        f"Ostatnie zdarzenia: {recap}\n"
        f"Wejście gracza: {user_text}\n\n"
        "Zwróć wyłącznie JSON wg schematu:\n"
        "{\n"
        "  \"text\": \"…\",                       // opis sceny\n"
        "  \"whispers\": [\"Logika: …\", \"Empatia: …\", \"Cynizm: …\"],\n"
        "  \"tags\": {\"location\":\"alley|office|crime_scene|bar|tenement|rooftop|street\","
        "\"action\":\"freeform\",\"mood\":\"tense|melancholic|threatening|hollow|frantic\",\"motif\":\"red_neon|red_blood|red_lipstick|red_file\",\"subject\":\"witness|suspect|victim|detective\",\"time\":\"night_rain|dawn_fog\"},\n"
        "  \"state_diff\": {\n"
        "     \"metrics_delta\": {\"time\": -1, \"suspicion\": 0, \"reputation\": 0},\n"
        "     \"location\": \"(opcjonalnie nowa lokacja)\",\n"
        "     \"inventory\": {\"pistol_loaded\": true|false, \"ammo_delta\": 0, \"cigarettes_delta\": 0},\n"
        "     \"casefile\": {\"clues_add\": [], \"suspects_upd\": []}\n"
        "  },\n"
        "  \"relations_delta\": [  // zmiany relacji NPC\n"
        "    {\"name\":\"Komendant\",\"mood_delta\":+0,\"trust_delta\":+0,\"fear_delta\":+0}\n"
        "  ],\n"
        "  \"sfx\": [\"reload\",\"lighter\",\"rain\"],  // wybierz tylko z listy\n"
        "  \"image_hint\": \"krótki obiekt związany ze sceną\"\n"
        "}\n"
    )

def _detect_action_from_text(text: str) -> str:
    """Rozpoznaj akcję z tekstu użytkownika"""
    t = text.lower()
    if any(k in t for k in ["jadę", "idę", "udaję się", "przemieszczam", "wracam", "jade", "ide"]):
        return "move"
    elif any(k in t for k in ["przesłuchuję", "pytam", "wypytuję", "rozmawiam"]):
        return "interrogate"
    elif any(k in t for k in ["zbadaj", "sprawdzam", "sprawdz", "oglądam", "przeszukuję"]):
        return "investigate"
    elif any(k in t for k in ["raportuję", "meldunek", "zgłaszam", "raport"]):
        return "report"
    else:
        return "freeform"

def _infer_graph_delta_from_story(sid: str, data: dict) -> dict:
    """MVP: jeśli tags.subject == witness/suspect -> dodaj węzeł; jeśli image_hint wygląda na obiekt -> clue"""
    g = _graph_get(sid)
    nodes_add, edges_add = [], []
    subj = (data.get("tags") or {}).get("subject")
    if subj in ("witness","suspect"):
        n = _ensure_node(g, "suspect" if subj=="suspect" else "witness", subj.capitalize())
        nodes_add.append(n)
    hint = data.get("image_hint") or ""
    if hint:
        n = _ensure_node(g, "clue", hint)
        nodes_add.append(n)
    # relacja luźna: witness ↔ clue (implies)
    if len(nodes_add) >= 2:
        s = nodes_add[0]["id"]; t = nodes_add[1]["id"]
        e = _add_edge(g, s, t, "implies", 0.55)
        edges_add.append(e)
    return {"nodes_add": nodes_add, "edges_add": edges_add}

def _story_from_raw_json(raw: str, fallback_text: str) -> dict:
    m = re.search(r"\{.*\}", raw, re.S)
    try:
        data = json.loads(m.group(0)) if m else {}
    except Exception:
        data = {}
    if "text" not in data:
        # Rozpoznaj akcję z tekstu
        detected_action = _detect_action_from_text(fallback_text)
        detected_location = "street" if detected_action == "move" else "office"
        
        data = {
            "text": fallback_text,
            "whispers": ["Logika: Zachowaj spokój.", "Empatia: Zauważ szczegóły.", "Cynizm: Sprawdź tył wyjścia."],
            "tags": {"location":detected_location,"action":detected_action,"mood":"tense","motif":"red_neon","subject":"detective","time":"night_rain"},
            "state_diff": {"metrics_delta":{"time":-1,"suspicion":0,"reputation":0}},
            "relations_delta": [],
            "sfx": [],
            "image_hint":"okno z kroplami"
        }
    # sanity defaults
    data.setdefault("whispers", [])
    data.setdefault("tags", {})
    data.setdefault("state_diff", {"metrics_delta":{"time":-1,"suspicion":0,"reputation":0}})
    data.setdefault("relations_delta", [])
    data.setdefault("sfx", [])
    return data

def _bot_fallback(last: str | None) -> str:
    if last == "interrogate": return "Sprawdzam miejsce zbrodni"
    if last == "investigate": return "Przesłuchuję świadka"
    if last == "move":        return "Raportuję do komendanta"
    return "Idę na posterunek"

def _story_fallback(state: dict, user_text: str) -> dict:
    turn = state.get("turn_id", 1)
    text = (
        f"Tura {turn}. Deszcz zasłania miasto jak kiepskie alibi. "
        f"{user_text.strip().capitalize()}. Światło lampy drży na mokrym asfalcie."
    )
    whispers = [
        "Logika: Przeszukaj miejsce — szczegóły nie kłamią.",
        "Empatia: Zadaj delikatne pytanie — ktoś tu pęknie.",
        "Cynizm: Sprawdź tylne drzwi — zawsze są uchylone."
    ]
    tags = {"location":"alley","action":"investigate","mood":"tense","motif":"red_neon","subject":"witness","time":"night_rain"}
    metrics_delta = {"time": -1, "suspicion": 0, "reputation": 0}
    casefile = {"clues_add": [], "suspects_upd": []}
    return {
        "text": text, "whispers": whispers, "tags": tags,
        "metrics_delta": metrics_delta, "casefile": casefile
    }

def _build_story_prompt(state: dict, user_text: str) -> str:
    turn = state.get("turn_id", 1)
    # krótki recap 2 ostatnich wpisów historii:
    hist = state.get("history", [])[-2:]
    recap = " | ".join([h.get("text","")[:120] for h in hist]) or "Brak."
    return (
        "Napisz scenę noir po polsku (60–120 słów), styl: Sin City/Max Payne/Disco Elysium.\n"
        f"Tura: {turn}\n"
        f"Ostatnie zdarzenia: {recap}\n"
        f"Wejście gracza (intencja): {user_text}\n"
        "Zwróć wyłącznie JSON bez komentarzy wg kluczy:\n"
        "{\n"
        "  \"text\": \"…\",\n"
        "  \"whispers\": [\"Logika: …\", \"Empatia: …\", \"Cynizm: …\"],\n"
        "  \"tags\": {\"location\":\"alley|office|crime_scene|bar|tenement|rooftop|street\","
        "\"action\":\"investigate|interrogate|connect|follow|report\",\"mood\":\"tense|melancholic|threatening|hollow|frantic\","
        "\"motif\":\"red_neon|red_blood|red_lipstick|red_file\",\"subject\":\"witness|suspect|victim|detective\",\"time\":\"night_rain|dawn_fog\"},\n"
        "  \"metrics_delta\": {\"time\":-1, \"suspicion\":0, \"reputation\":0},\n"
        "  \"casefile\": {\"clues_add\":[], \"suspects_upd\":[]}\n"
        "}\n"
    )

async def _bg_generate_and_push(session_id: str, turn_id: int, prompt_text: str, provider_prompt: str | None = None):
    try:
        use_prompt = provider_prompt or prompt_text
        url = await get_image_url(use_prompt)
        if not url: return
        async with httpx.AsyncClient(timeout=30) as client:
            await client.post(f"{GS_INTERNAL_BASE}/image_update",
                              headers={"X-Admin-Token": os.getenv("ADMIN_TOKEN","")},
                              json={"session_id": session_id, "turn": turn_id, "image": url})
        print(f"[Orchestrator] BG image pushed for {session_id}/t{turn_id}")
    except Exception as e:
        print("[Orchestrator] bg_generate_and_push error:", e)

@app.get("/health")
def health():
    return {"status": "ok", "llm_enabled": LLM_ENABLED}

# DEMO manifest
DEMO_MODE = os.getenv("DEMO_MODE","0") == "1"
DEMO_ASSETS_PATH = os.getenv("DEMO_ASSETS_PATH","/app/demo_assets/manifest.json")
demo_assets = None
if DEMO_MODE:
    try:
        import json
        with open(DEMO_ASSETS_PATH,"r",encoding="utf-8") as f:
            demo_assets = json.load(f)
        print("[Orchestrator] DEMO_MODE ON")
    except Exception as e:
        print("[Orchestrator] DEMO manifest load failed:", e)

def _pick_demo_image(narration: str) -> str | None:
    if not demo_assets: 
        print(f"[DEBUG] No demo_assets available")
        return None
    text = narration.lower()
    cats = demo_assets.get("images",{})
    print(f"[DEBUG] Narration: {text[:100]}...")
    
    # Rozszerzone słowa kluczowe dla lepszego dopasowania
    # Priorytet: crime_scene > chief_office > alley > fallback
    if ("miejsce zbrodni" in text or "krew" in text or "dowód" in text or 
        "sprawdzam" in text or "zbrodni" in text or "ślad" in text or "ciało" in text or
        "mężczyzna" in text or "fotografia" in text or "ból" in text):
        pool = cats.get("crime_scene") or []
        print(f"[DEBUG] Using crime_scene pool: {pool}")
    elif "komendant" in text or "chief" in text or "raport" in text or "biuro" in text:
        pool = cats.get("chief_office") or []
        print(f"[DEBUG] Using chief_office pool: {pool}")
    elif "alejk" in text or "ulic" in text or "ciem" in text or "deszcz" in text or "neon" in text:
        pool = cats.get("alley") or []
        print(f"[DEBUG] Using alley pool: {pool}")
    else:
        pool = cats.get("fallback") or []
        print(f"[DEBUG] Using fallback pool: {pool}")
    
    if not pool: return None
    import hashlib
    i = int(hashlib.sha256(narration.encode()).hexdigest(),16) % len(pool)
    result = pool[i]
    print(f"[DEBUG] Selected image: {result}")
    return result

def build_narration_fallback(game_state: dict, actions: dict) -> str:
    turn = game_state.get("turn_id", 0)
    players = game_state.get("players", [])
    acts = ", ".join(f"{p}:{actions.get(p)}" for p in players if p in actions)
    base = [
        "Deszcz bębni o szyby, światło ulic trzęsie się jak zeznania świadka.",
        "Miasto oddycha ciężko, jakby coś przygniotło mu klatkę piersiową.",
        "Dym z papierosa tnie powietrze – ktoś kłamie, ktoś milczy.",
    ]
    mood = base[turn % len(base)]
    return f"Tura {turn}. Działania: {acts}. {mood}"

def cache_get(key: str) -> dict | None:
    if not rdb:
        return None
    try:
        raw = rdb.get(key)
        if raw:
            import json
            return json.loads(raw)
    except Exception:
        return None

def cache_set(key: str, value: dict, ttl=900):
    if not rdb:
        return
    try:
        import json
        rdb.set(key, json.dumps(value), ex=ttl)
    except Exception:
        pass

@app.post("/bot_action")
async def bot_action(req: BotReq):
    turn = req.game_state.get("turn_id", 0)
    persona = req.persona or "ostrożny śledczy"
    if LLM_ENABLED:
        try:
            prompt = (
                f"Rola: {persona}. Tura {turn}. Ostatnia akcja człowieka: {req.last_human_action or 'brak'}.\n"
                "Zaproponuj JEDNĄ krótką komendę czynności śledczej po polsku z allowed actions "
                "(investigate/interrogate/move/report). Tylko komenda."
            )
            text = await generate_text_llm(prompt)
            text = text.split("\n")[0].split(".")[0].strip()
            if len(text) < 4: text = _bot_fallback(req.last_human_action)
            return {"text": text}
        except Exception:
            pass
    return {"text": _bot_fallback(req.last_human_action)}

@app.post("/orchestrate")
async def orchestrate(req: OrchestrateReq):
    gs = req.game_state
    actions = req.actions
    session_id = gs.get("session_id", "default")
    turn_id = gs.get("turn_id", 0)

    # klucz cache
    cache_key = f"orc:{session_id}:{turn_id}:{hashlib.sha256(str(actions).encode('utf-8')).hexdigest()}"
    cached = cache_get(cache_key)
    if cached:
        return cached

    # 1) Narracja
    if LLM_ENABLED:
        try:
            print(f"[DEBUG] Attempting LLM generation for session {session_id}, turn {turn_id}")
            narration = await generate_narrative_llm(gs, actions)
            print(f"[DEBUG] LLM generated narration: {narration[:100]}...")
        except Exception as e:
            print(f"[DEBUG] LLM failed, using fallback: {e}")
            narration = build_narration_fallback(gs, actions)
    else:
        print(f"[DEBUG] LLM disabled, using fallback")
        narration = build_narration_fallback(gs, actions)

    # 2) Obraz: provider → Vision fallback → placeholder
    image_url = None
    
    # Najpierw spróbuj real provider (Google/Banana/Local)
    try:
        image_url = await get_image_url(narration)
        if image_url:
            print(f"[Orchestrator] image provider OK: {image_url}")
    except Exception as e:
        print(f"[Orchestrator] provider error: {e}")

    # Jeśli nie ma providera, spróbuj Vision /match
    if not image_url:
        image_rel = "/assets/images/placeholder.png"
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.post(VISION_URL, json={"text": narration})
                image_rel = r.json().get("image_url", image_rel)
            print(f"[Orchestrator] Vision fallback: {image_rel}")
        except Exception as e:
            print(f"[Orchestrator] vision fallback error: {e}")
        image_url = f"{PUBLIC_VISION_BASE}{image_rel}" if image_rel.startswith("/assets/") else image_rel

    # 3) TTS przez TTS Gateway
    voice_audio = None
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            tts_req = {"text": narration, "turn_id": turn_id, "session_id": session_id}
            r = await client.post(TTS_URL, json=tts_req)
            if r.status_code == 200:
                voice_audio = r.json().get("audio_url")
                print(f"[DEBUG] TTS generated: {voice_audio}")
    except Exception as e:
        print(f"[DEBUG] TTS failed: {e}")

    # 4) Muzyka przez Suno + cache; fallback do deterministycznego tracka
    fallback_name = pick_music_key(session_id, turn_id)  # np. track_1.mp3
    music_prompt = build_music_prompt(gs, actions, narration)
    music_url = await get_music_url(music_prompt, deterministic_fallback_name=fallback_name)

    resp = {"narration": narration, "image": image_url, "music": music_url}
    if voice_audio:
        resp["voice_audio"] = voice_audio
    cache_set(cache_key, resp)
    return resp

@app.post("/story_step")
async def story_step(req: StoryReq):
    """
    Story Engine v2: Free-form NL actions & state diff
    Zwraca: text (scena), whispers, tags, state_diff (inventory/location/metrics/casefile)
    """
    state = req.state
    user_input = req.player_input
    sup = req.supervisor or {}
    reframed = False; reframed_from = None

    if (not sup.get("valid")) and sup.get("reason") in ("out_of_domain","profanity","unrecognized_intent"):
        reframed_from = user_input
        user_input = await _reframe_input_to_noir(state, user_input, sup.get("suggestion",""))
        reframed = True

    if LLM_ENABLED:
        try:
            prompt = _nl_story_prompt(state, user_input)
            raw = await generate_text_llm(prompt)
            data = _story_from_raw_json(raw, f"{user_input.strip().capitalize()}. Deszcz skrywa miasto jak brudne sumienie.")
        except Exception as e:
            print("[/story_step] LLM err:", e)
            data = _story_from_raw_json("", f"{user_input.strip().capitalize()}. Deszcz skrywa miasto jak brudne sumienie.")
    else:
        data = _story_from_raw_json("", f"{user_input.strip().capitalize()}. Deszcz skrywa miasto jak brudne sumienie.")

    # Shot planning (S2)
    tags = data.get("tags", {}) or {}
    image_hint = data.get("image_hint","")
    text = data.get("text","")
    plan = plan_shot(tags, subject_hint=tags.get("subject"), image_hint=image_hint, text=text)
    data["shot"] = plan["shot"]
    data["provider_prompt"] = plan["provider_prompt"]
    data["vision_query"] = plan["vision_query"]

    # SFX URL-e
    if ENABLE_SFX:
        data["sfx_urls"] = map_sfx_keys(data.get("sfx", []))
    else:
        data["sfx_urls"] = []

    # Graph delta (Case Board)
    sid = req.state.get("session_id","default")
    graph_delta = _infer_graph_delta_from_story(sid, data)
    data["graph_delta"] = graph_delta

    # Reframe flags
    data["reframed"] = reframed
    if reframed:
        data["reframed_from"] = reframed_from
        data["reframed_to"] = user_input

    # BG swap (dwubieg) – jak w poprzednim sprincie
    if os.getenv("ENABLE_BG_IMAGE_SWAP","0") == "1":
        sid = state.get("session_id","default")
        tid = state.get("turn_id",0)
        asyncio.create_task(_bg_generate_and_push(sid, tid, data.get("text",""), data.get("provider_prompt")))

    return data

@app.post("/link")
async def link(req: LinkReq):
    sid = req.state.get("session_id","default")
    g = _graph_get(sid)
    # heurystyka typu: clue/suspect/location (MVP: zgadnij po słowie)
    def _guess_type(lbl: str) -> str:
        t = "clue"
        if any(k in lbl.lower() for k in ["ulica","alej","bar","biuro","posterunek","kamienica"]): t="location"
        if any(k in lbl.lower() for k in ["komendant","podejrz","swiadk","świadk"]): t="suspect"
        return t
    a = _ensure_node(g, _guess_type(req.from_label), req.from_label)
    b = _ensure_node(g, _guess_type(req.to_label), req.to_label)
    e = _add_edge(g, a["id"], b["id"], req.relation, 0.7)
    return {"nodes_add":[a,b], "edges_add":[e]}

@app.post("/accuse")
async def accuse(req: AccuseReq):
    sid = req.state.get("session_id","default")
    suspect = req.suspect_label.strip()
    # LLM epilog (skrót)
    if LLM_ENABLED:
        prompt = (
            "Epilog noir po polsku (120–180 słów). Gracz kieruje sprawę do finału, wskazując podejrzanego.\n"
            f"Podejrzany: {suspect}\n"
            "Oceń na podstawie logiki noir: czy dowody są wystarczające (guilty / not_enough_evidence / wrong_person). "
            "Zwróć JSON: {\"verdict\":\"guilty|not_enough_evidence|wrong_person\",\"epilogue\":\"…\"} (tylko JSON)."
        )
        raw = await generate_text_llm(prompt)
        m = re.search(r"\{.*\}", raw, re.S)
        try:
            data = json.loads(m.group(0))
        except Exception:
            data = {"verdict":"not_enough_evidence","epilogue":"Miasto milczy, a papieros gaśnie szybciej niż sumienie."}
    else:
        data = {"verdict":"not_enough_evidence","epilogue":"Miasto milczy, a papieros gaśnie szybciej niż sumienie."}
    # SFX
    sfx_keys = ["gavel"] if data["verdict"]=="guilty" else ["heartbeat"]
    data["sfx_urls"] = map_sfx_keys(sfx_keys) if ENABLE_SFX else []
    return data

# Serwowanie statycznych plików muzyki (jeśli volume zamontowany z data/music)
from fastapi.staticfiles import StaticFiles
if os.path.isdir(MUSIC_DIR):
    app.mount("/music", StaticFiles(directory=MUSIC_DIR), name="music")