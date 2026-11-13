#!/usr/bin/env python3
"""Builds zielbild.html, the target design «Anlauf», from its sources.

    python3 docs/design/ux-reset/build.py

src/zielbild.html          the page: idea, rules, «Was wir nicht tun», the colour switch
assets/anlauf.css          tokens and components of the app    -> globals.css and components
assets/anlauf-farbe.js     colour model: club, opponent, clash -> lib/color.ts
assets/anlauf-feld.js      court, bundles, zones, tactics cam  -> the graphic components
assets/anlauf-demo.js      demo data in the API's shape        -> replaced by real data
assets/anlauf-screens.js   every screen of SPEC.md section 7   -> reference for the pages
assets/zielbild.css/.js    the presentation page only          -> not ported

`<!-- css -->` and `<!-- js -->` in the page are replaced by the inlined files, so the result
opens in a browser as it is (fonts come from Google Fonts). The earlier direction «Halle» and its
build live in archiv/halle/.
"""

import pathlib

here = pathlib.Path(__file__).parent
STYLES = ["assets/anlauf.css", "assets/zielbild.css"]
SCRIPTS = [
    "assets/anlauf-farbe.js",
    "assets/anlauf-demo.js",
    "assets/anlauf-feld.js",
    "assets/anlauf-screens.js",
    "assets/zielbild.js",
]


def read(path: str) -> str:
    return (here / path).read_text(encoding="utf8")


page = read("src/zielbild.html")
css = "\n".join(read(s) for s in STYLES)
js = "\n".join(read(s) for s in SCRIPTS)
page = page.replace("<!-- css -->", "<style>\n" + css + "\n</style>")
page = page.replace("<!-- js -->", "<script>\n" + js + "\n</script>")
(here / "zielbild.html").write_text(page, encoding="utf8")
print("zielbild.html:", len(page) // 1024, "kB")
