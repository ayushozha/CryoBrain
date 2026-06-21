"""GRPO algorithm on the MEASURED reward (SPEC-v5 C4 / MP3 — the climb).

GRPO (Group Relative Policy Optimization) needs no value/critic network: the
baseline is the *group mean* of the rollout rewards. For CryoBrain the policy is
a categorical distribution over a small, discrete design space (each ``DesignConfig``
knob is a categorical), so the "weight update" is a softmax-logit policy-gradient
step on those per-knob logits. This is intentionally framework-light: numpy only
(an existing project dependency), no torch — the point of MP3 is *the climb of a
MEASURED quantity*, not a heavyweight model.

The single hard invariant (SPEC-v5 keystone): **every reward in the advantage
computation comes from the measured boundary** (``measured_reward`` in
:mod:`cryobrain.rl.proposal_loop`, which runs Stim->Verilator->Yosys via
``score_measured`` and zeroes the reward on verification failure). There is NO
formula reward here — ``grpo.py`` never computes a reward, it only consumes the
measured rewards a :class:`~cryobrain.rl.rollout.RolloutGroup` carries.

What this module owns:
  * :func:`compute_advantages` — group-relative (mean-subtracted, std-normalized)
    advantages from MEASURED rewards.
  * :class:`DesignPolicy` — a categorical policy over the DesignConfig knob space
    with a softmax-logit policy-gradient update (the "weight update").
  * :func:`grpo_step` — one GRPO step: take a rollout group's measured rewards,
    compute advantages, update the policy logits, write a checkpoint referencing
    the group's measured memory rows (``rtl_hash``).

Modal (real GPU) wiring lives in :mod:`cryobrain.rl.modal_train`; the algorithm
here is backend-agnostic so the same step runs locally (CPU numpy) or remote.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np

from cryobrain.types import DesignConfig

if TYPE_CHECKING:  # avoid a runtime import cycle (rollout imports nothing from here)
    from cryobrain.rl.rollout import RolloutGroup

ROOT = Path(__file__).resolve().parents[2]
CHECKPOINT_DIR = ROOT / "artifacts" / "checkpoints"

# The discrete design space the policy is categorical over. Mirrors the knob
# choices used by cryobrain.design.config (G9) so generated DesignConfigs stay
# inside generate_rtl's supported envelope.
KNOB_CHOICES: dict[str, tuple[int, ...]] = {
    "bitwidth": (2, 4, 8),
    "num_layers": (1, 2, 3, 4),
    "parallelism": (1, 2, 4),
    "pipeline_depth": (2, 4, 8),
    "window_length": (4, 8, 16),
}
KNOBS: tuple[str, ...] = tuple(KNOB_CHOICES)


def compute_advantages(rewards: np.ndarray | list[float], *, eps: float = 1e-8) -> np.ndarray:
    """Group-relative advantages from MEASURED rewards (the GRPO baseline).

    GRPO uses the in-group statistics as the baseline (no critic):

        A_i = (r_i - mean(r)) / (std(r) + eps)

    ``rewards`` MUST be the measured rewards a rollout group carries (each from
    ``measured_reward`` -> ``score_measured``). A verification-failed rollout
    contributes reward 0.0, which correctly pulls its advantage below the group
    mean — the policy is pushed *away* from designs that fail to verify.
    """
    r = np.asarray(rewards, dtype=np.float64)
    if r.size == 0:
        return r
    centered = r - r.mean()
    std = r.std()
    # All-equal rewards (e.g. a whole group failing verification -> all 0.0) give
    # zero advantage everywhere: no spurious gradient from a degenerate group.
    if std < eps:
        return np.zeros_like(r)
    return centered / (std + eps)


@dataclass
class DesignPolicy:
    """Categorical policy over the DesignConfig knob space (softmax logits).

    One logit vector per knob; ``sample`` draws a DesignConfig, ``update`` applies
    a REINFORCE/GRPO policy-gradient step using measured-reward advantages. The
    logits ARE the trained weights — a checkpoint serializes them.
    """

    logits: dict[str, np.ndarray] = field(default_factory=dict)
    lr: float = 0.1

    def __post_init__(self) -> None:
        # Cold start: uniform logits per knob (zeros -> uniform softmax).
        for knob, choices in KNOB_CHOICES.items():
            if knob not in self.logits:
                self.logits[knob] = np.zeros(len(choices), dtype=np.float64)

    # -- distribution ------------------------------------------------------
    def _probs(self, knob: str) -> np.ndarray:
        z = self.logits[knob]
        z = z - z.max()  # numerical stability
        e = np.exp(z)
        return e / e.sum()

    def probabilities(self) -> dict[str, np.ndarray]:
        return {knob: self._probs(knob) for knob in KNOBS}

    def sample(self, rng: np.random.Generator) -> DesignConfig:
        """Sample one DesignConfig (one categorical draw per knob)."""
        picks: dict[str, int] = {}
        for knob, choices in KNOB_CHOICES.items():
            idx = int(rng.choice(len(choices), p=self._probs(knob)))
            picks[knob] = choices[idx]
        return DesignConfig(**picks)

    def _choice_index(self, knob: str, value: int) -> int:
        choices = KNOB_CHOICES[knob]
        return choices.index(value) if value in choices else int(np.argmin([abs(value - c) for c in choices]))

    # -- the weight update -------------------------------------------------
    def update(self, designs: list[DesignConfig], advantages: np.ndarray) -> dict[str, float]:
        """Apply one GRPO policy-gradient step from measured-reward advantages.

        For each knob, the softmax policy gradient of log pi(a) w.r.t. logits is
        ``(onehot(a) - probs)``; scaled by the (measured) advantage and averaged
        over the group, it nudges logits toward knob values that produced
        above-group-mean MEASURED reward. Returns the per-knob grad norm (for the
        checkpoint / climb provenance).
        """
        adv = np.asarray(advantages, dtype=np.float64)
        grad_norms: dict[str, float] = {}
        for knob, choices in KNOB_CHOICES.items():
            probs = self._probs(knob)
            grad = np.zeros(len(choices), dtype=np.float64)
            for design, a in zip(designs, adv, strict=True):
                onehot = np.zeros(len(choices), dtype=np.float64)
                onehot[self._choice_index(knob, getattr(design, knob))] = 1.0
                grad += a * (onehot - probs)
            grad /= max(len(designs), 1)
            self.logits[knob] = self.logits[knob] + self.lr * grad
            grad_norms[knob] = float(np.linalg.norm(grad))
        return grad_norms

    # -- serialization (checkpoint weights) --------------------------------
    def state_dict(self) -> dict[str, list[float]]:
        return {knob: self.logits[knob].tolist() for knob in KNOBS}

    @classmethod
    def from_state_dict(cls, state: dict[str, list[float]], *, lr: float = 0.1) -> "DesignPolicy":
        logits = {knob: np.asarray(state.get(knob, []), dtype=np.float64) for knob in KNOBS}
        # Backfill any missing/short knob to the right width.
        for knob, choices in KNOB_CHOICES.items():
            if logits[knob].shape != (len(choices),):
                logits[knob] = np.zeros(len(choices), dtype=np.float64)
        return cls(logits=logits, lr=lr)

    def argmax_design(self) -> DesignConfig:
        """The current greedy design (most-probable value per knob)."""
        picks = {knob: KNOB_CHOICES[knob][int(np.argmax(self._probs(knob)))] for knob in KNOBS}
        return DesignConfig(**picks)


@dataclass(frozen=True)
class GRPOStepResult:
    """Outcome of one GRPO step (all rewards MEASURED, no proxy)."""

    step: int
    rewards: list[float]
    advantages: list[float]
    mean_reward: float
    best_reward: float
    best_suppression: float
    grad_norms: dict[str, float]
    rtl_hashes: list[str]
    checkpoint_path: str
    n_valid: int


def write_checkpoint(
    *,
    step: int,
    policy: DesignPolicy,
    group: "RolloutGroup",
    advantages: np.ndarray,
    grad_norms: dict[str, float],
    checkpoint_dir: Path = CHECKPOINT_DIR,
    backend: str = "local-numpy",
) -> Path:
    """Write a GRPO checkpoint referencing the group's MEASURED memory rows.

    The checkpoint links to memory via ``rtl_hashes`` (the same sha256 keys the
    C1 ``MemoryStore`` uses) — a checkpoint is only meaningful against the
    measured variants it was trained on. ``reward_source`` is pinned to
    ``"measured"`` so no consumer can mistake this for a proxy run.
    """
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    rewards = group.rewards()
    valid = group.valid_mask()
    payload = {
        "step": step,
        "backend": backend,
        "reward_source": "measured",
        "policy": policy.state_dict(),
        "lr": policy.lr,
        "group": {
            "rtl_hashes": group.rtl_hashes(),
            "rewards": rewards,
            "advantages": [float(a) for a in advantages],
            "suppressions": group.suppressions(),
            "valid": valid,
            "designs": [d.to_dict() for d in group.designs()],
        },
        "grad_norms": grad_norms,
        "mean_reward": float(np.mean(rewards)) if rewards else 0.0,
        "best_reward": float(max(rewards)) if rewards else 0.0,
        "n_valid": int(sum(valid)),
        "written_at": time.time(),
    }
    path = checkpoint_dir / f"grpo_step_{step:04d}.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def grpo_step(
    *,
    step: int,
    policy: DesignPolicy,
    group: "RolloutGroup",
    checkpoint_dir: Path = CHECKPOINT_DIR,
    backend: str = "local-numpy",
) -> GRPOStepResult:
    """One GRPO step on a MEASURED rollout group.

    Pipeline: measured rewards (already in ``group``) -> group-relative
    advantages -> policy logit update -> checkpoint referencing the group's
    measured ``rtl_hash`` rows. The reward is never computed here; it is read
    from the measured boundary the rollout already drove.
    """
    rewards = group.rewards()
    designs = group.designs()
    advantages = compute_advantages(rewards)
    grad_norms = policy.update(designs, advantages)

    checkpoint_path = write_checkpoint(
        step=step,
        policy=policy,
        group=group,
        advantages=advantages,
        grad_norms=grad_norms,
        checkpoint_dir=checkpoint_dir,
        backend=backend,
    )

    suppressions = group.suppressions()
    valid = group.valid_mask()
    best_idx = int(np.argmax(rewards)) if rewards else 0
    return GRPOStepResult(
        step=step,
        rewards=rewards,
        advantages=[float(a) for a in advantages],
        mean_reward=float(np.mean(rewards)) if rewards else 0.0,
        best_reward=float(rewards[best_idx]) if rewards else 0.0,
        best_suppression=float(suppressions[best_idx]) if suppressions else 0.0,
        grad_norms=grad_norms,
        rtl_hashes=group.rtl_hashes(),
        checkpoint_path=str(checkpoint_path),
        n_valid=int(sum(valid)),
    )
