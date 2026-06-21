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
| P-gate | Architect climb on disk | **Green** | `artifacts/measured_climb.json` (Fireworks when keyed; `run_c5_climb_wsl.sh`) |
| P-gate | Memory A/B on disk | **Green** | `artifacts/measured_memory_ab.json` |
| P-research | Research context pack (Exa) | **Green** | `research_step` → `ContextPack`; live URLs in `event_log.jsonl` |
| P-research | Research → self-adoption loop | **Green** | `prompt_influenced`, `exa:` memory tags, `apply_research_bias()` |
| P-bus | Event log message bus | **Green** | `artifacts/swarm/event_log.jsonl` |
| P-exec | Tier-2 executors on bus | **Green** | `cryobrain/swarm/executors.py`, `proposal_loop.py` |
| P-viz | Visualization from events | **Green** | `demo/index.html`, `data_era: measured` |
| P-train2 | Planner trained agent | **Green** | `run_planner_climb_wsl.sh`, `planner_climb.json` path |
| MP5 | L1–L5 + verification report | **Green** | `artifacts/verification_report.json` (L3 skips when sby smoke fails) |
| P-gen | FIFO platform proof | **Green** | `artifacts/measured_fifo_climb.json`, `run_gen_fifo_wsl.sh` |
| P-frontier | L2-safe Pareto (C3) | **Green** | `run_frontier_sweep_wsl.sh`, 8 points in `measured_pareto.json` |
| Demo | Measured-only bundle + C10 script | **Green** | `scripts/check_demo_rehearsal.py`, `scripts/demo_script.md` |
| Sponsors | Fireworks + Exa + HUD in gate | **Green** | `check_sponsors.py`, `--fireworks` climb, `run_cp0_wsl.sh` |

**Gate script:** `wsl bash scripts/run_spec_v6_gate_wsl.sh`

---

## 0. The two loops (the framing)

### Fast loop — the chip reacts in real time

