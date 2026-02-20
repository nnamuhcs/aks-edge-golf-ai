# AKS Edge Golf AI – Swing Analyzer

A production-grade, containerized golf swing analyzer powered by AI. Upload a video, get instant stage-by-stage feedback with annotated side-by-side comparisons against good practice references.

![Demo](docs/demo-screenshot.png)

## Features

- 🎥 **Video Upload** – Drag & drop or browse; supports MP4, MOV, AVI, WebM
- 🤖 **AI Analysis** – MediaPipe pose estimation + CLIP embedding matching
- 📊 **8-Stage Breakdown** – Address → Takeaway → Backswing → Top → Downswing → Impact → Follow-Through → Finish
- 🎯 **Per-Stage Scoring** – 0–100 score with detailed good/bad/why/tips feedback
- 🖼️ **Side-by-Side Comparison** – Annotated user vs. reference frames with skeleton overlays and callouts
- 🔍 **Click to Enlarge** – Lightbox for detailed frame inspection
- ☸️ **K8s Ready** – Deploy to AKS or any conformant cluster
- 🐳 **Docker Compose** – One-command local demo

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- Docker (optional)

### Local Development

```bash
# 1. Generate demo content (synthetic videos + reference frames)
make demo-content

# 2. Install dependencies
make setup

# 3. Start backend (terminal 1)
make backend

# 4. Start frontend (terminal 2)
make frontend

# 5. Open http://localhost:3000
```

### Docker Compose (Recommended)

```bash
# Generate demo content first
make demo-content

# Build and run
docker-compose up --build

# Open http://localhost:3000
```

### Kubernetes Deployment

```bash
# Build images
make build

# Tag for your registry (if needed)
docker tag golf-swing-ai-backend <registry>/golf-swing-ai-backend:latest
docker tag golf-swing-ai-frontend <registry>/golf-swing-ai-frontend:latest
docker push <registry>/golf-swing-ai-backend:latest
docker push <registry>/golf-swing-ai-frontend:latest

# Deploy
kubectl apply -k deploy/overlays/demo

# Port-forward for access
make port-forward

# Open http://localhost:3000
```

## Architecture

```
┌──────────────────┐    ┌──────────────────────────────────┐
│   Frontend       │    │   Backend (FastAPI)               │
│   (React/Vite)   │───▶│                                  │
│                  │    │  POST /api/upload                 │
│  Upload Panel    │    │  GET  /api/status/{job_id}        │
│  Progress Bar    │    │  GET  /api/result/{job_id}        │
│  Results Panel   │    │  GET  /assets/...                 │
│  - Stage Timeline│    │                                  │
│  - Side-by-Side  │    │  Pipeline:                       │
│  - Feedback      │    │  1. Frame Extraction (OpenCV)    │
│  - Lightbox      │    │  2. Pose Detection (MediaPipe)   │
└──────────────────┘    │  3. Stage Segmentation           │
                        │  4. Orientation Normalization    │
                        │  5. Body Metrics Computation     │
                        │  6. Scoring + Feedback           │
                        │  7. Reference Matching (CLIP/HF) │
                        │  8. Frame Annotation             │
                        └──────────────────────────────────┘
```

## Model Choices

| Model | Purpose | Source |
|-------|---------|--------|
| MediaPipe Pose | Body landmark detection | Google MediaPipe |
| CLIP ViT-B/32 | Embedding similarity for reference matching | HuggingFace (openai/clip-vit-base-patch32) |

Both models run on CPU with acceptable latency for demo purposes. CLIP is downloaded at Docker build time and cached.

## Project Structure

```
aks-edge-golf-ai/
├── backend/
│   ├── app/                 # FastAPI application
│   │   ├── main.py          # API endpoints
│   │   ├── pipeline.py      # Analysis orchestrator
│   │   ├── video_decoder.py # Frame extraction
│   │   ├── pose_estimator.py# MediaPipe pose
│   │   ├── stage_segmentation.py
│   │   ├── orientation.py   # Frame rotation fix
│   │   ├── scoring.py       # Metrics + feedback
│   │   ├── annotator.py     # Visual annotations
│   │   ├── reference_matcher.py # CLIP matching
│   │   └── config.py
│   ├── tests/               # pytest tests
│   ├── reference_data/      # Good-practice frames
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   │   ├── UploadPanel.jsx
│   │   │   ├── ProgressPanel.jsx
│   │   │   └── ResultsPanel.jsx
│   │   └── index.css
│   ├── Dockerfile
│   └── package.json
├── deploy/
│   ├── base/                # K8s base manifests
│   └── overlays/demo/       # Demo kustomize overlay
├── scripts/
│   ├── generate_demo_content.py
│   └── verify_and_fix.sh
├── sample_videos/           # Demo videos (generated)
├── docs/                    # Documentation
├── docker-compose.yml
└── Makefile
```

## Testing

```bash
# Run backend tests
make test

# Run full verification loop (lint + test + build)
make verify
```

## How Stage Segmentation Works

The segmentation algorithm uses pose landmark signals:
1. **Motion signal** – velocity of key joints (wrists, hips, shoulders) frame-to-frame
2. **Wrist height signal** – proxy for club position (higher wrists = backswing/top)

Key transition points:
- **Address**: minimal motion at start
- **Top**: wrist height minimum (highest point in image coords)
- **Impact**: peak motion velocity
- Other stages are interpolated between these anchor points

**Limitations**: Works best with side-view videos. May struggle with oblique angles, multiple people, or very short clips.

## Adding New Reference Swings

1. Place stage frames in `backend/reference_data/stages/<stage_name>/`
2. Name files `ref_01.png`, `ref_02.png`, etc.
3. Rebuild the backend container or restart the server
4. The system will compute CLIP embeddings on startup and use the best-matching reference for each user stage

## License

MIT License. See [docs/licenses.md](docs/licenses.md) for dependency licenses.
