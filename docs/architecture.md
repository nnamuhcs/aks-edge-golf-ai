# Architecture

## Overview

Golf Swing AI Analyzer is a two-tier web application:
- **Frontend**: React SPA served by Nginx
- **Backend**: Python FastAPI with ML inference pipeline

## Request Flow

1. User uploads video via drag-and-drop UI
2. Frontend POSTs to `/api/upload`
3. Backend saves file, creates job, spawns analysis thread
4. Frontend polls `/api/status/{job_id}` for progress
5. Backend pipeline:
   - Extracts frames from video (OpenCV)
   - Detects body pose in each frame (MediaPipe)
   - Segments swing into 8 stages (motion + wrist height heuristics)
   - Computes biomechanical metrics per stage
   - Scores each metric against ideal ranges
   - Generates natural language feedback from templates
   - Finds best-matching reference frame (CLIP embedding similarity)
   - Annotates both user and reference frames (skeleton + callouts)
   - Saves annotated images and JSON result
6. Frontend fetches `/api/result/{job_id}` and renders results

## ML Pipeline Details

### Pose Estimation (MediaPipe)
- Detects 33 body landmarks per frame
- We use 13 key landmarks (nose, shoulders, elbows, wrists, hips, knees, ankles)
- Runs on CPU, ~50ms per frame

### Stage Segmentation
- Computes frame-to-frame motion velocity of key joints
- Computes wrist height signal (club position proxy)
- Identifies anchor points: address (still), top (highest wrists), impact (peak velocity)
- Interpolates remaining stages between anchors
- Deterministic: same video always produces same segmentation

### Scoring
- Each stage has defined ideal metric ranges
- Metrics: spine angle, knee flex, arm angles, hip-shoulder separation, head sway, stance width
- Scores: 100 at ideal, linear falloff toward min/max bounds
- Overall score: weighted average across stages (impact weighted highest)

### Reference Matching (CLIP)
- Uses OpenAI's CLIP ViT-B/32 from HuggingFace
- Computes embeddings for reference frames at startup
- For each user frame, computes embedding and finds highest cosine similarity match
- Enables visual comparison against best-matching good-practice example

### Annotation
- Draws skeleton overlay on both frames
- Adds callout boxes with metric values at relevant joints
- Green callouts for good metrics (≥70), red for areas needing improvement
- Maximum 3 callouts per frame for readability

## Kubernetes Architecture

```
┌─────────────────────────────────┐
│ Namespace: golf-ai              │
│                                 │
│ ┌─────────────┐ ┌─────────────┐│
│ │  frontend    │ │  backend    ││
│ │  (nginx)     │ │  (uvicorn)  ││
│ │  Port: 80    │ │  Port: 8000 ││
│ └──────┬──────┘ └──────┬──────┘│
│        │               │       │
│ ┌──────┴──────┐ ┌──────┴──────┐│
│ │ Service     │ │ Service     ││
│ │ ClusterIP   │ │ ClusterIP   ││
│ └─────────────┘ └──────┬──────┘│
│                 ┌──────┴──────┐│
│                 │ PVC: data   ││
│                 │ PVC: models ││
│                 └─────────────┘│
└─────────────────────────────────┘
```

## Configuration

All backend settings are configurable via environment variables:
- `GOLF_DATA_DIR` – Data storage directory
- `GOLF_REFERENCE_DIR` – Reference frames directory
- `GOLF_MODEL_CACHE` – HuggingFace model cache
- `MAX_UPLOAD_SIZE_MB` – Maximum upload size (default: 200)
- `INFERENCE_DEVICE` – PyTorch device (default: cpu)
- `CLIP_MODEL_NAME` – HuggingFace model ID (default: openai/clip-vit-base-patch32)
