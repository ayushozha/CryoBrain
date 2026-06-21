# CryoBrains — React app

A 14-section scrollytelling site for **CryoBrains**, the measured multi-agent
chip-design swarm. It is a faithful React port of the `CryoBrains.dc.html` Claude
Design page, bound to the **real measured artifacts** this repo produced — no mock
data.

![status](https://img.shields.io/badge/data-measured-30d158)
![stack](https://img.shields.io/badge/React_18-Vite_5-0a84ff)
![3d](https://img.shields.io/badge/three.js-R3F_v8-64d2ff)

## What it shows

Every metric on screen traces to `public/data/cryobrain.json`, which is built from
the swarm's real run (`artifacts/measured_*`, `verification_report.json`,
`swarm/event_log.jsonl`, the generated decoder RTL, the Stim/Verilator/Yosys
metrics, and the live Exa research hits):

| Section | Real data it binds |
|---|---|
| 01 Hero | decoder LER / area / power badge + 3D cryostat scene |
| 06 Live swarm | 8-agent ring replaying `replay[]` events (R3F) + live HUD |
| 07 Chip evidence | generated `cryo_brain_decoder.sv`, waveform, Yosys metrics, L1–L5 gates |
| 08 Benchmark | first 6 measured Pareto decoder variants (`cryo@<hash>`) |
| 09 Pareto | 26 measured designs / 22 on frontier (deterministic scatter) |
| 10 Research | the two real Exa paper links retrieved this run |
| 11 Memory | FIFO throughput climb `0.09375 → 0.3125` (+233%), 50/50 marathon |
| 12 2040 chip | concept chip cutaway (R3F) |

The remaining sections (02–05, 13–14) are narrative/static copy.

## Stack

- React 18 + Vite 5 + TypeScript (strict)
- React Three Fiber v8 + drei v9 + three r169 for the three scenes
- Charts are inline SVG computed in `src/data/derive.ts` (a 1:1 port of the
  design's `renderVals()`), so no chart library is needed.

## Run

```bash
cd web
npm install
npm run dev      # → http://localhost:5174
```

```bash
npm run build    # tsc -b && vite build → dist/
npm run preview  # serve the production build
```

## Layout

```
public/data/cryobrain.json   # the real measured data contract (single source of truth)
src/
  App.tsx                    # scroll-snap container, IntersectionObserver, dot/keyboard nav
  data/
    types.ts                 # types for cryobrain.json
    useCryoData.ts           # fetch hook (no fallback — surfaces load errors honestly)
    derive.ts                # port of renderVals(): chart geometry + swarm HUD + view-model
  sections/S01..S14          # one component per section
  three/                     # HeroScene, SwarmScene, ChipScene, Label (R3F)
```

## Data integrity

`useCryoData` loads only `public/data/cryobrain.json`. There is no fabricated
fallback data: if the fetch fails, the UI shows its "awaiting data / —"
placeholders and a visible error chip. To refresh the data, regenerate the
artifacts and re-export the bundle, then replace that file.

## Notes

- Static demo, no backend. Deploy as static files (`base: "./"`).
- `npm audit` flags the known esbuild/Vite **dev-server** advisory
  (GHSA-67mh-4wv8-2f99); it does not affect the production bundle and the fix
  requires a Vite major bump.
