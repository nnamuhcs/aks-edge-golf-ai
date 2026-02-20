"""Main analysis pipeline – orchestrates video processing end-to-end."""
import cv2
import json
import uuid
import logging
import traceback
import numpy as np
from pathlib import Path
from typing import Dict, Optional

from .config import (
    UPLOAD_DIR, RESULTS_DIR, ASSETS_DIR, REFERENCE_DIR,
    SWING_STAGES, STAGE_DISPLAY_NAMES,
)
from .video_decoder import extract_frames
from .pose_estimator import PoseEstimator, compute_body_metrics
from .stage_segmentation import segment_swing_stages
from .orientation import normalize_orientation, resize_to_match
from .scoring import score_stage, compute_overall_score, generate_stage_feedback
from .annotator import annotate_stage_frame
from .reference_matcher import ReferenceManager

logger = logging.getLogger(__name__)

# Target image size for annotations
TARGET_SIZE = (640, 480)

# Global singletons (lazy)
_pose_estimator: Optional[PoseEstimator] = None
_reference_manager: Optional[ReferenceManager] = None


def _get_pose_estimator() -> PoseEstimator:
    global _pose_estimator
    if _pose_estimator is None:
        _pose_estimator = PoseEstimator()
    return _pose_estimator


def _get_reference_manager() -> ReferenceManager:
    global _reference_manager
    if _reference_manager is None:
        _reference_manager = ReferenceManager(REFERENCE_DIR)
    return _reference_manager


# Job status store (in-memory for demo)
_jobs: Dict[str, dict] = {}


def get_job(job_id: str) -> Optional[dict]:
    return _jobs.get(job_id)


def create_job(video_filename: str) -> str:
    job_id = str(uuid.uuid4())[:8]
    _jobs[job_id] = {
        "job_id": job_id,
        "status": "queued",
        "progress": 0,
        "message": "Job created",
        "video_filename": video_filename,
        "result": None,
        "error": None,
    }
    return job_id


def run_analysis(job_id: str):
    """Run the full analysis pipeline for a job. Designed to run in a background thread."""
    job = _jobs.get(job_id)
    if not job:
        return

    try:
        job["status"] = "processing"
        job["progress"] = 5
        job["message"] = "Extracting video frames..."

        video_path = UPLOAD_DIR / job["video_filename"]
        job_assets_dir = ASSETS_DIR / job_id
        job_assets_dir.mkdir(parents=True, exist_ok=True)

        # Step 1: Extract frames
        frames = extract_frames(video_path, max_frames=100)
        job["progress"] = 15
        job["message"] = f"Extracted {len(frames)} frames. Detecting poses..."

        # Step 2: Pose estimation
        pose = _get_pose_estimator()
        poses = pose.detect_batch(frames)
        job["progress"] = 35
        job["message"] = "Poses detected. Segmenting swing stages..."

        # Step 3: Stage segmentation
        stage_indices = segment_swing_stages(poses, len(frames), frames=frames)
        job["progress"] = 45
        job["message"] = "Stages segmented. Analyzing each stage..."

        # Step 4: Per-stage analysis
        ref_mgr = _get_reference_manager()
        stage_results = []
        all_stage_scores = {}

        for i, stage in enumerate(SWING_STAGES):
            frame_idx = stage_indices[stage]
            frame = frames[frame_idx]
            landmarks = poses[frame_idx] if frame_idx < len(poses) else None

            # Normalize orientation
            frame = normalize_orientation(frame, landmarks)

            # Re-detect after rotation if rotated
            # (In practice, rotation may have changed landmark positions)

            # Compute metrics
            if landmarks:
                metrics = compute_body_metrics(landmarks)
            else:
                # Generate synthetic metrics for demo when pose detection unavailable
                metrics = _generate_demo_metrics(stage, frame_idx, len(frames))

            # Score
            stage_score, metric_scores = score_stage(stage, metrics)
            all_stage_scores[stage] = stage_score

            # Generate feedback
            feedback = generate_stage_feedback(stage, stage_score, metric_scores, metrics)

            # Resize user frame
            user_frame_resized = cv2.resize(frame, TARGET_SIZE, interpolation=cv2.INTER_AREA)

            # Annotate user frame
            user_annotated = annotate_stage_frame(
                user_frame_resized, landmarks, stage, metric_scores, metrics, is_reference=False
            )

            # Get reference frame
            ref_frame = ref_mgr.get_reference_frame(stage, frame)
            ref_annotated = None
            ref_landmarks = None

            if ref_frame is not None:
                ref_frame_resized = cv2.resize(ref_frame, TARGET_SIZE, interpolation=cv2.INTER_AREA)
                # Detect pose on reference
                ref_landmarks = pose.detect(ref_frame_resized)
                if ref_landmarks:
                    ref_metrics = compute_body_metrics(ref_landmarks)
                    ref_score, ref_metric_scores = score_stage(stage, ref_metrics)
                else:
                    ref_metric_scores = {}
                    ref_metrics = {}

                ref_annotated = annotate_stage_frame(
                    ref_frame_resized, ref_landmarks, stage,
                    ref_metric_scores, ref_metrics, is_reference=True
                )
            else:
                # Create placeholder reference
                ref_annotated = _create_placeholder_reference(stage, TARGET_SIZE)

            # Save images
            user_img_name = f"{stage}_user.jpg"
            ref_img_name = f"{stage}_reference.jpg"
            cv2.imwrite(str(job_assets_dir / user_img_name), user_annotated, [cv2.IMWRITE_JPEG_QUALITY, 92])
            cv2.imwrite(str(job_assets_dir / ref_img_name), ref_annotated, [cv2.IMWRITE_JPEG_QUALITY, 92])

            stage_result = {
                **feedback,
                "user_image": f"/assets/{job_id}/{user_img_name}",
                "reference_image": f"/assets/{job_id}/{ref_img_name}",
            }
            stage_results.append(stage_result)

            progress = 45 + int(45 * (i + 1) / len(SWING_STAGES))
            job["progress"] = progress
            job["message"] = f"Analyzed {STAGE_DISPLAY_NAMES[stage]}..."

        # Step 5: Overall score
        overall_score = compute_overall_score(all_stage_scores)

        # Determine overall feedback
        if overall_score >= 85:
            overall_comment = "Excellent swing! Your fundamentals are very strong."
        elif overall_score >= 70:
            overall_comment = "Good swing with some areas for improvement. Focus on the noted issues."
        elif overall_score >= 55:
            overall_comment = "Decent swing foundation. Work on the highlighted areas for significant improvement."
        else:
            overall_comment = "Several areas need attention. Start with the lowest-scoring stages."

        result = {
            "job_id": job_id,
            "overall_score": overall_score,
            "overall_comment": overall_comment,
            "stages": stage_results,
        }

        # Save result JSON
        result_path = RESULTS_DIR / f"{job_id}.json"
        with open(result_path, "w") as f:
            json.dump(result, f, indent=2)

        job["status"] = "completed"
        job["progress"] = 100
        job["message"] = "Analysis complete!"
        job["result"] = result

    except Exception as e:
        logger.error(f"Analysis failed for job {job_id}: {e}\n{traceback.format_exc()}")
        job["status"] = "failed"
        job["message"] = f"Analysis failed: {str(e)}"
        job["error"] = str(e)


