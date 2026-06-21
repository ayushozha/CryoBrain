#!/usr/bin/env python3
"""Hidden measured grader for the async_fifo GEN target (SPEC-v5 GEN / C9).

Consistent with the ``stream_arb_fifo_cocotb_dv`` donotaccess convention: the
answer key (the golden reference + the throughput DV) lives here and is hidden
from the agent. Unlike the DV task (which grades an agent-WRITTEN testbench),
this GEN target grades an agent-GENERATED FIFO ``.sv`` on a MEASURED metric:
sustained throughput under a fixed traffic pattern, gated on bit-exact
correctness vs the golden reference model.

``grade(workdir)`` -> ``{reward, valid, throughput, suppression, ...}`` where:
  * ``throughput`` = items drained / cycles, COUNTED from a real cocotb+Verilator
    run of ``workdir/rtl/stream_arb_fifo.sv`` against the hidden traffic. Not a
    formula.
  * ``valid`` (correctness gate) = the DUT matched the cycle-accurate golden
    reference bit-for-bit. Gate fail => reward 0 (mirrors the decoder reward gate).
  * ``reward`` = throughput when valid, else 0.

Linux/WSL only (Verilator). Importing this module never runs EDA.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

TRAFFIC_CYCLES = 64
TRAFFIC_SEED = 1729
BASELINE_DEPTH = 1


def grade(workdir: Path, *, hidden_root: Path | None = None) -> dict[str, object]:
    """Measured grade for the generated FIFO in ``workdir``.

    Reads the workdir's ``fifo_config.json`` for the design depth (so the DV
    reference model uses the right capacity), runs the hidden throughput DV, and
    returns the measured throughput gated on correctness.
    """
    from cryobrain.accuracy.fifo_throughput import measure_fifo

    workdir = Path(workdir)
    rtl_path = workdir / "rtl" / "stream_arb_fifo.sv"
    cfg_path = workdir / "fifo_config.json"
    depth, width = BASELINE_DEPTH, 8
    if cfg_path.is_file():
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        depth = int(cfg.get("depth", BASELINE_DEPTH))
        width = int(cfg.get("width", 8))

    result = measure_fifo(
        rtl_path,
        depth=depth,
        width=width,
        cycles=TRAFFIC_CYCLES,
        seed=TRAFFIC_SEED,
        task_root=ROOT,
    )
    score = result.to_score()
    return {
        "reward": score["reward"],
        "valid": score["valid"],
        "throughput": score["throughput"],
        "baseline_throughput": score["baseline_throughput"],
        "suppression": score["suppression"],
        "hard_caps": [] if score["valid"] else ["fifo_correctness_failed"],
        "source": "measured-fifo-sim",
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--workdir", default=str(ROOT))
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    result = grade(Path(args.workdir).resolve())
    print(json.dumps(result, indent=2 if args.pretty else None, sort_keys=True))
    return 0 if result["reward"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
