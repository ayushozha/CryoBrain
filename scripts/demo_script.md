# CryoBrain 2-minute demo script (SPEC-v6.1 C10)

Measured artifacts only. One command to refresh: `wsl bash scripts/run_demo_refresh_wsl.sh`
Then open `demo/index.html` offline and click **Play story**.

## Flow (agents keep improving)

1. **Concept (10s):** Every quantum chip needs a brain — CryoBrain is the swarm that designs that brain and **keeps improving** from measured feedback.
2. **Improvement strip (15s):** Point at the green cards — **FIFO throughput 0.09 → 0.44** (3 measured steps). Decoder row is honest “golden baseline” until multi-step climb lands.
3. **Play story → Panel B (25s):** Dual charts — decoder suppression + FIFO throughput climbing. This is the spine: propose → RTL → sim → score → memory.
4. **Swarm bus (20s):** Research → Architect → RTL → Measurement → Verifier → Scorer → Memory. Highlight `prompt_influenced: true` and Exa tags when online.
5. **Pareto (15s):** Panel D — 8 measured L2-safe points; accurate **and** fits cryo budget.
6. **Memory (15s):** Panel C — compounding asset (early A/B; slope claim when multi-step memory run exists).
7. **Close (10s):** Slow loop ships tonight; fast in-fridge loop is the 2040 arc.

## Honest talking points

| Claim | Artifact | Limit |
|-------|----------|-------|
| Agents improve on FIFO | `measured_fifo_climb.json` | Best multi-step proof today |
| Engine generalizes | decoder + FIFO in same env | Not “any RTL” — two fixed targets |
| Decoder climb | `measured_climb.json` | Early — 1 accepted step; say “baseline landed” |
| Pareto frontier | `measured_pareto.json` | 8 points, all LER=0 on golden path |
| Memory compounds | `measured_memory_ab.json` | Wiring proven; multi-step slope TBD |

**Backup:** Screen recording of Play story + improvement strip using committed artifacts.