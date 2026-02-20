"""Pose estimation using MediaPipe Tasks API (v0.10.x+)."""
import cv2
import numpy as np
import mediapipe as mp
import urllib.request
import os
from pathlib import Path
from typing import List, Optional, Dict, Tuple

# MediaPipe Pose landmark indices (same numbering as legacy API)
LANDMARK_NAMES = {
    0: "nose", 11: "left_shoulder", 12: "right_shoulder",
    13: "left_elbow", 14: "right_elbow", 15: "left_wrist", 16: "right_wrist",
    23: "left_hip", 24: "right_hip", 25: "left_knee", 26: "right_knee",
    27: "left_ankle", 28: "right_ankle",
}

MODEL_URL = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task"


def _ensure_model(cache_dir: str = None) -> str:
    """Download pose landmarker model if not already cached."""
    if cache_dir is None:
        cache_dir = os.environ.get("GOLF_MODEL_CACHE", "/tmp")
    model_path = os.path.join(cache_dir, "pose_landmarker_lite.task")
    if not os.path.exists(model_path):
        os.makedirs(cache_dir, exist_ok=True)
        urllib.request.urlretrieve(MODEL_URL, model_path)
    return model_path


class PoseEstimator:
    """Wraps MediaPipe PoseLandmarker (Tasks API) for golf swing analysis."""

    def __init__(self, model_path: str = None):
        if model_path is None:
            model_path = _ensure_model()

        BaseOptions = mp.tasks.BaseOptions
        PoseLandmarkerOptions = mp.tasks.vision.PoseLandmarkerOptions
        VisionRunningMode = mp.tasks.vision.RunningMode

        options = PoseLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=model_path),
            running_mode=VisionRunningMode.IMAGE,
            num_poses=1,
            min_pose_detection_confidence=0.5,
            min_pose_presence_confidence=0.5,
        )
        self.landmarker = mp.tasks.vision.PoseLandmarker.create_from_options(options)

    def detect(self, frame_bgr: np.ndarray) -> Optional[Dict[str, Tuple[float, float, float]]]:
        """Detect pose landmarks in a frame.

        Returns dict mapping landmark name -> (x, y, z) normalized coords,
        or None if no pose detected.
        """
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
        result = self.landmarker.detect(mp_image)

        if not result.pose_landmarks or len(result.pose_landmarks) == 0:
            return None

        pose_lms = result.pose_landmarks[0]
        landmarks = {}
        for idx, name in LANDMARK_NAMES.items():
            if idx < len(pose_lms):
                lm = pose_lms[idx]
                landmarks[name] = (lm.x, lm.y, lm.z)
        return landmarks

    def detect_batch(self, frames: List[np.ndarray]) -> List[Optional[Dict]]:
        """Detect poses for a batch of frames."""
        return [self.detect(f) for f in frames]

    def close(self):
        self.landmarker.close()


def compute_angle(p1: Tuple[float, float], p2: Tuple[float, float], p3: Tuple[float, float]) -> float:
    """Compute angle at p2 formed by p1-p2-p3, in degrees."""
    v1 = np.array([p1[0] - p2[0], p1[1] - p2[1]])
    v2 = np.array([p3[0] - p2[0], p3[1] - p2[1]])
    cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-8)
    return float(np.degrees(np.arccos(np.clip(cos_angle, -1, 1))))


def compute_body_metrics(landmarks: Dict[str, Tuple[float, float, float]]) -> Dict[str, float]:
    """Compute golf-relevant body metrics from landmarks."""
    metrics = {}

    ls = landmarks.get("left_shoulder", (0, 0, 0))
    rs = landmarks.get("right_shoulder", (0, 0, 0))
    lh = landmarks.get("left_hip", (0, 0, 0))
    rh = landmarks.get("right_hip", (0, 0, 0))
    lk = landmarks.get("left_knee", (0, 0, 0))
    rk = landmarks.get("right_knee", (0, 0, 0))
    la = landmarks.get("left_ankle", (0, 0, 0))
    ra = landmarks.get("right_ankle", (0, 0, 0))
    le = landmarks.get("left_elbow", (0, 0, 0))
    re = landmarks.get("right_elbow", (0, 0, 0))
    lw = landmarks.get("left_wrist", (0, 0, 0))
    rw = landmarks.get("right_wrist", (0, 0, 0))
    nose = landmarks.get("nose", (0, 0, 0))

    # Shoulder tilt (degrees from horizontal)
    shoulder_dx = rs[0] - ls[0]
    shoulder_dy = rs[1] - ls[1]
    metrics["shoulder_tilt"] = float(np.degrees(np.arctan2(shoulder_dy, shoulder_dx + 1e-8)))

    # Hip tilt
    hip_dx = rh[0] - lh[0]
    hip_dy = rh[1] - lh[1]
    metrics["hip_tilt"] = float(np.degrees(np.arctan2(hip_dy, hip_dx + 1e-8)))

    # Hip-shoulder separation (X-factor proxy)
    metrics["hip_shoulder_separation"] = abs(metrics["shoulder_tilt"] - metrics["hip_tilt"])

    # Spine angle (mid-shoulder to mid-hip vs vertical)
    mid_s = ((ls[0] + rs[0]) / 2, (ls[1] + rs[1]) / 2)
    mid_h = ((lh[0] + rh[0]) / 2, (lh[1] + rh[1]) / 2)
    spine_angle = float(np.degrees(np.arctan2(mid_s[0] - mid_h[0], mid_h[1] - mid_s[1] + 1e-8)))
    metrics["spine_angle"] = abs(spine_angle)

    # Knee flex (left)
    metrics["left_knee_angle"] = compute_angle(lh[:2], lk[:2], la[:2])
    # Knee flex (right)
    metrics["right_knee_angle"] = compute_angle(rh[:2], rk[:2], ra[:2])

    # Lead arm straightness (left elbow angle)
    metrics["left_arm_angle"] = compute_angle(ls[:2], le[:2], lw[:2])
    # Trail arm (right elbow angle)
    metrics["right_arm_angle"] = compute_angle(rs[:2], re[:2], rw[:2])

    # Head position relative to mid-hip (stability indicator)
    metrics["head_sway"] = abs(nose[0] - mid_h[0])

    # Wrist height (proxy for club position)
    metrics["left_wrist_height"] = lw[1]
    metrics["right_wrist_height"] = rw[1]

    # Stance width
    metrics["stance_width"] = abs(la[0] - ra[0])

    return metrics
