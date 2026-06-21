# CryoBrain — Full Spec (the 2040 build)

**A Quantum AI chip: an NPU "brain" co-located with the qubits that corrects errors in
real time — and a verifiable RL environment where an AI designs and improves that brain,
every result MEASURED. The decoder is the starting point; the engine generalizes to the
next generation of quantum-AI chips.**

> **Read the tags.** Each section is marked **[BUILT]** (real now), **[CLAIMABLE]** (say it
> after the checkpoint passes), or **[VISION]** (the 2040 arc — frame as future, never as done).
> If you say a [VISION] line as [BUILT], a judge sinks you. Match words to measurement (§12).

> **Keystone rule (every line obeys):** a design change must produce a **measured** change in
> accuracy and hardware — never a formula. Swap in a worse decoder → the measured number must
> drop. That single test is the difference between this being real and being a gimmick.

> **Honest ceiling:** reachable tonight = an AI proposing **measured** designs, climbing,
> **approaching** MWPM. NOT "we beat industry decoders." Show the gap **closing**.

---

## 0. The arc (what this is — honestly)

- **[VISION] 2040:** every fault-tolerant quantum chip ships with a co-located AI decoder
  ("the brain in the fridge") that keeps it alive. Those decoders are *designed by AI* in
  verifiable environments, then synthesized to silicon and mass-produced.
- **[VISION] The company:** the environment that designs and verifies those brains — and,
  generalized, any hardware accelerator you can simulate + synthesize + score.
- **[BUILT] Tonight's prototype:** a working verifiable environment that designs a *measured*
  surface-code decoder, improves it with a learning loop, and proves every number against
  Stim physics + Yosys synthesis. The decoder is the first instance of the general engine.

The pitch is the arc; the demo is the prototype. Never blur them.

---

## 1. Problem & value (why anyone pays)

**[BUILT — the problem is real and citable]** Fault-tolerant QC needs a classical decoder
co-located with the QPU that corrects syndromes faster than errors accumulate, inside
cryogenic power/area/latency budgets. The open tension: accurate decoders (AlphaQubit-class
neural nets) are too slow/large for real-time in-fridge use; fast hardware decoders (MWPM,
clustering) trade away accuracy. No reusable environment exists to *search and verify* that
frontier per chip + noise regime.

**[CLAIMABLE] The value:** a verifiable RL environment that *generates, measures, and verifies*
decoder designs on two grounded axes (Stim accuracy, Yosys hardware). Output = verified,
synthesizable RTL meeting a stated budget — reproducible on a customer's noise model.

**[VISION → CLAIMABLE-as-beachhead] Who pays, today:**
- *Frontier labs* — need verifiable environments + post-training data for hardware/coding
  models. This is HUD's own market; we build the category the host sells.
- *Chip/EDA + QPU makers* — verification is ~70% of design cost and least-automated; AI-for-
  verification is being funded now (SigmanticAI, Visibl, YC 2026). QPU makers (Riverlane
  partners: Rigetti, OQC, Infleqtion) buy decoder performance under hardware budgets.

**Moat (one line):** *improve any hardware design you can verify.* Simulator + synthesis
grounding means improvements are **checkable** — the property labs pay for and vibes-based
tools can't offer. Memory makes it an **appreciating asset**: it accumulates verified designs.

---

## 2. The four real components (the measured engine)

| # | Component | Tag | What makes it real |
|---|---|---|---|
| 1 | **Measured accuracy** (P0, keystone) | [BUILT-after-P0] | Stim error vectors → real RTL in Verilator → did it correct the error → real LER. Replaces the proxy. |
| 2 | **RTL is the artifact** (P1) | [BUILT-after-P1] | Parametric generator → different real `.sv` per design; Yosys synthesizes each → real area/latency. |
| 3 | **An AI that learns** (P2) | [BUILT-floor / CLAIMABLE-GRPO] | Model proposes designs/RTL → measured reward → improves (memory floor; GRPO target). |
| 4 | **Environment + demo** | [BUILT] | Stim anchor, validity gate, reward API, dashboard. True once 1–3 feed it measured numbers. |

**KILL LIST (do first):** delete `simulate_candidate_ler` / `decoder_quality_multiplier` from
grading. No candidate accuracy may come from a formula. (See P0 below.)

### P0 — measured accuracy (Agent A; nothing real before this)
`measure_candidate_ler(rtl_path, distance, noise, shots) -> {candidate_ler, mwpm_ler, suppression, ...}`
where `candidate_ler` comes from running `rtl_path` in Verilator on Stim-derived syndrome
vectors and comparing predicted vs true logical flip. **Acceptance: worse `.sv` → worse number.**

### P1 — RTL generator + per-variant synth (Agent B)
`generate_rtl(DesignConfig) -> .sv` (pipeline/width/parallelism become real Verilog);
`synth_metrics(rtl_path) -> {area_um2, latency_cycles, power_mw, valid}` (real Yosys per variant).
**Acceptance: 3 configs → 3 distinct `.sv` → 3 distinct measured (area, latency, LER).**

