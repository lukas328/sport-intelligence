"""The brand page: the whole process from brief to recommendation, as one HTML file."""
from marks import MARKS, WORD, lockup, mark_auge, svg, text

INK, STOFF, INK2, RULE = "#16171a", "#eceae5", "#53565b", "#d6d3cc"
CLUBS = [("Blau", "#1f4fd6", "#ffffff"), ("Rot", "#d3202e", "#ffffff"), ("Gelb", "#f6c500", INK),
         ("Schwarz", "#17191c", "#ffffff"), ("Weiss", "#ffffff", INK), ("Grün", "#12804a", "#ffffff")]


def sized(s, w=None, h=None, label=None):
    attr = (f' width="{w}"' if w else "") + (f' height="{h}"' if h else "") + (f' role="img" aria-label="{label}"' if label else ' aria-hidden="true"')
    return s.replace("<svg ", "<svg" + attr + " ", 1)


# ---------- the five directions ----------
DIRS = [
    {"key": "anlauf", "no": 1, "name": "Anlauf", "idea": "Ein Tor, wie die App es zeichnet: der Anlauf als dicke, gemessene Linie bis zur Wurfposition, dann der dünne Strich ins Tor. Das Tor links, wie auf der Taktikkamera.",
     "grid": "Raster 48. Lauf 7 breit mit runden Enden, Wurfposition r 6, Strich 2,6, Tor 4,5 x 24. Der Lauf endet 2 Einheiten vor dem Punkt, damit bei 16 px kein Klumpen entsteht.",
     "sports": "Trägt jede Torsportart: Fussball, Hockey, Unihockey haben auch Anlauf, Schuss, Tor. Das Zeichen sagt Analyse, nicht Handball.",
     "hi": "Braucht «HI» nicht. Die Wortmarke steht klein geschrieben, damit sie zum Strich passt.",
     "weak": "Als Zeichen allein ein Bewegungssymbol unter vielen; ohne Wortmarke nicht als Handball erkennbar. Stark als Bildsprache, schwächer als Stempel."},
    {"key": "feld", "no": 2, "name": "Feld", "idea": "Das Handballfeld von oben, gedreht: die zwei Seitenlinien und die Mittellinie ergeben ein H, die beiden Torraumbögen schliessen es oben und unten.",
     "grid": "Raster 48. Seitenlinien 7, Mittellinie 5 (optisch gleich schwer wie die Stämme), Torraumbögen r 9,5 mit 3. Die Bögen berühren die Stämme nicht, damit die Form bei 16 px offen bleibt.",
     "sports": "Das H mit Mittellinie trägt jede Feldsportart. Die Torraumbögen sind Handball; für eine zweite Sportart würden sie ausgetauscht (Strafraum, Korb), das H bleibt.",
     "hi": "Liest sich als H, nicht als «Hi». Die Kurzform braucht es nicht.",
     "weak": "Ein H im Rechteck ist verbreitet (Spital, Hotel, Helikopterlandeplatz). Die Bögen holen es da heraus, aber nur ab etwa 24 px. Steht aufrecht und passt damit weniger zum schrägen Anlauf."},
    {"key": "keil", "no": 3, "name": "Keil", "idea": "Der Wurf-Kopf selbst: der Block mit der schrägen Unterkante, «HI» ausgestanzt. In der App nimmt er die Vereinsfarbe an, wie der Kopf.",
     "grid": "Raster 48. Block 48 breit, links 46, rechts 36 hoch: dieselbe Schräge wie der Wurf-Kopf (100 zu 80 Prozent). HI in Kanit Black Italic, Versalhöhe 26, optisch mittig.",
     "sports": "Trägt jede Sportart, weil es nichts über Handball sagt.",
     "hi": "Lebt von «HI». Als Kurzform freundlich («Hi»), aber allein auf dem App-Icon liest man eher eine Begrüssung als einen Namen.",
     "weak": "Ein schräger Block mit Buchstaben ist ein Abzeichen, wie es viele Ligen und Sportmarken haben. Am nächsten an Wett-Logos von allen fünf."},
    {"key": "nummer", "no": 4, "name": "Rückennummer", "idea": "«HI» als Rückennummer mit zwei versetzten Konturen, so wie das Resultat im Wurf-Kopf steht.",
     "grid": "Raster 48. HI in Kanit Black Italic, Versalhöhe 29; zwei Konturen 1,1 stark, je 4,2 nach links und 3,4 nach oben versetzt, 60 und 30 Prozent Deckkraft.",
     "sports": "Trägt jede Mannschaftssportart: eine Rückennummer gibt es überall.",
     "hi": "Lebt ganz von «HI». Die Konturen machen es laut; mit «Hi» gelesen wirkt es wie ein Gruss auf einem Fan-Shirt.",
     "weak": "Die Konturen verschwinden unter 32 px und werden im Druck zur Fleissarbeit. Kommt dem Sportartikel- und Wett-Look am nächsten."},
    {"key": "hlauf", "no": 5, "name": "H im Lauf", "idea": "Ein schräges H, dessen Querstrich ein Anlauf ist: von links unten gezogen, endet er als Punkt, der Wurfposition, kurz vor dem rechten Stamm. Buchstabe und Spielzug in einem.",
     "grid": "Raster 48. Stämme 7 breit, 12 Grad schräg wie Kanit Italic. Lauf 5,5 mit rundem Ende, Punkt r 4,4, Abstand zum Stamm 2 Einheiten. Der Punkt sitzt auf halber Höhe, der Lauf beginnt unter der Mitte: der Querstrich steigt.",
     "sports": "Das H heisst Handball. Für «Sport Intelligence» als Dach wäre dasselbe Prinzip mit einem S möglich; als Handball-Produkt ist das H richtig.",
     "hi": "Kein «HI» nötig; das Zeichen ist ein H. Die Kurzform bleibt für Sprache, nicht für das Zeichen.",
     "weak": "Bei 16 px wird der Punkt zum Knoten im Querstrich; man liest ein H, die Geschichte erst ab 24 px. Ein schräges H gibt es oft; der Punkt muss es tragen."},
]

