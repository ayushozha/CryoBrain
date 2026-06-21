# CryoBrain — Progress Summary

**Last updated:** 2026-06-20
**Repo:** https://github.com/ayushozha/CryoBrain
**Branch:** `main` (published)
**Canonical spec:** [`docs/specs/SPEC-v5.md`](specs/SPEC-v5.md)
**Reality audit:** [`SPEC_REALITY_AUDIT.md`](SPEC_REALITY_AUDIT.md)
**Agent orchestration:** [`docs/agents/README.md`](agents/README.md)

---

## North star (SPEC-v5)

CryoBrain is a **measured** verifiable RL environment for cryogenic QEC decoder co-design:

1. **P0** — Candidate LER from Stim vectors → Verilator RTL (no proxy formulas).
2. **P1** — Parametric RTL generator + per-variant Yosys metrics.
3. **P2** — Model proposes designs; reward-ranked learning + memory; GRPO on Modal.
4. **L1–L5** — Verification stack gates every score.
5. **GEN** — Same env on a second RTL target (FIFO) for platform proof.

**Keystone rule:** worse RTL → worse measured LER. No `decoder_quality_multiplier` in production paths.

---

## Status at a glance

| Area | Status | Notes |
|------|--------|-------|
| **SPEC-v5 measured spine (Grok)** | **MP0–MP2 green** | `measure_candidate_ler`, `synth_metrics`, `score_measured` |
| **Proxy LER** | **Removed** | `decoder_policy.py` deleted; CI guards in place |
| **Parametric RTL** | **Skeleton + MP1** | `cryobrain/rtl_gen/generator.py` — 3 presets → distinct area+LER |
| **Verification layers** | **L1, L4, L5 landed** | L3 formal (Codex) pending for MP5 |
| **Learning loop (Claude)** | **Not on measured path yet** | `local_trainer.py` still knob-sweep era |
| **Measured artifacts (demo)** | **Not regenerated** | No `measured_*.json` yet — see artifact table below |
| **Demo dashboard** | **Offline shell green** | `build_demo.py` bundles proxy-era climb/memory into `demo/index.html` (~46 KB) |
| **GitHub** | **Published** | `ayushozha/CryoBrain` public, `main` pushed |
| **HUD / sponsors** | **Scaffolded** | CP0 green; Fireworks/Exa/Daytona/Modal wired, not full measured loop |
| **Tests** | **108 pytest** | Includes MP0–MP2 keystone, proxy guards, artifact schemas |

**Overall (SPEC-v5 definition of done): ~40%** — measured spine through MP2 + offline demo shell; measured trainer, measured artifacts, and MP5 remain.

---

## SPEC-v5 milestones (measured)

