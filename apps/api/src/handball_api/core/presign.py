"""Presigned S3 GET URLs (AWS Signature V4, query string), many at once.

A variant playlist of a full match lists over a thousand segments; boto3 needs about 0.3 ms per
URL, this signer derives the signing key once and needs one HMAC per URL. The signing time is
rounded down to a window, so the same segment gets the same URL for the whole window: the
browser cache and a later CDN see stable URLs across playlist reloads (ADR 002 point 7).
Equivalence with boto3 is tested (tests/test_media_direct.py).
"""

from __future__ import annotations

import hashlib
import hmac
from datetime import UTC, datetime
from urllib.parse import quote, urlsplit

MAX_EXPIRES_S = 7 * 24 * 3600  # SigV4 limit


def _q(value: str, safe: str = "-_.~") -> str:
    return quote(value, safe=safe)


class GetSigner:
    def __init__(
        self,
        endpoint: str,
        region: str,
        access_key: str,
        secret_key: str,
        now: datetime,
        expires_s: int,
    ) -> None:
        parts = urlsplit(endpoint)
        if parts.scheme not in ("http", "https") or not parts.netloc:
            raise ValueError(f"not an endpoint URL: {endpoint}")
        self._base = f"{parts.scheme}://{parts.netloc}{parts.path.rstrip('/')}"
        self._path = parts.path.rstrip("/")
        self._host = parts.netloc
        self._expires = min(max(1, expires_s), MAX_EXPIRES_S)
        self._amz_date = now.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")
        day = self._amz_date[:8]
        self._scope = f"{day}/{region}/s3/aws4_request"
        self._credential = f"{access_key}/{self._scope}"
        key = f"AWS4{secret_key}".encode()
        for part in (day, region, "s3", "aws4_request"):
            key = hmac.new(key, part.encode(), hashlib.sha256).digest()
        self._key = key

    def url(self, bucket: str, key: str, extra: dict[str, str] | None = None) -> str:
        path = f"{self._path}/{_q(bucket)}/{_q(key, safe='-_.~/')}"
        params = {
            "X-Amz-Algorithm": "AWS4-HMAC-SHA256",
            "X-Amz-Credential": self._credential,
            "X-Amz-Date": self._amz_date,
            "X-Amz-Expires": str(self._expires),
            "X-Amz-SignedHeaders": "host",
            **(extra or {}),
        }
        query = "&".join(f"{_q(k)}={_q(v)}" for k, v in sorted(params.items()))
        canonical = f"GET\n{path}\n{query}\nhost:{self._host}\n\nhost\nUNSIGNED-PAYLOAD"
        to_sign = (
            f"AWS4-HMAC-SHA256\n{self._amz_date}\n{self._scope}\n"
            + hashlib.sha256(canonical.encode()).hexdigest()
        )
        sig = hmac.new(self._key, to_sign.encode(), hashlib.sha256).hexdigest()
        return f"{self._base}/{_q(bucket)}/{_q(key, safe='-_.~/')}?{query}&X-Amz-Signature={sig}"


def window_start(now: datetime, window_s: int) -> datetime:
    """`now` rounded down to the signing window."""
    ts = int(now.timestamp())
    return datetime.fromtimestamp(ts - ts % max(1, window_s), UTC)
