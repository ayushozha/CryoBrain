# CryoBrain — Spec v3 (parallel build)

**The NPU brain inside the quantum chip that keeps it alive.** A self-improving RL
environment in which an AI learns to design real-time neural QEC decoders — graded on
accuracy (Stim) *and* cryogenic hardware budget (Yosys) — with a **memory** that
compounds verified designs and a **curriculum** that scales the brain as the chip scales.

> *By 2040 every quantum chip needs its own NPU — not to run ChatGPT, to survive.*
> CryoBrain is the environment that teaches AI to design that brain, and proves every
> improvement against a simulator instead of claiming it.

---

## 0. What this actually is (read first — no more confusion)

Three layers, all real, all distinct:
- **The chip** = `cryo_brain_decoder.sv` — a synthesizable Verilog decoder block
  (syndrome in → correction out). The artifact a model produces.
- **The environment** = the verifiable grader: accuracy (Stim LER) + hardware (Yosys/cost
  model), with an RTL-correctness validity gate. Scores any candidate chip.
- **The AI** = an RL loop that writes decoders, is scored by the environment, and improves
  — augmented with **memory** (conditions on its best past designs) and a **curriculum**
  (escalates code distance). The self-improving system.

The deliverable is the **environment + the self-improving loop**. The chip is what the
loop produces. "Improving at chip design from its own verified attempts" is the thesis.

---

## 1. Scope (locked)

| Tier | Item | Status |
|---|---|---|
| **CORE** | RL loop: model writes decoder → verifiable reward + correctness gate → train → climb chart. Benchmark/Pareto. | Must ship |
| **MEMORY** | Top-K verified-design buffer, retrieved as context so improvement compounds. | First-class (do after core climbs) |
| **STRETCH 2** | Distance curriculum d=3→5→7; brain co-scales with chip. | If time |
| **FROZEN** | No new substrate, no new framings, **no "beat industry standard" claim** (show the gap *closing*). | — |

**Honest framing rule:** beating MWPM / commercial EDA overnight is unlikely. Win on the
**self-improving loop with a verifiable reward**, not the absolute number. Approaching the
baseline *while demonstrably climbing* beats a static good design.

---

## 2. Parallel workstreams (for multiple agents)

The reward function is the **contract** between workstreams — agree its signature first,
then everyone builds against it independently.

```
REWARD CONTRACT (freeze this signature first):
  score(design) -> {reward: float, valid: bool, ler: float,
                    area_um2: float, latency_cycles: int, power_mw: float}
  - valid=False (RTL incorrect OR over cryo budget) => reward 0.0
  - else reward = continuous (LER-suppression dominant) in [0,1]
```

| WS | Owner-agent | Deliverable | Depends on | Interface out |
|---|---|---|---|---|
| **WS1 Environment core** | A | `grader.py` reward + validity gate; HUD `env.py` wrapper (forked verilog-template) | reward contract | `score()` |
| **WS2 Accuracy + benchmark** | B | Stim LER harness + `benchmark.py` (DONE — extend to score a real decoder) | — | `measure_ler()`, Pareto plot |
| **WS3 The chip (RTL)** | C | `cryo_brain_decoder.sv` (synth) + Yosys area + Verilator waveform | reward contract | `.sv` + 1 real hardware point |
| **WS4 RL loop** | D | rollout-against-reward + GRPO (HUD/Fireworks on Modal) + climb chart | WS1 `score()` | trained model + climb data |
| **WS5 Memory** | E | top-K verified-design buffer + retrieval-into-context | WS4 rollout hook | `retrieve(task)->exemplars` |
| **WS6 Curriculum + viz** | F | distance escalator + Pareto/scaling charts | WS1 scenario knob | curriculum tasks, final plots |
| **WS7 Demo + business** | G | slides, pitch, beachhead+moonshot narrative, visual integrity | all | the 2-min demo |

Dependency spine: **WS1 → WS4 → {WS5, WS6}**. WS2/WS3/WS7 run fully in parallel from t=0.

---

## 3. Features

**Core**
- **F1 Stim accuracy harness** — surface-code LER, d/noise configurable. (DONE)
- **F2 MWPM baseline** — PyMatching anchor; reward = suppression vs MWPM. (DONE)
- **F3 Decoder design space** — bitwidth (INT2/4/8), layers, width, parallelism, pipeline.
- **F4 NPU cost model** — area∝MACs×bitwidth+memory; latency∝depth/parallelism; power proxy. (DONE)
- **F5 Verifiable reward + validity gate** — §4.
- **F6 RL co-design loop** — model writes decoder, env scores, GRPO steps → climb chart.

