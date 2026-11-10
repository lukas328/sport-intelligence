#!/usr/bin/env python3
"""Builds runde2/<name>/index.html from runde2/<name>/src.html.

    python3 docs/design/ux-reset/runde2/build.py

`<!-- js -->` becomes runde2/common.js (court, charts, pictograms, frames); `<!-- led -->` becomes
the DSEG7 face from ../assets/fonts. The result opens in a browser without a build; only Google
Fonts are loaded from outside.
"""
import base64
import pathlib

here = pathlib.Path(__file__).parent
js = (here / "common.js").read_text(encoding="utf8")
led = base64.b64encode((here.parent / "assets/fonts/DSEG7Classic-Bold.woff2").read_bytes()).decode()
led_face = '@font-face{font-family:"DSEG7";font-weight:700;font-display:block;src:url(data:font/woff2;base64,' + led + ') format("woff2")}'

for src in sorted(here.glob("*/src.html")):
    page = src.read_text(encoding="utf8")
    page = page.replace("<!-- js -->", "<script>\n" + js + "</script>")
    page = page.replace("/* led */", led_face)
    out = src.with_name("index.html")
    out.write_text(page, encoding="utf8")
    print(out.relative_to(here), len(page) // 1024, "kB")
