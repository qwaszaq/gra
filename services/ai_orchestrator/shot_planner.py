import os, json, hashlib
from typing import Dict, Any, Tuple

SHOTS_CONFIG_PATH = os.getenv("SHOTS_CONFIG_PATH","/app/config/shots.json")
ANCHORS_CONFIG_PATH = os.getenv("ANCHORS_CONFIG_PATH","/app/config/anchors.json")

with open(SHOTS_CONFIG_PATH,"r",encoding="utf-8") as f:
    _SHOTS = json.load(f)
with open(ANCHORS_CONFIG_PATH,"r",encoding="utf-8") as f:
    _AN = json.load(f)

_STYLE = _SHOTS.get("meta",{}).get("style","black & white high-contrast film noir, film grain, 16:9")
_SHOT_LIST = _SHOTS.get("shots",[])

def _match_score(shot: Dict[str,Any], tags: Dict[str,str]) -> int:
    # proste dopasowanie: ile warunków spełnionych
    want = shot.get("match",{})
    score = 0
    for k, vals in want.items():
        if not isinstance(vals, list): vals = [vals]
        if tags.get(k) in vals: score += 1
    return score

def _anchor_text(tags: Dict[str,str], subject_hint: str|None) -> str:
    subj = subject_hint or tags.get("subject","detective")
    loc  = tags.get("location","street")
    s = _AN.get("subjects",{}).get(subj,"")
    l = _AN.get("locations",{}).get(loc,"")
    return ", ".join([t for t in [s,l] if t])

def plan_shot(tags: Dict[str,str], subject_hint: str|None = None, image_hint: str|None = None, text: str|None = None) -> Dict[str,str]:
    # wybierz najlepszy shot po punktach
    best = None; best_score = -1
    print(f"[ShotPlanner] Tags: {tags}")
    for sh in _SHOT_LIST:
        sc = _match_score(sh, tags)
        print(f"[ShotPlanner] Shot {sh.get('name')}: score={sc}, match={sh.get('match')}")
        if sc > best_score:
            best = sh; best_score = sc
    if best is None:  # fallback
        best = {"name":"alley_establishing","vision_query":"noir alley at night","provider_template":"{STYLE}, wet alley at night, {ANCHOR}"}
    print(f"[ShotPlanner] Selected: {best.get('name')} (score={best_score})")

    shot_name = best.get("name","alley_establishing")
    vision_query = best.get("vision_query","noir scene")
    tmpl = best.get("provider_template","{STYLE}, noir scene, {ANCHOR}")

    # wypełnij template
    prompt = tmpl.format(
        STYLE=_STYLE,
        LOCATION=tags.get("location","street"),
        SUBJECT=tags.get("subject","detective"),
        ACTION=tags.get("action","investigate"),
        MOOD=tags.get("mood","tense"),
        MOTIF=tags.get("motif","red_neon"),
        IMAGE_HINT=(image_hint or ""),
        ANCHOR=_anchor_text(tags, subject_hint),
        TEXT=(text or "")[:100]  # pierwsze 100 znaków sceny
    ).replace("  "," ").strip()

    return {"shot": shot_name, "vision_query": vision_query, "provider_prompt": prompt}
