"""X3 / MP5: SymbiYosys L3 formal smoke on cryo_brain_decoder golden RTL."""

from __future__ import annotations

from pathlib import Path

import pytest

from cryobrain.rtl_grader.flow import eda_tools_available
from cryobrain.verify.l3_formal import run_l3_formal, symbiyosys_available

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "tasks" / "cryo_brain_decoder" / "donotaccess" / "cryo_brain_decoder_golden.sv"
WRONG = ROOT / "tasks" / "cryo_brain_decoder" / "donotaccess" / "cryo_brain_decoder_wrong.sv"


def _formal_tools_available() -> bool:
    return eda_tools_available() and symbiyosys_available()


def test_skip_when_sby_missing(monkeypatch):
    monkeypatch.setattr(
        "cryobrain.verify.l3_formal.symbiyosys_available",
        lambda: False,
    )
    result = run_l3_formal(GOLDEN)
    assert result["passed"] is False
    assert result.get("skipped") is True
    assert "sby" in result.get("reason", "").lower()


@pytest.mark.wsl
@pytest.mark.skipif(not _formal_tools_available(), reason="verilator/sby not on PATH")
def test_golden_passes_l3():
    result = run_l3_formal(GOLDEN)
    if result.get("skipped"):
        pytest.skip(result.get("reason", "symbiyosys unavailable"))
    assert result["passed"] is True
    assert result["log_path"]


@pytest.mark.wsl
@pytest.mark.skipif(not _formal_tools_available(), reason="verilator/sby not on PATH")
def test_wrong_fails_l3():
    result = run_l3_formal(WRONG)
    if result.get("skipped"):
        pytest.skip(result.get("reason", "symbiyosys unavailable"))
    assert result["passed"] is False