"""Measured benchmarks for CryoBrain (SPEC-v5 C10).

Pareto frontier and benchmark plots whose accuracy axis is the MEASURED logical
error rate (``candidate_ler`` from Verilator-on-Stim, via
``measure_candidate_ler``) — never a formula/proxy LER, never an npu_cost-only
point. All inputs come from the C1 measured-variant memory store
(``query_pareto_candidates``), so only verified records with a measured LER and
an ``rtl_path`` can ever enter a benchmark.
"""

from typing import Any

__all__ = ["ACCURACY_AXIS_LABEL", "build_pareto"]


def __getattr__(name: str) -> Any:
    # Lazy re-export so ``python -m cryobrain.benchmark.pareto`` does not trigger
    # the runpy double-import warning (the submodule isn't imported at package load).
    if name in __all__:
        from cryobrain.benchmark import pareto

        return getattr(pareto, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
