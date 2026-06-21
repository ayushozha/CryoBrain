#!/usr/bin/env python3
"""Verify sponsor API connectivity (keys loaded from .env)."""

from __future__ import annotations

import argparse
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

CORE_SPONSORS = ("hud", "exa", "fireworks", "modal")


def build_report() -> dict[str, object]:
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

    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--require-core",
        action="store_true",
        help="fail unless HUD, Exa, Fireworks, and Modal are available",
    )
    args = parser.parse_args(argv)

    report = build_report()
    print(json.dumps(report, indent=2))
    if args.require_core:
        missing = [name for name in CORE_SPONSORS if not report.get(name)]
        if missing:
            print(f"missing required sponsor platform(s): {', '.join(missing)}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
