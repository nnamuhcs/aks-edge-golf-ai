"""Tests for scoring engine."""
import pytest
from app.scoring import score_metric, score_stage, compute_overall_score, generate_stage_feedback
from app.config import SWING_STAGES


class TestScoring:
    def test_score_metric_at_ideal(self):
        score = score_metric(30, (15, 30, 45))
        assert score == 100.0

    def test_score_metric_at_min(self):
        score = score_metric(15, (15, 30, 45))
        # Gaussian: at boundary, score ≈ 61 (1 sigma away)
        assert 55 <= score <= 65

    def test_score_metric_at_max(self):
        score = score_metric(45, (15, 30, 45))
        assert 55 <= score <= 65

    def test_score_metric_outside_range(self):
        score = score_metric(60, (15, 30, 45))
        # Gaussian: beyond range, still > 0 but low
        assert 0 <= score <= 25

    def test_score_metric_mid_range(self):
        score = score_metric(22.5, (15, 30, 45))
        # Gaussian: halfway between ideal and min → high score
        assert 80 <= score <= 95

    def test_score_stage_returns_score_and_metrics(self):
        metrics = {
            "spine_angle": 30,
            "left_knee_angle": 170,
            "right_knee_angle": 170,
            "stance_width": 0.25,
            "head_sway": 0.02,
            "shoulder_tilt": 0,
        }
        score, metric_scores = score_stage("address", metrics)
        assert 0 <= score <= 100
        assert len(metric_scores) > 0

    def test_overall_score_perfect(self):
        stage_scores = {s: 100.0 for s in SWING_STAGES}
        overall = compute_overall_score(stage_scores)
        assert overall == 100.0

    def test_overall_score_zero(self):
        stage_scores = {s: 0.0 for s in SWING_STAGES}
        overall = compute_overall_score(stage_scores)
        assert overall == 0.0

    def test_overall_score_weighted(self):
        stage_scores = {s: 50.0 for s in SWING_STAGES}
        overall = compute_overall_score(stage_scores)
        assert overall == 50.0

    def test_generate_feedback_structure(self):
        metrics = {"spine_angle": 30, "head_sway": 0.02}
        feedback = generate_stage_feedback("address", 85.0, {"spine_angle": 90, "head_sway": 95}, metrics)
        assert "stage" in feedback
        assert "display_name" in feedback
        assert "score" in feedback
        assert "good_points" in feedback
        assert "issues" in feedback
        assert "why_it_matters" in feedback
        assert "improvement_tips" in feedback
