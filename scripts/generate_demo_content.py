"""Generate synthetic demo videos and reference frames for the golf swing analyzer.

Creates detailed stick-figure animations with dramatically different poses per stage.
Each stage is visually unmistakable from the others.
"""
import cv2
import numpy as np
from pathlib import Path
import math

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
SAMPLE_DIR = PROJECT_ROOT / "sample_videos"
REFERENCE_DIR = PROJECT_ROOT / "backend" / "reference_data" / "stages"

WIDTH, HEIGHT = 640, 480
FPS = 30
DURATION_GOOD = 3.0
DURATION_BAD = 3.5

STAGES = ["address", "takeaway", "backswing", "top", "downswing", "impact", "follow_through", "finish"]

STAGE_FRACTIONS = {
    "address": 0.0,
    "takeaway": 0.12,
    "backswing": 0.25,
    "top": 0.40,
    "downswing": 0.55,
    "impact": 0.65,
    "follow_through": 0.80,
    "finish": 0.95,
}

# Stage-specific accent colors for easy visual identification
STAGE_COLORS = {
    "address":        (80, 200, 80),    # Green
    "takeaway":       (80, 180, 220),   # Cyan
    "backswing":      (220, 180, 80),   # Gold
    "top":            (220, 80, 80),    # Red
    "downswing":      (180, 80, 220),   # Purple
    "impact":         (80, 80, 255),    # Blue
    "follow_through": (80, 220, 180),   # Teal
    "finish":         (200, 200, 200),  # Silver
}

GROUND_Y = 390
BODY_BASE_X = 300
BODY_BASE_Y = GROUND_Y - 120  # hip

# Per-stage sky tints (BGR) to make each stage visually distinct background
STAGE_SKY_TINTS = {
    "address":        (220, 200, 140),   # Bright warm blue
    "takeaway":       (140, 200, 160),   # Green-teal
    "backswing":      (160, 170, 220),   # Warm orange/peach
    "top":            (200, 140, 160),    # Distinct purple-pink
    "downswing":      (140, 160, 200),   # Warm amber
    "impact":         (120, 140, 220),    # Deep orange
    "follow_through": (200, 220, 140),   # Bright teal
    "finish":         (220, 210, 210),    # Neutral silver
}

STAGE_GRASS_TINTS = {
    "address":        (40, 130, 40),
    "takeaway":       (40, 140, 50),
    "backswing":      (35, 120, 50),
    "top":            (30, 100, 45),
    "downswing":      (35, 110, 55),
    "impact":         (30, 120, 30),
    "follow_through": (45, 150, 55),
    "finish":         (50, 140, 60),
}


def lerp(a, b, t):
    return a + (b - a) * min(max(t, 0), 1)


def draw_background(frame, t, stage=None):
    """Draw sky, grass with stage-specific tints."""
    if stage is None:
        stage = get_stage_at(t)

    sky_base = STAGE_SKY_TINTS.get(stage, (200, 200, 200))
    grass = STAGE_GRASS_TINTS.get(stage, (40, 130, 40))

    # Sky gradient with stage-specific tint
    for row in range(GROUND_Y - 30):
        frac = row / (GROUND_Y - 30)
        b = int(lerp(sky_base[0], sky_base[0] * 0.7, frac))
        g = int(lerp(sky_base[1], sky_base[1] * 0.7, frac))
        r = int(lerp(sky_base[2], sky_base[2] * 0.7, frac))
        frame[row, :] = (min(b, 255), min(g, 255), min(r, 255))
    # Grass
    frame[GROUND_Y - 30:] = grass
    # Horizon line
    cv2.line(frame, (0, GROUND_Y - 30), (WIDTH, GROUND_Y - 30),
             (grass[0] + 20, grass[1] + 20, grass[2] + 20), 2)
    # Ball position marker
    cv2.circle(frame, (BODY_BASE_X + 20, GROUND_Y - 5), 7, (255, 255, 255), -1)
    cv2.circle(frame, (BODY_BASE_X + 20, GROUND_Y - 5), 7, (200, 200, 200), 1)
    # Tee
    cv2.line(frame, (BODY_BASE_X + 20, GROUND_Y - 5), (BODY_BASE_X + 20, GROUND_Y + 5), (139, 90, 43), 2)