# ---------- sketch sheet ----------
def sk(inner):
    return svg(inner)
S = 'fill="none" stroke="{c}" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"'.format(c=INK)
SKETCHES = [
    ("Anlauf", MARKS["anlauf"](), "weiter als Richtung 1"),
    ("Feld als H", MARKS["feld"](), "weiter als Richtung 2"),
    ("Schräge mit HI", MARKS["keil"](), "weiter als Richtung 3"),
    ("Rückennummer HI", MARKS["nummer"](), "weiter als Richtung 4"),
    ("H im Lauf", MARKS["hlauf"](), "weiter als Richtung 5, eigene Idee"),
    ("Das Auge", mark_auge(), "raus: liest sich als Smiley oder Überwachungskamera; das Auge ist das Klischee für «KI sieht»"),
    ("Ball mit Nähten", f'<circle cx="24" cy="24" r="18" {S}/><path d="M8 18C18 22 30 22 40 18M8 30C18 26 30 26 40 30M24 6V42" {S}/>', "raus: der Ball ist das Zeichen von IHF und EHF"),
    ("Sprungwurf", f'<circle cx="28" cy="8" r="4" fill="{INK}"/><path d="M27 14L22 28L28 40M22 28L14 38M25 18L36 12M25 18L14 22" {S}/><circle cx="40" cy="9" r="3.5" fill="{INK}"/>', "raus: die Spielerfigur mit Ball führen HBL und das Olympia-Piktogramm"),
    ("Netz aus Knoten", f'<path d="M10 12L24 8L38 14L34 30L20 38L10 26Z M24 8L20 38M10 26L38 14" {S}/>' + "".join(f'<circle cx="{x}" cy="{y}" r="3.2" fill="{INK}"/>' for x, y in [(10, 12), (24, 8), (38, 14), (34, 30), (20, 38), (10, 26)]), "raus: Tech-Startup; verspricht «KI» statt Fussarbeit"),
    ("Wappen mit HI", f'<path d="M8 6H40V26C40 36 32 42 24 45C16 42 8 36 8 26Z" {S}/><path d="M17 16V32M17 24H25M25 16V32M32 16V32" {S}/>', "raus: Verbandslogo; konkurriert mit dem Wappen des Vereins, das in der App vorne steht"),
    ("Blitz", f'<path d="M28 4L12 27H23L19 44L36 20H25Z" {S}/>', "raus: Wettanbieter und der Opel-Blitz im Ligalogo"),
    ("Stern", f'<path d="M24 5L29 18H43L32 27L36 41L24 33L12 41L16 27L5 18H19Z" {S}/>', "raus: Champions League, Sieger-Symbol"),
    ("Torraum als D", f'<path d="M10 6V42M10 6A18 18 0 0 1 10 42" {S}/><circle cx="20" cy="24" r="4" fill="{INK}"/>', "raus: liest sich als D"),
    ("Torraster 3x3", f'<rect x="6" y="10" width="36" height="28" {S}/><path d="M18 10V38M30 10V38M6 19.3H42M6 28.6H42" {S}/><rect x="31" y="29" width="10" height="8" fill="{INK}"/>', "raus: zeigt, was das Video nicht misst"),
    ("Sprechblase «Hi»", f'<path d="M6 8H42V32H20L10 41V32H6Z" {S}/><path d="M16 15V26M16 20.5H23M23 15V26M30 18V26" {S}/><circle cx="30" cy="14" r="1.6" fill="{INK}"/>', "raus: Chat-App; die App schickt keine Nachrichten"),
    ("Bildschirm mit Punkten", f'<rect x="5" y="8" width="38" height="26" {S}/><path d="M16 42H32M24 34V42" {S}/>' + "".join(f'<circle cx="{x}" cy="{y}" r="2.6" fill="{INK}"/>' for x, y in [(14, 16), (22, 22), (30, 18), (34, 27), (16, 27)]), "raus: bei 16 px ein Brei; bleibt als Bildwelt (Taktikkamera)"),
    ("Bündel", f'<rect x="14" y="2" width="20" height="4" fill="{INK}"/><path d="M8 44C12 32 18 26 22 22M24 45C24 34 24 28 24 23M40 44C36 32 30 26 26 22" {S}/><circle cx="24" cy="19" r="4.5" fill="{INK}"/>', "raus als Zeichen (Blume, Feuerwerk); bleibt als Muster aus echten Anläufen"),
    ("Keil allein", f'<path d="M4 22L44 30V36L4 30Z" fill="{INK}"/>', "raus: zu wenig Eigenart, liest sich als Unterstrich"),
    ("Zwei Teams", f'<circle cx="16" cy="24" r="10" fill="{INK}"/><circle cx="33" cy="24" r="10" {S}/>', "raus: Ampel, Schalter, Wahlzettel; beliebig"),
    ("Stoppuhr", f'<circle cx="24" cy="27" r="16" {S}/><path d="M24 27L31 19M20 5H28M24 5V11" {S}/>', "raus: Zeitnahme, nicht Auswertung"),
    ("Feld mit Kreis", f'<rect x="4" y="8" width="40" height="32" {S}/><path d="M24 8V40" {S}/><circle cx="24" cy="24" r="6" {S}/>', "raus: der Mittelkreis ist Fussball"),
    ("Zielscheibe", f'<circle cx="24" cy="24" r="18" {S}/><circle cx="24" cy="24" r="9" {S}/><circle cx="24" cy="24" r="3" fill="{INK}"/>', "raus: Ziel, Waffe, Wette"),
]

