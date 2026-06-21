"""L3 formal gate — SymbiYosys BMC smoke on decoder SVA (SPEC-v5 X3)."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import NotRequired, TypedDict

from cryobrain.rtl_grader.flow import tool_env
from cryobrain.rtl_grader.stage import cleanup_stage, stage_rtl_workdir

REPO_ROOT = Path(__file__).resolve().parents[2]
SVA_TEMPLATE = REPO_ROOT / "tasks" / "cryo_brain_decoder" / "sva" / "decoder_props.sva"
_FORMAL_TIMEOUT_S = 180


class L3Result(TypedDict):
    passed: bool
    log_path: str
    skipped: NotRequired[bool]
    reason: NotRequired[str]


def symbiyosys_available() -> bool:
    """Return True when ``sby`` is discoverable on PATH (OSS CAD / WSL)."""
    return shutil.which("sby", path=tool_env().get("PATH", "")) is not None


def _write_formal_top(path: Path) -> None:
    path.write_text(
        """\
module cryo_brain_decoder_formal_top;
    localparam int SYNDROME_WIDTH = 8;
    localparam int CORRECTION_WIDTH = 4;
    localparam int CONFIDENCE_WIDTH = 8;

    (* gclk *) logic clk;
    logic rst_n;
    (* anyseq *) logic syndromes_valid;
    (* anyseq *) logic [SYNDROME_WIDTH-1:0] syndromes;
    logic corrections_valid;
    logic [CORRECTION_WIDTH-1:0] corrections;
    logic [CONFIDENCE_WIDTH-1:0] confidence;

    initial begin
        rst_n = 1'b0;
    end

    always @(posedge clk) rst_n <= 1'b1;

    cryo_brain_decoder #(
        .SYNDROME_WIDTH(SYNDROME_WIDTH),
        .CORRECTION_WIDTH(CORRECTION_WIDTH),
        .CONFIDENCE_WIDTH(CONFIDENCE_WIDTH)
    ) dut (
        .clk(clk),
        .rst_n(rst_n),
        .syndromes_valid(syndromes_valid),
        .syndromes(syndromes),
        .corrections_valid(corrections_valid),
        .corrections(corrections),
        .confidence(confidence)
    );

    cryo_brain_decoder_props #(
        .CONFIDENCE_WIDTH(CONFIDENCE_WIDTH)
    ) props (
        .clk(clk),
        .rst_n(rst_n),
        .corrections_valid(corrections_valid),
        .confidence(confidence)
    );
endmodule
""",
        encoding="utf-8",
    )


def _write_sby_file(
    sby_path: Path,
    *,
    rtl: Path,
    formal_top: Path,
    props: Path,
    depth: int = 12,
) -> None:
    source_args = " ".join(str(path) for path in (rtl, formal_top, props))
    sby_path.write_text(
        f"""\
[options]
mode bmc
depth {depth}

[engines]
smtbmc z3

[script]
read -formal -sv {source_args}
prep -top cryo_brain_decoder_formal_top
""",
        encoding="utf-8",
    )


def run_l3_formal(rtl_path: Path, *, depth: int = 12) -> L3Result:
    """Run SymbiYosys BMC smoke on ``rtl_path`` using ``decoder_props.sva``.

    When ``sby`` is not on PATH the layer is skipped (``passed=False``, ``skipped=True``)
    so callers can treat missing tooling as non-fatal on dev hosts without formal EDA.
    """
    rtl_path = Path(rtl_path).resolve()
    if not symbiyosys_available():
        return L3Result(
            passed=False,
            log_path="",
            skipped=True,
            reason="symbiyosys (sby) not on PATH",
        )
    if not SVA_TEMPLATE.is_file():
        return L3Result(
            passed=False,
            log_path="",
            skipped=True,
            reason=f"SVA template missing: {SVA_TEMPLATE}",
        )

    stage = stage_rtl_workdir(rtl_path, prefix="cryobrain-l3-")
    log_path = stage / "reports" / "l3_formal.log"
    formal_dir = stage / "formal"
    formal_dir.mkdir(parents=True, exist_ok=True)
    try:
        rtl = stage / "rtl" / "cryo_brain_decoder.sv"
        props = formal_dir / "decoder_props.sva"
        formal_top = formal_dir / "cryo_brain_decoder_formal_top.sv"
        shutil.copy2(SVA_TEMPLATE, props)
        _write_formal_top(formal_top)

        work = stage / "build" / "formal" / "bmc"
        work.mkdir(parents=True, exist_ok=True)
        shutil.rmtree(work / "job", ignore_errors=True)
        sby_file = work / "job.sby"
        _write_sby_file(sby_file, rtl=rtl, formal_top=formal_top, props=props, depth=depth)

        proc = subprocess.run(
            ["sby", "-f", sby_file.name],
            cwd=work,
            env=tool_env(),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            timeout=_FORMAL_TIMEOUT_S,
        )
        log_path.write_text(proc.stdout or "", encoding="utf-8")
        passed = proc.returncode == 0 and "PASS" in (proc.stdout or "")
        return L3Result(passed=passed, log_path=str(log_path))
    except subprocess.TimeoutExpired:
        log_path.write_text(f"symbiyosys timed out after {_FORMAL_TIMEOUT_S}s", encoding="utf-8")
        return L3Result(passed=False, log_path=str(log_path))
    except FileNotFoundError as exc:
        return L3Result(
            passed=False,
            log_path=str(log_path),
            skipped=True,
            reason=f"symbiyosys invocation failed: {exc}",
        )
    finally:
        cleanup_stage(stage)
