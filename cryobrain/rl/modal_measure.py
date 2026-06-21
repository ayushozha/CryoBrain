"""Parallel Verilator/Yosys measurement fan-out on Modal (SPEC-v5 C3 / MP3).

Given N RTL paths + a scenario, fan out the **real** measured scorer across
parallel Modal containers and collect the results into a list of
``score_measured``-shaped dicts. We never reimplement measurement: each container
runs Grok's :func:`cryobrain.grader.score.score_measured` (which itself runs the
L1/L4/L5 gates, ``measure_candidate_ler`` for Stim->Verilator real LER, and
``synth_metrics`` for Yosys). Modal only *parallelizes* that real measure.

Public API
----------
``measure_batch(rtl_paths, scenario, ...) -> list[dict]``
    One measured result per RTL path (order preserved). Dispatches to Modal's
    ``.map`` when ``modal`` is installed and ``MODAL_TOKEN_ID/SECRET`` are set;
    otherwise runs the same real scorer locally (the measured-LER fallback C5
    documents — real numbers if EDA is present; an honest invalid/zero
    ``score_measured`` result if not — **never a faked number**).

``make_modal_score_fn(scenario, ...) -> Callable[[Path], dict]``
    A ``ScoreFn``-compatible callable (``workdir -> score dict``) C4/C5 can swap
    into ``measured_reward(score_fn=...)``. It routes a single workdir through
    the same Modal fan-out (batch of one), so the GRPO/local reward boundary can
    transparently run on Modal.

Windows note
------------
``modal`` + the EDA stack (verilator/yosys/stim) are Linux-only. This module is
import-guarded: ``import modal`` happens inside helpers, never at top level, so
it imports cleanly on Windows. The Windows gate is import + ``--dry-run`` + a
unit test that mocks the Modal/measure boundary. The real fan-out runs on Modal.
"""

from __future__ import annotations

import argparse
import atexit
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Callable, Sequence

from cryobrain.grader.score import score_measured
from cryobrain.integrations.secrets import get_key
from cryobrain.rl.modal_app import APP_NAME, REMOTE_TASK_DIR
from cryobrain.types import ScenarioConfig

ROOT = Path(__file__).resolve().parents[2]
TASK_ROOT = ROOT / "tasks" / "cryo_brain_decoder"

# A measured-score function (Grok G10 shape): workdir -> score dict.
ScoreFn = Callable[[Path], dict[str, Any]]


# --- scenario + workdir staging ----------------------------------------------


def _load_scenario(task_root: Path = TASK_ROOT) -> dict[str, Any]:
    """Default scenario for the fan-out, mirroring the trainer's grading floor."""
    raw = json.loads((task_root / "scenario.json").read_text(encoding="utf-8"))
    raw.setdefault("benchmark_vectors", 64)
    return raw


def _stage_measure_workdir(rtl_path: Path, scenario: dict[str, Any], *, task_root: Path) -> Path:
    """Stage exactly what ``score_measured`` reads: scenario + dv/synth/rtl.

    Copies the task fixtures and drops ``rtl_path`` in as the candidate
    ``rtl/cryo_brain_decoder.sv``. This is the same layout
    ``cryobrain.accuracy.measured_ler`` / ``score_measured`` expect, so the
    container runs the real measure unchanged.
    """
    rtl_path = Path(rtl_path).resolve()
    if not rtl_path.is_file():
        raise FileNotFoundError(f"RTL not found: {rtl_path}")
    stage = Path(tempfile.mkdtemp(prefix="cryobrain-fanout-"))
    for sub in ("dv", "synth", "rtl"):
        src = task_root / sub
        if src.is_dir():
            shutil.copytree(src, stage / sub, dirs_exist_ok=True)
    (stage / "rtl").mkdir(parents=True, exist_ok=True)
    shutil.copy2(rtl_path, stage / "rtl" / "cryo_brain_decoder.sv")
    (stage / "scenario.json").write_text(json.dumps(scenario, indent=2) + "\n", encoding="utf-8")
    design_src = task_root / "design_config.json"
    if design_src.is_file():
        shutil.copy2(design_src, stage / "design_config.json")
    return stage


# --- the real per-RTL measure unit (runs in each Modal container) ------------


