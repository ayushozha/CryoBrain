"""Parse Verilator VCD into compact waveform.json for the live dashboard."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def _parse_definitions(lines: list[str]) -> dict[str, dict[str, Any]]:
    """Map VCD symbol id -> {name, width, is_bus} from the top testbench scope only."""
    symbols: dict[str, dict[str, Any]] = {}
    in_tb = False
    depth = 0
    for raw in lines:
        line = raw.strip()
        if line == "$scope module cryo_brain_decoder_visible_tb $end":
            in_tb = True
            depth = 0
            continue
        if not in_tb:
            continue
        if line.startswith("$scope"):
            depth += 1
            continue
        if line == "$upscope $end":
            if depth == 0:
                in_tb = False
            else:
                depth -= 1
            continue
        if depth != 0:
            continue
        m = re.match(r"\$var\s+wire\s+(\d+)\s+(\S+)\s+(.+?)\s+\$end", line)
        if not m:
            continue
        width = int(m.group(1))
        sym_id = m.group(2)
        name = m.group(3).strip()
        if "[" in name:
            name = name.split("[", 1)[0].strip()
        symbols[sym_id] = {"name": name, "width": width, "is_bus": width > 1}
    return symbols


def _value_for_change(token: str, width: int) -> int:
    if token in {"0", "1"}:
        return int(token)
    if token.startswith("b"):
        return int(token[1:], 2) if token[1:] else 0
    return 0


def vcd_to_waveform(vcd_path: Path, *, max_samples: int = 120) -> dict[str, Any]:
    """Export timing samples for dashboard panel A."""
    text = vcd_path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    symbols = _parse_definitions(lines)

    wanted = {
        "syndromes_valid",
        "syndromes",
        "corrections_valid",
        "corrections",
        "clk",
    }
    # Prefer top-scope symbols (shorter ids) when names repeat across scopes.
    id_by_name: dict[str, str] = {}
    for sym_id, meta in symbols.items():
        name = meta["name"]
        if name not in wanted:
            continue
        if name not in id_by_name or len(sym_id) <= len(id_by_name[name]):
            id_by_name[name] = sym_id

    state: dict[str, int] = {name: 0 for name in id_by_name}
    samples: list[dict[str, Any]] = []
    latency_cycles: int | None = None
    last_syndrome_valid_time: int | None = None

    in_body = False
    current_time = 0
    for raw in lines:
        line = raw.strip()
        if line == "#0":
            in_body = True
            current_time = 0
            continue
        if not in_body:
            continue
        if line.startswith("#"):
            current_time = int(line[1:])
            if len(samples) < max_samples:
                samples.append({"t": current_time, **state})
            continue
        if not line or line.startswith("$"):
            continue

        if line[0] in "01":
            sym_id = line[1:]
            val = int(line[0])
        elif line.startswith("b"):
            parts = line.split()
            if len(parts) != 2:
                continue
            val = _value_for_change(parts[0], 8)
            sym_id = parts[1]
        else:
            continue

        meta = symbols.get(sym_id)
        if not meta:
            continue
        name = meta["name"]
        if name not in id_by_name:
            continue
        state[name] = val
        if name == "syndromes_valid" and val == 1:
            last_syndrome_valid_time = current_time
        if (
            name == "corrections_valid"
            and val == 1
            and last_syndrome_valid_time is not None
            and latency_cycles is None
        ):
            latency_cycles = max(1, (current_time - last_syndrome_valid_time) // 5000)

    return {
        "source": str(vcd_path.name),
        "timescale_ps": 1,
        "signals": list(id_by_name.keys()),
        "samples": samples[:max_samples],
        "latency_cycles": latency_cycles,
    }


def write_waveform_json(vcd_path: Path, out_path: Path) -> dict[str, Any]:
    payload = vcd_to_waveform(vcd_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload