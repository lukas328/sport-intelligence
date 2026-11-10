"""Inline lib/*.js into each direction's index.html so the page works on its own.
Source: <dir>/index.src.html with <script src="../lib/x.js"></script>. Run: python3 build.py"""
import pathlib, re
here = pathlib.Path(__file__).parent
for src in here.glob("*/index.src.html"):
    s = src.read_text()
    s = re.sub(r'<script src="\.\./lib/([\w.]+)"></script>', lambda m: "<script>\n" + (here / "lib" / m.group(1)).read_text() + "</script>", s)
    (src.parent / "index.html").write_text(s)
    print("built", src.parent.name)
