"""Materialize Stim-derived benchmark vector files per manifest split."""

from __future__ import annotations

from pathlib import Path

from cryobrain.accuracy.benchmark_vectors import generate_rtl_benchmark, write_rtl_benchmark
from cryobrain.stim.manifest import TASK_STIM_ROOT, split_config
from cryobrain.types import ScenarioConfig


def materialize_split(split: str, *, out_dir: Path | None = None) -> Path:
    cfg = split_config(split)
    scenario = ScenarioConfig.from_dict(cfg["scenario"])
    benchmark = generate_rtl_benchmark(
        scenario,
        seed=int(cfg["seed"]),
        vectors=int(cfg["vectors"]),
    )
    out_dir = out_dir or (TASK_STIM_ROOT / split)
    out_dir.mkdir(parents=True, exist_ok=True)
    return write_rtl_benchmark(out_dir / "vectors.mem", benchmark)