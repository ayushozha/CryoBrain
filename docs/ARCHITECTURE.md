# CryoBrain RL & Artifacts Architecture

## RL loop (`cryobrain/rl/`)

| Module | Role |
|--------|------|
| `config.py` | `TrainConfig` + `CurriculumStage` (d=3→5→7, cryo budgets) |
| `local_trainer.py` | Local stub that scores design knobs via cost model + synthetic LER |
| `modal_train.py` | Launcher: Modal GPU function when creds exist, else local stub |

**Outputs:** `artifacts/climb_chart.json` (reward history + curriculum transitions),
`artifacts/designs.json` (budget-feasible rollouts for Pareto).

```powershell
uv run python scripts/run_rl.py --steps 50
# or
uv run --extra rl python -m cryobrain.rl.modal_train --steps 50 --local
```

## Demo artifacts (`cryobrain/artifacts/`)

| Module | Role |
|--------|------|
| `pareto.py` | Accuracy↔hardware frontier (continuous LER suppression vs area) |
| `curriculum.py` | F7 distance-scaling chart from climb chart history |

```powershell
uv run python -m cryobrain.artifacts.pareto
# or
uv run python scripts/plot_pareto.py
```

**Outputs:** `pareto.png`, `pareto.json`, `distance_curriculum.png`, `distance_curriculum.json`.

## Checkpoints

- **CP4:** `run_rl.py` — reward trends up in `climb_chart.json`
- **CP6:** `plot_pareto.py` — visible frontier + d=3→5→7 re-optimization bands