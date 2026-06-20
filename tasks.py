"""CryoBrain task bindings for `hud eval tasks.py`."""

from env import cryo_task, env, verilog_task  # noqa: F401
from task_catalog import CRYO_CURRICULUM, TASK_SPECS

tasks = []

for _spec in TASK_SPECS:
    if _spec.template == "cryo_task":
        _curriculum = CRYO_CURRICULUM.get(_spec.slug, {})
        _task = cryo_task(
            task_id=_spec.task_id,
            distance=_curriculum.get("distance", 3),
            noise_rate=_curriculum.get("noise_rate", 0.001),
            max_latency_cycles=_curriculum.get("max_latency_cycles", 64),
            max_area_mm2=_curriculum.get("max_area_mm2", 0.06),
            max_power_mw=_curriculum.get("max_power_mw", 8.0),
        )
    else:
        _task = verilog_task(task_id=_spec.task_id)

    _task.slug = _spec.slug
    _task.columns = {
        "task_id": _spec.task_id,
        "track": _spec.track,
        "variant": _spec.variant,
        "language": _spec.language,
        "toolchain": _spec.toolchain,
        "module": _spec.module,
    }
    tasks.append(_task)