# Deployment Guide

This guide covers deploying the Golf Swing AI Analyzer to Azure Kubernetes clusters:

1. **AKS** (Azure Kubernetes Service) — managed K8s in Azure cloud
2. **AKS Arc** — AKS on Azure Stack HCI / Azure Local (hybrid/on-prem)
3. **AKS Edge Essentials** — lightweight K8s on edge devices

All deployment options use pre-built container images from `ghcr.io`. You can optionally build images yourself and push to your own Azure Container Registry (ACR).

---

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| kubectl | 1.28+ | K8s cluster management |
| Azure CLI | 2.50+ | AKS / ACR / Azure operations |
| Docker | 24+ | Only needed if building images yourself |

```bash
# Verify prerequisites
az version
kubectl version --client
az login
```

---

## Option 1: AKS (Azure Kubernetes Service)

The fastest path — deploy to a managed AKS cluster in Azure.

### Step 1: Connect to your cluster

```bash
az login
az aks get-credentials --name <your-cluster> --resource-group <your-rg>

# Verify connection
kubectl get nodes
```

### Step 2: Deploy

```bash
git clone https://github.com/nnamuhcs/aks-edge-golf-ai.git
cd aks-edge-golf-ai

kubectl apply -k deploy/base/
```

The manifests reference `ghcr.io/nnamuhcs/golf-ai-backend:latest` and `ghcr.io/nnamuhcs/golf-ai-frontend:latest`. Kubernetes pulls them automatically.

> ⏳ **First deploy note:** The backend image is approximately **6GB** because it includes all ML models (MediaPipe, CLIP ViT-B/32, PyTorch) baked in. The initial pull takes **3–10 minutes** depending on your AKS node size and network speed. The frontend image is only ~93MB and pulls almost instantly.
>
> Monitor progress: `kubectl get pods -n golf-ai -w` — wait for `ContainerCreating` → `Running`.

### Step 3: Expose via LoadBalancer

```bash
kubectl patch svc golf-frontend -n golf-ai -p '{"spec":{"type":"LoadBalancer"}}'

# Wait for Azure to assign an external IP (~1 min)
kubectl get svc golf-frontend -n golf-ai -w
```

### Step 4: Access

Open **http://\<EXTERNAL-IP\>** in your browser once the IP appears.

### Cleanup

```bash
kubectl delete namespace golf-ai
```

---

## Option 2: AKS Arc (Azure Stack HCI / Azure Local)

Deploy to an AKS Arc cluster running on your on-premises Azure Stack HCI or Azure Local infrastructure.

### Step 1: Connect to your AKS Arc cluster

```bash
az login

# Option A: Use connected cluster proxy
az connectedk8s proxy --name <arc-cluster> --resource-group <your-rg>

# Option B: Use kubeconfig from your on-prem cluster directly
export KUBECONFIG=/path/to/your/kubeconfig
```

```bash
# Verify connection
kubectl get nodes
```

### Step 2: Deploy

```bash
git clone https://github.com/nnamuhcs/aks-edge-golf-ai.git
cd aks-edge-golf-ai

kubectl apply -k deploy/base/
```

