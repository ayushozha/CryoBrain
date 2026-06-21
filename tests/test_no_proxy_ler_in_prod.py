"""X2 anti-cheat guard: production reward paths must not use proxy LER."""

from __future__ import annotations

import ast
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROD_PATHS = [
    ROOT / "cryobrain",
    ROOT / "tasks" / "cryo_brain_decoder",
    ROOT / "scripts",
]
FORBIDDEN_TEXT = (
    "simulate_candidate_ler",
    "decoder_quality_multiplier",
    "cryobrain.accuracy.decoder_policy",
)
FORBIDDEN_MODULE = "cryobrain.accuracy.decoder_policy"


def _prod_python_files() -> list[Path]:
    files: list[Path] = []
    for root in PROD_PATHS:
        if not root.exists():
            continue
        files.extend(
            path
            for path in root.rglob("*.py")
            if "__pycache__" not in path.parts and "tests" not in path.parts
        )
    return sorted(files)


def test_no_proxy_ler_symbols_in_production_sources():
    offenders: list[str] = []
    for path in _prod_python_files():
        text = path.read_text(encoding="utf-8")
        for token in FORBIDDEN_TEXT:
            if token in text:
                offenders.append(f"{path.relative_to(ROOT)} contains {token}")

    assert not offenders, "proxy/formula LER references remain:\n" + "\n".join(offenders)


def test_no_production_imports_from_decoder_policy():
    offenders: list[str] = []
    for path in _prod_python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == FORBIDDEN_MODULE:
                        offenders.append(f"{path.relative_to(ROOT)} imports {FORBIDDEN_MODULE}")
            elif isinstance(node, ast.ImportFrom) and node.module == FORBIDDEN_MODULE:
                offenders.append(f"{path.relative_to(ROOT)} imports from {FORBIDDEN_MODULE}")

    assert not offenders, "decoder_policy import path is production-forbidden:\n" + "\n".join(offenders)


def test_audit_reward_path_script_matches_pytest_guard():
    result = subprocess.run(
        ["bash", "scripts/audit_reward_path.sh"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    assert result.returncode == 0, result.stdout
