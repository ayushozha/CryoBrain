# CryoBrain

**The NPU brain inside the quantum chip that keeps it alive.** A HUD v6 RL environment that
co-designs a neural QEC decoder against **logical error rate** (Stim) and **cryogenic hardware**
(Yosys + NPU cost model).

Forked from [`hud-evals/verilog-template`](https://github.com/hud-evals/verilog-template) with
classical FIFO fallback tasks armed for CP7.

## Repository map

| Path | Role |
|------|------|
| `env.py` | HUD environment, uid wall, `@env.tool` observation + eval preview |
| `grader.py` | Routes to per-task hidden graders |
| `tasks.py` / `task_catalog.py` | Task bindings + RSI distance curriculum |
| `scenario_helpers.py` | Workspace reset + scenario injection |
| `cryobrain/` | Stim harness, MWPM baseline, cost model, reward, RL, artifacts |
| `tasks/cryo_brain_decoder/` | Primary co-design task (RTL + config + hidden grader) |
| `tasks/stream_arb_fifo_*` | Classical mutant-kill fallback (CP7) |
| `scripts/` | CP0–CP3 checkpoint scripts |
| `SPEC.md` | Full product spec v2 |

## Quick start

```powershell
uv sync
# HUD_API_KEY in .env (project root)
uv run python scripts/check_cp0.py
uv run python scripts/check_cp1.py
```

Local EDA tools (`verilator`, `yosys`, `sby`, `z3`) via
[OSS CAD Suite](https://github.com/YosysHQ/oss-cad-suite-build/releases/latest).

## Run evals

```powershell
# Primary CryoBrain task
hud eval tasks.py claude --task-ids cryo-brain-decoder-d3 --group 1 -y

# RSI curriculum variants
hud eval tasks.py claude --task-ids cryo-brain-decoder-d5 --group 1 -y

# CP7 fallback (classical DV)
hud eval tasks.py claude --task-ids stream-arb-fifo-cocotb-dv --group 1 -y
```

## Checkpoints (from SPEC.md)

| CP | Command |
|----|---------|
| CP0 | `uv run python scripts/check_cp0.py` |
| CP1 | `uv run python scripts/check_cp1.py` |
| CP2/CP3 | `uv run python scripts/calibrate_reward.py` |
| CP4 | `uv run --extra rl python -m cryobrain.rl.modal_train --steps 50` |
| CP6 | `uv run python -m cryobrain.artifacts.pareto` |

## Deploy

```powershell
hud deploy .
hud sync tasks cryobrain --yes
hud eval tasks.py claude --runtime hud --full
```

## License

MIT. Third-party HDL notices in `THIRD_PARTY_NOTICES.md`.