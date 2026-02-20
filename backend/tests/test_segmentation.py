"""Tests for stage segmentation."""
import pytest
import numpy as np
from app.stage_segmentation import segment_swing_stages
from app.config import SWING_STAGES


def _make_mock_poses(n=60):
    """Create mock pose data simulating a golf swing."""
    poses = []
    for i in range(n):
        t = i / n
        wrist_y = 0.5
        if t < 0.1:
            wrist_y = 0.7
        elif t < 0.4:
            wrist_y = 0.7 - 0.5 * ((t - 0.1) / 0.3)
        elif t < 0.45:
            wrist_y = 0.2
        elif t < 0.65:
            wrist_y = 0.2 + 0.5 * ((t - 0.45) / 0.2)
        else:
            wrist_y = 0.7 - 0.3 * ((t - 0.65) / 0.35)

        wrist_x = 0.5 + 0.1 * np.sin(t * np.pi * 2)
        pose = {
            "nose": (0.5, 0.2, 0),
            "left_shoulder": (0.45, 0.35, 0),
            "right_shoulder": (0.55, 0.35, 0),
            "left_elbow": (0.4, 0.45, 0),
            "right_elbow": (0.6, 0.45, 0),
            "left_wrist": (wrist_x - 0.05, wrist_y, 0),
            "right_wrist": (wrist_x + 0.05, wrist_y, 0),
            "left_hip": (0.47, 0.55, 0),
            "right_hip": (0.53, 0.55, 0),
            "left_knee": (0.45, 0.7, 0),
            "right_knee": (0.55, 0.7, 0),
            "left_ankle": (0.43, 0.85, 0),
            "right_ankle": (0.57, 0.85, 0),
        }
        poses.append(pose)
    return poses


def _make_mock_frames(n=60):
    """Create mock video frames with varying motion."""
    frames = []
    for i in range(n):
        t = i / n
        # More motion during impact phase (t=0.5-0.7)
        intensity = 128
        if 0.45 < t < 0.7:
            intensity = int(128 + 127 * ((t - 0.45) / 0.25))
        frame = np.full((120, 160, 3), intensity, dtype=np.uint8)
        # Add some noise for motion detection
        noise = np.random.randint(0, int(10 + 40 * (1 if 0.4 < t < 0.75 else 0)),
                                  frame.shape, dtype=np.uint8)
        frame = np.clip(frame.astype(int) + noise, 0, 255).astype(np.uint8)
        frames.append(frame)
    return frames


class TestStageSegmentation:
    def test_returns_all_stages(self):
        poses = _make_mock_poses(60)
        frames = _make_mock_frames(60)
        result = segment_swing_stages(poses, 60, frames=frames)
        assert set(result.keys()) == set(SWING_STAGES)

    def test_stages_are_monotonic(self):
        poses = _make_mock_poses(60)
        frames = _make_mock_frames(60)
        result = segment_swing_stages(poses, 60, frames=frames)
        indices = [result[s] for s in SWING_STAGES]
        for i in range(1, len(indices)):
            assert indices[i] >= indices[i - 1], f"Stage {SWING_STAGES[i]} index not monotonic"

    def test_indices_in_bounds(self):
        n = 60
        poses = _make_mock_poses(n)
        frames = _make_mock_frames(n)
        result = segment_swing_stages(poses, n, frames=frames)
        for stage, idx in result.items():
            assert 0 <= idx < n, f"{stage} index {idx} out of bounds"

    def test_few_frames_fallback(self):
        poses = [None] * 5
        result = segment_swing_stages(poses, 5)
        assert len(result) == len(SWING_STAGES)

    def test_none_poses_handled(self):
        poses = [None] * 20
        result = segment_swing_stages(poses, 20)
        assert len(result) == len(SWING_STAGES)

    def test_without_frames(self):
        """Segmentation should still work without video frames (no motion signal)."""
        poses = _make_mock_poses(60)
        result = segment_swing_stages(poses, 60, frames=None)
        assert set(result.keys()) == set(SWING_STAGES)
