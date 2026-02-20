"""Image annotation: draw skeleton overlays, arrows, and callouts on frames."""
import cv2
import numpy as np
from typing import Dict, List, Tuple, Optional


# Skeleton connections for drawing
SKELETON_CONNECTIONS = [
    ("left_shoulder", "right_shoulder"),
    ("left_shoulder", "left_elbow"),
    ("left_elbow", "left_wrist"),
    ("right_shoulder", "right_elbow"),
    ("right_elbow", "right_wrist"),
    ("left_shoulder", "left_hip"),
    ("right_shoulder", "right_hip"),
    ("left_hip", "right_hip"),
    ("left_hip", "left_knee"),
    ("left_knee", "left_ankle"),
    ("right_hip", "right_knee"),
    ("right_knee", "right_ankle"),
    ("nose", "left_shoulder"),
    ("nose", "right_shoulder"),
]

# Colors (BGR)
SKELETON_COLOR = (0, 255, 128)      # Green
JOINT_COLOR = (0, 200, 255)          # Orange
ARROW_COLOR_GOOD = (0, 200, 0)      # Green
ARROW_COLOR_BAD = (0, 0, 220)       # Red
CALLOUT_BG = (40, 40, 40)           # Dark gray
CALLOUT_TEXT = (255, 255, 255)       # White
REFERENCE_SKELETON_COLOR = (255, 180, 0)  # Blue-ish for reference


def draw_skeleton(
    frame: np.ndarray,
    landmarks: Dict[str, Tuple[float, float, float]],
    color: Tuple[int, int, int] = SKELETON_COLOR,
    thickness: int = 2,
) -> np.ndarray:
    """Draw pose skeleton overlay on frame."""
    h, w = frame.shape[:2]
    annotated = frame.copy()

    # Draw connections
    for joint_a, joint_b in SKELETON_CONNECTIONS:
        if joint_a in landmarks and joint_b in landmarks:
            pt_a = (int(landmarks[joint_a][0] * w), int(landmarks[joint_a][1] * h))
            pt_b = (int(landmarks[joint_b][0] * w), int(landmarks[joint_b][1] * h))
            cv2.line(annotated, pt_a, pt_b, color, thickness, cv2.LINE_AA)

    # Draw joints
    for name, (x, y, z) in landmarks.items():
        pt = (int(x * w), int(y * h))
        cv2.circle(annotated, pt, 5, JOINT_COLOR, -1, cv2.LINE_AA)
        cv2.circle(annotated, pt, 5, (0, 0, 0), 1, cv2.LINE_AA)

    return annotated


def draw_angle_annotation(
    frame: np.ndarray,
    p1: Tuple[int, int],
    vertex: Tuple[int, int],
    p2: Tuple[int, int],
    angle: float,
    label: str,
    color: Tuple[int, int, int] = ARROW_COLOR_GOOD,
) -> np.ndarray:
    """Draw an angle arc and label at a joint."""
    annotated = frame.copy()

    # Draw arc
    cv2.ellipse(annotated, vertex, (25, 25), 0, 0, int(angle), color, 2, cv2.LINE_AA)

    # Label
    label_pos = (vertex[0] + 30, vertex[1] - 10)
    cv2.putText(annotated, f"{label}: {angle:.0f}°", label_pos,
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1, cv2.LINE_AA)

    return annotated


