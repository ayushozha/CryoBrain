"""CryoBrain: HUD v6 neural QEC decoder co-design environment.

Forked from hud-evals/verilog-template. Keeps classical FIFO fallback tasks (CP7) and adds
CryoBrain decoder co-design with Stim accuracy + NPU cost model rewards.
"""

import json
import os
import sys

from hud import Environment
from hud.environment import Workspace

from grader import evaluate_task
from scenario_helpers import WORKSPACE_ROOT, setup_task, write_scenario_files
from task_catalog import TASK_SPECS_BY_ID

AGENT_UID = int(os.environ.get("AGENT_UID", "1000"))
AGENT_GID = int(os.environ.get("AGENT_GID", "1000"))


class _AgentWorkspace(Workspace):
    """Agent shell runs as unprivileged uid via setpriv (uid wall)."""

    def shell_argv(self, command=None, *, cwd=None, env=None):
        argv = super().shell_argv(command, cwd=cwd, env=env)
        if sys.platform != "win32" and hasattr(os, "geteuid") and os.geteuid() == 0:
            argv = [
                "setpriv",
                "--reuid", str(AGENT_UID),
                "--regid", str(AGENT_GID),
                "--clear-groups",
                "--",
                *argv,
            ]
        return argv


env = Environment(name="cryobrain-v1")

_ws = _AgentWorkspace(
    WORKSPACE_ROOT,
    network=False,
    env={"HOME": "/home/agent", "USER": "agent", "LOGNAME": "agent"},
)

_last_observation: dict[str, object] = {}


@env.initialize
async def _up() -> None:
    await _ws.start()
    env.add_capability(_ws.capability("shell"))


@env.shutdown
async def _down() -> None:
    await _ws.stop()


@env.tool()
async def get_observation() -> str:
    """Return the latest design scenario and grading-visible state."""
    return json.dumps(_last_observation, indent=2)


@env.tool()
async def run_eval_preview() -> str:
    """Run a lightweight local preview of lint/sim (agent-visible only; hidden grader is authoritative)."""
    from cryobrain.rtl_grader.flow import run_rtl_flow

    result = run_rtl_flow(WORKSPACE_ROOT)
    payload = {
        "sim_passed": result.sim_passed,
        "synth_passed": result.synth_passed,
        "lint_passed": result.lint_passed,
        "cell_count": result.cell_count,
    }
    return json.dumps(payload, indent=2)


@env.template(id="cryo_task")
async def cryo_task(
    task_id: str,
    distance: int = 3,
    noise_rate: float = 0.001,
    max_latency_cycles: int = 64,
    max_area_mm2: float = 0.06,
    max_power_mw: float = 8.0,
    validate_mode: str | None = None,
):
    """CryoBrain decoder co-design with curriculum-bound distance/noise/budget."""
    global _last_observation
    setup_meta = setup_task(
        task_id,
        validate_mode=validate_mode,
        scenario={
            "distance": distance,
            "noise_rate": noise_rate,
            "max_latency_cycles": max_latency_cycles,
            "max_area_mm2": max_area_mm2,
            "max_power_mw": max_power_mw,
        },
    )
    _last_observation = {
        "task_id": task_id,
        "distance": distance,
        "noise_rate": noise_rate,
        "budget": {
            "max_latency_cycles": max_latency_cycles,
            "max_area_mm2": max_area_mm2,
            "max_power_mw": max_power_mw,
        },
        "workdir": setup_meta.get("workdir"),
    }
    answer = yield TASK_SPECS_BY_ID[task_id].prompt
    evaluation = evaluate_task(task_id)
    info = dict(evaluation.info or {})
    info["setup"] = setup_meta
    info["observation"] = _last_observation
    info["final_answer"] = None if answer is None else str(answer)
    evaluation.info = info
    yield evaluation


@env.template(id="verilog_task")
async def verilog_task(task_id: str, validate_mode: str | None = None):
    """Classical FIFO fallback tasks (CP7)."""
    setup_meta = setup_task(task_id, validate_mode=validate_mode)
    answer = yield TASK_SPECS_BY_ID[task_id].prompt
    evaluation = evaluate_task(task_id)
    info = dict(evaluation.info or {})
    info["setup"] = setup_meta
    info["final_answer"] = None if answer is None else str(answer)
    evaluation.info = info
    yield evaluation