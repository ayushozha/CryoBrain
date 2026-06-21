"""MP0 keystone: worse RTL → worse measured candidate_ler (SPEC-v5 §2)."""

from __future__ import annotations

from pathlib import Path

import pytest

measured_ler = pytest.importorskip(
    "cryobrain.accuracy.measured_ler",
    reason="Grok G3 measure_candidate_ler API has not landed",
)
rtl_flow = pytest.importorskip(
    "cryobrain.rtl_grader.flow",
    reason="RTL flow helpers have not landed",
)
types_mod = pytest.importorskip("cryobrain.types", reason="ScenarioConfig has not landed")

measure_candidate_ler = measured_ler.measure_candidate_ler
eda_tools_available = rtl_flow.eda_tools_available
ScenarioConfig = types_mod.ScenarioConfig

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "tasks" / "cryo_brain_decoder" / "donotaccess" / "cryo_brain_decoder_golden.sv"
WRONG = ROOT / "tasks" / "cryo_brain_decoder" / "donotaccess" / "cryo_brain_decoder_wrong.sv"
STARTER = ROOT / "tasks" / "cryo_brain_decoder" / "rtl" / "cryo_brain_decoder.sv"

pytestmark = pytest.mark.skipif(not eda_tools_available(), reason="verilator/yosys not on PATH")


def _scenario() -> ScenarioConfig:
    return ScenarioConfig(distance=3, noise_rate=0.02, shots=800, rounds=3)


def test_wrong_rtl_worse_than_golden():
    scenario = _scenario()
    golden = measure_candidate_ler(GOLDEN, scenario, seed=1729)
    wrong = measure_candidate_ler(WRONG, scenario, seed=1729)
    assert wrong["candidate_ler"] > golden["candidate_ler"]
    assert golden["benchmark_vectors"] > 0
    assert wrong["benchmark_failures"] >= golden["benchmark_failures"]


def test_starter_buggy_rtl_worse_than_golden():
    scenario = _scenario()
    golden = measure_candidate_ler(GOLDEN, scenario, seed=1729)
    starter = measure_candidate_ler(STARTER, scenario, seed=1729)
    assert starter["candidate_ler"] >= golden["candidate_ler"]
    assert starter["benchmark_failures"] >= golden["benchmark_failures"]


def test_golden_near_zero_decode_failures():
    scenario = _scenario()
    golden = measure_candidate_ler(GOLDEN, scenario, seed=1729)
    assert golden["candidate_ler"] < 0.15
    assert golden["rtl_valid"] is True
