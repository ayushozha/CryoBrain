"""Measured benchmark plots (SPEC-v5 C10, §4).

Matplotlib plots whose accuracy / y-axis literally reads
``measured LER (Verilator)`` (``pareto.ACCURACY_AXIS_LABEL``) — never a
formula/proxy LER. Two plots:

  * Pareto scatter + frontier line over (measured LER, Yosys area_um2).
  * Optional learning-climb plot from ``artifacts/measured_climb.json`` if it
    exists (``history[].{step, candidate_ler, suppression, rtl_hash}``).

Matplotlib is a project dependency (``pyproject.toml``). We force the headless
``Agg`` backend so PNGs render in CI / WSL / Windows without a display. No new
dependency, no proxy data.

CLI::

    python -m cryobrain.benchmark.plots --out-dir artifacts
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")  # headless: render to file, never to a display.
import matplotlib.pyplot as plt  # noqa: E402  (must follow backend selection)

from cryobrain.benchmark.pareto import (  # noqa: E402
    ACCURACY_AXIS_LABEL,
    DEFAULT_PARETO,
    HARDWARE_AXIS_LABEL,
    build_pareto,
)

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = ROOT / "artifacts"
DEFAULT_CLIMB = ARTIFACTS / "measured_climb.json"


def _load_pareto(pareto_path: Path | str) -> dict[str, Any]:
    """Read a pareto artifact if present, else build one from the memory store."""
    p = Path(pareto_path)
    if p.is_file():
        return json.loads(p.read_text(encoding="utf-8"))
    return build_pareto()


def plot_pareto_png(
    artifact: dict[str, Any] | None = None,
    *,
    pareto_path: Path | str = DEFAULT_PARETO,
    out_path: Path | str = ARTIFACTS / "measured_pareto.png",
) -> Path:
    """Scatter of (area_um2, measured LER) with the Pareto frontier line.

    Y-axis is the MEASURED LER (``ACCURACY_AXIS_LABEL``). Lower-left is better
    (more accurate AND cheaper). Empty-but-valid when there are no measured
    points yet (the axes/labels still render so the demo never shows a proxy).
    """
    art = artifact if artifact is not None else _load_pareto(pareto_path)
    points = art.get("points", [])
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(8.5, 5.5))
    dominated = [p for p in points if not p.get("on_frontier")]
    frontier = sorted((p for p in points if p.get("on_frontier")), key=lambda p: p["area_um2"])

    if dominated:
        ax.scatter(
            [p["area_um2"] for p in dominated],
            [p["ler"] for p in dominated],
            marker="o", s=55, color="#7f7f7f", alpha=0.7, zorder=3, label="measured variant",
        )
    if frontier:
        ax.scatter(
            [p["area_um2"] for p in frontier],
            [p["ler"] for p in frontier],
            marker="o", s=80, color="#2ca02c", zorder=4, label="Pareto frontier (measured)",
        )
        if len(frontier) >= 2:
            ax.plot(
                [p["area_um2"] for p in frontier],
                [p["ler"] for p in frontier],
                color="#2ca02c", linewidth=1.6, alpha=0.85, zorder=3,
            )

    ax.set_xlabel(HARDWARE_AXIS_LABEL)
    ax.set_ylabel(ACCURACY_AXIS_LABEL + " — lower is more accurate")  # MEASURED axis only
    ax.set_title("CryoBrain measured accuracy ↔ hardware Pareto")
    ax.grid(True, alpha=0.25)
    if points:
        ax.legend(fontsize=8, loc="upper right")
    else:
        ax.text(0.5, 0.5, "no measured variants yet\n(run WSL measured climb)",
                ha="center", va="center", transform=ax.transAxes, color="#7f7f7f")

    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def plot_climb_png(
    *,
    climb_path: Path | str = DEFAULT_CLIMB,
    out_path: Path | str = ARTIFACTS / "measured_climb.png",
) -> Path | None:
    """Optional learning-climb plot from measured_climb.json (if it exists).

    Plots MEASURED ``candidate_ler`` and ``suppression`` per accepted step. The
    LER curve is labeled with ``ACCURACY_AXIS_LABEL`` so it can never be read as
    a proxy. Returns None (no file written) when the climb artifact is absent.
    """
    p = Path(climb_path)
    if not p.is_file():
        return None
    history = json.loads(p.read_text(encoding="utf-8")).get("history", [])
    if not history:
        return None

    steps = [row["step"] for row in history]
    lers = [row["candidate_ler"] for row in history]
    supp = [row.get("suppression") for row in history]

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig, ax1 = plt.subplots(figsize=(8.5, 5.0))
    ax1.plot(steps, lers, marker="o", color="#1f77b4", label=ACCURACY_AXIS_LABEL)
    ax1.set_xlabel("accepted step")
    ax1.set_ylabel(ACCURACY_AXIS_LABEL, color="#1f77b4")  # MEASURED axis only
    ax1.tick_params(axis="y", labelcolor="#1f77b4")
    ax1.grid(True, alpha=0.25)

    if any(s is not None for s in supp):
        ax2 = ax1.twinx()
        ax2.plot(steps, supp, marker="s", color="#2ca02c", label="measured suppression vs MWPM")
        ax2.set_ylabel("measured suppression vs MWPM (Stim)", color="#2ca02c")
        ax2.tick_params(axis="y", labelcolor="#2ca02c")

    ax1.set_title("CryoBrain measured learning climb")
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render measured benchmark plots (measured LER axis only).")
    parser.add_argument("--out-dir", type=Path, default=ARTIFACTS, help="directory for PNG output")
    parser.add_argument("--pareto", type=Path, default=DEFAULT_PARETO, help="pareto artifact JSON (built from memory if absent)")
    parser.add_argument("--climb", type=Path, default=DEFAULT_CLIMB, help="optional measured_climb.json")
    args = parser.parse_args(argv)

    pareto_png = plot_pareto_png(pareto_path=args.pareto, out_path=args.out_dir / "measured_pareto.png")
    print(f"wrote {pareto_png}")
    climb_png = plot_climb_png(climb_path=args.climb, out_path=args.out_dir / "measured_climb.png")
    print(f"wrote {climb_png}" if climb_png else "no measured_climb.json — skipped climb plot")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
