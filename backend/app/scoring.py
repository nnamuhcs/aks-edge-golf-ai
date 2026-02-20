"""Scoring engine: compute per-stage and overall scores from body metrics."""
import numpy as np
from typing import Dict, List, Tuple
from .config import SWING_STAGES, STAGE_WEIGHTS, STAGE_DISPLAY_NAMES


# Ideal ranges for metrics at each stage (min, ideal, max)
# Calibrated from Tiger Woods slow-motion swing (the gold standard).
# Wide tolerance bands accommodate frame-to-frame variation, different
# body types, and camera angles.  Pros should score 85-100; amateurs 25-60.
STAGE_IDEAL_METRICS = {
    "address": {
        "spine_angle": (0, 45, 90),
        "left_knee_angle": (90, 136, 180),
        "right_knee_angle": (80, 135, 180),
        "head_sway": (0.0, 0.30, 0.65),
        "shoulder_tilt": (-45, -5, 40),
    },
    "takeaway": {
        "spine_angle": (0, 42, 85),
        "left_arm_angle": (110, 175, 180),   # straight arm is ideal
        "head_sway": (0.0, 0.30, 0.60),
        "hip_shoulder_separation": (0, 10, 50),
    },
    "backswing": {
        "spine_angle": (0, 42, 85),
        "left_arm_angle": (90, 160, 180),
        "hip_shoulder_separation": (0, 16, 55),
        "shoulder_tilt": (-65, -20, 25),
    },
    "top": {
        "spine_angle": (0, 45, 90),
        "left_arm_angle": (90, 165, 180),     # straight arm is ideal
        "hip_shoulder_separation": (0, 15, 55),
        "right_arm_angle": (20, 85, 150),     # wider range, 90° is fine
    },
    "downswing": {
        "spine_angle": (5, 50, 90),
        "hip_shoulder_separation": (0, 11, 50),
        "left_arm_angle": (80, 165, 180),     # straight arm is ideal
        "head_sway": (0.0, 0.32, 0.65),
    },
    "impact": {
        "spine_angle": (5, 52, 90),
        "left_arm_angle": (80, 150, 180),
        "hip_shoulder_separation": (0, 8, 45),
        "head_sway": (0.0, 0.30, 0.65),
        "left_knee_angle": (85, 134, 180),
    },
    "follow_through": {
        "spine_angle": (0, 40, 85),
        "left_arm_angle": (20, 100, 180),
        "head_sway": (0.0, 0.28, 0.60),
    },
    "finish": {
        "spine_angle": (0, 30, 70),
        "left_arm_angle": (20, 100, 175),
        "head_sway": (0.0, 0.22, 0.55),
    },
}


def score_metric(value: float, ideal_range: Tuple[float, float, float]) -> float:
    """Score a single metric on 0-100 scale using gaussian-like falloff.

    ideal_range = (min_acceptable, ideal, max_acceptable)
    Returns 100 at ideal, ~61 at min/max boundaries, gentle decay beyond.
    """
    min_val, ideal, max_val = ideal_range
    if abs(value - ideal) < 1e-6:
        return 100.0

    # Use FULL range as sigma (generous — 61% at boundary, 13% at 2x range)
    if value <= ideal:
        sigma = (ideal - min_val) if (ideal - min_val) > 1e-6 else 1.0
    else:
        sigma = (max_val - ideal) if (max_val - ideal) > 1e-6 else 1.0

    z = (value - ideal) / sigma
    score = 100.0 * np.exp(-0.5 * z * z)
    return max(0.0, min(100.0, score))


def score_stage(stage: str, metrics: Dict[str, float]) -> Tuple[float, Dict[str, float]]:
    """Score a single stage based on its metrics.

    Returns (stage_score, {metric_name: metric_score}).
    """
    ideal = STAGE_IDEAL_METRICS.get(stage, {})
    if not ideal:
        return 75.0, {}  # Default score for stages without defined ideals

    metric_scores = {}
    for metric_name, ideal_range in ideal.items():
        if metric_name in metrics:
            metric_scores[metric_name] = score_metric(metrics[metric_name], ideal_range)
        else:
            metric_scores[metric_name] = 70.0  # Default if metric not available

    if metric_scores:
        stage_score = float(np.mean(list(metric_scores.values())))
    else:
        stage_score = 70.0

    return stage_score, metric_scores


def compute_overall_score(stage_scores: Dict[str, float]) -> float:
    """Compute weighted overall score from stage scores."""
    total = 0.0
    weight_sum = 0.0
    for stage, weight in STAGE_WEIGHTS.items():
        if stage in stage_scores:
            total += stage_scores[stage] * weight
            weight_sum += weight
    if weight_sum > 0:
        return round(total / weight_sum, 1)
    return 70.0


# ─── Feedback templates ───────────────────────────────────────────

