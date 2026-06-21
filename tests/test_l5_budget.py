"""G8: L5 cryo budget envelope."""

from __future__ import annotations

import pytest

from cryobrain.design.config import preset_variants
from cryobrain.rtl_gen.generator import generate_rtl
from cryobrain.rtl_grader.flow import eda_tools_available
from cryobrain.types import CryoBudget
from cryobrain.verify.l5_budget import run_l5

pytestmark = pytest.mark.skipif(not eda_tools_available(), reason="yosys not on PATH")


def test_preset_passes_default_budget(tmp_path):
    rtl = generate_rtl(preset_variants()[0], tmp_path)
    assert run_l5(rtl)["passed"] is True


def test_tight_budget_can_fail(tmp_path):
    rtl = generate_rtl(preset_variants()[1], tmp_path)
    tight = CryoBudget(max_latency_cycles=1, max_area_mm2=1e-9, max_power_mw=0.001)
    assert run_l5(rtl, budget=tight)["passed"] is False