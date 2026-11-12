"""Builds the presentation (index.html) and the logo files (logos/*.svg) for the six character marks.
Run: python3 build.py"""
import pathlib, base64
from marks import MARKS, text_path, P

HERE = pathlib.Path(__file__).parent
LOGOS = HERE / "logos"
LOGOS.mkdir(exist_ok=True)

INK = "#1b1a2e"
IDEAS = [
    dict(key="fuchs", name="Fuchs", font="bowlbyone", case="Handball|Intelligence", fs=124, bg="#fff6ea", icon="#ec6a1c", word="#22192b",
         sieht="Ein Fuchskopf mit Stirnband, auf dem ein Handball sitzt, und einer hochgezogenen Braue.",
         story="Der Fuchs ist schlau, frech und schnell, und er lebt in jedem Wald am Zürichsee. Intelligenz ohne Gehirn und ohne Funkeln: ein Spieler, der schon weiss, wohin der Ball geht. Die Braue sagt: Ich hab da was gesehen.",
         mono={"a": INK, "b": "#fff", "ink": INK, "c": "#fff", "d": INK, "eye": "#fff", "hl": INK}, scene="jacke",
         colors=[("Fuchsrot", "#ec6a1c"), ("Rahm", "#fff6ea"), ("Nachtblau", "#1d3fa8"), ("Tinte", "#22192b")]),
    dict(key="murmeli", name="Murmeli", font="barlowcondensed", case="HANDBALL|INTELLIGENCE", fs=136, bg="#f6ecdc", icon="#9a6235", word="#24170f",
         sieht="Ein Murmeltier steht aufrecht, hält einen Handball und pfeift.",
         story="Das Murmeltier steht Wache und pfeift, wenn es etwas sieht. Genau das tut die App: Sie schaut das ganze Spiel und pfeift bei den drei Dingen, die zählen. Schweizerisch, ohne Kreuz und ohne Kitsch, und ein Plüschtier, das man in die Sporttasche steckt.",
         mono={"a": INK, "b": "#fff", "c": "#fff", "d": INK, "ink": INK, "eye": "#fff"}, scene="flasche",
         colors=[("Murmelbraun", "#9a6235"), ("Bauch", "#f2dcb8"), ("Ballgelb", "#ffd23f"), ("Erde", "#24170f")]),
    dict(key="abklatschen", name="Abklatschen", font="archivoblack", case="Handball|Intelligence", fs=118, bg="#e9f5f2", icon="#1b1a2e", word="#1b1a2e",
         sieht="Zwei Hände klatschen sich ab, über ihnen knallt es.",
         story="Handball ist der Sport der Hand, und nach jedem Tor, jedem Wechsel und jedem Schlusspfiff klatscht man ab. Zwei Farben, zwei Menschen: die Trainerin und ihr Team, oder die App und die Trainerin. Es geht ums Danach, um das, was man zusammen gemerkt hat.",
         mono={"a": INK, "b": "#fff", "ink": INK}, scene="banner",
         colors=[("Korall", "#ff5a3c"), ("Türkis", "#2bb3a3"), ("Tinte", "#1b1a2e"), ("Weiss", "#ffffff")]),
    dict(key="wimpel", name="Wimpel", font="alfaslabone", case="Handball|Intelligence", fs=104, bg="#f6efe4", icon="#8c1d40", word="#2a1620",
         sieht="Ein Vereinswimpel mit Ball, Kordel und Quaste, wie er vor dem Spiel getauscht wird.",
         story="Vor jedem Spiel tauschen die Captains Wimpel. Er hängt in jedem Clubhaus, neben den Mannschaftsfotos. Die App sieht damit aus wie ein Verein, nicht wie eine Firma: mit genähter Kante, einem Gründungsjahr und dem Ball in der Mitte.",
         mono={"a": INK, "b": "#fff", "c": "#fff", "ink": INK}, scene="jacke",
         colors=[("Weinrot", "#8c1d40"), ("Gold", "#f2b84b"), ("Rahm", "#fff6e8"), ("Tinte", "#2a1620")]),
    dict(key="hi", name="hi", font="fredoka", case="handball|intelligence", fs=136, bg="#fff3ec", icon="#ff5a3c", word="#1b1a2e",
         sieht="Das Wort hi, schräg und in Bewegung; der Punkt auf dem i ist ein Handball im Flug.",
         story="Handball Intelligence wird kurz zu hi, und hi ist ein Gruss. So meldet sich die App am Sonntag: hi, drei Dinge vom Samstag. Der Ball als i-Punkt fliegt gerade ins Wort hinein. Freundlich, schnell, und es passt auf jeden Knopf.",
         mono={"a": INK, "b": "#fff", "ink": INK}, scene="handy",
         colors=[("Korall", "#ff5a3c"), ("Pfirsich", "#fff3ec"), ("Tinte", "#1b1a2e"), ("Weiss", "#ffffff")]),
    dict(key="abdruck", name="Harzabdruck", font="spacegrotesk", case="Handball|Intelligence", fs=116, bg="#fbf3e6", icon="#2a1a0e", word="#2a1a0e",
         sieht="Ein Fingerabdruck in Harzbraun, in seiner Mitte ein Handball.",
         story="Wer Handball spielt, hat Harz an den Fingern und hinterlässt Abdrücke auf dem Ball, dem Trikot, dem Handy. Jedes Team spielt anders, so wie jeder Finger anders ist. Die App liest diesen Abdruck. Persönlich und erwachsen, ein Zeichen ohne Witz.",
         mono={"a": INK, "b": "#fff", "ink": INK}, scene="flasche",
         colors=[("Harz", "#b5651d"), ("Ballgelb", "#ffd23f"), ("Bernstein", "#fbf3e6"), ("Tinte", "#2a1a0e")]),
]
RANK = ["fuchs", "abklatschen", "hi", "murmeli", "wimpel", "abdruck"]
WHY = {
    "fuchs": "Das stärkste Zeichen: sofort lesbar, mit Haltung und Witz, und es trägt auf allen Grössen, auch bei 32 px. Es erzählt «schlau» ohne KI-Klischee. Risiko: Füchse sind als Maskottchen verbreitet; die Braue und das Stirnband mit Ball müssen bleiben, sonst ist es irgendein Fuchs.",
    "abklatschen": "Am meisten Herz und am klarsten Handball: die Hand, der Moment danach. Als App-Icon kräftig. Risiko: Abklatschende Hände gibt es als Emoji; die zwei Farben und die harte Kontur müssen es zur Marke machen.",
    "hi": "Das freundlichste und praktischste Zeichen; es ist zugleich Kurzname und Gruss. Bei kleinen Grössen bleibt nur das hi, der Ball verschwindet unter 32 px. Risiko: Es ist eher Wortmarke als Bild, und «hi» klingt nach Chat-App.",
    "murmeli": "Das liebste Zeichen, schweizerisch und mit Geschichte (es pfeift, wenn es etwas sieht). Für Junioren und Merchandise stark. Risiko: Es ist niedlich und weniger sportlich; neben Erwachsenen-Teams kann es zu kindlich wirken.",
    "wimpel": "Am meisten Verein, sofort vertraut. Risiko: Es sieht aus wie ein echter Vereinswimpel, also wie viele Vereine, und es trägt nur gross; als Icon bleibt ein Wimpel mit Ball.",
    "abdruck": "Erwachsen und eigen, die Idee (Harz, jedes Team anders) ist gut. Aber der Fingerabdruck erinnert an Sicherheit und Ausweise, und bei 32 px wird er braun gemustert. Das schwächste Zeichen der sechs.",
}

