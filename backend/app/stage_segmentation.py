"""Stage segmentation: find the best frame for each swing stage.

Approach:
  1. Isolate the swing within the video (trim non-swing footage)
  2. Detect video speed (normal vs slow-motion) for adaptive sampling
  3. Compute full-body metrics for every frame in the swing window
  4. Compare each frame against all 8 reference stage profiles
  5. Use dynamic programming to find optimal monotonic assignment
     that maximizes total body similarity across all stages
"""
import json
import numpy as np
import cv2
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from .config import SWING_STAGES
from .pose_estimator import compute_body_metrics

logger = logging.getLogger(__name__)

# Load reference stage profiles (learned from verified reference frames)
_PROFILES_PATH = Path(__file__).parent / "stage_profiles.json"
_STAGE_PROFILES: Dict[str, dict] = {}
if _PROFILES_PATH.exists():
    with open(_PROFILES_PATH) as f:
        _STAGE_PROFILES = json.load(f)
    logger.info(f"Loaded {len(_STAGE_PROFILES)} stage profiles from {_PROFILES_PATH.name}")

# Metrics used for similarity comparison (all body parts)
_COMPARE_METRICS = [
    "shoulder_tilt", "hip_tilt", "hip_shoulder_separation",
    "spine_angle", "left_knee_angle", "right_knee_angle",
    "left_arm_angle", "right_arm_angle",
    "left_wrist_height", "right_wrist_height",
]

# Normalization ranges for each metric (approximate ranges in degrees/units)
_METRIC_RANGES = {
    "shoulder_tilt": 60.0,       # -30° to +30°
    "hip_tilt": 30.0,            # -15° to +15°
    "hip_shoulder_separation": 40.0,  # 0° to 40°
    "spine_angle": 50.0,         # 0° to 50°
    "left_knee_angle": 80.0,     # 100° to 180°
    "right_knee_angle": 80.0,
    "left_arm_angle": 180.0,     # 0° to 180°
    "right_arm_angle": 180.0,
    "left_wrist_height": 0.5,    # 0.2 to 0.7 (normalized)
    "right_wrist_height": 0.5,
}


def _compute_motion_energy(frames: List) -> np.ndarray:
    """Compute frame-to-frame motion energy (pixel difference)."""
    n = len(frames)
    motion = np.zeros(n)
    if n < 2:
        return motion
    prev = cv2.cvtColor(frames[0], cv2.COLOR_BGR2GRAY)
    prev = cv2.resize(prev, (160, 120))
    for i in range(1, n):
        gray = cv2.cvtColor(frames[i], cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, (160, 120))
        motion[i] = float(np.mean(cv2.absdiff(prev, gray)))
        prev = gray
    return motion


def _smooth(arr: np.ndarray, window: int = 5) -> np.ndarray:
    """Simple moving average smoothing."""
    k = max(3, window)
    if k % 2 == 0:
        k += 1
    kernel = np.ones(k) / k
    return np.convolve(arr, kernel, mode='same')