def measure_one(
    rtl_path: str | Path,
    scenario: dict[str, Any],
    *,
    shots: int = 1000,
    seed: int = 1729,
    score_fn: ScoreFn | None = None,
    task_root: Path | None = None,
) -> dict[str, Any]:
    """Measure a single RTL path -> ``score_measured``-shaped dict (REAL measure).

    This is the unit fanned across containers. It stages a workdir for
    ``rtl_path`` and runs ``score_fn`` (default ``score_measured`` — the real
    verify+measure+synth boundary), then threads ``rtl_path`` into the result so
    batch callers can re-associate results with inputs. No proxy, no fake LER.

    ``score_fn`` defaults to ``None`` and is resolved to the module-level
    ``score_measured`` at call time (late binding) so the real measure stays the
    default while remaining swappable/mockable.
    """
    score_fn = score_fn or score_measured
    task_root = task_root or TASK_ROOT
    stage = _stage_measure_workdir(Path(rtl_path), scenario, task_root=task_root)
    try:
        score = dict(score_fn(stage))
        score.setdefault("rtl_path", str(Path(rtl_path).resolve()))
        return score
    finally:
        shutil.rmtree(stage, ignore_errors=True)


# --- Modal fan-out (real parallel containers) --------------------------------


def _modal_available() -> bool:
    try:
        import modal  # noqa: F401
    except ImportError:
        return False
    has_token_pair = bool(get_key("MODAL_TOKEN_ID") and get_key("MODAL_TOKEN_SECRET"))
    has_local_config = (Path.home() / ".modal.toml").is_file()
    return has_token_pair or has_local_config


def _build_modal_fanout():
    """Build the Modal app + ``.map``-able measure function. Raises if no modal."""
    import modal

    from cryobrain.rl.modal_app import build_image

    image = build_image()
    app = modal.App(APP_NAME)

    @app.function(
        image=image,
        timeout=60 * 30,
        serialized=True,
        **_modal_secret_kwargs(modal),
    )
    def measure_remote(payload: dict[str, Any]) -> dict[str, Any]:
        # Inside the container: cryobrain pkg + task fixtures are mounted, and
        # verilator/yosys/stim are installed. Run the real measure.
        import shutil as _shutil
        import tempfile as _tempfile
        from pathlib import Path as _Path

        from cryobrain.rl.modal_measure import measure_one as _measure_one

        stage = _Path(_tempfile.mkdtemp(prefix="cryobrain-modal-rtl-"))
        rtl_path = stage / "cryo_brain_decoder.sv"
        rtl_path.write_text(str(payload["rtl_source"]), encoding="utf-8")
        try:
            result = _measure_one(
                rtl_path,
                payload["scenario"],
                shots=int(payload.get("shots", 1000)),
                seed=int(payload.get("seed", 1729)),
                task_root=_Path(REMOTE_TASK_DIR),
            )
            result["rtl_path"] = payload["rtl_path"]
            return result
        finally:
            _shutil.rmtree(stage, ignore_errors=True)

    return app, measure_remote


def _modal_secret_kwargs(modal: Any) -> dict[str, Any]:
    secret_name = os.environ.get("CRYOBRAIN_MODAL_SECRET")
    if not secret_name:
        return {}
    try:
        secret = modal.Secret.from_name(secret_name, required=True)
    except TypeError:
        secret = modal.Secret.from_name(secret_name)
    return {"secrets": [secret]}


def _measure_batch_modal(
    rtl_paths: Sequence[str | Path],
    scenario: dict[str, Any],
    *,
    shots: int,
    seed: int,
) -> list[dict[str, Any]]:
    """Fan out one container per RTL via Modal ``.map`` (order preserved)."""
    app, measure_remote = _build_modal_fanout()
    payloads = _modal_payloads(rtl_paths, scenario, shots=shots, seed=seed)
    with app.run():
        return list(measure_remote.map(payloads))


def _modal_payloads(
    rtl_paths: Sequence[str | Path],
    scenario: dict[str, Any],
    *,
    shots: int,
    seed: int,
) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    for p in rtl_paths:
        rtl_path = _modal_rtl_path(p)
        payloads.append(
            {
                "rtl_path": str(rtl_path),
                "rtl_source": rtl_path.read_text(encoding="utf-8"),
                "scenario": scenario,
                "shots": shots,
                "seed": seed,
            }
        )
    return payloads


