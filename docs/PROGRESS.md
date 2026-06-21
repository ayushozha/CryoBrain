# CryoBrain — Progress Summary

**Last updated:** 2026-06-21  
**Branch:** `feat/cryobrain-scaffold`  
**Spec:** [SPEC2.md](../SPEC2.md) (v3 — memory + curriculum as differentiators)

---

## What We Set Out to Build

CryoBrain is a verifiable RL environment where an AI learns to design neural quantum error correction (QEC) decoders. Every candidate is scored on:

- **Stim accuracy** — logical error rate (LER) suppression vs MWPM baseline
- **Cryogenic hardware budget** — Yosys area, Verilator latency, NPU cost model

The system also includes **verified-design memory** (compounding past winners) and a **distance curriculum** (d=3→5→7) so the decoder brain co-scales with the chip.

The deliverable is the **environment + self-improving loop**, not a single static chip design.

---

## Architecture (Three Layers)

| Layer | What it is | Artifact |
|---|---|---|
| **The chip** | Synthesizable Verilog decoder block | `cryo_brain_decoder.sv` |
| **The environment** | Verifiable grader: accuracy + hardware + validity gate | `grade.py`, `env.py` |
| **The AI** | RL loop augmented with memory + curriculum | `local_trainer.py`, `modal_train.py` |

---

## Phase 1: Core Environment (~85%)

### Reward contract

1. **Validity gate (binary):** RTL bit-exact vs golden + clean synth. Fail → reward `0.0`.
2. **Continuous reward:** LER suppression vs MWPM + latency/area terms in `[0, 1]`.
3. **Calibration (CP3):** Base policy lands in **20–50%** with measurable variance before training.

### Critical fix: honest LER in `grade.py`

**Before:** LER was derived from `benchmark_exactness × 0.5`, producing flat suppression (~0.25) for all design variants.

**After:** Calls `evaluate_accuracy()` from the Stim harness with real design-policy LER via `decoder_policy.py`. Grading floor: `noise_rate ≥ 0.02`, `shots ≥ 1000` so the MWPM anchor is non-zero at grade time.

**Commit:** `3115d4a` — `fix: wire grade.py to real Stim policy LER for honest F5/F7/F9`

### RTL and hardware pipeline

- Golden decoder through **Verilator** (syndrome → correction waveform, real VCD)
- **Yosys** synthesis (area, cell count, latch check)
- Classical FIFO fallback tasks (repair, cocotb-dv, formal) for SPEC2 CP8

### HUD environment (`env.py`)

Agent tools:

- `get_scenario`, `get_design_config`, `update_design_config`
- `run_eval` — full grader breakdown (LER, RTL validity, hardware)
- `run_eval_preview` — lightweight lint/sim preview
- `retrieve_exemplars` — verified-design memory hook (SPEC2 F7)

---

## Phase 2: Checkpoints

