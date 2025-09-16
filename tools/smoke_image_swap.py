#!/usr/bin/env python3
# tools/smoke_image_swap.py
import os, time, httpx, json

AI_BASE = os.getenv("PUBLIC_AI_BASE","http://localhost:8003")
VISION_BASE = os.getenv("PUBLIC_VISION_BASE","http://localhost:8004")

def main():
    payload = {"game_state":{"session_id":"swap-1","turn_id":1,"players":["A","B"],"history":[]},
               "actions":{"A":"investigate","B":"interrogate"}}
    r = httpx.post(f"{AI_BASE}/orchestrate", json=payload, timeout=60)
    r.raise_for_status()
    img1 = r.json().get("image")
    print("Stage1 (lib):", img1)
    time.sleep(8)  # poczekaj na tło
    # Czy pojawił się plik w generated?
    r2 = httpx.get(f"{VISION_BASE}/list?collection=generated", timeout=10)
    r2.raise_for_status()
    data = r2.json()
    print("Generated count:", len(data.get("images",[])))
    print("OK (smoke)")

if __name__ == "__main__":
    main()
