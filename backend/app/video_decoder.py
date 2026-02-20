"""Video decoding and frame extraction using OpenCV/ffmpeg."""
import cv2
import numpy as np
from pathlib import Path
from typing import List, Tuple


def extract_frames(video_path: str | Path, max_frames: int = 120) -> List[np.ndarray]:
    """Extract frames from video, evenly sampled up to max_frames.

    Returns list of BGR numpy arrays.
    """
    video_path = str(video_path)
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Cannot open video: {video_path}")

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

    if total_frames <= 0:
        # Fallback: read all frames
        frames = []
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frames.append(frame)
        cap.release()
        if not frames:
            raise ValueError("No frames extracted from video")
        total_frames = len(frames)
        if total_frames > max_frames:
            indices = np.linspace(0, total_frames - 1, max_frames, dtype=int)
            frames = [frames[i] for i in indices]
        return frames

    # Sample evenly
    sample_count = min(total_frames, max_frames)
    indices = np.linspace(0, total_frames - 1, sample_count, dtype=int)

    frames = []
    for idx in indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
        ret, frame = cap.read()
        if ret:
            frames.append(frame)

    cap.release()
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
