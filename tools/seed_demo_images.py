# tools/seed_demo_images.py
import os, base64, hashlib, pathlib, asyncio, httpx
from common import LOCAL_IMAGE_URL, OUT_IMAGES_DIR

PROMPTS = [
    "film noir, ciemna alejka w deszczu, świadek w cieniu, high contrast, red accent",
    "gabinet komendanta, dym cygara, plakat policyjny, noir comic style",
    "miejsce zbrodni, rozlana krew, neon za oknem, sin city style",
    "posterunek policji, noc, kubki po kawie, papierosy, noir ambience",
]

async def gen_one(client: httpx.AsyncClient, prompt: str):
    r = await client.post(LOCAL_IMAGE_URL, json={"prompt": prompt, "steps": 4, "width": 640, "height": 360}, timeout=60)
    r.raise_for_status()
    b64 = r.json().get("image_base64")
    if not b64:
        print("No image for prompt:", prompt)
        return None
    key = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]
    pathlib.Path(OUT_IMAGES_DIR).mkdir(parents=True, exist_ok=True)
    out = os.path.join(OUT_IMAGES_DIR, f"{key}.png")
    with open(out, "wb") as f:
        f.write(base64.b64decode(b64))
    return out

async def main():
    async with httpx.AsyncClient() as client:
        tasks = [gen_one(client, p) for p in PROMPTS]
        outs = await asyncio.gather(*tasks, return_exceptions=True)
        for o in outs:
            if isinstance(o, str):
                print("Saved:", o)
            else:
                print("Err:", o)

if __name__ == "__main__":
    asyncio.run(main())
