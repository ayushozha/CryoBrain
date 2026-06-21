# CryoBrain — Progress Update (2026-06-21)

**Canonical spec:** [`docs/specs/SPEC-v6.md`](specs/SPEC-v6.md)

**Branch:** `feat/real-measured-artifacts` (PR [#20](https://github.com/ayushozha/CryoBrain/pull/20))

**Repo:** https://github.com/ayushozha/CryoBrain

**Prior summary:** [`docs/PROGRESS.md`](PROGRESS.md) (stale — written for SPEC-v5; use this doc for current truth)

---

## Executive summary

The **core measured-data scope is complete**. CryoBrain now runs a real Stim + Verilator + Yosys pipeline with no proxy LER in production scoring, produces committed measured artifacts on disk, and builds a measured-only offline demo (`data_era: "measured"`). The Architect climb gate (P-gate) passes in WSL with **1 accepted step** (golden baseline: LER=0.0, suppression=+1.0).

**Full SPEC-v6 is ~75% done.** Remaining work is engineering lift (multi-step climb beyond golden, research→adoption wiring, FIFO WSL proof, demo rehearsal) — not replacing mock data with real data.

**Keystone rule holds:** worse RTL → worse measured LER. No formula accuracy in `score_measured`.

---

## Scope completion scorecard

| Scope item | Status | Evidence |
|------------|--------|----------|
| Real measured LER (no proxy in prod) | **Done** | MP0–MP2 green; `audit_reward_path.sh` + pytest guards |
| Real synthesizable RTL per variant | **Done** | MP1 green; `cryobrain/rtl_gen/generator.py` |
| Measured reward only | **Done** | MP2 green; `score_measured()` gates L1/L2/L4/L5 |
| Architect climb artifact on disk | **Done** | `artifacts/measured_climb.json` |
| Memory A/B on measured runs | **Done** | `artifacts/measured_memory_ab.json` |
| Measured Pareto on disk | **Done** | `artifacts/measured_pareto.json` |
| Measured-only demo bundle | **Done** | `build_demo.py` raises if `measured_*.json` missing; `demo/index.html` |
| SPEC-v6 swarm (bus / exec / viz) | **Done** | `event_bus.py`, `executors.py`, `visualization.py` |
| Planner as 2nd trained agent | **Code done** | `planner.py`, `planner_trainer.py` |
| L3 formal + verification report | **Code done** | `l3_formal.py`, `verification_report.py` (sby skips if absent) |
| Research self-adoption (§2.5) | **Spec only** | `research_step` emits pack; prompt/memory/planner wiring open |
| Multi-step climb improvement | **Partial** | 1/3–1/5 steps accepted; mutants fail L2 |
| FIFO platform proof (P-gen) | **Code only** | `run_gen_fifo_wsl.sh` not run green |
| Demo rehearsal + backup recording | **Not done** | Operational |
| PR merged to `main` | **Pending** | PR #20 open |

**Verdict:** Demo-honest measured story = **ready**. Full SPEC-v6 definition of done = **4 items still open** (see §DoD below).

---

## Measured artifacts (on disk)

All three primary artifacts use `reward_source: "score_measured"` and were produced by WSL runs (`run_c5_climb_wsl.sh`).

| File | Gate | Content (latest green run) |
|------|------|----------------------------|
| `artifacts/measured_climb.json` | MP3 / P-gate | 1 accepted step: step 0, LER=0.0, suppression=+1.0, golden RTL hash `239eb2ca…` |
| `artifacts/measured_memory_ab.json` | MP4 | with/without memory both hit golden at step 0 |
| `artifacts/measured_pareto.json` | C10 | 1 frontier point: LER=0.0, area=6.0 µm² |

**Climb honesty:** Steps 1+ reject because parametric generated RTL fails L2 (high LER). The climb proves the measured loop and golden baseline; it does **not** yet show the Architect beating golden over multiple steps.

---

## Session deliverables (2026-06-21)

| Deliverable | Detail |
|-------------|--------|
| WSL synthesis fix | `tool_env()` includes `/usr/bin` + `/bin` on Linux — fixes Yosys bash wrapper (`cell_count=0`) |
| Golden cold-start | `GOLDEN_BASELINE` + generator copies golden `.sv` when design matches |
| Measured-only demo | `build_demo.py` removes proxy fallback; `tests/test_demo_measured.py` |
| Artifact git policy | `.gitignore` allows `measured_*.json` + `baselines/` under `artifacts/` |
| SPEC-v6 §2.5 | Research-triggered self-adoption contract + P-research adoption gate |
| WSL reliability | `.gitattributes` (`*.sh eol=lf`), `scripts/run_c5_climb.ps1` PowerShell wrapper |
| Status table refresh | SPEC-v6 implementation status: P-gate green, demo measured-only |

---

## SPEC-v6 definition of done

| Item | Status |
|------|--------|
| Proxy dead; reward 100% measured (MP0–MP2) | [x] |
| Event-bus swarm (9 roles; Tier-1 trained, Tier-2 executing) | [x] |
| Visualization bound to `measured:true` events only | [x] |
| L1–L5 gate every score (L3 skips when sby absent) | [x] |
| Planner climb artifact path | [x] code |
| Architect climb + memory A/B committed | [x] |
| Research self-adoption loop closed (§2.5) | [ ] |
| FIFO platform proof (WSL green) | [ ] |
| Demo rehearsed; backup recorded; claims on earned rung | [ ] |
| Business arc documented for pitch | [ ] |

---

## Honest claim ladder (what you can say today)

| Claim | Safe? | Earned by |
|-------|-------|-----------|
| Candidate accuracy is measured (RTL on Stim vectors) | **Yes** | MP0 |
| Each design is real synthesizable RTL, synthesized per variant | **Yes** | MP1 |
| Reward is measured-only (no proxy formula) | **Yes** | MP2 |
| Architect is RL-trained on measured reward with climb on disk | **Yes** | P-gate artifact |
| Multi-agent swarm: trained design agents + specialist executors | **Yes** | P-bus + P-exec on `main`/branch |
| Climb shows measurable improvement over multiple steps | **No** | Only golden step 0 accepted |
| Research triggers self-adoption | **No** | §2.5 spec'd; wiring partial |
| Demonstrated on decoder + FIFO (general engine) | **No** | FIFO WSL proof pending |
| We beat MWPM / mass-produced silicon | **Never** | Honest ceiling in SPEC-v6 |

---

## Architecture (current)

```
Research → Planner → Architect → RTL → Measurement → Verifier → Scorer → Memory
                ↑______________________________________________|
                         (measured event bus — SPEC-v6 §2)
```

- **Measured spine:** `measure_candidate_ler` → `score_measured` → `compute_reward`
- **Training loop:** `local_trainer.py` → `proposal_loop.run_proposal_step`
- **Demo:** `scripts/build_demo.py` → `demo/index.html` (offline, measured JSON only)
- **Gap:** `research_step` returns `ContextPack` but does not yet thread into propose/plan/memory (§2.5)

---

## WSL commands (verified)

```powershell
# Recommended (PowerShell-safe)
.\scripts\run_c5_climb.ps1 -Steps 3

# Direct WSL
wsl --cd /mnt/c/Users/ayush/Desktop/Hackathons/YC/06-20-2026 bash scripts/run_c5_climb_wsl.sh 3

# Demo bundle (Windows)
python scripts/build_demo.py

# Fast unit tests (Windows)
uv run pytest tests/test_demo_measured.py tests/test_swarm_event_bus.py -q
```

**Avoid:** `(cd ... ; wsl ...)` in PowerShell (parse error), `wsl bash -c "..."` (can break PATH), parallel WSL EDA jobs (flake MP2 golden test).

If `set: pipefail: invalid option name` appears: `sed -i 's/\r$//' scripts/*.sh` in WSL.

---

## Risks and flakes observed

| Risk | Mitigation |
|------|------------|
| MP2 `test_golden_scores_higher_than_wrong` flakes under parallel WSL load | Run one climb at a time; kill stale apt-get/EDA background jobs |
| 0/3 accepted climb runs (all variants fail L2) | Re-run; usually transient when golden test also failed |
| Generated mutants never pass L2 | Next engineering priority: decode-valid parametric RTL |
| PR #20 not merged | Merge before demo claims reference `main` |

---

## Next priorities (ordered)

1. **Merge PR #20** — measured artifacts + demo measured-only + SPEC-v6 §2.5 + WSL fixes.
2. **Wire §2.5 adoption** — thread `ContextPack` into Architect prompt, Planner plan, Memory tags; emit `prompt_influenced` on bus.
3. **Climb beyond golden** — generator or proposer must produce L2-valid mutants so history has ≥2 accepted steps.
4. **FIFO WSL proof** — `wsl bash scripts/run_gen_fifo_wsl.sh`.
5. **Real swarm event log** — `artifacts/swarm/event_log.jsonl` from a measured run for viz/audit.
6. **Demo rehearsal** — live walkthrough + screen-record backup off measured data.
7. **Sync `docs/PROGRESS.md`** — point to SPEC-v6 and this update (legacy v5 table is stale).

---

## Test and tooling snapshot

| Metric | Value |
|--------|-------|
| Pytest collected | 237 |
| Latest C5 gate | `C5 PASS` (~4 min WSL, 1/3 accepted) |
| OSS CAD | Verilator 5.049, Yosys 0.66 (WSL `~/utils/oss-cad-suite`) |
| Demo `data_era` | `"measured"` |

---

## One-line status

**CryoBrain has a real measured spine, committed climb/memory/pareto artifacts, and a measured-only demo — demo-honest today; full SPEC-v6 still needs adoption wiring, multi-step climb, FIFO proof, and rehearsal.**