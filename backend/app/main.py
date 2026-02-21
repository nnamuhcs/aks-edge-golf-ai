"""FastAPI application – REST API for Golf Swing AI Analyzer."""
import os
import shutil
import threading
import logging
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse

import time
import collections

from .config import UPLOAD_DIR, ASSETS_DIR, MAX_UPLOAD_SIZE_MB
from .pipeline import create_job, get_job, run_analysis

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Activity feed for K8s panel (ring buffer of recent events)
_activity_log = collections.deque(maxlen=100)
_start_time = time.time()


def log_activity(event_type: str, message: str, detail: str = ""):
    """Record an activity event for the K8s panel feed."""
    _activity_log.append({
        "ts": time.time(),
        "elapsed": round(time.time() - _start_time, 1),
        "type": event_type,
        "message": message,
        "detail": detail,
    })

app = FastAPI(
    title="Golf Swing AI Coacher",
    description="Upload a golf swing video for AI-powered coaching",
    version="1.0.0",
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve generated analysis assets (images)
app.mount("/results-assets", StaticFiles(directory=str(ASSETS_DIR)), name="assets")

# Serve pre-generated static reference screenshots
_static_refs = Path(__file__).resolve().parent.parent / "static" / "references"
_static_refs.mkdir(parents=True, exist_ok=True)
app.mount("/static/references", StaticFiles(directory=str(_static_refs)), name="references")


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "golf-swing-ai"}


@app.get("/api/k8s/status")
async def k8s_status():
    """Return K8s component status, system metrics, and recent activity feed."""
    import socket
    import psutil
    hostname = socket.gethostname()
    pod_ip = socket.gethostbyname(hostname)

    # Detect if running in K8s
    in_k8s = os.path.exists("/var/run/secrets/kubernetes.io/serviceaccount/token")

    namespace = "default"
    if in_k8s:
        try:
            namespace = open("/var/run/secrets/kubernetes.io/serviceaccount/namespace").read().strip()
        except Exception:
            pass

    uptime = round(time.time() - _start_time)
    hours, rem = divmod(uptime, 3600)
    mins, secs = divmod(rem, 60)
    uptime_str = f"{hours}h {mins}m {secs}s" if hours else f"{mins}m {secs}s"

    # ── Real system metrics ──
    cpu_percent = psutil.cpu_percent(interval=0)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    disk_io = psutil.disk_io_counters()
    net_io = psutil.net_io_counters()
    proc = psutil.Process(os.getpid())
    proc_mem = proc.memory_info()

    metrics = {
        "cpu_percent": round(cpu_percent, 1),
        "cpu_cores": psutil.cpu_count(),
        "mem_used_gb": round(mem.used / (1024**3), 2),
        "mem_total_gb": round(mem.total / (1024**3), 2),
        "mem_percent": round(mem.percent, 1),
        "disk_used_gb": round(disk.used / (1024**3), 1),
        "disk_total_gb": round(disk.total / (1024**3), 1),
        "disk_percent": round(disk.percent, 1),
        "disk_read_mb": round(disk_io.read_bytes / (1024**2), 1) if disk_io else 0,
        "disk_write_mb": round(disk_io.write_bytes / (1024**2), 1) if disk_io else 0,
        "net_sent_mb": round(net_io.bytes_sent / (1024**2), 1) if net_io else 0,
        "net_recv_mb": round(net_io.bytes_recv / (1024**2), 1) if net_io else 0,
        "proc_mem_mb": round(proc_mem.rss / (1024**2), 1),
    }

    components = [
        {
            "name": "golf-ai-backend",
            "kind": "Pod" if in_k8s else "Process",
            "status": "Running",
            "ready": True,
            "info": f"{hostname} ({pod_ip})",
            "uptime": uptime_str,
        },
        {
            "name": "golf-ai-api",
            "kind": "Service",
            "status": "Active",
            "ready": True,
            "info": "ClusterIP :8000" if in_k8s else f"localhost:8000",
            "uptime": uptime_str,
        },
        {
            "name": "mediapipe-pose",
            "kind": "Model",
            "status": "Loaded",
            "ready": True,
            "info": "Heavy model, CPU",
            "uptime": "",
        },
        {
            "name": "clip-vit-b32",
            "kind": "Model",
            "status": "Loaded",
            "ready": True,
            "info": "HuggingFace ViT-B/32",
            "uptime": "",
        },
    ]

    if in_k8s:
        components.append({
            "name": "model-cache",
            "kind": "PVC",
            "status": "Bound",
            "ready": True,
            "info": f"ns/{namespace}",
            "uptime": "",
        })
        components.append({
            "name": "golf-ai-ingress",
            "kind": "Ingress",
            "status": "Active",
            "ready": True,
            "info": f"ns/{namespace}",
            "uptime": "",
        })

    # Recent activity (last 20 key events only)
    activity = list(_activity_log)[-20:]

    return {
        "namespace": namespace,
        "in_k8s": in_k8s,
        "components": components,
        "metrics": metrics,
        "activity": activity,
    }


