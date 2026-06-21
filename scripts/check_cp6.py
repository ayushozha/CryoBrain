#!/usr/bin/env python3
"""CP6 checkpoint: real Pareto designs + d=3→5→7 curriculum artifacts."""

from __future__ import annotations

import importlib.util
import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TASK_ROOT = ROOT / "tasks" / "cryo_brain_decoder"
HIDDEN = TASK_ROOT / "donotaccess"


def _to_wsl_path(path: Path) -> str:
    drive = path.drive.rstrip(":").lower()
    tail = path.as_posix().split(":", 1)[1]
    return f"/mnt/{drive}{tail}"


def _run_wsl_cp6() -> int:
    script = _to_wsl_path(ROOT / "scripts" / "run_cp6_wsl.sh")
    return subprocess.run(["wsl", "-e", "bash", script], cwd=ROOT).returncode


def _load_grade():
    spec = importlib.util.spec_from_file_location("cryo_hidden_grade", HIDDEN / "grade.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    from cryobrain.artifacts.pareto import generate_all_artifacts
    from cryobrain.calibration.cp6 import run_cp6_collection
    from cryobrain.rtl_grader.flow import eda_tools_available

    if not eda_tools_available() and platform.system() == "Windows" and shutil.which("wsl"):
        print("EDA missing on Windows — running real CP6 collection in WSL...")
        return _run_wsl_cp6()

    grade_mod = _load_grade()

    def _grade(workdir: Path, *, hidden_root: Path) -> dict[str, object]:
        return grade_mod.grade(workdir, hidden_root=hidden_root)

    collection = run_cp6_collection(_grade, TASK_ROOT, HIDDEN, artifacts_dir=ROOT / "artifacts")
    outputs = generate_all_artifacts(
        climb_chart_path=ROOT / "artifacts" / "climb_chart.json",
        designs_path=ROOT / "artifacts" / "designs.json",
        artifacts_dir=ROOT / "artifacts",
    )
    assessment = collection["assessment"]
    payload = {
        "ok": assessment["ok"],
        "assessment": assessment,
        "paths": collection["paths"],
        "artifacts": {k: str(v) for k, v in outputs.items()},
    }
    print(json.dumps(payload, indent=2))
    if not assessment["ok"]:
        print(f"CP6 failed: {', '.join(assessment['reasons'])}", file=sys.stderr)
        return 1
    print(
        f"CP6 passed: {assessment['policy_designs']} policy designs, "
        f"ler_spread={assessment['ler_spread']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())