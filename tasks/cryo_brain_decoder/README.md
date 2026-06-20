# CryoBrain Decoder Task

Primary HUD curriculum task: co-design `cryo_brain_decoder.sv` and `design_config.json`
under a cryogenic hardware budget with a verifiable reward (SPEC F8, CP2, CP5).

## Prerequisites

- **OSS CAD Suite** on `PATH` (`verilator`, `yosys`)
- **Python 3.11+** with repo deps (`uv sync` from workspace root)
- **GNU Make** (Linux/macOS/WSL). Native Windows shells can invoke the commands below directly.

If EDA tools are missing, `cryobrain.rtl_grader.flow` logs a clear skip message and the
validity gate returns reward `0` until tools are installed.

## Local targets

From this directory:

```bash
make lint    # Verilator lint on agent RTL
make test    # Visible testbench (SCENARIO basic_decode PASS)
make synth   # Yosys ice40 synthesis → reports/proc.json
make clean   # Remove build/ and reports/
```

Equivalent manual commands:

```bash
verilator --lint-only -Wall -Wno-fatal --top-module cryo_brain_decoder rtl/cryo_brain_decoder.sv

verilator --binary --timing -Wno-fatal --top-module cryo_brain_decoder_visible_tb \
  -Mdir build/obj_visible -o cryo_brain_decoder_visible \
  rtl/cryo_brain_decoder.sv dv/visible_tb.sv
./build/obj_visible/cryo_brain_decoder_visible

mkdir -p reports
yosys -q -s synth/synth.ys
```

## Calibration (CP2 / CP3)

From workspace root (requires `verilator` + `yosys`):

```bash
python tasks/cryo_brain_decoder/scripts/check_calibration.py
```

Expected reward band:

| Variant | Reward |
|---------|--------|
| `donotaccess/cryo_brain_decoder_wrong.sv` | `0` (validity gate) |
| Agent starter RTL | `0.20` – `0.50` |
| `donotaccess/cryo_brain_decoder_golden.sv` | `≥ 0.60` |

## Agent files

| Path | Role |
|------|------|
| `rtl/cryo_brain_decoder.sv` | Agent-editable decoder (starter uses OR, not XOR) |
| `design_config.json` | Quantization / depth / parallelism knobs |
| `scenario.json` | Surface-code distance, noise, cryo budget |
| `dv/visible_tb.sv` | Agent-visible smoke test |
| `donotaccess/` | Golden/wrong RTL + hidden grader (not for agents) |

## Grading model

1. **Validity gate** — RTL lint + visible sim + Yosys synth must pass; cryo budget must be met. Fail → reward `0`.
2. **Continuous reward** — `0.7 × LER suppression vs MWPM + 0.15 × latency + 0.15 × area` (see `cryobrain.reward.compute_reward`).