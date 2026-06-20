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

REQUIRED_EDA_TOOLS = ("verilator", "yosys")


@dataclass(frozen=True)
class RtlFlowResult:
    sim_passed: bool
    synth_passed: bool
    lint_passed: bool
    cell_count: int
    area_estimate: float
    latency_cycles: int
    logs: dict[str, str]
    tools_available: bool
    benchmark_vectors: int = 0
    benchmark_failures: int = 0
    benchmark_exactness: float = 0.0
    benchmark_confidence: float = 0.0

    @property
    def rtl_valid(self) -> bool:
        return self.tools_available and self.sim_passed and self.synth_passed and self.lint_passed


def _oss_cad_candidates() -> list[Path]:
    home = Path.home()
    system = platform.system()
    candidates = [
        home / "utils" / "oss-cad-suite" / "bin",
        Path("/opt/homebrew/bin"),
        Path("C:/oss-cad-suite/bin"),
        Path("C:/Program Files/oss-cad-suite/bin"),
    ]
    if system == "Windows":
        candidates.extend(
            [
                home / "oss-cad-suite" / "bin",
                Path(os.environ.get("OSS_CAD_SUITE_ROOT", "")) / "bin",
            ]
        )
    return [path for path in candidates if path.is_dir()]


def tool_env() -> dict[str, str]:
    env = os.environ.copy()
    env.pop("LC_ALL", None)
    env["LANG"] = "en_US.UTF-8"
    env["LC_CTYPE"] = "en_US.UTF-8"
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        env["HOME"] = "/home/agent"

    path_parts: list[str] = []
    for candidate in _oss_cad_candidates():
        path_parts.append(str(candidate))
    if platform.system() == "Darwin":
        path_parts.extend(["/usr/bin", "/bin", "/usr/sbin", "/sbin"])
    path_parts.append(env.get("PATH", ""))
    separator = ";" if platform.system() == "Windows" else ":"
    env["PATH"] = separator.join(part for part in path_parts if part)
    return env


def resolve_eda_tool(name: str) -> str | None:
    """Return an executable path for an EDA tool, probing OSS CAD Suite paths."""
    found = shutil.which(name, path=tool_env().get("PATH"))
    if found:
        return found
    suffix = ".exe" if platform.system() == "Windows" else ""
    for candidate_dir in _oss_cad_candidates():
        candidate = candidate_dir / f"{name}{suffix}"
        if candidate.is_file():
            return str(candidate)
    return None


def missing_eda_tools() -> list[str]:
    return [tool for tool in REQUIRED_EDA_TOOLS if resolve_eda_tool(tool) is None]


def eda_tools_available() -> bool:
    return not missing_eda_tools()


def _tool_missing_log(tool: str) -> str:
    searched = ", ".join(str(path) for path in _oss_cad_candidates()) or "(no OSS CAD paths found)"
    return (
        f"EDA tool '{tool}' not found on PATH. "
        f"Install OSS CAD Suite and add its bin directory to PATH, or set OSS_CAD_SUITE_ROOT. "
        f"Searched: {searched}"
    )


def run_cmd(args: list[str], *, cwd: Path, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    executable = args[0]
    if resolve_eda_tool(executable) is None and executable in REQUIRED_EDA_TOOLS:
        return subprocess.CompletedProcess(args, 127, _tool_missing_log(executable), None)
    resolved = resolve_eda_tool(executable) or executable
    cmd = [resolved, *args[1:]]
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=cwd,
            env=tool_env(),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            start_new_session=platform.system() != "Windows",
        )
    except FileNotFoundError as exc:
        return subprocess.CompletedProcess(cmd, 127, f"missing executable: {executable} ({exc})", None)
    try:
        stdout, _ = proc.communicate(timeout=timeout)
        return subprocess.CompletedProcess(cmd, proc.returncode, stdout, None)
    except subprocess.TimeoutExpired:
        if hasattr(os, "killpg"):
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
        else:
            proc.kill()
        return subprocess.CompletedProcess(cmd, -9, f"timed out after {timeout}s", None)


def _parse_cell_count(proc_json: Path) -> int:
    if not proc_json.is_file():
        return 0
    data = json.loads(proc_json.read_text(encoding="utf-8"))
    cells = data.get("modules", {}).get("cryo_brain_decoder", {}).get("cells", {})
    return len(cells)