### P2 — learning policy (Agent C)
Floor: model (Grok/Fireworks) proposes designs against measured reward; reward-ranked winners
compound via memory. Target: GRPO on Modal — real weight updates, real climb of *measured*
quality. **Acceptance: climb chart plots measured suppression rising.**

---

## 3. Verification layers (the moat — crucial)

A design is **never claimed until it passes every layer**. This stack *is* the product —
it's what makes outputs trustworthy and sellable.

| Layer | Tool | Gate |
|---|---|---|
| **L1 Functional correctness** | Verilator | decoder RTL runs, produces valid corrections; bit-exact vs golden where applicable. Fail → reward 0. |
| **L2 Decode accuracy (measured)** | Stim + Verilator | measured LER on real error vectors (P0). The accuracy axis. |
| **L3 Formal checks** | SymbiYosys + Z3 (template) | assertions / equivalence where defined; no illegal states. |
| **L4 Synthesis sign-off** | Yosys | synthesizes clean, no latches, lint pass, area/latency extracted (P1). |
| **L5 Budget gate** | cost model + L4 | meets cryo latency/area/power envelope. Fail → reward 0. |

**[CLAIMABLE]** "Every design that scores is verified across five layers — functional, formal,
synthesis, measured-accuracy, and budget — before we report a number." That sentence is your
credibility and your moat in one.

---

## 4. Real benchmarks (what we measure and show)

| Benchmark | Plot | Tag |
|---|---|---|
| **Error suppression** | LER vs physical error rate, per distance, vs MWPM (canonical QEC threshold plot) | [BUILT — `benchmark.py` produces this real] |
| **Accuracy↔hardware Pareto** | measured candidate LER vs **per-variant Yosys** area/latency; budget box; MWPM anchor | [BUILT-after-P0/P1] |
| **Learning climb** | measured suppression rising over training steps | [BUILT-after-P2] |
| **Memory A/B** | with vs without memory; claim **only** the artifact's truth (endpoint or slope) | [BUILT] |
| **Distance scaling** | re-optimization at d=3→5→7 | [BUILT — curriculum] |

Benchmark integrity: y-axes labeled "measured LER (Verilator)" vs "MWPM (Stim)". Suppression
may be negative early — that's honest and fine; the story is the *trend*, not the absolute.

---

## 5. RL learning loop + model training

**[BUILT-floor]** Model-in-the-loop: Grok/Fireworks proposes `DesignConfig`/RTL diff (prompted
with retrieved memory exemplars) → sample N → generate RTL (§2) → measure (§3,§P0) →
reward-rank → winners feed back through memory. Effective policy improves via context + memory.

**[CLAIMABLE-after-run]** GRPO target: roll out proposals → measured reward → GRPO weight
update → repeat, on Modal, rollouts/measurement fanned across GPUs. Real training run, real
weight updates. Curriculum (d=3→5→7) staged into progression.

Reward (fully measured):
```
if not all_verification_layers_pass(§3):  reward = 0.0
else: reward = w_acc*measured_suppression + w_lat*latency_score + w_area*area_score   # <=3 terms
```

---

## 6. Generalization — the platform [VISION → CLAIMABLE-with-one-proof]

The engine is **not decoder-specific**. The contract is: *any hardware-design target you can
(a) parameterize/generate as RTL, (b) simulate for a measured quality signal, (c) synthesize
for hardware cost, and (d) gate for correctness* plugs into the same loop.

- **[BUILT] Proven axes of generality now:** code distance (curriculum), noise model, decoder
  design space.
- **[CLAIMABLE with the platform proof]** Run the *same environment* on a second, unrelated RTL
  target — your classical FIFO/arbiter task — and show it optimizing there too. One extra data
  point converts "a quantum decoder tool" → "a general hardware-design engine, shown on 2 targets."
- **[VISION] Next-gen quantum-AI chips:** surface→color codes, larger logical blocks, the full
  control plane (calibration, readout, scheduling) — all expressible in this loop. State this as
  the roadmap, not as done.

**Honest line:** "Designed to generalize; demonstrated on two hardware targets; roadmap to the
full quantum control plane." Never "it already designs any chip."

---

## 7. Manufacturability path [VISION — frame as path, not done]

- **[BUILT]** Output is **synthesizable, standard-cell RTL** that passes Yosys sign-off (L4) —
  i.e. the *input a foundry/ASIC flow consumes*, not a toy.
- **[CLAIMABLE]** "We produce manufacturing-ready, verified RTL" — true (RTL that synthesizes and
  passes verification). NOT "we mass-produced a chip."
- **[VISION] Path to silicon:** verified RTL → place&route → tape-out → ASIC, the same path
  Riverlane's CC decoder ASIC (0.06 mm²/8 mW, >1000 qubits) took. Cite it as the precedent that
  the in-fridge ASIC brain is real and manufacturable — the destination of this pipeline.

Do not claim mass production. Claim: "the artifact is what mass production starts from."

---

## 8. Sponsors (mapped to real roles in the measured pipeline)

