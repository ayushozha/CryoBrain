"""Modal App + image definition for parallel measurement fan-out (SPEC-v5 C3).

This module owns the single Modal ``App`` and the container image used by the
measurement fan-out (:mod:`cryobrain.rl.modal_measure`). It mirrors the image
conventions already used by :mod:`cryobrain.rl.modal_train` so the two Modal
surfaces stay consistent (same apt EDA tools, same pip deps, same mounts).

Import-guarded by design: ``import modal`` happens *inside* :func:`build_image`
/ :func:`build_app`, never at module top level. The module therefore imports on
Windows (where ``modal`` and the EDA stack are absent) without raising — the
Windows gate is import + ``--dry-run`` + a unit test that mocks this boundary.
The real fan-out runs on Modal (Linux containers with verilator+yosys+stim).
"""

from __future__ import annotations

from pathlib import Path

APP_NAME = "cryobrain-measure-fanout"

# Repo root (…/cryobrain/rl/modal_app.py -> parents[2]).
ROOT = Path(__file__).resolve().parents[2]

# EDA + python deps installed into the Modal image. Verilator + Yosys are the
# real measurement backend (Stim->Verilator real LER, Yosys synth); stim +
# pymatching back ``measure_candidate_ler`` / the MWPM anchor. Kept in lock-step
# with cryobrain.rl.modal_train so both Modal images behave identically.
APT_PACKAGES = ("verilator", "yosys")
PIP_PACKAGES = (
    "stim>=1.14",
    "pymatching>=2.0",
    "numpy>=1.26",
    "pydantic>=2.0",
    "python-dotenv>=1.0",
)

# Directories mounted into the container: the cryobrain package (the real
# measurement code) + the decoder task fixtures (scenario.json, dv/, synth/,
# rtl/ — what ``measure_candidate_ler`` / ``score_measured`` stage and read).
LOCAL_PACKAGE_DIR = ROOT / "cryobrain"
LOCAL_TASKS_DIR = ROOT / "tasks"
REMOTE_PACKAGE_DIR = "/root/cryobrain"
REMOTE_TASK_DIR = "/root/tasks/cryo_brain_decoder"
PROJECT_ROOT_FILES = (
    "env.py",
    "tasks.py",
    "task_catalog.py",
    "grader.py",
    "scenario_helpers.py",
)


def _modal_source_ignore(path: Path) -> bool:
    return "donotaccess" in path.parts


def add_project_sources(image):
    image = image.add_local_dir(LOCAL_PACKAGE_DIR, remote_path=REMOTE_PACKAGE_DIR)
    image = image.add_local_dir(LOCAL_TASKS_DIR, remote_path="/root/tasks", ignore=_modal_source_ignore)
    for name in PROJECT_ROOT_FILES:
        path = ROOT / name
        if path.is_file():
            image = image.add_local_file(path, remote_path=f"/root/{name}")
    return image


def build_image():
    """Build the Modal image with verilator/yosys + stim and the mounted pkg.

    Raises :class:`ImportError` if ``modal`` is not installed (Windows). Callers
    in :mod:`cryobrain.rl.modal_measure` guard this and fall back to a local /
    dry-run path so the module is import-safe off-Modal.
    """
    import modal

    image = (
        modal.Image.debian_slim(python_version="3.12")
        .apt_install(*APT_PACKAGES)
        .pip_install(*PIP_PACKAGES)
    )
    return add_project_sources(image)


def build_app():
    """Construct the Modal ``App`` for the measurement fan-out.

    Returns the ``modal.App`` instance. Raises :class:`ImportError` when
    ``modal`` is unavailable. The fan-out function itself is registered by
    :mod:`cryobrain.rl.modal_measure` (which owns the per-RTL measure logic),
    so this stays a thin, single-source App/image definition.
    """
    import modal

    return modal.App(APP_NAME), build_image()
