"""Match report as PDF (BRIEF M8 "PDF-Berichte"), rendered with ReportLab.

Layout: club-coloured header band, score, key numbers side by side, score progression, goal grids
for both teams, player table and the ranked insights. Texts in de-CH, en and fr
(`report_texts.json`;
the insight templates are the same strings as in the web app, checked by a test).
"""

from __future__ import annotations

import io
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from reportlab.graphics.shapes import Drawing, Line, PolyLine, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

TEXTS: dict[str, Any] = json.loads(
    (Path(__file__).with_name("report_texts.json")).read_text(encoding="utf-8")
)
GRID = (("TL", "TC", "TR"), ("ML", "MC", "MR"), ("BL", "BC", "BR"))
INK = colors.HexColor("#111827")
MUTED = colors.HexColor("#6b7280")
LINE = colors.HexColor("#e5e7eb")
SURFACE = colors.HexColor("#f3f4f6")


def _styles() -> dict[str, ParagraphStyle]:
    base = ParagraphStyle("base", fontName="Helvetica", fontSize=9.5, leading=13, textColor=INK)
    return {
        "base": base,
        "muted": ParagraphStyle("muted", parent=base, textColor=MUTED, fontSize=8.5),
        "h1": ParagraphStyle("h1", parent=base, fontName="Helvetica-Bold", fontSize=18, leading=22),
        "h2": ParagraphStyle(
            "h2", parent=base, fontName="Helvetica-Bold", fontSize=11.5, leading=15, spaceBefore=8
        ),
        "score": ParagraphStyle(
            "score",
            parent=base,
            fontName="Helvetica-Bold",
            fontSize=30,
            leading=34,
            alignment=TA_LEFT,
        ),
    }


def _esc(text: object) -> str:
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _pct(v: float | None) -> str:
    return "-" if v is None else f"{round(v * 100)} %"


def _contrast(hex_colour: str) -> colors.Color:
    c = colors.HexColor(hex_colour)
    lum = 0.2126 * c.red + 0.7152 * c.green + 0.0722 * c.blue
    return colors.white if lum < 0.6 else INK


def insight_text(lang: str, item: dict[str, Any], names: dict[str, str]) -> str:
    t = TEXTS.get(lang, TEXTS["de-CH"])
    params = {k: v for k, v in item["params"].items() if v is not None}
    pid = item["params"].get("player_id")
    num = item["params"].get("number")
    params["who"] = (pid and names.get(str(pid))) or (f"#{num}" if num is not None else "?")
    zone = params.get("zone")
    if isinstance(zone, str):
        params["zone"] = t["goalZones"].get(zone) if len(zone) == 2 else t["zones"].get(zone, zone)
    if isinstance(params.get("type"), str):
        params["type"] = t["tt"].get(params["type"], params["type"])
    if isinstance(params.get("gsax"), int | float):
        params["gsax"] = f"{abs(float(params['gsax'])):.1f}"
    template = t["insights"].get(item["key"].split(".")[-1], "")
    try:
        return str(template.format(**params))
    except (KeyError, IndexError, ValueError):
        return str(template)


