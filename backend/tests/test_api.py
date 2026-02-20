"""Tests for API endpoints."""
import pytest
import os
import sys
from pathlib import Path
from fastapi.testclient import TestClient

# Ensure the app module is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.main import app
from app.config import DATA_DIR, UPLOAD_DIR, ASSETS_DIR


@pytest.fixture
def client():
    return TestClient(app)


class TestAPI:
    def test_health(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"

    def test_upload_no_file(self, client):
        resp = client.post("/api/upload")
        assert resp.status_code == 422

    def test_upload_wrong_type(self, client):
        resp = client.post(
            "/api/upload",
            files={"file": ("test.txt", b"hello world", "text/plain")},
        )
        assert resp.status_code == 400

    def test_status_not_found(self, client):
        resp = client.get("/api/status/nonexistent")
        assert resp.status_code == 404

    def test_result_not_found(self, client):
        resp = client.get("/api/result/nonexistent")
        assert resp.status_code == 404

    def test_upload_valid_video(self, client, tmp_path):
        """Test uploading a small synthetic video."""
        import cv2
        import numpy as np

        # Create a tiny test video
        video_path = tmp_path / "test.mp4"
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        writer = cv2.VideoWriter(str(video_path), fourcc, 10, (160, 120))
        for _ in range(20):
            frame = np.random.randint(0, 255, (120, 160, 3), dtype=np.uint8)
            writer.write(frame)
        writer.release()

        with open(video_path, "rb") as f:
            resp = client.post(
                "/api/upload",
                files={"file": ("test.mp4", f, "video/mp4")},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert "job_id" in data
        assert data["message"] == "Upload successful, analysis started"

        # Check status
        job_id = data["job_id"]
        resp2 = client.get(f"/api/status/{job_id}")
        assert resp2.status_code == 200
        status_data = resp2.json()
        assert status_data["job_id"] == job_id
        assert status_data["status"] in ("queued", "processing", "completed", "failed")
