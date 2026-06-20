"""Pareto frontier explorer (SPEC F9)."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt


def plot_pareto(designs: list[dict[str, float]], *, output: Path) -> Path:
    """Plot LER suppression vs hardware area for discovered designs."""
    output.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8, 5))
    for design in designs:
        ax.scatter(
            design.get("area_mm2", 0.0),
            design.get("ler_suppression", 0.0),
            label=design.get("name", "design"),
        )
    if designs:
        mwpm = next((d for d in designs if d.get("name") == "mwpm"), None)
        if mwpm:
            ax.axhline(mwpm.get("ler_suppression", 0.0), linestyle="--", color="gray", label="MWPM")
    ax.set_xlabel("Area (mm²)")
    ax.set_ylabel("LER suppression vs MWPM")
    ax.set_title("CryoBrain Pareto Frontier")
    ax.legend()
    fig.tight_layout()
    fig.savefig(output, dpi=150)
    plt.close(fig)
    return output


def main() -> None:
    sample = [
        {"name": "mwpm", "area_mm2": 0.06, "ler_suppression": 0.0},
        {"name": "starter", "area_mm2": 0.04, "ler_suppression": 0.25},
        {"name": "agent-v3", "area_mm2": 0.05, "ler_suppression": 0.42},
    ]
    out = plot_pareto(sample, output=Path("artifacts/pareto.png"))
    meta = Path("artifacts/pareto.json")
    meta.write_text(json.dumps(sample, indent=2), encoding="utf-8")
    print(f"wrote {out} and {meta}")


if __name__ == "__main__":
    main()