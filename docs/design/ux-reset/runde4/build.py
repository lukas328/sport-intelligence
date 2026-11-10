#!/usr/bin/env python3
"""Builds runde4/<name>/index.html from runde4/<name>/src.html.

    python3 docs/design/ux-reset/runde4/build.py

`<!-- js -->` becomes runde4/common.js (frames, club colours, match data). The result opens in a
browser without a build; only Google Fonts are loaded from outside.
"""
import pathlib

here = pathlib.Path(__file__).parent
js = (here / "common.js").read_text(encoding="utf8")

for src in sorted(here.glob("*/src.html")):
    page = src.read_text(encoding="utf8")
    page = page.replace("<!-- js -->", "<script>\n" + js + "</script>")
    out = src.with_name("index.html")
    out.write_text(page, encoding="utf8")
    print(out.relative_to(here), len(page) // 1024, "kB")
