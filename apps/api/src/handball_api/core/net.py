"""Outbound URL safety for link imports (SSRF protection)."""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlsplit


class UnsafeUrlError(ValueError):
    pass


def check_public_https_url(url: str, resolve: bool = True) -> str:
    parts = urlsplit(url)
    if parts.scheme != "https":
        raise UnsafeUrlError("only https links are supported")
    if not parts.hostname or parts.username or parts.password:
        raise UnsafeUrlError("invalid host")
    if parts.port not in (None, 443):
        raise UnsafeUrlError("only the default https port is allowed")
    if resolve:
        try:
            infos = socket.getaddrinfo(parts.hostname, 443, proto=socket.IPPROTO_TCP)
        except socket.gaierror as exc:
            raise UnsafeUrlError("host does not resolve") from exc
        for info in infos:
            ip = ipaddress.ip_address(info[4][0])
            if not ip.is_global or ip.is_multicast:
                raise UnsafeUrlError("host resolves to a private address")
    return url
