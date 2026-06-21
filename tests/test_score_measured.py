"""G10 / MP2: score_measured uses measured LER only."""

from __future__ import annotations

import importlib.util
import shutil
import tempfile
from pathlib import Path

import pytest

from cryobrain.design.config import preset_variants
from cryobrain.grader.score import score_measured
from cryobrain.rtl_gen.generator import generate_rtl
from cryobrain.rtl_grader.flow import eda_tools_available

ROOT = Path(__file__).resolve().parents[1]
TASK = ROOT / "tasks" / "cryo_brain_decoder"
GOLDEN = TASK / "donotaccess" / "cryo_brain_decoder_golden.sv"
WRONG = TASK / "donotaccess" / "cryo_brain_decoder_wrong.sv"
GRADE_PATH = TASK / "donotaccess" / "grade.py"

pytestmark = pytest.mark.skipif(not eda_tools_available(), reason="EDA not on PATH")


def _stage_task_with_rtl(rtl_src: Path) -> Path:
    stage = Path(tempfile.mkdtemp(prefix="cryobrain-score-"))
    shutil.copytree(TASK, stage, dirs_exist_ok=True, symlinks=True)
    shutil.copy2(rtl_src, stage / "rtl" / "cryo_brain_decoder.sv")
    return stage


def _load_grade_module():
    spec = importlib.util.spec_from_file_location("cryo_hidden_grade", GRADE_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_score_measured_required_fields():
    stage = _stage_task_with_rtl(GOLDEN)
    result = score_measured(stage)
    for key in (
        "reward",
        "valid",
        "ler",
        "area_um2",
        "latency_cycles",
        "power_mw",
        "layers_passed",
        "source",
    ):
        assert key in result
    assert result["source"] == "measured"
    assert "L2" in result["layers_passed"]


def test_golden_scores_higher_than_wrong():
    golden = score_measured(_stage_task_with_rtl(GOLDEN))
    wrong = score_measured(_stage_task_with_rtl(WRONG))
    assert golden["reward"] > wrong["reward"]
    assert golden["ler"] < wrong["ler"]
    assert wrong["valid"] is False


def test_reward_moves_with_measured_rtl_quality(tmp_path):
    good = generate_rtl(preset_variants()[0], tmp_path / "good")
    bad = generate_rtl(preset_variants()[2], tmp_path / "bad")
    good_stage = _stage_task_with_rtl(good)
    bad_stage = _stage_task_with_rtl(bad)
    good_score = score_measured(good_stage)
    bad_score = score_measured(bad_stage)
    assert good_score["ler"] < bad_score["ler"]
    assert good_score["reward"] >= bad_score["reward"]


def test_grade_module_uses_measured_path():
    text = GRADE_PATH.read_text(encoding="utf-8")
    assert "score_measured" in text
    assert "evaluate_accuracy" not in text
    assert "simulate_candidate_ler" not in text


def test_hidden_grade_returns_measured_info():
    grade_mod = _load_grade_module()
    result = grade_mod.grade(TASK, rtl_override=GOLDEN)
    assert result["info"]["source"] == "measured"
    assert "layers_passed" in result["info"]