ENV = [
    ("IHF (Weltverband)", "Handball als Kugel mit geschwungenen Linien, Buchstaben IHF senkrecht darüber; 2020 vereinfacht.", "Kein Ball, keine geschwungenen Nähte, keine Kugel als Grundform.", "https://www.ihf.info/media-center/news/refreshed-logo-ihf"),
    ("EHF (Europa)", "Dachmarke «We play handball» seit 2020, die Ballform als wiederkehrendes Motiv; Champions League mit goldenem Stern, European League mit einem drehenden E im Fünfeck.", "Kein Ball, kein Stern, kein Fünfeck, kein Gold.", "https://ehfec.eurohandball.com/news/en/we-play-handball-a-new-brand-identity/"),
    ("Handball-Bundesliga (HBL)", "Spieler mit Ball in der Hand und Wurfkreis (2024); seit Juli 2026 mit Opel-Blitz kombiniert.", "Keine Spielerfigur, kein Blitz. Unser Torraumbogen bleibt eine Linie im Feld, kein Kreis um eine Figur.", "https://www.media.stellantis.com/de-de/opel/press/opel-und-die-hbl-praesentieren-offizielles-logo-der-opel-handball-bundesliga"),
    ("Schweizerischer Handball-Verband (handball.ch)", "Rotes Verbandszeichen; das Rot des Verbands (Ausweise HEX BA1B22).", "Kein Rot als Markenfarbe, kein Schweizerkreuz, keine Verbandsanmutung. Wir zeigen Daten von handball.ch und dürfen nicht wie der Verband aussehen.", "https://www.handball.ch/media/0pxkayev/2025-12-04_reglement-ausweise-shv_de_v24_de.pdf"),
    ("Handball.ai", "Analyseplattform für Handball (Statistik, Scouting), mit XPS (Sideline Sports) verbunden.", "Der bisherige Name «Handball AI» ist praktisch derselbe. Der neue Name «Handball Intelligence» und ein Zeichen ohne «AI» halten Abstand.", "https://handball.ai/"),
    ("Analysewerkzeuge (Hudl, Catapult, Kinexon, Spiideo)", "Wortmarken, meist Grossbuchstaben oder kräftige Grotesk, Tech-Farben; Hudl in Orange (aus eigener Anschauung, nicht in der Suche bestätigt).", "Keine Tech-Farbe, kein Datenpunkt-Netz, keine Kamera als Zeichen.", "https://www.catapult.com/sports/handball"),
    ("Wettanbieter", "Schwarz mit Gelb, Rot mit Weiss, Grün mit Gelb; schräge, fette Wortmarken, Pfeile, Blitze, Quoten-Kacheln (aus eigener Anschauung).", "Kein Schwarz-Gelb, keine Leuchtfarbe, kein Pfeil, keine schräge Versalwortmarke. Schräg ja, aber in Tinte auf Stoff und klein geschrieben oder gemischt.", ""),
]

SCORE_COLS = ["Eigenständig", "Lesbar bei 16 px", "Passt zu Anlauf", "Als Handball erkennbar", "Trägt andere Sportarten", "Abstand zu bestehenden Zeichen", "Wenig Aufwand"]
SCORES = {"anlauf": [4, 3, 5, 2, 5, 4, 4], "feld": [3, 5, 3, 4, 3, 3, 5], "keil": [2, 4, 5, 1, 5, 2, 5], "nummer": [2, 2, 4, 2, 4, 2, 3], "hlauf": [5, 4, 5, 3, 3, 4, 4]}


def dots(n):
    return f'<span class="sc" aria-label="{n} von 5">' + "".join(f'<i class="{"on" if i < n else ""}"></i>' for i in range(5)) + f"</span>"


def grid_view(fn):
    g = "".join(f'<path d="M{i} 0V48M0 {i}H48" stroke="#9aa0a6" stroke-width=".12"/>' for i in range(0, 49, 4))
    g += '<path d="M24 0V48M0 24H48" stroke="#c0392b" stroke-width=".16" stroke-dasharray=".8 .8"/>'
    return sized(svg(f'<rect width="48" height="48" fill="#f7f6f2"/>{g}<g opacity=".88">{fn(INK)}</g>'), 240, 240, "Zeichen auf dem Raster")


def icon_ios(fn, bg=STOFF, fg=INK, size=120):
    return sized(svg(f'<rect width="48" height="48" rx="10.7" fill="{bg}"/><g transform="translate(10.8 10.8) scale(.55)">{fn(fg)}</g>'), size, size, "App-Icon iOS")


def icon_android(fn, bg=INK, fg=STOFF, size=120):
    # adaptive icon: 108 dp canvas, 72 dp visible, 66 dp safe zone; the mark sits in the safe zone
    return sized(svg(f'<circle cx="24" cy="24" r="24" fill="{bg}"/><g transform="translate(13.2 13.2) scale(.45)">{fn(fg)}</g>'), size, size, "App-Icon Android, runde Maske")


