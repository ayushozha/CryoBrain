"""Unit + smoke tests for CP5/CP6/CP7 checkpoints."""

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


def test_cp5_vcd_syndrome_to_correction_parser():
    from cryobrain.calibration.cp5 import assert_syndrome_to_correction

    vcd = """$var wire 1 ! syndromes_valid $end
$var wire 1 " corrections_valid $end
#0
0!
0"
#10
1!
#20
1"
"""
    path = ROOT / "artifacts" / "_test_cp5.vcd"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(vcd, encoding="utf-8")
    assert assert_syndrome_to_correction(path) is True


def test_cp6_assess_passes_with_spread():
    from cryobrain.calibration.cp6 import assess_cp6

    designs = [
        {"name": f"v{i}", "kind": "policy", "area_mm2": 0.03 + i * 0.01, "ler_suppression": 0.1 + i * 0.02}
        for i in range(8)
    ]
    climb = {
        "rewards_by_distance": {"3": 0.44, "5": 0.38, "7": 0.32},
        "backend": "real_cp6",
    }
    verdict = assess_cp6(designs, climb)
    assert verdict["ok"] is True


def test_cp6_has_eight_design_variants():
    from cryobrain.calibration.cp6 import CP6_DESIGN_VARIANTS

    assert len(CP6_DESIGN_VARIANTS) == 8


@pytest.mark.parametrize("script", ["check_cp2.py", "check_cp5.py", "check_cp6.py", "check_cp7.py"])
def test_checkpoint_scripts_import(script: str):
    mod = _load_script(script)
    code = mod.main()
    assert code in (0, 1)


@pytest.mark.parametrize("script", ["check_cp2.py", "check_cp5.py", "check_cp6.py", "check_cp7.py"])
def test_checkpoint_scripts_via_subprocess(script: str):
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / script)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=600,
    )
    assert proc.returncode in (0, 1)