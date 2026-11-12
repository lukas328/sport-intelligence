from __future__ import annotations

import json
from pathlib import Path

from httpx import AsyncClient

from handball_api.openapi import main as export_main


async def test_openapi_is_versioned(client: AsyncClient) -> None:
    r = await client.get("/v1/openapi.json")
    assert r.status_code == 200
    paths = r.json()["paths"]
    assert "/v1/health" in paths
    assert "/healthz" in paths


def test_openapi_export(tmp_path: Path, monkeypatch: object) -> None:
    import sys

    out = tmp_path / "openapi.json"
    sys_argv = sys.argv
    sys.argv = ["x", str(out)]
    try:
        export_main()
    finally:
        sys.argv = sys_argv
    assert json.loads(out.read_text())["info"]["title"] == "Handball Intelligence API"