def favicon(fn, px):
    return sized(svg(f'<rect width="48" height="48" fill="{INK}"/><g transform="translate(6 6) scale(.75)">{fn(STOFF)}</g>'), px, px, f"Favicon {px} px")


def app_head(d):
    fn, key = MARKS[d["key"]], d["key"]
    desk = (f'<div class="ahead"><span class="pm">{sized(svg(fn("var(--c)")), 30, 30, "Handball Intelligence")}</span><span class="sep"></span><span class="crest">HCZ</span><b class="kn">HC Zürichsee</b>'
            '<nav><a class="on">Spiele</a><a>Szenen</a><a>Saison</a><a>Team</a></nav><span class="up">Video hochladen</span></div>')
    phone = (f'<div class="ahead p"><span class="pm">{sized(svg(fn("var(--c)")), 26, 26, "Handball Intelligence")}</span><span class="sep"></span><span class="crest">HCZ</span><b class="kn">HC Zürichsee</b><span class="up sq">+</span></div>')
    login = f'<div class="login">{sized(lockup(key, INK, "zwei"), None, 56, "Handball Intelligence")}<p>Anmelden</p><span class="f"></span><span class="f"></span><span class="b">Weiter</span></div>'
    return desk, phone, login


def share(d):
    fn = MARKS[d["key"]]
    return (f'<div class="chat"><div class="bubble"><div class="og"><span class="ogm">{sized(lockup(d["key"], INK, "quer"), None, 18, "Handball Intelligence")}</span>'
            '<b class="t">Rückzug nach Ballverlust</b><span class="s">HC Zürichsee Herren 1 · 5 Szenen, 2:35</span><i class="kl"></i></div>'
            '<div class="meta"><b>Rückzug nach Ballverlust</b>Handball Intelligence</div><p class="msg">Schaut euch das bis Dienstag an.</p><p class="tm">21:14</p></div></div>')


def shirt(d):
    fn = MARKS[d["key"]]
    body = "M14 6L22 3C24 7 32 7 34 3L42 6L52 16L46 23L41 19V58H15V19L10 23L4 16Z"
    return sized(svg(f'<path d="{body}" fill="{INK}"/><path d="M22 3C24 7 32 7 34 3" fill="none" stroke="#2c2e33" stroke-width="1"/><g transform="translate(29 16) scale(.24)">{fn(STOFF)}</g>', 56, 62), 170, None, "T-Shirt mit Zeichen auf der Brust")


def sticker(d):
    fn = MARKS[d["key"]]
    return sized(svg(f'<rect x="1" y="1" width="62" height="62" fill="#ffffff" stroke="#c9c6bf" stroke-width=".6"/><rect x="5" y="5" width="54" height="54" fill="{INK}"/><g transform="translate(12 12) scale(.833)">{fn(STOFF)}</g>', 64, 64), 150, 150, "Kleber")


def direction(d):
    k, fn = d["key"], MARKS[d["key"]]
    head_d, head_p, login = app_head(d)
    clubs = "".join(f'<figure class="club" style="background:{c};{"box-shadow:inset 0 0 0 1.5px " + INK if c == "#ffffff" else ""}">{sized(lockup(k, ink, "quer"), None, 30, "Handball Intelligence auf " + n)}<figcaption style="color:{ink}">{n}</figcaption></figure>' for n, c, ink in CLUBS)
    sc = SCORES[k]
    return f'''<section class="dir" id="r{d["no"]}">
<header class="dh"><span class="no n">{d["no"]}</span><h3 class="d">{d["name"]}</h3><p>{d["idea"]}</p></header>
<div class="row">
  <figure class="big">{sized(svg(fn(INK)), 240, 240, "Zeichen " + d["name"])}<figcaption>Zeichen</figcaption></figure>
  <figure>{grid_view(fn)}<figcaption>{d["grid"]}</figcaption></figure>
  <div class="notes"><p><b>Andere Sportarten.</b> {d["sports"]}</p><p><b>«HI».</b> {d["hi"]}</p><p><b>Schwäche.</b> {d["weak"]}</p></div>
</div>
<h4>Wortmarke und Kombinationen</h4>
<div class="row lock">
  <figure>{sized(lockup(k, INK, "quer"), None, 48, "quer")}<figcaption>quer, eine Zeile</figcaption></figure>
  <figure>{sized(lockup(k, INK, "zwei"), None, 64, "zweizeilig")}<figcaption>zweizeilig</figcaption></figure>
  <figure>{sized(lockup(k, INK, "gestapelt"), None, 120, "gestapelt")}<figcaption>gestapelt</figcaption></figure>
  <figure>{sized(svg(fn(INK)), 64, 64, "nur Zeichen")}<figcaption>nur Zeichen</figcaption></figure>
</div>
<h4>Icon und Favicon</h4>
<div class="row icons">
  <figure>{icon_ios(fn)}<figcaption>iOS, Stoff</figcaption></figure>
  <figure>{icon_ios(fn, INK, STOFF)}<figcaption>iOS, Tinte</figcaption></figure>
  <figure>{icon_android(fn)}<figcaption>Android, runde Maske</figcaption></figure>
  <figure class="fav"><div class="tab"><span>{favicon(fn, 16)}</span>Handball Intelligence</div><div class="fx">{favicon(fn, 16)} {favicon(fn, 32)}</div><figcaption>Favicon 16 und 32 px in Originalgrösse, im Browser-Tab</figcaption></figure>
</div>
<h4>In der App</h4>
<div class="row app" style="--c:{INK}">{head_d}</div>
<div class="row app" style="--c:#1f4fd6">{head_p}<figure>{login}</figure></div>
<p class="cap">Oben in Tinte; darunter auf dem Handy in der Vereinsfarbe des angemeldeten Teams (hier Blau). Das Wappen des Vereins steht daneben und bleibt das grössere Zeichen.</p>
<h4>Geteilter Link, einfarbig, Vereinsfarben, Merch</h4>
<div class="row">
  {share(d)}
  <figure class="mono"><div style="background:#fff">{sized(lockup(k, "#000000", "zwei"), None, 52, "schwarz")}</div><div style="background:#000">{sized(lockup(k, "#ffffff", "zwei"), None, 52, "weiss")}</div><figcaption>einfarbig schwarz und weiss</figcaption></figure>
  <figure>{shirt(d)}<figcaption>T-Shirt der Trainerbank</figcaption></figure>
  <figure>{sticker(d)}<figcaption>Kleber, 6 x 6 cm</figcaption></figure>
</div>
<div class="clubs">{clubs}</div>
<div class="tw"><table class="mini"><tr>{"".join(f"<th>{c}</th>" for c in SCORE_COLS)}</tr><tr>{"".join(f"<td>{dots(v)}</td>" for v in sc)}</tr></table></div>
</section>'''