def draw_callout(
    frame: np.ndarray,
    position: Tuple[int, int],
    text: str,
    is_good: bool = True,
) -> np.ndarray:
    """Draw a callout box with arrow pointing to position."""
    annotated = frame.copy()
    h, w = annotated.shape[:2]

    color = ARROW_COLOR_GOOD if is_good else ARROW_COLOR_BAD
    icon = "✓" if is_good else "!"

    # Callout box position (offset from point)
    box_x = min(position[0] + 20, w - 200)
    box_y = max(position[1] - 30, 10)

    # Text sizing
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.4
    (tw, th), _ = cv2.getTextSize(text, font, font_scale, 1)

    # Background rectangle
    padding = 6
    cv2.rectangle(annotated,
                  (box_x - padding, box_y - th - padding),
                  (box_x + tw + padding + 15, box_y + padding),
                  CALLOUT_BG, -1)
    cv2.rectangle(annotated,
                  (box_x - padding, box_y - th - padding),
                  (box_x + tw + padding + 15, box_y + padding),
                  color, 1)

    # Icon
    cv2.putText(annotated, icon, (box_x, box_y), font, font_scale, color, 1, cv2.LINE_AA)
    # Text
    cv2.putText(annotated, text, (box_x + 15, box_y), font, font_scale, CALLOUT_TEXT, 1, cv2.LINE_AA)

    # Arrow from callout to point
    arrow_start = (box_x - padding, box_y - th // 2)
    cv2.arrowedLine(annotated, arrow_start, position, color, 1, cv2.LINE_AA, tipLength=0.15)

    return annotated


# Stage accent colors (BGR) for visual differentiation
STAGE_ACCENT = {
    "address":        (80, 200, 80),
    "takeaway":       (80, 180, 220),
    "backswing":      (80, 180, 220),
    "top":            (80, 80, 220),
    "downswing":      (220, 80, 180),
    "impact":         (255, 80, 80),
    "follow_through": (80, 220, 180),
    "finish":         (200, 200, 200),
}


def annotate_stage_frame(
    frame: np.ndarray,
    landmarks: Optional[Dict[str, Tuple[float, float, float]]],
    stage: str,
    metric_scores: Dict[str, float],
    metrics: Dict[str, float],
    is_reference: bool = False,
) -> np.ndarray:
    """Create a fully annotated frame for a swing stage.

    Draws skeleton + callouts + colored border + stage info overlay.
    """
    h, w = frame.shape[:2]
    annotated = frame.copy()

    accent = STAGE_ACCENT.get(stage, (200, 200, 200))
    skeleton_color = REFERENCE_SKELETON_COLOR if is_reference else SKELETON_COLOR

    # Draw skeleton if available
    if landmarks:
        annotated = draw_skeleton(annotated, landmarks, color=skeleton_color)

        callout_configs = _get_stage_callouts(stage)
        callout_count = 0
        for metric_name, joint_name, label in callout_configs:
            if callout_count >= 3:
                break
            if metric_name in metric_scores and joint_name in landmarks:
                score = metric_scores[metric_name]
                is_good = score >= 70
                pt = (int(landmarks[joint_name][0] * w), int(landmarks[joint_name][1] * h))
                value = metrics.get(metric_name, 0)
                text = f"{label}: {value:.0f}"
                if "angle" in metric_name:
                    text += "°"
                elif "sway" in metric_name or "width" in metric_name:
                    text = f"{label}: {'OK' if is_good else 'Check'}"
                annotated = draw_callout(annotated, pt, text, is_good)
                callout_count += 1
    elif metric_scores:
        # No landmarks but we have metrics – show metric overlay panel
        panel_y = h - 30 * min(len(metric_scores), 4) - 10
        cv2.rectangle(annotated, (10, panel_y - 5), (250, h - 5), (0, 0, 0), -1)
        cv2.rectangle(annotated, (10, panel_y - 5), (250, h - 5), accent, 1)
        row = 0
        for m_name, m_score in list(metric_scores.items())[:4]:
            color = ARROW_COLOR_GOOD if m_score >= 70 else ARROW_COLOR_BAD
            display = m_name.replace("_", " ").title()
            val = metrics.get(m_name, 0)
            text = f"{display}: {val:.0f} ({m_score:.0f}%)"
            cv2.putText(annotated, text, (18, panel_y + 18 + row * 26),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.38, color, 1, cv2.LINE_AA)
            row += 1

    # === Stage label bar at top with accent color ===
    label_prefix = "REFERENCE: " if is_reference else "YOUR SWING: "
    label_text = f"{label_prefix}{stage.replace('_', ' ').upper()}"
    cv2.rectangle(annotated, (0, 0), (w, 36), (20, 20, 20), -1)
    cv2.rectangle(annotated, (0, 32), (w, 36), accent, -1)  # Accent stripe
    cv2.putText(annotated, label_text, (10, 24),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, accent, 2, cv2.LINE_AA)

    # === Score badge in top-right ===
    if metric_scores:
        avg_score = sum(metric_scores.values()) / len(metric_scores)
        badge_color = ARROW_COLOR_GOOD if avg_score >= 70 else (0, 180, 255) if avg_score >= 50 else ARROW_COLOR_BAD
        score_text = f"{avg_score:.0f}"
        cv2.circle(annotated, (w - 35, 18), 16, badge_color, -1, cv2.LINE_AA)
        cv2.putText(annotated, score_text, (w - 48, 24),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2, cv2.LINE_AA)

    # === Colored border (3px) to make stage visually distinct ===
    cv2.rectangle(annotated, (0, 0), (w - 1, h - 1), accent, 3)

    return annotated


def _get_stage_callouts(stage: str) -> List[Tuple[str, str, str]]:
    """Get relevant (metric, joint, label) callouts for each stage."""
    common = [
        ("spine_angle", "left_hip", "Spine"),
        ("head_sway", "nose", "Head"),
    ]
    stage_specific = {
        "address": [
            ("stance_width", "left_ankle", "Stance"),
            ("left_knee_angle", "left_knee", "Knee"),
            ("shoulder_tilt", "left_shoulder", "Shoulders"),
        ],
        "takeaway": [
            ("left_arm_angle", "left_elbow", "Lead Arm"),
            ("hip_shoulder_separation", "left_hip", "X-Factor"),
        ],
        "backswing": [
            ("left_arm_angle", "left_elbow", "Lead Arm"),
            ("hip_shoulder_separation", "left_hip", "X-Factor"),
        ],
        "top": [
            ("left_arm_angle", "left_elbow", "Lead Arm"),
            ("right_arm_angle", "right_elbow", "Trail Arm"),
            ("hip_shoulder_separation", "left_hip", "X-Factor"),
        ],
        "downswing": [
            ("hip_shoulder_separation", "left_hip", "X-Factor"),
            ("left_arm_angle", "left_elbow", "Lead Arm"),
        ],
        "impact": [
            ("left_arm_angle", "left_elbow", "Lead Arm"),
            ("left_knee_angle", "left_knee", "Lead Knee"),
            ("hip_shoulder_separation", "left_hip", "X-Factor"),
        ],
        "follow_through": common,
        "finish": common,
    }
    return stage_specific.get(stage, common)
