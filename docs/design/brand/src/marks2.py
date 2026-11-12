"""Round 2: refinement of «H im Lauf» and «Feld», pixel favicons, the custom wordmark."""
import math

from marks import _font, text, svg
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
import uharfbuzz as hb

INK = "#16171a"


def hlauf(c=INK, slant=12, sw=7, cut=0, run_w=5.5, run=None, dot=(29.6, 22.6, 4.4), mode="dot", post=False, over=False):
    """A slanted H whose crossbar is a run. All in the 48 grid.
    slant: stem angle in degrees; cut: height difference of the slanted cut at top and bottom (0 = flat);
    mode: dot | none | hole; post: right stem as a short upright post; over: run starts left of the left stem."""
    s = math.tan(math.radians(slant))
    top, bot = 4, 44

    def stem(x0, y0=top, y1=bot, upright=False):
        k = 0 if upright else s
        xl = lambda y: x0 + (bot - y) * k
        xr = lambda y: x0 + sw + (bot - y) * k
        pts = ((xl(y0), y0), (xr(y0 + cut), y0 + cut), (xr(y1), y1), (xl(y1 - cut), y1 - cut))
        return "M" + "L".join(f"{p[0]:.2f} {p[1]:.2f}" for p in pts) + "Z"

    left = stem(3)
    right = stem(31 + (3 if post else 0), y0=17 if post else top, upright=post)
    cx, cy, r = dot
    rp = run or f"M{0.5 if over else 12.6} {32.5 if over else 30}C{6 if over else 16} {29.5 if over else 28} 18.5 25 23.4 23.6"
    out = f'<path d="{left} {right}" fill="{c}"/>'
    if mode == "hole":
        # the run meets the right stem; the shot spot is punched out of the stem
        out = f'<path d="{left}" fill="{c}"/><path d="{right} M{cx + r:.2f} {cy:.2f}A{r} {r} 0 1 0 {cx - r:.2f} {cy:.2f}A{r} {r} 0 1 0 {cx + r:.2f} {cy:.2f}Z" fill="{c}" fill-rule="evenodd"/>'
        out += f'<path d="{rp}" fill="none" stroke="{c}" stroke-width="{run_w}" stroke-linecap="round"/>'
        return out
    out += f'<path d="{rp}" fill="none" stroke="{c}" stroke-width="{run_w}" stroke-linecap="round"/>'
    if mode == "dot":
        out += f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{c}"/>'
    return out


VARIANTS = [
    ("a", "Grundform", "12 Grad, Punkt r 4,4 auf halber Höhe, Lauf 5,5.", dict()),
    ("b", "Punkt gross, Lauf flach", "Punkt r 5,4 etwas höher, Lauf 6,5 und flacher: der Punkt trägt mehr.",
     dict(dot=(28.6, 21.6, 5.4), run_w=6.5, run="M12.6 29.5C16.5 28 18 25.5 21.6 23.6")),
    ("c", "ohne Punkt", "Der Lauf endet vor dem Stamm, ohne Wurfposition.",
     dict(mode="none", run="M12.6 30C17 28 21 24.5 28.6 23")),
    ("d", "Punkt als Loch", "Der Lauf trifft den rechten Stamm, die Wurfposition ist ausgestanzt.",
     dict(mode="hole", dot=(39.0, 22.8, 2.4), run="M12.6 30C17 28 22 24.5 34 23.2")),
    ("e", "Lauf von aussen", "Der Lauf beginnt links ausserhalb des Stamms und kreuzt ihn.",
     dict(over=True, run_w=6)),
    ("f", "stärker geneigt", "18 Grad statt 12: schneller, aber näher an Wett-Kursiven.",
     dict(slant=18, dot=(31.0, 22.6, 4.4), run="M14 30C17.5 28 20 25 24.8 23.6")),
    ("g", "Keil-Schnitt", "Stämme oben und unten schräg geschnitten wie der Wurf-Kopf (3 Einheiten Fall).",
     dict(cut=3)),
    ("h", "rechter Stamm als Pfosten", "Rechts ein kurzer, aufrechter Pfosten: das Tor.",
     dict(post=True, dot=(29.0, 25.0, 4.4), run="M12.6 32C16 30 18.5 27.4 23 26")),
]


