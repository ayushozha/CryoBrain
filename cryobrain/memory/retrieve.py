"""Retrieve M most-relevant verified designs for a task (SPEC2 F7)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from cryobrain.memory.buffer import VerifiedDesignBuffer, VerifiedDesignRecord

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BUFFER = ROOT / "artifacts" / "verified_memory.json"


def _task_distance(task: dict[str, Any]) -> int:
    if "distance" in task:
        return int(task["distance"])
    scenario = task.get("scenario", {})
    if isinstance(scenario, dict) and "distance" in scenario:
        return int(scenario["distance"])
    return 3


def _task_noise(task: dict[str, Any]) -> float:
    if "noise_rate" in task:
        return float(task["noise_rate"])
    scenario = task.get("scenario", {})
    if isinstance(scenario, dict) and "noise_rate" in scenario:
        return float(scenario["noise_rate"])
    return 0.001


def _relevance(record: VerifiedDesignRecord, distance: int, noise_rate: float) -> float:
    dist_penalty = abs(record.distance - distance) * 0.05
    noise_penalty = abs(record.noise_rate - noise_rate) * 2.0
    return record.reward - dist_penalty - noise_penalty


def retrieve(
    task: dict[str, Any],
    *,
    buffer_path: Path | str = DEFAULT_BUFFER,
    k: int = 3,
) -> list[dict[str, Any]]:
    """Return exemplar dicts for prompt injection / candidate biasing."""
    buffer = VerifiedDesignBuffer(buffer_path)
    distance = _task_distance(task)
    noise = _task_noise(task)
    ranked = sorted(
        buffer.top(buffer.capacity),
        key=lambda r: _relevance(r, distance, noise),
        reverse=True,
    )
    exemplars: list[dict[str, Any]] = []
    for record in ranked[:k]:
        exemplars.append(
            {
                "design": record.design,
                "reward": round(record.reward, 6),
                "distance": record.distance,
                "noise_rate": record.noise_rate,
                "metrics": record.metrics,
                "source": record.source,
                "tags": record.tags,
            }
        )
    return exemplars