def _isolate_swing(motion: np.ndarray, n: int) -> Tuple[int, int]:
    """Find the start and end of the actual swing within the video.

    The swing is the main burst of motion. We find it by looking for
    the sustained high-motion region.
    """
    if n < 10:
        return 0, n - 1

    # Smooth motion to find the envelope
    smoothed = _smooth(motion, max(5, n // 10))
    threshold = np.max(smoothed) * 0.15  # 15% of peak motion

    # Find first and last frames above threshold
    above = np.where(smoothed > threshold)[0]
    if len(above) < 3:
        return 0, n - 1

    # Expand window to include setup (address) before and finish after
    swing_start = max(0, above[0] - max(3, n // 10))
    swing_end = min(n - 1, above[-1] + max(3, n // 15))

    logger.info(f"Swing isolated: frames {swing_start}-{swing_end} "
                f"(of {n} total, motion threshold={threshold:.1f})")
    return swing_start, swing_end


def _compute_frame_metrics(
    poses: List[Optional[Dict]],
) -> List[Optional[Dict[str, float]]]:
    """Compute full body metrics for every frame that has a valid pose."""
    result = []
    for p in poses:
        if p is not None:
            try:
                metrics = compute_body_metrics(p)
                # Also add hand position features
                lw = p.get("left_wrist", (0.5, 0.5, 0))
                rw = p.get("right_wrist", (0.5, 0.5, 0))
                ls = p.get("left_shoulder", (0.5, 0.5, 0))
                rs = p.get("right_shoulder", (0.5, 0.5, 0))
                avg_shoulder_y = (ls[1] + rs[1]) / 2
                avg_shoulder_x = (ls[0] + rs[0]) / 2
                metrics["avg_wrist_y"] = (lw[1] + rw[1]) / 2
                metrics["avg_wrist_x"] = (lw[0] + rw[0]) / 2
                metrics["hands_height"] = avg_shoulder_y - metrics["avg_wrist_y"]
                metrics["hands_lateral"] = metrics["avg_wrist_x"] - avg_shoulder_x
                result.append(metrics)
            except Exception:
                result.append(None)
        else:
            result.append(None)
    return result


def _body_similarity(frame_metrics: Dict[str, float], stage: str) -> float:
    """Compute full-body similarity between a frame and a reference stage profile.

    Compares ALL body metrics (shoulders, hips, spine, knees, arms, wrists)
    and returns a 0-1 score where 1 = identical to reference.
    """
    if stage not in _STAGE_PROFILES:
        return 0.0

    prof = _STAGE_PROFILES[stage]
    ref_metrics = prof.get("metrics", {})

    total_diff = 0.0
    count = 0

    # Compare all body metrics (normalized by expected range)
    for metric in _COMPARE_METRICS:
        ref_val = ref_metrics.get(metric)
        frame_val = frame_metrics.get(metric)
        if ref_val is not None and frame_val is not None:
            range_val = _METRIC_RANGES.get(metric, 50.0)
            normalized_diff = abs(frame_val - ref_val) / range_val
            total_diff += normalized_diff
            count += 1

    # Also compare hand position features
    for feat, ref_key, weight in [
        ("avg_wrist_y", "avg_wrist_y", 2.0),
        ("hands_height", "hands_height_above_shoulders", 1.5),
        ("hands_lateral", "hands_lateral_offset", 1.5),
    ]:
        frame_val = frame_metrics.get(feat)
        ref_val = prof.get(ref_key)
        if frame_val is not None and ref_val is not None:
            normalized_diff = abs(frame_val - ref_val) / 0.3  # normalize by ~0.3 range
            total_diff += normalized_diff * weight
            count += weight

    if count == 0:
        return 0.0

    avg_diff = total_diff / count
    # Exponential similarity: small diff → high score, large diff → near 0
    return float(np.exp(-avg_diff * 3.0))


def _optimal_stage_assignment(
    similarity_matrix: np.ndarray,
    n_frames: int,
    swing_start: int,
) -> List[int]:
    """Dynamic programming to find the best monotonically-increasing
    assignment of frames to stages that maximizes total similarity.

    similarity_matrix: shape (n_frames, 8) — similarity of each frame to each stage
    Returns: list of 8 frame indices (within the swing window)
    """
    n_stages = 8
    n = n_frames

    if n < n_stages:
        return list(range(min(n, n_stages)))

    # DP: best[s][f] = max total similarity assigning stages 0..s to frames ending at f
    # choice[s][f] = which frame was chosen for stage s-1
    INF = -1e9
    best = np.full((n_stages, n), INF)
    choice = np.full((n_stages, n), -1, dtype=int)

    # Stage 0: can be any frame
    for f in range(n):
        best[0][f] = similarity_matrix[f, 0]

    # Stages 1..7: must come after previous stage's frame
    for s in range(1, n_stages):
        running_max = INF
        running_best_f = 0
        for f in range(n):
            # Update running max from previous stage up to f-1
            if f > 0 and best[s-1][f-1] > running_max:
                running_max = best[s-1][f-1]
                running_best_f = f - 1
            if running_max > INF:
                score = running_max + similarity_matrix[f, s]
                if score > best[s][f]:
                    best[s][f] = score
                    choice[s][f] = running_best_f

    # Backtrack: find the best ending frame for the last stage
    last_f = int(np.argmax(best[n_stages - 1]))
    result = [0] * n_stages
    result[n_stages - 1] = last_f

    for s in range(n_stages - 2, -1, -1):
        result[s] = choice[s + 1][result[s + 1]]

    # Convert to global frame indices
    return [swing_start + f for f in result]


def segment_swing_stages(
    poses: List[Optional[Dict]],
    num_frames: int,
    frames: List = None,
) -> Dict[str, int]:
    """Find the best representative frame for each swing stage.

    New approach:
      1. Isolate the swing (trim non-swing footage)
      2. Compute full-body metrics for every frame
      3. Compare each frame against all 8 reference profiles
      4. Use DP to find optimal monotonic assignment maximizing body similarity
    """
    n = len(poses)

    # Fallback for very short videos or missing poses
    if n < 8:
        indices = np.linspace(0, n - 1, 8, dtype=int)
        return {stage: int(idx) for stage, idx in zip(SWING_STAGES, indices)}

    valid_poses = sum(1 for p in poses if p is not None)
    if valid_poses < n * 0.3:
        logger.warning(f"Only {valid_poses}/{n} frames have valid poses, using fallback")
        fracs = [0.06, 0.18, 0.32, 0.47, 0.60, 0.72, 0.87, 0.97]
        indices = [max(0, min(int(f * (n - 1)), n - 1)) for f in fracs]
        return {stage: idx for stage, idx in zip(SWING_STAGES, indices)}

    # Check if we have reference profiles
    if len(_STAGE_PROFILES) < 8:
        logger.warning("Missing stage profiles, falling back to heuristic method")
        return _fallback_heuristic(poses, n, frames)

    # Step 1: Compute motion and isolate swing
    motion = np.zeros(n)
    if frames is not None and len(frames) == n:
        motion = _compute_motion_energy(frames)

    swing_start, swing_end = _isolate_swing(motion, n)
    swing_n = swing_end - swing_start + 1

    if swing_n < 8:
        swing_start = 0
        swing_end = n - 1
        swing_n = n

    # Step 2: Compute full-body metrics for frames in swing window
    swing_poses = poses[swing_start:swing_end + 1]
    all_metrics = _compute_frame_metrics(swing_poses)

    # Step 3: Build similarity matrix (swing_frames × 8 stages)
    similarity_matrix = np.zeros((swing_n, 8))

    for f_idx in range(swing_n):
        fm = all_metrics[f_idx]
        if fm is None:
            # No pose detected — low similarity to everything
            similarity_matrix[f_idx, :] = 0.01
            continue
        for s_idx, stage in enumerate(SWING_STAGES):
            similarity_matrix[f_idx, s_idx] = _body_similarity(fm, stage)

    # Step 4: Optimal assignment via DP
    global_indices = _optimal_stage_assignment(
        similarity_matrix, swing_n, swing_start
    )

    # Clamp to valid range
    global_indices = [max(0, min(idx, n - 1)) for idx in global_indices]

    result = {stage: idx for stage, idx in zip(SWING_STAGES, global_indices)}

    logger.info(f"Stage detection (profile-based DP): {result}")
    for stage, idx in result.items():
        sim = 0.0
        fm = all_metrics[idx - swing_start] if swing_start <= idx <= swing_end else None
        if fm:
            sim = _body_similarity(fm, stage)
        logger.info(f"  {stage:20s} → frame {idx:3d}  (similarity={sim:.3f})")

    return result


def _fallback_heuristic(
    poses: List[Optional[Dict]],
    n: int,
    frames: List = None,
) -> Dict[str, int]:
    """Legacy heuristic fallback when profiles are not available."""
    fracs = [0.06, 0.18, 0.32, 0.47, 0.60, 0.72, 0.87, 0.97]
    indices = [max(0, min(int(f * (n - 1)), n - 1)) for f in fracs]
    return {stage: idx for stage, idx in zip(SWING_STAGES, indices)}