def cross(c=INK):
    """5 x 2: a slanted H whose crossbar is the goal area line (6 m arc), the dot is the shot spot inside."""
    s = math.tan(math.radians(12))
    def stem(x0):
        return f"M{x0 + 40 * s:.2f} 4H{x0 + 7 + 40 * s:.2f}L{x0 + 7:.2f} 44H{x0:.2f}Z"
    return (f'<path d="{stem(3)} {stem(31)}" fill="{c}"/>'
            f'<path d="M11.2 20C14 30.5 30 30.5 34.6 20" fill="none" stroke="{c}" stroke-width="5.5"/>')


def feld_schraeg(c=INK):
    return f'<g transform="matrix(1 0 -.2126 1 5.1 0)">' + feld_one(c, both=True) + "</g>"


def feld_one(c=INK, both=False):
    out = (f'<rect x="5" y="3" width="7" height="42" fill="{c}"/><rect x="36" y="3" width="7" height="42" fill="{c}"/>'
           f'<rect x="12" y="21.5" width="24" height="5" fill="{c}"/>'
           f'<path d="M14.5 3A9.5 9.5 0 0 0 33.5 3" fill="none" stroke="{c}" stroke-width="3"/>')
    if both:
        out += f'<path d="M14.5 45A9.5 9.5 0 0 1 33.5 45" fill="none" stroke="{c}" stroke-width="3"/>'
    return out


def feld_einbogen(c=INK):
    """Feld with one goal area only and the shot spot: half a court, our half."""
    return feld_one(c, both=False)


# ---------- pixel favicons: drawn on the pixel grid of each size, not scaled ----------
def _grid(n):
    return [["."] * n for _ in range(n)]


def _on(g, x, y):
    if 0 <= y < len(g) and 0 <= x < len(g):
        g[y][x] = "#"


def pix_h(n, cut=False, dot=True):
    """H im Lauf on an n-pixel grid. 16: stems 3 px, slant one pixel per 3 rows; 32: stems 6 px, one per 5 rows."""
    g = _grid(n)
    if n == 16:
        top, bot, sw, step, x0, gap = 2, 13, 3, 3, 1, 8
    else:
        top, bot, sw, step, x0, gap = 3, 28, 6, 5, 2, 15
    for y in range(top, bot + 1):
        x = x0 + (bot - y) // step
        for st in (0, gap):
            for i in range(sw):
                if cut and ((y == top and i >= sw - (1 if n == 16 else 2)) or (y == bot and i < (1 if n == 16 else 2))):
                    continue
                if cut and n == 32 and ((y == top + 1 and i >= sw - 1) or (y == bot - 1 and i < 1)):
                    continue
                _on(g, x + st + i, y)
    if n == 16:
        run = [(5, 10), (5, 9), (6, 9), (6, 8)]
        dt = [(7, 7), (8, 7), (7, 8), (8, 8)] if dot else [(7, 8), (8, 8)]
    else:
        run = [(9, 22), (10, 22), (9, 21), (10, 21), (11, 21), (11, 20), (12, 20), (12, 19), (13, 19), (13, 18)]
        dt = [(x, y) for y in range(11, 21) for x in range(11, 18) if (x - 14.5) ** 2 + (y - 15.5) ** 2 <= 9.6] if dot else [(14, 19), (15, 19), (16, 19)]
    for p in run + dt:
        _on(g, *p)
    return ["".join(r) for r in g]


def pix_feld(n):
    """Feld, slanted, on the pixel grid."""
    g = _grid(n)
    if n == 16:
        top, bot, sw, step, x0, gap, mid, arc = 1, 14, 2, 4, 1, 10, (7, 8), [(4, 2), (5, 3), (6, 4), (7, 4), (8, 4), (9, 3), (10, 2)]
    else:
        top, bot, sw, step, x0, gap, mid, arc = 2, 29, 4, 7, 2, 21, (14, 17), []
        for x in range(9, 25):
            y = 2 + int(round(((x - 16.5) / 7.5) ** 2 * -5.5 + 7))
            for t in range(2):
                arc.append((x + 1, y + t))
    for y in range(top, bot + 1):
        x = x0 + (bot - y) // step
        for st in (0, gap):
            for i in range(sw):
                _on(g, x + st + i, y)
        if mid[0] <= y <= mid[1]:
            for i in range(sw, gap):
                _on(g, x + i, y)
    for p in arc:
        _on(g, *p)
    return ["".join(r) for r in g]


