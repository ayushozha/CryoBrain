"""C4 unit: GRPO trains on the MEASURED reward only (boundary mocked).

The real measure stack (Stim->Verilator real LER + Yosys) is Linux/WSL-only, so
this unit MOCKS the measure/score boundary — the swappable ``score_fn`` threaded
into ``measured_reward`` — and asserts the GRPO *wiring* without any GPU/EDA:

  (a) one GRPO step calls the MEASURED reward path (mock call count == group_size),
  (b) advantages are computed from the MEASURED rewards (group-relative),
  (c) a checkpoint is written to ``artifacts/checkpoints/`` referencing the
      group's measured memory ``rtl_hash`` rows,
  (d) reward is 0.0 when verification fails (a verification-failed rollout
      contributes 0 reward and a below-mean advantage).

No real reward formula is exercised: the mock returns measured-shaped score
dicts; production code never computes a reward itself.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from cryobrain.memory.store import MemoryStore
from cryobrain.rl.grpo import DesignPolicy, compute_advantages, grpo_step
from cryobrain.rl.rollout import generate_rollout_group
from cryobrain.types import DesignConfig

TASK_ROOT = Path("tasks/cryo_brain_decoder")


# --- the mocked MEASURED boundary --------------------------------------------


class MeasureSpy:
    """A fake ``score_measured`` (the measure/score boundary C4 consumes).

    Counts calls (proves GRPO drove the measured path) and returns a measured-
    shaped score dict. ``valid_fn`` decides per-call verification pass/fail so we
    can assert the "verification failure => reward 0.0" contract.
    """

    def __init__(self, valid_fn=None) -> None:
        self.calls = 0
        self.seen_workdirs: list[Path] = []
        self._valid_fn = valid_fn or (lambda i, design: True)

    def __call__(self, workdir: Path) -> dict:
        i = self.calls
        self.calls += 1
        self.seen_workdirs.append(Path(workdir))
        design = DesignConfig.from_dict(
            json.loads((Path(workdir) / "design_config.json").read_text(encoding="utf-8"))
        )
        valid = bool(self._valid_fn(i, design))
        if not valid:
            # Verification failure: score_measured zeroes the reward.
            return {
                "reward": 0.0,
                "valid": False,
                "ler": 1.0,
                "mwpm_ler": 0.022,
                "suppression": 0.0,
                "area_um2": 0.0,
                "latency_cycles": 0,
                "power_mw": 0.0,
                "layers_passed": ["L1"],
                "source": "measured",
            }
        # Measured-valid: distinct reward/suppression per call so advantages spread.
        reward = 0.2 + 0.1 * i
        return {
            "reward": reward,
            "valid": True,
            "ler": 0.020 - 0.001 * i,
            "mwpm_ler": 0.022,
            "suppression": 0.05 + 0.05 * i,
            "area_um2": 6.0 + i,
            "latency_cycles": 8,
            "power_mw": 2.0,
            "layers_passed": ["L1", "L2", "L4", "L5"],
            "measurement": {
                "candidate_ler": 0.020 - 0.001 * i,
                "mwpm_ler": 0.022,
                "suppression": 0.05 + 0.05 * i,
            },
            "synth": {"area_um2": 6.0 + i, "latency_cycles": 8, "power_mw_est": 2.0, "valid": True},
            "source": "measured",
        }


@pytest.fixture
def store(tmp_path) -> MemoryStore:
    return MemoryStore(tmp_path / "measured_variants.jsonl")


def _fixed_sampler():
    """Deterministic distinct designs so each rollout maps to a distinct knob value."""
    seq = [
        DesignConfig(bitwidth=2, num_layers=1, parallelism=1, pipeline_depth=2, window_length=4),
        DesignConfig(bitwidth=4, num_layers=2, parallelism=2, pipeline_depth=4, window_length=8),
        DesignConfig(bitwidth=8, num_layers=4, parallelism=4, pipeline_depth=8, window_length=16),
    ]
    box = {"i": 0}

    def _sample(rng):
        d = seq[box["i"] % len(seq)]
        box["i"] += 1
        return d

    return _sample


# --- (a) one GRPO step drives the measured reward path -------------------------


def test_grpo_step_calls_measured_reward_path(tmp_path, store):
    spy = MeasureSpy()
    group_size = 3
    group = generate_rollout_group(
        step=0,
        scenario={"distance": 3, "noise_rate": 0.001, "shots": 200, "benchmark_vectors": 8},
        group_size=group_size,
        policy_sample=_fixed_sampler(),
        store=store,
        score_fn=spy,  # <-- the MEASURED boundary, mocked
        rng=np.random.default_rng(0),
        task_root=TASK_ROOT,
    )
    policy = DesignPolicy(lr=0.1)
    result = grpo_step(step=0, policy=policy, group=group, checkpoint_dir=tmp_path / "checkpoints")

    # The measured score_fn was called exactly once per rollout — GRPO used the
    # measured path, not a formula.
    assert spy.calls == group_size
    assert result.n_valid == group_size
    # Every reward came from the mocked measured boundary.
    assert result.rewards == pytest.approx([0.2, 0.3, 0.4])


# --- (b) advantages are computed from MEASURED rewards -------------------------


def test_advantages_from_measured_rewards(tmp_path, store):
    spy = MeasureSpy()
    group = generate_rollout_group(
        step=0,
        scenario={"distance": 3, "noise_rate": 0.001, "shots": 200, "benchmark_vectors": 8},
        group_size=3,
        policy_sample=_fixed_sampler(),
        store=store,
        score_fn=spy,
        rng=np.random.default_rng(0),
        task_root=TASK_ROOT,
    )
    policy = DesignPolicy(lr=0.1)
    result = grpo_step(step=0, policy=policy, group=group, checkpoint_dir=tmp_path / "checkpoints")

    # Advantages == group-relative normalization of the MEASURED rewards.
    expected = compute_advantages(group.rewards())
    assert result.advantages == pytest.approx([float(a) for a in expected])
    # Group-relative => mean ~0, and ordering follows measured reward (worst<0<best).
    assert result.advantages[0] < 0.0 < result.advantages[-1]
    assert sum(result.advantages) == pytest.approx(0.0, abs=1e-9)
    # The policy actually moved (a real weight update) from the measured advantages.
    assert any(n > 0.0 for n in result.grad_norms.values())


# --- (c) checkpoint written, referencing measured memory rtl_hashes -----------


def test_checkpoint_references_memory_rtl_hashes(tmp_path, store):
    spy = MeasureSpy()
    ckpt_dir = tmp_path / "checkpoints"
    group = generate_rollout_group(
        step=7,
        scenario={"distance": 3, "noise_rate": 0.001, "shots": 200, "benchmark_vectors": 8},
        group_size=3,
        policy_sample=_fixed_sampler(),
        store=store,
        score_fn=spy,
        rng=np.random.default_rng(0),
        task_root=TASK_ROOT,
    )
    policy = DesignPolicy(lr=0.1)
    result = grpo_step(step=7, policy=policy, group=group, checkpoint_dir=ckpt_dir)

    ckpt = Path(result.checkpoint_path)
    assert ckpt.is_file()
    assert ckpt.parent == ckpt_dir
    payload = json.loads(ckpt.read_text(encoding="utf-8"))

    # Measured-only provenance.
    assert payload["reward_source"] == "measured"
    assert payload["step"] == 7
    # Checkpoint references the group's measured memory rows by rtl_hash.
    hashes = payload["group"]["rtl_hashes"]
    assert len(hashes) == 3
    assert all(h for h in hashes)
    # Those hashes are exactly the keys the memory store persisted (the measured rows).
    stored_keys = set(_store_keys(store))
    assert set(group.recorded_hashes()).issubset(stored_keys)
    assert set(hashes) == set(group.rtl_hashes())
    # Serialized policy weights round-trip.
    restored = DesignPolicy.from_state_dict(payload["policy"])
    for knob in restored.logits:
        assert restored.logits[knob] == pytest.approx(policy.logits[knob])


# --- (d) reward 0.0 when verification fails -----------------------------------


def test_reward_zero_on_verification_failure(tmp_path, store):
    # Rollout index 1 fails verification; 0 and 2 pass.
    spy = MeasureSpy(valid_fn=lambda i, design: i != 1)
    group = generate_rollout_group(
        step=0,
        scenario={"distance": 3, "noise_rate": 0.001, "shots": 200, "benchmark_vectors": 8},
        group_size=3,
        policy_sample=_fixed_sampler(),
        store=store,
        score_fn=spy,
        rng=np.random.default_rng(0),
        task_root=TASK_ROOT,
    )
    rewards = group.rewards()
    valid = group.valid_mask()

    # The failed rollout carries reward exactly 0.0 and is not marked valid.
    assert rewards[1] == 0.0
    assert valid == [True, False, True]
    # A failed rollout is NOT recorded to memory (verification gate rejects it).
    assert spy.calls == 3
    assert len(group.recorded_hashes()) == 2

    policy = DesignPolicy(lr=0.1)
    result = grpo_step(step=0, policy=policy, group=group, checkpoint_dir=tmp_path / "checkpoints")
    # Zero-reward (failed) rollout sits below the group mean => negative advantage,
    # pushing the policy away from designs that fail to verify.
    assert result.advantages[1] < 0.0
    assert result.rewards[1] == 0.0


def _store_keys(store: MemoryStore):
    # The store is keyed by rtl_hash internally; expose its keys for the assert.
    return list(store._records.keys())  # noqa: SLF001 - test introspection
