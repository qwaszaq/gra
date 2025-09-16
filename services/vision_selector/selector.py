from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
import os, hashlib
from embeddings import VisionEmbeddings

app = FastAPI(title="Vision Selector", version="2.0.0")

# CORS
origins = [os.getenv("WEB_CLIENT_ORIGIN", "http://localhost:5173")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize embeddings system
embeddings_system = VisionEmbeddings()

ASSETS_DIR = "assets"
IMAGES_ROOT = os.path.join(ASSETS_DIR, "images")
DEFAULT_COLLECTION = os.getenv("DEFAULT_COLLECTION", "case_zero")
# Don't create directories if they're mounted via volume
if not os.path.exists(IMAGES_ROOT):
    os.makedirs(os.path.join(IMAGES_ROOT, DEFAULT_COLLECTION), exist_ok=True)

# Placeholder (pusty plik, może zostać podmieniony prawdziwym PNG)
placeholder = os.path.join(IMAGES_ROOT, "placeholder.png")
os.makedirs(os.path.dirname(placeholder), exist_ok=True)
if not os.path.exists(placeholder):
    with open(placeholder, "wb") as f:
        pass

app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")

class MatchReq(BaseModel):
    text: str
    collection: str | None = None

class MatchTopKReq(BaseModel):
    text: str
    collection: str | None = None
    k: int = 3

class ReindexReq(BaseModel):
    collection: str | None = None
    force: bool = False

@app.get("/health")
def health():
    col = DEFAULT_COLLECTION
    col_dir = os.path.join(IMAGES_ROOT, col)
    imgs = [f for f in os.listdir(col_dir) if f.lower().endswith((".png",".jpg",".jpeg"))] if os.path.exists(col_dir) else []
    
    # Get embeddings stats
    stats = embeddings_system.get_stats()
    
    return {
        "status": "ok", 
        "collection": col, 
        "images": len(imgs),
        "embeddings": stats,
        "embedding_enabled": stats["index_built"]
    }

def _deterministic_pick(items: list[str], key: str) -> str:
    if not items:
        return "/assets/images/placeholder.png"
    h = hashlib.sha256(key.encode("utf-8")).hexdigest()
    idx = int(h, 16) % len(items)
    return items[idx]

def _deterministic_indices(n: int, seed: str, k: int) -> list[int]:
    # wyznacz start i krok na podstawie hasha; gwarantuje różne indeksy
    h = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    start = int(h[:8], 16) % max(n, 1)
    step = (int(h[8:16], 16) % max(n - 1, 1)) + 1 if n > 1 else 1
    picks, used = [], set()
    i = 0
    while len(picks) < min(k, n):
        idx = (start + i * step) % n
        if idx not in used:
            used.add(idx)
            picks.append(idx)
        i += 1
    return picks

@app.post("/match")
def match(req: MatchReq):
    col = req.collection or DEFAULT_COLLECTION
    col_dir = os.path.join(IMAGES_ROOT, col)
    if not os.path.exists(col_dir):
        return {"image_url": "/assets/images/placeholder.png", "score": 0.0, "method": "fallback"}
    
    # Try embedding-based matching first
    if embeddings_system.index is not None:
        try:
            result = embeddings_system.get_best_match(req.text)
            if result:
                image_path, score = result
                # Convert absolute path to relative URL
                if image_path.startswith(col_dir):
                    rel_path = os.path.relpath(image_path, IMAGES_ROOT)
                    image_url = f"/assets/images/{rel_path.replace(os.sep, '/')}"
                    return {"image_url": image_url, "score": score, "method": "embedding"}
        except Exception as e:
            print(f"[VisionSelector] Embedding match failed: {e}")
    
    # Fallback to deterministic matching
    files = [f for f in os.listdir(col_dir) if f.lower().endswith((".png",".jpg",".jpeg"))]
    rels = [f"/assets/images/{col}/{f}" for f in files]
    chosen = _deterministic_pick(rels, req.text)
    return {"image_url": chosen, "score": 0.0, "method": "deterministic"}

@app.post("/match_topk")
def match_topk(req: MatchTopKReq):
    col = req.collection or DEFAULT_COLLECTION
    col_dir = os.path.join(IMAGES_ROOT, col)
    if not os.path.exists(col_dir):
        return {"collection": col, "images": [{"url": "/assets/images/placeholder.png", "score": 0.0}], "method": "fallback"}
    
    # Try embedding-based matching first
    if embeddings_system.index is not None:
        try:
            results = embeddings_system.search_similar(req.text, k=req.k)
            if results:
                images_with_scores = []
                for image_path, score in results:
                    if image_path.startswith(col_dir):
                        rel_path = os.path.relpath(image_path, IMAGES_ROOT)
                        image_url = f"/assets/images/{rel_path.replace(os.sep, '/')}"
                        images_with_scores.append({"url": image_url, "score": score})
                return {"collection": col, "images": images_with_scores, "method": "embedding"}
        except Exception as e:
            print(f"[VisionSelector] Embedding topk match failed: {e}")
    
    # Fallback to deterministic matching
    files = sorted([f for f in os.listdir(col_dir) if f.lower().endswith((".png",".jpg",".jpeg"))])
    rels = [f"/assets/images/{col}/{f}" for f in files]
    if not rels:
        return {"collection": col, "images": [{"url": "/assets/images/placeholder.png", "score": 0.0}], "method": "fallback"}
    idxs = _deterministic_indices(len(rels), req.text, req.k)
    images_with_scores = [{"url": rels[i], "score": 0.0} for i in idxs]
    return {"collection": col, "images": images_with_scores, "method": "deterministic"}

@app.get("/list")
def list_images(collection: str = "generated"):
    """
    Zwraca listę względnych ścieżek obrazów z assets/images/<collection>
    """
    col_dir = os.path.join(IMAGES_ROOT, collection)
    if not os.path.exists(col_dir):
        return {"collection": collection, "images": []}
    files = sorted([f for f in os.listdir(col_dir) if f.lower().endswith((".png",".jpg",".jpeg"))])
    rels = [f"/assets/images/{collection}/{f}" for f in files]
    return {"collection": collection, "images": rels}

@app.post("/reindex")
def reindex(req: ReindexReq = None):
    """Rebuild embeddings index for a collection"""
    try:
        # If no body provided, use default collection
        if req is None:
            col = DEFAULT_COLLECTION
            force_recompute = False
        else:
            col = req.collection or DEFAULT_COLLECTION
            force_recompute = req.force
            
        col_dir = os.path.join(IMAGES_ROOT, col)
        
        if not os.path.exists(col_dir):
            return {"status": "error", "message": f"Collection {col} not found"}
        
        print(f"[VisionSelector] Reindexing collection: {col}")
        success = embeddings_system.compute_embeddings(col_dir, force_recompute=force_recompute)
        
        if success:
            stats = embeddings_system.get_stats()
            return {
                "status": "success", 
                "message": f"Reindexed {col} successfully",
                "stats": stats
            }
        else:
            return {"status": "error", "message": "Failed to compute embeddings"}
            
    except Exception as e:
        print(f"[VisionSelector] Reindex error: {e}")
        return {"status": "error", "message": str(e)}

@app.on_event("startup")
async def startup_event():
    """Initialize embeddings on startup"""
    try:
        col_dir = os.path.join(IMAGES_ROOT, DEFAULT_COLLECTION)
        if os.path.exists(col_dir):
            print(f"[VisionSelector] Initializing embeddings for {DEFAULT_COLLECTION}")
            embeddings_system.compute_embeddings(col_dir, force_recompute=False)
        else:
            print(f"[VisionSelector] Collection {DEFAULT_COLLECTION} not found, skipping embeddings initialization")
    except Exception as e:
        print(f"[VisionSelector] Startup embeddings error: {e}")
