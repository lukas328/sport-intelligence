"""Round 2 on the brand page: variants of «H im Lauf», the cross with Feld, Feld away from the sign,
pixel favicons, the custom wordmark, the hard test, one recommendation."""
from marks import svg
from marks2 import (VARIANTS, PIX, cross, feld_einbogen, feld_schraeg, hlauf, pixsvg, word, wordmark,
                    wordmark_plain)

INK, STOFF = "#16171a", "#eceae5"


def final(c=INK):
    """The recommended version: Keil cut stems, the larger shot spot, the flatter run."""
    return hlauf(c, cut=3, dot=(28.6, 21.6, 5.4), run_w=6.5, run="M12.6 29.5C16.5 28 18 25.5 21.6 23.6")


def variant_b(c=INK):
    return hlauf(c, dot=(28.6, 21.6, 5.4), run_w=6.5, run="M12.6 29.5C16.5 28 18 25.5 21.6 23.6")


FINALISTS = [("G", "Keil-Schnitt, Punkt gross", final, "g"), ("B", "Punkt gross, gerade Stämme", variant_b, "b"), ("F", "Feld schräg", feld_schraeg, "feld")]


def sz(s, w=None, h=None, label=None):
    a = (f' width="{w}"' if w else "") + (f' height="{h}"' if h else "") + (f' role="img" aria-label="{label}"' if label else ' aria-hidden="true"')
    return s.replace("<svg ", "<svg" + a + " ", 1)


READ = {
    "a": ("H", "Liest sich als H. Bei 16 px wird der Punkt zum Knoten im Querstrich."),
    "b": ("H", "Liest sich als H; der grössere Punkt bleibt bei 24 px als Punkt sichtbar. Der Lauf wirkt wie ein Arm mit Ball, das ist erwünscht."),
    "c": ("H", "Ein H mit gebogenem Querstrich. Ohne Punkt fehlt die Wurfposition, und damit die Geschichte: beliebig."),
    "d": ("H", "Ein normales H; das Loch verschwindet unter 32 px. Raus."),
    "e": ("H?", "Der Lauf über den Stamm liest sich als durchgestrichenes H oder Doppelkreuz. Raus."),
    "f": ("H", "Liest sich als H, ist aber schneller und lauter; rückt an die Kursiven von Wettanbietern."),
    "g": ("H", "Liest sich als H. Die schräg geschnittenen Enden geben die eigenständigste Silhouette, auch bei 16 px; der Schnitt ist der des Wurf-Kopfs."),
    "h": ("h", "Der kurze rechte Stamm macht ein kleines h, je nach Schrift auch ein «n» mit Fahne. Raus."),
}


