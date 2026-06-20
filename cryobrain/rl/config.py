"""RL training configuration (SPEC F6, F7)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from cryobrain.types import CryoBudget


@dataclass(frozen=True)
class CurriculumStage:
    """One RSI distance stage with tightened cryo budget."""

    distance: int
    noise_rate: float
    budget: CryoBudget
    min_reward_to_advance: float = 0.55

    def to_dict(self) -> dict[str, object]:
        return {
            "distance": self.distance,
            "noise_rate": self.noise_rate,
            "budget": self.budget.to_dict(),
            "min_reward_to_advance": self.min_reward_to_advance,
        }


def default_curriculum() -> tuple[CurriculumStage, ...]:
    """d=3→5→7 escalation aligned with task_catalog.CRYO_CURRICULUM."""
    return (
        CurriculumStage(
            distance=3,
            noise_rate=0.001,
            budget=CryoBudget(max_latency_cycles=64, max_area_mm2=0.06, max_power_mw=8.0),
            min_reward_to_advance=0.52,
        ),
        CurriculumStage(
            distance=5,
            noise_rate=0.002,
            budget=CryoBudget(max_latency_cycles=96, max_area_mm2=0.08, max_power_mw=10.0),
            min_reward_to_advance=0.48,
        ),
        CurriculumStage(
            distance=7,
            noise_rate=0.003,
            budget=CryoBudget(max_latency_cycles=128, max_area_mm2=0.10, max_power_mw=12.0),
            min_reward_to_advance=0.45,
        ),
    )


@dataclass
class TrainConfig:
    """Modal / local RL launcher knobs."""

    steps: int = 50
    seed: int = 42
    curriculum: tuple[CurriculumStage, ...] = field(default_factory=default_curriculum)
    output: str = "artifacts/climb_chart.json"
    designs_output: str = "artifacts/designs.json"

    def to_dict(self) -> dict[str, object]:
        return {
            "steps": self.steps,
            "seed": self.seed,
            "curriculum": [s.to_dict() for s in self.curriculum],
            "output": self.output,
            "designs_output": self.designs_output,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> TrainConfig:
        raw_stages = data.get("curriculum")
        if isinstance(raw_stages, list) and raw_stages:
            stages: list[CurriculumStage] = []
            for item in raw_stages:
                if not isinstance(item, dict):
                    continue
                budget_raw = item.get("budget", {})
                if not isinstance(budget_raw, dict):
                    budget_raw = {}
                stages.append(
                    CurriculumStage(
                        distance=int(item.get("distance", 3)),
                        noise_rate=float(item.get("noise_rate", 0.001)),
                        budget=CryoBudget.from_dict(budget_raw),
                        min_reward_to_advance=float(item.get("min_reward_to_advance", 0.55)),
                    )
                )
            curriculum = tuple(stages) if stages else default_curriculum()
        else:
            curriculum = default_curriculum()

        return cls(
            steps=int(data.get("steps", 50)),
            seed=int(data.get("seed", 42)),
            curriculum=curriculum,
            output=str(data.get("output", "artifacts/climb_chart.json")),
            designs_output=str(data.get("designs_output", "artifacts/designs.json")),
        )