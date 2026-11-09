"""SSRF check shared by the API (link import) and the import worker."""

from __future__ import annotations

import socket
from typing import Any

import pytest

from handball_jobkit.net import UnsafeUrlError, check_public_https_url


def resolves_to(monkeypatch: pytest.MonkeyPatch, *ips: str) -> None:
    infos = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 443)) for ip in ips]
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: infos)


@pytest.mark.parametrize(
    ("url", "reason"),
    [
        ("http://videos.example/a.mp4", "https"),
        ("ftp://videos.example/a.mp4", "https"),
        ("https:///a.mp4", "invalid host"),
        ("https://user@videos.example/a.mp4", "invalid host"),
        ("https://user:pw@videos.example/a.mp4", "invalid host"),
        ("https://videos.example:8443/a.mp4", "port"),
    ],
)
def test_rejects_unsafe_urls_without_lookup(url: str, reason: str) -> None:
    with pytest.raises(UnsafeUrlError, match=reason):
        check_public_https_url(url, resolve=False)


@pytest.mark.parametrize(
    "ip", ["10.0.0.1", "127.0.0.1", "169.254.169.254", "192.168.1.5", "224.0.0.251", "::1"]
)
def test_rejects_private_and_multicast_addresses(monkeypatch: pytest.MonkeyPatch, ip: str) -> None:
    resolves_to(monkeypatch, "93.184.216.34", ip)  # one bad address is enough
    with pytest.raises(UnsafeUrlError, match="private"):
        check_public_https_url("https://videos.example/a.mp4")


def test_unresolvable_host(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(*a: Any, **k: Any) -> Any:
        raise socket.gaierror("Name or service not known")

    monkeypatch.setattr(socket, "getaddrinfo", fail)
    with pytest.raises(UnsafeUrlError, match="does not resolve"):
        check_public_https_url("https://nowhere.example/a.mp4")


def test_accepts_public_https(monkeypatch: pytest.MonkeyPatch) -> None:
    resolves_to(monkeypatch, "93.184.216.34")
    url = "https://videos.example:443/a.mp4?x=1"
    assert check_public_https_url(url) == url
    assert check_public_https_url("https://videos.example/a.mp4", resolve=False)
