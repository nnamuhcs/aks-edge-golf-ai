"""Reference matching – uses CLIP embeddings when available, falls back to direct file loading."""
import os
import cv2
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

# CLIP availability flag
_clip_available = False
_clip_model = None
_clip_processor = None


def _try_load_clip():
    """Attempt to load CLIP model. Returns True if successful."""
    global _clip_available, _clip_model, _clip_processor
    if _clip_model is not None:
        return _clip_available

    try:
        from transformers import CLIPModel, CLIPProcessor
        from .config import CLIP_MODEL_NAME, MODEL_CACHE_DIR, DEVICE

        logger.info(f"Loading CLIP model: {CLIP_MODEL_NAME}")
        _clip_processor = CLIPProcessor.from_pretrained(
            CLIP_MODEL_NAME, cache_dir=str(MODEL_CACHE_DIR)
        )
        _clip_model = CLIPModel.from_pretrained(
            CLIP_MODEL_NAME, cache_dir=str(MODEL_CACHE_DIR)
        )
        _clip_model.eval()
        _clip_available = True
        logger.info("CLIP model loaded successfully")
    except Exception as e:
        logger.warning(f"CLIP not available ({e}), using direct reference loading")
        _clip_available = False
        _clip_model = "unavailable"  # Sentinel to prevent re-attempts

    return _clip_available


def get_image_embedding(image_bgr: np.ndarray) -> Optional[np.ndarray]:
    """Get CLIP image embedding for a frame. Returns None if CLIP not available."""
    if not _try_load_clip():
        return None

    import torch
    from PIL import Image

    image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    pil_image = Image.fromarray(image_rgb)

    inputs = _clip_processor(images=pil_image, return_tensors="pt")
    with torch.no_grad():
        embedding = _clip_model.get_image_features(**inputs)
    emb = embedding.squeeze().numpy()
    emb = emb / (np.linalg.norm(emb) + 1e-8)
    return emb


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two vectors."""
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8))


class ReferenceManager:
    """Manages good-practice reference frames for side-by-side comparison."""

    def __init__(self, reference_dir: Path):
        self.reference_dir = reference_dir
        self.stages_dir = reference_dir / "stages"
        self.reference_frames: Dict[str, List[str]] = {}
        self.embeddings: Dict[str, List[Tuple[str, np.ndarray]]] = {}
        self._load_references()

    def _load_references(self):
        """Load reference frame paths and optionally compute embeddings."""
        if not self.stages_dir.exists():
            logger.warning(f"Reference stages directory not found: {self.stages_dir}")
            return

        from .config import SWING_STAGES
        for stage in SWING_STAGES:
            stage_dir = self.stages_dir / stage
            if not stage_dir.exists():
                continue

            paths = sorted(
                [str(p) for p in stage_dir.glob("*.png")] +
                [str(p) for p in stage_dir.glob("*.jpg")]
            )
            self.reference_frames[stage] = paths

            # Try CLIP embeddings (non-blocking)
            if _try_load_clip():
                self.embeddings[stage] = []
                for img_path in paths:
                    frame = cv2.imread(img_path)
                    if frame is not None:
                        emb = get_image_embedding(frame)
                        if emb is not None:
                            self.embeddings[stage].append((img_path, emb))

        total = sum(len(v) for v in self.reference_frames.values())
        logger.info(f"Loaded {total} reference frames across {len(self.reference_frames)} stages")

    def get_reference_frame(self, stage: str, user_frame: np.ndarray = None) -> Optional[np.ndarray]:
        """Get reference frame for a stage. Uses CLIP matching if available, else first ref."""
        # Try CLIP matching first
        if stage in self.embeddings and self.embeddings[stage] and user_frame is not None:
            user_emb = get_image_embedding(user_frame)
            if user_emb is not None:
                best_path, best_sim = None, -1.0
                for ref_path, ref_emb in self.embeddings[stage]:
                    sim = cosine_similarity(user_emb, ref_emb)
                    if sim > best_sim:
                        best_sim = sim
                        best_path = ref_path
                if best_path:
                    return cv2.imread(best_path)

        # Fallback: load first available reference
        if stage in self.reference_frames and self.reference_frames[stage]:
            return cv2.imread(self.reference_frames[stage][0])

        return None
