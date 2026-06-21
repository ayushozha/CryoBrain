from pathlib import Path

from cryobrain.memory.buffer import VerifiedDesignBuffer, VerifiedDesignRecord
from cryobrain.memory.retrieve import retrieve


def test_buffer_keeps_top_k_by_reward(tmp_path: Path):
    path = tmp_path / "memory.json"
    buf = VerifiedDesignBuffer(path, capacity=2)
    buf.add(VerifiedDesignRecord(design={"bitwidth": 2}, reward=0.3, metrics={}))
    buf.add(VerifiedDesignRecord(design={"bitwidth": 4}, reward=0.5, metrics={}))
    buf.add(VerifiedDesignRecord(design={"bitwidth": 8}, reward=0.4, metrics={}))
    assert len(buf) == 2
    top = buf.top(2)
    assert top[0].reward == 0.5
    assert top[1].reward == 0.4


def test_retrieve_prefers_matching_distance(tmp_path: Path):
    path = tmp_path / "memory.json"
    buf = VerifiedDesignBuffer(path)
    buf.add(
        VerifiedDesignRecord(
            design={"bitwidth": 4, "num_layers": 1, "parallelism": 1, "pipeline_depth": 4, "window_length": 8},
            reward=0.45,
            metrics={},
            distance=5,
        )
    )
    buf.add(
        VerifiedDesignRecord(
            design={"bitwidth": 2, "num_layers": 1, "parallelism": 2, "pipeline_depth": 2, "window_length": 4},
            reward=0.38,
            metrics={},
            distance=3,
        )
    )
    hits = retrieve({"distance": 3, "noise_rate": 0.001}, buffer_path=path, k=1)
    assert hits
    assert hits[0]["distance"] == 3