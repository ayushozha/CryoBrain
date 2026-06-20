"""Shared Verilator + Yosys RTL flow helpers."""

from __future__ import annotations

import json
import os
import platform
import re
import shutil
import signal
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RtlFlowResult:
    sim_passed: bool
    synth_passed: bool
    lint_passed: bool
    cell_count: int
    area_estimate: float
    latency_cycles: int
    logs: dict[str, str]

    @property
    def rtl_valid(self) -> bool:
        return self.sim_passed and self.synth_passed and self.lint_passed


def tool_env() -> dict[str, str]:
    env = os.environ.copy()
    env.pop("LC_ALL", None)
    env["LANG"] = "en_US.UTF-8"
    env["LC_CTYPE"] = "en_US.UTF-8"
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        env["HOME"] = "/home/agent"
    if platform.system() == "Darwin":
        path_parts = []
        for candidate in [Path("/opt/homebrew/bin"), Path.home() / "utils" / "oss-cad-suite" / "bin"]:
            if candidate.is_dir():
                path_parts.append(str(candidate))
        path_parts.extend(["/usr/bin", "/bin", "/usr/sbin", "/sbin", env.get("PATH", "")])
        env["PATH"] = ":".join(part for part in path_parts if part)
    else:
        oss_bin = Path.home() / "utils" / "oss-cad-suite" / "bin"
        if oss_bin.is_dir():
            env["PATH"] = f"{oss_bin}:{env.get('PATH', '')}"
    return env


def run_cmd(args: list[str], *, cwd: Path, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    proc = subprocess.Popen(
        args,
        cwd=cwd,
        env=tool_env(),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    try:
        stdout, _ = proc.communicate(timeout=timeout)
        return subprocess.CompletedProcess(args, proc.returncode, stdout, None)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
        return subprocess.CompletedProcess(args, -9, f"timed out after {timeout}s", None)


def _parse_cell_count(proc_json: Path) -> int:
    if not proc_json.is_file():
        return 0
    data = json.loads(proc_json.read_text(encoding="utf-8"))
    cells = data.get("modules", {}).get("cryo_brain_decoder", {}).get("cells", {})
    return len(cells)


def run_rtl_flow(workdir: Path, *, golden_mode: bool = False) -> RtlFlowResult:
    """Run lint, visible sim, and synthesis in the agent workspace."""
    logs: dict[str, str] = {}
    rtl = workdir / "rtl" / "cryo_brain_decoder.sv"
    visible_tb = workdir / "dv" / "visible_tb.sv"
    build_dir = workdir / "build"
    report_dir = workdir / "reports"
    build_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    lint = run_cmd(
        ["verilator", "--lint-only", "-Wall", "-Wno-fatal", "--top-module", "cryo_brain_decoder", str(rtl)],
        cwd=workdir,
    )
    logs["lint"] = lint.stdout or ""
    lint_passed = lint.returncode == 0

    sim_passed = False
    if visible_tb.is_file():
        sim = run_cmd(
            [
                "verilator",
                "--binary",
                "--timing",
                "-Wno-fatal",
                "--top-module",
                "cryo_brain_decoder_visible_tb",
                "-Mdir",
                str(build_dir / "obj_visible"),
                "-o",
                "cryo_brain_decoder_visible",
                str(rtl),
                str(visible_tb),
            ],
            cwd=workdir,
            timeout=180,
        )
        logs["verilate"] = sim.stdout or ""
        if sim.returncode == 0:
            run_bin = run_cmd([str(build_dir / "obj_visible" / "cryo_brain_decoder_visible")], cwd=workdir)
            logs["sim"] = run_bin.stdout or ""
            scenario_re = re.compile(r"^SCENARIO\s+(?P<name>\S+)\s+(?P<status>PASS|FAIL)")
            sim_passed = run_bin.returncode == 0 and any(
                m.group("status") == "PASS" for m in scenario_re.finditer(run_bin.stdout or "")
            )
        else:
            logs["sim"] = sim.stdout or ""

    synth_script = workdir / "synth" / "synth.ys"
    synth_passed = False
    cell_count = 0
    if synth_script.is_file():
        synth = run_cmd(["yosys", "-q", "-s", str(synth_script)], cwd=workdir)
        logs["synth"] = synth.stdout or ""
        proc_json = report_dir / "proc.json"
        synth_passed = synth.returncode == 0 and proc_json.is_file()
        cell_count = _parse_cell_count(proc_json) if synth_passed else 0

    area_estimate = cell_count * 1.5e-6
    latency_cycles = 8 if golden_mode else 12
    return RtlFlowResult(
        sim_passed=sim_passed,
        synth_passed=synth_passed,
        lint_passed=lint_passed,
        cell_count=cell_count,
        area_estimate=area_estimate,
        latency_cycles=latency_cycles,
        logs=logs,
    )