| Sponsor | Concrete role | Tag |
|---|---|---|
| **HUD** | The environment + grader + live `hud eval` (forked verilog-template). | [BUILT] Core |
| **Modal** | GPU for GRPO + **parallel per-variant measurement** (Verilator/Stim fan-out). | [Core-training] |
| **Fireworks** | The proposer/policy model; GRPO RFT loop. | [Core-training] |
| **Google DeepMind** | AlphaQubit authors → accuracy anchor + judge resonance; GCP credits. | High |
| **Anthropic/Claude** | Build/research copilot; eval baseline; analysis. | High |
| **Exa** | RAG: seed memory with decoder literature; ground benchmark citations. | Medium |
| **Daytona** | Snapshot/fork measurement workdirs for reproducible per-variant runs. | Medium (real fit now that measurement is per-variant) |
| **Antim Gizmo** | Concept scene (cryostat + QPU + brain block) — demo bookend, tagged "concept". | Optional |
| **SemiAnalysis** | Mentor resonance — manufacturability/compute-economics framing. | Soft |
| **Skip** | SixtyFour, Protege, MiniMax — no honest fit. | — |

Spine = HUD + Modal + Fireworks. Real support: DeepMind + Anthropic + Exa + Daytona.
Every entry is a *function in the pipeline*, not a logo. Don't staple.

---

## 9. Parallel agents (Grok Composer) — freeze §2 interfaces first

| Agent | Owns | Start | Blocks |
|---|---|---|---|
| **A** | P0 measured LER (Stim→Verilator→real LER) | NOW | everything |
| **B** | P1 parametric RTL gen + per-variant Yosys | NOW | feeds A & C |
| **C** | P2 policy: floor then GRPO on Modal | when A returns real reward | the climb |
| **D** | dashboard truth-up + benchmarks + Gizmo bookend | NOW, refine as A/B land | — |
| **E** | live HUD eval (CP0) + platform proof (FIFO target, §6) | NOW | credibility + generality |
| **F** | verification layers L1–L5 wired into the gate (§3) | NOW | trust |

Spine A→C; B parallel into A/C; D/E/F parallel from t=0.

---

## 10. Checkpoints (measured)
- **MP0** worse `.sv` → worse measured LER (no proxy). **MP1** 3 configs → 3 real distinct
  variants. **MP2** reward moves only on measured change. **MP3** measured climb. **MP4** memory
  A/B (claim only measured truth). **MP5** all 5 verification layers gate the score.
  **CP0** live `hud eval` green. **GEN** same env optimizes the FIFO target. **CP8** classical
  fallback armed.

---

## 11. The 2-min demo path (+ viable fallback)

**Hero path (everything measured):**
1. **[Gizmo, concept]** the fridge, qubit erroring, "it needs a brain — accurate AND tiny." 10s.
2. **[live] The AI designs a decoder** — show the policy propose a design; RTL generated.
3. **[live] It gets verified + measured** — the 5 layers pass; measured LER + Yosys area appear.
   ("Wrong design → reward 0" flashed for honesty.)
4. **[benchmark] Climb** — measured suppression rising over steps.
5. **[benchmark] Pareto** — the AI-designed decoder vs MWPM, in/near the budget box; measured axes.
6. **[benchmark] Memory A/B + distance scaling** — it compounds and co-scales.
7. **[close, VISION] arc** — "This is the prototype of the brain every quantum chip needs by
   2040. The engine generalizes to any hardware you can verify. Verified RTL is what a fab
   consumes. Sellable to labs today; the quantum brain is the moonshot."

**Viable fallback (if GRPO/measurement of the live design stalls):** show the *pre-measured*
artifacts (climb, Pareto, memory from a completed run) + the verification layers passing on one
real generated variant + live HUD eval + the FIFO platform proof. Still fully honest, still complete.

**Backup:** screen-record the hero path; present live, cut to tape on any stall.

---

## 12. Honest claim ladder (match words to measurement)
- After P0: "candidate accuracy is **measured** (RTL on Stim vectors)." 
- After P1: "each design is **real synthesizable hardware**, synthesized per variant." 
- After P2 floor: "a model **proposes** designs against the measured reward; winners compound." 
- After P2 GRPO: "a model is **trained (GRPO)** to design better decoders, measured." 
- With §6 proof: "demonstrated on **two** hardware targets — a general engine." 
- §7: "we produce **manufacturing-ready verified RTL**" (NOT "mass-produced silicon"). 
- NEVER: "we **beat** MWPM / industry." Show the gap **closing**.

---

## 13. Definition of done
- [ ] Proxy deleted; reward 100% measured (MP0–MP2).
- [ ] Parametric RTL gen + per-variant Yosys; 3+ real distinct variants.
- [ ] All 5 verification layers gate the score (MP5).
- [ ] Learning policy improving on measured reward (floor shipped; GRPO attempted).
- [ ] Benchmarks real: suppression curve, measured Pareto, climb, memory A/B, distance scaling.
- [ ] Generalization shown on a 2nd target (FIFO); live HUD eval green; classical fallback armed.
- [ ] Demo path rehearsed; backup recorded; every claim on its earned rung (§12).
- [ ] Business arc slide: beachhead (verification env today) + moonshot (quantum brain) + moat (verifiable, compounding).