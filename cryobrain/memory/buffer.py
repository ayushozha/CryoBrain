"""Top-K buffer of reward-verified decoder designs."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class VerifiedDesignRecord:
    """One gate-passing design with grader metrics."""

    design: dict[str, Any]
    reward: float
    metrics: dict[str, Any]
    distance: int = 3
    noise_rate: float = 0.001
    source: str = "grader"
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> VerifiedDesignRecord:
        return cls(
            design=dict(raw.get("design", {})),
            reward=float(raw.get("reward", 0.0)),
            metrics=dict(raw.get("metrics", {})),
            distance=int(raw.get("distance", 3)),
            noise_rate=float(raw.get("noise_rate", 0.001)),
            source=str(raw.get("source", "grader")),
            tags=list(raw.get("tags", [])),
        )


class VerifiedDesignBuffer:
    """Persistent top-K store; only designs with reward > 0 and no hard caps."""

    def __init__(self, path: Path | str, *, capacity: int = 32) -> None:
        self.path = Path(path)
        self.capacity = max(1, capacity)
        self._records: list[VerifiedDesignRecord] = []
        if self.path.is_file():
            self._load()

    def _load(self) -> None:
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        items = raw if isinstance(raw, list) else raw.get("records", [])
        self._records = [
            VerifiedDesignRecord.from_dict(item)
            for item in items
            if isinstance(item, dict)
        ]

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = [r.to_dict() for r in self._records[: self.capacity]]
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def add(self, record: VerifiedDesignRecord) -> bool:
        if record.reward <= 0.0:
            return False
        self._records.append(record)
        self._records.sort(key=lambda r: r.reward, reverse=True)
        self._records = self._records[: self.capacity]
        self.save()
        return True

    def add_from_grade(
        self,
        *,
        design: dict[str, Any],
        reward: float,
        metrics: dict[str, Any],
        distance: int,
        noise_rate: float,
        source: str = "grader",
        tags: list[str] | None = None,
    ) -> bool:
        return self.add(
            VerifiedDesignRecord(
                design=design,
                reward=reward,
                metrics=metrics,
                distance=distance,
                noise_rate=noise_rate,
                source=source,
                tags=tags or [],
            )
        )

    def top(self, k: int = 5) -> list[VerifiedDesignRecord]:
        return self._records[: max(0, k)]

    def __len__(self) -> int:
        return len(self._records)