def _modal_rtl_path(path: str | Path) -> Path:
    rtl_path = Path(path).resolve()
    if not rtl_path.is_file():
        raise FileNotFoundError(f"RTL not found: {rtl_path}")
    if rtl_path.suffix.lower() != ".sv":
        raise ValueError(f"Modal measurement only accepts SystemVerilog .sv files: {rtl_path}")
    if "donotaccess" in rtl_path.parts:
        raise ValueError(f"Refusing to upload hidden task material to Modal: {rtl_path}")
    return rtl_path


def _measure_batch_local(
    rtl_paths: Sequence[str | Path],
    scenario: dict[str, Any],
    *,
    shots: int,
    seed: int,
    score_fn: ScoreFn,
    task_root: Path,
) -> list[dict[str, Any]]:
    """Sequential local fallback running the same real ``measure_one`` per RTL."""
    return [
        measure_one(p, scenario, shots=shots, seed=seed, score_fn=score_fn, task_root=task_root)
        for p in rtl_paths
    ]


def measure_batch(
    rtl_paths: Sequence[str | Path],
    scenario: dict[str, Any] | ScenarioConfig | None = None,
    *,
    shots: int = 1000,
    seed: int = 1729,
    score_fn: ScoreFn | None = None,
    task_root: Path | None = None,
    force_local: bool = False,
) -> list[dict[str, Any]]:
    """Measure N RTL paths in parallel on Modal -> list of measured dicts.

    Each result is a ``score_measured``-shaped dict (so it is ``score_fn``
    compatible) with ``rtl_path`` threaded in. Order matches ``rtl_paths``.

    Dispatch: Modal ``.map`` when ``modal`` + ``MODAL_TOKEN_ID/SECRET`` are
    available and ``force_local`` is false; otherwise the same real scorer runs
    locally (real numbers if EDA present; honest invalid/zero ``score_measured``
    result otherwise — never a faked number).
    """
    score_fn = score_fn or score_measured
    if isinstance(scenario, ScenarioConfig):
        scenario = {**scenario.to_dict(), "benchmark_vectors": 64}
    scenario = scenario or _load_scenario(task_root or TASK_ROOT)
    task_root = task_root or TASK_ROOT

    if not force_local and _modal_available():
        return _measure_batch_modal(rtl_paths, scenario, shots=shots, seed=seed)
    return _measure_batch_local(
        rtl_paths, scenario, shots=shots, seed=seed, score_fn=score_fn, task_root=task_root
    )


# --- score_fn-compatible adapter for C4/C5 -----------------------------------


def make_modal_score_fn(
    scenario: dict[str, Any] | ScenarioConfig | None = None,
    *,
    shots: int = 1000,
    seed: int = 1729,
    force_local: bool = False,
) -> ScoreFn:
    """Return a ``ScoreFn`` (workdir -> score dict) that measures via Modal.

    C4/C5 swap this into ``measured_reward(score_fn=...)`` /
    ``run_measured_training(score_fn=...)`` so the existing reward boundary runs
    its measure on a Modal container instead of locally. The workdir already
    contains the generated ``rtl/cryo_brain_decoder.sv`` (from ``generate_rtl``);
    we route that single RTL through the fan-out (a batch of one) and return its
    ``score_measured``-shaped dict unchanged — fully ``score_fn`` compatible.
    """

    modal_app = None
    measure_remote = None
    modal_scenario: dict[str, Any] | None = None
    run_context = None

    if not force_local and _modal_available():
        if isinstance(scenario, ScenarioConfig):
            modal_scenario = {**scenario.to_dict(), "benchmark_vectors": 64}
        else:
            modal_scenario = dict(scenario or _load_scenario())
        modal_app, measure_remote = _build_modal_fanout()

    def _score_fn(workdir: Path) -> dict[str, Any]:
        nonlocal run_context
        rtl_path = Path(workdir) / "rtl" / "cryo_brain_decoder.sv"
        if modal_app is not None and measure_remote is not None and modal_scenario is not None:
            if run_context is None:
                run_context = modal_app.run()
                run_context.__enter__()
                atexit.register(lambda: run_context.__exit__(None, None, None))
            payloads = _modal_payloads([rtl_path], modal_scenario, shots=shots, seed=seed)
            return list(measure_remote.map(payloads))[0]
        results = measure_batch(
            [rtl_path],
            scenario,
            shots=shots,
            seed=seed,
            force_local=force_local,
        )
        return results[0]

    return _score_fn


