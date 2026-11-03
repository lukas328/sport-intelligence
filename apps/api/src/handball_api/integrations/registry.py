"""Lookup of adapters by category and name."""

from __future__ import annotations

from typing import Any

from handball_api.integrations import official_feed, stream, team_ops, video_sources, wearables
from handball_api.integrations.base import AdapterError

ADAPTERS: dict[str, dict[str, type[Any]]] = {
    "video_source": {
        c.name: c
        for c in (
            video_sources.FileLinkSource,
            video_sources.YouTubeSource,
            video_sources.VeoSource,
            video_sources.SpiideoSource,
            video_sources.AsportSource,
            video_sources.HudlSource,
        )
    },
    "stream": {stream.StreamStub.name: stream.StreamStub},
    "team_ops": {
        c.name: c for c in (team_ops.IcsTeamOps, team_ops.SpondTeamOps, team_ops.ClubCornerTeamOps)
    },
    "official_feed": {
        c.name: c
        for c in (official_feed.CsvFeed, official_feed.JsonFeed, official_feed.HandballChFeed)
    },
    "wearable": {
        c.name: c
        for c in (wearables.CsvWearable, wearables.KinexonWearable, wearables.PolarWearable)
    },
}


def adapter(category: str, name: str) -> Any:
    try:
        return ADAPTERS[category][name]()
    except KeyError as exc:
        raise AdapterError(f"Unknown adapter {category}/{name}") from exc
