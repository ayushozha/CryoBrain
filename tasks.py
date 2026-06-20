"""CryoBrain task bindings for `hud eval tasks.py`."""

from env import cryo_task, env, verilog_task  # noqa: F401
from task_catalog import CRYO_CURRICULUM, TASK_SPECS

tasks = []

for _spec in TASK_SPECS:
    if _spec.template == "cryo_task":
        _curriculum = CRYO_CURRICULUM[_spec.slug]
        _task = cryo_task(
            slug=_spec.slug,
            task_id=_spec.task_id,
            distance=_curriculum["distance"],
            noise_rate=_curriculum["noise_rate"],
            max_latency_cycles=_curriculum["max_latency_cycles"],
            max_area_mm2=_curriculum["max_area_mm2"],
            max_power_mw=_curriculum["max_power_mw"],
        )
    else:
        _task = verilog_task(slug=_spec.slug, task_id=_spec.task_id)

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