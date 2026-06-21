"""G4: parametric RTL generator."""

from __future__ import annotations

from pathlib import Path

from cryobrain.design.config import preset_variants
from cryobrain.rtl_gen.generator import generate_rtl, render_rtl
from cryobrain.types import DesignConfig


def test_render_contains_xor_policy():
    sv = render_rtl(DesignConfig())
    assert "^" in sv
    assert "module cryo_brain_decoder" in sv
    assert "PIPELINE_DEPTH" in sv
    assert "NUM_LAYERS" in sv


def test_degraded_single_layer_uses_or():
    from cryobrain.types import DesignConfig

    sv = render_rtl(DesignConfig(num_layers=1, pipeline_depth=8, bitwidth=2))
    assert "|" in sv


def test_generate_rtl_writes_file(tmp_path):
    path = generate_rtl(DesignConfig(), tmp_path)
    assert path.is_file()
    assert path.name == "cryo_brain_decoder.sv"


def test_preset_variants_emit_distinct_sv(tmp_path):
    paths = [generate_rtl(d, tmp_path / f"v{i}") for i, d in enumerate(preset_variants())]
    bodies = [p.read_text(encoding="utf-8") for p in paths]
    assert len(set(bodies)) == 3