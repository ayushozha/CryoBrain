# CryoBrain spec archive (versioned)

**Canonical spec:** [`SPEC-v5.md`](SPEC-v5.md) — the 2040 measured-engine build. All engineering work follows v5.

| File | Version | Role |
|---|---|---|
| `SPEC-v1.md` | v1 | Original hackathon scope (historical) |
| `SPEC-v2.md` | v2 | CP/checkpoint division + sponsor hooks |
| `SPEC-v4.md` | v4 | Demo-ready spec (dashboard + checkpoints) |
| `SPEC-v5.md` | **v5** | **ACTIVE** — measured LER, parametric RTL, verification stack, no proxy |
| `dashboardspec-v1.md` | dash v1 | Live dashboard brief (deferred until v5 feeds measured artifacts) |

**Gap analysis:** [`../SPEC_REALITY_AUDIT.md`](../SPEC_REALITY_AUDIT.md) — what v1–v4 shipped vs what v5 requires.

**Agent orchestration:** [`../agents/00-MASTER_PLAN.md`](../agents/00-MASTER_PLAN.md)

## Tag legend (from v5)

- **[BUILT]** — exists in repo today
- **[BUILT-after-P0/P1/P2]** — blocked on measured milestone
- **[CLAIMABLE]** — say only after checkpoint passes
- **[VISION]** — roadmap; never present as done

## Keystone rule (v5 §2)

> A design change must produce a **measured** change in accuracy and hardware. Worse RTL → worse LER. No formula may stand in for candidate accuracy in `grade.py`.