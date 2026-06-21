# CryoBrain — What the Spec Said vs What Actually Got Built

**Purpose of this doc:** Feed this to the next agent (or judge) so nobody mistakes the demo for real chip co-design. Written after someone looked at the live dashboard and said: *"what the heck, this is not a real chip design."* They were right.

---

## TL;DR

| SPEC4 / dashboard implied | Repo reality |
|---|---|
| "The AI writes decoders" / RTL is the artifact the loop produces | **One fixed** `cryo_brain_decoder.sv` — never mutated by training |
| Climb chart = learning to design better chips | Climb chart = **searching 5 integer knobs** against a **proxy formula** |
| Stim scores the candidate decoder | Stim scores **MWPM only**; candidate LER is **simulated** from knobs |
| Pareto = accuracy vs synthesized cryo hardware | Pareto = formula cost model + **one** Yosys pass on static RTL |
| Memory compounds verified **designs** | Memory stores past **knob vectors** that scored well on the proxy |
| Live dashboard proves the chip works | Dashboard honestly plots **real JSON** from a **knob-tuning loop** — not tape-out |

**What the spec was actually for:** scaffold a **verifiable RL grading environment** (Stim + RTL gate + reward API) and a **demo narrative** for a hackathon. It was **not** a spec for shipping neural QEC decoder silicon.

---

## What SPEC4 claimed (§0)

From `SPEC4.md`:

> - **The chip** = `cryo_brain_decoder.sv` — synthesizable Verilog (syndrome in → correction out). **The artifact a model produces.**
> - **The AI** = an RL loop that **writes decoders**, is scored by the environment, and improves

Honest-claim footnote in the same file:

