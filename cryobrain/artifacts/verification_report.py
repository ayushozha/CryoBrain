"""Aggregate L1–L5 verification results into ``artifacts/verification_report.json`` (X7)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

LAYER_ORDER: tuple[str, ...] = ("L1", "L2", "L3", "L4", "L5")


def _layer_entry(result: Mapping[str, Any] | None) -> dict[str, Any]:
    if not result:
        return {"passed": False, "log_path": "", "skipped": False}
    entry: dict[str, Any] = {
        "passed": bool(result.get("passed", False)),
        "log_path": str(result.get("log_path", "") or ""),
        "skipped": bool(result.get("skipped", False)),
    }
    reason = result.get("reason")
    if reason:
        entry["reason"] = str(reason)
    return entry


def _l2_from_measure(measure: Mapping[str, Any] | None) -> dict[str, Any]:
    if not measure:
        return {"passed": False, "log_path": "", "skipped": False}
    passed = bool(measure.get("rtl_valid")) and int(measure.get("benchmark_vectors", 0)) > 0
    return {
        "passed": passed,
        "log_path": str(measure.get("rtl_path", "") or ""),
        "skipped": False,
        "benchmark_vectors": int(measure.get("benchmark_vectors", 0)),
        "benchmark_failures": int(measure.get("benchmark_failures", 0)),
    }


def layers_passed_from_layers(layers: Mapping[str, Mapping[str, Any]]) -> list[str]:
    """Derive ``layers_passed`` tags from a report ``layers`` block."""
    passed: list[str] = []
    for name in LAYER_ORDER:
        entry = layers.get(name)
        if entry and entry.get("passed"):
            passed.append(name)
    return passed


def build_verification_report(
    *,
    rtl_path: Path | str,
    design: str = "cryo_brain_decoder",
    source: str = "measured",
    l1: Mapping[str, Any] | None = None,
    l2_measure: Mapping[str, Any] | None = None,
    l3: Mapping[str, Any] | None = None,
    l4: Mapping[str, Any] | None = None,
    l5: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a verification report dict from per-layer tool outputs."""
    layers = {
        "L1": _layer_entry(l1),
        "L2": _l2_from_measure(l2_measure),
        "L3": _layer_entry(l3),
        "L4": _layer_entry(l4),
        "L5": _layer_entry(l5),
    }
    layers_passed = layers_passed_from_layers(layers)
    l3_skipped = bool(layers["L3"].get("skipped"))
    required = {"L1", "L2", "L4", "L5"}
    if not l3_skipped:
        required.add("L3")
    all_passed = required.issubset(layers_passed)
    return {
        "design": design,
        "rtl_path": str(rtl_path),
        "source": source,
        "layers": layers,
        "layers_passed": layers_passed,
        "all_passed": all_passed,
    }


def generate_verification_report_template(*, design: str = "cryo_brain_decoder") -> dict[str, Any]:
    """Return an empty template suitable for ``artifacts/verification_report.json``."""
    layers = {name: {"passed": False, "log_path": "", "skipped": False} for name in LAYER_ORDER}
    return {
        "design": design,
        "rtl_path": "rtl/cryo_brain_decoder.sv",
        "source": "measured",
        "layers": layers,
        "layers_passed": [],
        "all_passed": False,
    }


def write_verification_report(
    workdir: Path,
    report: Mapping[str, Any],
    *,
    filename: str = "verification_report.json",
) -> Path:
    """Write ``report`` under ``workdir/artifacts/``."""
    workdir = Path(workdir)
    out = workdir / "artifacts" / filename
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(dict(report), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return out


def write_verification_report_template(
    repo_root: Path | None = None,
    *,
    filename: str = "verification_report.json",
) -> Path:
    """Materialize the checked-in template at ``artifacts/verification_report.json``."""
    root = Path(repo_root) if repo_root is not None else Path(__file__).resolve().parents[2]
    out = root / "artifacts" / filename
    out.parent.mkdir(parents=True, exist_ok=True)
    template = generate_verification_report_template()
    out.write_text(json.dumps(template, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return out