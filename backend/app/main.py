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

from .config import UPLOAD_DIR, ASSETS_DIR, MAX_UPLOAD_SIZE_MB
from .pipeline import create_job, get_job, run_analysis

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Golf Swing AI Analyzer",
    description="Upload a golf swing video for AI-powered analysis",
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


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "golf-swing-ai"}


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
