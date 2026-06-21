"""MP1: 3 L2-safe DesignConfigs → 3 distinct RTL, measured-valid."""

from __future__ import annotations

import pytest

from cryobrain.accuracy.measured_ler import measure_candidate_ler
from cryobrain.design.config import preset_variants
from cryobrain.rtl_gen.generator import generate_rtl
from cryobrain.rtl_grader.flow import eda_tools_available
from cryobrain.rtl_grader.synth_metrics import synth_metrics
from cryobrain.types import ScenarioConfig

pytestmark = pytest.mark.skipif(not eda_tools_available(), reason="EDA not on PATH")


def test_mp1_three_distinct_rtl_all_measured_valid(tmp_path):
    scenario = ScenarioConfig(distance=3, noise_rate=0.02, shots=500, rounds=3)
    bodies: list[str] = []
    lers: list[float] = []

    for i, design in enumerate(preset_variants()):
        rtl = generate_rtl(design, tmp_path / f"cfg{i}")
        synth = synth_metrics(rtl)
        measure = measure_candidate_ler(rtl, scenario, seed=1729 + i)
        assert synth["valid"]
        assert measure["rtl_valid"]
        assert measure["benchmark_vectors"] > 0
        bodies.append(rtl.read_text(encoding="utf-8"))
        lers.append(measure["candidate_ler"])

    assert len(set(bodies)) == 3
    assert all(ler < 0.05 for ler in lers)