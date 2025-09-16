import os
import httpx

GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")
LMSTUDIO_URL = os.getenv("LMSTUDIO_URL", "")  # np. http://localhost:1234/v1
OLLAMA_URL   = os.getenv("OLLAMA_URL", "")    # np. http://ollama:11434
LLM_MODEL    = os.getenv("LLM_MODEL", "llama3:8b-instruct")

NOIR_SYSTEM = (
    "Jesteś narratorem noir. Opowiadasz krótko, sugestywnie, w klimacie Sin City/Disco Elysium. "
    "Piszesz po polsku, trzymasz się faktów z akcji graczy, bez wulgaryzmów."
)

def _build_prompt(game_state: dict, actions: dict) -> str:
    turn = game_state.get("turn_id", 0)
    players = game_state.get("players", [])
    acts = ", ".join(f"{p}:{actions.get(p)}" for p in players if p in actions)
    ctx = f"Tura {turn}. Akcje: {acts}. Poprzednie zdarzenia: " + \
          " | ".join(h.get("text","") for h in game_state.get("history", [])[-3:])
    return f"{ctx}\nOpisz jedną zwięzłą scenę w stylu noir (2-3 zdania)."

async def _call_gemini(prompt: str) -> str:
    if not GEMINI_KEY:
        raise RuntimeError("No GEMINI_API_KEY")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GEMINI_KEY}"
    payload = {
        "contents": [
            {"parts": [{"text": NOIR_SYSTEM}]},
            {"parts": [{"text": prompt}]}
        ]
    }
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(url, json=payload)
        r.raise_for_status()
        data = r.json()
        # typowa ścieżka: candidates[0].content.parts[0].text
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()

async def _call_lmstudio(prompt: str) -> str:
    if not LMSTUDIO_URL:
        raise RuntimeError("No LMSTUDIO_URL")
    # OpenAI-compatible chat completions
    url = f"{LMSTUDIO_URL}/chat/completions" if not LMSTUDIO_URL.endswith("/chat/completions") else LMSTUDIO_URL
    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": NOIR_SYSTEM},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.6,
        "max_tokens": 180
    }
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(url, json=payload)
        r.raise_for_status()
        data = r.json()
        return data["choices"][0]["message"]["content"].strip()

async def _call_ollama(prompt: str) -> str:
    if not OLLAMA_URL:
        raise RuntimeError("No OLLAMA_URL")
    # Chat API
    url = f"{OLLAMA_URL}/api/chat"
    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": NOIR_SYSTEM},
            {"role": "user", "content": prompt}
        ],
        "stream": False
    }
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(url, json=payload)
        r.raise_for_status()
        data = r.json()
        return data["message"]["content"].strip()

async def generate_narrative_llm(game_state: dict, actions: dict) -> str:
    prompt = _build_prompt(game_state, actions)

    # Priorytet: LM Studio -> Gemini -> Ollama (możesz zmienić kolejność wg potrzeb)
    backends = []
    if LMSTUDIO_URL: backends.append(_call_lmstudio)
    if GEMINI_KEY:   backends.append(_call_gemini)
    if OLLAMA_URL:   backends.append(_call_ollama)

    if not backends:
        raise RuntimeError("No LLM backend configured")

    last_err = None
    for fn in backends:
        try:
            return await fn(prompt)
        except Exception as e:
            last_err = e
            continue
    raise RuntimeError(f"All LLM backends failed: {last_err}")

# Bot-specific LLM functions for short commands
async def _gemini_complete(prompt: str) -> str:
    if not GEMINI_KEY: raise RuntimeError("No GEMINI_API_KEY")
    model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_KEY}"
    payload = {"contents":[{"role":"user","parts":[{"text": prompt}]}]}
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(url, json=payload); r.raise_for_status()
        data = r.json()
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()

async def _lmstudio_complete(prompt: str) -> str:
    if not LMSTUDIO_URL: raise RuntimeError("No LMSTUDIO_URL")
    url = f"{LMSTUDIO_URL}/chat/completions" if not LMSTUDIO_URL.endswith("/chat/completions") else LMSTUDIO_URL
    payload = {"model": LLM_MODEL, "messages":[{"role":"user","content": prompt}], "temperature":0.6, "max_tokens":60}
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(url, json=payload); r.raise_for_status()
        data = r.json()
        return data["choices"][0]["message"]["content"].strip()

async def _ollama_complete(prompt: str) -> str:
    if not OLLAMA_URL: raise RuntimeError("No OLLAMA_URL")
    url = f"{OLLAMA_URL}/api/chat"
    payload = {"model": LLM_MODEL, "messages":[{"role":"user","content": prompt}], "stream": False}
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(url, json=payload); r.raise_for_status()
        data = r.json()
        return data["message"]["content"].strip()

async def generate_text_llm(prompt: str) -> str:
    backends = []
    if LMSTUDIO_URL: backends.append(_lmstudio_complete)
    if GEMINI_KEY:    backends.append(_gemini_complete)
    if OLLAMA_URL:    backends.append(_ollama_complete)
    if not backends:  raise RuntimeError("No LLM backend configured")
    last_err = None
    for fn in backends:
        try:
            return await fn(prompt)
        except Exception as e:
            last_err = e; continue
    raise RuntimeError(f"All LLM backends failed: {last_err}")
