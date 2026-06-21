#!/usr/bin/env python3
"""CP2 formalize checkpoint: wrong→0, starter mid-band, golden≥0.60."""

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


def _run_wsl_cp2() -> int:
    script = _to_wsl_path(ROOT / "scripts" / "run_cp2_wsl.sh")
    return subprocess.run(["wsl", "-e", "bash", script], cwd=ROOT).returncode


def _python() -> str:
    venv_linux = ROOT / ".venv-linux" / "bin" / "python"
    if venv_linux.is_file():
        return str(venv_linux)
    return sys.executable


def main() -> int:
    from cryobrain.rtl_grader.flow import eda_tools_available

    if not eda_tools_available() and platform.system() == "Windows" and shutil.which("wsl"):
        print("EDA missing on Windows — running real CP2 sanity in WSL...")
        return _run_wsl_cp2()

    proc = subprocess.run(
        [_python(), str(CALIB_SCRIPT), "--cp2-only"],
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
    cp2 = data.get("cp2", {})
    ok = bool(cp2.get("ok"))
    if not ok:
        print(
            f"CP2 failed: wrong={cp2.get('wrong')} starter={cp2.get('starter')} golden={cp2.get('golden')}",
            file=sys.stderr,
        )
        return 1
    print(
        f"CP2 passed: wrong={cp2.get('wrong')} starter={cp2.get('starter')} golden={cp2.get('golden')}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())