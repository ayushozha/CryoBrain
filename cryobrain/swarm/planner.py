"""Planner agent — chooses the next experiment direction (SPEC-v6 P-train2).

The Planner reads the memory store and recent climb history, picks which
DesignConfig knob to mutate next (bitwidth, parallelism, depth, etc.),
and returns a plan dict consumed by the Architect/proposer. Selection is
deterministic given ``seed`` + ``step`` + history.

Planner reward (trainer): measured suppression delta achieved by experiments
it directed — computed in :mod:`cryobrain.rl.planner_trainer`, not here.
"""

from __future__ import annotations

import random
from dataclasses import replace
from typing import Any

from cryobrain.design.config import preset_variants
from cryobrain.memory.store import MemoryStore
from cryobrain.swarm.event_bus import Agent, EventBus
from cryobrain.types import DesignConfig

KNOBS: tuple[str, ...] = (
    "bitwidth",
    "num_layers",
    "parallelism",
    "pipeline_depth",
    "window_length",
)

KNOB_CHOICES: dict[str, list[int]] = {
    "bitwidth": [2, 4, 8],
    "num_layers": [1, 2, 4],
    "parallelism": [1, 2, 4],
    "pipeline_depth": [2, 4, 8],
    "window_length": [4, 8, 16],
}


class Planner:
    """Tier-1 trained agent: search-direction policy (deterministic with seed)."""

    AGENT_NAME = Agent.PLANNER

    def __init__(
        self,
        *,
        seed: int = 0,
        bus: EventBus | None = None,
        explore_rate: float = 0.25,
    ) -> None:
        self.seed = seed
        self.bus = bus if bus is not None else EventBus(log_path=None)
        self.explore_rate = explore_rate

    def plan(
        self,
        step: int,
        *,
        store: MemoryStore | None = None,
        climb_history: list[dict[str, Any]] | None = None,
        plans_log: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Choose the next search direction and emit a bus event.

        Returns a plan dict::

            {
                "step": int,
                "design_id": str,
                "knob": str,
                "base_design": dict,
                "direction": "explore" | "exploit",
                "seed": int,
            }
        """
        climb_history = climb_history or []
        plans_log = plans_log or []
        rng = random.Random(self.seed + step * 1009)

        base_design = self._base_design(step, store)
        knob, direction = self._choose_knob(step, plans_log, rng)
        design_id = f"d{step:03d}"

        plan = {
            "step": step,
            "design_id": design_id,
            "knob": knob,
            "base_design": base_design.to_dict(),
            "direction": direction,
            "seed": self.seed,
            "climb_steps": len(climb_history),
        }

        self.bus.emit(
            self.AGENT_NAME,
            "plan",
            design_id,
            {"knob": knob, "direction": direction, "base_design": plan["base_design"]},
        )
        return plan

    def apply_plan(self, plan: dict[str, Any], rng: random.Random | None = None) -> DesignConfig:
        """Architect hook: mutate exactly the knob the Planner chose."""
        rng = rng or random.Random(plan["seed"] + plan["step"] * 1009 + 17)
        base = DesignConfig.from_dict(plan["base_design"])
        knob = str(plan["knob"])
        if knob not in KNOB_CHOICES:
            return base

        current = getattr(base, knob)
        alts = [v for v in KNOB_CHOICES[knob] if v != current]
        if not alts:
            return base
        new_val = rng.choice(alts)
        return replace(base, **{knob: new_val})

    def _base_design(self, step: int, store: MemoryStore | None) -> DesignConfig:
        """Best measured exemplar from memory, else preset cold-start."""
        if store is not None:
            best = store.best_holdout()
            if best is not None:
                return DesignConfig.from_dict(best.design)

            pareto = store.query_pareto_candidates()
            if pareto:
                digest = pareto[0]["rtl_hash"]
                rec = store._records.get(digest)  # noqa: SLF001 — intra-package read
                if rec is not None:
                    return DesignConfig.from_dict(rec.design)

        presets = preset_variants()
        return presets[step % len(presets)]

    def _choose_knob(
        self,
        step: int,
        plans_log: list[dict[str, Any]],
        rng: random.Random,
    ) -> tuple[str, str]:
        """Pick knob deterministically; bias toward knobs with positive measured delta."""
        if not plans_log:
            return KNOBS[step % len(KNOBS)], "explore"

        knob_scores: dict[str, float] = {k: 0.0 for k in KNOBS}
        knob_counts: dict[str, int] = {k: 0 for k in KNOBS}
        for entry in plans_log:
            knob = entry.get("knob")
            if knob not in knob_scores:
                continue
            delta = float(entry.get("planner_reward", 0.0))
            knob_scores[knob] += delta
            knob_counts[knob] += 1

        ranked = sorted(
            KNOBS,
            key=lambda k: (knob_scores[k] / max(knob_counts[k], 1), -knob_counts[k]),
            reverse=True,
        )

        if rng.random() < self.explore_rate:
            return KNOBS[step % len(KNOBS)], "explore"
        return ranked[0], "exploit"