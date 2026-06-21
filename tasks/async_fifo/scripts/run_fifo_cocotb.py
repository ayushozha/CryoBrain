#!/usr/bin/env python3
"""Run the FIFO throughput cocotb DV against a generated FIFO (SPEC-v5 GEN / C9).

Mirrors ``tasks/stream_arb_fifo_cocotb_dv/scripts/run_cocotb.py``, but for the
self-contained parametric FIFO (no vendor filelist) and wired to emit the
measured throughput report consumed by ``cryobrain.accuracy.fifo_throughput``.

WSL/Linux only (Verilator). Prints the parsed ``FIFO_THROUGHPUT`` line on stdout.
"""

import argparse
import os
import platform
from pathlib import Path

from cocotb_tools.runner import get_runner


def configure_tool_environment() -> None:
    os.environ.pop("LC_ALL", None)
    os.environ["LANG"] = "en_US.UTF-8"
    os.environ["LC_CTYPE"] = "en_US.UTF-8"
    oss_bin = Path.home() / "utils" / "oss-cad-suite" / "bin"
    if oss_bin.is_dir():
        os.environ["PATH"] = f"{oss_bin}:{os.environ.get('PATH', '')}"
    if platform.system() == "Darwin":
        os.environ.setdefault("AR", "/usr/bin/ar")
        os.environ.setdefault("RANLIB", "/usr/bin/ranlib")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rtl", required=True, help="Path to generated stream_arb_fifo.sv")
    parser.add_argument("--tests", required=True, help="Path to the cocotb test module")
    parser.add_argument("--traffic", required=True, help="Traffic JSON written by fifo_stim")
    parser.add_argument("--report", required=True, help="Where the DV writes the throughput report")
    parser.add_argument("--build-dir", default="build/fifo_cocotb")
    parser.add_argument("--results-xml", default="reports/fifo_results.xml")
    parser.add_argument("--top", default="stream_arb_fifo")
    args = parser.parse_args()

    rtl = Path(args.rtl).resolve()
    tests = Path(args.tests).resolve()
    traffic = Path(args.traffic).resolve()
    report = Path(args.report).resolve()
    build_dir = Path(args.build_dir).resolve()
    results_xml = Path(args.results_xml).resolve()
    results_xml.parent.mkdir(parents=True, exist_ok=True)

    configure_tool_environment()
    runner = get_runner("verilator")
    runner.build(
        sources=[rtl],
        hdl_toplevel=args.top,
        build_args=["--timing", "-Wno-fatal", "-Wno-WIDTHEXPAND"],
        build_dir=build_dir,
        always=True,
        clean=True,
    )
    runner.test(
        hdl_toplevel=args.top,
        test_module=tests.stem,
        test_dir=tests.parent,
        build_dir=build_dir,
        results_xml=str(results_xml),
        extra_env={
            **os.environ,
            "FIFO_TRAFFIC_FILE": str(traffic),
            "FIFO_REPORT_FILE": str(report),
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
