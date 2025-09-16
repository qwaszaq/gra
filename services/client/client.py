import os
import json
import asyncio
import threading
import tempfile
import webbrowser
import requests
import websockets

WS_URL = os.getenv("WS_URL", "ws://localhost:65432/ws")
OPEN_IMAGES = os.getenv("OPEN_IMAGES", "0") == "1"

def fetch_and_play_audio(url: str):
    try:
        import simpleaudio as sa
    except Exception:
        print("Audio: simpleaudio not available")
        return
    try:
        r = requests.get(url, stream=True, timeout=15)
        r.raise_for_status()
        suffix = ".wav" if url.lower().endswith(".wav") else ".bin"
        fd, tmp = tempfile.mkstemp(suffix=suffix)
        os.close(fd)
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)
        try:
            if tmp.lower().endswith(".wav"):
                wave_obj = sa.WaveObject.from_wave_file(tmp)
                wave_obj.play()  # non-blocking
            else:
                print(f"Audio: pobrano {url}, ale format nieobsługiwany do odtwarzania (nie-WAV).")
        except Exception as e:
            print("Audio play error:", e)
    except Exception as e:
        print("Audio fetch error:", e)

async def run_client():
    player = input("Kryptonim: ").strip() or "Detektyw"
    session_id = input("Session ID (np. demo-1): ").strip() or "demo-1"
    ws_url = input(f"WS URL [{WS_URL}]: ").strip() or WS_URL

    print(f"Łączenie z {ws_url} ...")
    async with websockets.connect(ws_url) as ws:
        # Login
        await ws.send(json.dumps({"type": "login", "player": player, "session_id": session_id}))
        print("Zalogowano. Wpisuj akcje pełnym zdaniem (np. 'Przesłuchuję świadka').")

        async def recv_loop():
            while True:
                raw = await ws.recv()
                try:
                    data = json.loads(raw)
                except Exception:
                    print("Odebrano:", raw)
                    continue

                if data.get("type") == "error":
                    print("Błąd:", data.get("reason"))
                    continue
                if data.get("type") == "info":
                    print("Info:", data.get("message"))
                    continue
                if data.get("type") == "narrative_update":
                    turn = data.get("turn_id")
                    text = data.get("text", "")
                    image_url = data.get("image")
                    audio_url = data.get("voice_audio")
                    music_url = data.get("music")

                    print(f"\n[Turn {turn}] Narrator: {text}")
                    if image_url:
                        print(f"[Obraz] {image_url}")
                        if OPEN_IMAGES:
                            try:
                                webbrowser.open(image_url)
                            except Exception:
                                pass
                    if audio_url:
                        threading.Thread(target=fetch_and_play_audio, args=(audio_url,), daemon=True).start()
                    if music_url:
                        print(f"[Muzyka] {music_url}")
                if data.get("type") == "override_update":
                    print(f"\n[OVERRIDE][Turn {data.get('turn_id')}]")
                    if data.get("text"):
                        print(f"Nowa narracja: {data['text']}")
                    if data.get("image"):
                        print(f"Nowy obraz: {data['image']}")
                        if OPEN_IMAGES:
                            try: 
                                webbrowser.open(data["image"])
                            except Exception: 
                                pass
                    if data.get("voice_audio"):
                        threading.Thread(target=fetch_and_play_audio, args=(data["voice_audio"],), daemon=True).start()
                    if data.get("music"):
                        print(f"Nowa muzyka: {data['music']}")
                    return

        async def send_loop():
            while True:
                txt = input("\nTwoja akcja: ").strip()
                if not txt:
                    continue
                # turn_id wysyłamy informacyjnie; serwer i tak synchronizuje turę
                msg = {"type": "action", "player": player, "session_id": session_id, "turn_id": 0, "text_raw": txt}
                await ws.send(json.dumps(msg))

        await asyncio.gather(recv_loop(), send_loop())

if __name__ == "__main__":
    try:
        asyncio.run(run_client())
    except KeyboardInterrupt:
        print("\nZamykam klienta…")
