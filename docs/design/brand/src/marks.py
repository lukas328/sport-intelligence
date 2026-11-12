"""Handball Intelligence: the marks of the five directions as clean SVG geometry.

Every mark lives on a 48 x 48 grid (1 unit = 1/48 of the mark). Wordmarks are Kanit (SIL OFL),
shaped with HarfBuzz and converted to outlines, so the SVG files need no font.
"""
import math
import pathlib

import uharfbuzz as hb
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

FONTS = pathlib.Path(__file__).parent / "fonts"
_cache = {}


def _font(name):
    if name not in _cache:
        path = FONTS / f"{name}.ttf"
        blob = hb.Blob.from_file_path(str(path))
        _cache[name] = (TTFont(str(path)), hb.Font(hb.Face(blob)))
    return _cache[name]


def text(s, font="Kanit-ExtraBoldItalic", size=24, x=0, y=0, track=0):
    """Outline of a line of text. Returns (path d, width, cap height) in user units; y is the baseline."""
    tt, hf = _font(font)
    upm = tt["head"].unitsPerEm
    buf = hb.Buffer()
    buf.add_str(s)
    buf.guess_segment_properties()
    hb.shape(hf, buf, {"kern": True, "liga": True})
    gs = tt.getGlyphSet()
    order = tt.getGlyphOrder()
    k = size / upm
    pen = SVGPathPen(gs, lambda v: f"{v:.2f}".rstrip("0").rstrip("."))
    cx = 0
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
        name = order[info.codepoint]
        tp = TransformPen(pen, (k, 0, 0, -k, x + (cx + pos.x_offset) * k, y - pos.y_offset * k))
        gs[name].draw(tp)
        cx += pos.x_advance + track * upm / size
    cap = tt["OS/2"].sCapHeight * k
    return pen.getCommands(), (cx - track * upm / size) * k, cap


# ---------- the marks ----------
def mark_anlauf(c="#16171a"):
    """1 Anlauf: one goal as the tactics camera shows it, goal on the left: the run (thick, measured)
    up to the shot spot, then a thin straight line into the goal."""
    return (f'<rect x="1.5" y="12" width="4.5" height="24" fill="{c}"/>'
            f'<path d="M42 42C38.5 32.5 33.5 27.5 27.5 25.6" fill="none" stroke="{c}" stroke-width="7" stroke-linecap="round"/>'
            f'<circle cx="19.5" cy="23" r="6" fill="{c}"/>'
            f'<path d="M13 21.4L7.5 20" stroke="{c}" stroke-width="2.6" stroke-linecap="round"/>')


def mark_feld(c="#16171a"):
    """2 Feld: the court from above, turned: two side lines and the centre line make an H; the goal areas close it."""
    return (f'<rect x="5" y="3" width="7" height="42" fill="{c}"/><rect x="36" y="3" width="7" height="42" fill="{c}"/>'
            f'<rect x="12" y="21.5" width="24" height="5" fill="{c}"/>'
            f'<path d="M14.5 3A9.5 9.5 0 0 0 33.5 3M14.5 45A9.5 9.5 0 0 1 33.5 45" fill="none" stroke="{c}" stroke-width="3"/>')


def _slant_block():
    return "M0 0H48V36L0 46Z"


def mark_keil(c="#16171a", hole=True):
    """3 Keil: the Wurf head itself, the block with the slanted lower edge; HI cut out."""
    d, w, cap = text("HI", "Kanit-BlackItalic", 36)
    x = (48 - w) / 2
    d2, _, _ = text("HI", "Kanit-BlackItalic", 36, x=x, y=5 + cap)
    return f'<path d="{_slant_block()} {d2}" fill="{c}" fill-rule="evenodd"/>'


