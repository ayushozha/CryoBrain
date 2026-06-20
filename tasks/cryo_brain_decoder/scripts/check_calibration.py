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
HIDDEN = ROOT / "donotaccess"


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
    grade_mod = _load_grade()
    workdir = _stage_baseline()

    wrong = grade_mod.grade(workdir, rtl_override=HIDDEN / "cryo_brain_decoder_wrong.sv", hidden_root=HIDDEN)
    starter = grade_mod.grade(workdir, hidden_root=HIDDEN)
    golden = grade_mod.grade(workdir, rtl_override=HIDDEN / "cryo_brain_decoder_golden.sv", hidden_root=HIDDEN)

    summary = {
        "wrong": wrong["reward"],
        "starter": starter["reward"],
        "golden": golden["reward"],
    }
    print(json.dumps(summary, indent=2))

    ok = summary["wrong"] == 0.0 and 0.15 <= summary["starter"] <= 0.55 and summary["golden"] >= 0.6
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())