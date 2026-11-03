"""Partner adapters (addendum 01 section 7)."""

from __future__ import annotations

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

import pytest

from handball_api.integrations import ADAPTERS, AdapterError, NotConfiguredError, adapter
from handball_api.integrations.official_feed import CsvFeed, JsonFeed, parse_clock
from handball_api.integrations.support import (
    CrispChat,
    ExternalStatusPage,
    NoStatusPage,
    NoSupportChat,
)
from handball_api.integrations.team_ops import CalendarEntry, IcsTeamOps
from handball_api.integrations.video_sources import FileLinkSource, YouTubeSource
from handball_api.integrations.wearables import CsvWearable

ICS = (
    "BEGIN:VCALENDAR\r\nVERSION:2.0\r\n"
    "BEGIN:VEVENT\r\nUID:t-2\r\nDTSTART;TZID=Europe/Zurich:20261112T193000\r\n"
    "DTEND;TZID=Europe/Zurich:20261112T211500\r\nSUMMARY:Training\\, Halle B\r\n"
    "LOCATION:Sporthalle Wankdorf\r\nDESCRIPTION:Schwerpunkt: Rückzug\\nBälle mitbringen\r\n"
    "END:VEVENT\r\n"
    "BEGIN:VEVENT\r\nUID:m-1\r\nDTSTART:20261107T170000Z\r\nSUMMARY:Spiel gegen\r\n"
    "  TV Gegner\r\nEND:VEVENT\r\n"
    "BEGIN:VEVENT\r\nUID:c-3\r\nDTSTART;VALUE=DATE:20261224\r\nSUMMARY:Pause\r\nEND:VEVENT\r\n"
    "END:VCALENDAR\r\n"
)


def test_ics_import_and_roundtrip() -> None:
    ics = IcsTeamOps()
    entries = ics.import_events(ICS)
    assert [e.uid for e in entries] == ["m-1", "t-2", "c-3"]
    match, training, holiday = entries
    assert match.title == "Spiel gegen TV Gegner"  # folded line
    assert match.starts_at == datetime(2026, 11, 7, 17, 0, tzinfo=UTC)
    assert training.title == "Training, Halle B"
    assert training.description == "Schwerpunkt: Rückzug\nBälle mitbringen"
    assert training.starts_at == datetime(2026, 11, 12, 19, 30, tzinfo=ZoneInfo("Europe/Zurich"))
    assert holiday.starts_at == date(2026, 12, 24)

    long = CalendarEntry(uid="x", title="Video-Sitzung " * 10, starts_at=match.starts_at)
    out = ics.export_events([*entries, long], "Herren 1")
    assert all(len(line.encode()) <= 75 for line in out.split("\r\n"))
    again = ics.import_events(out)
    assert {e.uid for e in again} == {"m-1", "t-2", "c-3", "x"}
    by_uid = {e.uid: e for e in again}
    assert by_uid["m-1"].starts_at == match.starts_at
    assert by_uid["t-2"].starts_at == training.starts_at
    assert by_uid["t-2"].description == training.description
    assert by_uid["x"].title == long.title
    assert by_uid["c-3"].starts_at == date(2026, 12, 24)
    with pytest.raises(AdapterError):
        ics.import_events("hello")


def test_official_feeds() -> None:
    csv_rows = CsvFeed().events(
        "period;clock;team;event;number\n1;05:12;own;goal;7\n2;31:00;opponent;2min;\n"
    )
    assert [(e.period, e.clock_s, e.side, e.kind, e.number) for e in csv_rows] == [
        (1, 312.0, "own", "goal", 7),
        (2, 1860.0, "opponent", "2min", None),
    ]
    js = JsonFeed().events(
        '{"events": [{"period": 1, "clock": "1:00", "team": "own", "event": "save"}]}'
    )
    assert js[0].kind == "save" and js[0].clock_s == 60.0
    with pytest.raises(AdapterError):
        CsvFeed().events("period,clock,team,event\n1,1:00,home,goal\n")
    with pytest.raises(AdapterError):
        JsonFeed().events("{")
    with pytest.raises(AdapterError):
        parse_clock("x:y")


def test_video_sources() -> None:
    link = FileLinkSource()
    assert link.download_url("https://nas.club.ch/spiele/2026-11-07.mp4").endswith(".mp4")
    assert link.metadata("https://nas.club.ch/a/b.mov").title == "b.mov"
    for bad in ("http://nas.club.ch/a.mp4", "ftp://x/a.mp4"):
        with pytest.raises(AdapterError):
            link.download_url(bad)
    with pytest.raises(AdapterError):
        link.download_url("https://nas.club.ch/index.html")
    yt = YouTubeSource()
    assert yt.video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=3") == "dQw4w9WgXcQ"
    assert yt.metadata("https://youtu.be/dQw4w9WgXcQ").url == "https://youtu.be/dQw4w9WgXcQ"
    with pytest.raises(AdapterError, match="owner"):
        yt.download_url("https://youtu.be/dQw4w9WgXcQ")


def test_wearable_csv() -> None:
    samples = CsvWearable().samples(
        "t_ms;number;x;y;heart_rate;load\n200;7;10,5;4;150;\n100;9;;;;1.5\n"
    )
    assert [(s.t_ms, s.number, s.x, s.heart_rate, s.load) for s in samples] == [
        (100, 9, None, None, 1.5),
        (200, 7, 10.5, 150, None),
    ]
    with pytest.raises(AdapterError, match="outside"):
        CsvWearable().samples("t_ms,number,x,y\n1,7,50,4\n")
    with pytest.raises(AdapterError, match="required"):
        CsvWearable().samples("t_ms,number\n1,\n")


def test_support_and_status() -> None:
    w = CrispChat("site-1").widget("de-CH", "abc")
    assert w is not None and w.config == {"website_id": "site-1", "locale": "de", "token_id": "abc"}
    assert NoSupportChat().widget("de-CH", None) is None
    page = ExternalStatusPage("https://status.example.ch")
    assert page.public_url() == "https://status.example.ch"
    report = {
        c.component: c.status
        for c in page.report({"database": False, "redis": False, "storage": True})
    }
    assert report == {"database": "down", "redis": "degraded", "storage": "operational"}
    assert NoStatusPage().report({"database": True}) == [] and NoStatusPage().public_url() is None


def test_registry_and_stubs() -> None:
    assert set(ADAPTERS) == {"video_source", "stream", "team_ops", "official_feed", "wearable"}
    assert isinstance(adapter("team_ops", "ics"), IcsTeamOps)
    with pytest.raises(AdapterError):
        adapter("team_ops", "nope")
    calls = {
        "video_source": lambda a: a.list_recordings("club"),
        "stream": lambda a: a.fetch_recording("s"),
        "team_ops": lambda a: a.import_events(""),
        "official_feed": lambda a: a.events(""),
        "wearable": lambda a: a.samples(""),
    }
    stubs = 0
    for category, items in ADAPTERS.items():
        for name, cls in items.items():
            if getattr(cls, "partner", None) == name:
                with pytest.raises(NotConfiguredError, match=name):
                    calls[category](cls())
                stubs += 1
    assert stubs == 10
