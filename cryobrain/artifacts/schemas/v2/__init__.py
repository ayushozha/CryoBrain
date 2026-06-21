"""Measured artifact schema validators for SPEC-v5."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

JsonMap = Mapping[str, Any]

PROXY_FIELDS = frozenset(
    "".join(parts)
    for parts in (
        ("decoder_quality", "_multiplier"),
        ("simulate_candidate", "_ler"),
    )
)


class ArtifactSchemaError(ValueError):
    """Raised when a measured artifact violates the v2 contract."""


def _reject_proxy_fields(value: Any, path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            key_text = str(key)
            if key_text in PROXY_FIELDS:
                raise ArtifactSchemaError(f"{path}.{key_text} is a proxy field")
            _reject_proxy_fields(child, f"{path}.{key_text}")
    elif isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        for index, child in enumerate(value):
            _reject_proxy_fields(child, f"{path}[{index}]")


def _require_mapping(value: Any, path: str) -> JsonMap:
    if not isinstance(value, Mapping):
        raise ArtifactSchemaError(f"{path} must be an object")
    return value


def _require_sequence(value: Any, path: str) -> Sequence[Any]:
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return value
    raise ArtifactSchemaError(f"{path} must be an array")


def _require_number(row: JsonMap, field: str, path: str) -> None:
    value = row.get(field)
    if not isinstance(value, int | float) or isinstance(value, bool):
        raise ArtifactSchemaError(f"{path}.{field} must be numeric")


def _require_int(row: JsonMap, field: str, path: str) -> None:
    value = row.get(field)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ArtifactSchemaError(f"{path}.{field} must be an integer")


def _require_string(row: JsonMap, field: str, path: str) -> None:
    if not isinstance(row.get(field), str) or not row[field]:
        raise ArtifactSchemaError(f"{path}.{field} must be a non-empty string")


def _validate_climb_row(row: JsonMap, path: str) -> None:
    _require_int(row, "step", path)
    _require_number(row, "candidate_ler", path)
    _require_number(row, "suppression", path)
    _require_string(row, "rtl_hash", path)


def validate_measured_climb(artifact: Any) -> JsonMap:
    """Validate ``artifacts/measured_climb.json`` shape."""
    root = _require_mapping(artifact, "$")
    _reject_proxy_fields(root)
    history = _require_sequence(root.get("history"), "$.history")
    if not history:
        raise ArtifactSchemaError("$.history must not be empty")
    for index, item in enumerate(history):
        _validate_climb_row(_require_mapping(item, f"$.history[{index}]"), f"$.history[{index}]")
    return root


def _validate_pareto_point(row: JsonMap, path: str) -> None:
    _require_string(row, "label", path)
    _require_number(row, "ler", path)
    _require_number(row, "area_um2", path)
    _require_int(row, "latency_cycles", path)
    _require_string(row, "rtl_path", path)


def validate_pareto(artifact: Any) -> JsonMap:
    """Validate ``artifacts/measured_pareto.json`` shape."""
    root = _require_mapping(artifact, "$")
    _reject_proxy_fields(root)
    points = _require_sequence(root.get("points"), "$.points")
    if not points:
        raise ArtifactSchemaError("$.points must not be empty")
    for index, item in enumerate(points):
        _validate_pareto_point(_require_mapping(item, f"$.points[{index}]"), f"$.points[{index}]")
    return root


def validate_measured_memory_ab(artifact: Any) -> JsonMap:
    """Validate measured memory A/B series."""
    root = _require_mapping(artifact, "$")
    _reject_proxy_fields(root)
    for field in ("with_memory", "without_memory"):
        series = _require_sequence(root.get(field), f"$.{field}")
        if not series:
            raise ArtifactSchemaError(f"$.{field} must not be empty")
        for index, item in enumerate(series):
            _validate_climb_row(_require_mapping(item, f"$.{field}[{index}]"), f"$.{field}[{index}]")
    return root