CSS = """
*{box-sizing:border-box}html,body{margin:0;background:#eceae5;color:#16171a;font:400 17px/1.5 "Hanken Grotesk",system-ui,sans-serif;-webkit-font-smoothing:antialiased}
body{background-image:radial-gradient(rgb(22 23 26/.07) .7px,transparent .9px),radial-gradient(rgb(22 23 26/.05) .7px,transparent .9px);background-size:6px 6px;background-position:0 0,3px 3px}
main{max-width:1200px;margin:0 auto;padding:48px 16px 80px;overflow-x:clip}
.d{font-family:Kanit,sans-serif;font-style:italic;font-weight:800;letter-spacing:-.01em}.n{font-family:Kanit,sans-serif;font-style:italic;font-weight:900}
h1{font:italic 900 96px/.88 Kanit,sans-serif;margin:0 0 18px;letter-spacing:-.02em}
h2{font:italic 800 40px/1 Kanit,sans-serif;margin:72px 0 16px;padding-bottom:10px;border-bottom:2px solid #16171a;position:relative}
h2 small{font:600 15px "Hanken Grotesk",sans-serif;color:#53565b;margin-left:12px;font-style:normal}
h4{font:italic 800 20px Kanit,sans-serif;margin:28px 0 10px}
p{max-width:72ch;margin:0 0 10px}.kick{font-weight:600;color:#53565b;font-size:15px;margin-bottom:10px}
.lead{font-weight:700;font-size:24px;line-height:1.3;max-width:60ch}
.keil{height:20px;background:#16171a;clip-path:polygon(0 0,100% 78%,100% 100%,0 100%);margin:28px 0 0}
table{border-collapse:collapse;width:100%;font-size:15px}th{text-align:left;font-size:13px;color:#53565b;font-weight:600;padding:8px 12px 8px 0;border-bottom:2px solid #16171a;vertical-align:bottom}
td{padding:10px 12px 10px 0;border-bottom:1px solid #d6d3cc;vertical-align:top}.tw{overflow-x:auto}
a{color:inherit;font-weight:700;text-underline-offset:3px}
.cols3{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:32px}.cols2{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:32px}
.cols3 h3,.cols2 h3{font:italic 800 22px Kanit,sans-serif;margin:0 0 8px}
ul.plain{padding-left:18px;margin:0}ul.plain li{margin-bottom:6px}
.sketches{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:20px 18px}
.sketches figure{margin:0}.sketches .pic{background:#f7f6f2;aspect-ratio:1;display:grid;place-items:center;padding:16%}
.sketches .pic svg{width:100%;height:100%}.sketches .out .pic{opacity:.55}
.sketches b{display:block;font:italic 800 16px Kanit,sans-serif;margin-top:8px}.sketches span{display:block;font-size:13px;color:#53565b;line-height:1.35}
.sketches .in span{color:#17703f;font-weight:700}
.dir{margin-top:56px;padding-top:24px;border-top:2px solid #16171a}
.dh{display:grid;grid-template-columns:auto minmax(0,1fr);gap:4px 20px;align-items:baseline}.dh .no{font-size:96px;line-height:.8;grid-row:span 2}
.dh h3{font-size:44px;line-height:1;margin:0}.dh p{margin:6px 0 0}
.row{display:flex;flex-wrap:wrap;gap:28px;align-items:flex-start;margin-top:16px}
figure{margin:0}figcaption{font-size:13px;color:#53565b;margin-top:8px;max-width:260px;line-height:1.4}
.big{background:#f7f6f2;padding:0}.notes{flex:1;min-width:280px}.notes p{font-size:15px}
.lock figure{background:#f7f6f2;padding:20px 24px;max-width:100%}.lock svg{display:block;max-width:100%;height:auto}
.icons figure{display:flex;flex-direction:column;align-items:flex-start}.icons svg{display:block}
.fav .tab{display:flex;align-items:center;gap:8px;background:#dcdad4;padding:8px 14px 8px 10px;font:13px system-ui,sans-serif;width:230px;border-bottom:2px solid #fff}
.fav .fx{display:flex;align-items:flex-end;gap:14px;margin-top:14px}.fav svg{display:block}
.app{--c:#16171a}.ahead{display:flex;align-items:center;gap:14px;height:64px;padding:0 24px;border-bottom:2px solid #16171a;background:#eceae5;width:100%;max-width:1000px}
.ahead.p{width:390px;padding:0 16px;height:60px;gap:10px}.ahead .sep{width:1.5px;height:28px;background:#c4c0b8}
.ahead .crest{width:30px;height:34px;background:#1f4fd6;color:#fff;display:grid;place-items:center;font:italic 800 11px Kanit,sans-serif;clip-path:polygon(0 0,100% 0,100% 74%,50% 100%,0 74%)}
.ahead .kn{font:italic 800 18px Kanit,sans-serif;flex:none}.ahead nav{display:flex;gap:22px;margin-left:16px;font:italic 700 17px Kanit,sans-serif;color:#53565b}.ahead nav .on{color:#16171a;box-shadow:inset 0 -5px 0 #1f4fd6}
.ahead .up{margin-left:auto;background:#16171a;color:#eceae5;font:700 14px "Hanken Grotesk",sans-serif;padding:12px 14px}.ahead .sq{padding:8px 15px;font-size:20px}
.login{width:300px;background:#f7f6f2;padding:22px;display:flex;flex-direction:column;gap:10px}.login p{font:italic 800 22px Kanit,sans-serif;margin:8px 0 0}
.login .f{height:44px;border:1.5px solid #16171a;background:#fff}.login .b{height:44px;background:#16171a;color:#eceae5;display:grid;place-items:center;font-weight:700}
.cap{font-size:13px;color:#53565b;margin-top:8px}
.chat{background:#e4ddd2;padding:16px;width:330px}.bubble{background:#fff;padding:6px;box-shadow:0 1px 0 rgb(0 0 0/.14)}
.og{position:relative;background:#eceae5;height:160px;padding:14px;display:flex;flex-direction:column;overflow:hidden}
.og .t{font:italic 800 25px/1 Kanit,sans-serif;margin-top:auto;max-width:85%}.og .s{font-size:12px;margin-top:6px;color:#53565b}
.og .kl{position:absolute;left:0;right:0;bottom:0;height:9px;background:#1f4fd6;clip-path:polygon(0 0,100% 78%,100% 100%,0 100%)}
.og .ogm svg{display:block}.meta{padding:8px 6px 2px;font-size:13px}.meta b{display:block;font-size:15px}.msg{font-size:15px;padding:6px 6px 0;margin:0}.tm{text-align:right;font-size:12px;color:#667;margin:0;padding:0 6px}
.mono div{padding:18px 22px}.mono svg{display:block}
.clubs{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:8px;margin-top:20px}.club{padding:16px 12px 10px;display:flex;flex-direction:column;justify-content:space-between;min-height:96px;overflow:hidden}.club svg{max-width:100%;height:auto}
.club figcaption{margin:8px 0 0;font-weight:700}
table.mini{margin-top:20px}table.mini th{font-size:12px}
.sc{display:inline-flex;gap:3px}.sc i{width:12px;height:12px;border:1.5px solid #16171a;transform:skewX(-14deg)}.sc i.on{background:#16171a}
.eval td:first-child{font:italic 800 18px Kanit,sans-serif;white-space:nowrap}.eval td.sum{font:italic 900 22px Kanit,sans-serif}
.rec{background:#16171a;color:#eceae5;padding:28px 28px 24px;margin-top:20px}.rec h3{font:italic 900 40px/1 Kanit,sans-serif;margin:0 0 12px}.rec p{max-width:80ch}
.pass li{margin-bottom:8px}.colorrow{display:flex;gap:10px;flex-wrap:wrap;margin-top:14px}.colorrow span{width:120px;height:72px;display:flex;align-items:flex-end;padding:8px;font-size:12px;font-weight:700}
@media (max-width:700px){.ahead{max-width:100%}.login,.chat{max-width:100%}.mono svg{max-width:100%;height:auto}.big svg,.row>figure>svg{max-width:100%;height:auto}.dh .no{font-size:64px}h1{font-size:60px}.cols3,.cols2{grid-template-columns:1fr}.sketches{grid-template-columns:repeat(2,minmax(0,1fr))}.clubs{grid-template-columns:repeat(2,minmax(0,1fr))}.ahead{overflow:hidden}.ahead nav{display:none}.ahead.p{width:100%}}
"""


