from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import os, time, unicodedata

app = FastAPI(title="Supervisor Service", version="1.2.0")

# CORS
origins = [os.getenv("WEB_CLIENT_ORIGIN", "http://localhost:5173")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

RATE_LIMIT_SECONDS = float(os.getenv("RATE_LIMIT_SECONDS", "1.0"))

BLACKLIST = [w.strip().lower() for w in os.getenv("BLACKLIST", "kurwa,kebab,lol,xd").split(",") if w.strip()]
DOMAIN_BLACKLIST = [w.strip().lower() for w in os.getenv("SUP_DOMAIN_BLACKLIST", "ogork,ogorek,ogórk,warzyw,roln,farma,plantacj,slimak,ślimak,krow,ziemniak,ogrody,ogród").split(",") if w.strip()]

def normalize(text: str) -> str:
    t = unicodedata.normalize("NFKD", text).encode("ascii","ignore").decode("ascii")
    return t.lower().strip()

INTENTS = {
    "investigate": ["zbadaj","sprawdzam","sprawdz","ogladam","przeszukuje","analizuje","badam","zabezpieczam","szukam sladow","slady","miejsce zbrodni","dowod","dowody"],
    "interrogate": ["przesluchuje","pytam","wypytuje","rozmawiam ze swiadkiem","swiadek","przesluchanie"],
    "move": ["ide","udaje sie","przemieszczam","wracam","jade","przenosze sie","na posterunek","idzie na posterunek"],
    "report": ["raportuje","meldunek","zglaszam","raport do komendanta","raportuje do komendanta"]
}

_last_call = {}

class Req(BaseModel):
    player: str = Field(min_length=2, max_length=64)
    input: str  = Field(min_length=1, max_length=500)

@app.get("/health")
def health(): return {"status":"ok"}

def ratelimit(player: str):
    now = time.monotonic()
    last = _last_call.get(player, 0.0)
    if now - last < RATE_LIMIT_SECONDS:
        raise HTTPException(status_code=429, detail="Too Many Requests")
    _last_call[player] = now

@app.post("/validate")
def validate(req: Req):
    ratelimit(req.player)
    t = normalize(req.input)

    # twarde przekroczenia
    for b in BLACKLIST:
        if b and b in t:
            return {"valid": False, "reason": "profanity", "domain": "out_of_domain", "suggestion": "Utrzymaj język profesjonalny."}

    # detekcja poza domeną noir (bardzo prosta heurystyka)
    out = any(k in t for k in DOMAIN_BLACKLIST)

    mapped, target = None, None
    for intent, keys in INTENTS.items():
        if any(k in t for k in keys):
            mapped = intent
            break

    # target heurystyka
    if "swiadk" in t or "witness" in t: target = "witness"
    elif "komendant" in t or "chief" in t: target = "chief"
    elif "noz" in t or "knife" in t: target = "knife"
    elif "posterunek" in t or "police" in t or "komisariat" in t: target = "police_station"
    elif "miejsce zbrodni" in t or "crime" in t or "scena zbrodni" in t: target = "crime_scene"

    if out and not mapped:
        # poza domeną + brak intencji – daj wskazówkę reframe
        return {
            "valid": False,
            "reason": "out_of_domain",
            "domain": "out_of_domain",
            "suggestion": "Zamień kontekst na trop, ślad, przesłuchanie lub obserwację w ciemnej scenerii."
        }

    if not mapped:
        return {
            "valid": False,
            "reason": "unrecognized_intent",
            "domain": "in_domain" if not out else "out_of_domain",
            "suggestion": "Użyj intencji: przeszukaj/przesłuchaj/idź/raportuj."
        }

    return {
        "valid": True,
        "mapped_action": mapped,
        "target": target,
        "summary": f"{mapped} {target or ''}".strip(),
        "domain": "out_of_domain" if out else "in_domain"
    }