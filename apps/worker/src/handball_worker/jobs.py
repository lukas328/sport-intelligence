from __future__ import annotations

import platform
import time
from typing import Any

from handball_worker import __version__


def ping(payload: str = "ping") -> dict[str, Any]:
    """Smoke-test job: proves the queue round trip works end to end."""
    return {
        "reply": "pong",
        "payload": payload,
        "worker_version": __version__,
        "host": platform.node(),
        "ts": time.time(),
    }
