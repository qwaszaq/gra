import os, io, base64
from fastapi import FastAPI
from pydantic import BaseModel
from PIL import Image
import torch
from diffusers import AutoPipelineForText2Image, DPMSolverMultistepScheduler

app = FastAPI(title="Diffusers Image Generator (CPU)")
MODEL_ID = os.getenv("MODEL_ID", "stabilityai/sd-turbo")
OUT_DIR = "/app/out"
PORT = int(os.getenv("PORT", "8502"))
WIDTH = int(os.getenv("IMG_GEN_WIDTH", "640"))
HEIGHT = int(os.getenv("IMG_GEN_HEIGHT", "360"))
STEPS = int(os.getenv("IMG_GEN_STEPS", "4"))
device = "cpu"
dtype = torch.float32
pipe = None

class GenReq(BaseModel):
    prompt: str
    width: int | None = None
    height: int | None = None
    steps: int | None = None
    seed: int | None = None

@app.on_event("startup")
def load_model():
    global pipe
    pipe = AutoPipelineForText2Image.from_pretrained(MODEL_ID, torch_dtype=dtype)
    pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config)
    pipe.to(device)
    print(f"[image_gen] Loaded {MODEL_ID} on {device}")

@app.get("/health")
def health():
    return {"status":"ok", "model": MODEL_ID, "device": device}

@app.post("/generate")
def generate(req: GenReq):
    if pipe is None:
        return {"error": "model not ready"}
    w = req.width or WIDTH
    h = req.height or HEIGHT
    s = req.steps or STEPS
    g = torch.Generator(device=device).manual_seed(req.seed) if req.seed is not None else None
    image = pipe(req.prompt, width=w, height=h, num_inference_steps=s, guidance_scale=0.0, generator=g).images[0]
    with io.BytesIO() as buf:
        image.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    return {"image_base64": b64, "width": w, "height": h, "steps": s}
