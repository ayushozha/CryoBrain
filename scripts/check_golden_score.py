#!/usr/bin/env python3
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from cryobrain.grader.score import score_measured

ROOT = Path(__file__).resolve().parents[1]
TASK = ROOT / "tasks" / "cryo_brain_decoder"
GOLDEN = TASK / "donotaccess" / "cryo_brain_decoder_golden.sv"

stage = Path(tempfile.mkdtemp())
shutil.copytree(TASK, stage, dirs_exist_ok=True)
shutil.copy2(GOLDEN, stage / "rtl" / "cryo_brain_decoder.sv")
result = score_measured(stage)
print(
    f"golden valid={result['valid']} layers={result['layers_passed']} "
    f"reward={result['reward']:.4f} sup={result['suppression']:.4f} ler={result['ler']:.4f}"
)