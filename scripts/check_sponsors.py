#!/usr/bin/env python3
"""Verify sponsor API connectivity (keys loaded from .env)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cryobrain.integrations.antim import request_concept_visual
from cryobrain.integrations.daytona import run_python_sandbox
from cryobrain.integrations.exa_rag import search_decoder_literature
from cryobrain.integrations.fireworks import propose_design_config
from cryobrain.integrations.secrets import get_key


def main() -> None:
    report: dict[str, object] = {
        "hud": bool(get_key("HUD_API_KEY")),
        "exa": False,
        "fireworks": False,
        "daytona": False,
        "antim": False,
        "modal": bool(
            (get_key("MODAL_TOKEN_ID") and get_key("MODAL_TOKEN_SECRET"))
            or (Path.home() / ".modal.toml").is_file()
        ),
    }
    try:
        hits = search_decoder_literature(num_results=2)
        report["exa"] = len(hits) > 0
        report["exa_hits"] = len(hits)
    except Exception as exc:
        report["exa"] = False
        report["exa_error"] = str(exc)

    proposed = propose_design_config(
        scenario={"distance": 3, "noise_rate": 0.001},
        exemplars=[],
    )
    report["fireworks"] = proposed is not None

    daytona = run_python_sandbox('print("cryobrain-daytona-ok")')
    report["daytona"] = bool(daytona.get("ok"))

    antim = request_concept_visual("CryoBrain NPU beside surface code qubits, technical diagram")
    report["antim"] = bool(antim.get("ok"))

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()