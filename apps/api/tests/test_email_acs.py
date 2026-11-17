"""Mail through Azure Communication Services: the signed REST call (no network)."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json

import httpx
import pytest

from handball_api.core.config import Settings
from handball_api.core.email import AcsEmailSender, Email, try_send
from handball_api.main import _email_sender

KEY = base64.b64encode(b"secret-access-key").decode()
CONN = f"endpoint=https://hb-stg-acs.switzerland.communication.azure.com/;accesskey={KEY}"


def _check_signature(request: httpx.Request) -> None:
    """The HMAC scheme of Azure Communication Services, computed independently."""
    body = request.content
    digest = base64.b64encode(hashlib.sha256(body).digest()).decode()
    assert request.headers["x-ms-content-sha256"] == digest
    path = request.url.raw_path.decode()
    to_sign = f"POST\n{path}\n{request.headers['x-ms-date']};{request.url.host};{digest}"
    sig = base64.b64encode(
        hmac.new(b"secret-access-key", to_sign.encode(), hashlib.sha256).digest()
    ).decode()
    assert request.headers["Authorization"] == (
        f"HMAC-SHA256 SignedHeaders=x-ms-date;host;x-ms-content-sha256&Signature={sig}"
    )


async def test_a_mail_is_sent_signed_with_text_html_and_attachment() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(202, json={"id": "op-1", "status": "Running"})

    sender = AcsEmailSender(
        CONN,
        "Handball Intelligence <noreply@handball-intelligence.com>",
        httpx.MockTransport(handler),
    )
    mail = Email(
        to="coach@example.ch",
        subject="Analyse fertig",
        text="Hallo",
        html="<p>Hallo</p>",
        attachments=(("bericht.pdf", "application/pdf", b"%PDF"),),
    )
    await sender.send(mail)
    (req,) = seen
    assert str(req.url) == (
        "https://hb-stg-acs.switzerland.communication.azure.com/emails:send?api-version=2023-03-31"
    )
    _check_signature(req)
    body = json.loads(req.content)
    assert body["senderAddress"] == "noreply@handball-intelligence.com"
    assert body["recipients"] == {"to": [{"address": "coach@example.ch"}]}
    assert body["content"] == {
        "subject": "Analyse fertig",
        "plainText": "Hallo",
        "html": "<p>Hallo</p>",
    }
    assert body["attachments"] == [
        {"name": "bericht.pdf", "contentType": "application/pdf", "contentInBase64": "JVBERg=="}
    ]
    assert body["userEngagementTrackingDisabled"] is True


async def test_a_refused_mail_raises_without_the_provider_message() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error": {"message": "coach@example.ch is invalid"}})

    sender = AcsEmailSender(CONN, "noreply@handball-intelligence.com", httpx.MockTransport(handler))
    mail = Email(to="coach@example.ch", subject="s", text="t")
    with pytest.raises(RuntimeError) as err:
        await sender.send(mail)
    assert "example.ch" not in str(err.value)
    assert await try_send(sender, mail, "test") is False


def test_the_backend_needs_a_connection_string() -> None:
    with pytest.raises(ValueError):
        AcsEmailSender("endpoint=https://x.communication.azure.com/", "a@b.ch")
    with pytest.raises(RuntimeError):
        _email_sender(Settings(email_backend="acs"))
    sender = _email_sender(Settings(email_backend="acs", acs_connection_string=CONN))
    assert isinstance(sender, AcsEmailSender)
    assert sender.endpoint == "https://hb-stg-acs.switzerland.communication.azure.com"
