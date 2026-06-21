#!/usr/bin/env python3
"""Quick L3 smoke: print formal results for golden vs wrong RTL."""
from __future__ import annotations

from pathlib import Path

from cryobrain.verify.l3_formal import run_l3_formal

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "tasks/cryo_brain_decoder/donotaccess/cryo_brain_decoder_golden.sv"
WRONG = ROOT / "tasks/cryo_brain_decoder/donotaccess/cryo_brain_decoder_wrong.sv"

for label, path in ("golden", GOLDEN), ("wrong", WRONG):
    print(label, run_l3_formal(path))