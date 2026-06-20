# CryoBrain — Spec v2

**The NPU brain inside the quantum chip that keeps it alive.** A real-time neural
QEC decoder, co-designed for accuracy *and* cryogenic hardware constraints, with an
RL environment that finds the accuracy↔hardware Pareto frontier and re-finds it as
the chip scales.

> *By 2040 every quantum chip needs its own NPU — not to run ChatGPT, to survive.*
> CryoBrain takes syndrome bits in and emits corrections in microseconds while
> fitting inside the fridge's power / area / latency budget.

---

## 1. Problem & thesis

Fault-tolerant quantum computing needs a classical "reflex layer" co-located with
the QPU that decodes error syndromes faster than errors accumulate, inside extreme
cryogenic budgets. The live tension (Riverlane, Google Quantum AI, NVIDIA): the most
*accurate* decoders (AlphaQubit-class neural nets) are too *slow/large* for real-time
in-fridge use; the *fast* hardware decoders (MWPM / clustering) trade away accuracy.
No one has a reusable way to **search that frontier** for a given chip + noise regime.

**CryoBrain is the RL environment that co-designs the decoder against both axes,**
each with a verifiable reward. It forks the hackathon's chip plumbing
(`hud-evals/verilog-template`), reuses the mutation-kill verification pattern, and
adds the quantum accuracy axis on top.

### Research statement
Future fault-tolerant quantum computers require a co-located classical decode layer
that corrects syndromes within cryogenic power/area/latency budgets. CryoBrain
prototypes a quantized neural QEC co-processor in RTL plus an RL environment that
co-optimizes decoder architecture against **both** logical error rate (via Stim) and
real hardware metrics (synthesis + an NPU-style cost model). The agent discovers
Pareto-optimal designs and re-optimizes as code distance scales — the co-design loop
needed for scalable hybrid Quantum-AI chips.

---

## 2. Features (expanded)

**F1 — Stim accuracy harness.** Surface-code memory experiment, configurable distance
(d=3,5,7) and noise (depolarizing → circuit-level). Generates syndrome shots with
ground-truth logical flips. Output: logical error rate (LER).

**F2 — MWPM baseline.** PyMatching decoder on the same shots = the anchor every design
is measured against. Reward uses *suppression vs MWPM*, not raw LER, so the number is
meaningful and bounded.

**F3 — Decoder design space.** Agent controls knobs: bitwidth (INT2/4/8), #layers,
parallelism, pipeline depth, sliding-window length. Each config maps to (a) a decode
policy scored by Stim and (b) a hardware footprint scored by the cost model.

**F4 — NPU-style hardware cost model.** Area ∝ MACs×bitwidth + weight memory; latency ∝
depth/parallelism (cycles); power ∝ toggle×MACs×bitwidth. Hard cryo caps on each.
Calibrated against one real Yosys synthesis point.

**F5 — Verifiable reward with a validity gate.** RTL-correctness + cryo-budget are
*gates* (fail → 0); decode quality is the *continuous* reward. (Full detail §4.)

**F6 — RL co-design loop.** Agent proposes designs, env scores, policy improves.
Trained on Modal. Produces the climb chart.

**F7 — RSI distance curriculum.** As the policy clears a distance, the env escalates
d=3→5→7 and re-poses the budget; the decoder co-scales with the chip. The
recursive-self-improvement story, as a chart.

**F8 — One synthesizable design point.** A real `cryo_brain_decoder.sv` synthesized in
Yosys for a true area/cell-count number + a Verilator waveform. Credibility, not
critical path.

**F9 — Pareto explorer.** Plots discovered designs vs MWPM and a neural baseline on the
accuracy↔hardware frontier. The "wow" slide.

---

## 3. Verification checkpoints (you know it's working when…)

Time-boxed against the schedule (Sat 12:30 start · **train by 8 AM Sun** · submit 1 PM Sun).

