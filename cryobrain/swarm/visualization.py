"""Swarm event-log timeline for dashboard visualization (SPEC-v6 P-viz).

Reads ``artifacts/swarm/event_log.jsonl`` and returns a timeline where only
``measured: true`` events are treated as finalized *results*; all other events
are *in_progress* (proposals, plans, pending measurement, etc.).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EVENT_LOG = ROOT / "artifacts" / "swarm" / "event_log.jsonl"

STATUS_RESULT = "result"
STATUS_IN_PROGRESS = "in_progress"

# Canonical bus order from SPEC-v6 (Visualization may sort/group by this).
PIPELINE_AGENTS = (
    "Research",
    "Planner",
    "Architect",
    "RTL",
    "Measurement",
    "Verifier",
    "Scorer",
    "Memory",
)


def _artifact_root_for_log(log_path: Path) -> Path:
    resolved = log_path.resolve()
    default = DEFAULT_EVENT_LOG.resolve()
    if resolved == default:
        return ROOT
    if resolved.parent.name == "swarm" and resolved.parent.parent.name == "artifacts":
        return resolved.parent.parent.parent
    return resolved.parent.parent


def _artifact_path(event: dict[str, Any], *, root: Path) -> Path | None:
    ref = event.get("artifact_ref")
    if not ref:
        return None
    path = Path(str(ref))
    if not path.is_absolute():
        path = root / path
    try:
        rel = path.resolve().relative_to(root.resolve())
    except ValueError:
        return None
    allowed = (
        Path("artifacts") / "measured",
        Path("artifacts") / "scores",
    )
    if len(rel.parts) < 3 or Path(*rel.parts[:2]) not in allowed:
        return None
    return path


def _artifact_matches(event: dict[str, Any], *, root: Path) -> bool:
    path = _artifact_path(event, root=root)
    if path is None or not path.is_file():
        return False
    try:
        artifact = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
    if artifact.get("design_id") != event.get("design_id"):
        return False
    if event.get("agent") == "Measurement":
        artifact_payload = artifact.get("measurement") or {}
    else:
        artifact_payload = artifact
    for key in ("candidate_ler", "ler", "suppression", "reward", "valid"):
        if key in payload and artifact_payload.get(key) != payload.get(key):
            return False
    return True


def _event_status(event: dict[str, Any], *, require_artifact: bool = False, root: Path = ROOT) -> str:
    """Map raw bus event to dashboard status."""
    if event.get("measured") is True and (not require_artifact or _artifact_matches(event, root=root)):
        return STATUS_RESULT
    return STATUS_IN_PROGRESS


def normalize_event(
    raw: dict[str, Any],
    *,
    require_artifact: bool = False,
    root: Path = ROOT,
) -> dict[str, Any]:
    """Normalize one bus event for dashboard / Gizmo consumption."""
    measured = raw.get("measured") is True
    status = _event_status(raw, require_artifact=require_artifact, root=root)
    return {
        "ts": raw.get("ts"),
        "agent": raw.get("agent"),
        "action": raw.get("action"),
        "design_id": raw.get("design_id"),
        "payload": raw.get("payload") if isinstance(raw.get("payload"), dict) else {},
        "measured": measured and status == STATUS_RESULT,
        "artifact_ref": raw.get("artifact_ref"),
        "status": status,
    }


def load_event_log(
    path: Path | str = DEFAULT_EVENT_LOG,
    *,
    require_artifacts: bool = False,
) -> list[dict[str, Any]]:
    """Load and normalize all events from the append-only JSONL log."""
    log_path = Path(path)
    artifact_root = _artifact_root_for_log(log_path)
    if not log_path.is_file():
        return []

    events: list[dict[str, Any]] = []
    for line_no, line in enumerate(log_path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            raw = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{log_path}:{line_no}: invalid JSONL event") from exc
        if not isinstance(raw, dict):
            raise ValueError(f"{log_path}:{line_no}: event must be a JSON object")
        events.append(normalize_event(raw, require_artifact=require_artifacts, root=artifact_root))
    return events


def build_swarm_timeline(path: Path | str | None = None) -> dict[str, Any] | None:
    """Build dashboard ``swarm_timeline`` section from the event log.

    Returns ``None`` when the log file is missing or empty.
    """
    log_path = Path(path) if path is not None else DEFAULT_EVENT_LOG
    events = load_event_log(log_path, require_artifacts=True)
    if not events:
        return None

    results = [e for e in events if e["status"] == STATUS_RESULT]
    in_progress = [e for e in events if e["status"] == STATUS_IN_PROGRESS]

    return {
        "source": str(log_path.relative_to(ROOT)) if log_path.is_relative_to(ROOT) else str(log_path),
        "pipeline_agents": list(PIPELINE_AGENTS),
        "events": events,
        "summary": {
            "total": len(events),
            "results": len(results),
            "in_progress": len(in_progress),
        },
    }
