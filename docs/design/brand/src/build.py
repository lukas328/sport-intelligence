#!/usr/bin/env python3
"""Builds the brand page and the logo files for «Handball Intelligence».

    pip install fonttools uharfbuzz
    python3 docs/design/brand/src/build.py

Writes docs/design/brand/index.html and docs/design/brand/logos/*.svg.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from marks import MARKS, WORD, lockup, mark_auge, svg, text  # noqa: E402
from page import page  # noqa: E402

HERE = pathlib.Path(__file__).parent.parent
INK, STOFF = "#16171a", "#eceae5"

(HERE / "logos").mkdir(exist_ok=True)
for key, fn in MARKS.items():
    files = {
        "zeichen": svg(fn(INK)),
        "zeichen-weiss": svg(fn("#ffffff")),
        "quer": lockup(key, INK, "quer"),
        "zweizeilig": lockup(key, INK, "zwei"),
        "gestapelt": lockup(key, INK, "gestapelt"),
        "app-icon": svg(f'<rect width="48" height="48" fill="{STOFF}"/><g transform="translate(9.6 9.6) scale(.6)">{fn(INK)}</g>'),
        "favicon": svg(f'<rect width="48" height="48" fill="{INK}"/><g transform="translate(6 6) scale(.75)">{fn(STOFF)}</g>'),
    }
    for name, content in files.items():
        (HERE / "logos" / f"{key}-{name}.svg").write_text(content, encoding="utf8")

from marks2 import PIX, pixsvg, wordmark  # noqa: E402
from page2 import final  # noqa: E402

wm = wordmark("title", INK, two=True)
wm_vb = [float(v) for v in wm.split('viewBox="')[1].split('"')[0].split()]
inner = wm.split(">", 1)[1].rsplit("</svg>", 1)[0]
k = 48 / wm_vb[3]
finals = {
    "zeichen": svg(final(INK)), "zeichen-weiss": svg(final("#ffffff")),
    "zweizeilig": svg(f'{final(INK)}<g transform="translate(60 0) scale({k:.4f})">{inner}</g>', 60 + wm_vb[2] * k, 48),
    "wortmarke-zweizeilig": wm, "wortmarke-quer": wordmark("title", INK),
    "app-icon": svg(f'<rect width="48" height="48" fill="{INK}"/><g transform="translate(10.8 10.8) scale(.55)">{final(STOFF)}</g>'),
    "favicon-16": pixsvg(PIX["g16"], STOFF, INK), "favicon-32": pixsvg(PIX["g32"], STOFF, INK),
}
for name, content in finals.items():
    (HERE / "logos" / f"final-{name}.svg").write_text(content, encoding="utf8")

(HERE / "index.html").write_text(page(), encoding="utf8")
print("index.html and", len(list((HERE / "logos").glob("*.svg"))), "logo files")
