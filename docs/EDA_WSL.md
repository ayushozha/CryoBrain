# EDA in WSL

CryoBrain SPEC-v5 EDA proof runs in WSL, not Windows-native Verilator.

## Toolchain

Install OSS CAD Suite in WSL at:

```bash
~/utils/oss-cad-suite/bin
```

The milestone scripts prepend that directory to `PATH` and use the Linux virtual environment at `.venv-linux`.

## Milestone Entrypoints

```bash
wsl bash scripts/run_mp0_wsl.sh
wsl bash scripts/run_mp1_wsl.sh
wsl bash scripts/run_mp5_wsl.sh
```

MP0 proves the keystone rule: worse RTL must produce worse measured candidate LER.

MP1 proves three generated variants produce distinct synthesis and measured LER outputs.

MP5 is a full L1-L5 gate stub until the later formal and verification-report tests land.

## Direct Helpers

```bash
wsl bash scripts/verilator_sim_wsl.sh tasks/cryo_brain_decoder
wsl bash scripts/yosys_synth_wsl.sh tasks/cryo_brain_decoder/rtl/cryo_brain_decoder.sv
```

Use these helpers for debugging a single RTL/workdir. Do not claim milestone success from a Windows-native EDA run unless this document is updated with an explicit supported path and matching validation evidence.
