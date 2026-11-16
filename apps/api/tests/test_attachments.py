"""Files kept with a match (K19) and videos of an opponent against another team (K3)."""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

import pytest

from handball_api.core.storage import MemoryStorage
from handball_api.services.attachments import clean_name, sniff

from .conftest import Api, setup_club
from .test_matches import new_match, upload
from .test_video_parts import _jobs

pytestmark = pytest.mark.usefixtures("clean_db")

PDF = b"%PDF-1.7\n" + b"0" * 200
JPEG = b"\xff\xd8\xff\xe0" + b"1" * 200


async def _attach(
    api: Api, org: str, match_id: str, data: bytes, ctype: str, name: str = "bericht.pdf"
) -> tuple[int, dict[str, Any]]:
    storage: MemoryStorage = api.app.state.storage
    r = await api.post(
        f"/v1/orgs/{org}/matches/{match_id}/attachments",
        json={"filename": name, "content_type": ctype, "size_bytes": len(data), "note": "Papier"},
    )
    if r.status_code != 201:
        return r.status_code, r.json()
    up = r.json()
    upload_id = re.search(r"uploadId=(\w+)", up["upload_url"]).group(1)  # type: ignore[union-attr]
    etag = storage.upload_part(upload_id, 1, data)
    done = await api.post(
        f"/v1/orgs/{org}/attachments/{up['attachment']['id']}/complete", json={"etag": etag}
    )
    return done.status_code, done.json()


def test_sniff_and_names() -> None:
    assert sniff(PDF) == "application/pdf" and sniff(JPEG) == "image/jpeg"
    assert sniff(b"\x89PNG\r\n\x1a\n....") == "image/png"
    assert sniff(b"\x00\x00\x00\x18ftypheic....") == "image/heic"
    assert sniff(b"<svg onload=alert(1)>") is None and sniff(b"<html>") is None
    assert clean_name("../../etc/passwd") == "etc_passwd"
    assert clean_name("Matchblatt 3.Liga.pdf") == "Matchblatt 3.Liga.pdf"


async def test_attach_list_open_note_and_delete(make_api: Callable[[], Api]) -> None:
    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    m = await new_match(api, ids)
    status, body = await _attach(api, org, m["id"], PDF, "application/pdf")
    assert status == 200, body
    assert body["status"] == "ready" and body["note"] == "Papier" and body["is_image"] is False
    assert body["created_by"] == "Coach Carter"
    status, photo = await _attach(api, org, m["id"], JPEG, "image/jpeg", name="foto.jpg")
    assert status == 200 and photo["is_image"]
    listed = (await api.get(f"/v1/orgs/{org}/matches/{m['id']}/attachments")).json()
    assert [a["filename"] for a in listed] == ["foto.jpg", "bericht.pdf"]

    pdf = await api.get(f"/v1/orgs/{org}/attachments/{body['id']}/file")
    assert pdf.status_code == 200 and pdf.content == PDF
    assert pdf.headers["content-disposition"].startswith("attachment")
    assert pdf.headers["x-content-type-options"] == "nosniff"
    img = await api.get(f"/v1/orgs/{org}/attachments/{photo['id']}/file")
    assert img.headers["content-disposition"].startswith("inline")
    assert "sandbox" in img.headers["content-security-policy"]

    r = await api.patch(f"/v1/orgs/{org}/attachments/{body['id']}", json={"note": " "})
    assert r.status_code == 200 and r.json()["note"] is None
    assert (await api.delete(f"/v1/orgs/{org}/attachments/{body['id']}")).status_code == 204
    listed = (await api.get(f"/v1/orgs/{org}/matches/{m['id']}/attachments")).json()
    assert [a["id"] for a in listed] == [photo["id"]]


async def test_only_photos_and_pdfs_up_to_the_limit(make_api: Callable[[], Api]) -> None:
    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    m = await new_match(api, ids)
    status, _ = await _attach(api, org, m["id"], b"<html>x</html>", "text/html", "x.html")
    assert status == 415
    # said to be a PDF, but is a page: refused at completion, nothing kept
    status, _ = await _attach(api, org, m["id"], b"<html>" + b"0" * 50, "application/pdf")
    assert status == 415
    assert (await api.get(f"/v1/orgs/{org}/matches/{m['id']}/attachments")).json() == []
    r = await api.post(
        f"/v1/orgs/{org}/matches/{m['id']}/attachments",
        json={"filename": "x.pdf", "content_type": "application/pdf", "size_bytes": 26 * 1024**2},
    )
    assert r.status_code == 413


