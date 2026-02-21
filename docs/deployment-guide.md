# Deployment Guide

This guide covers deploying the Golf Swing AI Analyzer in three ways:
1. **Local development** (no containers)
2. **Kind** (local Kubernetes)
3. **AKS / any Kubernetes cluster** (production)

---

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.11+ | Backend |
| Node.js | 18+ | Frontend build |
| Docker | 24+ | Container builds |
| kubectl | 1.28+ | K8s management |
| kind | 0.20+ | Local K8s (Option 2) |
| az CLI | 2.50+ | AKS (Option 3) |

---

## Option 1: Local Development

```bash
# Clone
git clone https://github.com/nnamuhcs/aks-edge-golf-ai.git
cd aks-edge-golf-ai

# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run build          # Build to dist/
# Backend serves the built frontend at http://localhost:8000
```

Open **http://localhost:8000** — the backend serves both the API and the frontend.

> **Note:** On first run, the CLIP model (~600MB) downloads automatically from HuggingFace.

---

## Option 2: Kind (Local Kubernetes)

This is the recommended way to demo the full K8s deployment locally. You have two paths:

- **Path A** — Pull pre-built images from `ghcr.io` (no build required, but large download)
- **Path B** — Build images locally (takes time, but no large download)

### Step 1: Create Kind cluster

```bash
# Create cluster with port mapping so NodePort is accessible on localhost
kind create cluster --name golf-ai --config deploy/kind-config.yaml
```

The `deploy/kind-config.yaml` maps host port **3001** → container port **30080** (the frontend NodePort).

### Step 2: Deploy

**Path A: Use pre-built images (no build needed)**

```bash
kubectl apply -k deploy/base/
```

The manifests reference `ghcr.io/nnamuhcs/golf-ai-backend:latest` and `ghcr.io/nnamuhcs/golf-ai-frontend:latest`. Kubernetes will pull them automatically.

> ⏳ **Heads up:** The backend image is approximately **6GB** because it includes all ML models (MediaPipe, CLIP ViT-B/32, PyTorch). The first pull may take **5–15 minutes** depending on your connection speed. The frontend image is only ~93MB and pulls almost instantly.
>
> Monitor progress: `kubectl get pods -n golf-ai -w` — look for `ContainerCreating` → `Running`.

**Path B: Build images locally**

```bash
cd aks-edge-golf-ai

# Build backend (includes ML models — takes ~5 min first time)
docker build -t golf-ai-backend:latest -f backend/Dockerfile backend/

# Build frontend (~1 min)
docker build -t golf-ai-frontend:latest -f frontend/Dockerfile frontend/

# Load into Kind (transfers images into the node's containerd)
kind load docker-image golf-ai-backend:latest golf-ai-frontend:latest --name golf-ai

# Deploy using the kind overlay (points to local image names)
kubectl apply -k deploy/overlays/kind
```

### Step 5: Verify

```bash
# Check pods are running
kubectl get pods -n golf-ai

# Expected output:
# NAME                             READY   STATUS    RESTARTS   AGE
# golf-backend-xxx                 1/1     Running   0          30s
# golf-frontend-xxx                1/1     Running   0          30s

# Check services
kubectl get svc -n golf-ai

# Check PVCs
kubectl get pvc -n golf-ai
```

### Step 6: Access

Open **http://localhost:3001** — no port-forward needed!

The frontend (nginx) proxies `/api/*` requests to the backend via K8s service DNS.

### Cleanup

```bash
kind delete cluster --name golf-ai
```

---

## Option 3: AKS / Production Kubernetes

The base manifests already use public images from `ghcr.io/nnamuhcs/`. You can deploy directly or use your own registry.

### Direct deploy (using public images)

```bash
# Connect to your AKS cluster
az aks get-credentials --name <cluster> --resource-group <rg>

# Deploy
kubectl apply -k deploy/base/
```

> ⏳ The backend image is ~6GB. Initial pull takes a few minutes on AKS nodes.

### Using your own ACR (optional)

```bash
# Create registry
az acr create --name <yourregistry> --resource-group <rg> --sku Basic
az acr login --name <yourregistry>

# Build and push
docker build -t <yourregistry>.azurecr.io/golf-ai-backend:latest -f backend/Dockerfile backend/
docker build -t <yourregistry>.azurecr.io/golf-ai-frontend:latest -f frontend/Dockerfile frontend/
docker push <yourregistry>.azurecr.io/golf-ai-backend:latest
docker push <yourregistry>.azurecr.io/golf-ai-frontend:latest

# Attach ACR to AKS
az aks update --name <cluster> --resource-group <rg> --attach-acr <yourregistry>
```

Edit `deploy/overlays/demo/kustomization.yaml` to use your registry:

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - ../../base

namespace: golf-ai

images:
  - name: ghcr.io/nnamuhcs/golf-ai-backend
    newName: <yourregistry>.azurecr.io/golf-ai-backend
    newTag: latest
  - name: ghcr.io/nnamuhcs/golf-ai-frontend
    newName: <yourregistry>.azurecr.io/golf-ai-frontend
    newTag: latest
```

Then deploy with: `kubectl apply -k deploy/overlays/demo`

### Expose the service

For AKS, change the frontend service type to `LoadBalancer`:

```bash
kubectl patch svc golf-frontend -n golf-ai -p '{"spec":{"type":"LoadBalancer"}}'
```

Then get the external IP:

```bash
kubectl get svc golf-frontend -n golf-ai -w
# Wait for EXTERNAL-IP to appear
```

Or use an Ingress controller for custom domain/TLS.

---

## Architecture Overview

```
                    ┌─────────────────────────────┐
                    │   Kubernetes Cluster         │
                    │   Namespace: golf-ai         │
                    │                              │
  localhost:3001 ──►│  ┌──────────┐  ┌──────────┐ │
  (NodePort 30080)  │  │ Frontend │  │ Backend  │ │
                    │  │ (nginx)  │─►│ (FastAPI) │ │
                    │  │ port 80  │  │ port 8000│ │
                    │  └──────────┘  └────┬─────┘ │
                    │                     │       │
                    │              ┌──────┴─────┐ │
                    │              │ PVC: data  │ │
                    │              │ PVC: models│ │
                    │              └────────────┘ │
                    └─────────────────────────────┘
```

- **Frontend (nginx)**: Serves React SPA, proxies `/api/*` to backend service
- **Backend (FastAPI)**: ML pipeline — MediaPipe pose + CLIP embeddings
- **PVCs**: Persistent storage for uploaded videos, results, and model cache

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GOLF_DATA_DIR` | `/app/data` | Upload and results storage |
| `GOLF_REFERENCE_DIR` | `/app/reference_data` | Reference frame directory |
| `GOLF_MODEL_CACHE` | `/app/model_cache` | HuggingFace model cache |
| `MAX_UPLOAD_SIZE_MB` | `200` | Max video upload size |
| `INFERENCE_DEVICE` | `cpu` | PyTorch device |

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Backend pod stuck in `ContainerCreating` | PVC may not bind — check `kubectl get pvc -n golf-ai` |
| Frontend shows blank page | Check nginx config — `/assets/` must NOT proxy to backend |
| Models downloading at startup | Normal on first run (~600MB CLIP model). Pre-baked in Docker image. |
| Upload fails with 413 | Increase `client_max_body_size` in nginx.conf (default: 200M) |
| Slow analysis | Expected on CPU — ~20-30s per video. GPU not required for demo. |