> ⏳ The backend image is ~6GB. On-prem pull speed depends on your network connection to ghcr.io. If your environment has limited internet access, consider building images and pushing to a local registry (see [Build Images Yourself](#build-images-yourself-optional) below).

### Step 3: Access via NodePort

The frontend service is exposed on **NodePort 30080** by default:

```bash
kubectl get svc golf-frontend -n golf-ai
kubectl get nodes -o wide   # Get node IP
```

Open **http://\<node-ip\>:30080**

### Cleanup

```bash
kubectl delete namespace golf-ai
```

---

## Option 3: AKS Edge Essentials

Deploy to a lightweight K3s/K8s cluster provisioned by AKS Edge Essentials on Windows IoT or edge devices.

### Step 1: Connect to your AKS Edge cluster

```bash
# AKS Edge Essentials provides a kubeconfig after provisioning
# Typically located at:
#   C:\Users\<user>\.kube\config  (Windows)
#   or exported via AKS Edge PowerShell module

kubectl get nodes
```

### Step 2: Deploy

```bash
git clone https://github.com/nnamuhcs/aks-edge-golf-ai.git
cd aks-edge-golf-ai

kubectl apply -k deploy/base/
```

> 💡 **Resource requirements:** Ensure your edge node has at least **8GB RAM** and **15GB free disk** for the ML model images. AKS Edge Essentials single-machine deployments should allocate sufficient memory to the Linux VM.

### Step 3: Access via NodePort

```bash
kubectl get svc golf-frontend -n golf-ai
```

Open **http://\<edge-node-ip\>:30080**

### Cleanup

```bash
kubectl delete namespace golf-ai
```

---

## Build Images Yourself (Optional)

If you prefer to use a private registry, need to customize the images, or have limited internet access on your cluster nodes:

### Build and push to ACR

```bash
# Create ACR (skip if you already have one)
az acr create --name <yourregistry> --resource-group <rg> --sku Basic
az acr login --name <yourregistry>

# Build images
docker build -t <yourregistry>.azurecr.io/golf-ai-backend:latest -f backend/Dockerfile backend/
docker build -t <yourregistry>.azurecr.io/golf-ai-frontend:latest -f frontend/Dockerfile frontend/

# Push to ACR
docker push <yourregistry>.azurecr.io/golf-ai-backend:latest
docker push <yourregistry>.azurecr.io/golf-ai-frontend:latest
```

> ⏳ The backend build takes ~5 minutes the first time as it downloads ML models (~600MB CLIP + MediaPipe) and bakes them into the image.

### Attach ACR to your AKS cluster

```bash
az aks update --name <cluster> --resource-group <rg> --attach-acr <yourregistry>
```

### Deploy with your registry

Edit `deploy/overlays/demo/kustomization.yaml` to point to your registry:

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

Then deploy:

```bash
kubectl apply -k deploy/overlays/demo
```

---

## Verify Deployment

These steps apply to all deployment options:

```bash
# Check pods are running
kubectl get pods -n golf-ai

# Expected output:
# NAME                             READY   STATUS    RESTARTS   AGE
# golf-backend-xxx                 1/1     Running   0          2m
# golf-frontend-xxx                1/1     Running   0          2m

# Check services
kubectl get svc -n golf-ai

# Check persistent volumes
kubectl get pvc -n golf-ai
```

---

## Architecture Overview

```
                    ┌──────────────────────────────────┐
                    │   Kubernetes Cluster              │
                    │   (AKS / AKS Arc / AKS Edge)     │
                    │   Namespace: golf-ai              │
                    │                                   │
                    │  ┌──────────┐    ┌──────────────┐ │
  LoadBalancer or ──►  │ Frontend │    │   Backend    │ │
  NodePort :30080   │  │ (nginx)  │───►│  (FastAPI)   │ │
                    │  │ port 80  │    │  port 8000   │ │
                    │  └──────────┘    └──────┬───────┘ │
                    │                         │         │
                    │                ┌────────┴───────┐ │
                    │                │  PVC: data     │ │
                    │                │  PVC: models   │ │
                    │                └────────────────┘ │
                    └──────────────────────────────────┘
```

- **Frontend (nginx)** — Serves the React SPA and proxies `/api/*` requests to the backend K8s service
- **Backend (FastAPI)** — ML inference pipeline: MediaPipe pose estimation + CLIP embedding matching
- **PVCs** — Persistent storage for uploaded videos, analysis results, and ML model cache

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
| Backend pod stuck in `ContainerCreating` | Image is ~6GB — wait for pull to complete. Check `kubectl describe pod <name> -n golf-ai` for pull progress |
| Backend pod `CrashLoopBackOff` | Check logs: `kubectl logs -n golf-ai deployment/golf-backend`. Likely insufficient memory — ensure node has ≥8GB RAM |
| PVC stuck in `Pending` | Storage class may not be available. Check `kubectl get sc` and ensure a default storage class exists |
| Frontend shows blank page | Check nginx config — `/assets/` must NOT proxy to backend |
| Upload fails with 413 | Increase `client_max_body_size` in nginx.conf (default: 200M) |
| Slow analysis | Expected on CPU — ~20-30s per video. GPU not required for demo |
| Can't pull images from ghcr.io | Ensure cluster nodes have internet access. For air-gapped environments, build and push to a local registry |
| AKS Arc: `connectedk8s proxy` fails | Ensure Arc agent is healthy: `az connectedk8s show --name <cluster> --resource-group <rg>` |
