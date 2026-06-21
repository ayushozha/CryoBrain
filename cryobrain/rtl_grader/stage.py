"""Stage cryo_brain_decoder task layout around a candidate RTL file."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

TASK_ROOT = Path(__file__).resolve().parents[2] / "tasks" / "cryo_brain_decoder"


def stage_rtl_workdir(rtl_path: Path, *, prefix: str = "cryobrain-rtl-") -> Path:
    rtl_path = rtl_path.resolve()
    if not rtl_path.is_file():
        raise FileNotFoundError(f"RTL not found: {rtl_path}")
    stage = Path(tempfile.mkdtemp(prefix=prefix))
    for sub in ("dv", "synth", "rtl"):
        src = TASK_ROOT / sub
        if src.is_dir():
            shutil.copytree(src, stage / sub, dirs_exist_ok=True)
    shutil.copy2(rtl_path, stage / "rtl" / "cryo_brain_decoder.sv")
    for name in ("scenario.json", "design_config.json"):
        src = TASK_ROOT / name
        if src.is_file():
            shutil.copy2(src, stage / name)
    (stage / "reports").mkdir(parents=True, exist_ok=True)
    (stage / "build").mkdir(parents=True, exist_ok=True)
    return stage


def cleanup_stage(stage: Path) -> None:
    shutil.rmtree(stage, ignore_errors=True)