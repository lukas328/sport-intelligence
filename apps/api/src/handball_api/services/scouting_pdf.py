"""Preparation report (A4) and goalkeeper shooter card (A6) as PDF (addendum 01, 4.6)."""

from __future__ import annotations

import io
from datetime import datetime
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, A6
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from handball_api.services.report_pdf import LINE, SURFACE, TEXTS, _esc, _goal_grid, _pct, _styles


def _t(lang: str) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    texts = TEXTS.get(lang, TEXTS["de-CH"])
    return texts["scouting"], texts["zones"], texts["goalZones"]


def _zone(z: str | None, zones: dict[str, str], goal_zones: dict[str, str]) -> str:
    if not z:
        return "-"
    return goal_zones.get(z) if len(z) == 2 and z in goal_zones else zones.get(z, z)  # type: ignore[return-value]


def observation_text(lang: str, o: dict[str, Any]) -> str:
    t, zones, goal_zones = _t(lang)
    p = dict(o["params"])
    for k in ("share", "pct"):
        if isinstance(p.get(k), float):
            p[k] = _pct(p[k])
    if "zone" in p:
        p["zone"] = _zone(p["zone"], zones, goal_zones)
    return t.get(f"obs_{o['key']}", "").format(**p)


def _table(rows: list[list[str]], widths: list[float]) -> Table:
    tbl = Table(rows, colWidths=widths, repeatRows=1)
    tbl.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("BACKGROUND", (0, 0), (-1, 0), SURFACE),
                ("LINEBELOW", (0, 0), (-1, -1), 0.4, LINE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return tbl


def render_report(
    lang: str, team: str, kickoff: datetime, facts: dict[str, Any], basis: dict[str, Any]
) -> bytes:
    t, zones, goal_zones = _t(lang)
    s = _styles()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=t["title"],
    )
    g = facts["glance"]
    story: list[Any] = [
        Paragraph(_esc(f"{t['title']}: {team}"), s["h1"]),
        Paragraph(
            _esc(
                t["subtitle"].format(
                    opponent=facts["opponent"]["name"], date=kickoff.strftime("%d.%m.%Y %H:%M")
                )
            ),
            s["muted"],
        ),
        Paragraph(
            _esc(
                t["basis"].format(
                    matches=basis.get("matches", 0),
                    tagged=basis.get("tagged_matches", 0),
                    videos=basis.get("videos", 0),
                )
            ),
            s["muted"],
        ),
    ]
    missing = [t.get(f"missing_{m}", m) for m in facts.get("missing", [])]
    if missing:
        story.append(Paragraph(_esc(t["missing"].format(items=", ".join(missing))), s["muted"]))

    story += [Paragraph(t["observations"], s["h2"])]
    obs = facts.get("observations") or []
    for o in obs:
        story.append(
            Paragraph(
                _esc(
                    f"• {observation_text(lang, o)} ({t['sample'].format(n=o['n'])}, "
                    f"{t['clips'].format(n=len(o['clips']))})"
                ),
                s["base"],
            )
        )
    if not obs:
        story.append(Paragraph(t["none"], s["muted"]))

    story += [
        Paragraph(t["glance"], s["h2"]),
        Paragraph(_esc(t["record"].format(**g["record"])), s["base"]),
        Paragraph(
            _esc(
                t["goalsPerMatch"].format(
                    v=g["goals_per_match"] if g["goals_per_match"] is not None else "-"
                )
            ),
            s["base"],
        ),
        Paragraph(_esc(t["shootingPct"].format(v=_pct(g["shooting_pct"]), n=g["n"])), s["base"]),
        Paragraph(t["shooters"], s["h2"]),
    ]
    rows = [[t["number"], t["goalsShots"], t["mainZone"], t["goalZones"]]]
    for sh in facts["shooters"]:
        gz = ", ".join(
            f"{_zone(z, zones, goal_zones)} ({n})" for z, n in list(sh["goal_zones"].items())[:3]
        )
        rows.append(
            [
                str(sh["number"]),
                f"{sh['goals']}/{sh['shots']} ({_pct(sh['shooting_pct'])})",
                _zone(sh["main_zone"], zones, goal_zones),
                gz or "-",
            ]
        )
    story.append(_table(rows, [14 * mm, 32 * mm, 50 * mm, 82 * mm]))

    story += [
        Paragraph(t["plays"], s["h2"]),
        Paragraph(t["playsMissing"], s["muted"]),
        Paragraph(t["defense"], s["h2"]),
    ]
    total = sum(facts["defense"]["formations_ms"].values()) or 0
    for f, ms in facts["defense"]["formations_ms"].items():
        story.append(
            Paragraph(
                _esc(t["formation"].format(f=f, share=_pct(ms / total if total else None))),
                s["base"],
            )
        )
    for w in facts["defense"]["weak_zones"]:
        story.append(
            Paragraph(
                _esc(
                    t["weakZone"].format(
                        zone=_zone(w["zone"], zones, goal_zones),
                        goals=w["goals"],
                        shots=w["shots"],
                        pct=_pct(w["pct"]),
                    )
                ),
                s["base"],
            )
        )
    fb = facts["fast_break"]
    story += [
        Paragraph(t["fastBreak"], s["h2"]),
        Paragraph(
            _esc(t["fastBreakText"].format(goals=fb["goals"], share=_pct(fb["share"]), n=fb["n"])),
            s["base"],
        ),
        Paragraph(t["numbers"], s["h2"]),
        Paragraph(
            _esc(
                t["theyPP"].format(
                    **{k: facts["numbers"]["they_in_powerplay"][k] for k in ("goals", "periods")}
                )
            ),
            s["base"],
        ),
        Paragraph(
            _esc(
                t["wePP"].format(
                    **{k: facts["numbers"]["we_in_powerplay"][k] for k in ("goals", "periods")}
                )
            ),
            s["base"],
        ),
    ]
    doc.build(story)
    return buf.getvalue()


def render_goalkeeper_card(lang: str, facts: dict[str, Any]) -> bytes:
    """A6 card for the water bottle: number, position, preferred goal zones (grid per shooter)."""
    t, zones, goal_zones = _t(lang)
    s = _styles()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A6,
        leftMargin=6 * mm,
        rightMargin=6 * mm,
        topMargin=6 * mm,
        bottomMargin=6 * mm,
        title=t["gkTitle"],
    )
    story: list[Any] = [
        Paragraph(_esc(f"{t['gkTitle']}: {facts['opponent']['name']}"), s["h2"]),
        Paragraph(t["gkHint"], s["muted"]),
        Spacer(1, 2 * mm),
    ]
    shooters = [sh for sh in facts["shooters"] if sh["shots"] >= 3][:4]
    if not shooters:
        story.append(Paragraph(t["few"], s["base"]))
    cells = []
    for sh in shooters:
        grid = _goal_grid(
            {z: {"goals": n, "shots": n} for z, n in sh["goal_zones"].items()},
            good_for_shooter=True,
        )
        where = _esc(_zone(sh["main_zone"], zones, goal_zones))
        label = Paragraph(
            f"<b>#{sh['number']}</b> {where} · {sh['goals']}/{sh['shots']}", s["base"]
        )
        cells.append([label, grid])
    if cells:
        tbl = Table(cells, colWidths=[30 * mm, 56 * mm])
        tbl.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor("#e5e7eb")),
                ]
            )
        )
        story.append(tbl)
    doc.build(story)
    return buf.getvalue()
