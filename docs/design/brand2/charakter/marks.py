"""Six character marks for Handball Intelligence, drawn as SVG in a 512 x 512 box.
Every mark is a function (palette) -> svg inner markup. Text is turned into outlines with fontTools,
so the SVG files need no font."""
import math, pathlib
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen

HERE = pathlib.Path(__file__).parent
_fonts = {}

def text_path(font, text, size, x=0, y=0, track=0, anchor="start"):
    """Outline text: returns (path d, width). y is the baseline."""
    if font not in _fonts:
        _fonts[font] = TTFont(HERE / "fonts" / f"{font}.ttf")
    f = _fonts[font]
    gs, cmap, hmtx = f.getGlyphSet(), f.getBestCmap(), f["hmtx"]
    upm = f["head"].unitsPerEm
    k = size / upm
    names = [cmap.get(ord(c)) for c in text]
    width = sum(hmtx[n][0] * k + track for n in names if n) - track
    if anchor == "middle": x -= width / 2
    if anchor == "end": x -= width
    pen = SVGPathPen(gs)
    cx = x
    for n in names:
        if not n: continue
        tp = TransformPen(pen, (k, 0, 0, -k, cx, y))
        gs[n].draw(tp)
        cx += hmtx[n][0] * k + track
    return pen.getCommands(), width

def P(d, fill, extra=""):
    return f'<path d="{d}" fill="{fill}" {extra}/>'

def lines(pts):
    return "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts)

# ---------- a cartoon hand built from fat strokes, wrist at origin, pointing up ----------
def hand(c, ink, x, y, rot=0, s=1.0, spread=1.0, outline=10, curl=None, thumb=1):
    curl = curl or [0, 0, 0, 0]
    fingers = [(-30, -64, 58, -10), (-10, -70, 70, -3), (11, -70, 68, 4), (30, -64, 54, 12)]
    parts = []
    palm = "M-34 -2 L34 -2 L38 -66 L-38 -66 Z"
    def seg(px, py, L, ang, cu):
        a = math.radians(ang * spread)
        ex, ey = px + math.sin(a) * L, py - math.cos(a) * L
        if cu:  # bend the last third forward
            mx, my = px + math.sin(a) * L * 0.6, py - math.cos(a) * L * 0.6
            b = a + math.radians(cu)
            ex, ey = mx + math.sin(b) * L * 0.45, my - math.cos(b) * L * 0.45
            return f"M{px} {py} L{mx:.1f} {my:.1f} L{ex:.1f} {ey:.1f}"
        return f"M{px} {py} L{ex:.1f} {ey:.1f}"
    strokes = [seg(px, py, L, ang, curl[i]) for i, (px, py, L, ang) in enumerate(fingers)]
    if thumb:
        strokes.append(seg(-34, -18, 50, -58 * thumb, 0))
    def layer(col, extra):
        g = f'<path d="{palm}" fill="{col}" stroke="{col}" stroke-width="{26 + extra}" stroke-linejoin="round"/>'
        for d in strokes:
            g += f'<path d="{d}" fill="none" stroke="{col}" stroke-width="{24 + extra}" stroke-linecap="round" stroke-linejoin="round"/>'
        return g
    inner = (layer(ink, outline * 2) if outline else "") + layer(c, 0)
    return f'<g transform="translate({x} {y}) rotate({rot}) scale({s})">{inner}</g>'

def ball(cx, cy, r, fill, ink, w=10):
    """A handball: circle with three seams."""
    return (f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}" stroke="{ink}" stroke-width="{w}"/>'
            f'<path d="M{cx - r * .96} {cy - r * .22} Q{cx} {cy - r * .62} {cx + r * .96} {cy - r * .22}" fill="none" stroke="{ink}" stroke-width="{w * .8}" stroke-linecap="round"/>'
            f'<path d="M{cx - r * .2} {cy - r * .97} Q{cx + r * .5} {cy} {cx - r * .2} {cy + r * .97}" fill="none" stroke="{ink}" stroke-width="{w * .8}" stroke-linecap="round"/>'
            f'<path d="M{cx - r * .9} {cy + r * .42} Q{cx - r * .45} {cy + r * .1} {cx - r * .06} {cy + r * .5}" fill="none" stroke="{ink}" stroke-width="{w * .8}" stroke-linecap="round"/>')