**CP0 — Tooling (Sat, first hour).** `uv sync` clean; OSS CAD Suite on PATH
(`verilator`, `yosys`, `sby`, `z3` all print versions); `HUD_API_KEY` set.
✅ *Pass:* `hud eval tasks.py claude --task-ids stream-arb-fifo-cocotb-dv --group 1 -y`
returns a score (template runs end to end before you touch it).

**CP1 — Accuracy harness (Sat afternoon).** Stim builds a d=3 surface code; PyMatching
decodes it.
✅ *Pass:* LER rises with physical error rate, and at low error rate MWPM LER is clearly
below the raw physical rate (suppression visible). Flat/nonsensical LER = circuit
wiring wrong — fix before continuing.

**CP2 — Validity gate (Sat afternoon).** Feed a deliberately wrong decoder and the
golden one through the RTL flow.
✅ *Pass:* wrong → reward 0; correct-but-trivial → low non-zero; reference → high.
(Mirror of KillRate weak-vs-strong; template calibrates 0.25/1.0.)

**CP3 — Combined reward + calibration (Sat evening — GATING CHECKPOINT).** Full reward on
~10 rollouts/task.
✅ *Pass:* base-policy reward sits in **20–50% with real variance** (not all-0/all-1).
Saturates high → harder noise/higher distance; all-0 → easier. **Do not train until this
passes** — an uncalibrated run wastes your only overnight window.

**CP4 — Training closes the loop (kick off by 8 AM Sun).** Short RL run on Modal.
✅ *Pass:* reward trends *up* over steps (even modestly). That curve is the climb chart.

**CP5 — Real artifacts (Sun morning).** One Yosys synthesis + one Verilator waveform.
✅ *Pass:* Yosys reports cell count/area without latch/lint errors; waveform shows
syndrome-in → correction-out after N cycles.

**CP6 — Pareto + scaling (Sun, pre-submit).** Plot designs vs MWPM/neural baseline; run
d=3→5→7 curriculum.
✅ *Pass:* a frontier is visible (designs trading accuracy for hardware) and the decoder
re-optimizes at higher distance.

**CP7 — Fallback armed (throughout).** Classical mutant-kill DV (template FIFO arbiter)
runs green, so you can demo a complete chip-track project even if Stim slips.

---

## 4. Reward design (the part that's easy to get wrong)

Two different "accuracies." Never merge them.

1. **RTL correctness → VALIDITY GATE.** Bit-exact vs golden (Verilator) + clean synth
   (Yosys, no latch/lint). Binary. Fail → `reward = 0`. (KillRate "must pass golden.")
2. **Decode quality → CONTINUOUS reward.** LER suppression vs MWPM, from Stim. NEVER
   express as "100% / 72%" — that's the all-or-nothing trap; it won't train.

```python
if not rtl_valid:            # compiles, matches golden, synthesizes, lint-clean
    reward = 0.0
elif not meets_cryo_budget:  # latency/area/power under the fridge envelope
    reward = 0.0
else:
    reward = w_acc  * ler_suppression_vs_mwpm   # continuous, dominant term
           + w_lat  * latency_score             # continuous
           + w_area * area_score                # continuous
    # keep terms <= 3; more weighted terms = more reward-hacking
```
Calibrate noise/distance so a base policy lands **20–50% with variance** (CP3).

---

## 5. `env.py` — what's in the environment file

Following HUD v6 (`env.py`, `grader.py`, `tasks.py`, `task_catalog.py`,
`scenario_helpers.py`), `env.py` defines the environment the agent acts in:

- **Setup / reset.** Materialize the selected task's agent-facing files into `/workdir`
  (decoder RTL stub, spec, harness entry); keep golden + mutants + answer key
  root-owned under `/donotaccess` (uid wall: agent shell runs as unprivileged `agent`).
- **Tools (`@env.tool`).** Edit the decoder design/RTL; `run_eval` triggers the hidden
  flow (Verilator sim + Yosys synth + Stim accuracy run); read observable state (sim
  pass/fail, lint, area, latency, LER). Expose state the agent needs — a silent mutator
  teaches nothing.
- **State / observation.** Current design config, last sim/synth results, current
  distance + noise (so the agent sees its curriculum stage).