**Memory (the compounding moat)**
- **F7 Verified-design memory** — persistent buffer of top-K `(design, reward, metrics)`,
  all reward-verified. On each rollout, retrieve the M most-relevant past designs (matched
  on distance/budget) and inject as few-shot exemplars: "high-scoring designs for similar
  constraints." Improvement compounds because the model conditions on its own best work.
  Verifiability preserved — memory only ever stores designs that passed the gate, so it
  never injects garbage. (This is the "Re:Call" idea: retrieval feeding a retry-improve loop.)
- **F7.1 (stretch) external memory** — Exa RAG over decoder literature to seed priors.

**Stretch 2 (the scaling story)**
- **F8 Distance curriculum** — when the policy clears a reward threshold at d, escalate
  d→d+2 and re-pose the cryo budget; the decoder re-optimizes. Brain co-scales with chip.
- **F9 Pareto explorer** — designs vs MWPM vs neural baseline; the "wow" slide.

**Credibility**
- **F10 One synthesizable design point** — real `.sv` through Yosys (area) + Verilator (waveform).

---

## 4. Reward design (do not get this wrong)

Two different "accuracies." Never merge.
1. **RTL correctness → VALIDITY GATE.** Bit-exact vs golden (Verilator) + clean synth
   (Yosys). Binary. Fail → reward 0. ("Stay true to the original design.")
2. **Decode quality → CONTINUOUS reward.** LER suppression vs MWPM (Stim). NEVER "100%/72%".

```python
if not rtl_valid:            reward = 0.0
elif not meets_cryo_budget:  reward = 0.0
else:                        reward = w_acc*ler_suppression + w_lat*latency_score + w_area*area_score
#                            keep terms <= 3 to avoid reward-hacking
```
Calibrate noise/distance so a base policy lands **20–50% with variance** (CP3, the gate).

---

## 5. `env.py` contents (HUD v6 template)

- **Setup/reset:** materialize task files to `/workdir` (decoder stub, spec); golden+mutants+
  answer key root-owned under `/donotaccess` (uid wall; agent shell = unprivileged `agent`).
- **Tools (`@env.tool`):** edit decoder/RTL; `run_eval` → Verilator sim + Yosys synth + Stim
  accuracy; read observable state (sim pass/fail, lint, area, latency, LER, current distance).
- **Grading hook:** calls `grader.py` `score()` (§4). `env.py` orchestrates; `grader.py` scores.
- **Memory hook:** before generation, call WS5 `retrieve(task)`; append exemplars to the prompt.
- **Curriculum knob:** scenario param for distance+noise; `scenario_helpers` binds variants.
- **Isolation:** serve/grade as root; agent via `setpriv`; rollout never reads `/donotaccess`.

---

## 6. Checkpoints (you know it works when…)

- **CP0 Tooling:** `hud eval` green on stock `stream-arb-fifo-cocotb-dv`.
- **CP1 Accuracy:** Stim LER suppresses with distance below threshold. (DONE — benchmark.py)
- **CP2 Gate:** wrong decoder → 0; reference → high.
- **CP3 Calibration (GATING):** base reward 20–50% w/ variance. **No training until green.**
- **CP4 Training closes loop:** reward trends up over steps → climb chart.
- **CP5 Memory compounds:** with memory on, reward rises *faster* / to a *higher* plateau than
  without (run both, overlay the curves — that A/B is the memory proof slide).
- **CP6 Curriculum:** decoder re-optimizes at d=5,7; scaling chart.
- **CP7 Artifacts:** real Yosys area + Verilator waveform.
- **CP8 Fallback armed:** classical mutant-kill DV runs green throughout.

---

## 7. Research we stand on
- **Accuracy:** AlphaQubit (Nature 2024, beats MWPM on Sycamore, Λ≈1.056); AlphaQubit 2
  (2026, surface+color, near-optimal, faster). RL decoders (Sweke; Andreasson toric).
- **Hardware/"brain in the fridge":** Riverlane LCD (sub-µs FPGA); CC decoder ASIC
  (0.06 mm²/8 mW, >1000 qubits); Real-Time QEC System Stack (2026).
- **Tooling:** Stim (Gidney), PyMatching (Higgott).
- **Fallback lineage:** AutoBench/AutoEval (mutant testbench eval); VeriReason/VERIRL (RL
  for Verilog; VERIRL documents the sparse-reward problem our dense reward fixes).