def section():
    v = ""
    for key, name, note, opt in VARIANTS:
        m = hlauf(**opt)
        r, verdict = READ[key]
        ok = r == "H" and key in ("a", "b", "g", "f")
        v += (f'<figure class="var{" out" if not ok else ""}"><div class="pic">{sz(svg(m), 120, 120, name)}</div>'
              f'<div class="small">{sz(svg(m), 16, 16)} {sz(svg(m), 24, 24)} {sz(svg(m), 32, 32)}</div>'
              f'<b>{key} {name}</b><span>{note}</span><span class="rd">Gelesen als: <em>{r}</em>. {verdict}</span></figure>')
    extra = ""
    for name, fn, verdict in (("Kreuzung 5 x 2: Querstrich als Torraumbogen", cross, "Liest sich als H mit durchhängendem Querstrich, eher Hängematte als Torraum. Mit Punkt darunter wurde es ein Gesicht. Der Bogen erklärt sich nur mit Text. Nicht weiter."),
                              ("Feld schräg", feld_schraeg, "Die Schräge nimmt das Schild weg; es wird ein Zeichen in Bewegung, bleibt aber klar Feld und H. Bei 16 px sicher. Kommt in den Härtetest."),
                              ("Feld mit einem Bogen", feld_einbogen, "Nur ein Torraum: liest sich als halbes Feld oder als Bilderrahmen mit Henkel. Weniger Schild, aber auch weniger H. Nicht weiter.")):
        extra += (f'<figure class="var"><div class="pic">{sz(svg(fn()), 120, 120, name)}</div>'
                  f'<div class="small">{sz(svg(fn()), 16, 16)} {sz(svg(fn()), 24, 24)} {sz(svg(fn()), 32, 32)}</div><b>{name}</b><span class="rd">{verdict}</span></figure>')

    px = ""
    for code, name, fn, k in FINALISTS:
        r16, r32 = PIX[k + "16"], PIX[k + "32"]
        px += (f'<figure class="px"><b>{code} {name}</b><div class="pxrow">'
               f'<div>{sz(pixsvg(r16, STOFF, INK), 128, 128, "16 px vergrössert")}<span>16 px, achtfach</span></div>'
               f'<div>{sz(pixsvg(r32, STOFF, INK), 128, 128, "32 px vergrössert")}<span>32 px, vierfach</span></div>'
               f'<div class="real">{sz(pixsvg(r16, STOFF, INK), 16, 16, "16 px")} {sz(pixsvg(r32, STOFF, INK), 32, 32, "32 px")}<span>Originalgrösse</span></div>'
               f'<div class="tab2">{sz(pixsvg(r16, STOFF, INK), 16, 16)}Handball Intelligence</div></div></figure>')

    wm = (f'<div class="wm"><div><span class="lab">gesetzt, Kanit ExtraBold Italic</span>{sz(wordmark_plain("title"), None, 44)}</div>'
          f'<div><span class="lab">angepasst, gross</span>{sz(wordmark("title"), None, 44)}</div>'
          f'<div><span class="lab">angepasst, klein</span>{sz(wordmark("lower"), None, 44)}</div>'
          f'<div class="two"><div><span class="lab">zweizeilig, gross</span>{sz(wordmark("title", two=True), None, 96)}</div><div><span class="lab">zweizeilig, klein</span>{sz(wordmark("lower", two=True), None, 96)}</div></div></div>')

    sizes = ""
    for code, name, fn, k in FINALISTS:
        cells = "".join(f'<td>{sz(svg(fn()), p, p, f"{p} px")}</td>' for p in (16, 24, 32, 64))
        on = ""
        for bg, fg, lab in (("#1f4fd6", "#ffffff", "Blau"), ("#f6c500", INK, "Gelb"), ("#ffffff", INK, "Weiss"), ("#17191c", "#ffffff", "Schwarz")):
            on += f'<td><span class="chip" style="background:{bg};{"box-shadow:inset 0 0 0 1px #b9b5ad" if bg == "#ffffff" else ""}">{sz(svg(fn(fg)), 32, 32, lab)}</span></td>'
        sizes += f"<tr><th>{code} {name}</th>{cells}{on}</tr>"

    def ghost(i):
        shapes = ['<circle cx="24" cy="24" r="11" fill="#fff" fill-opacity=".85"/>', '<path d="M14 32L24 14L34 32Z" fill="#fff" fill-opacity=".85"/>',
                  '<rect x="14" y="16" width="5" height="16" fill="#fff" fill-opacity=".85"/><rect x="21.5" y="20" width="5" height="12" fill="#fff" fill-opacity=".85"/><rect x="29" y="12" width="5" height="20" fill="#fff" fill-opacity=".85"/>',
                  '<path d="M12 24H36M24 12V36" stroke="#fff" stroke-opacity=".85" stroke-width="5"/>']
        tones = ["#7d8389", "#5f656b", "#9aa0a5", "#6c7277"]
        return sz(svg(f'<rect width="48" height="48" rx="10.7" fill="{tones[i]}"/>{shapes[i]}'), 60, 60, "neutrales App-Icon")

    homes = ""
    for code, name, fn, k in FINALISTS:
        ours = sz(svg(f'<rect width="48" height="48" rx="10.7" fill="{INK}"/><g transform="translate(10.8 10.8) scale(.55)">{fn(STOFF)}</g>'), 60, 60, name)
        labels = ["Liga", "Training", "Statistik", "Turnier"]
        apps = [f"<div>{ghost(i)}<span>{labels[i]}</span></div>" for i in range(4)]
        apps.insert(2, f'<div>{ours}<span>Handball Int…</span></div>')
        homes += f'<figure class="home"><div class="screen">{"".join(apps)}</div><figcaption>{code} {name}</figcaption></figure>'

    rec = final
    return f'''
<h2 id="runde2">Runde 2: Verfeinerung <small>nach der Rückmeldung zum ersten Durchgang</small></h2>
<p>Urteil zur Runde 1: «H im Lauf» hat als einzige Richtung eine eigene Idee, war aber nicht fertig gezeichnet. «Feld» las sich als Hinweisschild, «Anlauf» allein als Wasserhahn oder Hockeyschläger, Keil und Rückennummer als «HI»-Abzeichen nah an Wett- und Ligalogos. Diese Runde arbeitet deshalb nur an H im Lauf und Feld.</p>

<h3 class="sub">H im Lauf, acht Varianten <small>gross, dann 16, 24 und 32 px in Originalgrösse</small></h3>
<div class="vars">{v}</div>

<h3 class="sub">Kreuzung und Feld ohne Schild</h3>
<div class="vars three">{extra}</div>

<h3 class="sub">Favicons als Pixelzeichnung <small>für die drei Finalisten, auf dem Pixelraster gezeichnet, nicht verkleinert</small></h3>
<p>Bei 16 px: Stämme 3 Pixel, die Schräge ein Pixel pro drei Zeilen, ein Pixel Luft zwischen Punkt und rechtem Stamm, die Keil-Schnitte als je ein fehlendes Eckpixel. Bei 32 px: Stämme 6 Pixel, Punkt als gerundete Fläche von 6 x 8 Pixeln, Lauf zwei Pixel stark.</p>
<div class="pxs">{px}</div>

<h3 class="sub">Wortmarke</h3>
<p>Angepasst gegenüber gesetztem Kanit: Laufweite 0,6 Prozent enger; das doppelte l je 3,5 Prozent auseinander, damit «ll» nicht zur Wand wird; der Wortabstand auf 70 Prozent; der Punkt auf dem i rund wie die Wurfposition im Zeichen statt eckig; zweizeilig wird «Handball» so weit vergrössert, dass beide Zeilen gleich lang enden, und «Intelligence» rückt um die Schräge nach links.</p>
{wm}
<p><b>Empfehlung:</b> gross geschrieben («Handball Intelligence»). Klein wirkt freundlicher, aber «handball» klein liest sich wie ein Begriff, nicht wie ein Name, und neben dem Vereinsnamen («HC Zürichsee») stehen dann zwei Schreibweisen. Zweizeilig ist die Grundform neben dem Zeichen, einzeilig für schmale Köpfe.</p>

<h3 class="sub">Härtetest <small>einfarbig bei 16, 24, 32, 64 px, dann auf Blau, Gelb, Weiss, Schwarz</small></h3>
<div class="tw"><table class="hard"><thead><tr><th></th><th>16</th><th>24</th><th>32</th><th>64</th><th>Blau</th><th>Gelb</th><th>Weiss</th><th>Schwarz</th></tr></thead><tbody>{sizes}</tbody></table></div>
<p style="margin-top:16px">Auf dem Homescreen neben vier neutralen Sport-App-Platzhaltern:</p>
<div class="homes">{homes}</div>
<p>G fällt am meisten auf: die einzige Silhouette mit schräg geschnittenen Enden. B ist ruhiger, auf dem Homescreen aber ein schräges H unter vielen. F ist am sichersten lesbar, wirkt neben den anderen Icons aber wie ein Symbol aus einem Wegweiser.</p>

<div class="rec"><h3>Empfehlung: H im Lauf, Fassung G</h3>
<div style="display:flex;gap:28px;align-items:center;flex-wrap:wrap;margin:8px 0 16px">{sz(svg(rec(STOFF)), 120, 120, "Fassung G")}<span>{sz(svg(rec(STOFF)), 32, 32)} {sz(svg(rec(STOFF)), 16, 16)}</span>{sz(wordmark("title", STOFF, two=True), None, 80, "Handball Intelligence")}</div>
<p><b>Was sie von einem beliebigen schrägen H unterscheidet:</b> der Querstrich ist ein Anlauf, der vor dem rechten Stamm als Wurfposition endet, und die Stämme sind mit der Schräge des Wurf-Kopfs geschnitten, beides genau das, was die App misst und zeigt.</p>
<p>Zeichen: Stämme 7, 12 Grad, oben und unten 3 Einheiten Fall; Lauf 6,5; Punkt r 5,4 mit 1,8 Einheiten Luft zum Stamm. Dazu die angepasste Wortmarke gross, zweizeilig. Favicons als eigene Pixelzeichnungen. Dateien: <code>logos/final-*.svg</code>.</p>
<p>Zweite Wahl bleibt Feld, jetzt schräg gestellt.</p></div>
'''