def mark_nummer(c="#16171a"):
    """4 Rückennummer: HI as a back number with two offset outlines, as the result in the Wurf head."""
    d, w, cap = text("HI", "Kanit-BlackItalic", 40)
    x = (48 - w) / 2 + 3
    y = 10 + cap
    out = ""
    for i, op in ((2, ".3"), (1, ".6")):
        dd, _, _ = text("HI", "Kanit-BlackItalic", 40, x=x - 4.2 * i, y=y - 3.4 * i)
        out += f'<path d="{dd}" fill="none" stroke="{c}" stroke-width="1.1" stroke-opacity="{op}"/>'
    dd, _, _ = text("HI", "Kanit-BlackItalic", 40, x=x, y=y)
    return out + f'<path d="{dd}" fill="{c}"/>'


def mark_hlauf(c="#16171a"):
    """5 H im Lauf: a slanted H whose crossbar is a run that ends at the shot spot, short of the right stem."""
    s = math.tan(math.radians(12))
    def stem(x0):  # parallelogram, 7 wide, from y 4 to 44, slanted 12 degrees
        return f"M{x0 + 40 * s:.2f} 4H{x0 + 7 + 40 * s:.2f}L{x0 + 7:.2f} 44H{x0:.2f}Z"
    return (f'<path d="{stem(3)} {stem(31)}" fill="{c}"/>'
            f'<path d="M12.6 30C16 28 18.5 25 23.4 23.6" fill="none" stroke="{c}" stroke-width="5.5" stroke-linecap="round"/>'
            f'<circle cx="29.6" cy="22.6" r="4.4" fill="{c}"/>')


def mark_auge(c="#16171a"):
    """sketch only: the goal area arc and a dot read as an eye"""
    return (f'<path d="M6 12A18 18 0 0 0 42 12" fill="none" stroke="{c}" stroke-width="5"/>'
            f'<circle cx="24" cy="19" r="6" fill="{c}"/><rect x="18" y="6" width="12" height="3" fill="{c}"/>')


MARKS = {"anlauf": mark_anlauf, "feld": mark_feld, "keil": mark_keil, "nummer": mark_nummer, "hlauf": mark_hlauf}

# wordmark settings per direction: (font, case, two lines?)
WORD = {
    "anlauf": ("Kanit-ExtraBoldItalic", "handball intelligence"),
    "feld": ("Kanit-SemiBold", "Handball Intelligence"),
    "keil": ("Kanit-BlackItalic", "Handball Intelligence"),
    "nummer": ("Kanit-BlackItalic", "Handball Intelligence"),
    "hlauf": ("Kanit-ExtraBoldItalic", "Handball Intelligence"),
}


def svg(inner, w=48, h=48, extra=""):
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:.2f} {h:.2f}"{extra}>{inner}</svg>'


def lockup(key, c="#16171a", form="quer"):
    """Mark plus wordmark. quer: one line beside the mark; gestapelt: two lines under the mark; zwei: two lines beside."""
    font, s = WORD[key]
    a, b = s.split(" ")
    m = MARKS[key](c)
    if form == "quer":
        size = 30
        d, w, cap = text(s, font, size, x=62, y=24 + 30 * 0.36)
        return svg(f'<g>{m}</g><path d="{d}" fill="{c}"/>', 62 + w + 4, 48)
    if form == "zwei":
        size = 22
        d1, w1, cap = text(a, font, size, x=60, y=21)
        d2, w2, _ = text(b, font, size, x=60 - (3 if "Italic" in font else 0), y=43)
        return svg(f'<g>{m}</g><path d="{d1} {d2}" fill="{c}"/>', 60 + max(w1, w2) + 4, 48)
    # gestapelt
    size = 15
    d1, w1, cap = text(a, font, size)
    d2, w2, _ = text(b, font, size)
    W = max(w1, w2, 48)
    d1, _, _ = text(a, font, size, x=(W - w1) / 2, y=48 + 10 + cap)
    d2, _, _ = text(b, font, size, x=(W - w2) / 2, y=48 + 10 + cap + 17)
    return svg(f'<g transform="translate({(W - 48) / 2:.2f} 0)">{m}</g><path d="{d1} {d2}" fill="{c}"/>', W, 48 + 10 + cap + 17 + 4)