def get_stage_at(t):
    """Get current stage name for time fraction t."""
    current = "address"
    for stage, frac in STAGE_FRACTIONS.items():
        if t >= frac:
            current = stage
    return current


def compute_good_pose(t):
    """Return detailed body points for a good golfer at time t (0-1)."""
    hx, hy = BODY_BASE_X, BODY_BASE_Y

    # == TORSO rotation & tilt ==
    if t < 0.12:
        torso_rot = 0
        shoulder_rot = 0
    elif t < 0.40:
        p = (t - 0.12) / 0.28
        torso_rot = lerp(0, -20, p)
        shoulder_rot = lerp(0, -55, p)
    elif t < 0.55:
        p = (t - 0.40) / 0.15
        torso_rot = lerp(-20, 10, p)
        shoulder_rot = lerp(-55, -10, p)
    elif t < 0.65:
        p = (t - 0.55) / 0.10
        torso_rot = lerp(10, 25, p)
        shoulder_rot = lerp(-10, 15, p)
    else:
        p = (t - 0.65) / 0.35
        torso_rot = lerp(25, 50, p)
        shoulder_rot = lerp(15, 55, p)

    # == HEAD ==
    head_x = hx + int(3 * math.sin(math.radians(shoulder_rot * 0.2)))
    head_y = hy - 120
    head = (head_x, head_y)

    # == SPINE/SHOULDERS ==
    spine_top = (hx + int(8 * math.sin(math.radians(torso_rot * 0.3))), hy - 90)

    s_half = 35
    sx_off = int(s_half * math.cos(math.radians(shoulder_rot * 0.6)))
    sy_off = int(8 * math.sin(math.radians(shoulder_rot * 0.5)))
    left_shoulder = (spine_top[0] - sx_off, spine_top[1] - sy_off)
    right_shoulder = (spine_top[0] + sx_off, spine_top[1] + sy_off)

    # == HIPS (more stable) ==
    h_half = 25
    hx_off = int(h_half * math.cos(math.radians(torso_rot * 0.4)))
    left_hip = (hx - hx_off, hy)
    right_hip = (hx + hx_off, hy)

    # == LEGS (mostly stable, slight knee bend) ==
    knee_bend = 15
    left_knee = (hx - 30, hy + 55)
    right_knee = (hx + 30, hy + 55)
    left_ankle = (hx - 40, GROUND_Y)
    right_ankle = (hx + 40, GROUND_Y)

    # == ARMS & CLUB - the most dramatic per-stage changes ==
    if t < 0.05:
        # ADDRESS: arms hang down, club in front/down toward ball
        arm_angle = math.radians(-15)
        l_elbow = (left_shoulder[0] - 10, left_shoulder[1] + 40)
        r_elbow = (right_shoulder[0] + 10, right_shoulder[1] + 40)
        l_wrist = (l_elbow[0] + 5, l_elbow[1] + 35)
        r_wrist = (r_elbow[0] - 5, r_elbow[1] + 35)
        club_end = (BODY_BASE_X + 20, GROUND_Y - 10)
    elif t < 0.12:
        # TAKEAWAY: club starts moving back, wrists rising
        p = (t - 0.05) / 0.07
        l_elbow = (left_shoulder[0] - int(lerp(10, 25, p)), left_shoulder[1] + int(lerp(40, 30, p)))
        r_elbow = (right_shoulder[0] + int(lerp(10, 5, p)), right_shoulder[1] + int(lerp(40, 35, p)))
        l_wrist = (l_elbow[0] - int(lerp(0, 30, p)), l_elbow[1] + int(lerp(35, 15, p)))
        r_wrist = (r_elbow[0] - int(lerp(0, 20, p)), r_elbow[1] + int(lerp(35, 20, p)))
        club_end = (l_wrist[0] - int(lerp(0, 50, p)), l_wrist[1] + int(lerp(0, -20, p)))
    elif t < 0.25:
        # BACKSWING: arms and club going up and back
        p = (t - 0.12) / 0.13
        l_elbow = (left_shoulder[0] - int(lerp(25, 15, p)), left_shoulder[1] + int(lerp(30, -10, p)))
        r_elbow = (right_shoulder[0] + int(lerp(5, 15, p)), right_shoulder[1] + int(lerp(35, 10, p)))
        l_wrist = (l_elbow[0] - int(lerp(30, 20, p)), l_elbow[1] - int(lerp(-15, 40, p)))
        r_wrist = (r_elbow[0] + int(lerp(-20, 5, p)), r_elbow[1] - int(lerp(-20, 30, p)))
        club_end = (l_wrist[0] - int(lerp(50, 30, p)), l_wrist[1] - int(lerp(20, 50, p)))
    elif t < 0.40:
        # TOP: club way up, parallel to ground above head
        p = (t - 0.25) / 0.15
        l_elbow = (left_shoulder[0] - int(lerp(15, 5, p)), left_shoulder[1] - int(lerp(10, 40, p)))
        r_elbow = (right_shoulder[0] + int(lerp(15, 20, p)), right_shoulder[1] - int(lerp(-10, 15, p)))
        l_wrist = (l_elbow[0] + int(lerp(-20, 15, p)), l_elbow[1] - int(lerp(40, 30, p)))
        r_wrist = (r_elbow[0] + int(lerp(5, 15, p)), r_elbow[1] - int(lerp(30, 15, p)))
        club_end = (l_wrist[0] + int(lerp(-30, 60, p)), l_wrist[1] + int(lerp(-50, 10, p)))
    elif t < 0.55:
        # DOWNSWING: arms come down fast
        p = (t - 0.40) / 0.15
        l_elbow = (left_shoulder[0] - int(lerp(5, 15, p)), left_shoulder[1] - int(lerp(40, -10, p)))
        r_elbow = (right_shoulder[0] + int(lerp(20, 10, p)), right_shoulder[1] - int(lerp(-15, -5, p)))
        l_wrist = (l_elbow[0] + int(lerp(15, 10, p)), l_elbow[1] + int(lerp(-30, 40, p)))
        r_wrist = (r_elbow[0] - int(lerp(-15, 5, p)), r_elbow[1] + int(lerp(-15, 35, p)))
        club_end = (l_wrist[0] + int(lerp(60, 15, p)), l_wrist[1] + int(lerp(10, 40, p)))
    elif t < 0.65:
        # IMPACT: arms extended, club hitting ball
        p = (t - 0.55) / 0.10
        l_elbow = (left_shoulder[0] - int(lerp(15, 5, p)), left_shoulder[1] + int(lerp(10, 30, p)))
        r_elbow = (right_shoulder[0] + int(lerp(10, 5, p)), right_shoulder[1] + int(lerp(5, 25, p)))
        l_wrist = (l_elbow[0] + int(lerp(10, 15, p)), l_elbow[1] + int(lerp(40, 30, p)))
        r_wrist = (r_elbow[0] - int(lerp(5, 0, p)), r_elbow[1] + int(lerp(35, 30, p)))
        club_end = (BODY_BASE_X + 20, GROUND_Y - 10)
    elif t < 0.80:
        # FOLLOW-THROUGH: club swings up and left
        p = (t - 0.65) / 0.15
        l_elbow = (left_shoulder[0] + int(lerp(-5, 15, p)), left_shoulder[1] + int(lerp(30, -15, p)))
        r_elbow = (right_shoulder[0] - int(lerp(-5, 10, p)), right_shoulder[1] + int(lerp(25, -5, p)))
        l_wrist = (l_elbow[0] + int(lerp(15, 30, p)), l_elbow[1] - int(lerp(-30, 40, p)))
        r_wrist = (r_elbow[0] + int(lerp(0, 20, p)), r_elbow[1] - int(lerp(-30, 30, p)))
        club_end = (l_wrist[0] + int(lerp(15, -40, p)), l_wrist[1] - int(lerp(-10, 50, p)))
    else:
        # FINISH: arms wrapped around, club behind head
        p = (t - 0.80) / 0.20
        l_elbow = (left_shoulder[0] + int(lerp(15, 25, p)), left_shoulder[1] - int(lerp(15, 30, p)))
        r_elbow = (right_shoulder[0] - int(lerp(10, 5, p)), right_shoulder[1] - int(lerp(5, 25, p)))
        l_wrist = (l_elbow[0] + int(lerp(30, 10, p)), l_elbow[1] - int(lerp(40, 20, p)))
        r_wrist = (r_elbow[0] + int(lerp(20, 5, p)), r_elbow[1] - int(lerp(30, 15, p)))
        club_end = (l_wrist[0] - int(lerp(40, 50, p)), l_wrist[1] + int(lerp(50, 20, p)))

    # Weight shift in legs
    if t > 0.55:
        p = min((t - 0.55) / 0.3, 1.0)
        right_knee = (right_knee[0] - int(10 * p), right_knee[1])
        right_ankle = (right_ankle[0] - int(5 * p), right_ankle[1])

    return {
        "head": head,
        "left_shoulder": left_shoulder, "right_shoulder": right_shoulder,
        "spine_top": spine_top,
        "left_hip": left_hip, "right_hip": right_hip,
        "left_elbow": l_elbow, "right_elbow": r_elbow,
        "left_wrist": l_wrist, "right_wrist": r_wrist,
        "left_knee": left_knee, "right_knee": right_knee,
        "left_ankle": left_ankle, "right_ankle": right_ankle,
        "club_end": club_end,
    }


