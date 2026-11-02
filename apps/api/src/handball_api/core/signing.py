"""Signed, expiring values for cookies (OAuth state). HMAC-SHA256 over compact JSON."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def sign(secret: str, payload: dict[str, Any], ttl_s: int, purpose: str) -> str:
    body = _b64(
        json.dumps({**payload, "_exp": int(time.time()) + ttl_s}, separators=(",", ":")).encode()
    )
    mac = hmac.new(secret.encode(), f"{purpose}.{body}".encode(), hashlib.sha256).digest()
    return f"{body}.{_b64(mac)}"


def unsign(secret: str, value: str, purpose: str) -> dict[str, Any] | None:
    try:
        body, mac = value.split(".", 1)
        expected = hmac.new(secret.encode(), f"{purpose}.{body}".encode(), hashlib.sha256).digest()
        if not hmac.compare_digest(_unb64(mac), expected):
            return None
        data: dict[str, Any] = json.loads(_unb64(body))
    except (ValueError, json.JSONDecodeError):
        return None
    if data.pop("_exp", 0) < time.time():
        return None
    return data