def mark_svg(key, pal=None, size=None, extra=None):
    f, p = MARKS[key]
    q = dict(p); q.update(pal or {}); q.update(extra or {})
    s = f(q)
    sz = f' width="{size}" height="{size}"' if size else ""
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512"{sz}>{s}</svg>', s

def lockup(idea, pal=None, color=None, stacked=False):
    """mark + wordmark, text as outlines"""
    _, inner = mark_svg(idea["key"], pal)
    col = color or idea["word"]
    l1, l2 = idea["case"].split("|")
    fs = idea["fs"]
    ital = idea["font"] == "barlowcondensed"
    if stacked:
        d1, w1 = text_path(idea["font"], l1, fs, 256, 600, anchor="middle")
        d2, w2 = text_path(idea["font"], l2, fs, 256, 600 + fs * 1.0, anchor="middle")
        W = max(512, w1 + 40, w2 + 40)
        off = (W - 512) / 2
        H = 600 + fs * 1.25
        return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H:.0f}"><g transform="translate({off:.0f} 0)">{inner}{P(d1, col)}{P(d2, col)}</g></svg>'
    d1, w1 = text_path(idea["font"], l1, fs, 560, 256 - fs * 0.12, anchor="start")
    d2, w2 = text_path(idea["font"], l2, fs, 560, 256 + fs * 0.88, anchor="start")
    W = 560 + max(w1, w2) + 20
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} 512">{inner}{P(d1, col)}{P(d2, col)}</svg>'