- **Grading hook.** Calls `grader.py`'s reward (§4). `env.py` orchestrates; `grader.py`
  owns scoring + the gate.
- **Curriculum control.** A scenario knob for distance + noise; `scenario_helpers` binds
  variants so CP6's d=3→5→7 escalation is just different bound args.
- **Isolation.** Serve/grade as root; agent runs via `setpriv` as `agent`; rollout never
  reads `/donotaccess`.

`tasks.py` binds scenarios to concrete args (distance, noise, budget);
`task_catalog.py` lists the taskset; `grader.py` holds the reward + validity gate.

---

## 6. Research papers we're standing on

**Accuracy anchor / neural decoders**
- *AlphaQubit* (Bausch et al., Nature 2024) — recurrent transformer surface-code
  decoder; beats MWPM on real Sycamore d=3/d=5; Λ≈1.056. Accuracy benchmark + the
  "neural decoders work but are slow" gap.
- *AlphaQubit 2* (arXiv 2512.07737, 2026) — surface + color codes, near-optimal LER at
  scale, faster on color codes. Frontier still moving = room to contribute.
- RL decoders: Sweke et al. (RL decoders for FT-QC); Andreasson et al. (toric-code
  deep-RL decoder). Precedent for RL on the decode problem.

**Latency / hardware anchor (the "brain in the fridge")**
- Riverlane *Local Clustering Decoder* (Nature Communications, 2025) — FPGA, sub-µs per
  round, adaptive. Real-time precedent.
- Riverlane *CC decoder* (Nature Electronics) — ASIC 0.06 mm² / 8 mW decoding >1,000
  qubits. Cryo area/power reference (classical clustering — we model the *neural*
  footprint differently, §4).
- *Real-Time QEC System Stack* (arXiv 2605.30765, 2026) — layered architecture (data
  transport, decode engine, deadlines) CryoBrain sits inside.

**Tooling**
- *Stim* (Gidney) — fast stabilizer simulator; accuracy ground truth.
- *PyMatching* (Higgott) — MWPM decoder; the baseline.

**Classical-fallback lineage (if we ship the verification version)**
- *AutoBench/AutoEval* (Qiu et al., MLCAD 2024) — mutant-based testbench evaluation;
  precedent for mutation kill-rate as a quality metric.
- *VeriReason* (GRPO + testbench feedback) and *VERIRL* — RL for Verilog; VERIRL
  documents the *sparse/binary reward* problem our dense kill-rate / LER reward fixes.

**The gap we claim:** none ship an open RL *environment* that co-optimizes the decoder
*and* its silicon footprint on a verifiable reward. That environment is the deliverable.

---

## 7. Verifiable business path

**What we sell:** the co-design environment + the post-training data/designs it
produces — verified decoder designs that hit a target LER *under* a stated cryo budget.
The value is *verifiable*: each design ships with a simulator-grounded LER and a
synthesis-grounded area/latency, not a claim.

**Why it's a business now (not 2040):**
- YC's current hard-tech RFS explicitly wants semiconductor + physical-world AI; this is
  squarely in-thesis (guaranteed-interview prize feeds F26).
- Buyers exist today: QPU makers running real-time QEC stacks (Riverlane partners —
  Rigetti, OQC, Infleqtion, ORNL — plus IBM/Google internal). They are *actively* buying
  decoder performance under hardware budgets.
- The hackathon's own thesis is the GTM: HUD sells RL environments / post-training data
  to labs. CryoBrain is exactly that artifact, for the quantum control stack.

**Verifiable wedge / moat:** "improve any decoder you can verify." Because the reward is
simulator + synthesis grounded, a customer can *check* the improvement (LER suppression
at fixed budget) — the property that makes labs trust HUD environments. Land with one
QPU partner's noise model; expand to their distance-scaling roadmap (the RSI curriculum
is the upsell).

**The one checkable claim that closes a customer:** "decoder X achieves LER ≤ target at
≤ N cycles / ≤ A mm² on *your* noise model" — reproducible on their hardware.

---

## 8. Build order (scope discipline)

