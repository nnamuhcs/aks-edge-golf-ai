# AKS Edge Golf AI – Swing Analyzer

A production-grade, containerized golf swing analyzer powered by AI — built for **Azure Kubernetes Service (AKS)**, **AKS Arc**, and **AKS Edge Essentials**. Upload a golf swing video and get instant stage-by-stage feedback with annotated side-by-side comparisons against good practice references.

## Features

- **Video Upload** . Drag and drop or browse. Supports MP4, MOV, AVI, WebM.
- **AI Analysis** . MediaPipe pose estimation + CLIP embedding matching. All local inference, no cloud APIs.
- **8 Stage Breakdown** . Address, Takeaway, Backswing, Top, Downswing, Impact, Follow Through, Finish.
- **Per Stage Scoring** . 0 to 100 score with detailed good/bad/why/tips feedback.
- **Side by Side Comparison** . Annotated user vs. reference frames with skeleton overlays and callouts.
- **Click to Enlarge** . Lightbox for detailed frame inspection.
- **AKS Ready** . Deploy to AKS, AKS Arc, AKS Edge Essentials, or any conformant K8s cluster.
- **Architecture Viewer** . Interactive system architecture diagram built into the UI.
- **Live K8s Panel** . Real time cluster status when running in Kubernetes.

## Quick Start

### Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| kubectl | 1.28+ | [kubernetes.io](https://kubernetes.io/docs/tasks/tools/) |
| Azure CLI | 2.50+ | [learn.microsoft.com](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli) |

### Deploy to AKS (Azure Kubernetes Service)

```bash
# 1. Clone the repo
git clone https://github.com/nnamuhcs/aks-edge-golf-ai.git
cd aks-edge-golf-ai

# 2. Connect to your AKS cluster
az login
az aks get-credentials --name <your-cluster> --resource-group <your-rg>

# 3. Deploy — pre-built images pull from ghcr.io automatically
kubectl apply -k deploy/base/

# 4. Expose the frontend via LoadBalancer
kubectl patch svc golf-frontend -n golf-ai -p '{"spec":{"type":"LoadBalancer"}}'

# 5. Get the external IP (wait ~1 min for Azure to assign it)
kubectl get svc golf-frontend -n golf-ai -w
```

Open **http://\<EXTERNAL-IP\>** once the IP appears.

> **First deploy note:** The backend image is ~6GB (includes all ML models baked in). Initial pull takes 3 to 10 minutes depending on node size and network speed. Monitor with `kubectl get pods -n golf-ai -w`.

### Deploy to AKS Arc / AKS Edge Essentials

```bash
# 1. Connect to your AKS Arc cluster (on Azure Stack HCI / Azure Local)
az login
az connectedk8s proxy --name <arc-cluster> --resource-group <your-rg>
# Or use the kubeconfig from your on-prem cluster directly

# 2. Deploy
kubectl apply -k deploy/base/

# 3. Access via NodePort
kubectl get svc golf-frontend -n golf-ai
# Frontend is exposed on NodePort 30080
```

Open **http://\<node-ip\>:30080**

> **AKS Edge Essentials:** Same steps apply. The manifests work on any K3s/K8s cluster provisioned by AKS Edge. Ensure your node has at least **8GB RAM** for the ML models.

### Build Images Yourself (Optional)

If you prefer to build from source or push to a private registry:

```bash
# Build (backend ~5 min — downloads ML models during build)
docker build -t golf-ai-backend:latest -f backend/Dockerfile backend/
docker build -t golf-ai-frontend:latest -f frontend/Dockerfile frontend/

# Push to your ACR
az acr login --name <yourregistry>
docker tag golf-ai-backend:latest <yourregistry>.azurecr.io/golf-ai-backend:latest
docker tag golf-ai-frontend:latest <yourregistry>.azurecr.io/golf-ai-frontend:latest
docker push <yourregistry>.azurecr.io/golf-ai-backend:latest
docker push <yourregistry>.azurecr.io/golf-ai-frontend:latest

# Attach ACR to AKS and deploy with your registry
az aks update --name <cluster> --resource-group <rg> --attach-acr <yourregistry>
kubectl apply -k deploy/overlays/demo   # Edit overlay to point to your registry
```

> **Full deployment guide** with troubleshooting and configuration: [docs/deployment-guide.md](docs/deployment-guide.md)

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
