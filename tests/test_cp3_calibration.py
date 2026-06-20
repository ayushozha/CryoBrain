"""Unit tests for CP3 rollout stats (no EDA required)."""

from cryobrain.calibration.cp3 import CP3_ROLLOUT_VARIANTS, assess_cp3, summarize_rewards


def test_cp3_has_ten_rollout_variants():
    assert len(CP3_ROLLOUT_VARIANTS) == 10


def test_summarize_rewards_spread():
    stats = summarize_rewards([0.25, 0.30, 0.28, 0.22, 0.27])
    assert 0.20 <= stats["mean"] <= 0.35
    assert stats["spread"] > 0.05
    assert stats["std"] > 0.01


def test_assess_cp3_passes_in_band_with_variance():
    verdict = assess_cp3([0.22, 0.28, 0.31, 0.25, 0.27, 0.24, 0.29, 0.26, 0.23, 0.30])
    assert verdict["ok"] is True
    assert verdict["reasons"] == []


def test_assess_cp3_fails_flat_rewards():
    verdict = assess_cp3([0.35] * 10)
    assert verdict["ok"] is False
    assert "insufficient_variance" in verdict["reasons"]


def test_assess_cp3_fails_out_of_band():
    low = assess_cp3([0.05] * 10)
    assert low["ok"] is False
    assert "mean_below_0.20" in low["reasons"]

    high = assess_cp3([0.75, 0.80, 0.78, 0.72, 0.76, 0.79, 0.74, 0.77, 0.81, 0.73])
    assert high["ok"] is False
    assert "mean_above_0.50" in high["reasons"]