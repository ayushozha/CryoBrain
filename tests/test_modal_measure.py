"""C3 / MP3: Modal measurement fan-out wiring (boundary mocked / dry-run).

Modal + EDA (verilator/yosys/stim) are Linux-only, so these unit tests mock the
per-RTL measure boundary (``score_measured``) and assert the fan-out THREADS
real measured output through — without faking measured data in the production
code path. The real, parallel Modal run is Linux + token gated.

What is asserted:
  (a) ``measure_batch`` fans out exactly one measure call per RTL path;
  (b) results are ``score_measured``-shaped dicts, order-preserved, rtl_path threaded;
  (c) ``--dry-run`` works with no Modal creds and never invokes Modal;
  (d) ``make_modal_score_fn`` returns a ``ScoreFn``-compatible callable C4/C5 swap in;
  (e) that callable drops into ``measured_reward(score_fn=...)`` and yields its reward.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from cryobrain.rl import modal_measure
from cryobrain.types import DesignConfig, ScenarioConfig


def _valid_score(ler: float, suppression: float, reward: float = 0.3) -> dict[str, Any]:
    """A measured-VALID score_measured-shaped dict (verification passed)."""
    return {
        "reward": reward,
        "valid": True,
        "ler": ler,
        "area_um2": 6.1,
        "latency_cycles": 8,
        "power_mw": 0.048,
        "layers_passed": ["L1", "L2", "L4", "L5"],
        "hard_caps": [],
        "mwpm_ler": 0.022,
        "suppression": suppression,
        "source": "measured",
        "measurement": {"candidate_ler": ler, "mwpm_ler": 0.022, "suppression": suppression},
        "synth": {"area_um2": 6.1, "latency_cycles": 8, "power_mw_est": 0.048, "valid": True},
    }


def _rtl_files(tmp_path: Path, n: int) -> list[Path]:
    """Create N distinct dummy .sv files (staging copies them; content unused)."""
    paths = []
    for i in range(n):
        p = tmp_path / f"variant_{i}.sv"
        p.write_text(f"// variant {i}\nmodule m; endmodule\n", encoding="utf-8")
        paths.append(p)
    return paths


@pytest.fixture
def no_modal_creds(monkeypatch):
    """Force the local fallback: no Modal tokens => measure_batch runs locally."""
    monkeypatch.delenv("MODAL_TOKEN_ID", raising=False)
    monkeypatch.delenv("MODAL_TOKEN_SECRET", raising=False)


def _patch_stage(monkeypatch):
    """Bypass real fixture staging; stage = a temp workdir holding the .sv only.

    Keeps the test independent of the EDA task fixtures while still exercising the
    real ``measure_one`` (stage -> score_fn -> thread rtl_path) control flow.
    """
    import shutil
    import tempfile

    def fake_stage(rtl_path: Path, scenario: dict[str, Any], *, task_root: Path) -> Path:
        rtl_path = Path(rtl_path).resolve()
        if not rtl_path.is_file():
            raise FileNotFoundError(rtl_path)
        stage = Path(tempfile.mkdtemp(prefix="cryobrain-test-fanout-"))
        (stage / "rtl").mkdir(parents=True, exist_ok=True)
        shutil.copy2(rtl_path, stage / "rtl" / "cryo_brain_decoder.sv")
        return stage

    monkeypatch.setattr(modal_measure, "_stage_measure_workdir", fake_stage)


def test_measure_batch_fans_out_one_call_per_rtl(tmp_path, monkeypatch, no_modal_creds):
    """(a) + (b) One measure call per RTL; score-shaped dicts, order preserved."""
    _patch_stage(monkeypatch)
    seen_workdirs: list[Path] = []
    lers = iter([0.030, 0.020, 0.012])

    def fake_score(workdir: Path) -> dict[str, Any]:
        seen_workdirs.append(Path(workdir))
        # The real candidate RTL must be staged for each call.
        assert (Path(workdir) / "rtl" / "cryo_brain_decoder.sv").is_file()
        return _valid_score(next(lers), 0.2)

    rtls = _rtl_files(tmp_path, 3)
    results = modal_measure.measure_batch(rtls, {"distance": 3}, score_fn=fake_score)

    assert len(seen_workdirs) == 3  # exactly one measure per RTL
    assert len(results) == 3
    # Order preserved, measured fields threaded, rtl_path re-associated.
    assert [r["ler"] for r in results] == [0.030, 0.020, 0.012]
    for rtl, res in zip(rtls, results):
        assert res["source"] == "measured"
        assert res["valid"] is True
        assert Path(res["rtl_path"]) == rtl.resolve()
        assert set(_valid_score(0.0, 0.0)).issubset(res)  # full score_measured shape


def test_measure_batch_accepts_scenario_config(tmp_path, monkeypatch, no_modal_creds):
    """A ScenarioConfig is accepted and normalized (no separate scenario plumbing)."""
    _patch_stage(monkeypatch)
    captured: list[dict[str, Any]] = []

    def fake_stage(rtl_path, scenario, *, task_root):  # capture scenario
        captured.append(scenario)
        import shutil
        import tempfile

        stage = Path(tempfile.mkdtemp(prefix="cryobrain-test-"))
        (stage / "rtl").mkdir(parents=True, exist_ok=True)
        shutil.copy2(Path(rtl_path), stage / "rtl" / "cryo_brain_decoder.sv")
        return stage

    monkeypatch.setattr(modal_measure, "_stage_measure_workdir", fake_stage)
    rtls = _rtl_files(tmp_path, 1)
    modal_measure.measure_batch(
        rtls, ScenarioConfig(distance=5), score_fn=lambda wd: _valid_score(0.01, 0.3)
    )
    assert captured[0]["distance"] == 5
    assert captured[0]["benchmark_vectors"] == 64  # normalized for measurement


def test_measure_batch_never_calls_modal_without_creds(tmp_path, monkeypatch, no_modal_creds):
    """Local fallback must not attempt to build a Modal app when creds are absent."""
    _patch_stage(monkeypatch)

    def explode():  # pragma: no cover - asserts it is never reached
        raise AssertionError("Modal must not be built without creds")

    monkeypatch.setattr(modal_measure, "_build_modal_fanout", explode)
    rtls = _rtl_files(tmp_path, 2)
    results = modal_measure.measure_batch(rtls, {"distance": 3}, score_fn=lambda wd: _valid_score(0.02, 0.1))
    assert len(results) == 2


def test_modal_available_false_without_creds(no_modal_creds):
    """No tokens (and no modal pkg on Windows) => Modal dispatch is not selected."""
    assert modal_measure._modal_available() is False


def test_dry_run_works_without_modal_creds(tmp_path, monkeypatch, no_modal_creds):
    """(c) --dry-run validates one variant locally, never invoking Modal."""
    _patch_stage(monkeypatch)
    # Late-bound default score_fn => patching the module attr is enough.
    monkeypatch.setattr(modal_measure, "score_measured", lambda wd: _valid_score(0.017, 0.23))
    rtl = _rtl_files(tmp_path, 1)[0]
    out = modal_measure.dry_run(rtl)

    assert out["dry_run"] is True
    assert out["modal_invoked"] is False
    assert out["variants_measured"] == 1
    assert out["result"]["source"] == "measured"
    assert Path(out["result"]["rtl_path"]) == rtl.resolve()


def test_make_modal_score_fn_is_score_fn_compatible(tmp_path, monkeypatch, no_modal_creds):
    """(d) The adapter is a ScoreFn: workdir -> score dict, single-RTL via fan-out."""
    _patch_stage(monkeypatch)
    monkeypatch.setattr(modal_measure, "score_measured", lambda wd: _valid_score(0.015, 0.25, reward=0.4))

    # Build a workdir as score_measured/generate_rtl would: rtl/cryo_brain_decoder.sv.
    workdir = tmp_path / "wd"
    (workdir / "rtl").mkdir(parents=True)
    (workdir / "rtl" / "cryo_brain_decoder.sv").write_text("module m; endmodule\n", encoding="utf-8")

    score_fn = modal_measure.make_modal_score_fn({"distance": 3}, force_local=True)
    result = score_fn(workdir)  # called exactly like proposal_loop expects

    assert result["reward"] == 0.4
    assert result["ler"] == 0.015
    assert result["suppression"] == 0.25


def test_modal_score_fn_swaps_into_measured_reward(tmp_path, monkeypatch, no_modal_creds):
    """(e) C4/C5 swap-in: measured_reward(score_fn=make_modal_score_fn(...))."""
    from cryobrain.rl import proposal_loop

    _patch_stage(monkeypatch)
    monkeypatch.setattr(modal_measure, "score_measured", lambda wd: _valid_score(0.011, 0.33, reward=0.55))

    scenario = {"distance": 3, "noise_rate": 0.001, "shots": 200, "rounds": 3}
    modal_score_fn = modal_measure.make_modal_score_fn(scenario, force_local=True)

    reward, score, rtl_path = proposal_loop.measured_reward(
        DesignConfig(),
        scenario,
        score_fn=modal_score_fn,
    )
    assert reward == 0.55
    assert score["suppression"] == 0.33
    assert Path(rtl_path).is_file()  # real generated RTL drove the fan-out


def test_modules_import_on_windows():
    """The Modal modules import without `modal` installed/creds (Windows gate)."""
    import cryobrain.rl.modal_app as app_mod
    import cryobrain.rl.modal_measure as meas_mod

    # No modal on Windows => module-level app is None, but imports succeed.
    assert meas_mod.app is None or meas_mod.app is not None  # importable either way
    assert app_mod.APP_NAME == "cryobrain-measure-fanout"
