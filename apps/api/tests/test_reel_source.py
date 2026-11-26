"""The court a server-side render draws with (services/video_media.court_for_render) and what
the reel worker gets of a file (services/highlights._source). A moving camera's court refers to
the hall image (ADR 020): the render follows the camera with the view files, or draws nothing."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Any

import pytest

from handball_api.services import highlights
from handball_api.services.video_media import court_for_render

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


PANO = {"width": 1800, "height": 400}
MOVING = {"camera": "moving", "view_chunks": 2, "frame_size": [1280, 720], "panorama": PANO}


@pytest.mark.parametrize(
    ("meta", "expect"),
    [
        # a fixed camera: the calibration as it is
        ({"camera": "fixed"}, {"homography": COURT, "image_size": [1800, 400]}),
        ({}, {"homography": COURT, "image_size": [1800, 400]}),
        # a moving one with view files: the court on the hall image plus where it looked
        (
            MOVING,
            {
                "homography": COURT,
                "image_size": [1800, 400],
                "view_chunks": 2,
                "frame_size": [1280, 720],
            },
        ),
        # without view files (an analysis from before), or a court not on the hall image
        ({**MOVING, "view_chunks": None}, None),
        ({**MOVING, "frame_size": None}, None),
        ({**MOVING, "panorama": {"width": 1280, "height": 720}}, None),
    ],
)
def test_court_for_render(meta: dict[str, Any], expect: dict[str, Any] | None) -> None:
    cal = SimpleNamespace(homography=COURT, image_size=[1800, 400])
    assert court_for_render(meta, cal) == expect
    assert court_for_render(meta, None) is None


async def test_reel_source_follows_a_moving_camera() -> None:
    cal = SimpleNamespace(homography=COURT, image_size=[1800, 400])
    source, spots = await highlights._source(_ctx(cal), _asset({"chunk_ms": 30_000, **MOVING}))
    assert source["chunk_ms"] == 30_000 and spots == {}
    assert (source["homography"], source["view_chunks"], source["frame_size"]) == (
        COURT,
        2,
        [1280, 720],
    )
    old, _ = await highlights._source(
        _ctx(cal), _asset({"chunk_ms": 30_000, **MOVING, "view_chunks": None})
    )
    assert old["homography"] is None and old["view_chunks"] is None


async def test_reel_source_without_a_court() -> None:
    source, _ = await highlights._source(_ctx(None), _asset({"chunk_ms": 30_000}))
    assert source["homography"] is None and source["image_size"] is None
