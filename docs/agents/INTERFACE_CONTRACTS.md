# Frozen interfaces (SPEC-v5 merge contract)

**Owners:** Grok pool implements; Claude/Codex consume and test.

## `measure_candidate_ler` — Grok G1/G3

```python
# cryobrain/accuracy/measured_ler.py
def measure_candidate_ler(
    rtl_path: Path,
    scenario: ScenarioConfig,
    *,
    shots: int = 1000,
    seed: int = 0,
    benchmark_vectors: int = 64,
) -> MeasureResult:
```

`MeasureResult` fields: `candidate_ler`, `mwpm_ler`, `suppression`, `shots`, `vector_source`, `rtl_path`, `benchmark_vectors`, `benchmark_failures`, `rtl_valid`.

**MP0:** `cryo_brain_decoder_wrong.sv` → strictly worse `candidate_ler` than golden XOR.

## `generate_rtl` — Grok G4

```python
# cryobrain/rtl_gen/generator.py
def generate_rtl(design: DesignConfig, out_dir: Path) -> Path: ...
```

## `synth_metrics` — Grok G5 (MP1) ✅

```python
# cryobrain/rtl_grader/synth_metrics.py
def synth_metrics(rtl_path: Path) -> SynthMetrics: ...
# area_um2, latency_cycles, power_mw_est, valid, yosys_log_path, cell_count
```

**MP1:** `wsl bash scripts/run_mp1_wsl.sh` — 3 presets → 3 distinct cell counts + LER spread.

## `score_measured` — Grok G10 (MP2) ✅

```python
# cryobrain/grader/score.py
def score_measured(workdir: Path, *, shots: int = 1000, seed: int = 1729) -> dict: ...
# reward, valid, ler, area_um2, latency_cycles, power_mw, layers_passed, source="measured"
```

**MP2:** `wsl bash scripts/run_mp2_wsl.sh`

## Stim manifest — Grok G2

```python
# cryobrain/stim/manifest.py
def load_manifest() -> dict: ...
def holdout_paths() -> list[str]: ...
```

## DesignConfig — Grok G9

```python
# cryobrain/design/config.py + cryobrain/types.py
DesignConfig  # dataclass in cryobrain.types
validate_design(design) -> None
```

## Artifact schema v2 - Codex X5

```python
# cryobrain/artifacts/schemas/v2
validate_measured_climb(artifact) -> dict
validate_pareto(artifact) -> dict
validate_measured_memory_ab(artifact) -> dict
```

Measured artifact contracts:

| Artifact | Required payload |
|---|---|
| `artifacts/measured_climb.json` | `history[].{step, candidate_ler, suppression, rtl_hash}` |
| `artifacts/measured_pareto.json` | `points[].{label, ler, area_um2, latency_cycles, rtl_path}` |
| `artifacts/measured_memory_ab.json` | `with_memory[]` and `without_memory[]` rows matching measured climb rows |

Validators reject proxy/formula fields recursively; measured artifacts must be derived from RTL measurement outputs.