PIX = {"g16": pix_h(16, cut=True), "g32": pix_h(32, cut=True), "b16": pix_h(16), "b32": pix_h(32),
       "feld16": pix_feld(16), "feld32": pix_feld(32)}


def pixsvg(rows, c=INK, bg=None):
    n = len(rows)
    out = f'<rect width="{n}" height="{n}" fill="{bg}"/>' if bg else ""
    d = ""
    for y, row in enumerate(rows):
        x = 0
        while x < len(row):
            if row[x] == "#":
                x0 = x
                while x < len(row) and row[x] == "#":
                    x += 1
                d += f"M{x0} {y}h{x - x0}v1h{x0 - x}z"
            else:
                x += 1
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {n} {n}" shape-rendering="crispEdges">{out}<path d="{d}" fill="{c}"/></svg>'


# ---------- the custom wordmark ----------
def word(s, font, size, x=0, y=0, track=0.0, pairs=None, dot_i=False, space=1.0):
    """Like text(), with per-pair spacing (pairs: {index: dx in em}), word space factor and the i dot
    replaced by the round shot spot of the mark."""
    tt, hf = _font(font)
    upm = tt["head"].unitsPerEm
    buf = hb.Buffer(); buf.add_str(s); buf.guess_segment_properties()
    hb.shape(hf, buf, {"kern": True})
    gs = tt.getGlyphSet(); order = tt.getGlyphOrder(); cmap = tt.getBestCmap()
    k = size / upm
    pen = SVGPathPen(gs, lambda v: f"{v:.2f}".rstrip("0").rstrip("."))
    extra = ""
    cx = 0
    xh = tt["OS/2"].sxHeight * k
    for i, (info, pos) in enumerate(zip(buf.glyph_infos, buf.glyph_positions)):
        ch = s[info.cluster]
        name = order[info.codepoint]
        px = x + (cx + pos.x_offset) * k
        if dot_i and ch == "i":
            name = cmap.get(0x0131, name)  # dotless i
            # the dot: a circle above the stem, shifted by the slant
            stem_x = px + gs[name].width * k * 0.5
            extra += f'<circle cx="{stem_x + xh * 0.42 * 0.21:.2f}" cy="{y - xh - size * 0.13:.2f}" r="{size * 0.085:.2f}"/>'
        gs[name].draw(TransformPen(pen, (k, 0, 0, -k, px, y - pos.y_offset * k)))
        adv = pos.x_advance
        if ch == " ":
            adv *= space
        cx += adv + track * upm + (pairs or {}).get(i, 0) * upm
    w = (cx - track * upm) * k
    return pen.getCommands(), w, extra


def wordmark(case="title", c=INK, two=False, size=30):
    font = "Kanit-ExtraBoldItalic"
    a, b = ("Handball", "Intelligence") if case == "title" else ("handball", "intelligence")
    # optical fixes: the double l a touch apart, the word space smaller, tracking slightly tight
    def pairs(t):
        out = {}
        for i in range(len(t) - 1):
            if t[i:i + 2] == "ll":
                out[i] = 0.035
        return out
    if not two:
        s = a + " " + b
        d, w, ex = word(s, font, size, y=size, track=-0.006, pairs=pairs(s), dot_i=True, space=0.7)
        return svg(f'<g fill="{c}"><path d="{d}"/>{ex}</g>', w + 4, size * 1.3)
    # two lines: «Handball» scaled up so both lines end together
    _, wb, _ = word(b, font, size, track=-0.006, pairs=pairs(b), dot_i=True)
    _, wa, _ = word(a, font, size, track=-0.006, pairs=pairs(a), dot_i=True)
    sa = size * wb / wa
    d1, _, e1 = word(a, font, sa, y=sa * 0.78, track=-0.006, pairs=pairs(a), dot_i=True)
    d2, _, e2 = word(b, font, size, x=-size * 0.06, y=sa * 0.78 + size * 1.02, track=-0.006, pairs=pairs(b), dot_i=True)
    return svg(f'<g fill="{c}"><path d="{d1} {d2}"/>{e1}{e2}</g>', wb + 4, sa * 0.78 + size * 1.02 + size * 0.3)


def wordmark_plain(case="title", c=INK, size=30):
    s = "Handball Intelligence" if case == "title" else "handball intelligence"
    d, w, _ = text(s, "Kanit-ExtraBoldItalic", size, y=size)
    return svg(f'<path d="{d}" fill="{c}"/>', w + 4, size * 1.3)
