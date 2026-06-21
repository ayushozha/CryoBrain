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

## `synth_metrics` — Grok G5 (MP1)

```python
# cryobrain/rtl_grader/synth_metrics.py  — not yet landed
def synth_metrics(rtl_path: Path) -> dict: ...
```

## `score_measured` — Grok G10 (MP2)

```python
# cryobrain/grader/score.py  — not yet landed
def score_measured(workdir: Path) -> dict: ...
```

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