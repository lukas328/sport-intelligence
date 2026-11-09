"""Statistics matrix, CSV/Excel export, Sportscode XML export and import (addendum 01, 5.4)."""

from __future__ import annotations

import csv
import io
import json
from collections import Counter
from collections.abc import Callable

import asyncpg
import pytest
from defusedxml import ElementTree as SafeET
from openpyxl import load_workbook

from .assistant_eval import MATCHES
from .conftest import Api, setup_club
from .test_assistant import seed
from .test_matches import new_match, upload
from .test_official_report import recorded, reported_clip  # noqa: F401

pytestmark = pytest.mark.usefixtures("clean_db")


def instances(xml: bytes) -> Counter[tuple[str, str, str, tuple[tuple[str, str], ...]]]:
    root = SafeET.fromstring(xml)
    out: Counter[tuple[str, str, str, tuple[tuple[str, str], ...]]] = Counter()
    for el in root.iter("instance"):
        labels = tuple(
            sorted(
                (lab.findtext("group") or "", lab.findtext("text") or "")
                for lab in el.findall("label")
            )
        )
        out[
            (
                el.findtext("start") or "",
                el.findtext("end") or "",
                el.findtext("code") or "",
                labels,
            )
        ] += 1
    return out


async def test_matrix_templates_and_exports(
    make_api: Callable[[], Api], owner_conn: asyncpg.Connection
) -> None:
    api = make_api()
    ids = await seed(api, owner_conn)
    org, team = ids["org"], ids["team"]
    url = f"/v1/orgs/{org}/teams/{team}/matrix"
    spec = {"rows": "number", "metrics": ["goals", "shooting_pct"], "filter": {"side": "own"}}
    out = (await api.post(url, json=spec)).json()
    expected: Counter[int] = Counter(
        e["number"]
        for m in MATCHES
        for e in m.events
        if e["side"] == "own" and e["type"] == "shot" and e["outcome"] == "goal"
    )
    got = {r["label"]: r["cells"]["goals"]["value"] for r in out["rows"]}
    assert got == {f"#{n}": float(c) for n, c in expected.items()}
    assert out["totals"]["cells"]["goals"]["value"] == sum(expected.values())
    # sorted by the first column; every clip has a video time; ratios list their shots
    values = [r["cells"]["goals"]["value"] for r in out["rows"]]
    assert values == sorted(values, reverse=True)
    cell = out["rows"][0]["cells"]["shooting_pct"]
    assert cell["denominator"] == len(cell["event_ids"]) and cell["clips"]
    assert all(c["t_ms"] is not None for c in cell["clips"])

    plays = (await api.post(url, json={"rows": "play", "metrics": ["shots"], "filter": {}})).json()
    assert {r["label"] for r in plays["rows"]} == {"Kreuzung links", "Stoss Mitte"}
    halves = (
        await api.post(
            url, json={"rows": "period", "metrics": ["goals"], "filter": {"side": "opponent"}}
        )
    ).json()
    assert (
        sum(r["cells"]["goals"]["value"] for r in halves["rows"])
        == halves["totals"]["cells"]["goals"]["value"]
    )
    assert (await api.post(url, json={"rows": "shoe", "metrics": ["goals"]})).status_code == 422
    assert (await api.post(url, json={"rows": "match", "metrics": ["luck"]})).status_code == 422
    assert (
        await api.post(url, json={"rows": "match", "metrics": ["goals"], "filter": {"x": 1}})
    ).status_code == 422

    # templates
    turl = f"{url}/templates"
    t = await api.post(turl, json={"name": "Werfer", "config": spec})
    assert t.status_code == 201
    assert (await api.post(turl, json={"name": "Werfer", "config": spec})).status_code == 409
    assert [x["name"] for x in (await api.get(turl)).json()] == ["Werfer"]
    assert (
        await api.delete(f"/v1/orgs/{org}/matrix/templates/{t.json()['id']}")
    ).status_code == 204
    assert (await api.get(turl)).json() == []

    # CSV and Excel; a formula-like label is neutralised
    await owner_conn.execute("UPDATE opponents SET name = '=HYPERLINK(1)' WHERE name = 'TSV Test'")
    by_match = {"rows": "match", "metrics": ["goals", "shooting_pct"], "filter": {"side": "own"}}
    r = await api.post(f"{url}/export?format=csv", json=by_match)
    assert r.status_code == 200 and "attachment" in r.headers["content-disposition"]
    table = list(csv.reader(io.StringIO(r.content.decode("utf-8-sig")), delimiter=";"))
    assert table[0] == ["match", "goals", "shooting_pct (%)"] and table[-1][0] == "total"
    assert len(table) == len(MATCHES) + 2
    assert all(not row[0].startswith("=") for row in table)
    r = await api.post(f"{url}/export?format=xlsx", json=by_match)
    ws = load_workbook(io.BytesIO(r.content)).active
    assert ws is not None
    rows = list(ws.iter_rows(values_only=True))
    assert rows[0] == ("match", "goals", "shooting_pct (%)") and rows[-1][0] == "total"


