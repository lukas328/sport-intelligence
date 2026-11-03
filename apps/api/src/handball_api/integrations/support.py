"""Support chat and status page (addendum 01, 4.11/4.12): external providers, see ADR 018."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ChatWidget:
    provider: str
    config: dict[str, str]


class SupportChatAdapter(Protocol):
    name: str

    def widget(self, locale: str, user_hash: str | None) -> ChatWidget | None: ...


class CrispChat:
    """Crisp (EU hosting, GDPR DPA). Only a pseudonymous user hash is passed, no e-mail."""

    name = "crisp"

    def __init__(self, website_id: str) -> None:
        self.website_id = website_id

    def widget(self, locale: str, user_hash: str | None) -> ChatWidget | None:
        cfg = {"website_id": self.website_id, "locale": locale.split("-")[0]}
        if user_hash:
            cfg["token_id"] = user_hash
        return ChatWidget(provider=self.name, config=cfg)


class NoSupportChat:
    name = "none"

    def widget(self, locale: str, user_hash: str | None) -> ChatWidget | None:
        return None


@dataclass(frozen=True)
class ComponentStatus:
    component: str
    status: str  # operational | degraded | down


class StatusPageAdapter(Protocol):
    name: str

    def public_url(self) -> str | None: ...
    def report(self, checks: dict[str, bool]) -> list[ComponentStatus]: ...


class ExternalStatusPage:
    """Status page at an external provider (independent of our hosting); we push component state."""

    name = "external"

    def __init__(self, url: str) -> None:
        self.url = url

    def public_url(self) -> str | None:
        return self.url

    def report(self, checks: dict[str, bool]) -> list[ComponentStatus]:
        critical = {"database", "storage"}
        out = []
        for name, ok in sorted(checks.items()):
            status = "operational" if ok else ("down" if name in critical else "degraded")
            out.append(ComponentStatus(component=name, status=status))
        return out


class NoStatusPage:
    name = "none"

    def public_url(self) -> str | None:
        return None

    def report(self, checks: dict[str, bool]) -> list[ComponentStatus]:
        return []
