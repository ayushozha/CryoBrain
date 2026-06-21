#!/usr/bin/env python3
"""Debug one measured proposal step in WSL."""
from __future__ import annotations

import json
from pathlib import Path

from cryobrain.design.config import preset_variants
from cryobrain.rl.proposal_loop import run_proposal_step

ROOT = Path(__file__).resolve().parents[1]
scenario = json.loads((ROOT / "tasks/cryo_brain_decoder/scenario.json").read_text(encoding="utf-8"))

from cryobrain.grader.score import score_measured
from cryobrain.rl.proposal_loop import build_workdir
from cryobrain.verify.l1_functional import run_l1
from cryobrain.accuracy.measured_ler import measure_candidate_ler
from cryobrain.types import ScenarioConfig

from cryobrain.rtl_gen.generator import generate_rtl
import tempfile

for i, design in enumerate(preset_variants()[:3]):
    direct = generate_rtl(design, Path(tempfile.mkdtemp()) / "rtl")
    workdir = build_workdir(design, scenario)
    rtl = workdir / "rtl" / "cryo_brain_decoder.sv"
    score = score_measured(workdir)
    r = run_proposal_step(step=i, design=design, scenario=scenario)
    sc = ScenarioConfig.from_dict(scenario)
    sc_mp1 = ScenarioConfig(distance=3, noise_rate=0.02, shots=500, rounds=3)
    for label, path in ("direct", direct), ("staged", rtl):
        l1 = run_l1(path)
        meas = measure_candidate_ler(path, sc_mp1, seed=1729 + i)
        print(
            f"  {label}[{i}] l1={l1['passed']} meas_valid={meas.get('rtl_valid')} "
            f"vecs={meas.get('benchmark_vectors')} ler={meas.get('candidate_ler')}"
        )
    print(
        f"preset[{i}] score_valid={score.get('valid')} layers={score.get('layers_passed')}"
    )
    print(
        f"  step valid={r.valid} reward={r.reward:.4f} ler={r.candidate_ler:.4f} "
        f"sup={r.suppression:+.4f} layers={r.layers_passed}"
    )