| CP | SPEC2 meaning | Status | Evidence |
|---|---|---|---|
| **CP0** | HUD `hud eval` on stock FIFO | **Green (WSL)** | Live eval ~82s; mean reward **0.250** ([job](https://hud.ai/jobs/d5e730a977f04df59875afd1f3c022ba)) |
| **CP1** | Stim LER harness | Done | `benchmark.py` / `stim_harness.py` |
| **CP2** | Validity gate | Green (WSL) | wrong=0, starter≈0.36, golden≈0.63 |
| **CP3** | Calibration 20–50% | Green (WSL) | mean≈0.357, spread≈0.115 |
| **CP4** | RL climb chart | Green (WSL) | 0.364 → 0.459 over 12 steps |
| **CP5** | Memory A/B overlay | Green (WSL) | 0.464 → 0.522 with memory on |
| **CP6** | Curriculum d=3→5→7 | Green (WSL) | `ler_spread=0.2173` |
| **CP7** | Yosys + Verilator artifacts | Green (WSL) | Repo script: `check_cp5.py` |
| **CP8** | Classical FIFO fallback | Green (WSL) | Repo script: `check_cp7.py` |

> **Naming mismatch:** Repo `check_cp5` = waveform/synth (SPEC2 **CP7**). Repo `check_cp7` = FIFO fallback (SPEC2 **CP8**). SPEC2 **CP5 (memory A/B)** uses `check_cp5_memory.py`.

---

## Phase 3: Training Loop (F6)

### Implementation

- `cryobrain/rl/local_trainer.py` — hill-climb over 8 `DesignConfig` candidates
- Every step scored by the real hidden grader (`tasks/cryo_brain_decoder/donotaccess/grade.py`)
- Curriculum stages (d=3→5→7) woven into training progression
- Writes `artifacts/climb_chart.json` and `artifacts/designs.json`

### CP4 evidence

| Metric | Value |
|---|---|
| Steps | 12 |
| Start reward | 0.364 |
| End reward | 0.459 |
| Backend | `real_local` |
| Artifact | `artifacts/climb_chart_rl.json` |

This is a real climb — not area noise or stubbed rewards.

### Modal dispatch

- `cryobrain/rl/modal_train.py` — GPU launcher when Modal creds exist
- Modal authenticated to workspace `ayushozha` (`~/.modal.toml`)
- Image updated: Verilator, Yosys, task tree, sponsor deps
- **Not yet run:** production Modal GPU climb chart artifact

---

## Phase 4: Memory — The Differentiator (F7 / WS5)

### Built

| Component | Path | Role |
|---|---|---|
| Buffer | `cryobrain/memory/buffer.py` | Top-K verified `(design, reward, metrics)` store |
| Retrieval | `cryobrain/memory/retrieve.py` | `retrieve(task)` → M exemplars by distance/noise match |
| Seed | `scripts/seed_memory.py` | Populate from CP3 calibration rollouts |
| A/B run | `scripts/run_memory_ab.py` | With-memory vs without-memory overlay |
| Gate | `scripts/check_cp5_memory.py` | SPEC2 CP5 pass/fail |
| WSL helper | `scripts/run_memory_ab_wsl.sh` | Correct PATH + OSS CAD + uv |

Trainer flags in `TrainConfig`:

- `memory_enabled` — bias candidates from retrieved exemplars
- `exa_seed` — tag memory with Exa literature hits
- `use_fireworks` — Fireworks inference for design proposals (optional)

### CP5 memory A/B results (8 steps, WSL)

| Arm | End reward | Slope |
|---|---|---|
| Without memory | 0.464 | 0.014 |
| **With memory** | **0.522** | **0.031** |

`memory_wins: true` — demo slide #6 material.

Exa seeded literature into memory tags, e.g. FPGA neural decoder and memristive cryogenic decoder papers.

**Artifact:** `artifacts/memory_ab_overlay.json`

---

## Phase 5: Sponsor Integrations

| Sponsor | Module | Status |
|---|---|---|
| **HUD** | `env.py` | API key set; environment scaffolded |
| **Modal** | `modal_train.py` | Authenticated; image ready; GPU run pending |
| **Exa** | `cryobrain/integrations/exa_rag.py` | Works in WSL; seeds memory + citations |
| **Fireworks** | `cryobrain/integrations/fireworks.py` | Inference hook (`deepseek-v3p1`); optional in trainer |
| **Daytona** | `cryobrain/integrations/daytona.py` | Scaffold; install in WSL (native wheel blocked on Windows) |
| **Antim Gizmo** | `cryobrain/integrations/antim.py` | Best-effort concept visual hook |

Keys live in `.env` (gitignored). Optional deps: `uv sync --extra sponsors --extra rl`.

Health check: `python scripts/check_sponsors.py`

**Commit:** `825dc80` — `feat: wire sponsor integrations and verified-design memory`

---

## Artifacts (gitignored under `artifacts/`)

| File | Contents |
|---|---|
| `climb_chart_rl.json` | CP4 RL climb (12 steps) |
| `climb_chart_no_memory.json` | Memory A/B — control arm |
| `climb_chart_memory.json` | Memory A/B — treatment arm |
| `memory_ab_overlay.json` | A/B summary + `memory_wins` |
| `verified_memory.json` | Top-K verified designs |
| `designs.json` | Policy designs for Pareto |
| `pareto.png` / `pareto.json` | Pareto explorer |
| `distance_curriculum.png` | d=3→5→7 scaling chart |
| `cryo_golden_trace.vcd` | Real Verilator waveform |

---

## Git History

```
825dc80 feat: wire sponsor integrations and verified-design memory
3115d4a fix: wire grade.py to real Stim policy LER for honest F5/F7/F9
419a3e7 feat: CP2/CP5-CP7 checkpoints and env agent tools
48a5738 feat: run cp4 with real graded training
c0470aa feat: CP3 multi-rollout reward calibration gate
```

**Branch:** `feat/cryobrain-scaffold`  
**Remote:** not configured (push/PR blocked)

---

## SPEC2 Definition of Done — Scorecard

| Item | Status |
|---|---|
| CP0–CP7 green | Modal CP4 artifact remain |
| Reward = gate + LER + hardware, 20–50% band | Done |
| Real `.sv` → Yosys + Verilator | Done |
| Climb chart + memory-on-vs-off overlay | Local/WSL done; Modal pending |
| Pareto + distance-scaling, continuous accuracy | Done |
| Beachhead + moonshot business slide | Not started |
| CP8 classical fallback | Done |

**Overall progress: ~85%**

---

## CP0 Evidence (2026-06-21)

Command (WSL):

```bash
wsl bash /mnt/c/Users/ayush/Desktop/Hackathons/YC/06-20-2026/scripts/run_cp0_wsl.sh
# equivalent: hud eval tasks.py claude --task-ids stream-arb-fifo-cocotb-dv --group 1 -y
```

| Field | Value |
|---|---|
| Task | `stream-arb-fifo-cocotb-dv` |
| Agent | `claude` (claude-sonnet-4-6 via HUD Gateway) |
| Runtime | local |
| Duration | 82.1s |
| Mean reward | **0.250** (matches starter testbench calibration) |
| HUD job | https://hud.ai/jobs/d5e730a977f04df59875afd1f3c022ba |

No `ANTHROPIC_API_KEY` required — calls routed through HUD Gateway with `HUD_API_KEY`.

---

## How to Run

All WSL training should use the helper scripts (they set OSS CAD + `uv` paths correctly). Avoid raw `wsl bash -lc` with Windows `PATH` injection — it breaks on `Program Files (x86)` parentheses.

```bash
# CP4 training
wsl bash /mnt/c/Users/ayush/Desktop/Hackathons/YC/06-20-2026/scripts/run_cp4_wsl.sh --steps 50

# Memory A/B (SPEC2 CP5)
wsl bash /mnt/c/Users/ayush/Desktop/Hackathons/YC/06-20-2026/scripts/run_memory_ab_wsl.sh --steps 20

# Checkpoints (inside WSL venv)
cd /mnt/c/Users/ayush/Desktop/Hackathons/YC/06-20-2026
. .venv-linux/bin/activate
python scripts/check_cp2.py
python scripts/check_cp3.py
python scripts/check_cp5_memory.py
python scripts/check_cp6.py
python scripts/check_cp5.py   # waveform/synth (SPEC2 CP7)
python scripts/check_cp7.py   # FIFO fallback (SPEC2 CP8)

# Modal GPU training (Windows, after local climb is green)
py -3.12 -m modal run -m cryobrain.rl.modal_train --steps 50

# Sponsor connectivity
python scripts/check_sponsors.py
```

> **PowerShell note:** `wsl bash ... 2>&1` may report exit code 1 when `uv sync` writes to stderr, even if training succeeds. Check the artifact JSON for `"end_reward"` in `summary`.

---

## What's Left (~18%)

1. **Modal GPU climb chart** — sponsor-backed CP4 artifact for demo slide #5
2. **Fireworks GRPO** — model writes decoder RTL, not just knob sweep (full F6 vision)
3. ~~**CP0** — live `hud eval` on `stream-arb-fifo-cocotb-dv`~~ **Done** (2026-06-21)
4. **WS7 demo deck** — 2-min demo per SPEC2 §10 + beachhead/moonshot business narrative
5. **Antim concept visual** — optional architecture diagram (slide #1)
6. **Git remote** — enable PR workflow and push branch

---

## One-Line Status

We have a **working, honest, verifiable RL environment** with a **real climb chart** and a **memory A/B proof that compounding works**. Remaining work is mostly sponsor-backed scale (Modal/Fireworks), HUD eval proof, and demo/pitch packaging.