def app_icon(idea, size=None):
    _, inner = mark_svg(idea["key"], extra={"small": 1} if idea["key"] == "wimpel" else None)
    bg = idea["icon"] if idea["key"] not in ("murmeli",) else idea["bg"]
    if idea["key"] in ("fuchs",): bg = "#1d3fa8"
    if idea["key"] in ("hi", "abdruck"): bg = idea["bg"]
    sz = f' width="{size}" height="{size}"' if size else ""
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512"{sz}><rect width="512" height="512" rx="112" fill="{bg}"/><g transform="translate(51 51) scale(.8)">{inner}</g></svg>'

# ---------- situations ----------
def scene(idea):
    k = idea["scene"]
    mk = mark_svg(idea["key"], extra={"small": 1} if idea["key"] == "wimpel" else None)[1]
    if k == "jacke":
        lk = lockup(idea, color="#fff", pal=None)
        return f'''<svg viewBox="0 0 560 360" role="img" aria-label="Trainerjacke mit dem Zeichen auf der Brust">
<rect width="560" height="360" fill="#d9d4cc"/>
<path d="M120 360 L140 120 C150 80 200 60 240 52 L280 90 L320 52 C360 60 410 80 420 120 L440 360 Z" fill="#1f2433"/>
<path d="M240 52 L280 90 L320 52 L306 46 L280 70 L254 46 Z" fill="#141826"/>
<path d="M280 90 L280 360" stroke="#9aa0ab" stroke-width="3" stroke-dasharray="4 3"/>
<path d="M140 120 L60 360 L120 360 Z M420 120 L500 360 L440 360 Z" fill="#181c29"/>
<path d="M150 300 L262 300 M298 300 L410 300" stroke="#2c3346" stroke-width="3"/>
<g transform="translate(318 132) scale(.16)">{mk}</g>
<text x="318" y="236" style="font:700 11px sans-serif;fill:#e8e6e1;letter-spacing:.5px">Herren 1 · Trainerin</text>
</svg>'''
    if k == "banner":
        lk = lockup(idea)
        return f'''<svg viewBox="0 0 560 360" role="img" aria-label="Banner an der Hallenwand">
<rect width="560" height="360" fill="#c9cfd6"/><rect y="250" width="560" height="110" fill="#c4935f"/>
<path d="M0 250 H560" stroke="#8b6a45" stroke-width="4"/><path d="M0 300 L560 280" stroke="#fff" stroke-width="5" opacity=".8"/>
<rect x="40" y="60" width="480" height="130" fill="#fff" stroke="#1b1a2e" stroke-width="3"/>
<circle cx="52" cy="72" r="5" fill="#9aa0ab"/><circle cx="508" cy="72" r="5" fill="#9aa0ab"/><circle cx="52" cy="178" r="5" fill="#9aa0ab"/><circle cx="508" cy="178" r="5" fill="#9aa0ab"/>
<g transform="translate(70 76)"><svg width="420" height="98" viewBox="{lk.split('viewBox="')[1].split('"')[0]}">{lk.split('">', 1)[1].rsplit('</svg>', 1)[0]}</svg></g>
<rect x="430" y="200" width="18" height="50" fill="#e04b2a"/><rect x="430" y="200" width="70" height="50" fill="none" stroke="#e04b2a" stroke-width="6"/>
</svg>'''
    if k == "flasche":
        return f'''<svg viewBox="0 0 560 360" role="img" aria-label="Trinkflasche mit Kleber">
<rect width="560" height="360" fill="#e6e1d8"/><rect y="300" width="560" height="60" fill="#cfc7ba"/>
<rect x="246" y="30" width="68" height="40" rx="8" fill="#2a2d36"/><rect x="262" y="12" width="36" height="22" rx="6" fill="#2a2d36"/>
<path d="M226 76 C226 66 334 66 334 76 L344 110 L344 300 C344 316 216 316 216 300 L216 110 Z" fill="#3b7fbf"/>
<path d="M226 76 C226 66 334 66 334 76 L344 110 L216 110 Z" fill="#2f6ba6"/>
<path d="M236 130 L236 290" stroke="#ffffff55" stroke-width="10" stroke-linecap="round"/>
<circle cx="280" cy="206" r="58" fill="#fff" stroke="#00000022" stroke-width="2"/>
<g transform="translate(232 158) scale(.1875)">{mk}</g>
</svg>'''
    # handy
    ic = app_icon(idea).replace('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">', '<svg viewBox="0 0 512 512" width="54" height="54">')
    grey = ["#3c8f6e", "#e2b33c", "#5b6ee1", "#d9534f", "#8e6bd6", "#2aa3c4", "#f08a3c", "#6b7480", "#47a85b", "#c4568f", "#3b6fb6"]
    cells, k2 = "", 0
    for r in range(4):
        for c in range(4):
            x, y = 196 + c * 72, 70 + r * 84
            if (r, c) == (1, 2):
                cells += f'<g transform="translate({x} {y})">{ic}</g><text x="{x + 27}" y="{y + 70}" text-anchor="middle" style="font:500 10px sans-serif;fill:#fff">Handball Int…</text>'
            else:
                col = grey[k2 % len(grey)]; k2 += 1
                cells += f'<rect x="{x}" y="{y}" width="54" height="54" rx="12" fill="{col}" opacity=".85"/><rect x="{x + 6}" y="{y + 62}" width="42" height="6" rx="3" fill="#fff" opacity=".5"/>'
    return f'''<svg viewBox="0 0 560 360" role="img" aria-label="Handy-Startbildschirm mit dem App-Icon">
<rect width="560" height="360" fill="#ddd8d0"/>
<rect x="170" y="20" width="310" height="420" rx="40" fill="#111"/><rect x="180" y="30" width="290" height="400" rx="32" fill="#36507a"/>
<rect x="180" y="30" width="290" height="400" rx="32" fill="url(#g)"/><defs><linearGradient id="g" x2="0" y2="1"><stop offset="0" stop-color="#4a6b9a"/><stop offset="1" stop-color="#2a3d5c"/></linearGradient></defs>
<text x="325" y="56" text-anchor="middle" style="font:600 13px sans-serif;fill:#fff">So 9:41</text>
{cells}
</svg>'''

