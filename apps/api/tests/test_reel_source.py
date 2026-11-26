"""What the reel worker gets of a file (services/highlights._source): the court only when it
refers to the frame. A moving camera's court refers to the hall image (ADR 020), the reel renders
without ring and crop there."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Any

import pytest

from handball_api.services import highlights

COURT = [[2.0, 0, 10], [0, 2.0, 5], [0, 0, 1]]


def _ctx(cal: Any) -> Any:
    async def scalar(_q: Any) -> Any:
        return cal

    async def scalars(_q: Any) -> Any:
        return SimpleNamespace(all=lambda: [])

    return SimpleNamespace(db=SimpleNamespace(scalar=scalar, scalars=scalars))


def _asset(analysis: dict[str, Any]) -> Any:
    return SimpleNamespace(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        match_id=uuid.uuid4(),
        proxy_key="x/proxy.mp4",
        analysis=analysis,
    )


@pytest.mark.parametrize(("camera", "court"), [("fixed", True), (None, True), ("moving", False)])
async def test_reel_source_carries_the_court_only_on_the_frame(
    camera: str | None, court: bool
) -> None:
    cal = SimpleNamespace(homography=COURT, image_size=[1800, 400])
    meta = {"chunk_ms": 30_000, "camera": camera, "view_chunks": 2}
    source, spots = await highlights._source(_ctx(cal), _asset(meta))
    assert source["chunk_ms"] == 30_000 and spots == {}
    assert (source["homography"], source["image_size"]) == (
        (COURT, [1800, 400]) if court else (None, None)
    )


async def test_reel_source_without_a_court() -> None:
    source, _ = await highlights._source(_ctx(None), _asset({"chunk_ms": 30_000}))
    assert source["homography"] is None and source["image_size"] is None
