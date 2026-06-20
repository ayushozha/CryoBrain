# CryoBrain Decoder Co-Design

You are co-designing **CryoBrain**, the NPU reflex layer inside a fault-tolerant quantum chip.
The decoder must turn syndrome bits into corrections within a cryogenic hardware budget.

## Contract

1. Edit `rtl/cryo_brain_decoder.sv` and `design_config.json`.
2. Keep the module synthesizable (no latches; pass `make lint` and `make synth`).
3. The visible testbench must report `SCENARIO basic_decode PASS`.
4. Meet the cryo budget in `scenario.json` (latency, area, power).
5. Improve decode quality vs MWPM on the configured surface-code distance.

## Design knobs (`design_config.json`)

- `bitwidth` — INT2/4/8 quantization
- `num_layers` — network depth
- `parallelism` — MAC parallelism
- `pipeline_depth` — pipeline stages
- `window_length` — sliding syndrome window

## Grading

- **Validity gate:** RTL sim + synth + lint must pass, and cryo budget must be met. Fail → reward 0.
- **Continuous reward:** LER suppression vs MWPM + latency/area scores.

Run locally:

```bash
make lint
make test
make synth
```

Do not read anything under `/donotaccess`.