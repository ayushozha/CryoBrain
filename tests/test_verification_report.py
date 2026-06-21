"""X7: verification report aggregator for L1–L5 layer results."""

from __future__ import annotations

import json
from pathlib import Path

from cryobrain.artifacts.verification_report import (
    build_verification_report,
    generate_verification_report_template,
    layers_passed_from_layers,
    write_verification_report,
    write_verification_report_template,
)


def _mock_layers(*, l3_skipped: bool = False) -> dict:
    return {
        "L1": {"passed": True, "log_path": "/tmp/l1.log", "skipped": False},
        "L2": {
            "passed": True,
            "log_path": "rtl/cryo_brain_decoder.sv",
            "skipped": False,
            "benchmark_vectors": 64,
            "benchmark_failures": 0,
        },
        "L3": {
            "passed": not l3_skipped,
            "log_path": "/tmp/l3.log",
            "skipped": l3_skipped,
            **({"reason": "symbiyosys (sby) not on PATH"} if l3_skipped else {}),
        },
        "L4": {"passed": True, "log_path": "/tmp/l4.log", "skipped": False},
        "L5": {"passed": True, "log_path": "", "skipped": False},
    }


def test_build_report_layers_passed_matches_tool_output():
    report = build_verification_report(
        rtl_path="rtl/cryo_brain_decoder.sv",
        l1={"passed": True, "log_path": "/tmp/l1.log"},
        l2_measure={"rtl_valid": True, "benchmark_vectors": 64, "benchmark_failures": 0, "rtl_path": "rtl/x.sv"},
        l3={"passed": True, "log_path": "/tmp/l3.log"},
        l4={"passed": True, "log_path": "/tmp/l4.log", "cell_count": 42},
        l5={"passed": True, "area_um2": 1200.0, "latency_cycles": 8, "power_mw_est": 1.2},
    )
    assert report["layers_passed"] == ["L1", "L2", "L3", "L4", "L5"]
    assert report["all_passed"] is True
    assert report["source"] == "measured"
    assert report["layers"]["L4"]["passed"] is True


def test_skipped_l3_does_not_block_all_passed():
    report = build_verification_report(
        rtl_path="rtl/cryo_brain_decoder.sv",
        l1={"passed": True, "log_path": ""},
        l2_measure={"rtl_valid": True, "benchmark_vectors": 8, "benchmark_failures": 0},
        l3={"passed": False, "log_path": "", "skipped": True, "reason": "symbiyosys (sby) not on PATH"},
        l4={"passed": True, "log_path": ""},
        l5={"passed": True},
    )
    assert report["layers_passed"] == ["L1", "L2", "L4", "L5"]
    assert report["all_passed"] is True


def test_layers_passed_from_layers_helper():
    layers = _mock_layers()
    assert layers_passed_from_layers(layers) == ["L1", "L2", "L3", "L4", "L5"]


def test_write_report_to_workdir(tmp_path: Path):
    report = build_verification_report(
        rtl_path=tmp_path / "rtl" / "cryo_brain_decoder.sv",
        l1={"passed": False, "log_path": ""},
    )
    out = write_verification_report(tmp_path, report)
    assert out == tmp_path / "artifacts" / "verification_report.json"
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert loaded["design"] == "cryo_brain_decoder"
    assert "layers" in loaded


def test_generate_template_has_all_layers():
    template = generate_verification_report_template()
    assert set(template["layers"]) == {"L1", "L2", "L3", "L4", "L5"}
    assert template["layers_passed"] == []
    assert template["all_passed"] is False


def test_write_template_materializes_file(tmp_path: Path):
    out = write_verification_report_template(tmp_path)
    assert out.is_file()
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["rtl_path"] == "rtl/cryo_brain_decoder.sv"