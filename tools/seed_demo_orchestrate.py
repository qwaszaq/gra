# tools/seed_demo_orchestrate.py
import asyncio, httpx
from common import AI_BASE

SCENES = [
    ("demo-oc-1", 1, {"A":"investigate","B":"interrogate"}),
    ("demo-oc-2", 2, {"A":"interrogate","B":"report"}),
    ("demo-oc-3", 3, {"A":"move","B":"investigate"}),
]

async def run_one(client: httpx.AsyncClient, sid: str, turn: int, acts: dict):
    payload = {"game_state":{"session_id":sid,"turn_id":turn,"players":["A","B"],"history":[]}, "actions": acts}
    r = await client.post(f"{AI_BASE}/orchestrate", json=payload, timeout=90)
    r.raise_for_status()
    data = r.json()
    print(f"Orchestrated: {sid}/t{turn} | img={data.get('image')} music={data.get('music')}")

async def main():
    async with httpx.AsyncClient() as client:
        await asyncio.gather(*[run_one(client, sid, turn, acts) for sid,turn,acts in SCENES])

if __name__ == "__main__":
    asyncio.run(main())
