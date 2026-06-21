"""G3: measured LER determinism and structure."""

from __future__ import annotations

from pathlib import Path

import pytest

from cryobrain.accuracy.measured_ler import measure_candidate_ler
from cryobrain.rtl_grader.flow import eda_tools_available
from cryobrain.types import ScenarioConfig

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "tasks" / "cryo_brain_decoder" / "donotaccess" / "cryo_brain_decoder_golden.sv"

pytestmark = pytest.mark.skipif(not eda_tools_available(), reason="verilator/yosys not on PATH")


def test_measure_returns_required_fields():
    scenario = ScenarioConfig(distance=3, noise_rate=0.02, shots=500, rounds=3)
    result = measure_candidate_ler(GOLDEN, scenario, seed=1729)
    for key in (
        "candidate_ler",
        "mwpm_ler",
        "suppression",
        "shots",
        "vector_source",
        "rtl_path",
        "benchmark_vectors",
        "benchmark_failures",
        "rtl_valid",
    ):
        assert key in result


def test_measure_is_deterministic():
    scenario = ScenarioConfig(distance=3, noise_rate=0.02, shots=500, rounds=3)
    a = measure_candidate_ler(GOLDEN, scenario, seed=1729)
    b = measure_candidate_ler(GOLDEN, scenario, seed=1729)
    assert a["candidate_ler"] == b["candidate_ler"]
    assert a["benchmark_failures"] == b["benchmark_failures"]