# ================= 1 Fuchs =================
def fuchs(p):
    o, cr, ink, band, band2 = p["a"], p["b"], p["ink"], p["c"], p["d"]
    s = ""
    s += P("M112 52 L80 250 L232 190 Z", o) + P("M400 52 L432 250 L280 190 Z", o)
    s += P("M120 100 L102 222 L192 190 Z", ink) + P("M392 100 L410 222 L320 190 Z", ink)
    head = "M256 146 C336 146 408 172 440 220 L494 342 L404 352 L350 392 L256 480 L162 392 L108 352 L18 342 L72 220 C104 172 176 146 256 146 Z"
    s += P(head, o)
    mask = "M18 342 L126 318 C170 312 204 342 256 350 C308 342 342 312 386 318 L494 342 L404 352 L350 392 L256 480 L162 392 L108 352 Z"
    s += P(mask, cr)
    s += P("M66 230 C140 198 372 198 446 230 L458 276 C384 244 128 244 54 276 Z", band)
    s += P("M62 252 C136 224 376 224 450 252 L452 262 C378 234 134 234 60 262 Z", band2)
    s += ball(256, 238, 30, cr, ink, 7)
    # brows: one up, one down; he knows something
    s += f'<path d="M150 290 L226 300" stroke="{p.get("eye", ink)}" stroke-width="13" stroke-linecap="round"/><path d="M290 286 C312 270 340 268 364 278" fill="none" stroke="{p.get("eye", ink)}" stroke-width="13" stroke-linecap="round"/>'
    s += P("M156 318 C176 300 212 300 230 316 C214 334 178 334 156 318 Z", p.get("eye", ink))
    s += P("M356 318 C336 300 300 300 282 316 C298 334 334 334 356 318 Z", p.get("eye", ink))
    s += f'<circle cx="206" cy="313" r="6" fill="{p.get("hl", "#fff")}"/><circle cx="306" cy="313" r="6" fill="{p.get("hl", "#fff")}"/>'
    s += P("M224 414 C224 396 288 396 288 414 C288 432 272 444 256 448 C240 444 224 432 224 414 Z", ink)
    s += f'<path d="M256 448 L256 456 C268 466 284 464 296 450" fill="none" stroke="{ink}" stroke-width="9" stroke-linecap="round" stroke-linejoin="round"/>'
    return s

