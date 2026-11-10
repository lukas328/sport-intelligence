"""Builds docs/screens from the captures of apps/web/screens/capture.spec.ts.

The PNG captures in docs/screens/png become compact JPEGs, one folder per flow, and README.md shows
them per screen (desktop and phone side by side). Run after the capture:

    python3 docs/screens/build.py
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "png"
MAX_HEIGHT = 6000  # very long pages keep the full width; the height is capped to keep files small
GROUPS = {
    "1-einstieg": (
        "Einstieg",
        "Anmelden, registrieren und der erste Start mit der Teamsuche auf handball.ch.",
    ),
    "2-trainer": (
        "Trainer/in",
        "Demo-Verein mit analysierten Testvideos: Übersicht, Spiele, Match-Arbeitsplatz Schritt "
        "für Schritt, Analyse, Bibliothek, Training, Team, Einstellungen.",
    ),
    "3-spielerin": ("Spieler/in", "Ein Spielerkonto, mit dem Kadereintrag verknüpft."),
    "4-eltern": ("Eltern", "Ein Elternkonto für ein Kind im Kader."),
    "5-oeffentlich": ("Öffentlich", "Seiten ohne Anmeldung."),
}
HEADER = [
    "# Screenshots der App",
    "",
    "Stand: 10. November 2026 (main nach PR 33). Lokaler Stack mit dem Demo-Verein aus",
    "`scripts/seed.py` (synthetische Testvideos), erfundene Namen. Offizielle Daten (handball.ch)",
    "und Wurf-Vorschläge kommen aus aufgezeichneten Testantworten, weil der lokale Stack",
    "handball.ch nicht erreicht.",
    "",
    "Jeder Screen als Desktop (1440 px) und Phone (390 px), die ganze Seite. Neu erzeugen, bei",
    "laufendem Stack (`make up`, `make seed`) und Web-App:",
    "`cd apps/web && npx playwright test -c screens.config.ts`, dann",
    "`python3 docs/screens/build.py` (wandelt in JPEG und schreibt diese Seite).",
    "",
]


def anchor(title: str) -> str:
    return title.lower().replace("/", "").replace(" ", "-")


def build() -> None:
    toc: list[str] = []
    body: list[str] = []
    for group, (title, intro) in GROUPS.items():
        src = SRC / group
        if not src.is_dir():
            continue
        out = ROOT / group
        shutil.rmtree(out, ignore_errors=True)
        out.mkdir(parents=True)
        names = sorted({re.sub(r"-(desktop|phone)\.png$", "", p.name) for p in src.glob("*.png")})
        toc.append(f"- [{title}](#{anchor(title)}) ({len(names)} Screens)")
        body += [f"## {title}", "", intro, ""]
        for name in names:
            label = re.sub(r"^\d+-", "", name).replace("-", " ")
            cells = []
            for mode, width in (("desktop", 560), ("phone", 180)):
                png = src / f"{name}-{mode}.png"
                if not png.exists():
                    continue
                with Image.open(png) as im:
                    rgb = im.convert("RGB")
                if rgb.height > MAX_HEIGHT:
                    rgb = rgb.crop((0, 0, rgb.width, MAX_HEIGHT))
                jpg = f"{name}-{mode}.jpg"
                rgb.save(out / jpg, "JPEG", quality=72, optimize=True, progressive=True)
                cells.append(
                    f'<a href="{group}/{jpg}"><img src="{group}/{jpg}" width="{width}" '
                    f'alt="{label}, {mode}"></a>'
                )
            body += [f"### {label}", "", " ".join(cells), ""]
    (ROOT / "README.md").write_text("\n".join([*HEADER, "## Inhalt", "", *toc, "", *body]))
    shutil.rmtree(SRC)


if __name__ == "__main__":
    build()
