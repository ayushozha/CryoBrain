#!/usr/bin/env python3
"""CP5 checkpoint: golden Yosys synth + Verilator trace waveform."""

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


def _run_wsl_cp5() -> int:
    script = _to_wsl_path(ROOT / "scripts" / "run_cp5_wsl.sh")
    return subprocess.run(["wsl", "-e", "bash", script], cwd=ROOT).returncode


def _load_grade():
    spec = importlib.util.spec_from_file_location("cryo_hidden_grade", HIDDEN / "grade.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    from cryobrain.calibration.cp5 import assess_cp5, run_cp5_artifacts
    from cryobrain.rtl_grader.flow import eda_tools_available

    if not eda_tools_available() and platform.system() == "Windows" and shutil.which("wsl"):
        print("EDA missing on Windows — running real CP5 artifacts in WSL...")
        return _run_wsl_cp5()

    result = run_cp5_artifacts(TASK_ROOT, HIDDEN, artifacts_dir=ROOT / "artifacts")
    verdict = assess_cp5(result)
    payload = {
        "ok": verdict["ok"],
        "cp5": verdict,
        "details": result.details,
    }
    print(json.dumps(payload, indent=2))
    if not verdict["ok"]:
        print(f"CP5 failed: {', '.join(verdict['reasons'])}", file=sys.stderr)
        return 1
    print(
        f"CP5 passed: cells={result.cell_count} latches={result.latch_count} "
        f"vcd={result.vcd_path} syndrome_to_correction={result.syndrome_to_correction}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())