# ================= 2 Murmeli: the marmot on watch, with the ball =================
def murmeli(p):
    fur, belly, ink, dark = p["a"], p["c"], p["ink"], p["d"]
    w = 12
    s = ""
    # body: standing upright like on watch
    s += P("M256 168 C352 168 392 246 396 330 C400 420 360 492 256 492 C152 492 112 420 116 330 C120 246 160 168 256 168 Z", fur, f'stroke="{ink}" stroke-width="{w}"')
    s += P("M256 262 C318 262 340 320 340 380 C340 442 306 476 256 476 C206 476 172 442 172 380 C172 320 194 262 256 262 Z", belly)
    # feet
    s += P("M166 474 C150 490 160 506 196 504 C222 502 228 488 214 474 Z", dark, f'stroke="{ink}" stroke-width="{w}"')
    s += P("M346 474 C362 490 352 506 316 504 C290 502 284 488 298 474 Z", dark, f'stroke="{ink}" stroke-width="{w}"')
    # head
    s += P("M256 58 C350 58 398 106 398 168 C398 230 336 268 256 268 C176 268 114 230 114 168 C114 106 162 58 256 58 Z", fur, f'stroke="{ink}" stroke-width="{w}"')
    s += f'<ellipse cx="128" cy="118" rx="22" ry="18" fill="{fur}" stroke="{ink}" stroke-width="{w}"/><ellipse cx="384" cy="118" rx="22" ry="18" fill="{fur}" stroke="{ink}" stroke-width="{w}"/>'
    s += f'<ellipse cx="128" cy="118" rx="9" ry="7" fill="{dark}"/><ellipse cx="384" cy="118" rx="9" ry="7" fill="{dark}"/>'
    s += P("M256 66 C344 66 390 110 390 168 C390 224 332 260 256 260 C180 260 122 224 122 168 C122 110 168 66 256 66 Z", fur)
    s += P("M256 66 C330 66 372 96 382 136 C340 116 300 118 256 132 C212 118 172 116 130 136 C140 96 182 66 256 66 Z", dark)
    # muzzle, nose, the two front teeth
    s += P("M256 158 C282 150 340 164 344 202 C348 240 296 252 256 244 C216 252 164 240 168 202 C172 164 230 150 256 158 Z", belly)
    s += P("M234 170 C234 158 278 158 278 170 C278 184 266 192 256 192 C246 192 234 184 234 170 Z", ink)
    s += f'<path d="M256 192 L256 206" stroke="{ink}" stroke-width="8"/>'
    s += f'<rect x="240" y="206" width="32" height="30" rx="5" fill="#fff" stroke="{ink}" stroke-width="7"/><path d="M256 208 L256 234" stroke="{ink}" stroke-width="5"/>'
    # eyes: wide awake
    s += f'<circle cx="190" cy="150" r="16" fill="{p.get("eye", ink)}"/><circle cx="322" cy="150" r="16" fill="{p.get("eye", ink)}"/><circle cx="196" cy="144" r="5.5" fill="#fff"/><circle cx="328" cy="144" r="5.5" fill="#fff"/>'
    # the whistle: three sound marks
    s += f'<path d="M362 214 C378 206 386 194 388 180 M380 238 C404 228 418 208 420 184 M398 262 C432 250 452 222 454 190" fill="none" stroke="{ink}" stroke-width="11" stroke-linecap="round"/>'
    # the ball held against the chest, paws over it
    s += ball(256, 350, 76, p["b"], ink, 11)
    s += P("M168 318 C146 350 160 384 198 376 C214 372 218 352 206 336 Z", fur, f'stroke="{ink}" stroke-width="{w}"')
    s += P("M344 318 C366 350 352 384 314 376 C298 372 294 352 306 336 Z", fur, f'stroke="{ink}" stroke-width="{w}"')
    return s

# ================= 3 Abklatschen: high five =================
def abklatschen(p):
    s = ""
    # motion marks
    for a in (-60, -30, 0, 30, 60):
        r = math.radians(a)
        x1, y1 = 256 + math.sin(r) * 96, 230 - math.cos(r) * 110
        x2, y2 = 256 + math.sin(r) * 136, 230 - math.cos(r) * 150
        s += f'<path d="M{x1:.0f} {y1:.0f} L{x2:.0f} {y2:.0f}" stroke="{p["ink"]}" stroke-width="16" stroke-linecap="round"/>'
    s += hand(p["a"], p["ink"], 140, 540, rot=24, s=1.86, spread=1.15, outline=7)
    s += hand(p["b"], p["ink"], 372, 540, rot=-24, s=1.86, spread=1.15, outline=7, thumb=-1)
    return s

# ================= 4 Wimpel =================
def wimpel(p):
    s = ""
    s += f'<rect x="70" y="40" width="372" height="18" rx="9" fill="{p["ink"]}"/>'
    s += f'<path d="M96 40 C96 6 132 0 142 40 M416 40 C416 6 380 0 370 40" fill="none" stroke="{p["ink"]}" stroke-width="8"/>'
    # fringe
    fr = ""
    for i in range(16):
        t = i / 15
        x = 90 + (422 - 90) * t
        fr += f'<path d="M{x:.0f} 56 l0 0" stroke="{p["c"]}" stroke-width="8" stroke-linecap="round"/>'
    s += fr
    s += P("M90 58 L422 58 L422 250 L256 470 L90 250 Z", p["a"])
    s += f'<path d="M256 470 L256 486" stroke="{p["c"]}" stroke-width="6"/>' + P("M244 484 L268 484 L274 512 L238 512 Z", p["c"])
    s += P("M110 78 L402 78 L402 244 L256 438 L110 244 Z", "none", f'stroke="{p["c"]}" stroke-width="6" stroke-dasharray="14 9"')
    if p.get("small"):
        s += ball(256, 196, 92, p["b"], p["ink"], 14)
        return s
    d, w = text_path("alfaslabone", "HANDBALL", 40, 256, 136, track=2, anchor="middle")
    s += P(d, p["b"])
    s += ball(256, 222, 54, p["b"], p["ink"], 9)
    d, w = text_path("alfaslabone", "INTELLIGENCE", 22, 256, 318, track=1, anchor="middle")
    s += P(d, p["b"])
    d, w = text_path("alfaslabone", "SEIT 2026", 16, 256, 362, track=2, anchor="middle")
    s += P(d, p["c"])
    return s

