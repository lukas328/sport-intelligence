from __future__ import annotations

import json

import httpx

from handball_worker.push import EXPO_URL, messages, send


def test_push_batches_and_tickets() -> None:
    tokens = [f"ExponentPushToken[{i}]" for i in range(130)]
    seen: list[list[dict[str, object]]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == EXPO_URL
        batch = json.loads(request.content)
        seen.append(batch)
        tickets = [
            {"status": "ok"}
            if i % 10
            else {"status": "error", "details": {"error": "DeviceNotRegistered"}}
            for i in range(len(batch))
        ]
        return httpx.Response(200, json={"data": tickets})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    result = send({"tokens": tokens, "body": "Neue Aufgabe", "data": {"link": "/app/x"}}, client)
    assert [len(b) for b in seen] == [100, 30]
    assert result == {"sent": 130 - 13, "failed": 13}
    assert messages({"tokens": ["t"], "body": "b"})[0] == {
        "to": "t",
        "title": "Handball Intelligence",
        "body": "b",
        "data": {},
        "sound": "default",
    }


def test_push_service_down() -> None:
    client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(503)))
    assert send({"tokens": ["a", "b"], "body": "x"}, client) == {"sent": 0, "failed": 2}
