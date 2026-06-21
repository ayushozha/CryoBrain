# Handoff: Claude Pool (10 Agents)

**Orchestrator:** Claude Code  
**Canonical spec:** [`docs/specs/SPEC-v5.md`](../specs/SPEC-v5.md)  
**Master plan:** [`00-MASTER_PLAN.md`](./00-MASTER_PLAN.md)  
**Branch prefix:** `feat/v5-c{N}-<slug>`

---

## START HERE (read this if a human said “read this file”)

You have everything you need in this repo. Follow this section before touching code.

### Step 1 — Reading order (mandatory)

Read these files **in this order** before any implementation:

1. [`docs/specs/SPEC-v5.md`](../specs/SPEC-v5.md) — canonical requirements  
2. [`docs/SPEC_REALITY_AUDIT.md`](../SPEC_REALITY_AUDIT.md) — what is fake today  
3. [`00-MASTER_PLAN.md`](./00-MASTER_PLAN.md) — DAG, frozen interfaces, milestones  
4. **This file** — your pool’s 10 agent slots (sections C1–C10 below)

### Step 2 — Figure out your role

| Situation | What you do |
|-----------|-------------|
| Human said “read `HANDOFF-CLAUDE.md`” with **no slot** | You are the **Claude orchestrator**. Start **Wave 1** (C8 smoke only), then spawn subagents per [Orchestrator playbook](#orchestrator-playbook-claude) below. **Do not** launch full trainer/memory until Grok MP0/MP1 pass. |
| Human said “you are **C{N}**” or orchestrator assigned a slot | You are **Claude subagent C{N}**. Read **only** section **C{N}** below. |
| `from cryobrain.accuracy.measured_ler import measure_candidate_ler` fails | **Stop and wait** (except C8 smoke / C6 scaffold). Do not fork a local implementation — escalate to Grok G3. |

### Step 3 — Hard rules (every Claude agent)

- **Import** Grok APIs — never reimplement `measure_candidate_ler`, `generate_rtl`, `synth_metrics`, `score_measured`.  
- **Do not** edit `demo/`, dashboard, or Grok-owned paths (`cryobrain/accuracy/measured_ler.py`, `cryobrain/rtl_gen/`, `cryobrain/grader/score.py`).  
- **Do not** put `decoder_quality_multiplier` or formula LER into `artifacts/measured_*.json`.  
- **Sponsor calls must be real** when API keys exist; skip tests when keys missing — never fake responses in prod paths.  
- **One branch per slot:** `feat/v5-c{N}-<short-slug>`.  
- **Done** = section acceptance passes + artifacts validate against Codex X5 schemas when they exist.

### Step 4 — Wave order (do not launch all 10 at once)

| Wave | Slots | Start when | Wait for Grok |
|------|-------|------------|---------------|
| **1** | **C8** (smoke: imports, tool schema) | Immediately | None |
| **1b** | C6 scaffold, C1 schema draft | Parallel with Wave 1 | None |
| **2** | **C1**, **C5**, C2, C7 | **MP1** passed (`run_mp1_wsl.sh`) | G3, G4, G5, G10 |
| **3** | **C3**, **C4**, C10 | **MP2** passed | G10 `score_measured` |
| **4** | C9 (GEN FIFO) | **MP3** passed | Full decoder loop |
| **5** | C8 full CP0, C10 pareto finalize | MP3 + memory rows | L1–L5 stack |

**Orchestrator default:** if unsure, start with **C8 smoke**, then poll MP0/MP1 before assigning C5/C1.

### Orchestrator playbook (Claude)

When acting as orchestrator with 10 parallel subagents:

1. **Wave 1:** C8 smoke + C6 scaffold + C1 models-only (no measured loop).  
2. **Block** C5, C2, C3, C4, C7, C10 on Grok MP0 — check `wsl bash scripts/run_mp0_wsl.sh`.  
3. **Block** full C1/C5 integration on Grok MP1 — check `wsl bash scripts/run_mp1_wsl.sh`.  
4. After MP1: launch **C1 + C5 + C2 + C7** in parallel.  
5. After MP2: launch **C3 + C4**; then **C10**.  
6. After MP3: launch **C9**; finish **C8** CP0.

Subagent spawn text (orchestrator copies per slot):

```
You are Claude agent C{N} for CryoBrain SPEC-v5.
Read in order: docs/specs/SPEC-v5.md, docs/agents/00-MASTER_PLAN.md, docs/agents/HANDOFF-CLAUDE.md section C{N} only.
Branch: feat/v5-c{N}-<slug>. Own only paths listed in C{N}.
IMPORT Grok APIs — never implement measure_candidate_ler / generate_rtl / synth_metrics / score_measured.
If imports fail and you are not C8/C6 scaffold: stop and report blocker (Grok MP0/MP1).
NON-GOALS: demo/, dashboard, fake sponsor data, decoder_quality_multiplier.
Done when: <paste Acceptance block from section C{N}>.
```

### What the human can say (copy-paste)

**To Claude orchestrator (minimum):**

> Read `docs/agents/HANDOFF-CLAUDE.md` and execute it. You are the Claude orchestrator — follow START HERE and wave order. Wait for Grok MP0/MP1 before trainer/memory work.

**To a single Claude subagent:**

> Read `docs/agents/HANDOFF-CLAUDE.md`. You are Claude agent **C8**. Execute only section C8.

---

## Pool Mission

Claude owns **learning loop, memory, sponsor integrations, HUD eval, GEN second target, and measured artifacts** for benchmarks. You **consume** Grok's frozen APIs (`measure_candidate_ler`, `generate_rtl`, `synth_metrics`, `score_measured`) — never reimplement them.

**Non-goals:** Demo dashboard polish, Gizmo, PDFs, proxy LER, formula `npu_cost` as reward, fake API responses in production paths.

---

## You Consume (Do Not Reimplement)

```python
from cryobrain.accuracy.measured_ler import measure_candidate_ler
from cryobrain.rtl_gen.generator import generate_rtl
from cryobrain.rtl_grader.synth_metrics import synth_metrics
from cryobrain.grader.score import score_measured
```

**Block on Grok** if any import fails — do not fork alternate implementations.

---

## Memory Record Schema (Claude C1 Owns)

```json
{
  "rtl_path": "artifacts/variants/step_012_parallel.sv",
  "design": { "...DesignConfig..." },
  "measurement": { "candidate_ler": 0.017, "mwpm_ler": 0.022, "suppression": 0.23 },
  "synth": { "area_um2": 6.1, "latency_cycles": 8 },
  "verification": { "layers": ["L1","L2","L4","L5"], "passed": true },
  "provenance": { "step": 12, "backend": "verilator+stim+yosys" }
}
```

---

## Measured Artifacts (Real Data Only)

| File | Owner | Required fields |
|------|-------|-----------------|
| `artifacts/measured_climb.json` | C5/C4 | `history[].{step, candidate_ler, suppression, rtl_hash}` |
| `artifacts/measured_pareto.json` | C10 | `points[].{label, ler, area_um2, latency_cycles, rtl_path}` |
| `artifacts/measured_memory_ab.json` | C5 | two series from **measured** runs only |
| `artifacts/verification_report.json` | Codex X7 (consumer: C5) | per-layer pass/fail |

**Forbidden:** `decoder_quality_multiplier` results in any artifact after MP0.

---

## Agent Roster

| ID | Name | Milestone | Parallel group |
|----|------|-----------|----------------|
| C1 | **Memory Store** | MP2 | PG-MEM |
| C2 | **Fireworks Proposer** | MP2–MP3 | PG-SPONSOR |
| C3 | **Modal Fan-Out** | MP3 | PG-TRAIN |
| C4 | **GRPO Trainer** | MP3 | PG-TRAIN |
| C5 | **Local Trainer Rewrite** | MP2–MP4 | PG-TRAIN |
| C6 | **Exa Retrieval** | MP2 | PG-SPONSOR |
| C7 | **Daytona Sandboxes** | MP2–MP3 | PG-SPONSOR |
| C8 | **HUD Eval (CP0)** | MP0+ (smoke) / MP3 (full) | PG-HUD |
| C9 | **GEN FIFO Target** | MP4+ | PG-GEN |
| C10 | **Pareto + Benchmarks** | MP3–MP5 | PG-BENCH |

---

## C1 — Memory Store

**Mission:** Persist measured variants — RTL hash, design, LER, synth, verification. No formula scores.

**Owns:**
- `cryobrain/memory/store.py`
- `cryobrain/memory/models.py`
- `cryobrain/memory/schema.sql` (if SQL)
- `tests/test_memory_store.py`

**Inputs:** Grok measurement + synth outputs  
**Outputs:** `record_variant()`, `best_holdout()`, `query_pareto_candidates()`

**Acceptance:**
```bash
pytest tests/test_memory_store.py -q
# Round-trip golden fixture; holdout LER column sourced from measure_candidate_ler only
```

**Blockers:** MP1 (Grok G3/G4/G5)  
**Parallel with:** C6 scaffold

---

## C2 — Fireworks Proposer

**Mission:** Real Fireworks API proposes `DesignConfig` / RTL edits — structured JSON, retries, no mocked prod responses.

**Owns:**
- `cryobrain/integrations/fireworks.py` (harden)
- `cryobrain/rl/proposer.py`
- `tests/test_fireworks_proposer.py` (skip without `FIREWORKS_API_KEY`)

**Inputs:** C1 memory context; G9 DesignConfig  
**Outputs:** `propose_next_design(memory_snapshot) -> DesignConfig`

**Acceptance:** With key: one live call returns valid schema; without key: import + skip

**Blockers:** C1 schema; MP2  
**Parallel with:** C6, C7

---

## C3 — Modal Fan-Out

**Mission:** Parallel Verilator measurement jobs on Modal — real `modal_train.py` image, not pretend GPU.

**Owns:**
- `cryobrain/rl/modal_measure.py`
- `cryobrain/rl/modal_app.py`
- `scripts/launch_modal_measure.sh`

**Inputs:** G3 measure API; Modal token  
**Outputs:** Batch measure N RTL paths → JSON results

**Acceptance:**
```bash
modal run cryobrain/rl/modal_measure.py --dry-run
# 1 variant measured end-to-end with real LER in output
```

**Blockers:** MP0; G3 stable  
**Parallel with:** C4 prep

---

## C4 — GRPO Trainer

**Mission:** GRPO weight updates on Modal using **measured** reward only — real climb of measured suppression.

**Owns:**
- `cryobrain/rl/modal_train.py`
- `cryobrain/rl/grpo.py`
- `cryobrain/rl/rollout.py`
- `tests/test_grpo_measured.py`

**Inputs:** C2 proposer; C3 fan-out; C5 reward wiring; `score_measured`  
**Outputs:** Checkpoints in `artifacts/checkpoints/` referencing memory rows

**Acceptance:**
```bash
pytest tests/test_grpo_measured.py -q
# Integration: 1 GRPO step; reward_fn calls measure path (mock count in unit test)
```

**Blockers:** MP2; C5  
**Parallel with:** C3

---

## C5 — Local Trainer Rewrite

**Mission:** Replace preset knob sweep in `local_trainer.py` with measured loop: propose → generate_rtl → verify → measure → score → memory.

**Owns:**
- `cryobrain/rl/local_trainer.py`
- `cryobrain/rl/proposal_loop.py`
- `artifacts/measured_climb.json` (generator)
- `artifacts/measured_memory_ab.json`
- `tests/test_local_trainer_measured.py`

**Inputs:** C1, C2, Grok G4/G10  
**Outputs:** CLI `--steps N` writes memory + climb artifact

**Acceptance:**
```bash
python -m cryobrain.rl.local_trainer --steps 5
pytest tests/test_local_trainer_measured.py -q
# MP3: climb artifact shows measured suppression trend (not proxy)
```

**Blockers:** MP1 + G10  
**Parallel with:** C1 integration

---

## C6 — Exa Retrieval

**Mission:** Real Exa search seeds memory with cited RTL/papers context for proposals.

**Owns:**
- `cryobrain/integrations/exa.py`
- `cryobrain/retrieval/context_pack.py`
- `tests/test_exa_integration.py`

**Inputs:** `EXA_API_KEY`  
**Outputs:** `fetch_decoder_context(query) -> list[{url, snippet}]`

**Acceptance:** Live search returns ≥1 result; URLs stored in provenance

**Blockers:** None for scaffold  
**Parallel with:** C2, C7

---

## C7 — Daytona Sandboxes

**Mission:** Real Daytona SDK — fork measurement workdir per variant; destroy after run.

**Owns:**
- `cryobrain/integrations/daytona.py`
- `cryobrain/sandbox/measure_runner.py`
- `tests/test_daytona_integration.py`

**Inputs:** `DAYTONA_API_KEY`; G3 semantics  
**Outputs:** `measure_in_sandbox(rtl_path, scenario) -> dict` matching local LER within ε

**Acceptance:** create → measure → destroy; no fake sandbox IDs

**Blockers:** MP0  
**Parallel with:** C3, C6

---

## C8 — HUD Eval (CP0)

**Mission:** `hud eval` green on measured `env.py` tools — CP0 checkpoint.

**Owns:**
- `cryobrain/hud/env.py`
- `cryobrain/hud/tools.py`
- `tests/test_hud_eval_smoke.py`

**Inputs:** `score_measured`; Grok grade path  
**Outputs:** HUD tools call real measure/synth — no proxy in tool responses

**Acceptance:**
```bash
# Phase 0 smoke: imports + tool schema without full MP3
hud eval cryobrain/hud/env.py --smoke   # when MP3 ready
pytest tests/test_hud_eval_smoke.py -q
```

**Blockers:** MP0 for full path; smoke can start early (Phase 0 per master DAG)  
**Parallel with:** Codex X1 (independent smoke)

---

## C9 — GEN FIFO Target

**Mission:** Second RTL target (async FIFO) — same env optimizes non-decoder block (SPEC-v5 GEN).

**Owns:**
- `tasks/async_fifo/`
- `cryobrain/rtl_gen/fifo_generator.py`
- `cryobrain/stim/fifo_stim.py`
- `tests/test_gen_fifo.py`

**Inputs:** Grok generator patterns; measured metric for FIFO (throughput/latency from sim)  
**Outputs:** FIFO variants in memory with measured scores

**Acceptance:**
```bash
pytest tests/test_gen_fifo.py -m wsl -q
# MP4 GEN gate: optimizer improves FIFO measured metric over steps
```

**Blockers:** MP3 decoder loop stable  
**Parallel with:** Codex X3 formal for FIFO (optional)

---

## C10 — Pareto + Benchmarks

**Mission:** `measured_pareto.json`, benchmark plots — y-axes labeled "measured LER (Verilator)" only.

**Owns:**
- `cryobrain/benchmark/pareto.py`
- `cryobrain/benchmark/plots.py`
- `artifacts/measured_pareto.json`
- `tests/test_measured_pareto.py`

**Inputs:** C1 memory; Grok G5 synth  
**Outputs:** Pareto points with `rtl_path` + measured fields

**Acceptance:**
```bash
pytest tests/test_measured_pareto.py -q
python -m cryobrain.benchmark.pareto --emit artifacts/measured_pareto.json
# No npu_cost-only points in output
```

**Blockers:** MP2 memory populated  
**Parallel with:** Codex X9 research citations on plots

---

## Sequenced Execution

```
Phase 0 (hour 0–4):
  C8 HUD smoke only (no proxy dependency)

Phase 1–2 (hour 4–24):
  Wait for Grok MP0/MP1
  C1 schema + store scaffold

Phase 3 (hour 24–40):
  C5 + C2 + C6 + C7 parallel → MP2
  C3 + C4 → MP3
  C10 after memory has rows

Phase 4 (hour 40+):
  C9 GEN FIFO
  C8 full CP0
  C10 + MP4 memory A/B artifact
```

---

## Sponsor Map

| Sponsor | Agent | Real role |
|---------|-------|-----------|
| HUD | C8 | `env.py` tools → measured score |
| Modal | C3, C4 | Parallel measure + GRPO |
| Fireworks | C2, C4 | Propose designs + policy |
| Exa | C6 | Literature → memory seed |
| Daytona | C7 | Per-variant sandbox measure |

**Skip:** Antim Gizmo, demo-only wiring.

---

## Escalation

| Issue | Escalate to |
|-------|-------------|
| measure_candidate_ler missing | Grok G3 |
| Trainer still preset sweep | C5 — P0 bug |
| Artifact has proxy LER | Codex X2 + C5 |
| Modal image import fail | C3 + C4 |

---

## Subagent Prompt Template

```
You are Claude agent C{N} for CryoBrain SPEC-v5.
Read: docs/specs/SPEC-v5.md, docs/agents/HANDOFF-CLAUDE.md (section C{N}).
Branch: feat/v5-c{N}-<slug>
Import Grok APIs only — never reimplement measure/generate/synth/grade.
NON-GOALS: demo/, dashboard, fake data, decoder_quality_multiplier.
Acceptance: <paste from section C{N}>
Artifacts must use measured fields only.
```