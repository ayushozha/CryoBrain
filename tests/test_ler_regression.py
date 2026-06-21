"""X10: measured LER regression guard."""

from __future__ import annotations

from pathlib import Path

import pytest

from cryobrain.accuracy.measured_ler import measure_candidate_ler
from cryobrain.rtl_grader.flow import eda_tools_available
from cryobrain.types import ScenarioConfig

ROOT = Path(__file__).resolve().parents[1]
TASK = ROOT / "tasks" / "cryo_brain_decoder"
GOLDEN = TASK / "donotaccess" / "cryo_brain_decoder_golden.sv"
WRONG = TASK / "donotaccess" / "cryo_brain_decoder_wrong.sv"

pytestmark = [
    pytest.mark.wsl,
    pytest.mark.skipif(not eda_tools_available(), reason="EDA not on PATH"),
]


def test_measured_ler_regresses_for_wrong_rtl():
    scenario = ScenarioConfig(distance=3, noise_rate=0.02, shots=800, rounds=3)
    golden = measure_candidate_ler(GOLDEN, scenario, seed=1729)
    wrong = measure_candidate_ler(WRONG, scenario, seed=1729)

    assert golden["rtl_valid"] is True
    assert wrong["candidate_ler"] > golden["candidate_ler"]
    assert wrong["benchmark_failures"] > golden["benchmark_failures"]
