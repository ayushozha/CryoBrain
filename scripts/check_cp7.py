#!/usr/bin/env python3
"""CP7 checkpoint: all three FIFO fallback tasks green."""

from __future__ import annotations

import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FIFO_TASKS = (
    ("stream_arb_fifo_repair", "repair"),
    ("stream_arb_fifo_cocotb_dv", "cocotb-dv"),
    ("stream_arb_fifo_formal", "formal"),
)


def _to_wsl_path(path: Path) -> str:
    drive = path.drive.rstrip(":").lower()
    tail = path.as_posix().split(":", 1)[1]
    return f"/mnt/{drive}{tail}"


def _run_wsl_cp7() -> int:
    script = _to_wsl_path(ROOT / "scripts" / "run_cp7_wsl.sh")
    return subprocess.run(["wsl", "-e", "bash", script], cwd=ROOT).returncode


def _python() -> str:
    venv_linux = ROOT / ".venv-linux" / "bin" / "python"
    if venv_linux.is_file():
        return str(venv_linux)
    return sys.executable


def _run_calibration(task_id: str) -> tuple[bool, str]:
    script = ROOT / "tasks" / task_id / "scripts" / "check_calibration.py"
    proc = subprocess.run(
        [_python(), str(script)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    output = (proc.stdout or proc.stderr).strip()
    return proc.returncode == 0, output


def main() -> int:
    from cryobrain.rtl_grader.flow import eda_tools_available

    if not eda_tools_available() and platform.system() == "Windows" and shutil.which("wsl"):
        print("EDA missing on Windows — running real CP7 FIFO calibrations in WSL...")
        return _run_wsl_cp7()

    ok = True
    for task_id, label in FIFO_TASKS:
        passed, output = _run_calibration(task_id)
        status = "PASS" if passed else "FAIL"
        print(f"[{status}] {label} ({task_id})")
        if output:
            print(output)
        ok = ok and passed

    if not ok:
        print("CP7 failed: one or more FIFO calibrations did not pass", file=sys.stderr)
        return 1
    print("CP7 passed: repair + cocotb-dv + formal calibrations green")
    return 0


if __name__ == "__main__":
    sys.exit(main())