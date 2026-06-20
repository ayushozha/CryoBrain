"""Modal RL training entrypoints (SPEC F6)."""

from cryobrain.rl.config import CurriculumStage, TrainConfig, default_curriculum
from cryobrain.rl.local_trainer import baseline_designs, run_local_training

__all__ = [
    "CurriculumStage",
    "TrainConfig",
    "baseline_designs",
    "default_curriculum",
    "run_local_training",
]


def run_training(*args, **kwargs):
    from cryobrain.rl.modal_train import run_training as _run_training

    return _run_training(*args, **kwargs)