"""X10: measured pipeline integration gate."""

from __future__ import annotations

import shutil
import tempfile
import json
import hashlib
from pathlib import Path

import pytest

from cryobrain.accuracy.measured_ler import measure_candidate_ler
from cryobrain.artifacts.schemas.v2 import validate_measured_climb
from cryobrain.design.config import preset_variants
from cryobrain.grader.score import score_measured
from cryobrain.rtl_gen.generator import generate_rtl
from cryobrain.rtl_grader.flow import eda_tools_available
from cryobrain.rtl_grader.synth_metrics import synth_metrics
from cryobrain.types import ScenarioConfig

ROOT = Path(__file__).resolve().parents[2]
TASK = ROOT / "tasks" / "cryo_brain_decoder"
GOLDEN = TASK / "donotaccess" / "cryo_brain_decoder_golden.sv"

pytestmark = [
    pytest.mark.wsl,
    pytest.mark.skipif(not eda_tools_available(), reason="EDA not on PATH"),
]


def _stage_task_with_rtl(rtl_src: Path, *, scenario: ScenarioConfig, design) -> Path:
    stage = Path(tempfile.mkdtemp(prefix="cryobrain-x10-"))
    shutil.copytree(TASK, stage, dirs_exist_ok=True, symlinks=True)
    shutil.copy2(rtl_src, stage / "rtl" / "cryo_brain_decoder.sv")
    (stage / "scenario.json").write_text(json.dumps(scenario.to_dict(), indent=2), encoding="utf-8")
    (stage / "design_config.json").write_text(json.dumps(design.to_dict(), indent=2), encoding="utf-8")
    return stage


def test_design_to_measured_score_pipeline(tmp_path):
    design = preset_variants()[0]
    rtl = generate_rtl(design, tmp_path / "variant")
    scenario = ScenarioConfig(distance=3, noise_rate=0.02, shots=1000, rounds=3)

    measurement = measure_candidate_ler(rtl, scenario, seed=1729)
    synth = synth_metrics(rtl)
    score = score_measured(_stage_task_with_rtl(rtl, scenario=scenario, design=design), shots=1000, seed=1729)

    assert measurement["benchmark_vectors"] > 0
    assert synth["valid"] is True
    assert score["source"] == "measured"
    assert score["ler"] == measurement["candidate_ler"]
    assert score["area_um2"] == synth["area_um2"]

    validate_measured_climb(
        {
            "history": [
                {
                    "step": 0,
                    "candidate_ler": score["ler"],
                    "suppression": score["suppression"],
                    "rtl_hash": hashlib.sha256(rtl.read_bytes()).hexdigest(),
                }
            ]
        }
    )


def test_golden_rtl_scores_through_all_measured_layers():
    design = preset_variants()[0]
    scenario = ScenarioConfig(distance=3, noise_rate=0.02, shots=1000, rounds=3)
    score = score_measured(_stage_task_with_rtl(GOLDEN, scenario=scenario, design=design), shots=1000, seed=1729)

    assert score["valid"] is True
    assert score["source"] == "measured"
    assert {"L1", "L2", "L4", "L5"}.issubset(score["layers_passed"])