# ================= 5 hi =================
def hi(p):
    d, w = text_path("fredoka", "hı", 400, 236, 430, anchor="middle")
    s = '<g transform="rotate(-6 256 300)">' + P(d, p["a"])
    s += ball(372, 120, 50, p["b"], p["ink"], 10)
    s += f'<path d="M302 94 L244 78 M298 130 L232 132 M310 164 L264 182" stroke="{p["ink"]}" stroke-width="13" stroke-linecap="round"/></g>'
    return s

# ================= 6 Abdruck: a resin fingerprint =================
def abdruck(p):
    import random
    rnd = random.Random(7)
    c, w = p["a"], 11
    s = '<defs><clipPath id="fp"><path d="M256 40 C392 40 452 150 452 270 C452 404 366 488 256 488 C146 488 60 404 60 270 C60 150 120 40 256 40 Z"/></clipPath></defs><g clip-path="url(#fp)">'
    cx, cy = 248, 262
    for i in range(1, 14):
        rx, ry = 12 + i * 18.5, 20 + i * 22
        gap = rnd.uniform(0, 6.28)
        pts = []
        for k in range(73):
            a2 = k / 72 * 6.283
            if abs(((a2 - gap + 3.14) % 6.283) - 3.14) < 0.32: pts.append(None); continue
            wob = 1 + 0.018 * math.sin(a2 * 4 + i)
            pts.append((cx + math.cos(a2) * rx * wob, cy + math.sin(a2) * ry * wob * (0.82 if math.sin(a2) > 0 else 1) - (i * 3)))
        d, pen = "", False
        for q in pts:
            if q is None: pen = False; continue
            d += ("L" if pen else "M") + f"{q[0]:.1f} {q[1]:.1f} "; pen = True
        s += f'<path d="{d}" fill="none" stroke="{c}" stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round"/>'
    s += "</g>"
    s += ball(cx, cy - 4, 24, p["b"], p["ink"], 6)
    return s

MARKS = {
    "fuchs": (fuchs, {"a": "#ec6a1c", "b": "#fff6ea", "ink": "#22192b", "c": "#1d3fa8", "d": "#fff6ea"}),
    "murmeli": (murmeli, {"a": "#9a6235", "b": "#ffd23f", "c": "#f2dcb8", "d": "#4a2e1c", "ink": "#24170f"}),
    "abklatschen": (abklatschen, {"a": "#ff5a3c", "b": "#2bb3a3", "ink": "#1b1a2e"}),
    "wimpel": (wimpel, {"a": "#8c1d40", "b": "#fff6e8", "c": "#f2b84b", "ink": "#2a1620"}),
    "hi": (hi, {"a": "#ff5a3c", "b": "#fff", "ink": "#1b1a2e"}),
    "abdruck": (abdruck, {"a": "#b5651d", "b": "#ffd23f", "ink": "#2a1a0e"}),
}

def svg(name, inner=None, size=512, bg=None):
    f, p = MARKS[name]
    inner = inner if inner is not None else f(p)
    b = f'<rect width="512" height="512" fill="{bg}"/>' if bg else ""
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="{size}" height="{size}">{b}{inner}</svg>'

if __name__ == "__main__":
    import sys
    out = pathlib.Path(sys.argv[1])
    cells = "".join(f'<div><p>{n}</p>{svg(n, bg="#f4f1ec", size=380)}<div class="sm">{svg(n, size=64)}{svg(n, size=32)}</div></div>' for n in MARKS)
    out.write_text('<body style="margin:0;padding:20px;background:#ddd;font:16px sans-serif"><style>body>div{display:grid;grid-template-columns:repeat(3,400px);gap:16px}.sm{display:flex;gap:12px;align-items:center;margin-top:6px}</style><div>' + cells + "</div></body>")
