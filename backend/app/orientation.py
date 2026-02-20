"""Orientation normalization – ensure frames are correctly oriented (ground is down)."""
import cv2
import numpy as np
from typing import Dict, Optional, Tuple


def normalize_orientation(
    frame: np.ndarray,
    landmarks: Optional[Dict[str, Tuple[float, float, float]]] = None,
) -> np.ndarray:
    """Normalize frame orientation so the person is standing upright.

    Strategy:
    1. If landmarks available, check if ankles are above shoulders (upside down)
       or if the person is sideways. Rotate accordingly.
    2. Fallback: assume correct orientation (most phone cameras auto-rotate).

    Returns the corrected frame.
    """
    if landmarks is None:
        return frame

    # Get key vertical reference points
    ls = landmarks.get("left_shoulder")
    rs = landmarks.get("right_shoulder")
    la = landmarks.get("left_ankle")
    ra = landmarks.get("right_ankle")

    if not all([ls, rs, la, ra]):
        return frame

    mid_shoulder_y = (ls[1] + rs[1]) / 2
    mid_ankle_y = (la[1] + ra[1]) / 2
    mid_shoulder_x = (ls[0] + rs[0]) / 2
    mid_ankle_x = (la[0] + ra[0]) / 2

    # In a correctly oriented image, ankles have HIGHER y than shoulders
    # (y increases downward in image coordinates)
    vertical_diff = mid_ankle_y - mid_shoulder_y
    horizontal_diff = abs(mid_ankle_x - mid_shoulder_x)

    # Check if person is sideways (horizontal_diff > vertical_diff significantly)
    if horizontal_diff > abs(vertical_diff) * 1.5:
        # Person is roughly horizontal – rotate 90 degrees
        if mid_ankle_x > mid_shoulder_x:
            # Ankles to the right -> rotate clockwise 90
            frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
        else:
            # Ankles to the left -> rotate counter-clockwise 90
            frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
    elif vertical_diff < -0.1:
        # Ankles above shoulders -> upside down
        frame = cv2.rotate(frame, cv2.ROTATE_180)

    return frame


def resize_to_match(frame1: np.ndarray, frame2: np.ndarray, target_size: Tuple[int, int] = (640, 480)) -> Tuple[np.ndarray, np.ndarray]:
    """Resize both frames to the same target size."""
    f1 = cv2.resize(frame1, target_size, interpolation=cv2.INTER_AREA)
    f2 = cv2.resize(frame2, target_size, interpolation=cv2.INTER_AREA)
    return f1, f2
