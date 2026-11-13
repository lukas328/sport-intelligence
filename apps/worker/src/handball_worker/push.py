"""Sends push notifications through the Expo push service (addendum 01, 5.5).

Expo forwards to APNs (iOS) and FCM (Android). At most 100 messages per request; tokens the
service reports as unregistered are logged so the API can drop them later.
"""

from __future__ import annotations

from typing import Any

import httpx
import structlog

from handball_worker.config import WorkerSettings

log = structlog.get_logger("worker.push")
EXPO_URL = "https://exp.host/--/api/v2/push/send"
BATCH = 100


def messages(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "to": token,
            "title": payload.get("title") or "Handball Intelligence",
            "body": payload["body"],
            "data": payload.get("data") or {},
            "sound": "default",
        }
        for token in payload.get("tokens") or []
    ]


def send(payload: dict[str, Any], client: httpx.Client | None = None) -> dict[str, int]:
    settings = WorkerSettings()
    msgs = messages(payload)
    own = client is None
    http = client or httpx.Client(timeout=15)
    sent = failed = 0
    headers = {"accept": "application/json", "content-type": "application/json"}
    if settings.expo_access_token:
        headers["authorization"] = f"Bearer {settings.expo_access_token}"
    try:
        for i in range(0, len(msgs), BATCH):
            batch = msgs[i : i + BATCH]
            r = http.post(EXPO_URL, json=batch, headers=headers)
            if r.status_code >= 400:
                log.warning("push_failed", status=r.status_code)
                failed += len(batch)
                continue
            for ticket in r.json().get("data") or []:
                if ticket.get("status") == "ok":
                    sent += 1
                else:
                    failed += 1
                    log.info("push_ticket_error", error=(ticket.get("details") or {}).get("error"))
    finally:
        if own:
            http.close()
    return {"sent": sent, "failed": failed}