def mono(idea, color=INK, paper="#fff"):
    pal = {k: (color if v == INK else paper if v == "#fff" else v) for k, v in idea["mono"].items()}
    return mark_svg(idea["key"], pal, extra={"small": 1} if idea["key"] == "wimpel" else None)[0]

def fontface():
    css = ""
    for fam, file in [("Bricolage", None)]:
        pass
    return css

boards = ""
for i, idea in enumerate(IDEAS):
    k = idea["key"]
    big = mark_svg(k)[0]
    lk = lockup(idea)
    lk_st = lockup(idea, stacked=True)
    icon = app_icon(idea)
    mn = mono(idea)
    mn_inv = mono(idea, color="#fff", paper=INK)
    for name, svg in [("zeichen", big), ("wortmarke", lk), ("wortmarke-gestapelt", lk_st), ("app-icon", icon), ("einfarbig", mn)]:
        (LOGOS / f"{k}-{name}.svg").write_text(svg)
    sw = "".join(f'<li><i style="background:{c}"></i><b>{n}</b>{c}</li>' for n, c in idea["colors"])
    font_name = {"bowlbyone": "Bowlby One", "barlowcondensed": "Barlow Condensed ExtraBold Italic", "archivoblack": "Archivo Black", "alfaslabone": "Alfa Slab One", "fredoka": "Fredoka SemiBold", "spacegrotesk": "Space Grotesk Bold"}[idea["font"]]
    boards += f'''
<section class="board" id="{k}">
  <header><span class="no">{i + 1}</span><h2>{idea["name"]}</h2><p class="sees"><b>Das sieht man:</b> {idea["sieht"]}</p></header>
  <div class="grid">
    <figure class="big" style="background:{idea["bg"]}">{big}</figure>
    <div class="side">
      <figure class="lock" style="background:#fff">{lk}</figure>
      <div class="row">
        <figure class="icon"><div style="width:140px">{icon}</div><figcaption>App-Icon</figcaption></figure>
        <figure class="tiny"><div class="t32">{icon.replace('<svg ', '<svg width="32" height="32" ', 1)}{mn.replace('<svg ', '<svg width="32" height="32" ', 1)}</div><figcaption>32 px</figcaption></figure>
        <figure class="mono"><div style="width:120px">{mn}</div><figcaption>einfarbig</figcaption></figure>
        <figure class="mono inv"><div style="width:120px">{mn_inv}</div><figcaption>negativ</figcaption></figure>
      </div>
      <figure class="scene">{scene(idea)}</figure>
    </div>
  </div>
  <div class="about"><p>{idea["story"]}</p>
    <div><p class="meta"><b>Schrift</b> {font_name} (SIL OFL), als Pfade im SVG</p><ul class="sw">{sw}</ul></div></div>
</section>'''