@app.post("/api/k8s/clear-activity")
async def clear_activity():
    """Clear the activity log."""
    _activity_log.clear()
    return {"status": "cleared"}


@app.post("/api/upload")
async def upload_video(file: UploadFile = File(...)):
    """Upload a golf swing video for analysis."""
    # Validate file type
    allowed_types = {
        "video/mp4", "video/quicktime", "video/x-msvideo",
        "video/webm", "video/mpeg", "application/octet-stream",
    }
    content_type = file.content_type or "application/octet-stream"

    # Check extension as fallback
    ext = Path(file.filename or "video.mp4").suffix.lower()
    allowed_exts = {".mp4", ".mov", ".avi", ".webm", ".mkv", ".mpeg"}
    if content_type not in allowed_types and ext not in allowed_exts:
        raise HTTPException(400, f"Unsupported file type: {content_type} ({ext})")

    # Save uploaded file
    safe_name = f"{os.urandom(8).hex()}{ext}"
    dest = UPLOAD_DIR / safe_name

    try:
        size = 0
        max_bytes = MAX_UPLOAD_SIZE_MB * 1024 * 1024
        with open(dest, "wb") as f:
            while True:
                chunk = await file.read(1024 * 1024)  # 1MB chunks
                if not chunk:
                    break
                size += len(chunk)
                if size > max_bytes:
                    f.close()
                    dest.unlink(missing_ok=True)
                    raise HTTPException(413, f"File too large. Max {MAX_UPLOAD_SIZE_MB}MB")
                f.write(chunk)
    except HTTPException:
        raise
    except Exception as e:
        dest.unlink(missing_ok=True)
        raise HTTPException(500, f"Upload failed: {str(e)}")

    # Create job and start analysis
    job_id = create_job(safe_name)
    thread = threading.Thread(target=run_analysis, args=(job_id,), daemon=True)
    thread.start()

    logger.info(f"Job {job_id} created for {file.filename} ({size} bytes)")
    log_activity("upload", f"Video uploaded: {file.filename}", f"{size / 1024 / 1024:.1f} MB → job {job_id[:8]}")
    log_activity("pipeline", "Analysis job started", f"Job {job_id[:8]} queued for processing")
    return {"job_id": job_id, "message": "Upload successful, analysis started"}


@app.get("/api/status/{job_id}")
async def get_status(job_id: str):
    """Get the status of an analysis job."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")

    return {
        "job_id": job["job_id"],
        "status": job["status"],
        "progress": job["progress"],
        "message": job["message"],
    }


@app.get("/api/result/{job_id}")
async def get_result(job_id: str):
    """Get the analysis result for a completed job."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")

    if job["status"] == "processing" or job["status"] == "queued":
        return JSONResponse(
            status_code=202,
            content={"status": job["status"], "progress": job["progress"],
                     "message": "Analysis in progress"},
        )

    if job["status"] == "failed":
        raise HTTPException(500, f"Analysis failed: {job.get('error', 'Unknown error')}")

    return job["result"]


# Serve frontend static files (built Vite app)
_frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if _frontend_dist.is_dir():
    # Mount Vite's /assets (JS/CSS bundles) under /assets
    _fe_assets = _frontend_dist / "assets"
    if _fe_assets.is_dir():
        app.mount("/assets", StaticFiles(directory=str(_fe_assets)), name="fe-assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(request: Request, full_path: str):
        """Serve the frontend SPA – any non-API path returns index.html."""
        file_path = _frontend_dist / full_path
        if full_path and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(_frontend_dist / "index.html")
else:
    logger.warning(f"Frontend dist not found at {_frontend_dist}. Run 'cd frontend && npm run build'")
