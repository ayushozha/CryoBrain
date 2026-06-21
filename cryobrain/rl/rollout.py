"""Rollout generation for GRPO (SPEC-v5 C4 / MP3).

A *rollout group* is the unit GRPO consumes: N proposed ``DesignConfig``s, each
scored through the MEASURED reward boundary. The reward for every rollout comes
from :func:`cryobrain.rl.proposal_loop.measured_reward` (Grok ``score_measured``:
Stim -> Verilator real LER + Yosys synth + L1/L4/L5 gates, reward 0.0 on
verification failure). We never compute a reward here.

Two things are swappable so this same rollout runs locally OR fanned across GPUs:

  * ``policy_sample`` — how a DesignConfig is proposed. Default is a GRPO
    :class:`~cryobrain.rl.grpo.DesignPolicy` sample; a Fireworks-backed proposer
    (C2) can be substituted, or any callable ``(rng) -> DesignConfig``.
  * ``score_fn`` — the measured score function threaded straight into
    ``measured_reward``. Default is Grok's ``score_measured`` (one local
    Verilator/Yosys pass). **This is the exact swap point for C3's Modal
    fan-out:** C3 supplies a ``score_fn(workdir) -> score_dict`` that ships the
    workdir to a Modal worker and returns the measured score — the reward stays
    measured, only *where* it is measured changes.

Each valid (verification-passed) rollout is recorded to the C1 memory store by
``run_proposal_step`` and the group exposes the resulting ``rtl_hash`` per
rollout so a GRPO checkpoint can reference those measured memory rows.

Windows note: without Verilator/Yosys, ``score_measured`` returns invalid /
zero-reward variants (the real measure stack is Linux/WSL). The unit test
monkeypatches ``score_fn`` to exercise the wiring without EDA.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import numpy as np

from cryobrain.grader.score import score_measured
from cryobrain.memory.store import MemoryStore
from cryobrain.rl.grpo import DesignPolicy
from cryobrain.rl.proposal_loop import TASK_ROOT, ScoreFn, StepResult, run_proposal_step
from cryobrain.types import DesignConfig

# A policy sampler: rng -> next DesignConfig.
PolicySampler = Callable[[np.random.Generator], DesignConfig]


@dataclass(frozen=True)
class RolloutGroup:
    """A group of measured rollouts (the GRPO batch).

    Wraps the ``StepResult`` list from :func:`run_proposal_step`; every accessor
    reads MEASURED fields only (reward/suppression/rtl_hash from the measured
    boundary). Provides the numpy-friendly views GRPO needs.
    """

    step: int
    results: list[StepResult]

    def rewards(self) -> list[float]:
        """Measured rewards (verification failure => 0.0, from score_measured)."""
        return [float(r.reward) for r in self.results]

    def suppressions(self) -> list[float]:
        return [float(r.suppression) for r in self.results]

    def designs(self) -> list[DesignConfig]:
        return [r.design for r in self.results]

    def rtl_hashes(self) -> list[str]:
        """sha256 memory keys per rollout (links a checkpoint to memory rows)."""
        return [r.rtl_hash for r in self.results]

    def valid_mask(self) -> list[bool]:
        return [bool(r.valid) for r in self.results]

    def recorded_hashes(self) -> list[str]:
        """rtl_hashes of the rollouts actually written to the memory store."""
        return [r.rtl_hash for r in self.results if r.recorded and r.rtl_hash]

    def reward_array(self) -> np.ndarray:
        return np.asarray(self.rewards(), dtype=np.float64)

    def __len__(self) -> int:
        return len(self.results)


def default_policy_sampler(policy: DesignPolicy) -> PolicySampler:
    """A sampler that draws DesignConfigs from a GRPO :class:`DesignPolicy`."""

    def _sample(rng: np.random.Generator) -> DesignConfig:
        return policy.sample(rng)

    return _sample


def generate_rollout_group(
    *,
    step: int,
    scenario: dict[str, Any],
    group_size: int,
    policy_sample: PolicySampler,
    store: MemoryStore | None = None,
    score_fn: ScoreFn = score_measured,
    rng: np.random.Generator | None = None,
    backend: str = "verilator+stim+yosys",
    task_root: Path = TASK_ROOT,
) -> RolloutGroup:
    """Propose ``group_size`` designs and score each via the MEASURED boundary.

    For each rollout we call :func:`run_proposal_step`, which generates the real
    RTL, drives ``measured_reward`` with ``score_fn`` (default ``score_measured``;
    C3 swaps in a Modal-fanned scorer), and records valid variants to memory.
    The returned group carries the measured reward + ``rtl_hash`` per rollout.

    A whole-group failure (e.g. no EDA on Windows) yields all-zero rewards — a
    degenerate group GRPO handles by emitting zero advantages (no spurious step).
    """
    rng = rng if rng is not None else np.random.default_rng()
    store = store if store is not None else MemoryStore()
    results: list[StepResult] = []
    for i in range(group_size):
        design = policy_sample(rng)
        result = run_proposal_step(
            step=step * group_size + i,
            design=design,
            scenario=scenario,
            store=store,
            score_fn=score_fn,
            backend=backend,
            task_root=task_root,
        )
        results.append(result)
    return RolloutGroup(step=step, results=results)
