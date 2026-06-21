"""Measured candidate LER from Stim vectors + Verilator RTL (SPEC-v5 P0)."""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

from cryobrain.accuracy.stim_harness import surface_code_logical_error_rate
from cryobrain.accuracy.types import MeasureResult
from cryobrain.reward.compute_reward import ler_suppression_vs_mwpm
from cryobrain.rtl_grader.flow import run_rtl_flow
from cryobrain.types import ScenarioConfig

TASK_ROOT = Path(__file__).resolve().parents[2] / "tasks" / "cryo_brain_decoder"
_MIN_BENCHMARK_NOISE = 0.02
_DEFAULT_BENCHMARK_VECTORS = 64
_DEFAULT_BENCHMARK_SEED = 1729


def _stage_rtl_workdir(rtl_path: Path) -> Path:
    rtl_path = rtl_path.resolve()
    if not rtl_path.is_file():
        raise FileNotFoundError(f"RTL not found: {rtl_path}")
    stage = Path(tempfile.mkdtemp(prefix="cryobrain-measure-"))
    for sub in ("dv", "synth", "rtl"):
        src = TASK_ROOT / sub
        if src.is_dir():
            shutil.copytree(src, stage / sub, dirs_exist_ok=True)
    shutil.copy2(rtl_path, stage / "rtl" / "cryo_brain_decoder.sv")
    scenario_src = TASK_ROOT / "scenario.json"
    if scenario_src.is_file():
        shutil.copy2(scenario_src, stage / "scenario.json")
    design_src = TASK_ROOT / "design_config.json"
    if design_src.is_file():
        shutil.copy2(design_src, stage / "design_config.json")
    return stage


def _grading_scenario(scenario: ScenarioConfig, *, shots: int) -> ScenarioConfig:
    return ScenarioConfig(
        distance=scenario.distance,
        noise_rate=max(scenario.noise_rate, _MIN_BENCHMARK_NOISE),
        shots=max(shots, scenario.shots),
        rounds=scenario.rounds,
    )


def _write_benchmark_scenario(stage: Path, scenario: ScenarioConfig, *, seed: int, vectors: int) -> None:
    raw = json.loads((stage / "scenario.json").read_text(encoding="utf-8"))
    raw.update(
        {
            "distance": scenario.distance,
            "noise_rate": max(scenario.noise_rate, _MIN_BENCHMARK_NOISE),
            "shots": scenario.shots,
            "rounds": scenario.rounds,
            "benchmark_seed": seed,
            "benchmark_vectors": vectors,
        }
    )
    (stage / "scenario.json").write_text(json.dumps(raw, indent=2) + "\n", encoding="utf-8")


def _candidate_ler_from_flow(rtl_flow) -> tuple[float, int, int]:
    vectors = int(rtl_flow.benchmark_vectors)
    failures = int(rtl_flow.benchmark_failures)
    if vectors <= 0:
        return 1.0, 0, 0
    return failures / vectors, vectors, failures


def measure_candidate_ler(
    rtl_path: Path,
    scenario: ScenarioConfig,
    *,
    shots: int = 1000,
    seed: int = 0,
    benchmark_vectors: int = _DEFAULT_BENCHMARK_VECTORS,
) -> MeasureResult:
    """Run ``rtl_path`` in Verilator on Stim-derived vectors; return measured LER.

    ``candidate_ler`` = benchmark decode failures / vectors (not a formula).
    ``mwpm_ler`` = PyMatching anchor from the same Stim scenario.
    """
    stage = _stage_rtl_workdir(rtl_path)
    try:
        bench_seed = seed if seed else _DEFAULT_BENCHMARK_SEED
        _write_benchmark_scenario(stage, scenario, seed=bench_seed, vectors=benchmark_vectors)
        rtl_flow = run_rtl_flow(stage)
        candidate_ler, vectors, failures = _candidate_ler_from_flow(rtl_flow)

        graded = _grading_scenario(scenario, shots=shots)
        mwpm_stats = surface_code_logical_error_rate(
            distance=graded.distance,
            noise_rate=graded.noise_rate,
            shots=graded.shots,
            rounds=graded.rounds,
            decoder="mwpm",
        )
        mwpm_ler = float(mwpm_stats["logical_error_rate"])
        suppression = ler_suppression_vs_mwpm(candidate_ler, mwpm_ler)

        meta = {}
        if "benchmark_metadata" in rtl_flow.logs:
            meta = json.loads(rtl_flow.logs["benchmark_metadata"])

        return MeasureResult(
            candidate_ler=candidate_ler,
            mwpm_ler=mwpm_ler,
            suppression=suppression,
            shots=graded.shots,
            vector_source=str(meta.get("source", "Stim surface_code benchmark vectors")),
            rtl_path=str(rtl_path.resolve()),
            benchmark_vectors=vectors,
            benchmark_failures=failures,
            rtl_valid=rtl_flow.rtl_valid,
        )
    finally:
        shutil.rmtree(stage, ignore_errors=True)