"""E-mail port: SMTP (mailpit locally, provider in production), memory, console."""

from __future__ import annotations

from dataclasses import dataclass, field
from email.message import EmailMessage
from typing import Protocol

import aiosmtplib

from handball_api.core.logging import get_logger


@dataclass(frozen=True, slots=True)
class Email:
    to: str
    subject: str
    text: str
    html: str | None = None


class EmailSender(Protocol):
    async def send(self, email: Email) -> None: ...


@dataclass
class MemoryEmailSender:
    outbox: list[Email] = field(default_factory=list)

    async def send(self, email: Email) -> None:
        self.outbox.append(email)


class ConsoleEmailSender:
    async def send(self, email: Email) -> None:
        get_logger("email").info("email", to=email.to, subject=email.subject, text=email.text)


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
        await aiosmtplib.send(
            msg,
            hostname=self.host,
            port=self.port,
            username=self.username,
            password=self.password,
            start_tls=self.starttls,
            timeout=10,
        )
