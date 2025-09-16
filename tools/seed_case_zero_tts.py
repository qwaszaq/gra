# tools/seed_case_zero_tts.py
import json, os, httpx, shutil

SCENARIO = "scenarios/case_zero/scenario.json"
BACKUP   = "scenarios/case_zero/scenario.backup.json"
TTS_BASE = os.getenv("PUBLIC_TTS_BASE", "http://localhost:8001")

def main():
    with open(SCENARIO, "r", encoding="utf-8") as f:
        data = json.load(f)
    shutil.copyfile(SCENARIO, BACKUP)
    print("Backup:", BACKUP)

    for turn in data.get("turns", []):
        text = turn.get("narration", "")
        turn_id = turn.get("turn_id", 0)
        r = httpx.post(f"{TTS_BASE}/speak", json={"text": text, "turn_id": turn_id, "session_id":"case_zero"}, timeout=60)
        r.raise_for_status()
        url = r.json().get("audio_url")
        turn["voice_audio"] = url
        print("Turn", turn_id, "->", url)

    with open(SCENARIO, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("Updated:", SCENARIO)

if __name__ == "__main__":
    main()
