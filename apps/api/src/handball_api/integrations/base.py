from __future__ import annotations


class AdapterError(Exception):
    """Input could not be read or the partner answered with an error."""


class NotConfiguredError(AdapterError):
    """A stub: the partner connection needs a contract and credentials first."""

    def __init__(self, partner: str) -> None:
        super().__init__(f"{partner} is not connected yet (needs a partnership and credentials)")
        self.partner = partner


class Stub:
    """Base for partner stubs: every call raises NotConfiguredError."""

    partner = "partner"

    def _missing(self) -> NotConfiguredError:
        return NotConfiguredError(self.partner)
