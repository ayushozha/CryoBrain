"""Measured accuracy <-> hardware Pareto frontier (SPEC-v5 C10, §4).

Reads MEASURED variants from the C1 memory store (``query_pareto_candidates``)
and computes the non-dominated frontier over (measured LER, area_um2). Every
point carries the measured ``candidate_ler`` (the accuracy axis) and an
``rtl_path`` — there is NO formula/proxy LER path here, and the old proxy
``cryobrain/artifacts/pareto.py`` (formula cost model + ``ler_suppression``) is
deliberately NOT reused.

Frontier definition (both axes minimized):
  * accuracy axis = measured LER (lower is better / more accurate),
  * hardware axis = ``area_um2`` (lower is cheaper).
A point is on the frontier iff no other point is at least as good on both axes
and strictly better on one (standard Pareto dominance). ``latency_cycles`` is
carried for downstream budget reasoning but is not a frontier axis (keeps the
2-D accuracy<->hardware plot honest and simple).

Emitted artifact schema (frozen, per INTERFACE_CONTRACTS):
  ``points[].{label, ler, area_um2, latency_cycles, rtl_path}``
plus ``on_frontier`` (bool) and ``rtl_hash`` (provenance) — the five required
keys are always present and always sourced from a measured record.

CLI::

    python -m cryobrain.benchmark.pareto --emit artifacts/measured_pareto.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from cryobrain.memory.store import DEFAULT_STORE, query_pareto_candidates

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PARETO = ROOT / "artifacts" / "measured_pareto.json"

# Single source of truth for the accuracy axis label — imported by plots.py and
# asserted by tests. MUST name the measured backend; never "formula"/"proxy".
ACCURACY_AXIS_LABEL = "measured LER (Verilator)"
HARDWARE_AXIS_LABEL = "Yosys area (µm²) — lower is cheaper"

# The five measured fields every Pareto point must carry (frozen contract).
REQUIRED_POINT_FIELDS = ("label", "ler", "area_um2", "latency_cycles", "rtl_path")


def _is_dominated(candidate: dict[str, Any], others: list[dict[str, Any]]) -> bool:
    """True if some other point dominates ``candidate`` (min ler, min area).

    Dominated == another point is <= on both ler and area and < on at least one.
    Ties on both axes do not dominate (both stay on the frontier).
    """
    cl, ca = candidate["ler"], candidate["area_um2"]
    for other in others:
        if other is candidate:
            continue
        ol, oa = other["ler"], other["area_um2"]
        if ol <= cl and oa <= ca and (ol < cl or oa < ca):
            return True
    return False


def _label_for(candidate: dict[str, Any], index: int) -> str:
    """A short, stable label for a point: rtl filename stem + short hash."""
    stem = Path(str(candidate["rtl_path"])).stem or f"variant_{index}"
    short = str(candidate.get("rtl_hash", ""))[:8]
    return f"{stem}@{short}" if short else stem


def build_pareto(
    records: list[dict[str, Any]] | None = None,
    *,
    store_path: Path | str = DEFAULT_STORE,
) -> dict[str, Any]:
    """Build the measured Pareto artifact.

    Args:
        records: explicit list of measured candidates (each a mapping carrying
            ``ler``, ``area_um2``, ``latency_cycles``, ``rtl_path`` and
            optionally ``rtl_hash``) — used by tests with golden fixtures. When
            ``None``, candidates are read from the C1 memory store via
            ``query_pareto_candidates`` (verified, measured records only).
        store_path: memory store path used when ``records`` is None.

    Returns:
        ``{"accuracy_axis", "hardware_axis", "frontier_axes", "count",
           "frontier_count", "points": [...]}`` where each point has the five
        required measured fields plus ``on_frontier`` and ``rtl_hash``.

    Every point's ``ler`` is the MEASURED ``candidate_ler`` (the store sources it
    from ``measure_candidate_ler`` only). No proxy/formula or npu_cost-only point
    can enter: a candidate without an ``rtl_path`` or measured ``ler`` is invalid
    and raises rather than being silently included.
    """
    raw = list(query_pareto_candidates(path=store_path)) if records is None else list(records)

    cands: list[dict[str, Any]] = []
    for i, r in enumerate(raw):
        # Guard: a real measured point MUST carry an rtl_path and a measured ler.
        # This is the structural defense against proxy / npu_cost-only points.
        rtl_path = r.get("rtl_path")
        if not rtl_path or r.get("ler") is None or r.get("area_um2") is None:
            raise ValueError(
                f"pareto point {i} missing measured rtl_path/ler/area_um2 "
                f"(refusing proxy/npu_cost-only point): {r!r}"
            )
        cands.append(
            {
                "label": _label_for(r, i),
                "ler": float(r["ler"]),
                "area_um2": float(r["area_um2"]),
                "latency_cycles": int(r["latency_cycles"]),
                "rtl_path": str(rtl_path),
                "rtl_hash": str(r.get("rtl_hash", "")),
            }
        )

    # Stable order: ascending area, then ascending ler — readable frontier line.
    cands.sort(key=lambda c: (c["area_um2"], c["ler"]))
    for c in cands:
        c["on_frontier"] = not _is_dominated(c, cands)

    frontier_count = sum(1 for c in cands if c["on_frontier"])
    return {
        "accuracy_axis": ACCURACY_AXIS_LABEL,
        "hardware_axis": HARDWARE_AXIS_LABEL,
        "frontier_axes": ["ler", "area_um2"],
        "count": len(cands),
        "frontier_count": frontier_count,
        "points": cands,
    }


def emit(out_path: Path | str = DEFAULT_PARETO, *, store_path: Path | str = DEFAULT_STORE) -> Path:
    """Build from the memory store and write the artifact JSON. Returns the path.

    If the store is empty (no measured runs yet — e.g. on Windows without WSL
    measurement), this writes a valid artifact with ``points: []``.
    """
    artifact = build_pareto(store_path=store_path)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Emit the measured Pareto artifact (measured LER axis only).")
    parser.add_argument("--emit", type=Path, default=DEFAULT_PARETO, help="output JSON path")
    parser.add_argument("--store", type=Path, default=DEFAULT_STORE, help="memory store JSONL path")
    args = parser.parse_args(argv)

    out = emit(args.emit, store_path=args.store)
    artifact = json.loads(out.read_text(encoding="utf-8"))
    print(
        f"wrote {out} | points={artifact['count']} on_frontier={artifact['frontier_count']} "
        f"| accuracy_axis={artifact['accuracy_axis']!r}"
    )
    if artifact["count"] == 0:
        print("note: memory store empty — emitted valid points:[] (run WSL measured climb to populate)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