def _parse_benchmark(stdout: str) -> dict[str, int | float]:
    match = re.search(
        r"^BENCHMARK\s+stim_surface_code\s+vectors=(?P<vectors>\d+)\s+"
        r"passes=(?P<passes>\d+)\s+failures=(?P<failures>\d+)\s+"
        r"valid=(?P<valid>\d+)\s+exact_ppm=(?P<exact>\d+)\s+"
        r"confidence_ppm=(?P<confidence>\d+)",
        stdout,
        flags=re.MULTILINE,
    )
    if not match:
        return {
            "vectors": 0,
            "passes": 0,
            "failures": 0,
            "valid": 0,
            "exactness": 0.0,
            "confidence": 0.0,
        }
    return {
        "vectors": int(match.group("vectors")),
        "passes": int(match.group("passes")),
        "failures": int(match.group("failures")),
        "valid": int(match.group("valid")),
        "exactness": int(match.group("exact")) / 1_000_000,
        "confidence": int(match.group("confidence")) / 1_000_000,
    }


def _ensure_benchmark_vectors(workdir: Path) -> tuple[Path | None, dict[str, object]]:
    scenario_path = workdir / "scenario.json"
    if not scenario_path.is_file():
        return None, {}
    from cryobrain.accuracy.benchmark_vectors import generate_rtl_benchmark, write_rtl_benchmark
    from cryobrain.types import ScenarioConfig

    scenario = ScenarioConfig.from_dict(json.loads(scenario_path.read_text(encoding="utf-8")))
    benchmark = generate_rtl_benchmark(scenario)
    path = write_rtl_benchmark(workdir / "dv" / "stim_benchmark_vectors.mem", benchmark)
    return path, benchmark.metadata


def run_rtl_flow(workdir: Path, *, golden_mode: bool = False) -> RtlFlowResult:
    """Run lint, visible sim, and synthesis in the agent workspace."""
    logs: dict[str, str] = {}
    rtl = workdir / "rtl" / "cryo_brain_decoder.sv"
    visible_tb = workdir / "dv" / "visible_tb.sv"
    build_dir = workdir / "build"
    report_dir = workdir / "reports"
    build_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    missing = missing_eda_tools()
    tools_available = not missing
    if missing:
        banner = (
            "RTL flow skipped: required EDA tools are unavailable "
            f"({', '.join(missing)}). Reward validity gate will fail until "
            "verilator and yosys are installed."
        )
        for tool in missing:
            logs[tool] = _tool_missing_log(tool)
        logs["summary"] = banner
        return RtlFlowResult(
            sim_passed=False,
            synth_passed=False,
            lint_passed=False,
            cell_count=0,
            area_estimate=0.0,
            latency_cycles=12,
            logs=logs,
            tools_available=False,
        )

    lint = run_cmd(
        ["verilator", "--lint-only", "-Wall", "-Wno-fatal", "--top-module", "cryo_brain_decoder", str(rtl)],
        cwd=workdir,
    )
    logs["lint"] = lint.stdout or ""
    lint_passed = lint.returncode == 0

    sim_passed = False
    benchmark = {
        "vectors": 0,
        "failures": 0,
        "valid": 0,
        "exactness": 0.0,
        "confidence": 0.0,
    }
    if visible_tb.is_file():
        benchmark_path, benchmark_meta = _ensure_benchmark_vectors(workdir)
        if benchmark_meta:
            logs["benchmark_metadata"] = json.dumps(benchmark_meta, sort_keys=True)
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
            sim_bin = build_dir / "obj_visible" / "cryo_brain_decoder_visible"
            if platform.system() == "Windows" and not sim_bin.exists():
                sim_bin = sim_bin.with_suffix(".exe")
            run_args = [str(sim_bin)]
            if benchmark_path is not None:
                run_args.append(f"+BENCHMARK_VECTORS={benchmark_path}")
            run_bin = run_cmd(run_args, cwd=workdir)
            logs["sim"] = run_bin.stdout or ""
            scenario_re = re.compile(
                r"^SCENARIO\s+(?P<name>\S+)\s+(?P<status>PASS|FAIL)",
                flags=re.MULTILINE,
            )
            scenarios = list(scenario_re.finditer(run_bin.stdout or ""))
            benchmark = _parse_benchmark(run_bin.stdout or "")
            sim_passed = (
                run_bin.returncode == 0
                and any(m.group("status") == "PASS" for m in scenarios)
                and not any(m.group("status") == "FAIL" for m in scenarios)
                and int(benchmark["vectors"]) > 0
                and int(benchmark["valid"]) == int(benchmark["vectors"])
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
        tools_available=True,
        benchmark_vectors=int(benchmark["vectors"]),
        benchmark_failures=int(benchmark["failures"]),
        benchmark_exactness=float(benchmark["exactness"]),
        benchmark_confidence=float(benchmark["confidence"]),
    )
