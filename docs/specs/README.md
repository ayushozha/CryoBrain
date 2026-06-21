# CryoBrain spec archive (versioned)

**Canonical spec:** [`SPEC-v6.md`](SPEC-v6.md) — swarm framing + measured engine. Engineering spine remains v5 APIs; v6 adds the nine-role bus, demo path, and claim ladder.

| File | Version | Role |
|---|---|---|
| `SPEC-v1.md` | v1 | Original hackathon scope (historical) |
| `SPEC-v2.md` | v2 | CP/checkpoint division + sponsor hooks |
| `SPEC-v4.md` | v4 | Demo-ready spec (dashboard + checkpoints) |
| `SPEC-v5.md` | v5 | Measured LER, parametric RTL, verification stack, no proxy |
| `SPEC-v6.md` | **v6** | **ACTIVE** — nine-role swarm, event bus, honest claim ladder, 2-min demo |
| `dashboardspec-v1.md` | dash v1 | Live dashboard brief (swarm strip in v6 demo bundle) |

**Gap analysis:** [`../SPEC_REALITY_AUDIT.md`](../SPEC_REALITY_AUDIT.md) — what v1–v4 shipped vs what v5 requires.

**Agent orchestration:** [`../agents/00-MASTER_PLAN.md`](../agents/00-MASTER_PLAN.md)

## Tag legend (from v5)

- **[BUILT]** — exists in repo today
- **[BUILT-after-P0/P1/P2]** — blocked on measured milestone
- **[CLAIMABLE]** — say only after checkpoint passes
- **[VISION]** — roadmap; never present as done

## Keystone rule (v5 §2)

> A design change must produce a **measured** change in accuracy and hardware. Worse RTL → worse LER. No formula may stand in for candidate accuracy in `grade.py`.