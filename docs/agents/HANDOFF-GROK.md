# Handoff: Grok / Cursor Pool (10 Agents)

**Orchestrator:** Grok (Cursor)  
**Canonical spec:** [`docs/specs/SPEC-v5.md`](../specs/SPEC-v5.md)  
**Master plan:** [`00-MASTER_PLAN.md`](./00-MASTER_PLAN.md)  
**Branch prefix:** `feat/v5-g{N}-<slug>`

---

## START HERE (read this if a human said “read this file”)

You have everything you need in this repo. Follow this section before touching code.

**This pool is on the critical path.** Claude and Codex are blocked on your frozen APIs until MP0/MP1 land.

### Step 1 — Reading order (mandatory)

Read these files **in this order** before any implementation:

1. [`docs/specs/SPEC-v5.md`](../specs/SPEC-v5.md) — canonical requirements  
2. [`docs/SPEC_REALITY_AUDIT.md`](../SPEC_REALITY_AUDIT.md) — proxy kill list  
3. [`00-MASTER_PLAN.md`](./00-MASTER_PLAN.md) — DAG, frozen interfaces, milestones  
4. **This file** — your pool’s 10 agent slots (sections G1–G10 below)

### Step 2 — Figure out your role

| Situation | What you do |
|-----------|-------------|
| Human said “read `HANDOFF-GROK.md`” with **no slot** | You are the **Grok/Cursor orchestrator**. Run **Wave 1** in parallel, prioritize **G3** for MP0, per [Orchestrator playbook](#orchestrator-playbook-grok) below. |
| Human said “you are **G{N}**” or orchestrator assigned a slot | You are **Grok subagent G{N}**. Read **only** section **G{N}** below. |
| Codex X1 has not landed yet | Grok can still start G1/G2/G9/G4 skeleton; coordinate so G10 does not merge before proxy is dead. |

### Step 3 — Hard rules (every Grok agent)

- **You own** measured LER, RTL generation, Yosys metrics, L1/L4/L5 gates, and `score_measured`.  
- **Do not** edit `demo/`, dashboard, `cryobrain/memory/`, or `cryobrain/rl/` (Claude pool).  
- **Do not** use `simulate_candidate_ler` or `decoder_quality_multiplier` in any path you touch.  
- **Do not** break frozen interface signatures in `00-MASTER_PLAN.md` without updating `INTERFACE_CONTRACTS.md` and notifying other pools.  
- **One branch per slot:** `feat/v5-g{N}-<short-slug>`.  
- **EDA runs in WSL** — coordinate with Codex X8 scripts.  
- **Done** = section acceptance + MP gate unlocked if your slot owns it.

### Step 4 — Wave order (do not launch all 10 at once)

| Wave | Slots | Milestone | Notes |
|------|-------|-----------|-------|
| **1** | **G1**, **G2**, **G9**, G4 (skeleton) | — | All parallel; hour 0 |
| **2** | **G3** | **MP0** | Keystone — blocks Claude/Codex |
| **3** | **G4**, **G5**, G6, G7 | **MP1** | After MP0 green |
| **4** | **G10**, G8 | **MP2** | After MP1; needs Codex X1 proxy dead |
| **5** | G6/G7/G8 hardening | **MP5** | With Codex X3 |

**Orchestrator default:** if unsure, assign **G1 + G2 + G9** first, then **G3** as soon as G1 types exist.

### Orchestrator playbook (Grok)

When acting as orchestrator with 10 parallel subagents:

1. **Wave 1 (parallel):** G1 + G2 + G9 + G4 skeleton.  
2. **Wave 2 (critical):** G3 until `wsl bash scripts/run_mp0_wsl.sh` passes.  
3. **Wave 3:** G4 + G5 + G6 + G7 until `wsl bash scripts/run_mp1_wsl.sh` passes.  
4. **Wave 4:** G10 (after Codex X1 proxy kill) + G8.  
5. Announce in PR/mesh when MP0 and MP1 pass so Claude/Codex unlock Waves 2+.  
6. Each subagent: branch `feat/v5-g{N}-…`, owned paths only, acceptance from section G{N}.

Subagent spawn text (orchestrator copies per slot):

```
You are Grok agent G{N} for CryoBrain SPEC-v5.
Read in order: docs/specs/SPEC-v5.md, docs/SPEC_REALITY_AUDIT.md, docs/agents/00-MASTER_PLAN.md, docs/agents/HANDOFF-GROK.md section G{N} only.
Branch: feat/v5-g{N}-<slug>. Own only paths listed in G{N}.
NON-GOALS: demo/, dashboard, fake LER, decoder_quality_multiplier, cryobrain/memory/, cryobrain/rl/.
Done when: <paste Acceptance block from section G{N}>.
```

### What the human can say (copy-paste)

**To Grok/Cursor orchestrator (minimum):**

> Read `docs/agents/HANDOFF-GROK.md` and execute it. You are the Grok orchestrator — follow START HERE and prioritize G3 for MP0.

**To a single Grok subagent:**

> Read `docs/agents/HANDOFF-GROK.md`. You are Grok agent **G3**. Execute only section G3.

---

## Pool Mission

Grok/Cursor owns the **critical path spine**: measured LER (P0), parametric RTL generation (P1), per-variant Yosys (P1), verification layers L1/L4/L5, and `grade.py` → `score_measured`. **Nothing in Claude or Codex pools ships real numbers until Grok lands frozen interfaces.**

**Non-goals:** `demo/`, dashboard, Gizmo, PDFs, screen capture, proxy/formula LER, fake sponsor payloads.

---

## You Implement These Interfaces (Frozen — Do Not Break)

### `measure_candidate_ler` — G1/G3

```python
# cryobrain/accuracy/measured_ler.py
def measure_candidate_ler(
    rtl_path: Path,
    scenario: ScenarioConfig,
    *,
    shots: int = 1000,
    seed: int = 0,
) -> dict:
    """Returns candidate_ler, mwpm_ler, suppression, shots, vector_source, rtl_path."""
```

**MP0 acceptance:** `cryo_brain_decoder_wrong.sv` → strictly worse `candidate_ler` than fixed XOR golden.

### `generate_rtl` + `synth_metrics` — G4/G5

```python
# cryobrain/rtl_gen/generator.py
def generate_rtl(design: DesignConfig, out_dir: Path) -> Path: ...

# cryobrain/rtl_grader/synth_metrics.py
def synth_metrics(rtl_path: Path) -> dict:
    """area_um2, latency_cycles, power_mw_est, valid, yosys_log_path"""
```

**MP1 acceptance:** 3 `DesignConfig`s → 3 distinct `.sv` → 3 distinct `(area_um2, candidate_ler)` pairs.

### `score_measured` — G10

```python
# cryobrain/grader/score.py
def score_measured(workdir: Path) -> dict:
    """reward, valid, ler, area_um2, latency_cycles, power_mw, layers_passed: list[str]"""
```

Hidden `grade.py` calls this; **must not** import `simulate_candidate_ler`.

---

## Agent Roster

| ID | Name | Milestone | Parallel group |
|----|------|-----------|----------------|
| G1 | **Measure API + Types** | MP0 | PG-0 |
| G2 | **Stim Vector Bank** | MP0 | PG-0 |
| G3 | **Verilator TB + LER Core** | MP0 | PG-0 |
| G4 | **RTL Generator** | MP1 | PG-1 |
| G5 | **Yosys Per-Variant Synth** | MP1 | PG-1 |
| G6 | **L1 Functional Gate** | MP1–MP5 | PG-VERIFY |
| G7 | **L4 Synthesis Sign-Off** | MP1–MP5 | PG-VERIFY |
| G8 | **L5 Budget Gate** | MP2–MP5 | PG-VERIFY |
| G9 | **DesignConfig Schema** | MP0–MP1 | PG-1 |
| G10 | **Grade → score_measured** | MP2 | PG-2 |

---

## G1 — Measure API + Types

**Mission:** Land `measured_ler.py` signatures, `ScenarioConfig`, return dict schema — stub OK until G3 fills body.

**Owns:**
- `cryobrain/accuracy/measured_ler.py` (types + stub)
- `cryobrain/accuracy/types.py`
- `docs/agents/INTERFACE_CONTRACTS.md`

**Inputs:** SPEC-v5 P0; Codex X5 artifact schema  
**Outputs:** Importable API; documented JSON shape

**Acceptance:**
```bash
python -c "from cryobrain.accuracy.measured_ler import measure_candidate_ler; ..."
pytest tests/test_measured_ler_types.py -q  # create if missing
```

**Blockers:** None — **start hour 0**  
**Parallel with:** G2, G4 skeleton, Codex X1

---

## G2 — Stim Vector Bank

**Mission:** Real Stim-derived syndrome vectors; train/holdout splits; manifest with checksums.

**Owns:**
- `tasks/cryo_brain_decoder/stim/` layout
- `cryobrain/stim/manifest.py`
- `cryobrain/stim/vector_bank.py`

**Inputs:** Existing `stim_harness.py` expectations  
**Outputs:** `manifest.json`; holdout never used in training reward

**Acceptance:**
```bash
pytest tests/test_stim_manifest.py -q
python -c "from cryobrain.stim.manifest import holdout_paths; assert len(holdout_paths()) > 0"
```

**Blockers:** None  
**Parallel with:** G1, G9

---

## G3 — Verilator TB + LER Core

**Mission:** **Keystone implementation** — Stim vectors → Verilator DUT → measured `candidate_ler`. No formulas.

**Owns:**
- `cryobrain/accuracy/measured_ler.py` (implementation)
- `cryobrain/stim/stim_harness.py` (drive DUT)
- `cryobrain/eda/verilator_build.py`
- `tests/test_measured_ler.py` (WSL)

**Inputs:** G1 API, G2 vectors, `scripts/verilator_sim_wsl.sh` (Codex X8)  
**Outputs:** Deterministic LER; worse RTL → worse number

**Acceptance:**
```bash
wsl bash scripts/run_mp0_wsl.sh   # keystone gate
pytest tests/test_measured_ler.py -m wsl -q
```

**Blockers:** G1 types; G2 manifest  
**Parallel with:** Codex X4 keystone pytest after stub works

---

## G4 — RTL Generator

**Mission:** Parametric decoder Verilog — `DesignConfig` → distinct synthesizable `.sv` per variant.

**Owns:**
- `cryobrain/rtl_gen/generator.py`
- `cryobrain/rtl_gen/templates/`
- `tests/test_rtl_generator.py`

**Inputs:** G9 `DesignConfig`; reference `tasks/cryo_brain_decoder/rtl/cryo_brain_decoder.sv`  
**Outputs:** `generate_rtl(design, out_dir) -> Path`

**Acceptance:**
```bash
pytest tests/test_rtl_generator.py -q
# 3 configs → 3 files with different hashes; all verilator-buildable (WSL)
```

**Blockers:** G9 schema draft  
**Parallel with:** G5 after G3 MP0 passes

---

## G5 — Yosys Per-Variant Synth

**Mission:** Real Yosys `stat` per RTL path — area/latency/power from logs, not `npu_cost` formulas.

**Owns:**
- `cryobrain/rtl_grader/synth_metrics.py`
- `scripts/yosys_synth_wsl.sh` (coordinate Codex X8)
- `tests/test_synth_metrics.py` (WSL)

**Inputs:** G4 output paths  
**Outputs:** `synth_metrics(rtl_path) -> dict` with `valid: bool`

**Acceptance:**
```bash
wsl bash scripts/run_mp1_wsl.sh
pytest tests/test_synth_metrics.py -m wsl -q
```

**Blockers:** G4 + G3 (for MP1 joint gate)  
**Parallel with:** G7

---

## G6 — L1 Functional Gate

**Mission:** Verilator lint/smoke — broken RTL fails before L2 LER spend.

**Owns:**
- `cryobrain/verify/l1_functional.py`
- `tests/test_l1_functional.py`

**Inputs:** G3 verilator build  
**Outputs:** `run_l1(rtl_path) -> {passed, log_path}`

**Acceptance:** Known-broken SV fails; golden SV passes

**Blockers:** G3 build pipeline  
**Parallel with:** G7, G8

---

## G7 — L4 Synthesis Sign-Off

**Mission:** Yosys clean synth, no latches, lint — wraps G5 with pass/fail gate.

**Owns:**
- `cryobrain/verify/l4_synth.py`
- `tests/test_l4_synth.py`

**Inputs:** G5  
**Outputs:** Layer tag `"L4"` in `score_measured.layers_passed`

**Blockers:** G5  
**Parallel with:** G6, G8

---

## G8 — L5 Budget Gate

**Mission:** Cryo envelope check using **measured** L4 metrics + documented thresholds (not proxy cost model as reward).

**Owns:**
- `cryobrain/verify/l5_budget.py`
- `cryobrain/cost_model/envelope.py` (thresholds only — not LER)
- `tests/test_l5_budget.py`

**Inputs:** G5 synth dict, G7 pass  
**Outputs:** Fail → reward 0 in G10 path

**Blockers:** G5/G7  
**Parallel with:** G6

---

## G9 — DesignConfig Schema

**Mission:** Typed config space for RTL params — replaces implicit preset dicts in `local_trainer.py`.

**Owns:**
- `cryobrain/design/config.py`
- `cryobrain/design/validators.py`
- `tests/test_design_config.py`

**Inputs:** SPEC-v5 decoder parameters  
**Outputs:** Pydantic `DesignConfig`; `sample()`, `mutate()`

**Acceptance:**
```bash
pytest tests/test_design_config.py -q
```

**Blockers:** None — **start MP0**  
**Parallel with:** G1, G2, G4 stub

---

## G10 — Grade → score_measured

**Mission:** Rewire `tasks/.../grade.py` to call measured stack only; kill proxy imports.

**Owns:**
- `cryobrain/grader/score.py`
- `tasks/cryo_brain_decoder/grade.py` (or equivalent)
- `tests/test_score_measured.py`

**Inputs:** G3, G5, G6–G8 layer results  
**Outputs:** `score_measured(workdir)` — **MP2 gate**

**Acceptance:**
```bash
pytest tests/test_score_measured.py -q
rg "simulate_candidate_ler|decoder_quality_multiplier" cryobrain/grader/ tasks/
# zero hits
```

**Blockers:** MP0 + MP1; Codex X2 CI guard  
**Parallel with:** Claude C5 trainer (after API frozen)

---

## Sequenced Execution

```
Hour 0–4 (Phase 0 — parallel):
  G1 + G2 + G9 + G4 skeleton
  Codex X1/X2 proxy kill (unblocks G10 later)

Hour 4–12 (Phase 1 — P0 critical):
  G3 full implementation → MP0
  Codex X4 keystone pytest

Hour 12–24 (Phase 2 — P1):
  G4 + G5 + G6/G7/G8 → MP1
  wsl scripts/run_mp1_wsl.sh green

Hour 24+ (Phase 3):
  G10 → MP2
  Hand off to Claude C1/C5 for learning loop
```

---

## Path Ownership (Do Not Trespass)

| Path | Owner |
|------|-------|
| `cryobrain/accuracy/measured_ler.py` | G1/G3 |
| `cryobrain/rtl_gen/` | G4 |
| `cryobrain/rtl_grader/` | G5 |
| `cryobrain/grader/score.py` | G10 |
| `cryobrain/verify/l1|l4|l5` | G6/G7/G8 |
| `cryobrain/rl/`, `cryobrain/memory/` | Claude pool |
| `tests/test_keystone_rule.py` | Codex X4 |

---

## Escalation

| Issue | Agent |
|-------|-------|
| Proxy LER in grade path | G10 + Codex X1 |
| WSL Verilator fails | G3 + Codex X8 |
| 3 configs same LER | G4 + G3 |
| Yosys stat parse | G5 + G7 |

---

## Subagent Prompt Template

```
You are Grok agent G{N} for CryoBrain SPEC-v5.
Read: docs/specs/SPEC-v5.md, docs/agents/HANDOFF-GROK.md (section G{N}).
Branch: feat/v5-g{N}-<slug>
Own only listed paths. Import frozen interfaces; do not redefine.
NON-GOALS: demo/, dashboard, fake LER, decoder_quality_multiplier.
Acceptance: <paste from section G{N}>
Post mesh.log_action when done or blocked.
```