# tools/seed_sfx.py
import os, wave, struct, math, pathlib

OUT = pathlib.Path("data/sfx")
OUT.mkdir(parents=True, exist_ok=True)

def tone(path, freq=880.0, dur=0.15, vol=0.2, fr=44100):
    n = int(dur*fr)
    with wave.open(str(path), 'w') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(fr)
        for i in range(n):
            s = vol*32767.0*math.sin(2*math.pi*freq*(i/fr))
            w.writeframes(struct.pack('<h', int(s)))

def silence(path, dur=0.25, fr=44100):
    n = int(dur*fr)
    with wave.open(str(path), 'w') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(fr)
        z = struct.pack('<h', 0)
        for _ in range(n): w.writeframes(z)

if not (OUT/"reload.wav").exists(): tone(OUT/"reload.wav", freq=440, dur=0.12)
if not (OUT/"lighter.wav").exists(): tone(OUT/"lighter.wav", freq=660, dur=0.10)
if not (OUT/"rain.wav").exists(): silence(OUT/"rain.wav", dur=0.5)
if not (OUT/"gavel.wav").exists(): tone(OUT/"gavel.wav", freq=220, dur=0.12)
if not (OUT/"heartbeat.wav").exists(): tone(OUT/"heartbeat.wav", freq=110, dur=0.25)

print("SFX ready in data/sfx")