rank = "".join(f'<li><b>{[x["name"] for x in IDEAS if x["key"] == k][0]}</b><span>{WHY[k]}</span></li>' for k in RANK)
thumbs = "".join(f'<a href="#{x["key"]}"><div style="background:{x["bg"]}">{mark_svg(x["key"])[0]}</div>{x["name"]}</a>' for x in IDEAS)

html = f'''<!doctype html>
<html lang="de-CH"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Handball Intelligence Zeichen</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,700;12..96,800&display=swap" rel="stylesheet">
<style>
:root{{--bg:#efebe4;--paper:#fff;--ink:#1b1a2e;--ink-2:#58566a;--rule:#d9d3c9}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--bg);color:var(--ink);font:17px/1.55 "Bricolage Grotesque",system-ui,sans-serif}}
.wrap{{max-width:1240px;margin:0 auto;padding:56px max(16px,env(safe-area-inset-left)) 96px}}
.top h1{{font:800 72px/0.95 "Bricolage Grotesque";letter-spacing:-2px;max-width:900px}}
.top p{{max-width:760px;font-size:20px;margin-top:16px}}
.thumbs{{display:grid;grid-template-columns:repeat(6,1fr);gap:12px;margin-top:32px}}
.thumbs a{{text-decoration:none;color:inherit;font-weight:700;font-size:15px}}
.thumbs a div{{aspect-ratio:1;padding:12px;margin-bottom:6px}}
.thumbs svg{{width:100%;height:auto;display:block}}
.board{{background:var(--paper);margin-top:56px;padding:40px}}
.board header{{display:grid;grid-template-columns:auto 1fr;gap:4px 16px;align-items:baseline;margin-bottom:24px}}
.no{{font:800 20px "Bricolage Grotesque";color:var(--ink-2)}}
.board h2{{font:800 48px/1 "Bricolage Grotesque";letter-spacing:-1px}}
.sees{{grid-column:2;font-size:19px}}
.grid{{display:grid;grid-template-columns:480px minmax(0,1fr);gap:24px}}
figure{{margin:0}}
.big{{padding:24px;align-self:start}}
.big svg{{width:432px;height:432px;display:block}}
.side{{display:flex;flex-direction:column;gap:16px;min-width:0}}
.lock{{border:1px solid var(--rule);padding:20px 24px}}
.lock svg{{height:112px;width:auto;max-width:100%;display:block}}
.row{{display:flex;gap:16px;flex-wrap:wrap;align-items:flex-end}}
.row figure{{display:flex;flex-direction:column;align-items:center;gap:6px}}
.row figcaption{{font-size:13px;color:var(--ink-2)}}
.row svg{{display:block;width:100%;height:auto}}
.t32{{display:flex;gap:10px;align-items:center;height:140px}}
.t32 svg{{width:32px!important;height:32px!important}}
.mono div{{padding:8px;border:1px solid var(--rule)}}
.mono.inv div{{background:var(--ink);border-color:var(--ink)}}
.scene svg{{width:100%;height:auto;display:block}}
.about{{display:grid;grid-template-columns:1.3fr 1fr;gap:32px;margin-top:24px;border-top:1px solid var(--rule);padding-top:20px}}
.meta{{font-size:15px;color:var(--ink-2)}}
.sw{{list-style:none;display:grid;grid-template-columns:repeat(2,1fr);gap:8px 16px;margin-top:10px;font-size:14px}}
.sw li{{display:flex;gap:8px;align-items:center}}.sw i{{width:22px;height:22px;display:block;box-shadow:inset 0 0 0 1px #0002}}
.sw b{{font-weight:700}}
.rank{{background:var(--ink);color:#fff;margin-top:56px;padding:40px}}
.rank h2{{font:800 48px/1 "Bricolage Grotesque";margin-bottom:24px}}
.rank ol{{list-style:none;counter-reset:r}}
.rank li{{counter-increment:r;display:grid;grid-template-columns:56px 200px 1fr;gap:16px;padding:16px 0;border-top:1px solid #ffffff33}}
.rank li::before{{content:counter(r);font:800 34px/1 "Bricolage Grotesque";color:#ffd23f}}
.rank li b{{font:800 24px "Bricolage Grotesque"}}
.note{{margin-top:32px;font-size:15px;color:var(--ink-2);max-width:800px}}
@media (max-width:900px){{.grid,.about{{grid-template-columns:1fr}}.big svg{{width:100%;height:auto}}.thumbs{{grid-template-columns:repeat(3,1fr)}}.rank li{{grid-template-columns:40px 1fr}}.rank li span{{grid-column:2}}.top h1{{font-size:44px}}.board{{padding:20px}}}}
</style></head><body><div class="wrap">
<div class="top"><p style="font-weight:700;color:var(--ink-2)">Handball Intelligence · Logo-Runde 2 · Feld Charakter und Herz · 12. November 2026</p>
<h1>Sechs Zeichen mit Charakter</h1>
<p>Jede Idee ist so weit gezeichnet, dass man sie ernst nehmen kann: gross, mit Wortmarke, als App-Icon, bei 32 px, einfarbig und in einer echten Situation. Unter jedem Zeichen steht ein Satz, was man darauf sieht. Am Ende steht meine Rangfolge.</p>
<div class="thumbs">{thumbs}</div></div>
{boards}
<section class="rank"><h2>Meine Rangfolge</h2><ol>{rank}</ol></section>
<p class="note">Jedes Zeichen ging durch mindestens drei Runden: als SVG zeichnen, mit Playwright rendern, anschauen, verbessern. Zwei Ideen sind dabei rausgeflogen: «Griff» (eine Hand hält den Ball) sah nach zwei Runden immer noch aus wie ein Handschuh und war neben dem Abklatschen doppelt, «Teamkreis» (das Team von oben, Arm in Arm) las sich als Kette, nicht als Menschen. Ersetzt durch Murmeli; die Hand lebt im Abklatschen weiter. Die Wortmarken sind mit fontTools in Pfade umgewandelt; die SVG-Dateien in logos/ brauchen keine Schrift. Zur Abgrenzung: IHF, EHF, HBL, DHB und handball.ch arbeiten mit Ball, Stern, Spielerfigur oder Wortmarke; keines hat ein Tier, eine Hand, einen Wimpel oder einen Gruss. Der Ball kommt hier nur als kleines Teil vor (Stirnband, Pfoten, i-Punkt). Keine Markenrecherche: Bevor eines davon gilt, braucht es eine Prüfung im Markenregister.</p>
</div></body></html>'''
(HERE / "index.html").write_text(html)
print("ok", len(html))
