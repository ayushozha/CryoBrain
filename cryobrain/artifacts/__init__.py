"""Demo artifacts: Pareto plots, climb charts, distance curriculum."""

__all__ = [
    "generate_all_artifacts",
    "load_climb_chart",
    "load_designs",
    "plot_distance_curriculum",
    "plot_pareto",
    "write_curriculum_meta",
]


def __getattr__(name: str):
    if name in {"load_climb_chart", "plot_distance_curriculum", "write_curriculum_meta"}:
        from cryobrain.artifacts import curriculum as mod

        return getattr(mod, name)
    if name in {"generate_all_artifacts", "load_designs", "plot_pareto"}:
        from cryobrain.artifacts import pareto as mod

        return getattr(mod, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")