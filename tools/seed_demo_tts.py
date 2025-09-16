# tools/seed_demo_tts.py
import httpx, asyncio
from common import TTS_BASE

LINES = [
    "Miasto nie śpi. A my też nie powinniśmy.",
    "Deszcz skrywa więcej niż tylko brud ulicy.",
    "Nie każde alibi wytrzymuje próbę czasu.",
]

async def speak_one(client: httpx.AsyncClient, text: str):
    r = await client.post(f"{TTS_BASE}/speak", json={"text": text, "turn_id": 1, "session_id": "seed"}, timeout=30)
    r.raise_for_status()
    url = r.json().get("audio_url")
    print("TTS:", text, "->", url)

async def main():
    async with httpx.AsyncClient() as client:
        await asyncio.gather(*[speak_one(client, t) for t in LINES])

if __name__ == "__main__":
    asyncio.run(main())