> Say "optimization driven by a verifiable reward," not "the AI authors RTL from scratch" (that's only true once the Fireworks GRPO path is real).

**Reality:** The footnote is the truth. The §0 bullets oversell. The loop does **not** write decoders. Fireworks GRPO is scaffolded, not driving RTL edits in the shipped path.

---

## The "chip" is one static RTL file

Agent-facing RTL (`tasks/cryo_brain_decoder/rtl/cryo_brain_decoder.sv`):

```systemverilog
// Agent-facing starter RTL (intentionally minimal — improve for reward).
...
        end else if (syndromes_valid) begin
            // Buggy starter: bitwise OR instead of XOR
            corr_q <= syndromes[3:0] | syndromes[7:4];
```

- This module is **not** regenerated per training step.
- "Training" never patches XOR→XOR, never adds pipeline stages in Verilog, never changes parallelism in hardware.
- Verilator VCD / Yosys always run on **this same file** (or golden/wrong variants for calibration).
- The waveform panel in the dashboard shows **that one block toggling** — not a family of synthesized variants.

**Verdict:** The chip is a **props module** for the validity gate and demo waveform, not the output of co-design.

---

## What "RL training" actually does

Implementation: `cryobrain/rl/local_trainer.py`

The search space is `DesignConfig`:

- `bitwidth`, `num_layers`, `parallelism`, `pipeline_depth`, `window_length`

Mechanism:

1. Start from ~8 **preset** knob tuples (`_design_sweep`).
2. Each step: pick/mutate knobs (optionally biased by memory exemplars).
3. Stage a workdir with `design_config.json` + **unchanged** RTL.
4. Call hidden `grade.py` → scalar reward.
5. Accept if reward improves; append to climb chart JSON.

This is **discrete hyperparameter search with memory**, not GRPO over RTL, not gradient-based policy learning over a neural decoder.

Modal / Fireworks hooks exist (`cryobrain/rl/modal_train.py`, `propose_design_config`) but the **green checkpoint path** that produced demo artifacts is `run_memory_ab_wsl.sh` / `local_trainer` on **knob configs**.

---

## The reward is mostly a proxy — this is the core gimmick

### MWPM anchor (real)

`cryobrain/accuracy/stim_harness.py` builds real Stim surface-code circuits. PyMatching MWPM LER is measured on sampled shots. **This part is legitimate physics.**

### Candidate LER (fake)

`cryobrain/accuracy/decoder_policy.py` — file header says it explicitly:

> Maps `DesignConfig` to a candidate logical error rate … **before a trained net exists.**

```python
def simulate_candidate_ler(design, mwpm_ler, *, rtl_valid=True):
    if not rtl_valid:
        return mwpm_ler * 1.25
    return mwpm_ler * decoder_quality_multiplier(design)
```

`decoder_quality_multiplier` is a hand-tuned analytic function of the five knobs (bitwidth curves, layer penalty, pipeline penalty, etc.). **Changing `parallelism` in JSON does not run a different neural net.** It scales LER by a formula calibrated so the default starter lands ~18% suppression vs MWPM.

So when the climb chart shows 0.364 → 0.459 → 0.501:

- The **numbers are real outputs of `grade.py`**.
- The **improvement is not measured decode quality** — it's "picked knobs the formula likes better."

### Hardware metrics (spreadsheet)

`cryobrain/cost_model/npu_cost.py`:

```python
macs_per_layer = design.window_length * (2 ** design.bitwidth)
mac_count = macs_per_layer * design.num_layers
area_mm2 = mac_count * design.bitwidth * calibrated_area_per_mac + ...
latency_cycles = max(1, design.pipeline_depth // max(design.parallelism, 1))
```

Yosys may run (`cryobrain/rtl_grader/flow.py`) but area on the Pareto winner is **not** "we synthesized 10 different RTLs." It's formula + one RTL validity check.

**Verdict:** The reward contract in SPEC4 (`score(design) -> {reward, ler, area_um2, ...}`) is implemented, but **`ler` and `area` for candidates are not grounded in synthesized per-design hardware or a trained decoder.**

---

## What the dashboard adds (WS7)

`dashboardspec.md` / `demo/index.html`:

- **Integrity rules are followed:** no hardcoded numbers, sources cited, no "AI writes RTL" in copy.
- **Visual problem:** instrument-panel aesthetic + climb animation + Pareto green box **reads like** a live co-design lab to anyone who doesn't read `decoder_policy.py`.
- Panels A–D plot **authentic artifact JSON** from the proxy loop. Honest data pipeline, **misleading phenomenon**.

Memory panel headline wanted "~2× slope." Latest WSL run (`memory_ab_overlay.json`): slopes ~0.0086 vs ~0.0086 (ratio ~1×). Memory wins on **endpoint** (0.501 vs 0.459), not learning rate. Dashboard shows measured truth — which undercuts the pitch.

---

## What IS real (credit where due)

Worth keeping; not gimmick:

| Piece | Why it's real |
|---|---|
| Stim surface-code + shot sampling | Actual quantum error model |
| MWPM / PyMatching baseline LER | Industry-standard decoder anchor |
| RTL validity gate | Broken/wrong RTL → reward 0 |
| Verilator sim → VCD | Real timing trace of the props module |
| HUD `env.py` + `hud eval` CP0 | Live eval job against packaged task |
| Hidden grader contract | `grade.py` is a usable **scoring oracle** if you plug real candidates in |
| Memory buffer + retrieval API | Infrastructure works; it just stores knob exemplars today |

**The spec's actual valuable deliverable:** a **forkable verifiable environment** for hardware-design RL — Stim physics on one side, synth/sim gate on the other, scalar reward in the middle. That's a legitimate product wedge ("sellable to labs") **if you stop pretending the candidate path is already physical.**

---

## Spec workstream map — intended vs shipped

| WS | Spec intent | Shipped reality |
|---|---|---|
| WS1 Environment | `score()` contract + validity gate | ✅ Works |
| WS2 Accuracy | Stim LER + benchmark | ⚠️ MWPM real; **candidate LER simulated** |
| WS3 The chip | Synth RTL + Yosys per design | ⚠️ **One static RTL** + Yosys smoke |
| WS4 RL loop | GRPO writes decoders | ⚠️ **Knob search**; Modal/Fireworks scaffold |
| WS5 Memory | Compound verified designs | ⚠️ Compounds **knob configs** that fooled proxy |
| WS6 Curriculum | d=3→5→7 co-scaling | ✅ Curriculum stages exist; still proxy reward |
| WS7 Demo | Live dashboard, honest copy | ✅ Built; **phenomenon still feels like chip design** |

---

## Why the spec was written this way (best guess)

1. **Hackathon time budget** — Real RTL-parametric co-design + Stim-in-the-loop per variant is weeks/months, not 48 hours.
2. **Demo needs a climb** — Proxy LER guarantees monotonic-ish improvement for judges without training a neural decoder.
3. **Narrative wedge** — "Verifiable environment for quantum hardware RL" is fundable; "we tuned five integers" is not.
4. **Honest footnote buried** — SPEC4 line 8–10 says don't claim RTL authorship; §0 and dashboard aesthetics still imply it.
5. **Parallel agent split** — WS1–WS7 let multiple agents work without noticing WS2 candidate path and WS3 RTL path **don't connect**.

The spec optimized for **demo + checkpoint green**, not **physical fidelity**.

---

## What would make it "not a gimmick"

Minimum bar before saying "chip design" again:

### P0 — Ground the reward (kill the proxy)

- [ ] Delete or gate `simulate_candidate_ler` / `decoder_quality_multiplier` from production grading.
- [ ] Candidate LER = **RTL benchmark sim** (Stim-derived vectors through Verilator) OR a **real trained model** inference path.
- [ ] Reward moves only when **measured** accuracy changes, not when `parallelism` changes in JSON.

### P1 — RTL is actually the artifact

- [ ] **Parametric RTL generator** from `DesignConfig` (pipeline depth, width, parallelism in generated `.sv`), OR
- [ ] **Agent edits RTL** (Fireworks GRPO / env tools) and reward reads sim results.
- [ ] Per-variant Yosys area/latency on **that** generated/edited RTL for Pareto.

### P2 — Training is training

- [ ] Replace `_design_sweep` with policy that proposes **RTL diffs** or **generator params**, not shuffle of 8 tuples.
- [ ] Memory stores **RTL snippets + sim logs**, not just knob dicts.

### P3 — Demo matches physics

- [ ] Dashboard Panel C only claims slope ratio if artifact shows it.
- [ ] Pareto y-axis labeled "sim LER" not formula LER.
- [ ] Explicit UI badge: **"candidate accuracy: RTL sim"** vs **"MWPM: Stim"**.

---

## Suggested copy for the next agent

**Do say:**

> CryoBrain is a verifiable RL **environment** for quantum decoder **design search** — real Stim MWPM anchor, RTL correctness gate, continuous reward API. We're building the grading loop labs can trust before claiming silicon wins.

**Do not say:**

> The AI designs the NPU brain inside the chip / climb proves better decoders / Pareto shows cryo-fitting synthesized variants — **until P0–P1 are done.**

---

## Key files to read first

| File | What you'll learn |
|---|---|
| `SPEC4.md` | What we promised |
| `dashboardspec.md` | What the demo shows |
| `tasks/cryo_brain_decoder/rtl/cryo_brain_decoder.sv` | The only "chip" |
| `cryobrain/accuracy/decoder_policy.py` | **The proxy** |
| `cryobrain/cost_model/npu_cost.py` | Formula hardware |
| `cryobrain/rl/local_trainer.py` | What "training" does |
| `tasks/cryo_brain_decoder/donotaccess/grade.py` | Reward assembly |
| `artifacts/climb_chart_rl.json` | Demo climb data |
| `artifacts/memory_ab_overlay.json` | Memory A/B truth |
| `demo/index.html` | WS7 dashboard |

---

## One sentence for Claude

**The spec was a hackathon blueprint for a verifiable RL grading environment with a quantum decoder *story*; what shipped is knob search against an analytic LER proxy with one static Verilog props module, wrapped in a polished dashboard that looks like chip design but isn't.**