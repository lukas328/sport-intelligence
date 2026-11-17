"""E-mail port: SMTP (mailpit locally), Azure Communication Services (production), memory,
console."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from dataclasses import dataclass, field
from email.message import EmailMessage
from email.utils import formatdate, parseaddr
from typing import Any, Protocol
from urllib.parse import urlsplit

import aiosmtplib
import httpx

from handball_api.core.logging import get_logger


@dataclass(frozen=True, slots=True)
class Email:
    to: str
    subject: str
    text: str
    html: str | None = None
    attachments: tuple[tuple[str, str, bytes], ...] = ()  # (filename, mime type, content)
    # the template the mail was rendered from (logged without the text by the console backend)
    template: str | None = None


class EmailSender(Protocol):
    async def send(self, email: Email) -> None: ...


async def try_send(sender: EmailSender, email: Email, purpose: str, **fields: object) -> bool:
    """Send, but never let a provider failure undo the action that triggered the mail.

    Logs the failure without the recipient address or the provider message (SMTP errors often
    echo the address); `fields` carries ids only. Returns whether the mail went out.
    """
    try:
        await sender.send(email)
    except Exception as exc:
        get_logger("email").error(
            "email_send_failed", purpose=purpose, error=type(exc).__name__, **fields
        )
        return False
    return True


@dataclass
class MemoryEmailSender:
    outbox: list[Email] = field(default_factory=list)

    async def send(self, email: Email) -> None:
        self.outbox.append(email)


class ConsoleEmailSender:
    """Writes mails to the log instead of sending them.

    Mails carry sign-in, reset and invitation links: only in local development (`full`) does the
    log get the whole text; anywhere else it gets the recipient's domain, the subject and the
    template, never the address or a link (L10).
    """

    def __init__(self, full: bool = False) -> None:
        self.full = full

    async def send(self, email: Email) -> None:
        if self.full:
            get_logger("email").info("email", to=email.to, subject=email.subject, text=email.text)
            return
        get_logger("email").info(
            "email_not_sent",
            to_domain=email.to.rsplit("@", 1)[-1].lower(),
            subject=email.subject,
            template=email.template,
        )


class SmtpEmailSender:
    def __init__(
        self,
        host: str,
        port: int,
        sender: str,
        username: str | None = None,
        password: str | None = None,
        starttls: bool = False,
    ) -> None:
        self.host, self.port, self.sender = host, port, sender
        self.username, self.password, self.starttls = username, password, starttls

    async def send(self, email: Email) -> None:
        msg = EmailMessage()
        msg["From"] = self.sender
        msg["To"] = email.to
        msg["Subject"] = email.subject
        msg.set_content(email.text)
        if email.html:
            msg.add_alternative(email.html, subtype="html")
        for name, mime, content in email.attachments:
            maintype, subtype = mime.split("/", 1)
            msg.add_attachment(content, maintype=maintype, subtype=subtype, filename=name)
        await aiosmtplib.send(
            msg,
            hostname=self.host,
            port=self.port,
            username=self.username,
            password=self.password,
            start_tls=self.starttls,
            timeout=10,
        )


class AcsEmailSender:
    """Azure Communication Services Email over its REST API, signed with the resource's access
    key (HMAC-SHA256): no SMTP user and no app registration needed. The display name of the
    sender is set on its sender username in Azure; here only the address is sent."""

    API_VERSION = "2023-03-31"

    def __init__(
        self,
        connection_string: str,
        sender: str,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        parts = dict(
            item.split("=", 1) for item in connection_string.strip().strip(";").split(";") if item
        )
        fields = {k.lower(): v for k, v in parts.items()}
        endpoint, key = fields.get("endpoint"), fields.get("accesskey")
        if not endpoint or not key:
            raise ValueError("the connection string needs endpoint and accesskey")
        self.endpoint = endpoint.rstrip("/")
        self.key = base64.b64decode(key)
        self.sender = parseaddr(sender)[1] or sender
        self.transport = transport

    def _body(self, email: Email) -> dict[str, Any]:
        content: dict[str, str] = {"subject": email.subject, "plainText": email.text}
        if email.html:
            content["html"] = email.html
        body: dict[str, Any] = {
            "senderAddress": self.sender,
            "content": content,
            "recipients": {"to": [{"address": email.to}]},
            "userEngagementTrackingDisabled": True,
        }
        if email.attachments:
            body["attachments"] = [
                {
                    "name": name,
                    "contentType": mime,
                    "contentInBase64": base64.b64encode(data).decode(),
                }
                for name, mime, data in email.attachments
            ]
        return body

    def signed_headers(self, path_and_query: str, content: bytes) -> dict[str, str]:
        host = urlsplit(self.endpoint).netloc
        date = formatdate(usegmt=True)
        digest = base64.b64encode(hashlib.sha256(content).digest()).decode()
        to_sign = f"POST\n{path_and_query}\n{date};{host};{digest}"
        signature = base64.b64encode(
            hmac.new(self.key, to_sign.encode(), hashlib.sha256).digest()
        ).decode()
        return {
            "x-ms-date": date,
            "x-ms-content-sha256": digest,
            "Authorization": "HMAC-SHA256 SignedHeaders=x-ms-date;host;x-ms-content-sha256"
            f"&Signature={signature}",
            "Content-Type": "application/json",
        }

    async def send(self, email: Email) -> None:
        path = f"/emails:send?api-version={self.API_VERSION}"
        content = json.dumps(self._body(email)).encode()
        async with httpx.AsyncClient(transport=self.transport, timeout=10) as client:
            res = await client.post(
                self.endpoint + path, content=content, headers=self.signed_headers(path, content)
            )
        if res.status_code >= 300:
            # the provider message can echo the address: only the status goes up (try_send logs
            # the exception type)
            raise RuntimeError(f"Azure Communication Services answered {res.status_code}")
