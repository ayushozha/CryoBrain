"""RSI distance curriculum chart (SPEC F7, CP6)."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt


def load_climb_chart(path: Path) -> dict[str, object]:
    if not path.is_file():
        raise FileNotFoundError(f"climb chart not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def plot_distance_curriculum(
    climb_chart: dict[str, object],
    *,
    output: Path,
) -> Path:
    """Plot reward vs step with d=3→5→7 stage bands and transition markers."""
    history = climb_chart.get("history", [])
    if not isinstance(history, list) or not history:
        raise ValueError("climb_chart.history is empty")

    steps = [int(h["step"]) for h in history]
    rewards = [float(h["reward"]) for h in history]
    distances = [int(h.get("distance", 3)) for h in history]
    transitions = climb_chart.get("curriculum_transitions", [])
    if not isinstance(transitions, list):
        transitions = []

    output.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(9, 5))

    # Stage background bands
    stage_colors = {3: "#e8f4fc", 5: "#fff4e6", 7: "#f3e8ff"}
    if steps:
        seg_start = steps[0]
        current_d = distances[0]
        for idx, step in enumerate(steps[1:], start=1):
            if distances[idx] != current_d:
                ax.axvspan(seg_start, step, color=stage_colors.get(current_d, "#f5f5f5"), alpha=0.55)
                seg_start = step
                current_d = distances[idx]
        ax.axvspan(seg_start, steps[-1], color=stage_colors.get(current_d, "#f5f5f5"), alpha=0.55)

    ax.plot(steps, rewards, color="#1f77b4", linewidth=2, label="Policy reward")
    for tr in transitions:
        if not isinstance(tr, dict):
            continue
        x = int(tr.get("step", 0))
        ax.axvline(x, color="#d62728", linestyle="--", alpha=0.7)
        to_d = tr.get("to_distance", "?")
        ax.annotate(
            f"d{tr.get('from_distance', '?')}→d{to_d}",
            xy=(x, float(tr.get("reward_at_transition", rewards[min(x, len(rewards) - 1)]))),
            xytext=(8, 12),
            textcoords="offset points",
            fontsize=9,
            color="#d62728",
        )

    ax.set_xlabel("Training step")
    ax.set_ylabel("Reward (validity gate + continuous LER/hardware)")
    ax.set_title("CryoBrain RSI Distance Curriculum (d=3→5→7)")
    ax.set_ylim(0.0, 1.0)
    ax.grid(True, alpha=0.25)

    # Legend for distance bands
    from matplotlib.patches import Patch

    band_patches = [
        Patch(facecolor=stage_colors[d], alpha=0.55, label=f"d={d} stage")
        for d in sorted(stage_colors)
    ]
    ax.legend(handles=[*band_patches, ax.lines[0]], loc="lower right")
    fig.tight_layout()
    fig.savefig(output, dpi=150)
    plt.close(fig)
    return output


def write_curriculum_meta(climb_chart: dict[str, object], *, output: Path) -> Path:
    """Serialize curriculum summary for demo slides."""
    history = climb_chart.get("history", [])
    by_distance: dict[int, list[float]] = {}
    if isinstance(history, list):
        for row in history:
            if not isinstance(row, dict):
                continue
            d = int(row.get("distance", 3))
            by_distance.setdefault(d, []).append(float(row.get("reward", 0.0)))

    summary = {
        "transitions": climb_chart.get("curriculum_transitions", []),
        "mean_reward_by_distance": {
            str(d): round(sum(vals) / len(vals), 4) for d, vals in sorted(by_distance.items())
        },
        "final_distance": climb_chart.get("final_distance"),
        "summary": climb_chart.get("summary", {}),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return output


def main() -> None:
    chart_path = Path("artifacts/climb_chart.json")
    climb = load_climb_chart(chart_path)
    png = plot_distance_curriculum(climb, output=Path("artifacts/distance_curriculum.png"))
    meta = write_curriculum_meta(climb, output=Path("artifacts/distance_curriculum.json"))
    print(f"wrote {png} and {meta}")


if __name__ == "__main__":
    main()