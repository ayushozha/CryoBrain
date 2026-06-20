# CryoBrain

**The NPU brain inside the quantum chip that keeps it alive.**

CryoBrain is a [HUD v6](https://github.com/hud-evals) RL environment for co-designing a
neural quantum error correction (QEC) decoder against two verifiable axes:

- **Accuracy** — logical error rate from [Stim](https://github.com/quantumlib/Stim), scored as
  suppression vs a PyMatching (MWPM) baseline
- **Hardware** — synthesizable RTL (Verilator + Yosys) plus an NPU-style cryogenic cost model

The repo forks [`hud-evals/verilog-template`](https://github.com/hud-evals/verilog-template) and
keeps classical FIFO mutant-kill tasks armed as a complete fallback track (CP7).

Full product spec: [`SPEC.md`](SPEC.md).

---

## Repository map

| Path | Role |
|------|------|
| `env.py` | HUD environment: uid wall, `@env.tool` (`get_observation`, `run_eval_preview`), curriculum templates |
| `grader.py` | Routes scoring to per-task hidden graders under `tasks/*/donotaccess/` |
| `tasks.py` | Binds catalog entries to HUD eval scenarios |
| `task_catalog.py` | Six eval slugs (3× RSI cryo + 3× FIFO fallback) and `CRYO_CURRICULUM` knobs |
| `scenario_helpers.py` | Workspace reset, scenario injection into `scenario.json` |
| `cryobrain/` | Stim harness, MWPM baseline, NPU cost model, reward gate, RL, artifacts |
| `tasks/cryo_brain_decoder/` | Primary co-design task (RTL stub, config, hidden grader) |
| `tasks/stream_arb_fifo_*` | Classical repair / cocotb DV / formal fallback (CP7) |
| `scripts/` | CP0–CP3 checkpoint scripts |
| `tests/` | Integration tests for catalog, env tools, checkpoints |
| `Dockerfile.hud` | Container image for `hud serve` + `hud eval --runtime hud` |
| `SPEC.md` | Spec v2 (reward design, checkpoints, demo script) |

---

## Quick start

**Prerequisites:** Python 3.11–3.12, [uv](https://docs.astral.sh/uv/), `HUD_API_KEY` in `.env`.

```powershell
uv sync
uv run python scripts/check_cp0.py   # EDA + HUD CLI on PATH
uv run python scripts/check_cp1.py   # Stim + MWPM smoke test
uv run pytest -q                     # catalog + env integration tests
```

**Local EDA (recommended):** install
[OSS CAD Suite](https://github.com/YosysHQ/oss-cad-suite-build/releases/latest) and ensure
`verilator`, `yosys`, `sby`, and `z3` are on `PATH`.

---

## Task catalog (6 eval slugs)

| Slug | Track | Curriculum / notes |
|------|-------|-------------------|
| `cryo-brain-decoder-d3` | qec-codesign | d=3, noise 0.001, tight cryo budget |
| `cryo-brain-decoder-d5` | qec-codesign | d=5, escalated noise + budget |
| `cryo-brain-decoder-d7` | qec-codesign | d=7, hardest RSI stage |
| `stream-arb-fifo-repair` | fallback-design | Verilog repair + sim |
| `stream-arb-fifo-cocotb-dv` | fallback-verification | Cocotb mutant-kill DV |
| `stream-arb-fifo-formal` | fallback-formal | SymbiYosys properties |

RSI distance/noise/budget bindings live in `task_catalog.CRYO_CURRICULUM` and are written into
`/workdir/scenario.json` at episode reset.

---

## Run evals

```powershell
# Primary CryoBrain task (d=3)
hud eval tasks.py claude --task-ids cryo-brain-decoder-d3 --group 1 -y

# RSI curriculum
hud eval tasks.py claude --task-ids cryo-brain-decoder-d5,cryo-brain-decoder-d7 --group 1 -y

# CP7 fallback (classical DV)
hud eval tasks.py claude --task-ids stream-arb-fifo-cocotb-dv --group 1 -y
```

**Agent tools** (see `env.py`):

- `get_observation` — current slug, distance, noise, budget, last RTL preview
- `run_eval_preview` — lightweight lint/sim/synth preview (hidden grader is authoritative)

---

## Verification checkpoints

| CP | What | Command / pass criterion |
|----|------|--------------------------|
| **CP0** | Tooling | `uv run python scripts/check_cp0.py` — `verilator`, `yosys`, `sby`, `z3`, `hud` on PATH |
| **CP1** | Stim harness | `uv run python scripts/check_cp1.py` — LER rises with noise; MWPM sane at low noise |
| **CP2/CP3** | Reward gate + calibration | `uv run python scripts/calibrate_reward.py` — base policy in 20–50% band |
| **CP4** | RL loop | `uv run --extra rl python -m cryobrain.rl.modal_train --steps 50` |
| **CP5** | Real artifacts | Yosys netlist + Verilator waveform from `tasks/cryo_brain_decoder` |
| **CP6** | Pareto + scaling | `uv run python -m cryobrain.artifacts.pareto` + d3→d5→d7 evals |
| **CP7** | Fallback armed | `hud eval tasks.py claude --task-ids stream-arb-fifo-cocotb-dv --group 1 -y` |

Integration tests: `uv run pytest tests/test_env_catalog.py tests/test_checkpoints.py -q`.

---

## Deploy (HUD runtime)

```powershell
hud deploy .
hud sync tasks cryobrain --yes
hud eval tasks.py claude --runtime hud --full
```

`Dockerfile.hud` bakes task baselines into `/donotaccess/<task_id>/baseline` and serves
`env:env` on port 8765 with the agent uid wall (`setpriv` → uid 1000).

---

## License

MIT. Third-party HDL notices in `THIRD_PARTY_NOTICES.md`.