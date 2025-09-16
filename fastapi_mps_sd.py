from fastapi import FastAPI
from pydantic import BaseModel
from diffusers import AutoPipelineForText2Image, DPMSolverMultistepScheduler
import torch, base64, io
from PIL import Image

app = FastAPI(title="Local SD (MPS)")
device = "mps" if torch.backends.mps.is_available() else "cpu"

model_id = "stabilityai/sd-turbo"
pipe = AutoPipelineForText2Image.from_pretrained(model_id, torch_dtype=torch.float16 if device=="mps" else torch.float32)
pipe.to(device)
pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config)

class GenReq(BaseModel):
    prompt: str
    width: int = 640
    height: int = 360
    steps: int = 4
    seed: int | None = None

@app.post("/generate")
def generate(req: GenReq):
    g = torch.Generator(device=device)
    if req.seed is not None:
        g = g.manual_seed(req.seed)
    image = pipe(
        req.prompt, width=req.width, height=req.height,
        num_inference_steps=req.steps, guidance_scale=0.0, generator=g
    ).images[0]
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    return {"image_base64": b64}
