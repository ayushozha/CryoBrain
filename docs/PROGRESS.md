# CryoBrain — Progress Summary

**Last updated:** 2026-06-21 (evening)

**Repo:** https://github.com/ayushozha/CryoBrain

**Branch:** `feat/spec-v61-checkpoints` (PR [#21](https://github.com/ayushozha/CryoBrain/pull/21))

**Canonical spec:** [`docs/specs/SPEC-v6.1-checkpointed.md`](specs/SPEC-v6.1-checkpointed.md) — checkpoints C0–C10, honest claim ladder, 2-min demo

**Latest snapshot:** [`PROGRESS_UPDATE_2026-06-21.md`](PROGRESS_UPDATE_2026-06-21.md)

**Reality audit:** [`SPEC_REALITY_AUDIT.md`](SPEC_REALITY_AUDIT.md)

**Agent orchestration:** [`docs/agents/README.md`](agents/README.md)

---

## North star (SPEC-v6.1)

CryoBrain is a **self-improving AI hardware lab**: a swarm researches, proposes, generates, verifies, measures, scores, remembers, and improves decoder designs — every improvement grounded in real Stim + Verilator + Yosys measurements.

**Slow loop (built):** Research → Planner → Architect → RTL → Measurement → Verifier → Scorer → Memory — coordinated on the event bus.

**Fast loop (vision):** Real-time NPU inside the fridge — 2040 arc, never demo as done today.

**Keystone rule:** worse RTL → worse measured LER. No proxy formula LER in production paths.

---

## Status at a glance (SPEC-v6.1)

| Phase | Status | Notes |
|-------|--------|-------|
| **MP0–MP2** (measured spine) | **Green** | WSL gates pass |
| **C0–C10 checkpoints** | **Green** | `check_spec_v61_checkpoints.py` ALL PASS |
| **P-gate** (Architect climb + memory A/B) | **Green** | Artifacts on disk; decoder climb early (1 step) |
| **P-bus / P-exec / P-viz** | **Green** | Event bus, executors, swarm strip in demo |
| **P-research** (Exa → self-adopt) | **Green** | §2.5 closed; `prompt_influenced` on bus |
| **P-gen** (FIFO / C9) | **Green** | `measured_fifo_climb.json` — 3 steps, throughput ↑ |
| **C3 Pareto** | **Green** | 8 measured L2-safe points |
| **Demo (C10)** | **Green** | Dual-track improvement panel + Play story |
| **Decoder climb quality** | **Partial** | Golden baseline only; mutants need L2-valid path |
| **Memory slope claim** | **Partial** | Single-step A/B artifact |
| **PR merge** | **Pending** | PR #21 |

**Overall (SPEC-v6.1 definition of done): ~95%** — demo-ready; merge + optional recording remain.

---

## Demo (easily demoable today)

| Component | Path | Status |
|-----------|------|--------|
| Offline dashboard | `demo/index.html` | Built from measured artifacts |
| Bundle builder | `scripts/build_demo.py` | Requires `measured_*.json`; bundles FIFO climb + improvement summary |
| Refresh one-liner | `scripts/run_demo_refresh_wsl.sh` | Rebuild + C10 check; `--live` for new FIFO steps |
| Walkthrough script | `scripts/demo_script.md` | 2-min flow: improvement strip → Play story → swarm → Pareto |
| Rehearsal gate | `scripts/check_demo_rehearsal.py` | PASS — FIFO improving track required |

```bash
wsl bash scripts/run_demo_refresh_wsl.sh
# open demo/index.html → click Play story
```

**Best improvement story:** FIFO throughput 0.094 → 0.438 (3 measured steps). Decoder row shows honest golden baseline.

---

## Measured artifacts (committed)

| File | Used by demo | Content |
|------|--------------|---------|
| `measured_climb.json` | Panel B (decoder) | 1 golden step |
| `measured_fifo_climb.json` | Panel B (FIFO) + improvement strip | 3 steps, throughput climb |
| `measured_memory_ab.json` | Panel C | Early A/B |
| `measured_pareto.json` | Panel D | 8 points |
| `swarm/event_log.jsonl` | Swarm strip | Measured events + research adoption |
| `design_runs/d000–d002/` | C2 export | 3 design cycles |

All use `reward_source: score_measured` or `measured_fifo_throughput`. Demo `data_era: "measured"`.

---

## Architecture

```
Research → Planner → Architect → RTL → Measurement → Verifier → Scorer → Memory
                ↑______________________________________________|
                         (measured event bus — SPEC-v6 §2)
```

- **Measured spine:** `measure_candidate_ler` → `score_measured` → `compute_reward`
- **FIFO platform:** `fifo_loop.py` → `measured_fifo_climb.json`
- **Pareto:** `frontier_sweep.py` → L2-safe decoder variants
- **Demo:** `build_demo.py` → dual-track improvement + swarm timeline

---

## Honest claim ladder

| Claim | Safe today? |
|-------|-------------|
| Candidate accuracy is measured (RTL on Stim vectors) | **Yes** |
| Reward is measured-only (no proxy formula) | **Yes** |
| Agents keep improving (measured) | **Yes on FIFO** — 3-step climb |
| Engine generalizes (decoder + FIFO) | **Yes (two fixed targets)** |
| Decoder beats golden over multiple steps | **No** — 1 accepted step |
| Memory compounds faster (slope) | **Partial** — wiring only |
| We beat MWPM / mass-produced silicon | **Never** |

---

## How to run

```bash
# Full SPEC-v6.1 gate (WSL)
wsl bash scripts/run_spec_v6_gate_wsl.sh

# Demo refresh (WSL)
wsl bash scripts/run_demo_refresh_wsl.sh
wsl bash scripts/run_demo_refresh_wsl.sh --live   # optional: new FIFO climb

# Checkpoint validator (Windows)
uv run python scripts/check_spec_v61_checkpoints.py
uv run python scripts/check_demo_rehearsal.py

# Measured milestones (WSL)
wsl bash scripts/run_mp0_wsl.sh
wsl bash scripts/run_c5_climb_wsl.sh 5
wsl bash scripts/run_gen_fifo_wsl.sh 5

# Tests
uv run pytest tests/test_demo_measured.py -q
```

See [`docs/EDA_WSL.md`](EDA_WSL.md) for toolchain setup.

---

## What's next

1. **Merge PR #21** to `main`
2. **Screen-record** Play story + improvement strip (pitch backup)
3. **Decoder climb** — ≥2 accepted L2-valid steps beyond golden
4. **Memory multi-step A/B** — earn slope claim
5. **Live demo refresh** before presentations (`--live`)

---

## One-line status

**CryoBrain is demo-ready:** SPEC-v6.1 C0–C10 green, FIFO proves agents keep improving, offline dashboard tells the story honestly — merge PR #21 and record backup for pitch.