def compute_bad_pose(t):
    """Bad swing: introduces common faults."""
    pose = compute_good_pose(t)

    # Excessive head sway
    sway = int(25 * math.sin(t * math.pi * 2))
    pose["head"] = (pose["head"][0] + sway, pose["head"][1])

    # Standing too upright (reduce spine tilt)
    for k in ["spine_top", "left_shoulder", "right_shoulder"]:
        pose[k] = (pose[k][0], pose[k][1] - 12)

    # Chicken wing after impact
    if t > 0.65:
        pose["left_wrist"] = (pose["left_wrist"][0] - 20, pose["left_wrist"][1] + 15)
        pose["left_elbow"] = (pose["left_elbow"][0] - 10, pose["left_elbow"][1] + 10)

    # Hip sway
    for k in ["left_hip", "right_hip"]:
        pose[k] = (pose[k][0] + sway // 2, pose[k][1])

    return pose


def draw_golfer(frame, pose, body_color=(255, 255, 255), thickness=3):
    """Draw a detailed stick figure golfer."""
    # Head
    cv2.circle(frame, pose["head"], 14, body_color, -1, cv2.LINE_AA)
    cv2.circle(frame, pose["head"], 14, (0, 0, 0), 1, cv2.LINE_AA)

    # Neck
    neck = ((pose["head"][0] + pose["spine_top"][0]) // 2,
            (pose["head"][1] + pose["spine_top"][1]) // 2 + 5)
    cv2.line(frame, pose["head"], neck, body_color, thickness, cv2.LINE_AA)

    # Shoulders
    cv2.line(frame, pose["left_shoulder"], pose["right_shoulder"], body_color, thickness, cv2.LINE_AA)
    cv2.circle(frame, pose["left_shoulder"], 4, (0, 200, 255), -1, cv2.LINE_AA)
    cv2.circle(frame, pose["right_shoulder"], 4, (0, 200, 255), -1, cv2.LINE_AA)

    # Spine
    hip_center = ((pose["left_hip"][0] + pose["right_hip"][0]) // 2,
                  (pose["left_hip"][1] + pose["right_hip"][1]) // 2)
    cv2.line(frame, pose["spine_top"], hip_center, body_color, thickness, cv2.LINE_AA)

    # Hips
    cv2.line(frame, pose["left_hip"], pose["right_hip"], body_color, thickness, cv2.LINE_AA)

    # Left arm
    cv2.line(frame, pose["left_shoulder"], pose["left_elbow"], body_color, thickness, cv2.LINE_AA)
    cv2.line(frame, pose["left_elbow"], pose["left_wrist"], body_color, thickness, cv2.LINE_AA)
    cv2.circle(frame, pose["left_elbow"], 3, (0, 200, 255), -1, cv2.LINE_AA)
    cv2.circle(frame, pose["left_wrist"], 3, (0, 255, 200), -1, cv2.LINE_AA)

    # Right arm
    cv2.line(frame, pose["right_shoulder"], pose["right_elbow"], body_color, thickness, cv2.LINE_AA)
    cv2.line(frame, pose["right_elbow"], pose["right_wrist"], body_color, thickness, cv2.LINE_AA)
    cv2.circle(frame, pose["right_elbow"], 3, (0, 200, 255), -1, cv2.LINE_AA)
    cv2.circle(frame, pose["right_wrist"], 3, (0, 255, 200), -1, cv2.LINE_AA)

    # Club (thinner, silver)
    cv2.line(frame, pose["left_wrist"], pose["club_end"], (180, 180, 180), 2, cv2.LINE_AA)
    # Club head
    cv2.circle(frame, pose["club_end"], 5, (160, 160, 160), -1, cv2.LINE_AA)

    # Legs
    cv2.line(frame, pose["left_hip"], pose["left_knee"], body_color, thickness, cv2.LINE_AA)
    cv2.line(frame, pose["left_knee"], pose["left_ankle"], body_color, thickness, cv2.LINE_AA)
    cv2.line(frame, pose["right_hip"], pose["right_knee"], body_color, thickness, cv2.LINE_AA)
    cv2.line(frame, pose["right_knee"], pose["right_ankle"], body_color, thickness, cv2.LINE_AA)
    cv2.circle(frame, pose["left_knee"], 3, (0, 200, 255), -1, cv2.LINE_AA)
    cv2.circle(frame, pose["right_knee"], 3, (0, 200, 255), -1, cv2.LINE_AA)


def draw_stage_indicator(frame, stage_name, t, accent_color):
    """Draw stage name and a colored bar at top."""
    # Colored bar
    cv2.rectangle(frame, (0, 0), (WIDTH, 40), (30, 30, 30), -1)
    cv2.rectangle(frame, (0, 36), (WIDTH, 40), accent_color, -1)

    display = stage_name.replace("_", " ").upper()
    cv2.putText(frame, display, (15, 28),
                cv2.FONT_HERSHEY_SIMPLEX, 0.75, accent_color, 2, cv2.LINE_AA)

    # Progress bar
    bar_w = int((WIDTH - 200) * t)
    cv2.rectangle(frame, (200, 14), (WIDTH - 15, 26), (60, 60, 60), -1)
    cv2.rectangle(frame, (200, 14), (200 + bar_w, 26), accent_color, -1)


def generate_video(output_path, duration, pose_fn, body_color, label):
    """Generate a synthetic golf swing video."""
    total_frames = int(duration * FPS)
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(str(output_path), fourcc, FPS, (WIDTH, HEIGHT))

    for i in range(total_frames):
        t = i / total_frames
        frame = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)

        stage = get_stage_at(t)
        accent = STAGE_COLORS.get(stage, (200, 200, 200))

        draw_background(frame, t, stage)

        pose = pose_fn(t)
        draw_golfer(frame, pose, body_color)
        draw_stage_indicator(frame, stage, t, accent)

        # Bottom label
        cv2.putText(frame, label, (10, HEIGHT - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 180, 180), 1, cv2.LINE_AA)

        writer.write(frame)

    writer.release()
    print(f"  Generated: {output_path} ({total_frames} frames)")


def generate_reference_frames():
    """Generate one reference frame per stage from the good swing."""
    print("Generating reference frames...")
    for stage, frac in STAGE_FRACTIONS.items():
        stage_dir = REFERENCE_DIR / stage
        stage_dir.mkdir(parents=True, exist_ok=True)

        frame = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
        draw_background(frame, frac, stage)
        pose = compute_good_pose(frac)
        draw_golfer(frame, pose)

        accent = STAGE_COLORS.get(stage, (200, 200, 200))
        draw_stage_indicator(frame, stage, frac, accent)

        # "REFERENCE" watermark
        cv2.putText(frame, "GOOD PRACTICE REFERENCE", (10, HEIGHT - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 200, 100), 1, cv2.LINE_AA)

        out_path = stage_dir / "ref_01.png"
        cv2.imwrite(str(out_path), frame)
        print(f"  Saved: {out_path}")


def main():
    print("=== Generating Golf Swing Demo Content ===\n")
    SAMPLE_DIR.mkdir(parents=True, exist_ok=True)

    print("Generating good swing video...")
    generate_video(SAMPLE_DIR / "good_swing.mp4", DURATION_GOOD,
                   compute_good_pose, (255, 255, 255), "Good Swing Demo")

    print("Generating needs-improvement swing video...")
    generate_video(SAMPLE_DIR / "needs_improvement.mp4", DURATION_BAD,
                   compute_bad_pose, (200, 200, 255), "Needs Improvement Demo")

    generate_reference_frames()
    print("\n✅ Demo content generation complete!")


if __name__ == "__main__":
    main()
