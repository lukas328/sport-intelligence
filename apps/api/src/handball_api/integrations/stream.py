"""Livestream partners (no own livestream, non-goal): assign a match, fetch the recording."""

from __future__ import annotations

from typing import Protocol

from handball_api.integrations.base import Stub


class StreamPartnerAdapter(Protocol):
    name: str

    def assign_match(self, stream_id: str, match_ref: str) -> None: ...
    def fetch_recording(self, stream_id: str) -> str: ...


class StreamStub(Stub):
    name = partner = "stream_partner"

    def assign_match(self, stream_id: str, match_ref: str) -> None:
        raise self._missing()

    def fetch_recording(self, stream_id: str) -> str:
        raise self._missing()