async def test_matrix_reads_the_requested_seasons_only(
    make_api: Callable[[], Api], owner_conn: asyncpg.Connection, query_counter: list[str]
) -> None:
    """By default the current and the previous season, else the seasons asked for; only the
    columns the statistics use (not every event and video analysis of all seasons)."""
    api = make_api()
    ids = await seed(api, owner_conn)
    org, team = ids["org"], ids["team"]
    url = f"/v1/orgs/{org}/teams/{team}/matrix"
    spec = {"rows": "match", "metrics": ["goals"], "filter": {"side": "own"}}
    everything = (await api.post(url, json=spec)).json()
    total = everything["totals"]["cells"]["goals"]["value"]
    goals = {r["key"]: r["cells"]["goals"]["value"] for r in everything["rows"]}
    seasons = {}
    for label, start, end in (
        ("2025/26", "2025-07-01", "2026-06-30"),
        ("2019/20", "2019-07-01", "2020-06-30"),
    ):
        r = await api.post(
            f"/v1/orgs/{org}/teams/{team}/seasons",
            json={"label": label, "starts_on": start, "ends_on": end},
        )
        assert r.status_code == 201, r.text
        seasons[label] = r.json()["id"]
    last_season, old = sorted(goals, key=lambda k: -goals[k])[:2]
    for match, season in ((last_season, "2025/26"), (old, "2019/20")):
        await owner_conn.execute(
            "UPDATE matches SET season_id = $1::uuid WHERE id = $2::uuid", seasons[season], match
        )
    # a video with an analysis: only its formations are read
    await upload(api, ids, last_season, b"v" * 100)
    analysis = {
        "formations": [{"team": "away", "start_ms": 0, "end_ms": 10**9, "formation": "6-0"}]
    }
    await owner_conn.execute(
        "UPDATE video_assets SET analysis = $1::jsonb, status = 'ready' WHERE match_id = $2::uuid",
        json.dumps({**analysis, "tracks_summary": "x" * 10_000}),
        last_season,
    )
    query_counter.clear()
    out = (await api.post(url, json=spec)).json()
    assert out["totals"]["cells"]["goals"]["value"] == total - goals[old]
    assert {r["key"] for r in out["rows"]} == set(goals) - {old}
    asked = (await api.post(url, json={**spec, "season_ids": [seasons["2019/20"]]})).json()
    assert [r["key"] for r in asked["rows"]] == [old]
    assert asked["totals"]["cells"]["goals"]["value"] == goals[old]
    six = {**spec, "filter": {"side": "own", "opponent_formation": "6-0"}}
    in_six = (await api.post(url, json=six)).json()
    assert {r["key"]: r["cells"]["goals"]["value"] for r in in_six["rows"]} == {
        last_season: goals[last_season]
    }
    # only the needed columns
    events = [q for q in query_counter if "FROM events" in q]
    assert events and not any("events.created_by_id" in q for q in events)
    videos = [q for q in query_counter if "FROM video_assets" in q]
    assert videos and not any("video_assets.analysis AS" in q for q in videos)


