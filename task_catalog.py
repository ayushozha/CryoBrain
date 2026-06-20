"""CryoBrain + fallback task catalog."""

from dataclasses import dataclass
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent
TASK_ROOT = ROOT_DIR / "tasks"


@dataclass(frozen=True)
class TaskSpec:
    task_id: str
    slug: str
    prompt: str
    track: str
    variant: str
    language: str
    module: str
    toolchain: str
    template: str = "cryo_task"


def _prompt(task_id: str) -> str:
    return (TASK_ROOT / task_id / "prompt.md").read_text(encoding="utf-8")


CRYO_BRAIN_DECODER_D3 = TaskSpec(
    task_id="cryo_brain_decoder",
    slug="cryo-brain-decoder-d3",
    prompt=_prompt("cryo_brain_decoder"),
    track="qec-codesign",
    variant="distance_3",
    language="systemverilog+python",
    module="cryo_brain_decoder",
    toolchain="verilator+yosys+stim",
    template="cryo_task",
)

CRYO_BRAIN_DECODER_D5 = TaskSpec(
    task_id="cryo_brain_decoder",
    slug="cryo-brain-decoder-d5",
    prompt=_prompt("cryo_brain_decoder"),
    track="qec-codesign",
    variant="distance_5",
    language="systemverilog+python",
    module="cryo_brain_decoder",
    toolchain="verilator+yosys+stim",
    template="cryo_task",
)

CRYO_BRAIN_DECODER_D7 = TaskSpec(
    task_id="cryo_brain_decoder",
    slug="cryo-brain-decoder-d7",
    prompt=_prompt("cryo_brain_decoder"),
    track="qec-codesign",
    variant="distance_7",
    language="systemverilog+python",
    module="cryo_brain_decoder",
    toolchain="verilator+yosys+stim",
    template="cryo_task",
)

STREAM_ARB_FIFO_REPAIR = TaskSpec(
    task_id="stream_arb_fifo_repair",
    slug="stream-arb-fifo-repair",
    prompt=_prompt("stream_arb_fifo_repair"),
    track="fallback-design",
    variant="repair_debug",
    language="systemverilog",
    module="stream_arb_fifo",
    toolchain="verilator+yosys",
    template="verilog_task",
)

STREAM_ARB_FIFO_COCOTB_DV = TaskSpec(
    task_id="stream_arb_fifo_cocotb_dv",
    slug="stream-arb-fifo-cocotb-dv",
    prompt=_prompt("stream_arb_fifo_cocotb_dv"),
    track="fallback-verification",
    variant="repair_debug",
    language="python+cocotb",
    module="stream_arb_fifo",
    toolchain="cocotb+verilator",
    template="verilog_task",
)

STREAM_ARB_FIFO_FORMAL = TaskSpec(
    task_id="stream_arb_fifo_formal",
    slug="stream-arb-fifo-formal",
    prompt=_prompt("stream_arb_fifo_formal"),
    track="fallback-formal",
    variant="repair_debug",
    language="systemverilog-formal",
    module="stream_arb_fifo",
    toolchain="symbiyosys+yosys",
    template="verilog_task",
)

TASK_SPECS = [
    CRYO_BRAIN_DECODER_D3,
    CRYO_BRAIN_DECODER_D5,
    CRYO_BRAIN_DECODER_D7,
    STREAM_ARB_FIFO_REPAIR,
    STREAM_ARB_FIFO_COCOTB_DV,
    STREAM_ARB_FIFO_FORMAL,
]

# HUD eval binds by slug (6 curriculum/fallback variants). On-disk graders share task_id.
TASK_SPECS_BY_SLUG = {spec.slug: spec for spec in TASK_SPECS}

# One metadata row per filesystem task directory (4 on-disk tasks).
TASK_SPECS_BY_TASK_ID: dict[str, TaskSpec] = {}
for _spec in TASK_SPECS:
    TASK_SPECS_BY_TASK_ID.setdefault(_spec.task_id, _spec)

# Back-compat alias used by grader/setup (filesystem task_id, not eval slug).
TASK_SPECS_BY_ID = TASK_SPECS_BY_TASK_ID

# RSI distance curriculum bindings (SPEC F7 / CP6)
CRYO_CURRICULUM = {
    "cryo-brain-decoder-d3": {
        "distance": 3,
        "noise_rate": 0.001,
        "max_latency_cycles": 64,
        "max_area_mm2": 0.06,
        "max_power_mw": 8.0,
    },
    "cryo-brain-decoder-d5": {
        "distance": 5,
        "noise_rate": 0.002,
        "max_latency_cycles": 96,
        "max_area_mm2": 0.08,
        "max_power_mw": 10.0,
    },
    "cryo-brain-decoder-d7": {
        "distance": 7,
        "noise_rate": 0.003,
        "max_latency_cycles": 128,
        "max_area_mm2": 0.10,
        "max_power_mw": 12.0,
    },
}

CRYO_SLUGS = tuple(CRYO_CURRICULUM)
FALLBACK_SLUGS = tuple(
    spec.slug for spec in TASK_SPECS if spec.track.startswith("fallback")
)


def curriculum_for_slug(slug: str) -> dict[str, float | int]:
    """Return RSI distance/noise/budget knobs for a cryo eval slug."""
    return dict(CRYO_CURRICULUM[slug])