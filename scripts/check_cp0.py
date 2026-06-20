#!/usr/bin/env python3
"""CP0 tooling checkpoint: verify HUD + EDA tools on PATH."""

from __future__ import annotations

import shutil
import subprocess
import sys


def _version(cmd: list[str]) -> str:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=10)
        return (proc.stdout or proc.stderr or "").strip().splitlines()[0]
    except (FileNotFoundError, subprocess.TimeoutExpired, IndexError):
        return "missing"


def main() -> int:
    tools = {
        "verilator": ["verilator", "--version"],
        "yosys": ["yosys", "-V"],
        "sby": ["sby", "--version"],
        "z3": ["z3", "-version"],
        "hud": ["hud", "version"],
    }
    ok = True
    for name, cmd in tools.items():
        if shutil.which(cmd[0]) is None:
            print(f"{name}: missing")
            ok = False
            continue
        print(f"{name}: {_version(cmd)}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())