- **Gap claimed:** no open RL *environment* co-optimizing decoder + silicon footprint on a
  verifiable reward, with memory + curriculum. That's the deliverable.

---

## 8. Verifiable business path (beachhead + moonshot)

**Do NOT claim "sell a quantum decoder today."** The honest, stronger story:

**What we built:** a verifiable RL environment that trains models to do hardware design
under hard constraints — every improvement *checkable* against a simulator, not claimed.

**Beachhead (revenue path today):**
1. *Frontier labs* — need verifiable environments + post-training data for hardware/coding
   models. This is literally HUD's business; we build the category the host sells. Built-in buyer.
2. *Chip/EDA companies* — verification is ~70% of design cost and least-automated; AI-for-
   verification is being funded *now* (SigmanticAI, Visibl, YC 2026). Our classical KillRate
   harness is the today-product beachhead.

**Moonshot (the wow):** the same engine pointed at quantum decoder co-design (CryoBrain) —
the 2040 "brain in the fridge," buyers = QPU makers running real-time QEC stacks.

**Moat (one line):** *improve any hardware design you can verify.* Simulator-grounded reward
means improvements are checkable — the property labs pay for and vibes-based tools can't offer.
**Memory is the asset:** the environment accumulates *verified* design knowledge and compounds
— the more it runs, the more valuable it gets. That's a defensible, appreciating asset, not a
one-off model.

**The one checkable claim that closes a customer:** "design X hits LER ≤ target at ≤ N cycles /
≤ A area on *your* noise model" — reproducible on their hardware.

---

## 9. Sponsors (meaningful use only)
| Sponsor | Use | Tier |
|---|---|---|
| **HUD** | Environment + grader (forked verilog-template). | Core |
| **Modal** | GPU for RL + parallel Stim sampling; powers climb chart. | Core |
| **Fireworks** | GRPO RFT of the open code model (skip if custom net on Modal). | Core-if-training |
| **Google DeepMind** | AlphaQubit authors → judge resonance; accuracy anchor; GCP credits. | High |
| **Anthropic/Claude** | Build+research copilot; eval baseline; config-proposing agent. | High |
| **Exa** | RAG: external memory (F7.1) + slide citations. | Medium |
| **SemiAnalysis** | Mentor resonance — hardware-budget/compute-econ framing. | Soft |
| **Antim Labs** | Optional concept visual of brain next to qubits. | Optional |
| **Skip** | SixtyFour, Protege, MiniMax — no honest fit. | — |

Spine = HUD + Modal (+ Fireworks if training). Real support: DeepMind + Anthropic + Exa.

---

## 10. Demo (2 min) — strongest cut
1. **Architecture (CONCEPT, labeled)** — QPU + CryoBrain NPU in the fridge. 10s.
2. **Waveform (REAL sim — lead)** — syndrome in → correction out. Pre-captured.
3. **Netlist still (REAL silicon, 5s)** — Yosys area number. "Synthesizable, not Python."
4. **Validity gate (5s)** — wrong decoder → 0. Honest reward.
5. **Climb chart (REAL RL — most on-thesis)** — reward rising over steps.
6. **Memory A/B (the differentiator)** — with-memory vs without-memory curves; memory climbs
   faster/higher. "It compounds — it remembers what works."
7. **Pareto + distance-scaling (wow)** — designs vs MWPM/neural; accuracy = *continuous* LER
   suppression (NOT 100%/72%); d=3→5→7 re-optimization.
8. **Close** — survival tagline + open problem (Riverlane/Google/DeepMind) + business:
   "verifiable hardware-design environments — sellable to labs today, quantum is the moonshot."

**Visual integrity:** waveform/netlist/synthesis/climb come from the real Stim/Verilator/Yosys/RL
flow. Only the architecture diagram is hand-drawn, labeled "concept." If training stalls: cut
5–7's RL framing, demo env+gate+one design point+classical fallback. Still complete.

---

## 11. Definition of done
- [ ] CP0–CP7 green (CP3 the hard gate; CP5 memory A/B is the differentiator).
- [ ] Reward = validity gate + continuous LER-suppression + hardware, 20–50% band.
- [ ] Real `.sv` → Yosys area + Verilator waveform.
- [ ] Climb chart (real Modal run) + memory-on-vs-off overlay.
- [ ] Pareto + distance-scaling with continuous accuracy.
- [ ] Beachhead+moonshot business slide; one checkable customer claim.
- [ ] CP8 classical fallback armed.