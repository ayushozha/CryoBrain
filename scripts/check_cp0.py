#!/usr/bin/env python3
"""CP0 tooling checkpoint: real EDA binaries + HUD surface + WSL fallback on Windows."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _to_wsl_path(path: Path) -> str:
    drive = path.drive.rstrip(":").lower()
    tail = path.as_posix().split(":", 1)[1]
    return f"/mnt/{drive}{tail}"


def _version(cmd: list[str]) -> str:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=15)
        return (proc.stdout or proc.stderr or "").strip().splitlines()[0]
    except (FileNotFoundError, subprocess.TimeoutExpired, IndexError):
        return "missing"


def _check_eda_on_path() -> tuple[bool, dict[str, str]]:
    tools = {
        "verilator": ["verilator", "--version"],
        "yosys": ["yosys", "-V"],
        "sby": ["sby", "--version"],
        "z3": ["z3", "-version"],
    }
    versions: dict[str, str] = {}
    ok = True
    for name, cmd in tools.items():
        if shutil.which(cmd[0]) is None:
            versions[name] = "missing"
            ok = False
        else:
            versions[name] = _version(cmd)
    return ok, versions


def _run_wsl_cp0() -> int:
    script = _to_wsl_path(ROOT / "scripts" / "run_cp0_wsl.sh")
    return subprocess.run(["wsl", "-e", "bash", script], cwd=ROOT).returncode


def main() -> int:
    ok, versions = _check_eda_on_path()
    for name, ver in versions.items():
        print(f"{name}: {ver}")

    if shutil.which("hud") is None:
        for candidate in (ROOT / ".venv" / "Scripts" / "hud.exe", ROOT / ".venv-linux" / "bin" / "hud"):
            if candidate.is_file():
                print(f"hud: {_version([str(candidate), 'version'])}")
                break
        else:
            print("hud: missing (run uv sync)")
            ok = False
    else:
        print(f"hud: {_version(['hud', 'version'])}")

    if not ok and platform.system() == "Windows" and shutil.which("wsl"):
        print("\nEDA missing on Windows — running real CP0 in WSL (OSS CAD + hud eval)...")
        return _run_wsl_cp0()

    try:
        import env  # noqa: F401
        import task_catalog
        import tasks

        print(f"task_catalog: {len(task_catalog.TASK_SPECS)} eval slugs")
        print(f"tasks.py: {len(tasks.tasks)} bound scenarios")
    except Exception as exc:  # noqa: BLE001
        print(f"hud_surface: import failed ({type(exc).__name__}: {exc})")
        ok = False

    if not ok:
        print("hint: bash scripts/install_oss_cad_wsl.sh && bash scripts/run_cp0_wsl.sh")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())