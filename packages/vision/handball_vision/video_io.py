"""Reading the proxy video: open it, decode it as a stream (PyAV, frames never touch the
disk) or sample frames across it by seeking."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import av
from numpy.typing import NDArray

U8 = NDArray[Any]  # images (OpenCV returns loosely typed arrays)


def _open(path: Path) -> tuple[Any, Any, float, int]:
    container = av.open(str(path))
    stream = container.streams.video[0]
    stream.thread_type = "AUTO"
    fps = float(stream.average_rate or 25)
    total = int(stream.frames or 0) or int(
        (float(stream.duration or 0) * float(stream.time_base or 0)) * fps
    )
    return container, stream, fps, total


def iter_frames(path: Path) -> Iterator[U8]:
    container, stream, _, _ = _open(path)
    try:
        for frame in container.decode(stream):
            yield frame.to_ndarray(format="bgr24")
    finally:
        container.close()


def sample_frames(path: Path, count: int) -> list[U8]:
    """Frames spread across the video via seeking (fast, no full decode)."""
    container, stream, _, _ = _open(path)
    try:
        duration = float(container.duration or 0) / av.time_base
        out: list[U8] = []
        for k in range(count):
            target = duration * (k + 0.5) / count
            container.seek(
                int(target / float(stream.time_base)), stream=stream, any_frame=False, backward=True
            )
            for frame in container.decode(stream):
                if frame.time is not None and frame.time >= target - 0.05:
                    out.append(frame.to_ndarray(format="bgr24"))
                    break
        return out
    finally:
        container.close()


def _frames(path: Path, max_frames: int | None) -> Iterator[U8]:
    for n, frame in enumerate(iter_frames(path)):
        if max_frames is not None and n >= max_frames:
            return
        yield frame
