"""Shared configuration types for CryoBrain tasks."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class DesignConfig:
    bitwidth: int = 4
    num_layers: int = 2
    parallelism: int = 1
    pipeline_depth: int = 4
    window_length: int = 8

    def to_dict(self) -> dict[str, int]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> DesignConfig:
        return cls(
            bitwidth=int(data.get("bitwidth", 4)),
            num_layers=int(data.get("num_layers", 2)),
            parallelism=int(data.get("parallelism", 1)),
            pipeline_depth=int(data.get("pipeline_depth", 4)),
            window_length=int(data.get("window_length", 8)),
        )


@dataclass(frozen=True)
class CryoBudget:
    max_latency_cycles: int = 64
    max_area_mm2: float = 0.06
    max_power_mw: float = 8.0

    def to_dict(self) -> dict[str, float | int]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> CryoBudget:
        return cls(
            max_latency_cycles=int(data.get("max_latency_cycles", 64)),
            max_area_mm2=float(data.get("max_area_mm2", 0.06)),
            max_power_mw=float(data.get("max_power_mw", 8.0)),
        )


@dataclass(frozen=True)
class ScenarioConfig:
    distance: int = 3
    noise_rate: float = 0.001
    shots: int = 1000
    rounds: int = 3

    def to_dict(self) -> dict[str, float | int]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> ScenarioConfig:
        return cls(
            distance=int(data.get("distance", 3)),
            noise_rate=float(data.get("noise_rate", 0.001)),
            shots=int(data.get("shots", 1000)),
            rounds=int(data.get("rounds", 3)),
        )