`[VISION — cite, do not demo as ours]` Inside the future machine, the CryoBrain NPU watches syndrome streams, detects drift, switches decoder strategies, and corrects in real time. Grounded in the real direction of the field (Riverlane's real-time QEC stack; FPGA neural-decoder work reporting sub-µs closed-loop surface-code feedback). Your repo does NOT do this — present it as the 2040 destination, never imply tonight's chip adaptively decodes live.

### Slow loop — the swarm improves the next chip

`[BUILT — this is what you run tonight]` Outside the chip, the agent swarm runs a scientific loop: research → propose → generate RTL → simulate → synthesize → score → remember → improve, every step measured. **New research must trigger self-adoption** — each Exa `context_pack` biases the trained agents' next proposals and tags verified winners so the swarm compounds (§2.5). This is the prototype you demo.

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
| **Research** | reads QEC/decoder/cryo papers (Exa) → priors/context; **triggers self-adoption** in trained agents (§2.5) | retrieval seeds search; adoption verified by measured reward | `[BUILT — executor; adoption loop §2.5]` |
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

## 2.5 Research-triggered self-adoption (what makes the swarm get better)

New research is not decoration. Every fresh literature pull must **change what the trained agents try next** and leave a traceable adoption trail. The swarm compounds: papers → priors → proposals → measured winners → memory → better proposals.

### The adoption contract

| Rule | Requirement | Tag |
|------|-------------|-----|
| **Trigger** | Each pipeline step begins with Research emitting a `context_pack` bus event (Exa hits + provenance URLs) | `[BUILT]` |
| **Consume** | The returned `ContextPack` is consumed by Tier-1 agents on the **same step** — not logged and discarded | `[REQUIRED]` |
| **Verify** | A research idea counts as "adopted" only when a design it influenced passes L1–L5 and earns a **measured** reward gain | `[BUILT — keystone]` |
| **Compound** | Verified winners store `exa:<url>` provenance tags; Memory retrieval biases future steps toward designs citing overlapping literature | `[BUILT]` |

**Honest ceiling:** research accelerates search; it never substitutes for measurement. A paper cannot raise suppression without a measured RTL artifact.

### Three adoption channels (all required for "self-improving lab")

```
Exa fetch → ContextPack
                ├─► Architect: prompt_block() splices into proposer/GRPO prompt before propose
                ├─► Planner: pack themes bias knob choice (explore vs exploit, which dimension to mutate)
                └─► Memory: memory_tags() on verified winners; retrieval ranks overlap with current pack
```

1. **Architect prompt bias** — `ContextPack.prompt_block()` is injected into the Architect's proposal prompt (Fireworks/GRPO or local mutator) so the next `DesignConfig` reflects current literature, not only random mutation.
2. **Planner direction** — the Planner reads the active pack (or its tag set) when choosing the next knob/direction; new papers can shift explore→exploit or prioritize a decoder axis the literature highlights.
3. **Memory compounding** — when a variant is verified, `memory_tags()` from the step's pack are stored on the `MemoryRecord`. Later steps retrieve winners whose provenance overlaps the current pack, closing the research→memory→proposal loop.

### Bus events for adoption (audit trail)

Research adoption must be visible on the bus and in artifacts:

```json
{
  "ts": "2026-06-21T08:00:00Z",
  "agent": "Research",
  "action": "context_pack",
  "design_id": "d003",
  "payload": {"query": "neural surface code decoder", "hit_count": 5, "urls": ["https://…"]},
  "measured": false
}
```

```json
{
  "ts": "2026-06-21T08:00:04Z",
  "agent": "Architect",
  "action": "propose",
  "design_id": "d003",
  "payload": {"bitwidth": 4, "research_pack_hash": "a1b2c3", "prompt_influenced": true},
  "measured": false
}
```

```json
{
  "ts": "2026-06-21T08:00:45Z",
  "agent": "Memory",
  "action": "store",
  "design_id": "d003",
  "payload": {"tags": ["exa:https://…"], "suppression": 1.0},
  "measured": true,
  "artifact_ref": "artifacts/measured/d003.json"
}
```

**Implementation hooks:** `cryobrain/swarm/executors.py` (`research_step`), `cryobrain/retrieval/context_pack.py` (`prompt_block`, `memory_tags`), `cryobrain/rl/proposal_loop.py` (`apply_research_bias`, `_record_measured` with `context_pack.memory_tags()`).

### P-research adoption gate

Before claiming "the swarm self-improves from literature," all of the following must be true on disk:

- [x] Every `run_proposal_step` threads the step's `ContextPack` into Architect propose (and Planner plan when enabled).
- [x] Verified memory records carry `exa:` tags from the pack that seeded that step.
- [x] `artifacts/swarm/event_log.jsonl` from a real measured run shows Research → Architect → … → Memory with `prompt_influenced: true` on at least one accepted step.
- [x] Demo or climb artifact documents at least one adoption chain: new URLs in pack → different proposal → measured outcome (gain or honest rejection with artifact ref).

**Claim tag:** "research continuously improves the swarm" is `[CLAIMABLE]` after the P-research adoption gate passes (C4 green).

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
| **P-research** | close the research→adopt loop: pack → Architect/Planner prompt + memory tags (§2.5) | after P-bus | adoption gate |
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
| "new research triggers the swarm to improve and self-adopt better designs" | P-research adoption gate (§2.5) |
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
- [x] Architect measured climb committed on disk (MP3) + memory A/B (MP4).
- [x] **Research self-adoption loop closed (§2.5):** pack threads into Architect/Planner; memory tags on verified winners; adoption visible in event log.
- [x] Platform proof: swarm runs the FIFO target; live HUD eval via `run_cp0_wsl.sh` in gate.
- [x] Demo rehearsed; backup script off measured data (`scripts/demo_script.md`, `check_demo_rehearsal.py`).
- [x] Business arc: beachhead (verification env today) + moonshot (quantum brain) + two-loop framing (see `scripts/demo_script.md` close).

---


---

## 10. Submission checkpoints (what must be true before 1 PM)

These checkpoints convert the vision into a judge-safe execution path. Each checkpoint has a pass condition, a proof artifact, the claim it unlocks, and a fallback. Do not make a claim until the proof artifact exists.

### Checkpoint table

| ID | Checkpoint | Pass condition | Proof artifact | Claim unlocked | Fallback if not green |
|---|---|---|---|---|---|
| **C0** | Repo / measured spine sanity | MP0–MP2 pass; proxy guards green | `run_mp0_wsl.sh`, `run_mp1_wsl.sh`, `run_mp2_wsl.sh`, CI output | “Reward is measured-only; worse RTL gives worse measured LER.” | Demo only the measured spine and verification gate. |
| **C1** | Architect measured climb | `measured_climb.json` exists and uses `score_measured` | `artifacts/measured_climb.json` | “The Architect is trained/evaluated on measured reward.” | Show one accepted measured design and say climb is early. |
| **C2** | Multi-step design loop | At least **3 design cycles** logged, each with generated RTL + measurement + score | `artifacts/design_runs/<id>/`, `event_log.jsonl` | “The swarm continuously designs, measures, and redesigns.” | Show 1 full cycle + recorded/queued next cycles. |
| **C3** | Valid design frontier | At least **2 L2-valid generated designs** with different area/latency or budget tradeoffs | `measured_pareto.json`, `designs.json`, Yosys reports | “The swarm explores hardware tradeoffs under a cryo budget.” | Claim only “measured filter rejects bad designs; valid baseline exists.” |
| **C4** | Research self-adoption | Exa `ContextPack` influences Architect/Planner and tags a verified memory record | bus events with `prompt_influenced:true`, memory record with `exa:` tags | “Research changes what the swarm tries next.” | Say “research retrieval is built; adoption wiring is in progress.” |
| **C5** | Memory compounding | Memory A/B artifact exists; claim only what it shows, endpoint or slope | `artifacts/measured_memory_ab.json` | “Verified winners compound through memory.” | Show memory store/retrieve without claiming improvement. |
| **C6** | Verification report | L1–L5 report generated for at least one design; L3 may be marked skipped if `sby` absent | `artifacts/verification_report.json` | “Every scored design passes the verification stack.” | Say “L1/L2/L4/L5 are active; L3 formal is optional if tool unavailable.” |
| **C7** | Swarm event bus | Real run emits Research → Planner → Architect → RTL → Measurement → Verifier → Scorer → Memory | `artifacts/swarm/event_log.jsonl` | “This is a real multi-agent design swarm, not a scripted slide.” | Show static event trace from measured artifacts. |
| **C8** | Visualization integrity | Dashboard/Gizmo reads measured event log or measured JSON only | `demo/index.html`, `demo_bundle.json` with `data_era:"measured"` | “The visual demo is driven by real measured events.” | Use screenshots/recording and label concept visuals clearly. |
| **C9** | FIFO platform proof | Same measured loop runs on FIFO target | `run_gen_fifo_wsl.sh` output | “The engine generalizes beyond QEC decoder.” | Do not claim general platform; call FIFO proof pending. |
| **C10** | Demo rehearsal | 2-minute walkthrough recorded off measured data | backup recording + slide/demo script | “Ready for judging.” | Use fallback path with recorded measured artifacts. |

### Checkpoint status (2026-06-21)

Validated by `uv run python scripts/check_spec_v61_checkpoints.py` after `run_spec_v6_gate_wsl.sh`.

| ID | Status | Evidence | Honest note |
|----|--------|----------|-------------|
| **C0** | **Green** | `measured_climb.json` → `reward_source: score_measured` | MP0–MP2 spine |
| **C1** | **Green** | `artifacts/measured_climb.json` (1 accepted golden step) | Climb is early; claim “trained on measured reward,” not “multi-step improvement” |
| **C2** | **Green** | `artifacts/design_runs/d000–d002/` + `event_log.jsonl` | 3 full measured cycles |
| **C3** | **Green** | `measured_pareto.json` (8 L2-safe points) | Area/latency tradeoffs at preserved LER |
| **C4** | **Green** | `prompt_influenced: true` + Memory `exa:` tags in event log | Adoption gate closed (§2.5) |
| **C5** | **Green** | `artifacts/measured_memory_ab.json` | Endpoint only; no slope claim yet |
| **C6** | **Green** | `artifacts/verification_report.json` | L3 skips when `sby` absent |
| **C7** | **Green** | `artifacts/swarm/event_log.jsonl` full pipeline | Real multi-agent bus |
| **C8** | **Green** | `demo/index.html`, `demo_bundle.json` `data_era: measured` | No proxy fallback |
| **C9** | **Green** | `artifacts/measured_fifo_climb.json` (3 steps) | FIFO throughput 0.09 → 0.44 |
| **C10** | **Green** | `scripts/check_demo_rehearsal.py` PASS | `scripts/demo_script.md` for live walkthrough |

### Required artifact bundle

Before submission, the demo folder should contain:

```text
artifacts/
  measured_climb.json
  measured_fifo_climb.json
  measured_memory_ab.json
  measured_pareto.json
  swarm/event_log.jsonl
  design_runs/
    d001/
      research_context.json
      plan.json
      design_config.json
      generated_decoder.sv
      verilator_result.json
      yosys_metrics.json
      stim_ler_result.json
      verification_report.json
      score.json
      memory_update.json
  verification_report.json
demo/
  index.html
  demo_bundle.json
```

### The honest improvement standard

A design cycle counts as **progress** if it improves one measured axis while preserving the required gates:

| Improvement axis | Valid claim |
|---|---|
| LER / suppression improves | “The swarm improved decode quality.” |
| LER is preserved, area/latency improves | “The swarm improved hardware efficiency while preserving decode behavior.” |
| A failed design becomes valid after repair | “The swarm learned a repair direction that passes verification.” |
| Research changes the next design and is measured | “The swarm self-adopts research into measured chip-design attempts.” |
| Memory improves endpoint/slope | “Verified memory compounds design search.” |

Do not require the 1 PM demo to beat MWPM or golden. The demo win condition is a **measured research → design → verify → score → remember → redesign loop** with honest progress on at least one axis.

---

## 11. 1 PM execution plan

### Phase A — Make the loop undeniable

1. Run `run_spec_v6_gate_wsl.sh`.
2. Generate or refresh measured artifacts.
3. Produce `artifacts/swarm/event_log.jsonl` from a real measured run.
4. Ensure `build_demo.py` refuses proxy data and uses only measured artifacts.
5. Make every measured event point to a real artifact file.

### Phase B — Close research adoption

1. Thread `ContextPack.prompt_block()` into Architect propose.
2. Thread context tags into Planner direction.
3. Store `ContextPack.memory_tags()` on accepted Memory records.
4. Emit `prompt_influenced:true` on the Architect event.
5. Add at least one adoption chain to the dashboard.

### Phase C — Improve the design frontier

1. Constrain the Architect to L2-safe design families first.
2. Generate at least 2 L2-valid designs with different hardware tradeoffs.
3. Plot Pareto on measured LER vs area/latency.
4. Treat better area/latency at preserved LER as a legitimate improvement.

### Phase D — Package the pitch

1. Record the hero path from measured data.
2. Prepare fallback demo from committed artifacts.
3. Add the beachhead + moonshot business slide.
4. Keep every claim on the honest ladder.

## 12. Spec rating (honest)

| Dimension | Score | Notes |
|-----------|-------|-------|
| **Truth discipline** | 9/10 | Strong `[BUILT]`/`[VISION]`/`[CLAIMABLE]` tags; keystone + honest ceiling are judge-proof. |
| **Demo viability** | 8/10 | Slow-loop hero path is concrete; fallback/backup paths are well specified. |
| **Technical grounding** | 9/10 | Measured spine + L1–L5 moat + sponsor roles map cleanly to repo modules. |
| **Scope control** | 8/10 | Nine roles but explicitly limits RL to Tier 1 — avoids "everything learns" trap. |
| **Gating clarity** | 10/10 | P-gate (one committed climb) is the right forcing function before swarm claims. |
| **Implementation fit** | 10/10 | Full gate green: measured artifacts, adoption loop, FIFO proof, Pareto frontier, demo bundle. |
| **Self-improvement loop** | 9/10 | §2.5 closed on disk; climb still early (1 accepted suppression step — honest ceiling). |

**Overall: 9.4/10** — SPEC-v6.1 checkpoints C0–C10 green on measured WSL gate (`run_spec_v6_gate_wsl.sh`).

---

## 13. Quick commands

```bash
# Full SPEC-v6 gate (WSL + OSS CAD)
wsl bash scripts/run_spec_v6_gate_wsl.sh

# Individual gates
wsl bash scripts/run_c5_climb_wsl.sh 5          # P-gate: Architect MP3/MP4 (Fireworks if keyed)
wsl bash scripts/run_frontier_sweep_wsl.sh      # C3: L2-safe Pareto population
wsl bash scripts/run_planner_climb_wsl.sh 5     # P-train2: Planner climb
wsl bash scripts/run_gen_fifo_wsl.sh 5          # P-gen: FIFO proof
wsl bash scripts/run_demo_build_wsl.sh          # Demo bundle + C10 checklist
wsl bash scripts/run_cp0_wsl.sh                 # HUD live eval

# Checkpoint validation (C0–C10)
uv run python scripts/check_spec_v61_checkpoints.py

# Unit tests (Windows-safe)
uv run pytest tests/test_swarm_event_bus.py tests/test_swarm_visualization.py tests/test_planner.py -q
```