"""Grade-path tests: measured scoring contract."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from cryobrain.accuracy.stim_harness import evaluate_accuracy
from cryobrain.types import DesignConfig, ScenarioConfig

ROOT = Path(__file__).resolve().parents[1]
GRADE_PATH = ROOT / "tasks" / "cryo_brain_decoder" / "donotaccess" / "grade.py"


def _load_grade_module():
    spec = importlib.util.spec_from_file_location("cryo_hidden_grade", GRADE_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_grade_module_wires_score_measured():
    text = GRADE_PATH.read_text(encoding="utf-8")
    assert "score_measured" in text
    assert "decoder_policy" not in text


def test_evaluate_accuracy_fail_closed_without_measured_rtl():
    """Design knobs must not move accuracy without measured RTL evidence."""
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
    assert suppressions == [0.0, 0.0, 0.0]


def test_grade_imports_without_proxy_symbols():
    grade_mod = _load_grade_module()
    assert hasattr(grade_mod, "grade")