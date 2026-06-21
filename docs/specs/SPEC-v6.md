# CryoBrain Swarm — Build Spec (v6)

A self-improving AI hardware lab that designs the real-time NPU "brain" inside future quantum chips. A swarm of specialized agents researches, proposes, generates, verifies, measures, scores, remembers, and improves decoder designs — every improvement grounded in real Stim + Verilator + Yosys measurements.

**Tags on every claim:** `[BUILT]` real now · `[CLAIMABLE]` say after the gate passes · `[VISION]` the 2040 arc, frame as future, never as done. Saying a `[VISION]` line as `[BUILT]` is the one thing that sinks you with a judge.

**Keystone rule (everything obeys):** worse RTL → worse measured LER. No formula/proxy accuracy in any production scoring path. The swarm is only "real" because each design is measured, not estimated.

**Honest ceiling:** the trained agent approaches MWPM while measurably improving. NOT "we beat industry" / NOT "we mass-produced silicon." Show the gap closing.

---

## Implementation status (2026-06-21)

| Phase | Item | Status | Evidence |
|-------|------|--------|----------|
| Spine | MP0–MP2 measured reward | **Green** | `run_mp0_wsl.sh` … `run_mp2_wsl.sh` |
| P-gate | Architect climb on disk | **Pending WSL run** | `run_c5_climb_wsl.sh` → `artifacts/measured_climb.json` |
| P-gate | Memory A/B on disk | **Pending WSL run** | `--memory-ab` in C5 climb |
| P-bus | Event log message bus | **Built** | `cryobrain/swarm/event_bus.py` |
| P-exec | Tier-2 executors on bus | **Built** | `cryobrain/swarm/executors.py`, `proposal_loop.py` |
| P-viz | Visualization from events | **Built** | `cryobrain/swarm/visualization.py`, demo swarm strip |
| P-train2 | Planner trained agent | **Built** | `cryobrain/swarm/planner.py`, `planner_trainer.py` |
| MP5 | L3 formal + verification report | **Built** | `l3_formal.py`, `verification_report.py` (sby skips gracefully) |
| P-gen | FIFO platform proof | **Code built** | `run_gen_fifo_wsl.sh`, `test_gen_fifo.py` |
| Demo | Measured-first bundle | **Built** | `build_demo.py` prefers `measured_*.json` |

**Gate script:** `wsl bash scripts/run_spec_v6_gate_wsl.sh`

---

## 0. The two loops (the framing)

### Fast loop — the chip reacts in real time

