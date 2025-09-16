# tools/seed_all.py
import asyncio, subprocess, sys
from common import wait_all

async def run(cmd):
    print(">>", " ".join(cmd))
    p = await asyncio.create_subprocess_exec(*cmd)
    await p.wait()
    if p.returncode != 0:
        print("Command failed:", cmd, file=sys.stderr)

async def main():
    print("Waiting for services health…")
    wait_all()
    # Kolejność: obrazy (lokalny MPS), TTS sample, muzyka (orchestrator), orchestracja
    await run([sys.executable, "tools/seed_demo_images.py"])
    await run([sys.executable, "tools/seed_demo_tts.py"])
    await run([sys.executable, "tools/seed_demo_music.py"])
    await run([sys.executable, "tools/seed_demo_orchestrate.py"])
    # opcjonalnie:
    # await run([sys.executable, "tools/seed_case_zero_tts.py"])
    # await run([sys.executable, "tools/seed_admin_fake_logs.py"])
    print("Done – seeds ready.")

if __name__ == "__main__":
    asyncio.run(main())
