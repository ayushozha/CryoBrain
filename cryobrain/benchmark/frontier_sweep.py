"""Sweep L2-safe decoder variants into the memory store (SPEC-v6.1 C3)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from cryobrain.design.config import l2_safe_variants
from cryobrain.grader.score import score_measured
from cryobrain.memory.store import MemoryStore
from cryobrain.rl.proposal_loop import TASK_ROOT, run_proposal_step

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STORE = ROOT / "artifacts" / "measured_variants.jsonl"


def _load_scenario() -> dict:
    return json.loads((TASK_ROOT / "scenario.json").read_text(encoding="utf-8"))


def sweep(*, store_path: Path = DEFAULT_STORE) -> dict:
    scenario = _load_scenario()
    store = MemoryStore(store_path)
    recorded = 0
    for step, design in enumerate(l2_safe_variants()):
        result = run_proposal_step(
            step=step,
            design=design,
            scenario=scenario,
            store=store,
            score_fn=score_measured,
        )
        if result.recorded:
            recorded += 1
    return {"variants": len(l2_safe_variants()), "recorded": recorded, "store": str(store_path)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Record L2-safe measured variants for Pareto (C3).")
    parser.add_argument("--store", type=Path, default=DEFAULT_STORE)
    args = parser.parse_args(argv)
    summary = sweep(store_path=args.store)
    print(json.dumps(summary, indent=2))
    if summary["recorded"] < 2:
        raise SystemExit(f"C3 blocked: only {summary['recorded']} L2-valid variants recorded")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())