async def test_attachments_stay_in_their_club(make_api: Callable[[], Api]) -> None:
    api = make_api()
    ids = await setup_club(api)
    m = await new_match(api, ids)
    _, body = await _attach(api, ids["org"], m["id"], PDF, "application/pdf")
    other = make_api()
    mine = await setup_club(other, email="other@hc-else.ch")
    r = await other.get(f"/v1/orgs/{mine['org']}/attachments/{body['id']}/file")
    assert r.status_code == 404
    r = await other.get(f"/v1/orgs/{ids['org']}/attachments/{body['id']}/file")
    assert r.status_code in (403, 404)


async def test_scouting_video_stays_out_of_the_own_season(make_api: Callable[[], Api]) -> None:
    """K3: a video of the opponent against another team. Its kits go to the analysis (the other
    team on the own side), our roster is not used, the match is not listed with the team's
    matches by default, and it adds to what we know about the opponent."""
    api = make_api()
    ids = await setup_club(api)
    org = ids["org"]
    await api.put(
        f"/v1/orgs/{org}/teams/{ids['team']}/seasons/{ids['season']}/roster",
        json=[{"first_name": "Lea", "last_name": "Muster", "jersey_number": 7}],
    )
    ours = await new_match(api, ids)
    r = await api.post(
        f"/v1/orgs/{org}/teams/{ids['team']}/matches",
        json={"opponent_name": "TV Gegner", "kickoff_at": "2026-11-01T18:00:00+01:00"},
    )
    bad = await api.post(
        f"/v1/orgs/{org}/teams/{ids['team']}/matches",
        json={
            "kind": "scouting",
            "opponent_name": "TV Gegner",
            "kickoff_at": "2026-11-01T18:00:00+01:00",
        },
    )
    assert bad.status_code == 422  # the other team is needed
    r = await api.post(
        f"/v1/orgs/{org}/teams/{ids['team']}/matches",
        json={
            "kind": "scouting",
            "opponent_name": "TV Gegner",
            "scouting_other": "HC Dritte",
            "kickoff_at": "2026-11-01T18:00:00+01:00",
            "kit_own": "#ffffff",
            "kit_opponent": "#ff0000",
        },
    )
    assert r.status_code == 201, r.text
    scout = r.json()
    assert scout["kind"] == "scouting" and scout["scouting_other"] == "HC Dritte"
    assert scout["opponent"]["id"] == ours["opponent"]["id"]
    assert scout["kit_own"] == "#ffffff"  # not the club colour: the other team's shirt

    team_matches = (await api.get(f"/v1/orgs/{org}/teams/{ids['team']}/matches")).json()
    assert scout["id"] not in [x["id"] for x in team_matches]
    listed = (
        await api.get(f"/v1/orgs/{org}/teams/{ids['team']}/matches", params={"scouting": True})
    ).json()
    row = next(x for x in listed if x["id"] == scout["id"])
    assert row["scouting_other"] == "HC Dritte"

    video = await upload(api, ids, scout["id"], b"v" * 100)
    from .test_video_parts import HALF, _ingest

    await _ingest(api, video["id"], HALF)
    payload = [j for j in _jobs(api).jobs if j[1].endswith("run_analysis")][-1][3]
    assert payload["kits"]["home"] == "#ffffff" and payload["kits"]["away"] == "#ff0000"
    assert "home" not in payload.get("rosters", {})  # never our players

    profile = await api.get(f"/v1/orgs/{org}/opponents/{scout['opponent']['id']}/profile")
    if profile.status_code == 200:  # the plan may not include the season figures
        kinds = {x["match_id"]: x["kind"] for x in profile.json()["matches"]}
        assert kinds[scout["id"]] == "scouting"
        assert sum(profile.json()["record"].values()) == 0  # no result of ours from it