METRIC_FEEDBACK = {
    "spine_angle": {
        "good": "Good spine angle maintained",
        "bad_low": "Spine too upright – bend more from the hips",
        "bad_high": "Excessive forward bend – risk of back strain and inconsistent contact",
        "why": "Proper spine angle sets the swing plane and ensures consistent ball striking",
        "tip": "Practice with a club across your shoulders, tilting from hips until club points at ball",
    },
    "left_arm_angle": {
        "good": "Lead arm nicely extended",
        "bad_low": "Lead arm too bent – losing width and power",
        "bad_high": "Lead arm overly rigid – minor flex is natural",
        "why": "A straight lead arm maximizes swing arc and clubhead speed",
        "tip": "Feel like you're pushing the club away from your body during takeaway",
    },
    "right_arm_angle": {
        "good": "Trail arm properly folded",
        "bad_low": "Trail arm too tight – restricting backswing",
        "bad_high": "Trail arm flying out – losing connection",
        "why": "Proper trail arm fold creates a powerful position at the top",
        "tip": "Imagine holding a tray with your right hand at the top of backswing",
    },
    "hip_shoulder_separation": {
        "good": "Great X-factor (hip-shoulder separation)",
        "bad_low": "Limited rotation – losing potential power",
        "bad_high": "Over-rotation – may lose control and balance",
        "why": "Hip-shoulder separation stores elastic energy for an explosive downswing",
        "tip": "Focus on turning shoulders against a stable lower body",
    },
    "shoulder_tilt": {
        "good": "Shoulders properly level at setup",
        "bad_low": "Right shoulder too high – will promote a steep swing",
        "bad_high": "Left shoulder too high – may cause reverse pivot",
        "why": "Shoulder alignment at address determines initial swing path",
        "tip": "Let your trail arm naturally lower the trail shoulder slightly",
    },
    "left_knee_angle": {
        "good": "Proper knee flex for athletic stance",
        "bad_low": "Knees too bent – restricts rotation",
        "bad_high": "Legs too straight – reduces stability and power",
        "why": "Athletic knee flex provides a stable base and allows hip rotation",
        "tip": "Feel like you're sitting slightly on a bar stool – just a gentle flex",
    },
    "right_knee_angle": {
        "good": "Trail leg properly flexed",
        "bad_low": "Trail knee too bent",
        "bad_high": "Trail leg too straight",
        "why": "Trail knee flex supports weight transfer and pivot",
        "tip": "Maintain slight flex in trail knee throughout backswing – resist straightening",
    },
    "head_sway": {
        "good": "Excellent head stability",
        "bad_low": None,  # Low head sway is always good
        "bad_high": "Excessive head movement – hurts consistency",
        "why": "A steady head keeps the swing center stable for clean contact",
        "tip": "Focus on a spot behind the ball and keep your head centered over it",
    },
    "stance_width": {
        "good": "Good stance width for the club",
        "bad_low": "Stance too narrow – may lose balance",
        "bad_high": "Stance too wide – restricts hip turn",
        "why": "Proper stance width balances stability with rotational freedom",
        "tip": "For driver, feet should be roughly shoulder-width apart",
    },
}


def generate_stage_feedback(
    stage: str,
    stage_score: float,
    metric_scores: Dict[str, float],
    metrics: Dict[str, float],
) -> Dict:
    """Generate natural language feedback for a stage."""
    display_name = STAGE_DISPLAY_NAMES.get(stage, stage.replace("_", " ").title())
    ideal_ranges = STAGE_IDEAL_METRICS.get(stage, {})

    good_points = []
    issues = []
    tips = []
    why_matters = []

    for metric_name, m_score in metric_scores.items():
        fb = METRIC_FEEDBACK.get(metric_name, None)
        if fb is None:
            continue

        value = metrics.get(metric_name, 0)
        ideal_range = ideal_ranges.get(metric_name, (0, 50, 100))

        if m_score >= 70:
            good_points.append(fb["good"])
        elif value < ideal_range[1]:
            if fb["bad_low"] is not None:
                issues.append(fb["bad_low"])
                tips.append(fb["tip"])
                why_matters.append(fb["why"])
            else:
                good_points.append(fb["good"])
        else:
            issues.append(fb["bad_high"])
            tips.append(fb["tip"])
            why_matters.append(fb["why"])

    if not good_points:
        good_points.append(f"Reasonable {display_name.lower()} position overall")
    if not issues:
        issues.append("No major issues detected")
    if not tips:
        tips.append("Continue practicing this stage with focus on consistency")

    why_text = why_matters[0] if why_matters else f"The {display_name.lower()} stage sets the foundation for the phases that follow"

    return {
        "stage": stage,
        "display_name": display_name,
        "score": round(stage_score, 1),
        "good_points": good_points[:3],
        "issues": issues[:3],
        "why_it_matters": why_text,
        "improvement_tips": tips[:3],
    }