# --- dry-run + CLI ------------------------------------------------------------

GOLDEN_RTL = TASK_ROOT / "rtl" / "cryo_brain_decoder.sv"


def dry_run(rtl_path: Path | None = None) -> dict[str, Any]:
    """Validate fan-out wiring/shape locally with ONE variant (no Modal call).

    Runs the real ``score_measured`` on one RTL. On Linux+EDA this is a true
    end-to-end measure (real LER). On Windows (no EDA) ``score_measured`` returns
    its honest invalid/zero result — this is a wiring/shape check only and is
    marked ``"dry_run": True`` so it can never be mistaken for a production
    measured result. The live, parallel run is Modal/Linux + tokens.
    """
    rtl_path = Path(rtl_path) if rtl_path else GOLDEN_RTL
    results = measure_batch([rtl_path], _load_scenario(), force_local=True)
    result = results[0]
    eda_present = bool(shutil.which("verilator")) and bool(shutil.which("yosys"))
    return {
        "dry_run": True,
        "modal_invoked": False,
        "eda_present": eda_present,
        "variants_measured": len(results),
        "rtl_path": result.get("rtl_path", str(rtl_path)),
        "result": result,
        "note": (
            "Real end-to-end measure (verilator+yosys present)."
            if eda_present
            else "Wiring/shape check only — EDA absent (Windows); run live on Modal/Linux."
        ),
    }


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="CryoBrain Modal measurement fan-out (C3)")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Measure ONE variant locally (no Modal call) to validate wiring/shape.",
    )
    parser.add_argument(
        "--rtl",
        type=Path,
        action="append",
        help="RTL path to measure (repeatable). Defaults to the golden decoder.",
    )
    parser.add_argument("--shots", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=1729)
    parser.add_argument(
        "--local",
        action="store_true",
        help="Force the local fallback even if Modal creds are present.",
    )
    args = parser.parse_args(argv)

    if args.dry_run:
        rtl = args.rtl[0] if args.rtl else None
        print(json.dumps(dry_run(rtl), indent=2))
        return

    rtl_paths = args.rtl or [GOLDEN_RTL]
    results = measure_batch(
        rtl_paths,
        _load_scenario(),
        shots=args.shots,
        seed=args.seed,
        force_local=args.local,
    )
    print(json.dumps({"variants_measured": len(results), "results": results}, indent=2))


# --- Modal entrypoint (registered only when modal is installed) --------------


def _register_modal_entrypoint():
    """Register a ``modal run`` entrypoint when Modal is installed; else None."""
    try:
        import modal  # noqa: F401
    except Exception:
        return None

    try:
        app, measure_remote = _build_modal_fanout()
    except Exception:
        return None

    try:
        local_entrypoint = app.local_entrypoint()

        @local_entrypoint
        def modal_main(dry_run: bool = False, rtl: str = "", shots: int = 1000, seed: int = 1729) -> None:
            scenario = _load_scenario()
            if dry_run:
                # Even under `modal run --dry-run` we validate one variant end-to-end
                # via a single remote container (real LER) without a full batch.
                target = rtl or str(GOLDEN_RTL)
                target_path = _modal_rtl_path(target)
                payload = {
                    "rtl_path": str(target_path),
                    "rtl_source": target_path.read_text(encoding="utf-8"),
                    "scenario": scenario,
                    "shots": shots,
                    "seed": seed,
                }
                result = measure_remote.remote(payload)
                print(json.dumps({"dry_run": True, "modal_invoked": True, "result": result}, indent=2))
                return
            targets = [rtl] if rtl else [str(GOLDEN_RTL)]
            results = measure_batch(targets, scenario, shots=shots, seed=seed)
            print(json.dumps({"variants_measured": len(results), "results": results}, indent=2))
    except Exception:
        return app

    return app


# Module-level app: importable on Windows (None when modal is absent).
app = _register_modal_entrypoint()


if __name__ == "__main__":
    main()
