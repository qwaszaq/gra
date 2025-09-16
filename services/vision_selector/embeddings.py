import os
import numpy as np
import faiss
from PIL import Image
import torch
from transformers import CLIPProcessor, CLIPModel
import json
from typing import List, Tuple, Dict, Optional

class VisionEmbeddings:
    def __init__(self, model_name: str = "openai/clip-vit-base-patch32"):
        self.model_name = model_name
        self.model = None
        self.processor = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.embeddings_cache = {}
        self.index = None
        self.image_paths = []
        self.embeddings_file = "embeddings.npz"
        self.index_file = "index.faiss"
        self.metadata_file = "metadata.json"
        
    def load_model(self):
        """Load CLIP model and processor"""
        if self.model is None:
            print(f"[VisionEmbeddings] Loading CLIP model: {self.model_name}")
            self.model = CLIPModel.from_pretrained(self.model_name)
            self.processor = CLIPProcessor.from_pretrained(self.model_name)
            self.model.to(self.device)
            self.model.eval()
            print(f"[VisionEmbeddings] Model loaded on {self.device}")
    
    def get_text_embedding(self, text: str) -> np.ndarray:
        """Get CLIP embedding for text"""
        self.load_model()
        
        inputs = self.processor(text=text, return_tensors="pt", padding=True, truncation=True)
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        with torch.no_grad():
            text_features = self.model.get_text_features(**inputs)
            text_features = text_features / text_features.norm(dim=-1, keepdim=True)
            return text_features.cpu().numpy().flatten()
    
    def get_image_embedding(self, image_path: str) -> np.ndarray:
        """Get CLIP embedding for image"""
        self.load_model()
        
        try:
            image = Image.open(image_path).convert("RGB")
            inputs = self.processor(images=image, return_tensors="pt")
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            with torch.no_grad():
                image_features = self.model.get_image_features(**inputs)
                image_features = image_features / image_features.norm(dim=-1, keepdim=True)
                return image_features.cpu().numpy().flatten()
        except Exception as e:
            print(f"[VisionEmbeddings] Error processing image {image_path}: {e}")
            return np.zeros(512)  # CLIP base model has 512 dimensions
    
    def scan_images(self, images_dir: str) -> List[str]:
        """Scan directory for images and return list of paths"""
        image_extensions = {'.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.webp'}
        image_paths = []
        
        for root, dirs, files in os.walk(images_dir):
            for file in files:
                if any(file.lower().endswith(ext) for ext in image_extensions):
                    full_path = os.path.join(root, file)
                    image_paths.append(full_path)
        
        print(f"[VisionEmbeddings] Found {len(image_paths)} images in {images_dir}")
        return image_paths
    
    def compute_embeddings(self, images_dir: str, force_recompute: bool = False) -> bool:
        """Compute embeddings for all images in directory"""
        if not force_recompute and self.load_cached_embeddings():
            print("[VisionEmbeddings] Using cached embeddings")
            return True
        
        print("[VisionEmbeddings] Computing embeddings...")
        image_paths = self.scan_images(images_dir)
        
        if not image_paths:
            print("[VisionEmbeddings] No images found")
            return False
        
        embeddings = []
        valid_paths = []
        
        for i, image_path in enumerate(image_paths):
            print(f"[VisionEmbeddings] Processing {i+1}/{len(image_paths)}: {os.path.basename(image_path)}")
            embedding = self.get_image_embedding(image_path)
            if embedding is not None and not np.all(embedding == 0):
                embeddings.append(embedding)
                valid_paths.append(image_path)
        
        if not embeddings:
            print("[VisionEmbeddings] No valid embeddings computed")
            return False
        
        self.embeddings = np.array(embeddings)
        self.image_paths = valid_paths
        
        # Build FAISS index
        dimension = self.embeddings.shape[1]
        self.index = faiss.IndexFlatIP(dimension)  # Inner product for cosine similarity
        
        # Normalize embeddings for cosine similarity
        faiss.normalize_L2(self.embeddings)
        self.index.add(self.embeddings)
        
        print(f"[VisionEmbeddings] Built FAISS index with {len(embeddings)} embeddings")
        
        # Save to cache
        self.save_embeddings()
        return True
    
    def save_embeddings(self):
        """Save embeddings and index to disk"""
        try:
            # Save embeddings
            np.savez_compressed(self.embeddings_file, embeddings=self.embeddings)
            
            # Save FAISS index
            faiss.write_index(self.index, self.index_file)
            
            # Save metadata
            metadata = {
                "image_paths": self.image_paths,
                "model_name": self.model_name,
                "num_embeddings": len(self.image_paths),
                "embedding_dim": self.embeddings.shape[1] if hasattr(self, 'embeddings') else 0
            }
            
            with open(self.metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            print(f"[VisionEmbeddings] Saved embeddings to {self.embeddings_file}")
            print(f"[VisionEmbeddings] Saved index to {self.index_file}")
            print(f"[VisionEmbeddings] Saved metadata to {self.metadata_file}")
            
        except Exception as e:
            print(f"[VisionEmbeddings] Error saving embeddings: {e}")
    
    def load_cached_embeddings(self) -> bool:
        """Load embeddings and index from disk"""
        try:
            if not all(os.path.exists(f) for f in [self.embeddings_file, self.index_file, self.metadata_file]):
                return False
            
            # Load embeddings
            data = np.load(self.embeddings_file)
            self.embeddings = data['embeddings']
            
            # Load FAISS index
            self.index = faiss.read_index(self.index_file)
            
            # Load metadata
            with open(self.metadata_file, 'r') as f:
                metadata = json.load(f)
                self.image_paths = metadata['image_paths']
            
            print(f"[VisionEmbeddings] Loaded {len(self.image_paths)} cached embeddings")
            return True
            
        except Exception as e:
            print(f"[VisionEmbeddings] Error loading cached embeddings: {e}")
            return False
    
    def search_similar(self, text: str, k: int = 5) -> List[Tuple[str, float]]:
        """Search for most similar images to text query"""
        if self.index is None or len(self.image_paths) == 0:
            return []
        
        # Get text embedding
        text_embedding = self.get_text_embedding(text)
        text_embedding = text_embedding.reshape(1, -1)
        
        # Normalize for cosine similarity
        faiss.normalize_L2(text_embedding)
        
        # Search
        scores, indices = self.index.search(text_embedding, min(k, len(self.image_paths)))
        
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < len(self.image_paths):
                image_path = self.image_paths[idx]
                results.append((image_path, float(score)))
        
        return results
    
    def get_best_match(self, text: str) -> Optional[Tuple[str, float]]:
        """Get the best matching image for text query"""
        results = self.search_similar(text, k=1)
        return results[0] if results else None
    
    def get_stats(self) -> Dict:
        """Get statistics about the embeddings"""
        return {
            "num_images": len(self.image_paths) if hasattr(self, 'image_paths') else 0,
            "embedding_dim": self.embeddings.shape[1] if hasattr(self, 'embeddings') else 0,
            "model_name": self.model_name,
            "device": self.device,
            "index_built": self.index is not None
        }
