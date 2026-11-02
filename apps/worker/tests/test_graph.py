import pytest

from handball_worker.pipeline import GraphError, PipelineGraph, Stage
from handball_worker.pipeline.stages import build_pipeline


def test_v1_pipeline_is_valid() -> None:
    g = build_pipeline()
    order = g.order()
    assert order[0] == "ingest"
    assert order.index("tracking") > order.index("detection")
    assert order.index("insights") > order.index("metrics")
    assert order[-1] == "clips"


def test_correction_only_recomputes_downstream() -> None:
    g = build_pipeline()
    assert g.downstream(["corrections"]) == ["metrics", "insights", "clips"]


def test_duplicate_stage() -> None:
    with pytest.raises(GraphError, match="duplicate"):
        PipelineGraph([Stage.of("a", outputs=["x"]), Stage.of("a", outputs=["y"])])


def test_duplicate_producer() -> None:
    with pytest.raises(GraphError, match="produced by"):
        PipelineGraph([Stage.of("a", outputs=["x"]), Stage.of("b", outputs=["x"])])


def test_external_cannot_be_produced() -> None:
    with pytest.raises(GraphError, match="external"):
        PipelineGraph([Stage.of("a", outputs=["x"])], external_inputs=["x"])


def test_unknown_input() -> None:
    with pytest.raises(GraphError, match="unknown inputs"):
        PipelineGraph([Stage.of("a", inputs=["nope"], outputs=["x"])])


def test_cycle() -> None:
    with pytest.raises(GraphError, match="cycle"):
        PipelineGraph([Stage.of("a", ["y"], ["x"]), Stage.of("b", ["x"], ["y"])])


def test_cache_key_changes_with_inputs_and_version() -> None:
    g = PipelineGraph([Stage.of("a", ["in"], ["x"], version="1")], external_inputs=["in"])
    k1 = g.cache_key("a", {"in": "h1"})
    assert k1 == g.cache_key("a", {"in": "h1"})
    assert k1 != g.cache_key("a", {"in": "h2"})
    g2 = PipelineGraph([Stage.of("a", ["in"], ["x"], version="2")], external_inputs=["in"])
    assert k1 != g2.cache_key("a", {"in": "h1"})
    with pytest.raises(GraphError, match="missing input"):
        g.cache_key("a", {})
