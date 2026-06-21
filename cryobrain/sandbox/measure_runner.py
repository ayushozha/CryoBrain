"""Run the measured-LER flow inside a forked Daytona sandbox (SPEC-v5 C7).

``measure_in_sandbox`` provisions a Daytona sandbox, transfers the ``cryobrain``
package + the decoder task fixtures + the candidate RTL, runs the *same*
``measure_candidate_ler`` path inside it (the sandbox is where the Linux-only EDA
tools -- Verilator/Yosys -- actually live), returns the ``MeasureResult``-shaped
dict, and destroys the sandbox in a ``finally`` block.

It does NOT reimplement LER: it orchestrates Grok's ``measure_candidate_ler`` on
a remote Linux executor and parses its result back. Without the Daytona SDK or
``DAYTONA_API_KEY`` it raises ``RuntimeError`` -- it never fabricates a result.
"""

from __future__ import annotations

import io
import json
import tarfile
from pathlib import Path

from cryobrain.integrations.daytona import daytona_available, daytona_sandbox
from cryobrain.types import ScenarioConfig

_REPO_ROOT = Path(__file__).resolve().parents[2]
_TASK_REL = "tasks/cryo_brain_decoder"
_CANDIDATE_REL = f"{_TASK_REL}/rtl/cryo_brain_decoder.sv"

# MeasureResult (TypedDict) fields the parsed sandbox result must carry.
_RESULT_FIELDS = (
    "candidate_ler",
    "mwpm_ler",
    "suppression",
    "shots",
    "vector_source",
    "rtl_path",
    "benchmark_vectors",
    "benchmark_failures",
    "rtl_valid",
)

# Runtime deps the in-sandbox driver needs (EDA binaries come from the image).
_PIP_DEPS = "numpy stim pymatching"

_REMOTE_ROOT = "/home/daytona/cryobrain"
_RESULT_PATH = f"{_REMOTE_ROOT}/measure_result.json"


def _build_payload(rtl_path: Path) -> bytes:
    """Tar the cryobrain package, task fixtures, and candidate RTL into memory.

    The candidate ``rtl_path`` overwrites the task's ``rtl/cryo_brain_decoder.sv``
    so the in-sandbox ``measure_candidate_ler`` stages exactly this design.
    """
    rtl_path = rtl_path.resolve()
    if not rtl_path.is_file():
        raise FileNotFoundError(f"RTL not found: {rtl_path}")

    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        tar.add(_REPO_ROOT / "cryobrain", arcname="cryobrain")
        tar.add(_REPO_ROOT / _TASK_REL, arcname=_TASK_REL)
        # Overwrite the staged candidate with the variant under test.
        data = rtl_path.read_bytes()
        info = tarfile.TarInfo(name=_CANDIDATE_REL)
        info.size = len(data)
        info.mode = 0o644
        tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def _driver_source(scenario: ScenarioConfig, *, shots: int, seed: int, benchmark_vectors: int) -> str:
    """Python the sandbox runs to call measure_candidate_ler and emit JSON."""
    return (
        "import json, sys\n"
        f"sys.path.insert(0, {_REMOTE_ROOT!r})\n"
        "from pathlib import Path\n"
        "from cryobrain.accuracy.measured_ler import measure_candidate_ler\n"
        "from cryobrain.types import ScenarioConfig\n"
        "scenario = ScenarioConfig("
        f"distance={scenario.distance}, noise_rate={scenario.noise_rate!r}, "
        f"shots={scenario.shots}, rounds={scenario.rounds})\n"
        f"rtl = Path({_REMOTE_ROOT!r}) / {_CANDIDATE_REL!r}\n"
        "result = measure_candidate_ler(rtl, scenario, "
        f"shots={shots}, seed={seed}, benchmark_vectors={benchmark_vectors})\n"
        f"Path({_RESULT_PATH!r}).write_text(json.dumps(dict(result)))\n"
        "print('CRYOBRAIN_MEASURE_OK')\n"
    )


def _remote_command(scenario: ScenarioConfig, *, shots: int, seed: int, benchmark_vectors: int) -> str:
    """Shell command: unpack payload, install deps, run the driver."""
    driver = _driver_source(scenario, shots=shots, seed=seed, benchmark_vectors=benchmark_vectors)
    # base64-encode the driver so quoting survives the shell round-trip.
    import base64

    driver_b64 = base64.b64encode(driver.encode("utf-8")).decode("ascii")
    return (
        f"set -e\n"
        f"mkdir -p {_REMOTE_ROOT}\n"
        f"tar -xzf /tmp/cryobrain_payload.tgz -C {_REMOTE_ROOT}\n"
        f"python3 -m pip install --quiet {_PIP_DEPS} >/dev/null 2>&1 || true\n"
        f"echo {driver_b64} | base64 -d > {_REMOTE_ROOT}/_driver.py\n"
        f"python3 {_REMOTE_ROOT}/_driver.py\n"
    )


def measure_in_sandbox(
    rtl_path: Path,
    scenario: ScenarioConfig,
    *,
    shots: int = 1000,
    seed: int = 0,
    benchmark_vectors: int = 64,
    timeout_sec: int = 900,
) -> dict:
    """Measure ``rtl_path`` inside a fresh Daytona sandbox; destroy it after.

    Returns a ``MeasureResult``-shaped dict (same fields as the local
    ``measure_candidate_ler``), produced by running that exact function inside a
    Linux sandbox where Verilator/Yosys are installed. The sandbox is created,
    used, and destroyed within this call (teardown in a ``finally`` block).

    Raises ``RuntimeError`` when the Daytona SDK or ``DAYTONA_API_KEY`` is
    unavailable -- it never returns a fabricated measurement.
    """
    if not daytona_available():
        raise RuntimeError("Daytona SDK or DAYTONA_API_KEY unavailable; cannot measure in sandbox")

    payload = _build_payload(Path(rtl_path))
    command = _remote_command(scenario, shots=shots, seed=seed, benchmark_vectors=benchmark_vectors)

    with daytona_sandbox() as sandbox:
        sandbox.fs.upload_file(payload, "/tmp/cryobrain_payload.tgz")
        response = sandbox.process.exec(command, timeout=timeout_sec)
        exit_code = int(getattr(response, "exit_code", 1))
        if exit_code != 0:
            raise RuntimeError(
                f"sandbox measure failed (exit {exit_code}): {getattr(response, 'result', '')[:2000]}"
            )
        raw = sandbox.fs.download_file(_RESULT_PATH)
        result = json.loads(raw.decode("utf-8") if isinstance(raw, bytes) else raw)

    missing = [f for f in _RESULT_FIELDS if f not in result]
    if missing:
        raise RuntimeError(f"sandbox result missing MeasureResult fields: {missing}")
    return result
