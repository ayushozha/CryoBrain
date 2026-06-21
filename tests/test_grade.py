"""Grade-path tests: Stim policy LER spread + golden reference anchor."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from cryobrain.accuracy.stim_harness import evaluate_accuracy
from cryobrain.reward.compute_reward import ler_suppression_vs_mwpm
from cryobrain.types import DesignConfig, ScenarioConfig

ROOT = Path(__file__).resolve().parents[1]
GRADE_PATH = ROOT / "tasks" / "cryo_brain_decoder" / "donotaccess" / "grade.py"


def _load_grade_module():
    spec = importlib.util.spec_from_file_location("cryo_hidden_grade", GRADE_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_grade_module_exposes_golden_reference_factor():
    grade_mod = _load_grade_module()
    assert grade_mod._GOLDEN_LER_FACTOR == 0.50


def test_evaluate_accuracy_spreads_ler_suppression_across_designs():
    """Design knobs must move the continuous accuracy axis (CP6 / F5)."""
    scenario = ScenarioConfig(distance=3, noise_rate=0.02, shots=800, rounds=3)
    designs = (
        DesignConfig(),
        DesignConfig(bitwidth=8, num_layers=4, window_length=16, parallelism=2, pipeline_depth=4),
        DesignConfig(bitwidth=2, num_layers=1, window_length=4, parallelism=1, pipeline_depth=8),
    )
    suppressions = [
        float(evaluate_accuracy(scenario, design, rtl_valid=True)["ler_suppression_vs_mwpm"])
        for design in designs
    ]
    assert max(suppressions) - min(suppressions) >= 0.02


def test_golden_reference_suppression_matches_cp2_anchor():
    scenario = ScenarioConfig(distance=3, noise_rate=0.02, shots=800, rounds=3)
    design = DesignConfig()
    accuracy = evaluate_accuracy(scenario, design, rtl_valid=True)
    mwpm_ler = float(accuracy["mwpm_ler"])
    golden_ler = mwpm_ler * 0.50
    suppression = ler_suppression_vs_mwpm(golden_ler, mwpm_ler)
    assert suppression == 0.50