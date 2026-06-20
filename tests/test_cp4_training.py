from pathlib import Path
import json

from cryobrain.rl.config import TrainConfig
from cryobrain.rl.local_trainer import run_graded_training


def fake_grade(workdir: Path) -> dict[str, object]:
    scenario = json.loads((workdir / "scenario.json").read_text(encoding="utf-8"))
    design = json.loads((workdir / "design_config.json").read_text(encoding="utf-8"))
    distance_bonus = 0.01 * int(scenario["distance"])
    area_score = 1.0 - 0.01 * int(design["bitwidth"])
    reward = 0.35 + distance_bonus + 0.01 * area_score
    metrics = {"area_mm2": 0.001, "latency_cycles": 12, "power_mw": 1.0}
    return {
        "reward": reward,
        "hard_caps": [],
        "subscores": {
            "rtl_validity": {"result": {"benchmark_exactness": 0.5}},
            "ler_suppression": {"raw_score": 0.25},
            "latency": {"raw_score": 0.8, "result": metrics},
            "area": {"raw_score": area_score, "result": metrics},
        },
    }


def test_cp4_training_writes_real_backend_artifacts(tmp_path):
    config = TrainConfig(
        steps=6,
        seed=7,
        output=str(tmp_path / "climb_chart.json"),
        designs_output=str(tmp_path / "designs.json"),
    )

    result = run_graded_training(
        config,
        grade_fn=fake_grade,
        task_root=Path("tasks/cryo_brain_decoder"),
    )

    history = result["history"]
    assert result["backend"] == "real_local"
    assert len(history) == 6
    assert history[-1]["reward"] > history[0]["reward"]
    assert result["summary"]["end_reward"] == history[-1]["reward"]
    assert (tmp_path / "climb_chart.json").is_file()
    assert (tmp_path / "designs.json").is_file()
