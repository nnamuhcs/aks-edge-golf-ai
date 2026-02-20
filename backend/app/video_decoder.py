"""Video decoding and frame extraction using OpenCV/ffmpeg."""
import cv2
import numpy as np
from pathlib import Path
from typing import List, Tuple
import logging

logger = logging.getLogger(__name__)


def _is_slow_motion(fps: float, total_frames: int) -> bool:
    """Decide if video needs the two-pass swing-finding treatment.

    Returns False (= needs two-pass) when:
    - Short duration videos where the swing might occupy the whole clip
    - The swing likely takes < 30% of total frames (long setup/walk-up)

    We ALWAYS use two-pass for normal-speed videos to find the swing.
    For actual slow-mo replays (120fps+), evenly sampling works fine since
    the swing spans most of the video.

    Actually: the safest approach is to ALWAYS use two-pass for everything
    EXCEPT very high fps (120+) where the swing already spans many frames.
    """
    # Only skip two-pass for genuine high-framerate slow-mo cameras
    if fps >= 100:
        return True
    # Everything else: use two-pass to find the swing
    return False


def _find_swing_region_coarse(frames: List[np.ndarray]) -> Tuple[int, int]:
    """Coarse pass: find the approximate start/end of the swing using
    frame-to-frame motion magnitude. The swing is the region with the
    most intense motion.

    Returns (start_idx, end_idx) in terms of frame indices.
    """
    n = len(frames)
    if n < 10:
        return 0, n - 1

    # Compute motion magnitude between consecutive frames using grayscale diff
    motion = np.zeros(n)
    prev_gray = cv2.cvtColor(frames[0], cv2.COLOR_BGR2GRAY)
    # Downsample for speed
    small_h, small_w = 120, 160
    prev_gray = cv2.resize(prev_gray, (small_w, small_h))

    for i in range(1, n):
        gray = cv2.cvtColor(frames[i], cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, (small_w, small_h))
        diff = cv2.absdiff(prev_gray, gray)
        motion[i] = np.mean(diff)
        prev_gray = gray

    # Smooth motion signal
    k = max(3, n // 20)
    if k % 2 == 0:
        k += 1
    kernel = np.ones(k) / k
    smooth_motion = np.convolve(motion, kernel, mode='same')

    # Find peak motion region — this is the swing
    peak_idx = int(np.argmax(smooth_motion))
    threshold = np.max(smooth_motion) * 0.25

    # Walk backward from peak to find swing start
    start = peak_idx
    for i in range(peak_idx, -1, -1):
        if smooth_motion[i] < threshold:
            start = i
            break
    else:
        start = 0

    # Walk forward from peak to find swing end
    end = peak_idx
    for i in range(peak_idx, n):
        if smooth_motion[i] < threshold:
            end = i
            break
    else:
        end = n - 1

    # Add asymmetric padding: MORE before (to catch address/backswing)
    # than after (follow-through/finish are fast and already captured).
    # The backswing is slow = low motion, so motion detector misses it.
    swing_len = end - start
    pad_before = max(15, swing_len * 3)   # very generous backward padding
    pad_after = max(15, swing_len * 2)   # generous forward padding for follow-through/finish
    start = max(0, start - pad_before)
    end = min(n - 1, end + pad_after)

    logger.info(f"Swing region detected: frames {start}-{end} of {n} "
                f"(peak motion at {peak_idx})")
    return start, end


def extract_frames(video_path: str | Path, max_frames: int = 120) -> List[np.ndarray]:
    """Extract frames from video.

    For normal-speed videos, uses a two-pass approach:
    1. Coarse pass: read all frames, find the swing region via motion
    2. Fine pass: extract EVERY frame in the swing region

    For slow-motion videos, samples evenly since there are plenty of frames.

    Returns list of BGR numpy arrays.
    """
    video_path = str(video_path)
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Cannot open video: {video_path}")

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    cap.release()

    if total_frames <= 0:
        cap = cv2.VideoCapture(video_path)
        frames = []
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frames.append(frame)
        cap.release()
        if not frames:
            raise ValueError("No frames extracted from video")
        if len(frames) > max_frames:
            indices = np.linspace(0, len(frames) - 1, max_frames, dtype=int)
            frames = [frames[i] for i in indices]
        return frames

    slow_mo = _is_slow_motion(fps, total_frames)

    if slow_mo:
        # Slow-motion: sample evenly
        sample_count = min(total_frames, max_frames)
        indices = np.linspace(0, total_frames - 1, sample_count, dtype=int)
        cap = cv2.VideoCapture(video_path)
        frames = []
        for idx in indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
            ret, frame = cap.read()
            if ret:
                frames.append(frame)
        cap.release()
        logger.info(f"Slow-mo: sampled {len(frames)} of {total_frames} frames")
    else:
        # Normal speed: two-pass approach
        # Pass 1: read all frames (or coarse sample for very long videos)
        cap = cv2.VideoCapture(video_path)
        all_frames = []
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            all_frames.append(frame)
        cap.release()

        if not all_frames:
            raise ValueError("No frames extracted from video")

        # For very long videos, coarse-sample first pass
        coarse_step = 1
        if len(all_frames) > 500:
            coarse_step = max(1, len(all_frames) // 500)
            coarse_frames = all_frames[::coarse_step]
        else:
            coarse_frames = all_frames

        # Find swing region using motion detection
        swing_start, swing_end = _find_swing_region_coarse(coarse_frames)

        # Map back to original frame indices
        orig_start = swing_start * coarse_step
        orig_end = min(swing_end * coarse_step, len(all_frames) - 1)

        # Pass 2: take EVERY frame in the swing region
        swing_frames = all_frames[orig_start:orig_end + 1]
        logger.info(f"Normal-speed: {len(all_frames)} total frames, "
                     f"swing region: {orig_start}-{orig_end} "
                     f"({len(swing_frames)} frames)")

        # Subsample if still too many frames
        if len(swing_frames) > max_frames:
            indices = np.linspace(0, len(swing_frames) - 1, max_frames, dtype=int)
            swing_frames = [swing_frames[i] for i in indices]

        frames = swing_frames

    if not frames:
        raise ValueError("No frames extracted from video")
    return frames


def get_video_info(video_path: str | Path) -> dict:
    """Get basic video metadata."""
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise ValueError(f"Cannot open video: {video_path}")
    info = {
        "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
        "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        "fps": cap.get(cv2.CAP_PROP_FPS),
        "frame_count": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
        "duration_sec": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) / max(cap.get(cv2.CAP_PROP_FPS), 1),
    }
    cap.release()
    return info
