# CryoBrain — Progress Summary

**Last updated:** 2026-06-21

**Repo:** https://github.com/ayushozha/CryoBrain

**Branch:** `feat/real-measured-artifacts` (PR [#20](https://github.com/ayushozha/CryoBrain/pull/20)) — measured artifacts + SPEC-v6 §2.5

**Canonical spec:** [`docs/specs/SPEC-v6.md`](specs/SPEC-v6.md) — nine-role swarm, event bus, honest claim ladder, 2-min demo

**Latest snapshot:** [`PROGRESS_UPDATE_2026-06-21.md`](PROGRESS_UPDATE_2026-06-21.md)

**Reality audit:** [`SPEC_REALITY_AUDIT.md`](SPEC_REALITY_AUDIT.md)

**Agent orchestration:** [`docs/agents/README.md`](agents/README.md)

**SPEC-v5** remains the measured-engine reference (MP0–MP2 APIs); **SPEC-v6** is the active product spec. See [`specs/README.md`](specs/README.md).

---

## North star (SPEC-v6)

CryoBrain is a **self-improving AI hardware lab**: a swarm of agents researches, proposes, generates, verifies, measures, scores, remembers, and improves decoder designs — every improvement grounded in real Stim + Verilator + Yosys measurements.

**Slow loop (built):** Research → Planner → Architect → RTL → Measurement → Verifier → Scorer → Memory — coordinated on the event bus.

**Fast loop (vision):** Real-time NPU inside the fridge — 2040 arc, never demo as done today.

**Keystone rule:** worse RTL → worse measured LER. No proxy formula LER in production paths.

**Research adoption (§2.5):** New Exa literature must bias trained agents and tag verified winners — spec'd; wiring partial.

---

## Status at a glance (SPEC-v6)

| Phase | Status | Notes |
|-------|--------|-------|
| **MP0–MP2** (measured spine) | **Green** | WSL gates pass |
| **P-gate** (Architect climb + memory A/B) | **Green** | `measured_climb.json`, `measured_memory_ab.json` on disk |
| **P-bus / P-exec / P-viz** | **Built** | Event bus, executors, demo swarm strip |
| **P-train2** (Planner) | **Built** | `planner.py`, `planner_trainer.py` |
| **P-research** (Exa → self-adopt) | **Partial** | `context_pack` emitted; §2.5 closed loop open |
| **Demo** | **Measured-only** | `build_demo.py` requires `measured_*.json`; `data_era: "measured"` |
| **P-gen** (FIFO) | **Code only** | `run_gen_fifo_wsl.sh` not proven in WSL |
| **Climb quality** | **Partial** | 1/3–1/5 steps accepted (golden only; mutants fail L2) |
| **Tests** | **237 pytest** | Collected locally |

**Overall (SPEC-v6 definition of done): ~75%** — demo-honest measured story ready; adoption wiring, multi-step climb, FIFO proof, rehearsal remain.

---

## Historical — SPEC-v5 milestone IDs (engineering spine)

The v5 IDs (MP0–MP5, C1–C10, X1–X10) map to the same modules. Tables below use v5 labels; v6 phase names (P-gate, P-bus, …) are in [`SPEC-v6.md`](specs/SPEC-v6.md) §6.

## SPEC-v5 milestones (measured)

| ID | Gate | Status | Evidence |
|----|------|--------|----------|
| **MP0** | Worse `.sv` → worse measured LER | **Green (WSL)** | `wsl bash scripts/run_mp0_wsl.sh` |
| **MP1** | 3 configs → 3 distinct (area, LER) | **Green (WSL)** | `wsl bash scripts/run_mp1_wsl.sh` |
| **MP2** | Reward only on measured change | **Green (WSL)** | `wsl bash scripts/run_mp2_wsl.sh` |
| **MP3** | Measured climb (not proxy) | **Code green · artifact pending** | `local_trainer.py` + `run_c5_climb_wsl.sh`; no `measured_climb.json` yet |
| **MP4** | Memory A/B on measured runs | **Code green · artifact pending** | Trainer emits `measured_memory_ab.json`; not generated on disk |
| **MP5** | L1–L5 all gate score | **Partial** | L1/L4/L5 in `score_measured`; `test_l3_formal.py` + `test_verification_report.py` missing |
| **CP0** | HUD eval smoke | **Green (unit)** | `tests/test_hud_eval_smoke.py`; full live `hud eval` gated on MP3 run |
| **GEN** | FIFO second target | **Code landed** | `tests/test_gen_fifo.py`, `scripts/run_gen_fifo_wsl.sh` |

---

## Agent pools — what's on `main`

### Grok (G1–G10) — measured engine

| Component | Path | Status |
|-----------|------|--------|
| Keystone API | `cryobrain/accuracy/measured_ler.py` | Landed |
| RTL generator | `cryobrain/rtl_gen/generator.py` | Landed |
| Yosys metrics | `cryobrain/rtl_grader/synth_metrics.py` | Landed |
| L1 / L4 / L5 gates | `cryobrain/verify/l1_functional.py`, `l4_synth.py`, `l5_budget.py` | Landed |
| Score API | `cryobrain/grader/score.py` → `score_measured()` | Landed |
| Gates | `scripts/run_mp0_wsl.sh` … `run_mp2_wsl.sh` | WSL-green |

### Claude (C1–C10) — learning + sponsors + GEN

| ID | Deliverable | Path | Status |
|----|-------------|------|--------|
| **C1** | Measured memory store | `cryobrain/memory/store.py`, `models.py` | **Merged** (PR #9) |
| **C2** | Fireworks proposer | `cryobrain/rl/proposer.py`, `integrations/fireworks.py` | **Merged** (PR #9) |
| **C3** | Modal measure fan-out | `cryobrain/rl/modal_measure.py`, `modal_app.py` | **Merged** (PR #13) |
| **C4** | GRPO on measured reward | `cryobrain/rl/grpo.py`, `rollout.py` | **Merged** (PR #14) |
| **C5** | Measured local trainer | `cryobrain/rl/local_trainer.py`, `proposal_loop.py` | **Merged** (PR #9) |
| **C6** | Exa retrieval + context pack | `cryobrain/retrieval/context_pack.py` | **Merged** (PR #10) |
| **C7** | Daytona per-variant sandbox | `cryobrain/sandbox/measure_runner.py` | **Merged** (PR #11) |
| **C8** | HUD eval smoke | `tests/test_hud_eval_smoke.py` | **Merged** (PR #12) |
| **C9** | FIFO GEN second target | `tasks/async_fifo/`, `cryobrain/rtl_gen/fifo_generator.py` | **Merged** (PR #16) |
| **C10** | Measured Pareto + plots | `cryobrain/benchmark/pareto.py`, `plots.py` | **Merged** (PR #15) |

### Codex (X1–X10) — truth enforcement

| ID | Deliverable | Status |
|----|-------------|--------|
| **X1** | Proxy killer | **Done** — `tests/test_proxy_removed.py` |
| **X2** | CI anti-cheat guards | **Done** — `audit_reward_path.sh`, `test_no_proxy_ler_in_prod.py` |
| **X3** | SymbiYosys L3 formal | **Not started** — no `l3_formal.py` / `test_l3_formal.py` |
| **X4** | Keystone pytest | **Done** — `test_keystone_rule.py` (WSL) |
| **X5** | Artifact schema v2 | **Done** — `cryobrain/artifacts/schemas/v2/` |
| **X6** | Stim harness tests | **Done** — `cryobrain/stim/compare.py` + tests |
| **X7** | Verification report | **Not started** — no `verification_report.py` |
| **X8** | WSL runners | **Partial** — mp0/mp1/mp2 green; `run_mp5_wsl.sh` blocked on X3+X7 |
| **X9** | LER baselines + research | **Done** — `artifacts/baselines/ler_baselines.json`, `ECC_DECODER_METRICS.md` |
| **X10** | Integration gate | **Landed** — `tests/integration/test_measured_pipeline.py`; WSL acceptance needs re-verify |

**Codex completion: 7/10 done, 1 partial (X8), 2 not started (X3, X7).**

---

## Architecture (v5, post-consolidation)

| Layer | What it is | Key paths |
|-------|------------|-----------|
| **The chip** | Parametric synthesizable Verilog per `DesignConfig` | `cryobrain/rtl_gen/generator.py` |
| **The environment** | Measured grader: Verilator LER + Yosys + L1/L4/L5 | `cryobrain/grader/score.py`, hidden `grade.py` |
| **The AI** | Measured propose → generate → verify → measure → score → memory | `proposal_loop.py`, `local_trainer.py`, `memory/store.py` |
| **Training scale** | Modal fan-out + GRPO on measured reward | `modal_measure.py`, `grpo.py` |
| **Sponsors** | Fireworks proposer, Exa RAG, Daytona sandbox | `proposer.py`, `context_pack.py`, `measure_runner.py` |
| **GEN** | FIFO second RTL target in same env | `tasks/async_fifo/`, `fifo_loop.py` |
| **The demo** | Offline dashboard from JSON bundle | `scripts/build_demo.py` → `demo/index.html` |

Frozen APIs: [`docs/agents/INTERFACE_CONTRACTS.md`](agents/INTERFACE_CONTRACTS.md).

---

## Recent session wins (2026-06-21)

| Done | Detail |
|------|--------|
| **Branch consolidation** | PRs #5–#17 merged; all feature branches deleted; `main` is the only branch |
| **Claude C1–C10** | Memory, measured trainer, Fireworks, Modal, GRPO, Exa, Daytona, HUD smoke, Pareto, FIFO GEN |
| **Codex X4/X6/X9/X10** | Keystone WSL marker, stim compare, LER baselines, integration gate (PRs #1–#4) |
| **Proxy guard fix** | PR #17 — docstring cleanup after merge; guards green again |
| **Test suite growth** | 108 → **207** collected tests |
| **`.gitignore`** | `terminals/` scratch dir ignored (PR #5) |

### Prior session (2026-06-20)

| Done | Detail |
|------|--------|
| **Grok MP0–MP2** | Measured LER spine, parametric RTL, `score_measured` — WSL-green |
| **Proxy elimination** | `decoder_policy.py` removed; stim harness fail-closed to MWPM |
| **SPEC-v5 docs** | Versioned specs, 30-agent handoffs, reality audit |
| **Demo dashboard shell** | Offline `demo/index.html` (~46 KB) from proxy-era artifacts |

---

## Legacy era (SPEC v1–v4)

Before SPEC-v5, the repo shipped a **knob-sweep trainer** with **proxy** candidate LER. That produced real-looking climb/memory JSON but was not measured co-design. Legacy artifacts remain on disk for the demo; see [`SPEC_REALITY_AUDIT.md`](SPEC_REALITY_AUDIT.md).

| CP | Meaning | Status | Caveat for v5 |
|----|---------|--------|---------------|
| CP0 | HUD eval FIFO | Green | Still valid |
| CP1 | Stim MWPM harness | Green | Still valid |
| CP2–CP3 | Validity / calibration | Green | Superseded by measured layers |
| CP4 | RL climb | Green | **Proxy-era** — not MP3 |
| CP5 | Memory A/B | Green | **Proxy-era** — not MP4 |
| CP6–CP8 | Curriculum / waveform / FIFO | Green | FIFO scaffold extended by C9 GEN |

---

## Phase: Demo dashboard (offline shell — proxy sources)

| Component | Path | Status |
|-----------|------|--------|
| Template | `demo/dashboard.template.html` | Done |
| Bundle builder | `scripts/build_demo.py` | Green — reads `artifacts/*.json` |
| VCD export | `cryobrain/demo/vcd_export.py` | Green |
| Offline HTML | `demo/index.html` | Built (~46 KB) |

**Honesty caveat:** `build_demo.py` still sources proxy-era `climb_chart_rl.json`, `memory_ab_overlay.json`, `designs.json`. Truth-up requires running `run_c5_climb_wsl.sh` and pointing the builder at `measured_*.json`.

```bash
python scripts/build_demo.py
# open demo/index.html — fully offline
```

---

## Phase: Sponsors (integrated on `main`)

| Sponsor | Module | Status |
|---------|--------|--------|
| **HUD** | `env.py`, `tests/test_hud_eval_smoke.py` | Smoke green; full eval needs WSL measured climb |
| **Modal** | `cryobrain/rl/modal_measure.py`, `modal_app.py` | Fan-out code landed; live run needs Modal creds |
| **Fireworks** | `cryobrain/rl/proposer.py` | Proposer wired; `--fireworks` flag on trainer |
| **Exa** | `cryobrain/retrieval/context_pack.py` | Search + provenance pack; live test skips without key |
| **Daytona** | `cryobrain/sandbox/measure_runner.py` | Per-variant sandbox measure scaffold |
| **Antim Gizmo** | `integrations/antim.py` | Optional concept visual only |

Health: `python scripts/check_sponsors.py` · Keys in `.env` (gitignored).

---

## Artifacts

### On disk today

| File | Era | Used by demo? |
|------|-----|---------------|
| `climb_chart_*.json`, `designs*.json`, `memory_ab_overlay.json` | Proxy | Yes |
| `pareto.json` / `pareto.png` | Proxy | Indirect |
| `waveform.json`, `cryo_golden_trace.vcd` | Real sim | Yes |
| `demo_bundle.json` | Bundled | Source for `index.html` |
| `verified_memory.json` | Proxy-era tags | Trainer seed only |
| `baselines/ler_baselines.json` | **Measured** | Regression guard (Codex X9) |

### SPEC-v5 target (generate via WSL)

| File | Gate | Generator |
|------|------|-----------|
| `artifacts/measured_climb.json` | MP3 | `wsl bash scripts/run_c5_climb_wsl.sh` |
| `artifacts/measured_memory_ab.json` | MP4 | `local_trainer.py --memory-ab` (WSL) |
| `artifacts/measured_pareto.json` | MP4+ | `cryobrain/benchmark/pareto.py` |
| `artifacts/verification_report.json` | MP5 | Codex X7 (not started) |

Schema validation: `cryobrain/artifacts/schemas/v2/`.

---

## Git history (recent)

```
79490b3 fix: restore proxy guards after Claude branch consolidation (#17)
fc4032c feat: FIFO GEN second target (#16)
c0bbac3 feat: measured trainer + memory + Fireworks proposer (#9)
c94de11 test: measured LER baselines (#1)
328243a feat: Grok MP2 score_measured (G10)
a64efb8 feat: Grok MP0 measured LER spine (G3)
```

**Remote:** `git@github.com:ayushozha/CryoBrain.git` · default branch `main` · no open PRs

---

## How to run

```bash
# Measured milestones (WSL + OSS CAD required)
wsl bash scripts/run_mp0_wsl.sh
wsl bash scripts/run_mp1_wsl.sh
wsl bash scripts/run_mp2_wsl.sh

# Claude measured climb + artifacts (MP3/MP4)
wsl bash scripts/run_c5_climb_wsl.sh 5

# Codex baselines
wsl bash scripts/compute_ler_baselines_wsl.sh

# GEN FIFO (C9)
wsl bash scripts/run_gen_fifo_wsl.sh

# MP5 (blocked until Codex X3 + X7 land)
wsl bash scripts/run_mp5_wsl.sh

# Demo dashboard (Windows or WSL)
python scripts/build_demo.py

# Tests
uv run pytest -m "not wsl"    # fast unit suite (Windows)
uv run pytest                 # 207 tests (WSL tests need -m wsl + EDA)
python scripts/check_sponsors.py
```

See [`docs/EDA_WSL.md`](EDA_WSL.md) for toolchain setup.

---

## What's next (priority order)

1. **WSL artifact run** — `run_c5_climb_wsl.sh` → check in `measured_climb.json` + `measured_memory_ab.json` (**MP3/MP4 proof**).
2. **Demo truth-up** — Point `build_demo.py` at `measured_*.json`; show placeholder when missing.
3. **Codex X3** — SymbiYosys L3 formal (`l3_formal.py`, `test_l3_formal.py`).
4. **Codex X7** — `verification_report.json` generator + tests.
5. **Codex X8** — `run_mp5_wsl.sh` full L1–L5 gate once X3+X7 land.
6. **Live sponsor runs** — Modal GRPO + Fireworks proposer on a real measured climb.
7. **GEN WSL proof** — `run_gen_fifo_wsl.sh` green on golden FIFO RTL.

---

## One-line status

**CryoBrain** has a **full measured stack on `main`**: Grok MP0–MP2 green, Claude C1–C10 code merged, Codex guards/schemas/baselines landed. The **demo-ready measured story** still needs a **WSL climb run** to produce `measured_*.json`, plus **demo truth-up** and **Codex L3 formal** for MP5.

**Claim ladder:** candidate accuracy is **measured** (proven MP0); each design is **real synthesizable RTL** (MP1); reward is **measured-only** (MP2); learning climb and memory wins are **code-complete but not yet artifact-proven** (MP3/MP4); the offline dashboard **works** but climb/memory panels are still **proxy-era data**.