"""G7: L4 synthesis sign-off."""

from __future__ import annotations

import pytest

from cryobrain.design.config import preset_variants
from cryobrain.rtl_gen.generator import generate_rtl
from cryobrain.rtl_grader.flow import eda_tools_available
from cryobrain.verify.l4_synth import run_l4

pytestmark = pytest.mark.skipif(not eda_tools_available(), reason="yosys not on PATH")


def test_generated_rtl_passes_l4(tmp_path):
    rtl = generate_rtl(preset_variants()[0], tmp_path)
    result = run_l4(rtl)
    assert result["passed"] is True
    assert result["cell_count"] > 0