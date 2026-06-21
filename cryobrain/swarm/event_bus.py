"""Append-only swarm event log (SPEC-v6 §2 / P-bus).

Each agent action emits one JSON event::

    {ts, agent, action, design_id, payload, measured?:bool, artifact_ref?:str}

Persisted at ``artifacts/swarm/event_log.jsonl``. The log is the coordination
channel, audit trail, and Visualization feed. Any event with ``measured: true``
MUST carry an ``artifact_ref`` (enforced at emit time).
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LOG = ROOT / "artifacts" / "swarm" / "event_log.jsonl"

_NOT_GIVEN = object()


class Agent:
    """Nine swarm roles (SPEC-v6 §1)."""

    RESEARCH = "Research"
    PLANNER = "Planner"
    ARCHITECT = "Architect"
    RTL = "RTL"
    MEASUREMENT = "Measurement"
    VERIFIER = "Verifier"
    SCORER = "Scorer"
    MEMORY = "Memory"
    VISUALIZATION = "Visualization"


ALL_AGENTS: tuple[str, ...] = (
    Agent.RESEARCH,
    Agent.PLANNER,
    Agent.ARCHITECT,
    Agent.RTL,
    Agent.MEASUREMENT,
    Agent.VERIFIER,
    Agent.SCORER,
    Agent.MEMORY,
    Agent.VISUALIZATION,
)


class EventBusError(ValueError):
    """Raised when an event violates the bus contract."""


@dataclass(frozen=True)
class SwarmEvent:
    """One append-only bus record."""

    ts: str | float
    agent: str
    action: str
    design_id: str
    payload: dict[str, Any]
    measured: bool = False
    artifact_ref: str | None = None

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "ts": self.ts,
            "agent": self.agent,
            "action": self.action,
            "design_id": self.design_id,
            "payload": self.payload,
        }
        if self.measured:
            out["measured"] = True
        if self.artifact_ref is not None:
            out["artifact_ref"] = self.artifact_ref
        return out

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "SwarmEvent":
        return cls(
            ts=raw["ts"],
            agent=str(raw["agent"]),
            action=str(raw["action"]),
            design_id=str(raw["design_id"]),
            payload=dict(raw.get("payload") or {}),
            measured=bool(raw.get("measured", False)),
            artifact_ref=str(raw["artifact_ref"]) if raw.get("artifact_ref") else None,
        )


def validate_event_dict(raw: dict[str, Any]) -> dict[str, Any]:
    """Validate schema + measured:true ⇒ artifact_ref rule."""
    required = ("ts", "agent", "action", "design_id", "payload")
    missing = [k for k in required if k not in raw]
    if missing:
        raise EventBusError(f"event missing required fields: {missing}")
    if not isinstance(raw["payload"], dict):
        raise EventBusError("payload must be a dict")
    measured = bool(raw.get("measured", False))
    artifact_ref = raw.get("artifact_ref")
    if measured and not artifact_ref:
        raise EventBusError("measured:true events require artifact_ref")
    if artifact_ref is not None and not str(artifact_ref).strip():
        raise EventBusError("artifact_ref must be non-empty when present")
    return raw


def _default_ts() -> float:
    return time.time()


class EventBus:
    """JSONL-backed append-only message bus with in-memory mirror."""

    def __init__(
        self,
        path: Path | str | None = None,
        *,
        log_path: Path | str | None = _NOT_GIVEN,
    ) -> None:
        if log_path is not _NOT_GIVEN:
            self.log_path = Path(log_path) if log_path is not None else None
        elif path is not None:
            self.log_path = Path(path)
        else:
            self.log_path = DEFAULT_LOG
        self._events: list[dict[str, Any]] = []

    def emit(
        self,
        agent: str,
        action: str,
        design_id: str,
        payload: dict[str, Any],
        *,
        measured: bool = False,
        artifact_ref: str | None = None,
        ts: str | float | None = None,
    ) -> dict[str, Any]:
        """Append one swarm event; return the emitted record."""
        event = SwarmEvent(
            ts=ts if ts is not None else _default_ts(),
            agent=agent,
            action=action,
            design_id=design_id,
            payload=dict(payload),
            measured=measured,
            artifact_ref=artifact_ref,
        )
        raw = validate_event_dict(event.to_dict())
        self._events.append(raw)
        if self.log_path is not None:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with self.log_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(raw) + "\n")
        return raw

    def events(self) -> list[dict[str, Any]]:
        """All events emitted on this bus instance (in order)."""
        return list(self._events)

    def read_all(self) -> list[dict[str, Any]]:
        if self.log_path is None or not self.log_path.is_file():
            return list(self._events)
        out: list[dict[str, Any]] = []
        for line in self.log_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            out.append(json.loads(line))
        return out

    def read_tail(self, n: int = 100) -> list[dict[str, Any]]:
        """Return the last *n* events (oldest-first within the tail window)."""
        if n <= 0:
            return []
        events = self.read_all()
        return events[-n:]

    def read_measured(self, n: int = 100) -> list[dict[str, Any]]:
        """Return the last *n* events where ``measured`` is true."""
        measured = [e for e in self.read_all() if e.get("measured")]
        return measured[-n:] if n > 0 else []