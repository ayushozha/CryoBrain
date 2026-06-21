"""DesignConfig helpers for parametric RTL (SPEC-v5 G9)."""

from __future__ import annotations

import random
from dataclasses import replace

from cryobrain.types import DesignConfig

_DEFAULT = DesignConfig()

# Measured-climb cold start: golden RTL decodes Stim vectors (L2 green in WSL).
GOLDEN_BASELINE = DesignConfig(
    bitwidth=4,
    num_layers=2,
    parallelism=1,
    pipeline_depth=1,
    window_length=8,
)


def sample_random(rng: random.Random | None = None) -> DesignConfig:
    rng = rng or random.Random()
    return DesignConfig(
        bitwidth=rng.choice([2, 4, 8]),
        num_layers=rng.randint(1, 4),
        parallelism=rng.choice([1, 2, 4]),
        pipeline_depth=rng.choice([2, 4, 8]),
        window_length=rng.choice([4, 8, 16]),
    )


def mutate(design: DesignConfig, rng: random.Random | None = None) -> DesignConfig:
    rng = rng or random.Random()
    field = rng.choice(["bitwidth", "num_layers", "parallelism", "pipeline_depth", "window_length"])
    if field == "bitwidth":
        return replace(design, bitwidth=rng.choice([2, 4, 8]))
    if field == "num_layers":
        return replace(design, num_layers=rng.randint(1, 4))
    if field == "parallelism":
        return replace(design, parallelism=rng.choice([1, 2, 4]))
    if field == "pipeline_depth":
        return replace(design, pipeline_depth=rng.choice([2, 4, 8]))
    return replace(design, window_length=rng.choice([4, 8, 16]))


def preset_variants() -> list[DesignConfig]:
    """Three distinct configs for MP1 acceptance."""
    return [
        GOLDEN_BASELINE,
        DesignConfig(bitwidth=8, num_layers=4, parallelism=2, pipeline_depth=4, window_length=16),
        DesignConfig(bitwidth=2, num_layers=1, parallelism=1, pipeline_depth=8, window_length=4),
    ]