def page():
    sk = "".join(f'<figure class="{"in" if v.startswith("weiter") else "out"}"><div class="pic">{sized(svg(m), label=n)}</div><b>{n}</b><span>{v}</span></figure>' for n, m, v in SKETCHES)
    env = "".join(f'<tr><td><b>{n}</b></td><td>{w}</td><td>{a}</td><td>{f"<a href=\'{u}\'>Quelle</a>" if u else "eigene Anschauung"}</td></tr>' for n, w, a, u in ENV)
    dirs = "".join(direction(d) for d in DIRS)
    ev = "".join(f'<tr><td>{d["no"]} {d["name"]}</td>{"".join(f"<td>{dots(v)}</td>" for v in SCORES[d["key"]])}<td class="sum">{sum(SCORES[d["key"]])}</td></tr>' for d in DIRS)
    chips = "".join(f'<span style="background:{c};color:{i};{"box-shadow:inset 0 0 0 1.5px #16171a" if c == "#ffffff" else ""}">{sized(svg(MARKS["hlauf"](i)), 28, 28)}<br>{n}</span>' for n, c, i in CLUBS)
    return f'''<!doctype html><html lang="de-CH"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Marke Handball Intelligence</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Hanken+Grotesk:wght@400;600;700&family=Kanit:ital,wght@1,700;1,800;1,900&display=swap" rel="stylesheet">
<style>{CSS}</style></head><body><main>
<p class="kick">Handball Intelligence · Marke und Logo · Stand 12. November 2026 · Entscheid offen</p>
<h1>Ein Zeichen für<br>Handball Intelligence</h1>
<p class="lead">Der Weg von der Grundlage über 22 Skizzen zu fünf ausgearbeiteten Richtungen, mit Bewertung und Empfehlung. Alle Zeichen als SVG in <code>logos/</code>.</p>
<div class="keil"></div>

<h2>1 Grundlage</h2>
<div class="cols3">
<div><h3>Für wen</h3><p>Trainerinnen und Trainer im Amateurhandball, die am Samstag spielen und am Sonntag wissen wollen, was passiert ist. Sie zeigen die App ihrem Team, nicht einem Publikum.</p></div>
<div><h3>Was sie verspricht</h3><p>Aus dem Video eines Spiels werden drei Dinge, die stimmen, und die Szenen dazu. Gezeigt wird nur, was gemessen ist.</p></div>
<div><h3>Drei Eigenschaften</h3><ul class="plain"><li><b>Genau:</b> jede Linie ein gemessener Weg.</li><li><b>Zur Hand:</b> nah an der Halle, nicht am Labor.</li><li><b>Zurückhaltend:</b> die Farben gehören den Teams.</li></ul></div>
</div>
<div class="cols2" style="margin-top:24px">
<div><h3>Was sie nicht sein soll</h3><ul class="plain"><li><b>Wettanbieter:</b> kein Schwarz-Gelb, keine Leuchtfarbe, kein Blitz, keine Quoten-Anmutung.</li><li><b>Tech-Startup:</b> kein Netz aus Punkten, kein Gehirn, kein Auge, kein «AI» im Zeichen.</li><li><b>Verbandslogo:</b> kein Wappen, kein Ball mit Nähten, kein Rot-Weiss, kein Kreuz. Das Wappen in der App ist das des Vereins.</li></ul></div>
<div><h3>Der Name</h3><ul class="plain"><li><b>Schreibweise:</b> Handball Intelligence, zwei Wörter, gross geschrieben. In Richtung 1 klein als Wortmarke: handball intelligence.</li><li><b>Kurzform:</b> im Gespräch «HI». Sie liest sich als «Hi»: freundlich im Satz («Hi, HC Zürichsee»), schwach als Zeichen allein, weil es nach Begrüssung oder Chat aussieht. Deshalb kein Zeichen, das nur aus HI besteht, als Empfehlung.</li><li><b>Zweizeilig:</b> Handball / Intelligence, linksbündig neben dem Zeichen.</li><li><b>Sprachen:</b> der Name bleibt in de, fr und en gleich; «Intelligence» ist im Französischen und Englischen dasselbe Wort, im Deutschen verständlich. Keine Übersetzung.</li><li>Der frühere Name «Handball AI» fällt weg, auch weil es «handball.ai» als Analyseplattform schon gibt.</li></ul></div>
</div>

<h2>2 Umfeld <small>Keine rechtliche Markenprüfung, nur offensichtliche Nähe</small></h2>
<div class="tw"><table><thead><tr><th>Wer</th><th>Was ihr Zeichen ausmacht</th><th>Abstand, den wir halten</th><th></th></tr></thead><tbody>{env}</tbody></table></div>
<p style="margin-top:14px">Daraus: kein Ball, keine Spielerfigur, kein Stern, kein Blitz, kein Rot als Markenfarbe, keine Tech-Farbe, kein «AI». Frei ist das, was nur wir zeigen: das Feld von oben, der Anlauf als Linie, die Schräge des Kopfs.</p>

<h2>3 Skizzenbogen <small>22 Skizzen, fünf gehen weiter</small></h2>
<div class="sketches">{sk}</div>

<h2>4 Fünf Richtungen</h2>
<p>Jede auf einem Raster von 48 Einheiten, Kanit als Wortmarke (in Pfade umgewandelt, SIL OFL), Tinte <code>#16171a</code> auf Stoff <code>#eceae5</code>. Keine Verläufe, keine Effekte.</p>
{dirs}

<h2>5 Bewertung <small>1 schwach bis 5 stark, von mir nach zwei Durchgängen</small></h2>
<div class="tw"><table class="eval"><thead><tr><th>Richtung</th>{"".join(f"<th>{c}</th>" for c in SCORE_COLS)}<th>Summe</th></tr></thead><tbody>{ev}</tbody></table></div>
<p style="margin-top:12px">Die Summe entscheidet nicht allein. Anlauf liegt knapp vor Feld, weil es überall passt; als Zeichen trägt es aber am wenigsten (siehe Durchgang 2). Gewichtet man Eigenständigkeit, Lesbarkeit und Handball doppelt, liegen H im Lauf (40) und Feld (38) vorn.</p>

<h2>Farbe <small>Trägt «es trägt eure Farben»?</small></h2>
<p>Teilweise. In der App ja: dort ist immer ein Verein angemeldet, das Zeichen steht neben seinem Wappen und darf seine Farbe annehmen, wie der Wurf-Kopf. Ausserhalb der App nein: App-Store, Rechnung, Kleber, die Vorschau eines geteilten Links an jemanden ohne Verein brauchen eine feste Fassung. Eine eigene Markenfarbe braucht es trotzdem nicht. Die feste Fassung ist <b>Tinte auf Stoff</b> (und umgekehrt fürs Icon); das ist neutral, wiedererkennbar und hält Abstand zu allen Rot-, Blau- und Schwarz-Gelb-Zeichen im Umfeld. Auf der Website darf das Zeichen durch die Vereinsfarben wechseln, aber nur als Bewegung, nie als einzige Fassung.</p>
<div class="colorrow"><span style="background:#16171a;color:#eceae5">{sized(svg(MARKS["hlauf"]("#eceae5")), 28, 28)}<br>fest: Tinte</span><span style="background:#eceae5;color:#16171a;box-shadow:inset 0 0 0 1.5px #16171a">{sized(svg(MARKS["hlauf"]("#16171a")), 28, 28)}<br>fest: Stoff</span>{chips}</div>

<h2>6 Zwei Durchgänge als Art Director</h2>
<div class="cols2 pass">
<div><h3>Durchgang 1: sieht es generiert oder beliebig aus?</h3><ul class="plain">
<li>Anlauf sah in der ersten Fassung (Tor oben, Strich nach unten) wie ein Wasserhahn aus, dann wie eine Lampe. Gedreht: das Tor links wie auf der Taktikkamera; jetzt liest es sich als Bewegung zum Tor.</li>
<li>Rückennummer: die Konturen lagen zu eng und wurden zum Gitter. Weiter versetzt; bleibt trotzdem die lauteste und beliebigste Richtung.</li>
<li>Keil: HI war zu klein im Block, sah aus wie ein Platzhalter. Grösser gesetzt. Bleibt ein Abzeichen, wie es viele haben.</li>
<li>H im Lauf: der Punkt berührte den rechten Stamm, dann las man ein A. Zwei Einheiten Luft.</li>
<li>Das Auge flog hier raus: es sah wie jedes KI-Logo aus.</li></ul></div>
<div><h3>Durchgang 2: würde ein Verein es auf einen Kleber drucken?</h3><ul class="plain">
<li><b>H im Lauf:</b> ja. Eine Form, eine Farbe, man erkennt den Wurf, wenn man es erklärt bekommt, und das H, wenn nicht.</li>
<li><b>Feld:</b> ja, auf eine Trainingstasche eher als auf ein Handy. Wirkt wie ein Hallenschild.</li>
<li><b>Anlauf:</b> vielleicht; als Kleber zu abstrakt ohne Namen.</li>
<li><b>Keil</b> und <b>Rückennummer:</b> eher nicht. Sie sehen nach Fan-Artikel aus, nicht nach dem Werkzeug der Trainerin.</li></ul></div>
</div>

<h2>7 Empfehlung</h2>
<div class="rec"><h3>H im Lauf</h3>
<p>Das einzige Zeichen, das Buchstabe und Spiel zugleich ist: ein H für Handball, dessen Querstrich ein Anlauf mit Wurfposition ist, also genau das, was die App misst und zeichnet. Es steht schräg wie die Titel in Anlauf, funktioniert einfarbig, bei 16 px als H, auf dem Kleber als Form. Es braucht kein «HI» und kein «AI». Schwäche: die Geschichte (der Punkt) erschliesst sich erst ab etwa 24 px, und ein schräges H allein ist nicht selten. Feinschliff muss den Punkt tragen.</p>
<p><b>Zweite Wahl: Feld.</b> Am besten lesbar bei 16 px und klar Handball, aber aufrecht, näher an Hinweisschildern und weniger eigen. Wenn die Marke später andere Sportarten tragen soll, ist das Feld der leichtere Weg (Bögen tauschen); für das H im Lauf bräuchte es dann ein zweites Zeichen nach demselben Prinzip.</p>
<p><b>Anlauf</b> bleibt als Bildsprache: Muster aus echten Anläufen für Website, Ladebildschirm, Social-Media-Bilder.</p></div>
<h3 class="d" style="font-size:26px;margin:28px 0 8px">Nächste Schritte</h3>
<ol>
<li><b>Entscheid</b> von Lukas zwischen H im Lauf und Feld (oder einer Mischung: Feld mit schrägen Stämmen).</li>
<li><b>Feinschliff:</b> optische Korrekturen bei 16, 24, 32 und 512 px getrennt (eigene Favicon-Zeichnung mit dickerem Lauf), Wortmarke mit angepasstem Abstand zwischen den Wörtern und eigener Ligatur prüfen, Schutzzone und Mindestgrösse festlegen.</li>
<li><b>Prüfung:</b> Marken- und Domainrecherche durch eine Fachperson in CH, EU und den Stores; Name und Zeichen.</li>
<li><b>Dateien:</b> SVG, PNG für iOS (1024) und Android (adaptiv, 108 dp mit 66 dp Schutzzone), favicon.ico mit 16/32/48, Open-Graph-Bild 1200 x 630, ein Blatt Markenregeln (eine Seite).</li>
<li><b>Umbenennung in der App:</b> «Handball AI» in <code>apps/web/messages/*.json</code>, Titel, Manifest, E-Mails, Store-Einträge und Open-Graph-Bild ersetzen; das Zeichen im Kopf links vor dem Vereinswappen, in Tinte oder der Vereinsfarbe. Erst nach dem Entscheid, in einer eigenen Session.</li>
</ol>
</main></body></html>'''