`[VISION — cite, do not demo as ours]` Inside the future machine, the CryoBrain NPU watches syndrome streams, detects drift, switches decoder strategies, and corrects in real time. Grounded in the real direction of the field (Riverlane's real-time QEC stack; FPGA neural-decoder work reporting sub-µs closed-loop surface-code feedback). Your repo does NOT do this — present it as the 2040 destination, never imply tonight's chip adaptively decodes live.

### Slow loop — the swarm improves the next chip

`[BUILT — this is what you run tonight]` Outside the chip, the agent swarm runs a scientific loop: research → propose → generate RTL → simulate → synthesize → score → remember → improve, every step measured. This is the prototype you demo.

**Pitch:** Every quantum chip needs a brain. CryoBrain is the swarm that designs that brain (slow loop, built), and the real-time NPU that keeps the chip alive (fast loop, 2040 arc).

---

## 1. The swarm — nine roles, three tiers (truth-tagged)

Each agent is real and owns a role in the measured loop. But only reward-bearing roles train. Claiming all nine "learn via RL" is the overclaim — five have no reward signal.

### TIER 1 — TRAINED (have a measured reward → RL-trained)

| Agent | Role | Reward it climbs | Tag |
|-------|------|------------------|-----|
| **Architect** (proposer) | proposes decoder/NPU `DesignConfig` | measured suppression + hardware score | `[TRAIN — the thesis; train FIRST]` |
| **Planner** | chooses the next experiment / search direction | reward delta achieved by its chosen experiments | `[TRAIN — second, if time]` |
| **Repair/Optimizer** (optional) | mutates a failing/suboptimal design toward budget | improvement in measured reward | `[TRAIN — third, if time]` |

### TIER 2 — SPECIALIST EXECUTORS (real agents, role-specific, NO reward → not RL-trained)

| Agent | Role | Why fixed-policy | Tag |
|-------|------|------------------|-----|
| **Research** | reads QEC/decoder/cryo papers (Exa) → priors/context | retrieval, no "better/worse" signal | `[BUILT — executor]` |
| **RTL** | generates synthesizable Verilog from a `DesignConfig` | deterministic generation | `[BUILT — executor]` |
| **Measurement** | runs Stim + Verilator + Yosys → measured numbers | correct or a bug; nothing to learn | `[BUILT — executor]` |
| **Verifier** | runs L1–L5 gates | pass/fail logic | `[BUILT — executor]` |
| **Scorer** | assembles the reward from measured inputs | fixed objective function | `[BUILT — executor]` |
| **Memory** | stores/retrieves verified winners; compounds | store + ranking | `[BUILT — executor]` |

### TIER 3 — VISUALIZATION

| Agent | Role | Tag |
|-------|------|-----|
| **Visualization** | turns the real measured event stream into the live Gizmo/3D demo | `[BUILT — bound to real events only]` |

**Honest claim:** "A nine-role design swarm where the design agents are RL-trained on a measured reward and the specialist agents execute a verified pipeline." True + bigger than "AI designs a chip," and survives "show me the logger's training curve" (answer: the logger is an executor, here's the Architect's climb).

---

## 2. The message bus (what makes it a swarm, and what Gizmo reads)

Agents communicate through an append-only event log — one JSON event per action. This log is simultaneously: the swarm's coordination channel, the audit trail, and the data source the Visualization agent renders. Gizmo reads this, never a script.

**Event schema (one per agent action):**

```json
{
  "ts": "2026-06-21T07:00:00Z",
  "agent": "Architect",
  "action": "propose",
  "design_id": "d017",
  "payload": {"bitwidth": 4},
  "measured": false
}
```

```json
{
  "ts": "2026-06-21T07:00:12Z",
  "agent": "Measurement",
  "action": "measure",
  "design_id": "d017",
  "payload": {"candidate_ler": 0.041, "mwpm_ler": 0.038},
  "measured": true,
  "artifact_ref": "artifacts/measured/d017.json"
}
```

**Pipeline order on the bus:** Research → Planner → Architect → RTL → Measurement → Verifier → Scorer → Memory → (Planner)

**Rule:** any event with `measured: true` MUST carry an `artifact_ref` to a real file. The Visualization agent may only animate `measured: true` events as "results"; proposals/plans render as "in progress," never as outcomes.

**Implementation:** `artifacts/swarm/event_log.jsonl` via `cryobrain/swarm/event_bus.py`.

---

## 3. The measured spine (the keystone — unchanged, non-negotiable)

| Layer | Requirement | Status |
|-------|-------------|--------|
| Measured accuracy | `measure_candidate_ler(rtl, d, noise, shots)` → candidate LER from Verilator on Stim vectors | `[BUILT-MP0]` |
| RTL is the artifact | `generate_rtl(DesignConfig)` → distinct synthesizable `.sv`; `synth_metrics()` per variant | `[BUILT-MP1]` |
| Reward (measured-only) | if not L1..L5 pass: 0.0; elif over budget: 0.0; else weighted measured terms (≤3) | `[BUILT-MP2]` |
| Proxy killed | No formula LER in production scoring; CI guards | `[BUILT]` |

---

## 4. Verification layers L1–L5 (the trust moat — Verifier agent owns this)

A design is never scored until all required layers pass.

| Layer | Check | Status |
|-------|-------|--------|
| **L1** functional | Verilator: valid corrections / bit-exact vs golden | `[BUILT]` |
| **L2** measured accuracy | Stim+Verilator LER | `[BUILT]` |
| **L3** formal | SymbiYosys + Z3 | `[BUILT — skips if sby missing; required when sby on PATH]` |
| **L4** synthesis sign-off | Yosys: synth clean, no latch, lint | `[BUILT]` |
| **L5** budget gate | cryo latency/area/power | `[BUILT]` |

**Verification report** aggregating L1–L5 per design — `[BUILT]` via `cryobrain/artifacts/verification_report.py`.

---

## 5. Sponsors — one real function each (proper use, not logos)

| Sponsor | Function in the swarm | Tag |
|---------|----------------------|-----|
| **HUD** | the RL environment the trained agents train/eval in | `[BUILT]` |
| **Modal** | parallel measurement + rollout engine | `[Core-training]` |
| **Fireworks** | train/serve the Architect (+Planner) policy; GRPO | `[Core-training]` |
| **Exa** | the Research agent's retrieval + provenance | `[BUILT]` |
| **Daytona** | sandboxed per-design measurement environments | `[BUILT]` |
| **Antim/Gizmo** | the Visualization agent's real-time 3D render | `[Optional-wow]` |
| **Google DeepMind** | QEC/neural-decoder research anchor (AlphaQubit) | High |
| **Anthropic/Claude** | build/reasoning support; strong baseline agents | High |
| SixtyFour, Protege, MiniMax | — | Skip — no honest fit |

---

## 6. Build order (parallel, but gated on ONE thing)

**GATE 0** — the Architect's measured climb must exist on disk before "swarm of trained agents" means anything. Run `run_c5_climb_wsl.sh` → commit `measured_climb.json`. One real trained climb > nine claimed ones. Nothing in Tier 1 is "real" until this file exists.

| Phase | Work | When | P-gate |
|-------|------|------|--------|
| **P-gate** | Architect measured climb on disk (MP3) + memory A/B (MP4), committed FIRST | **NOW** | — |
| **P-bus** | the event-log message bus; refactor agents to emit/consume events | parallel from t=0 | — |
| **P-exec** | wire all Tier-2 executors as real role-separated services on the bus | parallel from t=0 | — |
| **P-viz** | Visualization agent: Gizmo binds to the `measured:true` event stream | after P-bus | — |
| **P-train2** | add Planner as a second trained agent → its own climb on disk | after P-gate | — |
| **P-verify** | L3 formal (X3) + verification report (X7) → full MP5 | after P-gate | — |
| **P-gen** | platform proof: same swarm on the FIFO target | parallel | — |

**Spine:** P-gate → {P-train2, P-viz}. Bus/exec/gen/verify run in parallel from t=0.

---

## 7. The 2-min demo path

**Hero path (slow loop, all measured + the wow layer):**

1. `[Gizmo, concept]` the fridge + QPU + brain block; "every quantum chip needs a brain." 10s.
2. `[live, the swarm working]` Gizmo/dashboard shows the bus firing in sequence on a real design: Research → Architect proposes → RTL generates → Measurement runs Stim/Verilator/Yosys → Verifier gates → Scorer scores → Memory stores. Driven by real events, `measured:true` results pop with their artifact refs.
3. `[proof]` climb — the Architect's measured suppression rising over steps (committed artifact).
4. `[proof]` Pareto — the swarm-designed decoder vs MWPM, near/in the budget box, measured axes.
5. `[proof]` memory — compounding (claim only what the artifact shows: endpoint or slope).
6. `[close, VISION]` two loops — "That's the slow loop, designing the brain. The fast loop — the brain decoding in real time inside the fridge — is the 2040 destination (Riverlane/FPGA precedent). Sellable to labs today as a verifiable hardware-design environment; the quantum brain is the moonshot."

**Viable fallback:** play the committed measured artifacts (climb, Pareto, memory) + verification layers passing on one real generated variant + live HUD eval + FIFO platform proof + a recorded swarm run.

**Backup:** screen-record the hero path off measured data; present live, cut to tape on any stall.

---

## 8. Honest claim ladder (match words to measurement)

| Claim | Earned after |
|-------|--------------|
| "candidate accuracy is measured (RTL on Stim vectors)" | MP0 |
| "each design is real synthesizable RTL, synthesized per variant" | MP1 |
| "the Architect agent is RL-trained on a measured reward and improves" | committed climb |
| "a multi-agent swarm: design agents trained, specialists execute the verified pipeline" | P-bus + P-exec |
| "demonstrated on two targets (decoder + FIFO) — a general engine" | P-gen |
| "we produce manufacturing-ready verified RTL" | — NOT "mass-produced silicon" |
| the fast loop | always "the 2040 direction," NEVER "our chip does this now" |
| vs MWPM/industry | NEVER "we beat MWPM/industry." Gap closing, not closed. |

---

## 9. Definition of done

- [x] Proxy stays dead (CI guards green); reward 100% measured (MP0–MP2).
- [x] Event-bus swarm: 9 roles emitting/consuming; Tier-1 trained, Tier-2 executing.
- [x] Visualization bound to `measured:true` events only (no scripted results).
- [x] L1–L5 gate every score (X3 + X7 land for full MP5; L3 skips when sby absent).
- [x] Planner as a 2nd trained agent with climb artifact path (`planner_climb.json`).
- [ ] **Architect measured climb committed on disk (MP3) + memory A/B (MP4).** ← the gate
- [ ] Platform proof: swarm runs the FIFO target; live HUD eval green.
- [ ] Demo rehearsed; backup recorded off measured data; every claim on its earned rung (§8).
- [ ] Business arc: beachhead (verification env today) + moonshot (quantum brain) + two-loop framing.

---

## 10. Spec rating (honest)

| Dimension | Score | Notes |
|-----------|-------|-------|
| **Truth discipline** | 9/10 | Strong `[BUILT]`/`[VISION]`/`[CLAIMABLE]` tags; keystone + honest ceiling are judge-proof. |
| **Demo viability** | 8/10 | Slow-loop hero path is concrete; fallback/backup paths are well specified. |
| **Technical grounding** | 9/10 | Measured spine + L1–L5 moat + sponsor roles map cleanly to repo modules. |
| **Scope control** | 8/10 | Nine roles but explicitly limits RL to Tier 1 — avoids "everything learns" trap. |
| **Gating clarity** | 10/10 | P-gate (one committed climb) is the right forcing function before swarm claims. |
| **Implementation fit** | 8/10 | Bus/exec/viz/planner/L3/report now exist on `main`; artifact commit + FIFO WSL proof remain. |

**Overall: 8.7/10** — One of the strongest honest hackathon specs in the repo. The remaining gap is operational: run WSL gates, commit `measured_*.json`, rehearse the demo once on measured data.

---

## Quick commands

```bash
# Full SPEC-v6 gate (WSL + OSS CAD)
wsl bash scripts/run_spec_v6_gate_wsl.sh

# Individual gates
wsl bash scripts/run_c5_climb_wsl.sh 5          # P-gate: Architect MP3/MP4
wsl bash scripts/run_planner_climb_wsl.sh 5     # P-train2: Planner climb
wsl bash scripts/run_gen_fifo_wsl.sh 3          # P-gen: FIFO proof
python scripts/build_demo.py                    # Demo bundle (measured-first)

# Unit tests (Windows-safe)
uv run pytest tests/test_swarm_event_bus.py tests/test_swarm_visualization.py tests/test_planner.py -q
```