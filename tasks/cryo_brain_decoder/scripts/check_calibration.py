#!/usr/bin/env python3
"""Calibration driver (CP2/CP3): wrong → 0, starter → mid, golden → high."""

from __future__ import annotations

import importlib.util
import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parents[1]
HIDDEN = ROOT / "donotaccess"

if str(WORKSPACE) not in sys.path:
    sys.path.insert(0, str(WORKSPACE))


def _load_grade():
    spec = importlib.util.spec_from_file_location("cryo_hidden_grade", HIDDEN / "grade.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _stage_baseline() -> Path:
    stage = Path(tempfile.mkdtemp(prefix="cryobrain-calib-"))
    for name in ("Makefile", "filelist.f", "rtl", "dv", "synth", "design_config.json", "scenario.json"):
        src = ROOT / name
        if not src.exists():
            continue
        dst = stage / name
        if src.is_dir():
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)
    return stage


def main() -> int:
    from cryobrain.rtl_grader.flow import eda_tools_available, missing_eda_tools

    if not eda_tools_available():
        missing = missing_eda_tools()
        print(
            json.dumps(
                {
                    "ok": False,
                    "skipped": True,
                    "reason": "EDA tools not on PATH",
                    "missing_tools": missing,
                    "hint": (
                        "Install OSS CAD Suite (verilator + yosys) and add its bin directory to PATH, "
                        "or set OSS_CAD_SUITE_ROOT. On Windows, WSL/Linux is the supported local path."
                    ),
                },
                indent=2,
            )
        )
        return 1

    grade_mod = _load_grade()
    workdir = _stage_baseline()

    wrong = grade_mod.grade(workdir, rtl_override=HIDDEN / "cryo_brain_decoder_wrong.sv", hidden_root=HIDDEN)
    starter = grade_mod.grade(workdir, hidden_root=HIDDEN)
    golden = grade_mod.grade(workdir, rtl_override=HIDDEN / "cryo_brain_decoder_golden.sv", hidden_root=HIDDEN)

    summary = {
        "wrong": wrong["reward"],
        "starter": starter["reward"],
        "golden": golden["reward"],
        "details": {
            "wrong_caps": wrong.get("hard_caps"),
            "starter_caps": starter.get("hard_caps"),
            "golden_caps": golden.get("hard_caps"),
        },
    }
    summary["ok"] = (
        summary["wrong"] == 0.0
        and 0.20 <= summary["starter"] <= 0.50
        and summary["golden"] >= 0.60
    )
    print(json.dumps(summary, indent=2))

    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())