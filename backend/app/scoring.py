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
        "good": "Your spine tilt looks solid — you're bending from the hips, not the waist",
        "bad_low": "You're standing too tall — push your hips back and tilt your chest toward the ball until you feel pressure in your hamstrings",
        "bad_high": "You're hunching over too much — straighten up a bit, push your butt out, and feel your weight on the balls of your feet, not your toes",
        "why": "Your spine angle controls the entire swing plane — if it changes during the swing, you'll hit fat or thin shots",
        "tip": "Stand upright, then hinge forward from your hip crease (not your waist) until your arms hang naturally. That's your spine angle — lock it in",
    },
    "left_arm_angle": {
        "good": "Your lead arm is nicely extended — that's giving you a wide, powerful arc",
        "bad_low": "Your lead arm is collapsing — imagine pushing a wall away with your left hand as you take the club back. Keep that arm long",
        "bad_high": "Your lead arm is locked stiff — allow a tiny natural softness at the elbow so you're not fighting tension",
        "why": "A straight lead arm creates the widest possible swing arc, which means more clubhead speed and more distance",
        "tip": "During takeaway, feel like your left hand is reaching as far from your body as possible — stretch that arm out without locking the elbow",
    },
    "right_arm_angle": {
        "good": "Your trail elbow is tucked nicely — great connection to your body",
        "bad_low": "Your right elbow is pinching in too tight — let it fold naturally like you're carrying a pizza box under your arm",
        "bad_high": "Your right elbow is flying away from your body — practice swinging with a headcover or towel tucked under your right armpit",
        "why": "When your trail elbow stays connected, you deliver the club on plane. A flying elbow leads to over-the-top slices",
        "tip": "At the top of your backswing, your right elbow should point at the ground, not behind you. Feel like it's tucked against your ribs",
    },
    "hip_shoulder_separation": {
        "good": "Great coil — your shoulders are turning well against your hips, storing power",
        "bad_low": "You're not rotating enough — your hips and shoulders are turning together. Try to keep your belt buckle quieter while your chest turns more",
        "bad_high": "You're over-rotating — your hips are sliding instead of turning. Plant your right foot and feel your right hip stay over your right ankle",
        "why": "The twist between your hips and shoulders is your power source — it's like winding a rubber band. More separation = more stored energy",
        "tip": "Put your hands on your hips, turn your shoulders 90° while keeping hips at 45° — feel that stretch in your core? That's the power position",
    },
    "shoulder_tilt": {
        "good": "Your shoulders are properly set — slight tilt toward the trail side, ready to swing on plane",
        "bad_low": "Your shoulders are too level — since your right hand is lower on the grip, let your right shoulder drop naturally about an inch below your left",
        "bad_high": "Your left shoulder is too high — this can cause a reverse pivot. Relax your left shoulder down and let both arms hang evenly",
        "why": "Your shoulder tilt at address pre-sets your swing path. Wrong tilt = wrong swing direction from the start",
        "tip": "When you grip the club, let your trail hand being lower naturally pull that shoulder down. Don't force it — just let gravity do the work",
    },
    "left_knee_angle": {
        "good": "Nice athletic knee flex — you look ready to move",
        "bad_low": "You're squatting too much — straighten up slightly until you feel balanced, like you could jump if you needed to",
        "bad_high": "Your legs are too straight and locked — unlock your knees with a gentle flex, like you're about to sit on a tall bar stool",
        "why": "Your knee flex creates an athletic base — too straight and you can't rotate; too bent and you lose power and balance",
        "tip": "Bounce lightly on your toes before you set up. Where your knees naturally settle is your ideal flex — memorize that feeling",
    },
    "right_knee_angle": {
        "good": "Your trail knee has good flex — solid foundation for your backswing",
        "bad_low": "Your right knee is bending too much — you're dipping. Keep your right knee stable and feel your weight on the inside of your right foot",
        "bad_high": "Your right leg is straightening out — this means you're swaying. Keep a little flex in that right knee throughout the backswing, like a spring loaded up",
        "why": "Your trail knee is an anchor — if it straightens or sways, you lose your base and your downswing path gets off",
        "tip": "Feel pressure on the inside of your right foot during the backswing. If pressure moves to the outside, your knee is collapsing",
    },
    "head_sway": {
        "good": "Your head is staying very still — that's the mark of a consistent ball striker",
        "bad_low": None,
        "bad_high": "Your head is moving too much — pick a dimple on the back of the ball and stare at it. Your head should feel like it's nailed in place",
        "why": "Your head is the center of your swing — if it moves, everything else shifts and you'll struggle to make solid contact",
        "tip": "Have a friend hold a club grip against the top of your head while you swing slowly. If your head pushes into it, you're swaying",
    },
    "stance_width": {
        "good": "Good stance width — you've got a stable base without restricting your turn",
        "bad_low": "Your feet are too close together — widen them to about shoulder width for driver, slightly narrower for irons. You need stability",
        "bad_high": "Your stance is too wide — you're locking up your hips. Bring your feet in a couple inches until you can freely rotate your hips",
        "why": "Stance width is a balance between stability and mobility — too narrow you fall over, too wide you can't turn",
        "tip": "For driver: insides of your feet should be shoulder-width apart. For a 7-iron: about two inches narrower. Adjust from there based on comfort",
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
