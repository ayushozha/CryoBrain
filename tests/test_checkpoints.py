"""Checkpoint script smoke tests (CP0/CP1)."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load_script(name: str):
    path = ROOT / "scripts" / name
    spec = importlib.util.spec_from_file_location(name.replace(".py", ""), path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_check_cp0_imports_and_runs():
    mod = _load_script("check_cp0.py")
    code = mod.main()
    assert code in (0, 1)


def test_check_cp1_imports_and_runs():
    mod = _load_script("check_cp1.py")
    code = mod.main()
    assert code in (0, 1)


@pytest.mark.parametrize(
    "script",
    ["check_cp2.py", "check_cp5.py", "check_cp6.py", "check_cp7.py"],
)
def test_new_checkpoint_scripts_import(script: str):
    mod = _load_script(script)
    code = mod.main()
    assert code in (0, 1)


def test_check_cp0_via_subprocess():
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_cp0.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode in (0, 1)
    assert "verilator" in proc.stdout.lower() or "missing" in proc.stdout.lower()


@pytest.mark.parametrize(
    "module_path",
    ["env", "task_catalog", "tasks", "grader", "scenario_helpers"],
)
def test_hud_surface_imports(module_path: str):
    proc = subprocess.run(
        [sys.executable, "-c", f"import {module_path}"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr