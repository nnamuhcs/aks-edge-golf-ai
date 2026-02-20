"""Stage segmentation: automatically split swing into stages using pose landmarks."""
import numpy as np
from typing import List, Dict, Optional, Tuple
from .config import SWING_STAGES


def compute_motion_signal(poses: List[Optional[Dict]], frames: List = None) -> np.ndarray:
    """Compute a motion magnitude signal from sequential pose landmarks or frames.

    Uses wrist and hip positions as primary motion indicators.
    Falls back to frame differencing if no poses available.
    Returns array of shape (N,) where N = len(poses).
    """
    n = len(poses)
    motion = np.zeros(n)

    # Check if we have any valid poses
    valid_poses = sum(1 for p in poses if p is not None)

    if valid_poses >= n * 0.3:
        # Use pose-based motion
        key_joints = ["left_wrist", "right_wrist", "left_hip", "right_hip",
                      "left_shoulder", "right_shoulder"]
        for i in range(1, n):
            if poses[i] is None or poses[i - 1] is None:
                motion[i] = motion[i - 1] if i > 0 else 0
                continue
            delta = 0.0
            count = 0
            for joint in key_joints:
                if joint in poses[i] and joint in poses[i - 1]:
                    prev = np.array(poses[i - 1][joint][:2])
                    curr = np.array(poses[i][joint][:2])
                    delta += np.linalg.norm(curr - prev)
                    count += 1
            motion[i] = delta / max(count, 1)
    elif frames is not None and len(frames) == n:
        # Fallback: use frame differencing
        import cv2
        for i in range(1, n):
            gray_prev = cv2.cvtColor(frames[i - 1], cv2.COLOR_BGR2GRAY).astype(float)
            gray_curr = cv2.cvtColor(frames[i], cv2.COLOR_BGR2GRAY).astype(float)
            diff = np.mean(np.abs(gray_curr - gray_prev)) / 255.0
            motion[i] = diff
    else:
        # Last fallback: simulate a swing motion curve
        for i in range(n):
            t = i / max(n - 1, 1)
            # Bell curve peaking at ~60% (impact)
            motion[i] = np.exp(-((t - 0.6) ** 2) / 0.02) * 0.5

    return motion


def compute_wrist_height_signal(poses: List[Optional[Dict]]) -> np.ndarray:
    """Compute average wrist height (y-coord, lower = higher in image)."""
    n = len(poses)
    heights = np.zeros(n)
    for i, p in enumerate(poses):
        if p is None:
            heights[i] = heights[i - 1] if i > 0 else 0.5
            continue
        lw = p.get("left_wrist", (0.5, 0.5, 0))
        rw = p.get("right_wrist", (0.5, 0.5, 0))
        heights[i] = (lw[1] + rw[1]) / 2
    return heights


def segment_swing_stages(
    poses: List[Optional[Dict]],
    num_frames: int,
    frames: List = None,
) -> Dict[str, int]:
    """Segment a golf swing into 8 stages.

    Returns dict mapping stage name -> frame index of representative frame.

    Uses a combination of:
    - Motion signal (velocity of key joints)
    - Wrist height signal (club position proxy)
    - Heuristic proportional splitting as fallback

    The algorithm:
    1. Address: first low-motion segment (golfer is still)
    2. Takeaway: motion begins, wrists start rising
    3. Backswing: continued upward wrist movement
    4. Top: wrist height minimum (highest point, since y is inverted)
    5. Downswing: rapid downward motion
    6. Impact: maximum motion velocity (peak speed)
    7. Follow-through: deceleration after impact
    8. Finish: return to low motion at end
    """
    n = len(poses)
    if n < 8:
        indices = np.linspace(0, n - 1, 8, dtype=int)
        return {stage: int(idx) for stage, idx in zip(SWING_STAGES, indices)}

    # Check if we have meaningful pose data
    valid_poses = sum(1 for p in poses if p is not None)
    has_pose_data = valid_poses >= n * 0.3

    motion = compute_motion_signal(poses, frames)

    # If motion signal has very low variance, fall back to proportional timing
    motion_range = motion.max() - motion.min()
    if not has_pose_data or motion_range < 0.001:
        # Use golf-swing-proportional timing
        # Match the midpoints of each stage's visual territory in demo videos
        # address:0.0-0.12, takeaway:0.12-0.25, backswing:0.25-0.40,
        # top:0.40-0.55, downswing:0.55-0.65, impact:0.65-0.80,
        # follow_through:0.80-0.95, finish:0.95-1.0
        proportional_fracs = [0.06, 0.18, 0.32, 0.47, 0.60, 0.72, 0.87, 0.97]
        indices = [max(0, min(int(f * (n - 1)), n - 1)) for f in proportional_fracs]
        return {stage: idx for stage, idx in zip(SWING_STAGES, indices)}

    wrist_h = compute_wrist_height_signal(poses)

    # Smooth signals
    kernel_size = max(3, n // 20)
    if kernel_size % 2 == 0:
        kernel_size += 1
    kernel = np.ones(kernel_size) / kernel_size

    motion_smooth = np.convolve(motion, kernel, mode='same')
    wrist_smooth = np.convolve(wrist_h, kernel, mode='same')

    # Find key transition points
    # Address: frame near start where motion is still low (first 20% with min motion)
    start_region = max(1, n // 5)
    address_idx = int(np.argmin(motion_smooth[:start_region]))

    # Impact: peak motion (somewhere in middle-to-late)
    search_start = n // 4
    search_end = min(n - n // 8, n - 1)
    impact_region = motion_smooth[search_start:search_end]
    if len(impact_region) > 0:
        impact_idx = search_start + int(np.argmax(impact_region))
    else:
        impact_idx = n * 3 // 4

    # Top: minimum wrist height (highest position) between address and impact
    top_search_start = address_idx + max(1, (impact_idx - address_idx) // 4)
    top_search_end = impact_idx
    if top_search_end > top_search_start:
        wrist_region = wrist_smooth[top_search_start:top_search_end]
        top_idx = top_search_start + int(np.argmin(wrist_region))
    else:
        top_idx = (address_idx + impact_idx) // 2

    # Takeaway: 1/3 between address and top
    takeaway_idx = address_idx + max(1, (top_idx - address_idx) // 3)

    # Backswing: 2/3 between address and top
    backswing_idx = address_idx + max(1, 2 * (top_idx - address_idx) // 3)

    # Downswing: midpoint between top and impact
    downswing_idx = (top_idx + impact_idx) // 2

    # Follow-through: 1/3 after impact toward end
    remaining = n - 1 - impact_idx
    follow_idx = impact_idx + max(1, remaining // 3)

    # Finish: 2/3 after impact toward end, or near the last frame
    finish_idx = min(impact_idx + max(1, 2 * remaining // 3), n - 1)

    # Ensure monotonically increasing and within bounds
    indices = [address_idx, takeaway_idx, backswing_idx, top_idx,
               downswing_idx, impact_idx, follow_idx, finish_idx]

    # Fix any ordering violations
    for i in range(1, len(indices)):
        if indices[i] <= indices[i - 1]:
            indices[i] = min(indices[i - 1] + 1, n - 1)

    # Clamp
    indices = [max(0, min(idx, n - 1)) for idx in indices]

    return {stage: int(idx) for stage, idx in zip(SWING_STAGES, indices)}