def _timeline(
    points: list[dict[str, Any]],
    own: str,
    opp: str,
    accent: colors.Color,
    period_s: int = 1800,
    periods: int = 2,
) -> Drawing:
    w, h = 170 * mm, 45 * mm
    d = Drawing(w, h)
    pad_l, pad_b = 18, 14
    max_t = max([float(period_s * periods), *[float(p["clock_s"]) for p in points]])
    max_g = max([5, *[max(p["own"], p["opp"]) for p in points]])

    def x(s: float) -> float:
        return float(pad_l + s / max_t * (w - pad_l - 6))

    def y(g: float) -> float:
        return float(pad_b + g / max_g * (h - pad_b - 8))

    for g in (0, max_g // 2, max_g):
        d.add(Line(pad_l, y(g), w - 6, y(g), strokeColor=LINE, strokeWidth=0.5))
        d.add(
            String(
                pad_l - 4,
                y(g) - 3,
                str(g),
                fontName="Helvetica",
                fontSize=7,
                fillColor=MUTED,
                textAnchor="end",
            )
        )
    step = 15 if max_t > 2400 else 5
    for m in range(0, int(max_t // 60) + 1, step):
        d.add(
            String(
                x(m * 60),
                3,
                f"{m}'",
                fontName="Helvetica",
                fontSize=7,
                fillColor=MUTED,
                textAnchor="middle",
            )
        )
    for k in range(1, periods):
        xs = x(k * period_s)
        d.add(Line(xs, pad_b, xs, h - 8, strokeColor=LINE, strokeDashArray=[2, 2]))

    def steps(key: str) -> list[float]:
        pts: list[float] = [x(0), y(0)]
        for p in points[1:]:
            pts += [x(p["clock_s"]), pts[-1], x(p["clock_s"]), y(p[key])]
        pts += [x(max_t), pts[-1]]
        return pts

    if len(points) > 1:
        d.add(PolyLine(steps("opp"), strokeColor=MUTED, strokeWidth=1.2, strokeDashArray=[3, 2]))
        d.add(PolyLine(steps("own"), strokeColor=accent, strokeWidth=1.8))
    d.add(
        String(
            w - 6,
            h - 8,
            own,
            fontName="Helvetica-Bold",
            fontSize=7.5,
            fillColor=accent,
            textAnchor="end",
        )
    )
    d.add(
        String(
            w - 6,
            h - 17,
            opp,
            fontName="Helvetica",
            fontSize=7.5,
            fillColor=MUTED,
            textAnchor="end",
        )
    )
    return d


def _goal_grid(data: dict[str, dict[str, int]], good_for_shooter: bool) -> Table:
    cells = []
    style = [
        ("GRID", (0, 0), (-1, -1), 1.2, colors.HexColor("#dc2626")),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
    ]
    for r, row in enumerate(GRID):
        line = []
        for c, zone in enumerate(row):
            v = data.get(zone)
            if v and v["shots"]:
                share = v["goals"] / v["shots"]
                line.append(f"{v['goals']}/{v['shots']}")
                tint = colors.HexColor("#16a34a" if good_for_shooter else "#dc2626")
                bg = colors.Color(tint.red, tint.green, tint.blue, alpha=0.12 + 0.5 * share)
                style.append(("BACKGROUND", (c, r), (c, r), bg))
            else:
                line.append("")
        cells.append(line)
    t = Table(cells, colWidths=[18 * mm] * 3, rowHeights=[9 * mm] * 3)
    t.setStyle(TableStyle(style))
    return t


def render(
    lang: str,
    org: dict[str, Any],
    match: dict[str, Any],
    stats: dict[str, Any],
    insights: list[dict[str, Any]],
    names: dict[str, str],
) -> bytes:
    t = TEXTS.get(lang, TEXTS["de-CH"])["labels"]
    s = _styles()
    accent = colors.HexColor(org["primary_color"])
    band_text = _contrast(org["primary_color"])
    buf = io.BytesIO()
    created = datetime.now(UTC).strftime("%d.%m.%Y")

    def frame(canvas: Any, doc: Any) -> None:
        width, height = A4
        canvas.saveState()
        canvas.setFillColor(accent)
        canvas.rect(0, height - 18 * mm, width, 18 * mm, stroke=0, fill=1)
        canvas.setFillColor(band_text)
        canvas.setFont("Helvetica-Bold", 12)
        canvas.drawString(16 * mm, height - 11.5 * mm, org["name"])
        canvas.setFont("Helvetica", 9)
        canvas.drawRightString(width - 16 * mm, height - 11.5 * mm, t["report"])
        canvas.setFillColor(MUTED)
        canvas.setFont("Helvetica", 7.5)
        canvas.drawString(16 * mm, 9 * mm, t["footer"])
        canvas.drawRightString(width - 16 * mm, 9 * mm, t["page"].format(n=doc.page))
        canvas.restoreState()

    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=26 * mm,
        bottomMargin=16 * mm,
        title=f"{t['report']} {match['home']} - {match['away']}",
        author=org["name"],
        creator="Handball AI",
    )
    story: list[Any] = [
        Paragraph(f"{_esc(match['home'])} - {_esc(match['away'])}", s["h1"]),
        Paragraph(_esc(match["subtitle"]), s["muted"]),
        Spacer(1, 4 * mm),
    ]
    if match.get("score"):
        ht = f"  ({t['halftime']} {match['halftime']})" if match.get("halftime") else ""
        story += [
            Paragraph(
                f"{match['score']}<font size=10 color='#6b7280'>{_esc(ht)}</font>", s["score"]
            ),
            Spacer(1, 3 * mm),
        ]

    if not stats["quality"]["events"]:
        story.append(Paragraph(t["noEvents"], s["base"]))
    else:
        if insights:
            story.append(Paragraph(t["insights"], s["h2"]))
            for item in insights:
                badge = t["strength"] if item["kind"] == "strength" else t["weakness"]
                tone = "#15803d" if item["kind"] == "strength" else "#b91c1c"
                story.append(
                    Paragraph(
                        f"<font color='{tone}'><b>{_esc(badge)}</b></font>  "
                        f"{_esc(insight_text(lang, item, names))}",
                        s["base"],
                    )
                )
        own, opp = stats["own"], stats["opponent"]
        rows = [
            ["", match["own_name"], match["opp_name"]],
            [t["goals"], own["goals"], opp["goals"]],
            [t["shots"], own["shots"], opp["shots"]],
            [t["shootingPct"], _pct(own["shooting_pct"]), _pct(opp["shooting_pct"])],
            [t["saves"], own["saves"], opp["saves"]],
            [t["savePct"], _pct(own["save_pct"]), _pct(opp["save_pct"])],
            [t["turnovers"], own["turnovers"], opp["turnovers"]],
            [
                t["sevenM"],
                f"{own['seven_m_goals']}/{own['seven_m_shots']}",
                f"{opp['seven_m_goals']}/{opp['seven_m_shots']}",
            ],
            [t["fastBreak"], own["fast_break_goals"], opp["fast_break_goals"]],
            [t["suspensions"], own["suspensions"], opp["suspensions"]],
            [t["xg"], f"{own['xg']:.1f}", f"{opp['xg']:.1f}"],
        ]
        table = Table(rows, colWidths=[70 * mm, 50 * mm, 50 * mm], hAlign="LEFT")
        table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9.5),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("TEXTCOLOR", (1, 0), (1, 0), accent),
                    ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, SURFACE]),
                    ("LINEBELOW", (0, 0), (-1, 0), 0.8, INK),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]
            )
        )
        story += [Paragraph(t["comparison"], s["h2"]), table]
        story += [
            Paragraph(t["timeline"], s["h2"]),
            _timeline(
                stats["timeline"]["score"],
                match["own_name"],
                match["opp_name"],
                accent,
                int(match.get("period_s", 1800)),
                int(match.get("periods", 2)),
            ),
        ]
        grids = Table(
            [
                [Paragraph(t["goalOwn"], s["muted"]), Paragraph(t["goalOpp"], s["muted"])],
                [_goal_grid(own["goal_zones"], True), _goal_grid(opp["goal_zones"], False)],
            ],
            colWidths=[85 * mm, 85 * mm],
            hAlign="LEFT",
        )
        story += [Spacer(1, 3 * mm), KeepTogether(grids)]

        players = [p for p in stats["players"].values() if p["side"] == "own"]
        players.sort(key=lambda p: (-p["goals"], p.get("number") or 99))
        if players:
            prow = [
                [
                    "#",
                    t["player"],
                    t["goals"],
                    t["shots"],
                    t["shootingPct"],
                    t["sevenM"],
                    t["turnovers"],
                    t["suspensions"],
                    t["saves"],
                ]
            ]
            for p in players:
                prow.append(
                    [
                        p.get("number") if p.get("number") is not None else "",
                        _esc(names.get(str(p.get("player_id")), "") or ""),
                        p["goals"],
                        p["shots"],
                        _pct(p["goals"] / p["shots"] if p["shots"] else None),
                        f"{p['seven_m_goals']}/{p['seven_m_shots']}",
                        p["turnovers"],
                        p["suspensions"],
                        p["saves"],
                    ]
                )
            pt = Table(
                prow, colWidths=[9 * mm, 52 * mm] + [15.5 * mm] * 7, repeatRows=1, hAlign="LEFT"
            )
            pt.setStyle(
                TableStyle(
                    [
                        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 7.5),
                        ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
                        ("LINEBELOW", (0, 0), (-1, 0), 0.8, INK),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, SURFACE]),
                    ]
                )
            )
            story += [Paragraph(t["players"], s["h2"]), pt]

    story += [Spacer(1, 4 * mm), Paragraph(t["generated"].format(date=created), s["muted"])]
    doc.build(story, onFirstPage=frame, onLaterPages=frame)
    return buf.getvalue()
