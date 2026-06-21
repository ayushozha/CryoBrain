# Agent orchestration (SPEC-v5)

**30 parallel subagents** across 3 orchestrators (10 each). Engineering only — no demo/dashboard/fake data.

---

## Tell agents to read — that is enough

Each handoff doc has a **START HERE** section at the top. You do **not** need to write a long prompt.

### What to say (one line per orchestrator)

| Tool | Say this |
|------|----------|
| **Codex** | Read `docs/agents/HANDOFF-CODEX.md` and execute it. |
| **Claude** | Read `docs/agents/HANDOFF-CLAUDE.md` and execute it. |
| **Grok / Cursor** | Read `docs/agents/HANDOFF-GROK.md` and execute it. |

Each orchestrator will: read the spec stack, pick the right **wave** (not all 10 agents at once), spawn subagents with the built-in spawn template, and respect blockers.

### Optional: assign one slot directly

If you want a single subagent instead of the full orchestrator:

| Tool | Say this |
|------|----------|
| Codex | Read `docs/agents/HANDOFF-CODEX.md`. You are Codex agent **X1**. Execute only section X1. |
| Claude | Read `docs/agents/HANDOFF-CLAUDE.md`. You are Claude agent **C8**. Execute only section C8. |
| Grok | Read `docs/agents/HANDOFF-GROK.md`. You are Grok agent **G3**. Execute only section G3. |

Replace `X1` / `C8` / `G3` with any slot from that handoff doc.

### Launch order across tools (you only say “read” — they coordinate)

1. **Codex** + **Grok** first (proxy kill + MP0 spine)  
2. **Claude** anytime for C8 smoke; full Claude work unlocks after Grok MP0/MP1  
3. Details: [`00-MASTER_PLAN.md`](./00-MASTER_PLAN.md)

---

## Documents

| Doc | Audience |
|-----|----------|
| [`00-MASTER_PLAN.md`](./00-MASTER_PLAN.md) | Shared DAG, frozen interfaces, milestones, path ownership |
| [`HANDOFF-GROK.md`](./HANDOFF-GROK.md) | Grok/Cursor — P0/P1 spine: measure, RTL gen, Yosys, grade |
| [`HANDOFF-CLAUDE.md`](./HANDOFF-CLAUDE.md) | Claude — memory, learning, sponsors, HUD, GEN, artifacts |
| [`HANDOFF-CODEX.md`](./HANDOFF-CODEX.md) | Codex — kill proxy, tests, formal, WSL, schemas |

## Specs

Canonical: [`../specs/SPEC-v5.md`](../specs/SPEC-v5.md)  
Index: [`../specs/README.md`](../specs/README.md)  
Reality gap: [`../SPEC_REALITY_AUDIT.md`](../SPEC_REALITY_AUDIT.md)

## Milestones (quick reference)

| ID | Gate |
|----|------|
| MP0 | Worse `.sv` → worse measured LER |
| MP1 | 3 configs → 3 distinct (area, LER) |
| MP2 | Reward only on measured change |
| MP3 | Measured climb (not proxy) |
| MP4 | Memory A/B on measured runs |
| MP5 | L1–L5 all gate score |
| CP0 | HUD eval on measured path |
| GEN | FIFO second target in same env |

## Start order

1. **Codex X1** — proxy kill (unblocks all)
2. **Grok G1/G2/G9** — types, stim, DesignConfig (parallel)
3. **Grok G3** — `measure_candidate_ler` → **MP0**
4. **Grok G4/G5** → **MP1**
5. **Grok G10** + **Claude C1/C5** → **MP2/MP3**
6. **Claude C9** + **Codex X3** → **GEN / MP5**

## Frozen paths (no cross-edit without PR note)

See path table in `00-MASTER_PLAN.md`. `demo/` is **frozen** for all v5 agents.