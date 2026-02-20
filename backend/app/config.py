"""Configuration settings for the Golf AI backend."""
import os
from pathlib import Path

# Directories
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("GOLF_DATA_DIR", str(BASE_DIR / "data")))
UPLOAD_DIR = DATA_DIR / "uploads"
RESULTS_DIR = DATA_DIR / "results"
ASSETS_DIR = DATA_DIR / "assets"
REFERENCE_DIR = Path(os.environ.get("GOLF_REFERENCE_DIR", str(BASE_DIR / "reference_data")))
MODEL_CACHE_DIR = Path(os.environ.get("GOLF_MODEL_CACHE", str(BASE_DIR / "model_cache")))

# Ensure directories exist
for d in [UPLOAD_DIR, RESULTS_DIR, ASSETS_DIR, MODEL_CACHE_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Upload limits
MAX_UPLOAD_SIZE_MB = int(os.environ.get("MAX_UPLOAD_SIZE_MB", "200"))

# Model settings
CLIP_MODEL_NAME = os.environ.get("CLIP_MODEL_NAME", "openai/clip-vit-base-patch32")
DEVICE = os.environ.get("INFERENCE_DEVICE", "cpu")

# Swing stages in order
SWING_STAGES = [
    "address",
    "takeaway",
    "backswing",
    "top",
    "downswing",
    "impact",
    "follow_through",
    "finish",
]

STAGE_DISPLAY_NAMES = {
    "address": "Address",
    "takeaway": "Takeaway",
    "backswing": "Backswing",
    "top": "Top of Swing",
    "downswing": "Downswing",
    "impact": "Impact",
    "follow_through": "Follow-Through",
    "finish": "Finish",
}

# Stage weights for overall score
STAGE_WEIGHTS = {
    "address": 0.10,
    "takeaway": 0.10,
    "backswing": 0.12,
    "top": 0.15,
    "downswing": 0.15,
    "impact": 0.18,
    "follow_through": 0.10,
    "finish": 0.10,
}
