#!/usr/bin/env python3
"""Builds zielbild.html (one self-contained file) from src/ and assets/.

    python3 docs/design/ux-reset/build.py

src/page.html is the report. The marker `<!-- screens -->` is replaced by every template in
src/screens. The stylesheets, the script and the scoreboard font are inlined, so the result can
be opened in a browser or published as it is.
"""
import base64
import pathlib

here = pathlib.Path(__file__).parent


def read(path: str) -> str:
    return (here / path).read_text(encoding="utf8")


page = read("src/page.html")
screens = "\n".join(p.read_text(encoding="utf8") for p in sorted((here / "src/screens").glob("*.html")))
page = page.replace("<!-- screens -->", screens)

font = base64.b64encode((here / "assets/fonts/DSEG7Classic-Bold.woff2").read_bytes()).decode()
face = (
    '@font-face{font-family:"DSEG7";font-weight:700;font-display:block;'
    + "src:url(data:font/woff2;base64," + font + ') format("woff2")}'
)
css = face + "\n" + read("assets/halle.css") + "\n" + read("assets/zielbild.css")
page = page.replace("<!-- css -->", "<style>\n" + css + "\n</style>")
page = page.replace("<!-- js -->", "<script>\n" + read("assets/zielbild.js") + "\n</script>")
(here / "zielbild.html").write_text(page, encoding="utf8")
print("zielbild.html:", len(page) // 1024, "kB,", page.count("<template"), "screens")