| ID | Gate | Status | Evidence |
|----|------|--------|----------|
| **MP0** | Worse `.sv` → worse measured LER | **Green (WSL)** | `wsl bash scripts/run_mp0_wsl.sh` |
| **MP1** | 3 configs → 3 distinct (area, LER) | **Green (WSL)** | `wsl bash scripts/run_mp1_wsl.sh` |
| **MP2** | Reward only on measured change | **Green (WSL)** | `wsl bash scripts/run_mp2_wsl.sh` |
| **MP3** | Measured climb (not proxy) | **Not started** | Needs Claude C5 trainer on `score_measured` |
| **MP4** | Memory A/B on measured runs | **Not started** | Needs measured trainer + `measured_memory_ab.json` |
| **MP5** | L1–L5 all gate score | **Partial** | L1/L4/L5 in `score_measured`; L3 formal + `test_l3_formal.py` pending |
| **CP0** | HUD eval green | **Green (WSL)** | [HUD job](https://hud.ai/jobs/d5e730a977f04df59875afd1f3c022ba) |
| **GEN** | FIFO second target | **Not started** | Claude C9 / scaffold only |

---

## What landed in the measured engine (Grok, MP0–MP2)

### P0 — measured accuracy

| Component | Path |
|-----------|------|
| Keystone API | `cryobrain/accuracy/measured_ler.py` |
| Types | `cryobrain/accuracy/types.py` |
| Stim manifest | `cryobrain/stim/manifest.py`, `tasks/cryo_brain_decoder/stim/` |
| Tests | `tests/test_keystone_rule.py`, `tests/test_measured_ler.py` |
| Gate | `scripts/run_mp0_wsl.sh` |

### P1 — RTL + per-variant synth

| Component | Path |
|-----------|------|
| RTL generator | `cryobrain/rtl_gen/generator.py` |
| DesignConfig space | `cryobrain/design/config.py`, `validators.py` |
| Yosys metrics | `cryobrain/rtl_grader/synth_metrics.py` |
| Staging helper | `cryobrain/rtl_grader/stage.py` |
| L1 / L4 / L5 gates | `cryobrain/verify/l1_functional.py`, `l4_synth.py`, `l5_budget.py` |
| Gate | `scripts/run_mp1_wsl.sh` |

### P2 — measured grading

| Component | Path |
|-----------|------|
| Score API | `cryobrain/grader/score.py` → `score_measured()` |
| Hidden grader | `tasks/cryo_brain_decoder/donotaccess/grade.py` (imports `score_measured` only) |
| Proxy kill + CI | `tests/test_no_proxy_ler_in_prod.py`, `scripts/audit_reward_path.sh` |
| Gate | `scripts/run_mp2_wsl.sh` |

### Interface contract

Frozen APIs documented in [`docs/agents/INTERFACE_CONTRACTS.md`](agents/INTERFACE_CONTRACTS.md).

---

## Architecture (updated for v5)

| Layer | What it is | Artifact (today) |
|-------|------------|------------------|
| **The chip** | Parametric synthesizable Verilog per `DesignConfig` | `cryobrain/rtl_gen/generator.py` → `.sv` |
| **The environment** | Measured grader: Verilator LER + Yosys + L1/L4/L5 | `cryobrain/grader/score.py`, hidden `grade.py` |
| **The AI** | RL loop + memory + sponsors (needs measured rewire) | `local_trainer.py`, `modal_train.py` |
| **The demo** | Offline dashboard from JSON bundle | `scripts/build_demo.py` → `demo/index.html` |

---

## Recent session wins (2026-06-20)

| Done | Detail |
|------|--------|
| **SPEC-v5 docs** | Versioned specs, 30-agent handoffs, reality audit, interface contracts |
| **Grok MP0–MP2** | Measured LER spine, parametric RTL, `score_measured` grading — all WSL-green |
| **Proxy elimination** | `decoder_policy.py` removed; `stim_harness.py` fail-closed to MWPM only |
| **GitHub publish** | `ayushozha/CryoBrain` public on `main` |
| **Demo dashboard shell** | `dashboard.template.html` + `build_demo.py` → offline `demo/index.html` (~46 KB) |
| **VCD → waveform** | `cryobrain/demo/vcd_export.py` exports 5 signals from golden trace |
| **Memory A/B refresh** | WSL re-ran `climb_chart_no_memory.json` / `climb_chart_memory.json` / overlay |
| **Legacy CP gates** | CP2/CP3/CP5/CP6/CP7 green in WSL; grade.py wired to real Stim MWPM LER |

---

## Legacy era (SPEC v1–v4) — still in repo, not the demo story

Before SPEC-v5, the repo shipped a **knob-sweep trainer** against a **static** `cryo_brain_decoder.sv` with **proxy** candidate LER (`decoder_policy.py`). That produced real-looking climb/memory JSON but was **not** measured co-design. See [`SPEC_REALITY_AUDIT.md`](SPEC_REALITY_AUDIT.md).

### Historical checkpoints (proxy era — WSL green)

| CP | Meaning | Status | Caveat for v5 |
|----|---------|--------|---------------|
| CP0 | HUD eval FIFO | Green | Still valid |
| CP1 | Stim MWPM harness | Green | Still valid |
| CP2 | Validity gate | Green | Now superseded by `score_measured` layers |
| CP3 | Calibration band | Green | Pre-measured reward band |
| CP4 | RL climb | Green | **Proxy-era** — not MP3 |
| CP5 | Memory A/B | Green | **Proxy-era** — not MP4 |
| CP6 | Curriculum d=3→5→7 | Green | Curriculum code exists |
| CP7/CP8 | Waveform / FIFO fallback | Green | Still valid |

> Repo script naming: `check_cp5.py` = waveform/synth (SPEC2 CP7); `check_cp7.py` = FIFO (SPEC2 CP8); `check_cp5_memory.py` = memory A/B.

---

## Phase: Documentation & orchestration

| Deliverable | Status |
|-------------|--------|
| Versioned specs (`docs/specs/`) | Done — **SPEC-v5 canonical** |
| Multi-agent handoffs (30 agents) | Done — Grok / Claude / Codex |
| `SPEC_REALITY_AUDIT.md` | Done — spec vs gimmick gap |
| `INTERFACE_CONTRACTS.md` | Done — frozen APIs |
| GitHub `ayushozha/CryoBrain` | Done — public, `main` |

**Kickoff one-liners for agents:**

```
Read docs/agents/HANDOFF-GROK.md and execute it.
Read docs/agents/HANDOFF-CLAUDE.md and execute it.
Read docs/agents/HANDOFF-CODEX.md and execute it.
```

---

## Phase: Demo dashboard (offline shell — proxy sources)

| Component | Path | Status |
|-----------|------|--------|
| Template | `demo/dashboard.template.html` | Done |
| Bundle builder | `scripts/build_demo.py` | Green — reads `artifacts/*.json` |
| VCD export | `cryobrain/demo/vcd_export.py` | Green — 5 signals from golden trace |
| Offline HTML | `demo/index.html` | Built (~46 KB, no server needed) |
| Bundle JSON | `artifacts/demo_bundle.json` | Generated |

**Honesty caveat:** `build_demo.py` still sources `climb_chart_rl.json`, `memory_ab_overlay.json`, and `designs.json` — all **proxy-era**. The dashboard renders correctly but does **not** yet read `measured_*.json`. Truth-up is blocked on MP3/MP4 artifacts.

```bash
python scripts/build_demo.py          # rebuild demo/index.html from artifacts/
# open demo/index.html in browser — fully offline
```

---

## Phase: Sponsors (scaffold — not yet on measured loop)

| Sponsor | Module | Status |
|---------|--------|--------|
| **HUD** | `env.py`, `grader.py` | CP0 green; decoder task needs measured eval refresh |
| **Modal** | `modal_train.py` | Image ready; no measured GRPO run yet |
| **Fireworks** | `integrations/fireworks.py` | API hook; not driving RTL proposals in trainer |
| **Exa** | `integrations/exa_rag.py` | Works; seeded proxy-era memory tags |
| **Daytona** | `integrations/daytona.py` | Scaffold |
| **Antim Gizmo** | `integrations/antim.py` | Optional concept visual only |

Health: `python scripts/check_sponsors.py` · Keys in `.env` (gitignored).

---

## Artifacts

### On disk today (local `artifacts/` — mostly proxy-era)

| File | Size | Era | Used by demo? |
|------|------|-----|---------------|
| `climb_chart_rl.json` | ~10 KB | Proxy | Yes (climb panel) |
| `climb_chart_no_memory.json` | ~10 KB | Proxy | Yes (memory A/B) |
| `climb_chart_memory.json` | ~10 KB | Proxy | Yes (memory A/B) |
| `memory_ab_overlay.json` | ~0.4 KB | Proxy | Yes (memory summary) |
| `designs.json` / `designs_rl.json` | ~3–5 KB | Proxy | Yes (pareto panel) |
| `pareto.json` / `pareto.png` | ~3–89 KB | Proxy | Indirect |
| `waveform.json` | ~19 KB | Real VCD | Yes (waveform panel) |
| `demo_bundle.json` | ~38 KB | Bundled | Source for `index.html` |
| `cryo_golden_trace.vcd` | ~6 KB | Real sim | VCD source |
| `verified_memory.json` | ~18 KB | Proxy-era tags | No (trainer memory) |

### SPEC-v5 target (not yet generated)

| File | Panel / use |
|------|-------------|
| `artifacts/measured_climb.json` | Demo climb (MP3) |
| `artifacts/measured_memory_ab.json` | Memory A/B (MP4) |
| `artifacts/measured_pareto.json` | Pareto (real Yosys area) |
| `artifacts/invalid_vs_valid.json` | Honesty flash (wrong → reward 0) |

Schema validation: `cryobrain/artifacts/schemas/v2/` (Codex X5).

---

## Git history (recent)

```
2c3bada chore: proxy removal, artifact schemas, README links for GitHub publish
328243a feat: Grok MP2 score_measured rewires grade off proxy (G10)
d8660da feat: Grok MP1 synth metrics, verify layers, parametric RTL (G4-G8)
a64efb8 feat: Grok MP0 measured LER spine (G1-G4, G9, G3)
e51aa97 docs: SPEC-v5 archive and 30-agent orchestration handoffs
88c3d5c docs: spec vs reality audit
3cee7e2 feat: offline live demo dashboard (WS7)
```

**Remote:** `git@github.com:ayushozha/CryoBrain.git` · default branch `main`

---

## How to run

```bash
# Measured milestones (WSL + OSS CAD required)
wsl bash scripts/run_mp0_wsl.sh   # MP0 keystone
wsl bash scripts/run_mp1_wsl.sh   # MP1 synth + variants
wsl bash scripts/run_mp2_wsl.sh   # MP2 score_measured + proxy guard

# Demo dashboard (Windows or WSL)
python scripts/build_demo.py      # rebuild offline demo/index.html

# Legacy checkpoints (still useful)
wsl bash scripts/run_cp0_wsl.sh
wsl bash scripts/run_cp4_wsl.sh --steps 12   # proxy-era climb — not MP3
wsl bash scripts/run_memory_ab_wsl.sh        # proxy-era memory A/B

# Tests + sponsors
uv run pytest                     # 108 tests
python scripts/check_sponsors.py
```

See [`docs/EDA_WSL.md`](EDA_WSL.md) for toolchain setup.

---

## What's next (priority order)

1. **Claude C5** — Rewire `local_trainer.py` to `generate_rtl` → `score_measured` → memory; emit `measured_climb.json` (**MP3**).
2. **Claude C5/C10** — Measured memory A/B + pareto artifacts (**MP4**).
3. **Demo truth-up** — Point `build_demo.py` at `measured_*.json` only; show "awaiting artifact" when missing.
4. **Codex X3** — SymbiYosys L3 in `layers_passed` + `test_l3_formal.py` (**MP5**).
5. **Claude C3/C4** — Modal + Fireworks GRPO on measured reward.
6. **Claude C9** — FIFO GEN platform proof.

---

## One-line status

**CryoBrain** has a **real measured spine** (MP0–MP2): Verilator LER, per-variant Yosys, and `score_measured` grading with proxy LER dead. An **offline demo dashboard** renders proxy-era climb/memory/waveform artifacts honestly labeled as pre-MP3. The **demo-ready measured story** still needs a **measured trainer run** (MP3/MP4) and dashboard truth-up.

**Claim ladder tonight:** candidate accuracy is **measured**; each design is **real synthesizable RTL**; the offline dashboard **works** but climb/memory panels are **not yet measured**; learning climb and memory wins are **not claimable** until MP3/MP4 artifacts exist.
