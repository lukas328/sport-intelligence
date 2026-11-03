"""Video sources: a file link, YouTube (own or released videos only) and camera partner stubs."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.parse import urlparse

from handball_api.integrations.base import AdapterError, Stub


@dataclass(frozen=True)
class Recording:
    external_id: str
    title: str
    url: str
    duration_s: float | None = None
    recorded_at: str | None = None


class VideoSourceAdapter(Protocol):
    name: str

    def list_recordings(self, account: str) -> list[Recording]: ...
    def metadata(self, ref: str) -> Recording: ...
    def download_url(self, ref: str) -> str: ...
    def parse_webhook(self, payload: dict[str, Any]) -> Recording | None: ...


_VIDEO_EXT = (".mp4", ".mov", ".m4v", ".mkv", ".avi")


class FileLinkSource:
    """A direct https link to a video file the club owns (Dropbox, Drive export, NAS)."""

    name = "file_link"

    def _check(self, url: str) -> str:
        u = urlparse(url)
        if u.scheme != "https" or not u.netloc:
            raise AdapterError("Only https links are accepted")
        return url

    def list_recordings(self, account: str) -> list[Recording]:
        return []

    def metadata(self, ref: str) -> Recording:
        url = self._check(ref)
        title = urlparse(url).path.rsplit("/", 1)[-1] or "video"
        return Recording(external_id=url, title=title, url=url)

    def download_url(self, ref: str) -> str:
        url = self._check(ref)
        if not urlparse(url).path.lower().endswith(_VIDEO_EXT) and "dl=1" not in url:
            raise AdapterError("The link does not point to a video file")
        return url

    def parse_webhook(self, payload: dict[str, Any]) -> Recording | None:
        return None


_YT = re.compile(r"(?:youtube\.com/(?:watch\?v=|live/|shorts/)|youtu\.be/)([\w-]{11})")


class YouTubeSource:
    """Own or released YouTube videos. Downloading needs the owner's OAuth consent via the YouTube
    Data API; scraping or ripping is not done (terms of service)."""

    name = "youtube"

    def video_id(self, url: str) -> str:
        m = _YT.search(url)
        if not m:
            raise AdapterError("Not a YouTube video link")
        return m.group(1)

    def list_recordings(self, account: str) -> list[Recording]:
        return []

    def metadata(self, ref: str) -> Recording:
        vid = self.video_id(ref)
        return Recording(external_id=vid, title=f"YouTube {vid}", url=f"https://youtu.be/{vid}")

    def download_url(self, ref: str) -> str:
        self.video_id(ref)
        raise AdapterError(
            "YouTube videos can only be imported by their owner through the YouTube connection"
        )

    def parse_webhook(self, payload: dict[str, Any]) -> Recording | None:
        return None


class _CameraStub(Stub):
    name = "camera"

    def list_recordings(self, account: str) -> list[Recording]:
        raise self._missing()

    def metadata(self, ref: str) -> Recording:
        raise self._missing()

    def download_url(self, ref: str) -> str:
        raise self._missing()

    def parse_webhook(self, payload: dict[str, Any]) -> Recording | None:
        raise self._missing()


class VeoSource(_CameraStub):
    name = partner = "veo"


class SpiideoSource(_CameraStub):
    name = partner = "spiideo"


class AsportSource(_CameraStub):
    name = partner = "asport"


class HudlSource(_CameraStub):
    name = partner = "hudl"
