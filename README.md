# AKS Edge Golf AI – Swing Analyzer

A production-grade, containerized golf swing analyzer powered by AI. Upload a video, get instant stage-by-stage feedback with annotated side-by-side comparisons against good practice references.

## Features

- 🎥 **Video Upload** – Drag & drop or browse; supports MP4, MOV, AVI, WebM
- 🤖 **AI Analysis** – MediaPipe pose estimation + CLIP embedding matching
- 📊 **8-Stage Breakdown** – Address → Takeaway → Backswing → Top → Downswing → Impact → Follow-Through → Finish
- 🎯 **Per-Stage Scoring** – 0–100 score with detailed good/bad/why/tips feedback
- 🖼️ **Side-by-Side Comparison** – Annotated user vs. reference frames with skeleton overlays and callouts
- 🔍 **Click to Enlarge** – Lightbox for detailed frame inspection
- ☸️ **K8s Ready** – Deploy to AKS, Kind, or any conformant K8s cluster
- 📐 **Architecture Viewer** – Interactive system architecture diagram built into the UI
- 📡 **Live K8s Panel** – Real-time cluster status when running in Kubernetes

## Quick Start (Local — No Docker)

```bash
git clone https://github.com/nnamuhcs/aks-edge-golf-ai.git
cd aks-edge-golf-ai

# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
# First run downloads CLIP model (~600MB) from HuggingFace

# Frontend (separate terminal)
cd frontend
npm install && npm run build
# Backend serves the built frontend at http://localhost:8000
```

Open **http://localhost:8000**

## Quick Start (Kind — Local Kubernetes)

**Option A: Pull pre-built images (no build needed)**

```bash
# Create Kind cluster with port mapping
kind create cluster --name golf-ai --config deploy/kind-config.yaml

# Deploy — images pull from ghcr.io automatically
kubectl apply -k deploy/base/
```

> ⏳ **Note:** The backend image is ~6GB (includes ML models). First pull may take 5–15 minutes depending on your internet speed. You can monitor progress with `kubectl get pods -n golf-ai -w`.

**Option B: Build images locally**

```bash
# Build images (backend ~5 min first time — downloads ML models)
docker build -t golf-ai-backend:latest -f backend/Dockerfile backend/
docker build -t golf-ai-frontend:latest -f frontend/Dockerfile frontend/

# Create Kind cluster with port mapping
kind create cluster --name golf-ai --config deploy/kind-config.yaml

# Load locally-built images into Kind & deploy
kind load docker-image golf-ai-backend:latest golf-ai-frontend:latest --name golf-ai
kubectl apply -k deploy/overlays/kind
```

Open **http://localhost:3001** — no port-forward needed!

> 📖 **Full deployment guide** (including AKS): [docs/deployment-guide.md](docs/deployment-guide.md)

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
