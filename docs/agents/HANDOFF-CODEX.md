# Handoff: Codex Pool (10 Agents)

**Orchestrator:** OpenAI Codex CLI  
**Canonical spec:** [`docs/specs/SPEC-v5.md`](../specs/SPEC-v5.md)  
**Master plan:** [`00-MASTER_PLAN.md`](./00-MASTER_PLAN.md)  
**Branch prefix:** `feat/v5-x{N}-<slug>`

---

## START HERE (read this if a human said “read this file”)

You have everything you need in this repo. Follow this section before touching code.

### Step 1 — Reading order (mandatory)

Read these files **in this order** before any implementation:

1. [`docs/specs/SPEC-v5.md`](../specs/SPEC-v5.md) — canonical requirements  
2. [`docs/SPEC_REALITY_AUDIT.md`](../SPEC_REALITY_AUDIT.md) — what is fake today; kill list  
3. [`00-MASTER_PLAN.md`](./00-MASTER_PLAN.md) — DAG, frozen interfaces, milestones, path ownership  
4. **This file** — your pool’s 10 agent slots (sections X1–X10 below)

### Step 2 — Figure out your role

| Situation | What you do |
|-----------|-------------|
| Human said “read `HANDOFF-CODEX.md`” with **no slot** | You are the **Codex orchestrator**. Run **Wave 1** yourself (X1), then spawn subagents per [Orchestrator playbook](#orchestrator-playbook-codex) below. |
| Human said “you are **X{N}**” or orchestrator assigned a slot | You are **Codex subagent X{N}**. Read **only** section **X{N}** below. Do not implement other slots. |
| Grok APIs (`measure_candidate_ler`, etc.) do not exist yet | Expected early on. **X1, X2, X5, X8 stubs, X4 tests** can proceed. Do **not** implement those APIs — that is Grok G3/G4/G5. |

### Step 3 — Hard rules (every Codex agent)

- **Do not** implement `measure_candidate_ler`, `generate_rtl`, `synth_metrics`, or `score_measured` — test and guard Grok’s implementations.  
- **Do not** edit `demo/`, dashboard, or write fake LER / `decoder_quality_multiplier` into artifacts.  
- **Do not** edit Claude-owned paths (`cryobrain/memory/`, `cryobrain/rl/local_trainer.py`) except tests.  
- **One branch per slot:** `feat/v5-x{N}-<short-slug>`.  
- **EDA proof runs in WSL** — use `scripts/run_mp0_wsl.sh`, not Windows-native Verilator.  
- **Done** = your section’s acceptance commands pass + `mesh.log_action` or PR note if mesh unavailable.

### Step 4 — Wave order (do not launch all 10 at once)

| Wave | Slots | Start when | Blocks |
|------|-------|------------|--------|
| **1** | **X1**, X2, X5, X8 (stubs OK) | Immediately | Everyone (proxy must die) |
| **2** | **X4**, X6, X9 | Grok G3 has minimal `measure_candidate_ler` | MP0 |
| **3** | X8 (mp1), X10 | Grok G4/G5 land | MP1 |
| **4** | X7, X10 (full) | Grok G10 + Claude C5 | MP2 |
| **5** | X3, X8 (mp5) | MP3 stable | MP5 |

**Orchestrator default:** if unsure which slot to run, start with **X1 (Proxy Killer)**.

### Orchestrator playbook (Codex)

When acting as orchestrator with 10 parallel subagents:

1. Run **X1** first (or assign subagent X1) — nothing else merges until proxy is dead.  
2. Launch **X2 + X5 + X8** in parallel with X1.  
3. Poll Grok **G3**; when `measure_candidate_ler` stub works, launch **X4 + X6**.  
4. After MP0 green (`wsl bash scripts/run_mp0_wsl.sh`), launch **X9**.  
5. After MP1, launch **X10**; after MP2, **X7**; after MP3, **X3**.  
6. Each subagent: branch `feat/v5-x{N}-…`, owned paths only, acceptance block from section X{N}.

Subagent spawn text (orchestrator copies per slot):

```
You are Codex agent X{N} for CryoBrain SPEC-v5.
Read in order: docs/specs/SPEC-v5.md, docs/SPEC_REALITY_AUDIT.md, docs/agents/00-MASTER_PLAN.md, docs/agents/HANDOFF-CODEX.md section X{N} only.
Branch: feat/v5-x{N}-<slug>. Own only paths listed in X{N}.
Do NOT implement measure_candidate_ler / generate_rtl / synth_metrics (Grok owns those).
NON-GOALS: demo/, dashboard, fake LER, decoder_quality_multiplier.
Done when: <paste Acceptance block from section X{N}>.
```

### What the human can say (copy-paste)

**To Codex orchestrator (minimum):**

> Read `docs/agents/HANDOFF-CODEX.md` and execute it. You are the Codex orchestrator — follow START HERE and the wave order.

**To a single Codex subagent:**

> Read `docs/agents/HANDOFF-CODEX.md`. You are Codex agent **X1**. Execute only section X1.

---

## Pool Mission

Codex owns **proxy elimination, CI guards, keystone tests, artifact schema, SymbiYosys formal, WSL runners, and integration gates**. You are the **truth enforcement layer** — if proxy LER sneaks back, your tests must fail before merge.

**Non-goals:** Dashboard, demo HTML, PDFs, mocked EDA, synthetic LER tables, implementing `measure_candidate_ler` (that's Grok G3).

---

## You Do NOT Own (Import / Test Only)

| API | Owner |
|-----|-------|
| `measure_candidate_ler` | Grok G3 |
| `generate_rtl` | Grok G4 |
| `synth_metrics` | Grok G5 |
| `score_measured` | Grok G10 |
| Memory / trainer | Claude C1/C5 |

Codex **tests and guards** these — does not fork alternate implementations.

---

## Agent Roster

| ID | Name | Milestone | Parallel group |
|----|------|-----------|----------------|
| X1 | **Proxy Killer** | MP0 | — |
| X2 | **CI Anti-Cheat Guard** | MP0–MP5 | PG-GUARD |
| X3 | **SymbiYosys L3 Formal** | MP4–MP5 | PG-FORMAL |
| X4 | **Keystone Pytest** | MP0 | PG-TEST |
| X5 | **Artifact Schema v2** | MP0 | PG-SCHEMA |
| X6 | **Stim Harness Tests** | MP0 | PG-TEST |
| X7 | **Verification Report** | MP2–MP5 | PG-SCHEMA |
| X8 | **WSL Runners** | MP0–MP5 | PG-INFRA |
| X9 | **Research + Baselines** | MP1 | PG-VALIDATE |
| X10 | **Integration Gate** | MP2–MP5 | PG-TEST |

---

## X1 — Proxy Killer

**Mission:** Delete/quarantine `simulate_candidate_ler` / `decoder_quality_multiplier` from all production paths.

**Owns:**
- Remove prod usage of `cryobrain/accuracy/decoder_policy.py` (move to `tests/fixtures/` if needed)
- Update `cryobrain/stim/stim_harness.py` importers
- Update any `cryobrain/grading/` proxy references
- `tests/test_proxy_removed.py`

**Inputs:** `docs/SPEC_REALITY_AUDIT.md` kill list  
**Outputs:** Zero prod imports

**Acceptance:**
```bash
rg "simulate_candidate_ler|decoder_quality_multiplier" cryobrain/ tasks/ scripts/ --glob '!**/tests/**'
# zero hits
pytest tests/test_proxy_removed.py -q
```

**Blockers:** None — **highest priority, hour 0, blocks everyone**  
**Parallel with:** X2, X5

---

## X2 — CI Anti-Cheat Guard

**Mission:** Pre-push / CI fails if proxy or formula reward reappears.

**Owns:**
- `tests/test_no_proxy_ler_in_prod.py`
- `tests/test_keystone_rule.py`
- `scripts/audit_reward_path.sh`
- `.github/workflows/ci.yml` guard job (if remote exists)

**Inputs:** X1 patterns  
**Outputs:** `make check` includes guard tests

**Acceptance:**
```bash
bash scripts/audit_reward_path.sh
pytest tests/test_no_proxy_ler_in_prod.py tests/test_keystone_rule.py -q
```

**Blockers:** X1 land first  
**Parallel with:** X1, Grok G1

---

## X3 — SymbiYosys L3 Formal

**Mission:** L3 formal checks per SPEC-v5 — SVA templates, symbiyosys smoke on golden RTL.

**Owns:**
- `cryobrain/verify/l3_formal.py`
- `tasks/cryo_brain_decoder/sva/`
- `tests/test_l3_formal.py` (WSL, long timeout)

**Inputs:** Grok G4 generated RTL  
**Outputs:** `run_l3_formal(rtl_path) -> {passed, log_path}`

**Acceptance:**
```bash
pytest tests/test_l3_formal.py -m wsl -q --timeout=300
# Golden RTL passes; intentionally mutated RTL fails
```

**Blockers:** MP1; Grok G4  
**Parallel with:** Grok G6/G7 (MP5 stack)

---

## X4 — Keystone Pytest

**Mission:** Automated proof of SPEC-v5 keystone: worse `.sv` → worse measured LER.

**Owns:**
- `tests/test_keystone_rule.py`
- `tests/fixtures/rtl/cryo_brain_decoder_wrong.sv`
- `tests/fixtures/rtl/cryo_brain_decoder_golden.sv`

**Inputs:** Grok G3 `measure_candidate_ler`  
**Outputs:** MP0 gate test

**Acceptance:**
```bash
wsl bash scripts/run_mp0_wsl.sh
pytest tests/test_keystone_rule.py -m wsl -q
# assert wrong.candidate_ler > golden.candidate_ler
```

**Blockers:** G3 minimal implementation  
**Parallel with:** G3 hardening

---

## X5 — Artifact Schema v2

**Mission:** JSON schemas for measured artifacts — reject proxy fields.

**Owns:**
- `cryobrain/artifacts/schemas/v2/`
- `tests/test_artifact_schemas.py`
- `docs/agents/INTERFACE_CONTRACTS.md` (artifact section)

**Inputs:** Master plan memory record + artifact table  
**Outputs:** `validate_measured_climb()`, `validate_pareto()`, etc.

**Acceptance:**
```bash
pytest tests/test_artifact_schemas.py -q
# Fixture with decoder_quality_multiplier field must fail validation
```

**Blockers:** None — start Phase 0  
**Parallel with:** Claude C1, X1

---

## X6 — Stim Harness Tests

**Mission:** Unit + WSL tests for stim compare logic — no policy shortcuts in harness.

**Owns:**
- `tests/test_stim_harness.py`
- `tests/test_stim_compare.py`
- `cryobrain/stim/compare.py` (if split from Grok harness)

**Inputs:** Grok G2 vectors  
**Outputs:** Deterministic mismatch counts on fixtures

**Acceptance:**
```bash
pytest tests/test_stim_harness.py tests/test_stim_compare.py -q
```

**Blockers:** Grok G2 manifest  
**Parallel with:** X4

---

## X7 — Verification Report

**Mission:** `artifacts/verification_report.json` — per-layer L1–L5 pass/fail from real runs.

**Owns:**
- `cryobrain/artifacts/verification_report.py`
- `artifacts/verification_report.json` (generated template)
- `tests/test_verification_report.py`

**Inputs:** Grok G6/G7/G8 + G3 L2 + X3 L3  
**Outputs:** Schema-valid report; `layers_passed` matches actual tool output

**Acceptance:**
```bash
pytest tests/test_verification_report.py -q
```

**Blockers:** MP2 layer wiring  
**Parallel with:** Grok G10

---

## X8 — WSL Runners

**Mission:** Single entrypoints for MP gates and EDA — all pools use these scripts.

**Owns:**
- `scripts/run_mp0_wsl.sh`
- `scripts/run_mp1_wsl.sh`
- `scripts/run_mp5_wsl.sh`
- `scripts/verilator_sim_wsl.sh`
- `scripts/yosys_synth_wsl.sh`
- `docs/EDA_WSL.md`

**Inputs:** OSS CAD at `~/utils/oss-cad-suite/bin`  
**Outputs:** Documented WSL workflow; exit 0 on smoke

**Acceptance:**
```bash
wsl bash scripts/run_mp0_wsl.sh   # after G3 lands
wsl bash scripts/run_mp1_wsl.sh   # after MP1
```

**Blockers:** G3 for mp0; G4/G5 for mp1  
**Parallel with:** Grok G3 from hour 0 (script stubs OK)

---

## X9 — Research + Baselines

**Mission:** Real baseline LER JSON from WSL runs + ECC research doc (informs tests, not fake numbers).

**Owns:**
- `artifacts/baselines/ler_baselines.json`
- `scripts/compute_ler_baselines_wsl.sh`
- `docs/research/ECC_DECODER_METRICS.md`
- `tests/test_ler_baselines.py`

**Inputs:** Grok G3; stim manifest hash  
**Outputs:** Checked-in baselines with git SHA + reproducibility ε

**Acceptance:**
```bash
wsl bash scripts/compute_ler_baselines_wsl.sh
pytest tests/test_ler_baselines.py -m wsl -q
```

**Blockers:** MP0  
**Parallel with:** X4 regression extension

---

## X10 — Integration Gate

**Mission:** End-to-end pytest: DesignConfig → generate_rtl → measure → synth → score → memory schema.

**Owns:**
- `tests/integration/test_measured_pipeline.py`
- `tests/test_ler_regression.py`
- `pytest.ini` markers (`wsl`, `slow`)

**Inputs:** All MP2 APIs  
**Outputs:** Single integration proof on WSL

**Acceptance:**
```bash
pytest tests/integration/test_measured_pipeline.py -m wsl -q
pytest tests/test_ler_regression.py -m wsl -q
```

**Blockers:** MP2  
**Parallel with:** Claude C5, Grok G10

---

## Sequenced Execution

```
Hour 0 (BLOCKS ALL — parallel):
  X1 proxy kill
  X2 guard scaffold
  X5 artifact schemas
  X8 script stubs

Hour 4–12 (MP0):
  X4 keystone + X6 stim tests
  X8 run_mp0_wsl.sh green with Grok G3

Hour 12–24 (MP1):
  X9 baselines
  X8 run_mp1_wsl.sh

Hour 24–40 (MP2–MP3):
  X7 verification report
  X10 integration gate

Hour 40+ (MP4–MP5):
  X3 SymbiYosys
  X8 run_mp5_wsl.sh full L1–L5
```

---

## WSL Convention

```bash
wsl bash -lc 'cd /mnt/c/Users/ayush/Desktop/Hackathons/YC/06-20-2026 && uv run pytest tests/test_keystone_rule.py -m wsl -q'
```

Never claim MP0 pass on Windows-native Verilator unless `docs/EDA_WSL.md` documents it.

---

## Handshake Matrix

| Gate | Codex proves | Grok proves | Claude proves |
|------|--------------|-------------|---------------|
| MP0 | X4 wrong > golden | G3 measure works | C8 smoke imports |
| MP1 | X8 mp1 script | G4/G5 3 variants | — |
| MP2 | X2 no proxy | G10 score_measured | C5 trainer loop |
| MP3 | X10 integration | — | C4 climb artifact |
| MP5 | X3 L3 + X7 report | G6/G7/G8 layers | C10 pareto |

---

## Escalation

| Symptom | Agent |
|---------|-------|
| Proxy import survived X1 | X1 + X2 |
| Keystone flaky | X4 + X9 manifest drift |
| Schema allows fake LER field | X5 |
| mp0 script fails | X8 + Grok G3 |

---

## Subagent Prompt Template

```
You are Codex agent X{N} for CryoBrain SPEC-v5.
Read: docs/specs/SPEC-v5.md, docs/SPEC_REALITY_AUDIT.md, docs/agents/HANDOFF-CODEX.md (section X{N}).
Branch: feat/v5-x{N}-<slug>
Test and guard Grok/Claude APIs — do not reimplement measure/generate/synth/trainer.
NON-GOALS: demo/, dashboard, fake LER, implementing measured_ler core (Grok G3).
Acceptance: <paste from section X{N}>
```