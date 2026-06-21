#!/usr/bin/env python3
"""Hidden grader: measured LER + Yosys hardware reward (SPEC-v5 G10)."""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _stage_with_rtl(workdir: Path, rtl_src: Path) -> Path:
    stage = Path(tempfile.mkdtemp(prefix="cryobrain-grade-"))
    shutil.copytree(workdir, stage, dirs_exist_ok=True, symlinks=True)
    shutil.copy2(rtl_src, stage / "rtl" / "cryo_brain_decoder.sv")
    return stage


def grade(
    workdir: Path,
    rtl_override: Path | None = None,
    hidden_root: Path | None = None,
) -> dict[str, object]:
    _ = hidden_root
    if rtl_override is not None:
        workdir = _stage_with_rtl(workdir, rtl_override)

    from cryobrain.cost_model.npu_cost import HardwareMetrics
    from cryobrain.grader.score import grade_result_to_subscores, score_measured

    score = score_measured(workdir)
    metrics = HardwareMetrics(
        mac_count=0,
        area_mm2=score["area_um2"] / 1_000_000.0,
        latency_cycles=score["latency_cycles"],
        power_mw=score["power_mw"],
    )
    subscores = grade_result_to_subscores(score, metrics=metrics)

    return {
        "reward": score["reward"],
        "hard_caps": score["hard_caps"],
        "subscores": subscores,
        "info": {
            "valid": score["valid"],
            "ler": score["ler"],
            "mwpm_ler": score["mwpm_ler"],
            "suppression": score["suppression"],
            "layers_passed": score["layers_passed"],
            "area_um2": score["area_um2"],
            "latency_cycles": score["latency_cycles"],
            "power_mw": score["power_mw"],
            "source": "measured",
            "measurement": score.get("measurement"),
            "synth": score.get("synth"),
        },
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("workdir", type=Path, nargs="?", default=ROOT)
    args = parser.parse_args()
    print(json.dumps(grade(args.workdir), indent=2))