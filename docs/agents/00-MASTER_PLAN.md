# CryoBrain SPEC-v5 — Multi-orchestrator master plan

**Canonical spec:** `docs/specs/SPEC-v5.md`  
**Audience:** Grok/Cursor, Claude, Codex — each running **10 parallel subagents**  
**Scope:** Engineering only. **Out of scope:** demo video, dashboard polish, PDFs, Gizmo, screen capture, fake/proxy data.

---

## Human kickoff (one line per tool)

You do not need a custom prompt. Each pool handoff opens with **START HERE**:

| Orchestrator | Human says |
|--------------|------------|
| Codex | Read `docs/agents/HANDOFF-CODEX.md` and execute it. |
| Claude | Read `docs/agents/HANDOFF-CLAUDE.md` and execute it. |
| Grok / Cursor | Read `docs/agents/HANDOFF-GROK.md` and execute it. |

Orchestrators read the spec stack, follow wave order (not 10 agents at once), spawn subagents from the template in their handoff, and block on MP0/MP1 where required. Optional single slot: *“You are agent **G3** — execute only section G3.”*

Index: [`README.md`](./README.md)

---

## North star

Build a **measured** verifiable RL environment for cryogenic QEC decoder co-design:

1. **P0** — Candidate LER from Stim vectors → Verilator RTL → measured logical errors (kill proxy).
2. **P1** — Parametric RTL generator + **per-variant** Yosys (area/latency/power).
3. **P2** — Model proposes designs/RTL; reward-ranked learning + memory; GRPO on Modal (real).
4. **L1–L5** — Full verification gate before any reward &gt; 0.
5. **GEN** — Same env optimizes a **second** RTL target (FIFO) — platform proof.
6. **Sponsors** — HUD, Modal, Fireworks, Exa, Daytona wired to **real pipeline steps**, not logos.

Read `docs/SPEC_REALITY_AUDIT.md` first — v1–v4 shipped knob search + `decoder_quality_multiplier`. v5 replaces that entirely.

---

## Three orchestrator pools (30 agents total)

| Pool | Handoff doc | Owns | Critical path |
|---|---|---|---|
| **Grok / Cursor** | `HANDOFF-GROK.md` | P0 measurement spine, P1 RTL gen, Yosys, L1/L4/L5, `grade.py` | **Yes — blocks everyone** |
| **Claude** | `HANDOFF-CLAUDE.md` | Learning loop, memory, Modal/Fireworks/Exa/Daytona, HUD, FIFO proof, benchmarks | After P0 API frozen |
| **Codex** | `HANDOFF-CODEX.md` | Kill proxy CI, tests, SymbiYosys, artifacts schema, WSL runners, integration | Parallel from t=0 |

**Rule:** Grok pool lands **frozen interfaces** (below) before Claude/Codex wire consumers. Codex can delete/guard proxy immediately without waiting.

---

## Frozen interfaces (merge contract — do not break)

Implement these types/signatures first; all pools import them.

### `measure_candidate_ler` (P0 — Grok G3)

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

**Acceptance (MP0):** `cryo_brain_decoder_wrong.sv` → strictly worse `candidate_ler` than fixed XOR golden.

### `generate_rtl` + `synth_metrics` (P1 — Grok G4/G5)

```python
# cryobrain/rtl_gen/generator.py
def generate_rtl(design: DesignConfig, out_dir: Path) -> Path: ...

# cryobrain/rtl_grader/synth_metrics.py
def synth_metrics(rtl_path: Path) -> dict:
    """area_um2, latency_cycles, power_mw_est, valid, yosys_log_path"""
```

**Acceptance (MP1):** 3 `DesignConfig`s → 3 distinct `.sv` files → 3 distinct `(area_um2, candidate_ler)` pairs.

### `score_measured` (Grok G10 — replaces proxy grade path)

```python
# cryobrain/grader/score.py
def score_measured(workdir: Path) -> dict:
    """reward, valid, ler, area_um2, latency_cycles, power_mw, layers_passed: list[str]"""
```

Hidden `grade.py` calls this; **must not** import `simulate_candidate_ler`.

### Memory record (Claude C1)

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

### Artifact files (measured only)

| File | Producer | Required fields |
|---|---|---|
| `artifacts/measured_climb.json` | Claude C5/C4 | `history[].{step, candidate_ler, suppression, rtl_hash}` |
| `artifacts/measured_pareto.json` | Claude C10 | `points[].{label, ler, area_um2, latency_cycles, rtl_path}` |
| `artifacts/measured_memory_ab.json` | Claude C5 | two series from **measured** runs |
| `artifacts/verification_report.json` | Codex X7 | per-layer pass/fail |

**Forbidden:** writing `decoder_quality_multiplier` results into artifacts after MP0 lands.

---

## Dependency DAG (non-blocking where possible)

