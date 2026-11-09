"""Downloads of official reports: fixed hosts, timeouts, size limits, PDF to text."""

from __future__ import annotations

import asyncio
import contextlib
import tempfile
from collections.abc import Awaitable, Callable
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import httpx

from handball_api.core.errors import ProblemError

TIMEOUT = httpx.Timeout(15.0, connect=5.0)
HEADERS = {"User-Agent": "handball-ai/1.0 (official match report import)", "Accept-Language": "de"}
MAX_PDF_BYTES = 5_000_000
PDFTOTEXT_TIMEOUT_S = 20.0

MAX_HTML_BYTES = 2_000_000
MAX_REDIRECTS = 3

PdfText = Callable[[bytes], Awaitable[str]]


async def pdf_text(pdf: bytes) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "report.pdf"
        path.write_bytes(pdf)
        try:
            proc = await asyncio.create_subprocess_exec(
                "pdftotext",
                "-layout",
                "-enc",
                "UTF-8",
                str(path),
                "-",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
        except FileNotFoundError as exc:
            raise ProblemError(
                503, "report-unavailable", "Reading PDF reports is not set up (pdftotext)"
            ) from exc
        try:
            out, _ = await asyncio.wait_for(proc.communicate(), PDFTOTEXT_TIMEOUT_S)
        except TimeoutError as exc:
            with contextlib.suppress(ProcessLookupError):
                proc.kill()
            raise ProblemError(422, "report-unreadable", "The PDF could not be read") from exc
    if proc.returncode != 0:
        raise ProblemError(422, "report-unreadable", "The PDF could not be read")
    return out.decode("utf-8", errors="replace")


def _origin(url: str) -> tuple[str, str | None, int] | None:
    """Scheme, host and effective port of an https URL (None for anything else or a bad port)."""
    parts = urlsplit(url)
    if parts.scheme != "https":
        return None
    try:
        port = parts.port or 443
    except ValueError:
        return None
    return parts.scheme, parts.hostname, port


async def download(url: str, max_bytes: int, what: str) -> bytes:
    """One GET with timeouts and a size limit; redirects are followed on the same host and port
    only (https)."""
    origin = _origin(url)
    try:
        async with httpx.AsyncClient(
            timeout=TIMEOUT, headers=HEADERS, follow_redirects=False
        ) as client:
            for _ in range(MAX_REDIRECTS + 1):
                async with client.stream("GET", url) as r:
                    if r.is_redirect:
                        target = urljoin(url, r.headers.get("location", ""))
                        if origin is None or _origin(target) != origin:
                            raise ProblemError(
                                502, "report-unavailable", f"{what} sent the report elsewhere"
                            )
                        url = target
                        continue
                    if r.status_code == 404:
                        raise ProblemError(404, "report-not-found", f"{what} has no such report")
                    r.raise_for_status()
                    body = bytearray()
                    async for chunk in r.aiter_bytes():
                        body += chunk
                        if len(body) > max_bytes:
                            raise ProblemError(422, "report-unreadable", "The report is too large")
                    return bytes(body)
    except httpx.HTTPError as exc:
        raise ProblemError(
            502, "report-unavailable", f"{what} did not answer, try again later"
        ) from exc
    raise ProblemError(502, "report-unavailable", f"{what} redirected too often")
