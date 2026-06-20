#!/usr/bin/env python3
"""CP3 gating checkpoint: ~10 real rollouts, mean reward 20–50% with variance."""

from __future__ import annotations

import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CALIB_SCRIPT = ROOT / "tasks" / "cryo_brain_decoder" / "scripts" / "check_calibration.py"


def _to_wsl_path(path: Path) -> str:
    drive = path.drive.rstrip(":").lower()
    tail = path.as_posix().split(":", 1)[1]
    return f"/mnt/{drive}{tail}"


def _run_wsl_cp3() -> int:
    script = _to_wsl_path(ROOT / "scripts" / "run_cp3_wsl.sh")
    return subprocess.run(["wsl", "-e", "bash", script], cwd=ROOT).returncode


def _python() -> str:
    venv_linux = ROOT / ".venv-linux" / "bin" / "python"
    if venv_linux.is_file():
        return str(venv_linux)
    return sys.executable


def main() -> int:
    from cryobrain.rtl_grader.flow import eda_tools_available

    if not eda_tools_available() and platform.system() == "Windows" and shutil.which("wsl"):
        print("EDA missing on Windows — running real CP3 calibration in WSL...")
        code = _run_wsl_cp3()
        if code == 0:
            print("CP3 gate passed via WSL (see JSON summary above)")
        return code

    proc = subprocess.run(
        [_python(), str(CALIB_SCRIPT)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    stdout = proc.stdout or proc.stderr
    print(stdout)
    if proc.returncode != 0:
        return proc.returncode

    data = json.loads(stdout)
    cp3 = data.get("cp3", {})
    stats = cp3.get("stats", {})
    mean = float(stats.get("mean", 0.0))
    ok = bool(data.get("ok")) and 0.20 <= mean <= 0.50
    if not ok:
        reasons = cp3.get("reasons", ["calibration_failed"])
        print(f"CP3 gate failed: {', '.join(reasons)}", file=sys.stderr)
        return 1
    print(
        f"CP3 gate passed: mean={mean:.3f} std={float(stats.get('std', 0.0)):.3f} "
        f"spread={float(stats.get('spread', 0.0)):.3f}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())