```
Phase 0 (hour 0–4, parallel)
├── Codex X1/X2: proxy kill + CI guard
├── Grok G1: measure_candidate_ler API stub + types
├── Grok G4: RTL generator skeleton
├── Claude C8: HUD eval smoke (no proxy dependency)
└── Codex X5: artifact schema v2

Phase 1 (hour 4–12, P0 critical)
├── Grok G2/G3: Stim vector bank + Verilator TB  ──► MP0
├── Grok G10: grade.py → score_measured
└── Codex X4: keystone pytest (worse → worse)

Phase 2 (hour 12–24, P1)
├── Grok G5/G7/G8: per-variant Yosys + L4/L5
└── MP1 checkpoint

Phase 3 (hour 24–40, learning)
├── Claude C1/C2/C5: memory + Fireworks proposer + trainer rewrite
├── Claude C3/C4: Modal fan-out + GRPO
├── Claude C6/C7: Exa + Daytona on real workdirs
└── MP2/MP3

Phase 4 (hour 40+, platform)
├── Claude C9: FIFO second target (GEN)
├── Codex X3/X7: SymbiYosys + MP5 full gate
└── Claude C10 + Codex X8: benchmark + WSL runners
```

---

## Branch & collision rules

- **One branch per agent slot:** `feat/v5-g3-verilator-ler`, `feat/v5-c4-grpo`, etc.
- **Owned paths** — do not edit another agent's primary files; open PR notes if interface change needed.
- **EDA runs in WSL** — use `scripts/*_wsl.sh`; never grade on Windows bare metal.
- **Merge order:** interface PRs (G1, G3, G4, G5) → grade integration (G10) → consumers (Claude/Codex).
- **No direct push to main** — PR only per global gate.

### Path ownership map

| Path | Owner pool |
|---|---|
| `cryobrain/accuracy/measured_ler.py`, `decoder_policy.py` (delete usage) | Grok + Codex |
| `cryobrain/rtl_gen/` | Grok G4 |
| `cryobrain/rtl_grader/synth_metrics.py` | Grok G5 |
| `cryobrain/grader/score.py`, `tasks/.../grade.py` | Grok G10 |
| `cryobrain/rl/local_trainer.py`, `modal_train.py` | Claude C4/C5 |
| `cryobrain/memory/` | Claude C1 |
| `cryobrain/integrations/{fireworks,exa,daytona}.py` | Claude C6/C7/C2 |
| `tests/test_measured_*.py`, `tests/test_keystone_rule.py` | Codex |
| `scripts/run_mp*_wsl.sh` | Codex X8 |
| `demo/`, `dashboardspec*` | **FROZEN — no v5 agent touches** |

---

## Milestone checklist (from SPEC-v5 §10)

| ID | Gate | Owner |
|---|---|---|
| **MP0** | Worse `.sv` → worse measured LER | Grok G3 + Codex X4 |
| **MP1** | 3 configs → 3 distinct measured (area, LER) | Grok G4/G5 |
| **MP2** | Reward moves only on measured change | Grok G10 + Codex X7 |
| **MP3** | Measured climb (not proxy) | Claude C4/C5 |
| **MP4** | Memory A/B on measured runs only | Claude C5 |
| **MP5** | L1–L5 all gate score | Codex X3 + Grok G6/G7/G8 |
| **CP0** | `hud eval` green on measured path | Claude C8 |
| **GEN** | FIFO target optimizes in same env | Claude C9 |

---

## Sponsor integration (real roles only)

| Sponsor | Must do | Agent |
|---|---|---|
| **HUD** | `env.py` tools call measured `score()`; CP0 eval | Claude C8 |
| **Modal** | Parallel Verilator measurement + GRPO GPU | Claude C3/C4 |
| **Fireworks** | Propose RTL/design; GRPO policy | Claude C2/C4 |
| **Exa** | Literature → memory seed with citations | Claude C6 |
| **Daytona** | Snapshot/fork per-variant measurement workdir | Claude C7 |
| **DeepMind** | Citation anchor in benchmark plots (research) | Codex X9 |

**Skip:** Antim Gizmo, demo-only integrations until measured artifacts exist.

---

## Validation commands (pre-PR)

```bash
# WSL (OSS CAD + Linux venv)
wsl bash scripts/run_mp0_wsl.sh      # keystone: worse RTL → worse LER
wsl bash scripts/run_mp1_wsl.sh      # 3 variants distinct
uv run ruff check .
uv run pytest tests/test_measured_*.py tests/test_keystone_rule.py -q
```

---

## Handoff index

1. [`HANDOFF-GROK.md`](HANDOFF-GROK.md) — 10 agents: measurement + RTL + synth spine  
2. [`HANDOFF-CLAUDE.md`](HANDOFF-CLAUDE.md) — 10 agents: learning + sponsors + platform  
3. [`HANDOFF-CODEX.md`](HANDOFF-CODEX.md) — 10 agents: kill proxy, tests, formal, integration  

Each subagent prompt must include: slot ID, owned files, interface imports, acceptance test, and explicit **NON-GOALS** (no demo/dashboard/fake data).