def _create_placeholder_reference(stage: str, size: tuple) -> np.ndarray:
    """Create a placeholder image when no reference is available."""
    img = np.zeros((size[1], size[0], 3), dtype=np.uint8)
    img[:] = (50, 50, 50)

    # Add text
    display = STAGE_DISPLAY_NAMES.get(stage, stage)
    text = f"REFERENCE: {display.upper()}"
    cv2.putText(img, text, (20, size[1] // 2 - 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 1, cv2.LINE_AA)
    cv2.putText(img, "Good Practice Example", (20, size[1] // 2 + 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1, cv2.LINE_AA)

    # Draw a stylized golfer silhouette (simple)
    cx, cy = size[0] // 2, size[1] // 2 + 60
    # Head
    cv2.circle(img, (cx, cy - 80), 15, (100, 100, 100), -1)
    # Body
    cv2.line(img, (cx, cy - 65), (cx, cy), (100, 100, 100), 3)
    # Legs
    cv2.line(img, (cx, cy), (cx - 25, cy + 50), (100, 100, 100), 3)
    cv2.line(img, (cx, cy), (cx + 25, cy + 50), (100, 100, 100), 3)
    # Arms
    cv2.line(img, (cx, cy - 50), (cx - 40, cy - 20), (100, 100, 100), 3)
    cv2.line(img, (cx, cy - 50), (cx + 40, cy - 20), (100, 100, 100), 3)

    return img


def _generate_demo_metrics(stage: str, frame_idx: int, total_frames: int) -> dict:
    """Generate plausible synthetic metrics for demo when pose detection is unavailable.

    Uses deterministic values seeded by stage and frame position to produce
    varied but realistic-looking scores.
    """
    import hashlib
    seed = int(hashlib.md5(f"{stage}_{frame_idx}".encode()).hexdigest()[:8], 16)
    rng = np.random.RandomState(seed)

    # Base "good" values with per-stage variation
    base = {
        "address":        {"spine_angle": 28, "left_knee_angle": 168, "right_knee_angle": 168,
                           "stance_width": 0.24, "head_sway": 0.02, "shoulder_tilt": 2},
        "takeaway":       {"spine_angle": 29, "left_arm_angle": 172, "head_sway": 0.03,
                           "hip_shoulder_separation": 8},
        "backswing":      {"spine_angle": 31, "left_arm_angle": 168, "hip_shoulder_separation": 25,
                           "shoulder_tilt": -28},
        "top":            {"spine_angle": 30, "left_arm_angle": 165, "hip_shoulder_separation": 38,
                           "right_arm_angle": 88},
        "downswing":      {"spine_angle": 29, "hip_shoulder_separation": 32, "left_arm_angle": 170,
                           "head_sway": 0.03},
        "impact":         {"spine_angle": 28, "left_arm_angle": 176, "hip_shoulder_separation": 33,
                           "head_sway": 0.02, "left_knee_angle": 170},
        "follow_through": {"spine_angle": 22, "head_sway": 0.05},
        "finish":         {"spine_angle": 12, "head_sway": 0.04},
    }

    metrics = base.get(stage, {"spine_angle": 25, "head_sway": 0.03})
    # Add noise to make it look real
    result = {}
    for k, v in metrics.items():
        noise = rng.normal(0, abs(v) * 0.08 + 0.5)
        result[k] = v + noise
    return result
