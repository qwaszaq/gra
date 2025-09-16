# tools/seed_demo_music.py
import asyncio, httpx
from common import AI_BASE

REQS = [
    {"game_state":{"session_id":"music-1","turn_id":1,"players":["A","B"],"history":[]}, "actions":{"A":"investigate","B":"interrogate"}},
    {"game_state":{"session_id":"music-2","turn_id":2,"players":["A","B"],"history":[]}, "actions":{"A":"interrogate","B":"report"}},
    {"game_state":{"session_id":"music-3","turn_id":3,"players":["A","B"],"history":[]}, "actions":{"A":"move","B":"investigate"}},
]

async def run_one(client: httpx.AsyncClient, payload: dict):
    r = await client.post(f"{AI_BASE}/orchestrate", json=payload, timeout=90)
    r.raise_for_status()
    data = r.json()
    print("Music:", data.get("music"))

async def main():
    async with httpx.AsyncClient() as client:
        await asyncio.gather(*[run_one(client, p) for p in REQS])

if __name__ == "__main__":
    asyncio.run(main())
