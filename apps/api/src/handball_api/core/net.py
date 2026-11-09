"""Outbound URL safety for link imports (SSRF protection), shared with the import worker."""

from handball_jobkit.net import UnsafeUrlError, check_public_https_url

__all__ = ["UnsafeUrlError", "check_public_https_url"]
