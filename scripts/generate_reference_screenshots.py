"""One-time script: extract reference stage frames from a reference video
using the SAME stage segmentation algorithm as the analysis pipeline,
then generate annotated static reference screenshots.

This ensures reference stages are correctly matched because they use
the exact same detection logic as user videos.

Outputs:
  - backend/reference_data/{stage}/ref_01.jpg  (raw frame per stage)
  - backend/static/references/{stage}_reference.jpg  (annotated)

These annotated images are served as static assets and never regenerated per job.
"""
import sys
from pathlib import Path

# Add backend to path
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

import cv2
import numpy as np
from app.config import SWING_STAGES
from app.pose_estimator import PoseEstimator, compute_body_metrics
from app.orientation import normalize_orientation
from app.scoring import score_stage
from app.annotator import annotate_stage_frame

TARGET_WIDTH = 640
OUTPUT_DIR = PROJECT_ROOT / "backend" / "static" / "references"
RAW_REF_DIR = PROJECT_ROOT / "backend" / "reference_data"

# Default reference video — slow motion Tiger Woods swing
DEFAULT_REF_VIDEO = PROJECT_ROOT / "sample_videos" / "Tiger_woods_slow_motion_reference.mp4"

# Manually verified frame indices (out of 90 subsampled frames) for
# Tiger_woods_slow_motion_reference.mp4.  These were visually confirmed
# by a human reviewer and must not be changed by the algorithm.
MANUAL_FRAME_INDICES = {
    "address":        1,
    "takeaway":      32,
    "backswing":     45,
    "top":           59,
    "downswing":     72,
    "impact":        76,
    "follow_through":82,
    "finish":        87,
}


def extract_all_frames(video_path: str, max_frames: int = 90):
    """Extract and subsample frames from a video file."""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Cannot open video: {video_path}")

    frames = []
    fps = cap.get(cv2.CAP_PROP_FPS)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"  Video: {total} frames, {fps:.1f} fps, {total/fps:.1f}s")

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frames.append(frame)
    cap.release()

    if len(frames) > max_frames:
        step = len(frames) / max_frames
        indices = [int(i * step) for i in range(max_frames)]
        frames = [frames[i] for i in indices]
        print(f"  Subsampled to {len(frames)} frames")

    return frames


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Generate reference stage screenshots from a video")
    parser.add_argument("--video", type=str, default=str(DEFAULT_REF_VIDEO),
                        help="Path to reference golf swing video")
    args = parser.parse_args()

    video_path = args.video
    print(f"🎬 Reference video: {video_path}")

    if not Path(video_path).exists():
        print(f"❌ Video not found: {video_path}")
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Step 1: Extract frames
    print("\n📹 Step 1: Extracting frames...")
    frames = extract_all_frames(video_path)

    # Step 2: Normalize orientation
    print("\n🔄 Step 2: Normalizing orientation...")
    frames = [normalize_orientation(f) for f in frames]

    # Step 3: Use manually verified frame indices
    print("\n📊 Step 3: Using manually verified stage frame indices...")
    stage_indices = MANUAL_FRAME_INDICES
    for stage in SWING_STAGES:
        idx = stage_indices[stage]
        print(f"    {stage:20s} → frame {idx:3d} / {len(frames)}")

    # Step 4: Pose detect + annotate each stage
    print("\n🖼️ Step 4: Generating reference images...")
    pose = PoseEstimator()

    for stage in SWING_STAGES:
        idx = stage_indices[stage]
        frame = frames[idx]

        # Save raw frame
        raw_dir = RAW_REF_DIR / stage
        raw_dir.mkdir(parents=True, exist_ok=True)
        raw_path = raw_dir / "ref_01.jpg"
        cv2.imwrite(str(raw_path), frame, [cv2.IMWRITE_JPEG_QUALITY, 95])

        # Resize for annotation
        rh, rw = frame.shape[:2]
        scale = TARGET_WIDTH / rw
        ref_h = int(rh * scale)
        resized = cv2.resize(frame, (TARGET_WIDTH, ref_h), interpolation=cv2.INTER_AREA)

        landmarks = pose.detect(resized)
        if landmarks:
            metrics = compute_body_metrics(landmarks)
            _, metric_scores = score_stage(stage, metrics)
        else:
            metrics, metric_scores = {}, {}

        annotated = annotate_stage_frame(
            resized, landmarks, stage, metric_scores, metrics, is_reference=True
        )

        out_path = OUTPUT_DIR / f"{stage}_reference.jpg"
        cv2.imwrite(str(out_path), annotated, [cv2.IMWRITE_JPEG_QUALITY, 92])
        print(f"  ✅ {stage:20s}: frame {idx}, {annotated.shape[1]}x{annotated.shape[0]}")

    pose.close()

    # Contact sheet
    print("\n📋 Generating contact sheet...")
    thumb_w, thumb_h = 240, 427
    cols, rows = 4, 2
    pad = 40
    canvas = np.ones((rows * (thumb_h + pad), cols * thumb_w, 3), dtype=np.uint8) * 255

    for i, stage in enumerate(SWING_STAGES):
        r, c = divmod(i, cols)
        img = cv2.imread(str(OUTPUT_DIR / f"{stage}_reference.jpg"))
        if img is None:
            continue
        thumb = cv2.resize(img, (thumb_w, thumb_h))
        x, y = c * thumb_w, r * (thumb_h + pad) + pad
        canvas[y:y+thumb_h, x:x+thumb_w] = thumb
        cv2.putText(canvas, f"{i+1}. {stage}", (x + 5, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

    cv2.imwrite(str(OUTPUT_DIR / "contact_sheet.jpg"), canvas, [cv2.IMWRITE_JPEG_QUALITY, 90])

    print(f"\n✅ All reference screenshots saved to {OUTPUT_DIR}")
    print(f"   Verify at: http://localhost:8000/static/references/contact_sheet.jpg")


if __name__ == "__main__":
    main()
