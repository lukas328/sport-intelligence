#!/usr/bin/env python3
"""Builds the two self-contained pages of this folder from their sources.

    python3 docs/design/ux-reset/build.py

zielbild.html    the target design: src/page.html plus every template in src/screens
richtungen.html  four alternative visual directions: richtungen/page.html plus the templates in
                 richtungen/ and the current start screen for comparison

In a page source, `<!-- screens -->` is replaced by the templates. Stylesheets, the script and
the scoreboard fonts are inlined, so each result can be opened in a browser or published as it is.
"""

import base64
import pathlib

here = pathlib.Path(__file__).parent


def read(path: str) -> str:
    return (here / path).read_text(encoding="utf8")


def face(family: str, file: str) -> str:
    data = base64.b64encode((here / "assets/fonts" / file).read_bytes()).decode()
    return (
        '@font-face{font-family:"'
        + family
        + '";font-weight:700;font-display:block;'
        + "src:url(data:font/woff2;base64,"
        + data
        + ') format("woff2")}'
    )


def build(
    source: str, target: str, templates: list[str], styles: list[str], fonts: list[tuple[str, str]]
) -> None:
    page = read(source)
    page = page.replace("<!-- screens -->", "\n".join(read(t) for t in templates))
    css = "\n".join([face(f, n) for f, n in fonts] + [read(s) for s in styles])
    page = page.replace("<!-- css -->", "<style>\n" + css + "\n</style>")
    page = page.replace("<!-- js -->", "<script>\n" + read("assets/zielbild.js") + "\n</script>")
    (here / target).write_text(page, encoding="utf8")
    print(target + ":", len(page) // 1024, "kB,", page.count("<template"), "templates")


def names(folder: str) -> list[str]:
    return [
        str(p.relative_to(here))
        for p in sorted((here / folder).glob("*.html"))
        if p.name != "page.html"
    ]


build(
    "src/page.html",
    "zielbild.html",
    names("src/screens"),
    ["assets/halle.css", "assets/zielbild.css"],
    [("DSEG7", "DSEG7Classic-Bold.woff2")],
)
build(
    "richtungen/page.html",
    "richtungen.html",
    ["src/screens/spiele.html", *names("richtungen")],
    ["assets/halle.css", "assets/zielbild.css", "richtungen/richtungen.css"],
    [("DSEG7", "DSEG7Classic-Bold.woff2"), ("DSEG14", "DSEG14Classic-Bold.woff2")],
)
