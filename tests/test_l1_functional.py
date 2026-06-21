"""G6: L1 Verilator lint gate."""

from __future__ import annotations

from pathlib import Path

import pytest

from cryobrain.rtl_grader.flow import eda_tools_available
from cryobrain.verify.l1_functional import run_l1

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "tasks" / "cryo_brain_decoder" / "donotaccess" / "cryo_brain_decoder_golden.sv"
WRONG = ROOT / "tasks" / "cryo_brain_decoder" / "donotaccess" / "cryo_brain_decoder_wrong.sv"

pytestmark = pytest.mark.skipif(not eda_tools_available(), reason="verilator not on PATH")


def test_golden_passes_l1():
    assert run_l1(GOLDEN)["passed"] is True


def test_wrong_still_lints():
    # Zero-output RTL is syntactically valid.
    assert run_l1(WRONG)["passed"] is True