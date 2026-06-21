# CryoBrain — Live Demo Dashboard (BUILD BRIEF)

**This is the demo. Not slides, not a doc — one live screen, driven by real artifact
data, that visibly *does the thing*.** A judge looks at it and believes the project
works because every number on screen traces to a file your pipeline actually produced.

> Build this with design tooling. Use **Claude's frontend-design skill / Claude Design**
> (or Grok's design mode) to make it look intentional and polished — not a default
> Bootstrap dashboard. Aesthetic direction is in §3. Substance rules are in §6 and are
> non-negotiable.

---

## 0. The one true sentence (header copy — say it, show it)

> **"A verifiable RL environment that drives quantum-decoder design optimization
> against a real physics + hardware reward — and compounds with memory."**

HONESTY RULE (hard): the system *optimizes designs against a verifiable reward*. Do
**not** write "the AI writes RTL from scratch" or "learns to author decoders" anywhere
in the UI — that's an overclaim a judge catches instantly. "Optimization driven by a
verifiable reward" is the true, strong claim. Every label obeys this.

---

## 1. What it is, technically

- **One self-contained file** (single `index.html` with inline CSS/JS, or a single-file
  React build). Must run **offline from `file://`** — no server, no network at demo time.
- **Reads real artifact JSON** produced by the pipeline (see §4). On load it fetches/embeds
  those files and renders. NO hardcoded numbers anywhere — if an artifact is missing, the
  panel shows "awaiting artifact", never a fake value.
- **One screen, 2×2 grid, no scrolling.** Fits 1920×1080 and a projector. Dark theme.
- **A single "▶ Play story" control** that runs the four panels in demo order (§5), plus
  per-panel replay. The presenter hits Play and narrates.

---

## 2. Layout (2×2, one screen)

```
┌───────────────────────────────┬───────────────────────────────┐
│  PANEL A — WAVEFORM            │  PANEL B — CLIMB               │
│  "The chip, running"           │  "It improves (the spine)"     │
│  syndrome in → correction out  │  reward ↑ over steps, animated │
├───────────────────────────────┼───────────────────────────────┤
│  PANEL C — MEMORY A/B          │  PANEL D — PARETO              │
│  "It compounds — 2× faster"    │  "Accurate AND fits the fridge"│
│  two climb curves overlaid     │  designs vs MWPM + budget box  │
└───────────────────────────────┴───────────────────────────────┘
HEADER: title + the one true sentence (§0)
FOOTER: data-source line (§6) + business close (§7)
```

---

## 3. Aesthetic direction (give this to the design tool)

- **Mood:** cryogenic / quantum lab. Near-black background (#0a0e14-ish), cold cyan/blue
  for structure and data, a single semantic accent pair — **green = qubit survives / good
  reward, red = qubit dies / invalid**. Restraint: one accent pair, not a rainbow.
- **Type:** clean grotesk sans for labels (Inter/IBM Plex Sans); **monospace for all
  numbers** (IBM Plex Mono / JetBrains Mono) — numbers should feel like instrument readouts.
- **Feel:** an instrument panel that's *live*, not a report. Subtle glow on active elements,
  smooth value transitions, gridlines understated. No drop-shadow card clutter, no emoji.
- **Motion:** purposeful only — the climb animates because it's *learning*; the waveform
  advances because it's *running*. Nothing animates for decoration.

---

## 4. DATA CONTRACTS (real artifacts → panels)

Read the **actual** files under `artifacts/` and adapt to their real field names. Expected
shapes (from the pipeline) below — if a field differs, match the file, never invent.

| Panel | Artifact file | Expected content → use |
|---|---|---|
| A Waveform | `cryo_golden_trace.vcd` → pre-export to `waveform.json` | digital signals over time: `syndrome_in[..]`, `valid_in`, pipeline regs, `correction_out[..]`, `valid_out`. Render as a timing diagram; highlight the cycle latency from syndrome→correction. |
| B Climb | `climb_chart_rl.json` | `summary: {start_reward≈0.364, end_reward≈0.459, steps:12, backend}` + per-step `[{step, reward}]`. Plot reward vs step; animate point-by-point. |
| C Memory A/B | `memory_ab_overlay.json` + `climb_chart_memory.json` + `climb_chart_no_memory.json` | two series; summary `{with:{end≈0.522, slope≈0.031}, without:{end≈0.464, slope≈0.014}, memory_wins:true}`. Overlay both curves; headline the **slope ratio (~2×)**. |
| D Pareto | `designs.json` / `pareto.json` (+ real Yosys area) | points `[{label, ler, area_um2, latency_cycles, power_mw, fits_budget}]`. x = latency (or area), y = LER (lower=better); draw the cryo budget box; MWPM marked off-budget; the winning design in the green box, annotated with its **real Yosys area number**. |

**VCD note:** parse the VCD to a small `waveform.json` (signal → list of `[time,value]`)
with a tiny script, or use a wavedrom-style renderer. Don't try to render raw VCD live.

---

## 5. "Play story" sequence (the 2-minute run)

One button walks these in order; waveform (A) loops live throughout:

1. **Beat 1 — Gate honesty (2s flash on a callout):** show a *wrong* design scoring
   `reward 0.0`, then a valid one scoring real. Tiny inset or a toast: "reward can't be
   gamed." (Pull from a stored invalid-vs-valid example; label as such.)
2. **Beat 2 — Climb (Panel B):** animate the curve 0.364 → 0.459. Caption:
   "improving from its own verified attempts."
3. **Beat 3 — Memory (Panel C):** reveal both curves; the with-memory line pulls away.
   Headline the **2× slope**, not the endpoint gap.
4. **Beat 4 — Pareto (Panel D):** points land; budget box draws; MWPM flagged off-budget;
   winner glows green with its real area number.
5. **Hold on the full panel** for the spoken business close (§7).

Each panel also has its own replay button for Q&A.

---

## 6. FRAMING & INTEGRITY RULES (non-negotiable)

1. **Every number traces to an artifact.** Under each panel, a small caption:
   `source: artifacts/<file>.json`. This is both honesty and a credibility flex — judges
   see you're reading real data, not mocking it.
2. **Memory = slope, not endpoint.** Lead with "improves ~2× faster with memory"
   (0.031 vs 0.014). The 0.464→0.522 endpoint is secondary text.
3. **Accuracy is continuous LER suppression — never "100% / 72%".** The Pareto y-axis is
   logical error rate; no all-or-nothing accuracy anywhere.
4. **"Optimization," not "authorship."** Per §0. The reward drives design search; the
   model is not shown writing RTL unless/until the Fireworks GRPO path is real.
5. **Real vs concept must be labeled.** This dashboard shows only *measured* data. Any
   Gizmo/architecture art is a *separate* concept bookend, explicitly tagged "concept" —
   it never appears inside these four data panels.
6. **No fake fallback values.** Missing artifact → "awaiting artifact", never a placeholder
   number that could read as real.

---

## 7. Header & footer copy

- **Header:** `CryoBrain` + the one true sentence (§0).
- **Footer-left (integrity):** rotating data-source line, e.g.
  `live from: climb_chart_rl.json · memory_ab_overlay.json · designs.json · cryo_golden_trace.vcd`.
- **Footer-right (business close, spoken at Beat 5):**
  "Verifiable hardware-design environments — sellable to labs today; quantum is the moonshot.
  Memory is the compounding asset."

---

## 8. Backup / resilience

- Build so it runs from `file://` with artifacts embedded or sibling — **no live process
  needed to present.**
- Record a clean screen-capture of a full "Play story" run as the fallback video. Present
  live; cut to the recording the instant anything stalls.

---

## 9. Acceptance criteria (the building agent is done when…)

- [ ] One file, opens offline, renders all four panels with **real artifact data**.
- [ ] No hardcoded numbers; missing artifact → "awaiting artifact".
- [ ] Each panel captions its source file.
- [ ] Climb and memory curves animate; waveform shows syndrome→correction latency.
- [ ] Memory panel headlines the **2× slope**.
- [ ] Pareto shows the budget box, MWPM off-budget, winner green with **real Yosys area**.
- [ ] "▶ Play story" runs Beats 1–5 cleanly; per-panel replay works.
- [ ] No "AI writes RTL" language; accuracy shown continuous; concept art excluded.
- [ ] Looks intentional (built with design tooling), 1080p + projector friendly.
- [ ] Screen-capture backup recorded.
```
```