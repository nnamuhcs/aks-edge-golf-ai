"""Stage segmentation: classify each frame to find the best match for each swing stage."""
import json
import numpy as np
import cv2
import logging
from pathlib import Path
from typing import List, Dict, Optional
from .config import SWING_STAGES

logger = logging.getLogger(__name__)

# Load reference stage profiles (learned from verified reference frames)
_PROFILES_PATH = Path(__file__).parent / "stage_profiles.json"
_STAGE_PROFILES: Dict[str, dict] = {}
if _PROFILES_PATH.exists():
    with open(_PROFILES_PATH) as f:
        _STAGE_PROFILES = json.load(f)
    logger.info(f"Loaded {len(_STAGE_PROFILES)} stage profiles from {_PROFILES_PATH.name}")


def _smooth(arr: np.ndarray, n: int) -> np.ndarray:
    k = max(3, n // 15)
    if k % 2 == 0:
        k += 1
    kernel = np.ones(k) / k
    return np.convolve(arr, kernel, mode='same')


def _compute_frame_features(
    poses: List[Optional[Dict]],
    frames: List,
) -> Dict[str, np.ndarray]:
    """Compute per-frame features useful for stage classification."""
    n = len(poses)
    features = {
        "wrist_y": np.full(n, 0.5),
        "arm_spread": np.full(n, 0.0),
        "motion": np.zeros(n),
        "stillness": np.zeros(n),
        "has_pose": np.zeros(n, dtype=bool),
    }

    for i, p in enumerate(poses):
        if p is None:
            continue
        features["has_pose"][i] = True

        lw = p.get("left_wrist", (0.5, 0.5, 0))
        rw = p.get("right_wrist", (0.5, 0.5, 0))
        ls = p.get("left_shoulder", (0.5, 0.5, 0))
        rs = p.get("right_shoulder", (0.5, 0.5, 0))

        features["wrist_y"][i] = (lw[1] + rw[1]) / 2
        mid_s_y = (ls[1] + rs[1]) / 2
        features["arm_spread"][i] = mid_s_y - features["wrist_y"][i]

    # Motion (frame-to-frame pixel diff)
    if frames is not None and len(frames) == n:
        prev = cv2.cvtColor(frames[0], cv2.COLOR_BGR2GRAY)
        prev = cv2.resize(prev, (160, 120))
        for i in range(1, n):
            gray = cv2.cvtColor(frames[i], cv2.COLOR_BGR2GRAY)
            gray = cv2.resize(gray, (160, 120))
            features["motion"][i] = np.mean(cv2.absdiff(prev, gray))
            prev = gray

    # Smooth all signals
    for key in ["wrist_y", "arm_spread", "motion"]:
        features[key] = _smooth(features[key], n)

    # Stillness = inverse of local motion
    win = max(3, n // 20)
    for i in range(n):
        lo = max(0, i - win)
        hi = min(n, i + win + 1)
        features["stillness"][i] = 1.0 / (np.mean(features["motion"][lo:hi]) + 0.1)

    return features


def segment_swing_stages(
    poses: List[Optional[Dict]],
    num_frames: int,
    frames: List = None,
) -> Dict[str, int]:
    """Find the best representative frame for each swing stage.

    Strategy: find IMPACT first (peak motion — camera-angle-independent),
    then find TOP (hands highest before impact), then work outward.
    This anchors the swing around its two most distinctive moments.
    """
    n = len(poses)
    if n < 8:
        indices = np.linspace(0, n - 1, 8, dtype=int)
        return {stage: int(idx) for stage, idx in zip(SWING_STAGES, indices)}

    valid_poses = sum(1 for p in poses if p is not None)
    if valid_poses < n * 0.3:
        fracs = [0.06, 0.18, 0.32, 0.47, 0.60, 0.72, 0.87, 0.97]
        indices = [max(0, min(int(f * (n - 1)), n - 1)) for f in fracs]
        return {stage: idx for stage, idx in zip(SWING_STAGES, indices)}

    features = _compute_frame_features(poses, frames)

    wrist = features["wrist_y"]
    motion = features["motion"]
    stillness = features["stillness"]

    wrist_min = np.min(wrist)
    wrist_max = np.max(wrist)
    wrist_range = max(wrist_max - wrist_min, 0.01)
    motion_max = np.max(motion)

    # ============================================================
    # Step 1: Find IMPACT = peak motion frame (club hitting ball)
    # ============================================================
    # Exclude first 15% and last 3% to avoid video-start/end artifacts
    search_lo = max(1, n * 15 // 100)
    search_hi = max(search_lo + 1, n - n * 3 // 100)
    impact_idx = search_lo + int(np.argmax(motion[search_lo:search_hi]))

    # ============================================================
    # Step 2: Find TOP = hands at highest point BEFORE impact
    # ============================================================
    # Search for minimum wrist_y (= highest in image) before impact
    # but not in first 10% (may be walking up / pre-shot)
    top_search_lo = max(1, n // 10)
    top_search_hi = impact_idx
    if top_search_hi <= top_search_lo:
        top_search_hi = top_search_lo + 1
    pre_impact_wrist = wrist[top_search_lo:top_search_hi]
    if len(pre_impact_wrist) > 0:
        top_idx = top_search_lo + int(np.argmin(pre_impact_wrist))
    else:
        top_idx = max(0, impact_idx - 3)

    # Refine: if there's a local motion DIP near the wrist minimum
    # (brief pause at top), prefer that frame
    local_window = max(3, (impact_idx - top_idx) // 4)
    refine_lo = max(0, top_idx - local_window)
    refine_hi = min(impact_idx, top_idx + local_window)
    if refine_hi > refine_lo:
        # Among frames near wrist minimum, prefer lower motion (pause)
        combined = wrist[refine_lo:refine_hi] + 0.3 * motion[refine_lo:refine_hi] / max(motion_max, 0.1) * wrist_range
        top_idx = refine_lo + int(np.argmin(combined))

    # ============================================================
    # Step 3: Find ADDRESS = still frame with hands low, before top
    # ============================================================
    # Address should be: low motion, hands near ball (high wrist_y)
    # Search before top
    if top_idx > 2:
        addr_scores = np.zeros(top_idx)
        for i in range(top_idx):
            # High stillness (not moving)
            s = stillness[i] / max(np.max(stillness), 0.1) * 3.0
            # High wrist_y (hands at ball level)
            s += (wrist[i] - wrist_min) / wrist_range * 2.0
            # Prefer not the very first frames (might be mid-walk)
            if i >= 3:
                s += 0.5
            addr_scores[i] = s
        address_idx = int(np.argmax(addr_scores))
    else:
        address_idx = 0

    # ============================================================
    # Step 4: Find FINISH = still again after impact, hands high
    # ============================================================
    if impact_idx < n - 3:
        finish_scores = np.zeros(n - impact_idx)
        for i in range(len(finish_scores)):
            fi = impact_idx + i
            # Stillness (decelerating)
            s = stillness[fi] / max(np.max(stillness), 0.1) * 2.0
            # Hands high (low wrist_y)
            s += (1.0 - (wrist[fi] - wrist_min) / wrist_range) * 1.0
            # Later is better
            s += (i / max(len(finish_scores) - 1, 1)) * 2.0
            # Minimum distance from impact
            if i < 3:
                s -= 2.0
            finish_scores[i] = s
        finish_idx = impact_idx + int(np.argmax(finish_scores))
    else:
        finish_idx = n - 1

    # ============================================================
    # Step 5: Interpolate intermediate stages proportionally
    # ============================================================
    # Between address and top: takeaway at 1/3, backswing at 2/3
    addr_to_top = top_idx - address_idx
    takeaway_idx = address_idx + max(1, addr_to_top // 3)
    backswing_idx = address_idx + max(1, 2 * addr_to_top // 3)

    # Between top and impact: downswing at 1/3
    top_to_impact = impact_idx - top_idx
    downswing_idx = top_idx + max(1, top_to_impact // 3)

    # Between impact and finish: follow_through at 1/4
    impact_to_finish = finish_idx - impact_idx
    follow_idx = impact_idx + max(1, impact_to_finish // 4)

    # ============================================================
    # Step 6: Refine each interpolated stage toward best local frame
    # ============================================================
    def _profile_similarity(frame_idx, stage):
        """Compute similarity between a frame's pose and the reference profile for a stage.
        Returns 0-1 score (1 = perfect match). Returns 0 if no profile or no pose."""
        if stage not in _STAGE_PROFILES or poses[frame_idx] is None:
            return 0.0

        prof = _STAGE_PROFILES[stage]
        p = poses[frame_idx]

        lw = p.get("left_wrist", (0.5, 0.5, 0))
        rw = p.get("right_wrist", (0.5, 0.5, 0))
        ls = p.get("left_shoulder", (0.5, 0.5, 0))
        rs = p.get("right_shoulder", (0.5, 0.5, 0))

        frame_wrist_y = (lw[1] + rw[1]) / 2
        frame_wrist_x = (lw[0] + rw[0]) / 2
        frame_shoulder_y = (ls[1] + rs[1]) / 2
        frame_hands_height = frame_shoulder_y - frame_wrist_y
        frame_hands_lateral = frame_wrist_x - (ls[0] + rs[0]) / 2

        # Compare key pose features to reference profile
        diffs = []
        # Wrist height (most discriminative between stages)
        diffs.append(abs(frame_wrist_y - prof["avg_wrist_y"]) * 3.0)
        # Hands lateral position (left/right relative to shoulders)
        diffs.append(abs(frame_hands_lateral - prof["hands_lateral_offset"]) * 2.0)
        # Hands above/below shoulders
        diffs.append(abs(frame_hands_height - prof["hands_height_above_shoulders"]) * 2.0)

        avg_diff = sum(diffs) / len(diffs)
        # Convert to 0-1 similarity (exponential decay)
        return float(np.exp(-avg_diff * 5.0))

    def _refine_stage(center_idx, stage, search_range=None):
        """Search around center for frame that best matches stage criteria,
        combining motion heuristics with learned profile similarity."""
        if search_range is None:
            search_range = max(3, n // 20)
        lo = max(0, center_idx - search_range)
        hi = min(n, center_idx + search_range + 1)
        best_score = -999
        best_idx = center_idx
        for i in range(lo, hi):
            s = 0.0
            wy_norm = (wrist[i] - wrist_min) / wrist_range
            m_norm = motion[i] / max(motion_max, 0.1)
            st_norm = stillness[i] / max(np.max(stillness), 0.1)

            # Heuristic scoring (original logic)
            if stage == "takeaway":
                s += (1.0 - abs(wy_norm - 0.7)) * 2.0
                s += min(m_norm * 2, 1.0)
            elif stage == "backswing":
                s += (1.0 - wy_norm) * 2.0
                s += min(m_norm * 2, 1.0)
            elif stage == "downswing":
                s += m_norm * 3.0
                s += (1.0 - wy_norm) * 1.0
            elif stage == "follow_through":
                s += m_norm * 2.0
                s += (1.0 - wy_norm) * 1.5

            # Profile similarity bonus (learned from reference)
            profile_sim = _profile_similarity(i, stage)
            s += profile_sim * 3.0  # strong weight on profile match

            # Proximity to original estimate
            dist = abs(i - center_idx) / max(search_range, 1)
            s -= dist * 0.5

            if s > best_score:
                best_score = s
                best_idx = i
        return best_idx

    search_r = max(3, addr_to_top // 4)
    takeaway_idx = _refine_stage(takeaway_idx, "takeaway", search_r)
    backswing_idx = _refine_stage(backswing_idx, "backswing", search_r)
    search_r = max(3, top_to_impact // 4)
    downswing_idx = _refine_stage(downswing_idx, "downswing", search_r)
    search_r = max(3, impact_to_finish // 4)
    follow_idx = _refine_stage(follow_idx, "follow_through", search_r)

    # ============================================================
    # Assemble and enforce monotonic ordering
    # ============================================================
    indices = [address_idx, takeaway_idx, backswing_idx, top_idx,
               downswing_idx, impact_idx, follow_idx, finish_idx]

    for i in range(1, len(indices)):
        if indices[i] <= indices[i - 1]:
            indices[i] = min(indices[i - 1] + 1, n - 1)

    indices = [max(0, min(idx, n - 1)) for idx in indices]
    result = {stage: int(idx) for stage, idx in zip(SWING_STAGES, indices)}

    logger.info(f"Stage detection: {result}")
    logger.info(f"  Impact at frame {impact_idx} (motion={motion[impact_idx]:.1f}), "
                f"Top at frame {top_idx} (wrist_y={wrist[top_idx]:.3f})")
    return result
