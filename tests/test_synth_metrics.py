"""G5: per-variant Yosys synth_metrics."""

from __future__ import annotations

from pathlib import Path

import pytest

from cryobrain.design.config import preset_variants
from cryobrain.rtl_gen.generator import generate_rtl
from cryobrain.rtl_grader.flow import eda_tools_available
from cryobrain.rtl_grader.synth_metrics import synth_metrics

pytestmark = pytest.mark.skipif(not eda_tools_available(), reason="yosys not on PATH")


def test_synth_metrics_returns_fields(tmp_path):
    rtl = generate_rtl(preset_variants()[0], tmp_path / "v0")
    result = synth_metrics(rtl)
    for key in ("area_um2", "latency_cycles", "power_mw_est", "valid", "yosys_log_path", "cell_count"):
        assert key in result
    assert result["valid"] is True
    assert result["cell_count"] > 0
    assert Path(result["yosys_log_path"]).is_file()


def test_three_presets_distinct_rtl_and_valid_synth(tmp_path):
    bodies = []
    for i, design in enumerate(preset_variants()):
        rtl = generate_rtl(design, tmp_path / f"v{i}")
        metrics = synth_metrics(rtl)
        assert metrics["valid"]
        bodies.append(rtl.read_text(encoding="utf-8"))
    assert len(set(bodies)) == 3