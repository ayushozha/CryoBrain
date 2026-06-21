"""RL policy proposer: a real Fireworks model proposes the next DesignConfig.

Decoupled from the C1 memory store: ``propose_next_design`` accepts a plain
``memory_snapshot`` (dict or list), not a store object, so C1/C5 can feed it
whatever they have. The returned ``DesignConfig`` is always validated.

No-key contract (documented):
  - ``propose_next_design`` RAISES ``RuntimeError`` when ``FIREWORKS_API_KEY``
    is absent or the live call yields no valid config. This is deliberate: the
    proposer is the learning policy, and a silent fallback would let a trainer
    loop quietly degrade or emit un-grounded designs. Callers that want a
    soft path should call ``cryobrain.integrations.fireworks.propose_design_config``
    directly (it returns ``None`` instead) or pass ``strict=False`` here to get
    ``None`` back.
"""

from __future__ import annotations

from typing import Any

from cryobrain.design.validators import validate_design
from cryobrain.integrations.fireworks import DEFAULT_MODEL, propose_design_config
from cryobrain.integrations.secrets import get_key
from cryobrain.types import DesignConfig

# Expected memory_snapshot shape (any of these; all optional):
#   {
#     "scenario": {"distance": 3, "noise_rate": 0.001, ...},   # task context
#     "best": [ {"design": {...}, "reward": 0.23, "metrics": {...}}, ... ],
#   }
# Aliases accepted for the exemplar list: "best", "exemplars", "records",
# "top", "history". A bare list is treated as the exemplar list directly.

_EXEMPLAR_KEYS = ("best", "exemplars", "records", "top", "history")


def _split_snapshot(
    memory_snapshot: dict[str, Any] | list[Any] | None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Normalize a plain snapshot into (scenario, exemplars)."""
    if memory_snapshot is None:
        return {}, []
    if isinstance(memory_snapshot, list):
        return {}, [e for e in memory_snapshot if isinstance(e, dict)]
    if not isinstance(memory_snapshot, dict):
        return {}, []

    scenario = memory_snapshot.get("scenario")
    scenario = dict(scenario) if isinstance(scenario, dict) else {}

    exemplars: list[dict[str, Any]] = []
    for key in _EXEMPLAR_KEYS:
        value = memory_snapshot.get(key)
        if isinstance(value, list):
            exemplars = [e for e in value if isinstance(e, dict)]
            break
    return scenario, exemplars


def propose_next_design(
    memory_snapshot: dict[str, Any] | list[Any] | None = None,
    *,
    model: str = DEFAULT_MODEL,
    strict: bool = True,
) -> DesignConfig | None:
    """Propose the next DesignConfig via a real Fireworks call.

    Builds a prompt from the best variants in ``memory_snapshot``, asks the
    model for a JSON DesignConfig, and returns it only after it passes
    ``validate_design``. The model output is never trusted raw.

    Args:
        memory_snapshot: plain dict/list of prior measured variants (see module
            docstring for accepted shapes). May be empty/None for a cold start.
        model: Fireworks model id.
        strict: when True (default), raise ``RuntimeError`` if no key or no valid
            proposal; when False, return ``None`` instead.

    Returns:
        A validated ``DesignConfig`` (always, when ``strict``), else ``None``.

    Raises:
        RuntimeError: in strict mode, when ``FIREWORKS_API_KEY`` is missing or
            the live call produced no valid config.
    """
    if not get_key("FIREWORKS_API_KEY"):
        if strict:
            raise RuntimeError(
                "FIREWORKS_API_KEY not set; cannot propose a design. "
                "Set the key, or call propose_design_config()/strict=False for a soft path."
            )
        return None

    scenario, exemplars = _split_snapshot(memory_snapshot)
    design = propose_design_config(scenario=scenario, exemplars=exemplars, model=model)

    if design is None:
        if strict:
            raise RuntimeError(
                "Fireworks returned no valid DesignConfig after retries "
                "(empty/malformed/out-of-bounds response)."
            )
        return None

    # Defensive re-validation: the contract is that nothing un-validated escapes.
    validate_design(design)
    return design
