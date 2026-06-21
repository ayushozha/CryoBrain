"""MP1: 3 DesignConfigs → 3 distinct (area_um2, candidate_ler)."""

from __future__ import annotations

import pytest

from cryobrain.accuracy.measured_ler import measure_candidate_ler
from cryobrain.design.config import preset_variants
from cryobrain.rtl_gen.generator import generate_rtl
from cryobrain.rtl_grader.flow import eda_tools_available
from cryobrain.rtl_grader.synth_metrics import synth_metrics
from cryobrain.types import ScenarioConfig

pytestmark = pytest.mark.skipif(not eda_tools_available(), reason="EDA not on PATH")


def test_mp1_three_distinct_area_and_ler(tmp_path):
    scenario = ScenarioConfig(distance=3, noise_rate=0.02, shots=500, rounds=3)
    areas: list[float] = []
    lers: list[float] = []

    for i, design in enumerate(preset_variants()):
        rtl = generate_rtl(design, tmp_path / f"cfg{i}")
        synth = synth_metrics(rtl)
        measure = measure_candidate_ler(rtl, scenario, seed=1729 + i)
        assert synth["valid"]
        assert measure["benchmark_vectors"] > 0
        areas.append(synth["area_um2"])
        lers.append(measure["candidate_ler"])

    assert len(set(areas)) == 3
    assert len(set(round(l, 4) for l in lers)) >= 2
    assert max(lers) > min(lers)