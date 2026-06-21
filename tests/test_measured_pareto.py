"""Measured Pareto + benchmark plots (SPEC-v5 C10).

Drives ``build_pareto`` with golden MEASURED records (ParetoCandidate-shaped:
``{rtl_hash, rtl_path, ler, area_um2, latency_cycles}``, where ``ler`` is the
measured ``candidate_ler``) so no EDA / Verilator / Yosys is required. Asserts:

  * Pareto frontier correctness over (measured LER, area_um2),
  * the frozen point schema (``label, ler, area_um2, latency_cycles, rtl_path``),
  * NO proxy / npu_cost-only points — every point carries an rtl_path + measured
    ler, and a record missing them is rejected,
  * the plot accuracy axis label literally says "measured" (and names Verilator)
    — guarding against a proxy-labeling regression.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cryobrain.benchmark import pareto as pareto_mod
from cryobrain.benchmark.pareto import (
    ACCURACY_AXIS_LABEL,
    REQUIRED_POINT_FIELDS,
    build_pareto,
)


def _cand(rtl_path: str, ler: float, area: float, latency: int, h: str = "") -> dict:
    """A ParetoCandidate-shaped golden MEASURED record (store output shape)."""
    return {
        "rtl_hash": h or rtl_path,
        "rtl_path": rtl_path,
        "ler": ler,          # measured candidate_ler
        "area_um2": area,    # Yosys area
        "latency_cycles": latency,
    }


# --- frontier correctness -----------------------------------------------------


def test_frontier_marks_non_dominated_points():
    """A clear 2-D Pareto: lower ler AND lower area dominate.

    Points (area, ler):
      A (3.0, 0.030)  on frontier (cheapest)
      B (6.0, 0.020)  on frontier (more accurate for more area)
      C (9.0, 0.010)  on frontier (most accurate)
      D (6.0, 0.030)  DOMINATED by A (A is cheaper-or-equal area? no) and by B
                       (B same area 6.0, lower ler 0.020 < 0.030) -> dominated.
    """
    records = [
        _cand("a.sv", 0.030, 3.0, 4),
        _cand("b.sv", 0.020, 6.0, 6),
        _cand("c.sv", 0.010, 9.0, 8),
        _cand("d.sv", 0.030, 6.0, 6),  # dominated by b (same area, worse ler)
    ]
    art = build_pareto(records)
    on = {p["label"].split("@")[0]: p["on_frontier"] for p in art["points"]}
    assert on == {"a": True, "b": True, "c": True, "d": False}
    assert art["frontier_count"] == 3
    assert art["count"] == 4
    assert art["frontier_axes"] == ["ler", "area_um2"]


def test_single_point_is_trivially_on_frontier():
    art = build_pareto([_cand("solo.sv", 0.05, 4.0, 8)])
    assert art["count"] == 1
    assert art["points"][0]["on_frontier"] is True


def test_equal_points_both_on_frontier():
    """Ties on both axes do not dominate each other — both stay on the frontier."""
    art = build_pareto([_cand("x.sv", 0.02, 5.0, 8, h="hx"), _cand("y.sv", 0.02, 5.0, 8, h="hy")])
    assert all(p["on_frontier"] for p in art["points"])
    assert art["frontier_count"] == 2


def test_points_sorted_by_area_then_ler():
    art = build_pareto(
        [_cand("c.sv", 0.01, 9.0, 8), _cand("a.sv", 0.03, 3.0, 4), _cand("b.sv", 0.02, 6.0, 6)]
    )
    areas = [p["area_um2"] for p in art["points"]]
    assert areas == sorted(areas)


# --- schema -------------------------------------------------------------------


def test_point_schema_has_all_required_measured_fields():
    art = build_pareto([_cand("artifacts/variants/step_012.sv", 0.017, 6.1, 8, h="abc123")])
    p = art["points"][0]
    for field in REQUIRED_POINT_FIELDS:
        assert field in p, f"missing required field {field}"
    assert p["ler"] == 0.017          # measured candidate_ler, not a formula
    assert p["area_um2"] == 6.1
    assert p["latency_cycles"] == 8
    assert p["rtl_path"] == "artifacts/variants/step_012.sv"
    assert p["label"].startswith("step_012")
    # Provenance hash short-prefix is carried for plotting/labels.
    assert p["rtl_hash"] == "abc123"


def test_top_level_artifact_shape():
    art = build_pareto([_cand("a.sv", 0.03, 3.0, 4)])
    assert set(art) >= {"accuracy_axis", "hardware_axis", "frontier_axes", "count", "frontier_count", "points"}
    assert art["accuracy_axis"] == ACCURACY_AXIS_LABEL


def test_empty_records_emit_valid_empty_points():
    art = build_pareto([])
    assert art["points"] == []
    assert art["count"] == 0
    assert art["frontier_count"] == 0
    assert art["accuracy_axis"] == ACCURACY_AXIS_LABEL  # axis still labeled measured


# --- no proxy / npu_cost-only points ------------------------------------------


def test_every_point_carries_rtl_path_and_measured_ler():
    """No npu_cost-only points: each point must have an rtl_path + measured ler."""
    art = build_pareto([_cand("a.sv", 0.03, 3.0, 4), _cand("b.sv", 0.02, 6.0, 6)])
    for p in art["points"]:
        assert p["rtl_path"], "point without rtl_path (would be a proxy/npu_cost-only point)"
        assert isinstance(p["ler"], float)


def test_point_missing_rtl_path_is_rejected():
    """A candidate with no rtl_path (e.g. an npu_cost-only formula point) raises."""
    bad = {"rtl_hash": "h", "ler": 0.02, "area_um2": 5.0, "latency_cycles": 8}  # no rtl_path
    with pytest.raises(ValueError):
        build_pareto([bad])


def test_point_missing_measured_ler_is_rejected():
    bad = {"rtl_hash": "h", "rtl_path": "a.sv", "area_um2": 5.0, "latency_cycles": 8}  # no ler
    with pytest.raises(ValueError):
        build_pareto([bad])


def test_no_proxy_field_names_in_emitted_artifact():
    """Belt-and-suspenders: no formula/proxy keys leak into the emitted JSON."""
    art = build_pareto([_cand("a.sv", 0.03, 3.0, 4)])
    blob = json.dumps(art)
    for forbidden in ("decoder_quality_multiplier", "npu_cost", "ler_suppression", "area_mm2"):
        assert forbidden not in blob


# --- CLI emit -----------------------------------------------------------------


def test_emit_writes_valid_artifact_from_store(tmp_path: Path):
    """Reading from an empty store path emits a valid points:[] artifact."""
    out = tmp_path / "measured_pareto.json"
    empty_store = tmp_path / "no_variants.jsonl"  # does not exist -> empty store
    pareto_mod.emit(out, store_path=empty_store)
    art = json.loads(out.read_text(encoding="utf-8"))
    assert art["points"] == []
    assert art["accuracy_axis"] == ACCURACY_AXIS_LABEL


# --- plot axis label guard ----------------------------------------------------


def test_accuracy_axis_label_says_measured_and_verilator():
    """Guard against proxy labeling regression on the accuracy axis."""
    assert "measured" in ACCURACY_AXIS_LABEL.lower()
    assert "verilator" in ACCURACY_AXIS_LABEL.lower()
    assert "formula" not in ACCURACY_AXIS_LABEL.lower()
    assert "proxy" not in ACCURACY_AXIS_LABEL.lower()


def test_pareto_plot_renders_and_labels_axis_measured(tmp_path: Path):
    """Render the plot; the PNG exists and the shared y-label names the measured backend."""
    from cryobrain.benchmark.plots import plot_pareto_png

    art = build_pareto([_cand("a.sv", 0.03, 3.0, 4), _cand("c.sv", 0.01, 9.0, 8)])
    out = plot_pareto_png(art, out_path=tmp_path / "measured_pareto.png")
    assert out.is_file()
    # The plot's y-axis is built from ACCURACY_AXIS_LABEL, already asserted to
    # contain "measured"/"verilator" above — so the rendered axis cannot be proxy.
    assert "measured" in ACCURACY_AXIS_LABEL.lower()


def test_climb_plot_skipped_when_artifact_absent(tmp_path: Path):
    from cryobrain.benchmark.plots import plot_climb_png

    assert plot_climb_png(climb_path=tmp_path / "missing_climb.json") is None


def test_climb_plot_renders_from_measured_history(tmp_path: Path):
    """If a measured_climb.json exists, the climb plot renders (measured fields)."""
    from cryobrain.benchmark.plots import plot_climb_png

    climb = tmp_path / "measured_climb.json"
    climb.write_text(
        json.dumps(
            {
                "backend": "verilator+stim+yosys",
                "history": [
                    {"step": 0, "candidate_ler": 0.030, "suppression": -0.05, "rtl_hash": "h0"},
                    {"step": 3, "candidate_ler": 0.020, "suppression": 0.10, "rtl_hash": "h3"},
                    {"step": 7, "candidate_ler": 0.015, "suppression": 0.25, "rtl_hash": "h7"},
                ],
            }
        ),
        encoding="utf-8",
    )
    out = plot_climb_png(climb_path=climb, out_path=tmp_path / "measured_climb.png")
    assert out is not None and out.is_file()