CSS2 = """
h3.sub{font:italic 800 26px Kanit,sans-serif;margin:40px 0 12px}h3.sub small{font:600 14px "Hanken Grotesk",sans-serif;color:#53565b;font-style:normal;margin-left:10px}
.vars{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:24px 20px}.vars.three{grid-template-columns:repeat(3,minmax(0,1fr))}
.var .pic{background:#f7f6f2;display:grid;place-items:center;padding:14px}.var .small{display:flex;gap:12px;align-items:flex-end;margin-top:10px}
.var b{display:block;font:italic 800 17px Kanit,sans-serif;margin-top:8px}.var span{display:block;font-size:13px;color:#53565b;line-height:1.4}.var .rd{color:#16171a;margin-top:4px}
.var.out .pic{opacity:.5}
.pxs{display:flex;flex-direction:column;gap:20px}.px b{font:italic 800 18px Kanit,sans-serif}.pxrow{display:flex;gap:24px;align-items:flex-end;flex-wrap:wrap;margin-top:8px}
.pxrow span{display:block;font-size:12px;color:#53565b;margin-top:4px}.pxrow svg{display:block;image-rendering:pixelated}.pxrow .real{display:flex;gap:12px;align-items:flex-end;flex-wrap:wrap}
.tab2{display:flex;align-items:center;gap:8px;background:#dcdad4;padding:8px 14px 8px 10px;font:13px system-ui,sans-serif;width:220px}.tab2 svg{display:block}
.wm{display:flex;flex-direction:column;gap:18px;background:#f7f6f2;padding:22px}.wm .lab{display:block;font-size:12px;color:#53565b;margin-bottom:6px}.wm svg{display:block;max-width:100%;height:auto}
.wm .two{display:flex;gap:48px;flex-wrap:wrap}
table.hard th{font-size:13px}table.hard tbody th{border-bottom:1px solid #d6d3cc;vertical-align:middle;color:#16171a;font:italic 800 16px Kanit,sans-serif}table.hard td{vertical-align:middle}table.hard td svg{display:block}table.hard .chip{display:grid;place-items:center;width:56px;height:56px}
.homes{display:flex;gap:20px;flex-wrap:wrap}.home .screen{padding:20px 16px;background:#3d4b57;display:grid;grid-template-columns:repeat(5,60px);gap:12px}
.home .screen div{display:flex;flex-direction:column;align-items:center;gap:6px}.home .screen span{font:11px system-ui,sans-serif;color:#fff;white-space:nowrap}
@media (max-width:700px){.vars,.vars.three{grid-template-columns:repeat(2,minmax(0,1fr))}.home .screen{grid-template-columns:repeat(5,52px);gap:6px;padding:14px 8px}.home .screen svg{width:52px;height:52px}}
"""