The **environment/reward loop is the centerpiece**; the `.sv` is ONE validating point.
Order: CP0 tooling → CP1 Stim → CP2 gate → **CP3 calibrate (gating)** → CP4 train by
8 AM → CP5 artifacts → CP6 Pareto/scaling. Fallback (CP7) armed throughout.

**Risk register (say it in the pitch, don't hide it):**
- A tiny INT4 net *beating* MWPM in 24h is unlikely → demo the **co-design LOOP and
  frontier**, not the absolute number. Beating MWPM = bonus, not the bet.
- Stim integration is the schedule risk → classical mutant-kill DV fallback is a
  complete project on its own.

---

## 9. Sponsors (meaningful use only — judges penalize stapling)

| Sponsor | Where it's used | Tier |
|---|---|---|
| **HUD** | The environment + grading (forked verilog-template). | Core |
| **Modal** | GPU for RL + parallel Stim sampling. Powers the climb chart. | Core |
| **Google DeepMind** | AlphaQubit authors → judge resonance; accuracy anchor in problem + Pareto; GCP credits if Modal runs dry. | High |
| **Anthropic / Claude** | Build + research copilot; optional config-proposing agent. | High |
| **Exa** | RAG over decoder/cryo literature; grounds slide citations. | Medium |
| **SemiAnalysis** | Mentor resonance — hardware-budget / compute-economics is their beat. Name-drop. | Soft |
| **Antim Labs** | Optional Gizmo concept visual of decoder block next to qubits. | Optional |
| **Skip** | Fireworks (LLM FT; decoder trains on Modal — don't fake), SixtyFour, Protege, MiniMax. | — |

Spine = **HUD + Modal**; real support **DeepMind + Anthropic + Exa**. Six used, zero stapled.

---

## 10. Demo (2 min) — stronger cut

Open cold on the tagline, then ~90s of *real artifacts*, then the frontier.

1. **Architecture (CONCEPT, labeled)** — QPU + CryoBrain NPU in the fridge. 10s.
   "Real benchmark is Verilog + EDA; this shows where it sits."
2. **Waveform (REAL sim — lead visual)** — syndrome bits in → cycles → correction +
   confidence out. Pre-captured image/recording (live gtkwave is a stage risk).
   "Actual RTL; syndrome from a QEC cycle in, correction out."
3. **Netlist still (REAL silicon, 5s)** — Yosys output + area/cell number beside it.
   "Synthesizable hardware, not Python." Don't dwell.
4. **Validity gate (5s)** — wrong decoder → reward 0. The reward is honest.
5. **Climb chart (REAL RL signal — most on-thesis)** — reward rising over steps. "The
   model is learning to design the brain."
6. **Pareto + distance-scaling (the "wow")** — designs vs MWPM vs neural baseline,
   **accuracy = continuous LER suppression (NOT 100%/72%)**, plus d=3→5→7 re-optimization.
   "Fast-but-dumb here, smart-but-slow there; the agent finds the budget-feasible sweet
   spot, and re-finds it as the chip scales."
7. **Close** — survival tagline + open problem (Riverlane/Google/DeepMind) + the
   one-line business: "verified decoders under a cryo budget — sellable to every QPU
   maker today." Sit down.

**Visual integrity rule:** waveform, netlist, synthesis numbers, climb chart come from
the *actual* Stim/Verilator/Yosys/RL flow. Only the architecture diagram is hand-drawn,
labeled "concept."

If training stalls: cut #5–#6's RL framing, demo env + gate + one design point + the
classical fallback. Still complete.

---

## 11. Definition of done
- [ ] CP0–CP6 green (CP3 calibration the hard gate).
- [ ] Reward = validity gate + continuous LER-suppression + hardware, in 20–50% band.
- [ ] Real waveform + real synthesized design point (area number).
- [ ] Climb chart from a real (even short) Modal run.
- [ ] Pareto + distance-scaling with *continuous* accuracy.
- [ ] One-line verifiable business claim on the closing slide.
- [ ] CP7 classical fallback armed.
