#!/usr/bin/env python3
"""Calibration driver (CP2 sanity + CP3 multi-rollout gate)."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
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


def main() -> int:
    parser = argparse.ArgumentParser(description="CryoBrain CP2/CP3 calibration")
    parser.add_argument("--cp2-only", action="store_true", help="Run CP2 sanity only")
    parser.add_argument("--cp3-only", action="store_true", help="Run CP3 rollouts only")
    args = parser.parse_args()

    from cryobrain.calibration.cp3 import run_cp2_sanity, run_cp3_rollouts
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

    def _grade_starter(workdir: Path) -> dict[str, object]:
        return grade_mod.grade(workdir, hidden_root=HIDDEN)

    run_cp2 = not args.cp3_only
    run_cp3 = not args.cp2_only

    payload: dict[str, object] = {"ok": True}
    if run_cp2:
        cp2 = run_cp2_sanity(grade_mod.grade, ROOT, HIDDEN)
        payload["cp2"] = cp2
        if not cp2["ok"]:
            payload["ok"] = False

    if run_cp3:
        cp3_result = run_cp3_rollouts(_grade_starter, ROOT)
        payload["cp3"] = cp3_result["cp3"]
        payload["rollouts"] = cp3_result["rollouts"]
        payload["starter_rewards"] = cp3_result["rewards"]
        if not cp3_result["cp3"]["ok"]:
            payload["ok"] = False

    print(json.dumps(payload, indent=2))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())