from cryobrain.design.config import GOLDEN_BASELINE
from cryobrain.retrieval.context_pack import ContextPack
from cryobrain.rl.proposal_loop import apply_research_bias
from cryobrain.types import DesignConfig


def _pack(snippet: str) -> ContextPack:
    return ContextPack(query="qec", hits=[{"url": "https://example.test/paper", "snippet": snippet}])


def test_research_bias_preserves_golden_seed():
    biased = apply_research_bias(GOLDEN_BASELINE, _pack("fpga parallel pipeline latency"))

    assert biased == GOLDEN_BASELINE


def test_research_bias_chains_independent_themes():
    design = DesignConfig(bitwidth=4, num_layers=2, parallelism=1, pipeline_depth=4, window_length=8)

    biased = apply_research_bias(design, _pack("parallel fpga pipeline latency"))

    assert biased.parallelism == 2
    assert biased.pipeline_depth == 6
