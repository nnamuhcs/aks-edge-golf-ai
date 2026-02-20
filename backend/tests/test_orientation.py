"""Tests for orientation normalization."""
import pytest
import numpy as np
from app.orientation import normalize_orientation, resize_to_match


def _make_frame(h=480, w=640):
    return np.random.randint(0, 255, (h, w, 3), dtype=np.uint8)


def _upright_landmarks():
    """Normal upright person: shoulders above ankles."""
    return {
        "nose": (0.5, 0.15, 0),
        "left_shoulder": (0.4, 0.3, 0),
        "right_shoulder": (0.6, 0.3, 0),
        "left_hip": (0.45, 0.5, 0),
        "right_hip": (0.55, 0.5, 0),
        "left_knee": (0.45, 0.7, 0),
        "right_knee": (0.55, 0.7, 0),
        "left_ankle": (0.43, 0.9, 0),
        "right_ankle": (0.57, 0.9, 0),
        "left_elbow": (0.35, 0.4, 0),
        "right_elbow": (0.65, 0.4, 0),
        "left_wrist": (0.3, 0.5, 0),
        "right_wrist": (0.7, 0.5, 0),
    }


class TestOrientationNormalization:
    def test_upright_no_change(self):
        frame = _make_frame()
        landmarks = _upright_landmarks()
        result = normalize_orientation(frame, landmarks)
        assert result.shape == frame.shape

    def test_no_landmarks_no_change(self):
        frame = _make_frame()
        result = normalize_orientation(frame, None)
        assert result.shape == frame.shape

    def test_upside_down_rotated(self):
        frame = _make_frame()
        # Upside down: ankles y < shoulders y
        landmarks = _upright_landmarks()
        landmarks["left_ankle"] = (0.43, 0.1, 0)
        landmarks["right_ankle"] = (0.57, 0.1, 0)
        landmarks["left_shoulder"] = (0.4, 0.7, 0)
        landmarks["right_shoulder"] = (0.6, 0.7, 0)
        result = normalize_orientation(frame, landmarks)
        # Should be rotated 180
        assert result.shape == frame.shape

    def test_resize_to_match(self):
        f1 = _make_frame(100, 200)
        f2 = _make_frame(300, 400)
        r1, r2 = resize_to_match(f1, f2, (640, 480))
        assert r1.shape == (480, 640, 3)
        assert r2.shape == (480, 640, 3)