async def test_sportscode_round_trip_and_csv(
    make_api: Callable[[], Api], owner_conn: asyncpg.Connection
) -> None:
    api = make_api()
    ids = await seed(api, owner_conn)
    org = ids["org"]
    # the newest seeded match has video times; add a tagged clip with labels
    match_id = await owner_conn.fetchval(
        "SELECT id::text FROM matches ORDER BY kickoff_at DESC LIMIT 1"
    )
    sets = await api.post(
        f"/v1/orgs/{org}/teams/{ids['team']}/tag-sets",
        json={"name": "Angriff", "tags": [{"name": "7 gegen 6"}, {"name": "Kreuzung"}]},
    )
    tags = [t["id"] for t in sets.json()["tags"]]
    clip = await api.post(
        f"/v1/orgs/{org}/clips",
        json={"match_id": match_id, "start_ms": 61_000, "end_ms": 70_500, "title": "Überzahl"},
    )
    assert clip.status_code == 201, clip.text
    r = await api.put(
        f"/v1/orgs/{org}/tag-links",
        json={"target_type": "clip", "target_id": clip.json()["id"], "tag_ids": tags},
    )
    assert r.status_code in (200, 204), r.text

    xml1 = (await api.get(f"/v1/orgs/{org}/matches/{match_id}/export/sportscode")).content
    first = instances(xml1)
    with_video = sum(1 for e in MATCHES[-1].events if e["t_ms"] is not None)
    assert sum(first.values()) == with_video + 1
    assert (
        "61.000",
        "70.500",
        "Überzahl",
        (("Angriff", "7 gegen 6"), ("Angriff", "Kreuzung")),
    ) in first
    root = SafeET.fromstring(xml1)
    assert root.tag == "file" and root.find("ROWS") is not None

    # import into an empty match, export again: the same instances
    other = await new_match(
        api, ids, opponent_name="Rundlauf", kickoff_at="2026-12-01T18:00:00+01:00"
    )
    imp = await api.post(
        f"/v1/orgs/{org}/matches/{other['id']}/import/sportscode",
        files={"file": ("timeline.xml", xml1, "application/xml")},
    )
    assert imp.status_code == 200, imp.text
    assert imp.json()["clips"] == sum(first.values())
    xml2 = (await api.get(f"/v1/orgs/{org}/matches/{other['id']}/export/sportscode")).content
    assert instances(xml2) == first
    # importing twice reuses the tags
    again = await api.post(
        f"/v1/orgs/{org}/matches/{other['id']}/import/sportscode",
        files={"file": ("timeline.xml", xml1, "application/xml")},
    )
    assert again.json()["tags_created"] == 0

    # broken, empty and unsafe XML
    bad = {
        "broken": b"<file><instance>",
        "empty": b"<file><ALL_INSTANCES/></file>",
        "entity": b'<?xml version="1.0"?><!DOCTYPE x [<!ENTITY e SYSTEM "file:///etc/passwd">]>'
        b"<file><instance><start>1</start><end>2</end><code>&e;</code></instance></file>",
    }
    for name, payload in bad.items():
        r = await api.post(
            f"/v1/orgs/{org}/matches/{other['id']}/import/sportscode",
            files={"file": (f"{name}.xml", payload, "application/xml")},
        )
        assert r.status_code == 422, name

    r = await api.get(f"/v1/orgs/{org}/matches/{match_id}/export/events")
    rows = list(csv.reader(io.StringIO(r.content.decode("utf-8-sig")), delimiter=";"))
    assert rows[0][:3] == ["period", "clock_s", "video_ms"]
    assert len(rows) == len(MATCHES[-1].events) + 1
    own_shot = next(row for row in rows[1:] if row[3] == "shot" and row[4] == "own")
    assert own_shot[9]  # jersey number from the roster, no names
    assert "P7" not in r.text


@pytest.mark.usefixtures("recorded")
async def test_sportscode_export_has_only_moments_of_the_video(make_api: Callable[[], Api]) -> None:
    """A clip of five minutes from mid-half with the whole game's official report: the export
    used to write the report's events before the video with a negative end and the ones after it
    past the end of the file (Sportscode shows them as broken instances, our own import drops
    them)."""
    api = make_api()
    ids = await setup_club(api)
    m, _ = await reported_clip(api, ids)
    base = f"/v1/orgs/{ids['org']}/matches/{m['id']}"
    events = (await api.get(f"{base}/events")).json()
    inside = [e for e in events if e["t_ms"] is not None and 0 <= e["t_ms"] <= 300_000]
    assert 0 < len(inside) < len(events)
    found = instances((await api.get(f"{base}/export/sportscode")).content)
    assert sum(found.values()) == len(inside)
    for start, end, _code, _labels in found:
        assert 0 <= float(start) < float(end) <= 300.0, (start, end)
