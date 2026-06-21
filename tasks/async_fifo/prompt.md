# async_fifo — GEN second RTL target (SPEC-v5 §6)

Optimize a **two-lane stream-arbiter FIFO** for **measured sustained throughput**
under a fixed bursty traffic pattern, without breaking correctness.

This is the platform-proof target: the SAME measured optimization env that
designs the QEC decoder also optimizes this NON-decoder block, on a metric that
comes from **simulation**, not a formula.

## Design space (`FifoConfig`)

- `depth` — FIFO capacity (entries). The primary throughput knob: a deeper FIFO
  absorbs more of the burst before backpressuring, so it drains more items in
  the window.
- `width` — datapath bit-width.

## Measured metric

`throughput = items drained / cycles`, COUNTED from a cocotb+Verilator run of the
generated `rtl/stream_arb_fifo.sv` against `cryobrain.stim.fifo_stim` traffic.
Correctness gate: the DUT must match the cycle-accurate golden reference
bit-for-bit (ready/valid/data/count), else throughput is not credited (reward 0).

`suppression` = measured throughput gain over the single-entry FIFO baseline
(the `mwpm`-style anchor).

## Reward

```
reward = throughput  if correctness gate passes
reward = 0.0         otherwise
```

No proxy / formula reward. The optimizer climbs by proposing deeper FIFOs and
seeing the MEASURED throughput rise.
