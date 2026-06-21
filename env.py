"""CryoBrain: HUD v6 neural QEC decoder co-design environment.

Forked from hud-evals/verilog-template. Keeps classical FIFO fallback tasks (CP7) and adds
CryoBrain decoder co-design with Stim accuracy + NPU cost model rewards.
"""

import json
import os
import sys

from hud import Environment
from hud.environment import Workspace

from pathlib import Path

from grader import evaluate_task
from scenario_helpers import WORKSPACE_ROOT, hidden_dir, setup_task, write_scenario_files
from task_catalog import TASK_SPECS_BY_SLUG

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


def _read_json(path: Path) -> dict[str, object]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _agent_eval_payload(result: dict[str, object]) -> dict[str, object]:
    """Strip hidden grader internals; expose observable LER/hardware breakdown."""
    subscores = result.get("subscores", {})
    ler = subscores.get("ler_suppression", {}) if isinstance(subscores, dict) else {}
    rtl = subscores.get("rtl_validity", {}) if isinstance(subscores, dict) else {}
    latency = subscores.get("latency", {}) if isinstance(subscores, dict) else {}
    area = subscores.get("area", {}) if isinstance(subscores, dict) else {}
    return {
        "reward": float(result.get("reward", 0.0)),
        "hard_caps": result.get("hard_caps", []),
        "rtl_validity": rtl.get("result", {}),
        "ler_suppression": {
            "score": float(ler.get("raw_score", 0.0)) if isinstance(ler, dict) else 0.0,
            "details": ler.get("result", {}) if isinstance(ler, dict) else {},
        },
        "latency": latency.get("result", {}) if isinstance(latency, dict) else {},
        "area": area.get("result", {}) if isinstance(area, dict) else {},
    }


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
async def get_scenario() -> str:
    """Read the agent-visible scenario.json (distance, noise, budget knobs)."""
    return json.dumps(_read_json(WORKSPACE_ROOT / "scenario.json"), indent=2)


@env.tool()
async def get_design_config() -> str:
    """Read the current decoder design_config.json."""
    return json.dumps(_read_json(WORKSPACE_ROOT / "design_config.json"), indent=2)


@env.tool()
async def update_design_config(patch_json: str) -> str:
    """Merge a JSON patch into design_config.json and return the updated config."""
    patch = json.loads(patch_json)
    if not isinstance(patch, dict):
        raise ValueError("patch_json must be a JSON object")
    path = WORKSPACE_ROOT / "design_config.json"
    merged = {**_read_json(path), **patch}
    _write_json(path, merged)
    global _last_observation
    _last_observation = {**_last_observation, "design_config": merged}
    return json.dumps(merged, indent=2)


@env.tool()
async def run_eval() -> str:
    """Full agent-visible eval: RTL validity + Stim LER + hardware reward breakdown."""
    global _last_observation
    import importlib.util

    task_id = str(_last_observation.get("task_id", "cryo_brain_decoder"))
    hidden = hidden_dir(task_id)
    grade_path = hidden / "grade.py"
    spec = importlib.util.spec_from_file_location(f"{task_id}_agent_grade", grade_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import grader at {grade_path}")
    grade_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(grade_mod)
    result = grade_mod.grade(WORKSPACE_ROOT, hidden_root=hidden)
    payload = _agent_eval_payload(result)
    _last_observation = {
        **_last_observation,
        "last_eval": payload,
        "scenario": _read_json(WORKSPACE_ROOT / "scenario.json"),
        "design_config": _read_json(WORKSPACE_ROOT / "design_config.json"),
    }
    return json.dumps(payload, indent=2)


@env.tool()
async def run_eval_preview() -> str:
    """Run a lightweight local preview of lint/sim (agent-visible only; hidden grader is authoritative)."""
    global _last_observation
    from cryobrain.rtl_grader.flow import run_rtl_flow

    result = run_rtl_flow(WORKSPACE_ROOT)
    payload = {
        "sim_passed": result.sim_passed,
        "synth_passed": result.synth_passed,
        "lint_passed": result.lint_passed,
        "cell_count": result.cell_count,
        "area_estimate": result.area_estimate,
        "latency_cycles": result.latency_cycles,
    }
    _last_observation = {**_last_observation, "last_preview": payload}
    return json.dumps(payload, indent=2)


@env.template(id="cryo_task")
async def cryo_task(
    slug: str,
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
    task_spec = TASK_SPECS_BY_SLUG[slug]
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
        "slug": slug,
        "task_id": task_id,
        "track": task_spec.track,
        "variant": task_spec.variant,
        "distance": distance,
        "noise_rate": noise_rate,
        "budget": {
            "max_latency_cycles": max_latency_cycles,
            "max_area_mm2": max_area_mm2,
            "max_power_mw": max_power_mw,
        },
        "workdir": setup_meta.get("workdir"),
        "last_preview": None,
    }
    answer = yield task_spec.prompt
    evaluation = evaluate_task(task_id)
    info = dict(evaluation.info or {})
    info["setup"] = setup_meta
    info["observation"] = _last_observation
    info["final_answer"] = None if answer is None else str(answer)
    evaluation.info = info
    yield evaluation


@env.template(id="verilog_task")
async def verilog_task(slug: str, task_id: str, validate_mode: str | None = None):
    """Classical FIFO fallback tasks (CP7)."""
    task_spec = TASK_SPECS_BY_SLUG[slug]
    setup_meta = setup_task(task_id, validate_mode=validate_mode)
    answer = yield task_spec.prompt
    evaluation = evaluate_task(task_id)
    info = dict(evaluation.info or {})
    info["setup"] = setup_meta
    info["final_answer"] = None if answer is None else str(answer)
    evaluation.info = info
    yield evaluation