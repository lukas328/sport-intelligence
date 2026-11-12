/* Builds index.html from data.json (written by build.js) and the files in final/.
   node docs/design/brand2/taktik/page.js */
"use strict";
const fs = require("fs"), path = require("path");
const here = __dirname, D = JSON.parse(fs.readFileSync(path.join(here, "data.json"), "utf8"));
const O = D.out, V = Object.fromEntries(D.V.map((v) => [v.id, v]));
const fin = (n, cls = "", label = "Handball Intelligence") => O[n].replace("<svg ", `<svg class="${cls}" role="img" aria-label="${label}" `);
const inl = (s, cls = "", label = "") => s.replace("<svg ", `<svg class="${cls}" ${label ? `role="img" aria-label="${label}"` : 'aria-hidden="true"'} `);
const vcard = (id, note) => `<figure class="v"><div class="vb">${inl(V[id].svg, "vm", V[id].label)}</div><figcaption><b>${V[id].label}</b><span class="tiny">${inl(V[id].svg, "s32")}${inl(V[id].small, "s32")}<em>32 px</em></span>${note ? `<p>${note}</p>` : ""}</figcaption></figure>`;
const icon = (s, cls) => s.replace("<svg ", `<svg class="${cls}" aria-hidden="true" `);

const html = `<!doctype html>
<html lang="de-CH">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Taktik Logo</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62..125,400..900&family=Kanit:ital,wght@1,800&display=swap">
<style>
/* Layout: a long sheet of boards, one question per board, the answer as pictures. */
:root { color-scheme: light; --bg: #e9ebee; --paper: #ffffff; --board: #f7f8f6; --ink: #111316; --ink-2: #535a62; --rule: #d5d8dc; --blue: #1d47d1; --red: #e1251b; --f: "Archivo", system-ui, sans-serif; --k: "Kanit", "Archivo", sans-serif; }
*, *::before, *::after { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--ink); font: 400 16px/1.5 var(--f); }
.wrap { max-width: 1320px; margin: 0 auto; padding-block: 48px 96px; padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); display: grid; grid-template-columns: minmax(0, 1fr); gap: 40px; }
h1, h2, h3, p, figure, ul, ol { margin: 0; }
.intro { display: grid; gap: 16px; max-width: 960px; }
.lab { font: 700 13px/1.2 var(--f); font-stretch: 125%; letter-spacing: .08em; text-transform: uppercase; color: var(--ink-2); }
.intro h1 { font: 900 clamp(44px, 8vw, 104px)/.9 var(--f); font-stretch: 75%; letter-spacing: -.02em; text-wrap: balance; }
.intro p { font-size: 19px; color: var(--ink-2); max-width: 64ch; }
.intro nav { display: flex; flex-wrap: wrap; gap: 6px 18px; font-weight: 700; }
.intro nav a { color: var(--ink); text-underline-offset: 4px; }
.sec { background: var(--paper); padding: 32px; display: grid; grid-template-columns: minmax(0, 1fr); gap: 24px; scroll-margin-top: 16px; }
.sec > h2 { font: 900 36px/1 var(--f); font-stretch: 80%; }
.sec > .lead { max-width: 72ch; color: var(--ink-2); font-size: 17px; }
.grid5 { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 20px; }
.grid3 { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(280px, 100%), 1fr)); gap: 20px; }
.grid3 > * { min-width: 0; }
.v { display: grid; gap: 10px; align-content: start; min-width: 0; }
.vb { background: var(--board); aspect-ratio: 1; display: grid; place-items: center; }
.vm { width: 100%; height: auto; }
.v figcaption { display: grid; gap: 6px; font-size: 14px; }
.v .tiny { display: flex; gap: 10px; align-items: center; color: var(--ink-2); font-size: 12px; }
.v .tiny em { font-style: normal; }
.s32 { width: 32px; height: 32px; }
.v p { color: var(--ink-2); font-size: 14px; }
.verdict { border-top: 2px solid var(--ink); padding-top: 14px; max-width: 80ch; display: grid; gap: 8px; }
.verdict b { font-weight: 800; }
.box { background: var(--board); padding: 24px; display: grid; place-items: center; min-width: 0; }
.box svg { max-width: 100%; height: auto; }
.ovl { position: relative; width: 100%; }
.ovl svg { display: block; width: 100%; height: auto; }
.ovl svg:first-child { opacity: .3; }
.ovl svg + svg { position: absolute; inset: 0; mix-blend-mode: multiply; opacity: .85; }
.cap { font-size: 14px; color: var(--ink-2); margin-top: 8px; }
.wm { display: grid; gap: 16px; padding: 20px; background: var(--board); min-width: 0; }
.wm.rec { box-shadow: inset 0 0 0 3px var(--ink); }
.wm h3 { font: 800 18px/1.2 var(--f); }
.wm p { font-size: 14px; color: var(--ink-2); }
.wm .row { display: grid; grid-template-columns: minmax(0, 3fr) minmax(0, 2fr) minmax(0, 1.2fr); gap: 16px; align-items: center; }
.wm svg { width: 100%; height: auto; max-height: 120px; }
.sizes { display: flex; flex-wrap: wrap; gap: 28px; align-items: flex-end; }
.sizes figure { display: grid; justify-items: center; gap: 6px; font-size: 12px; color: var(--ink-2); }
.pxgrid { width: 192px; height: 192px; image-rendering: pixelated; background: #fff; box-shadow: inset 0 0 0 1px var(--rule); }
.bgs { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 12px; }
.bgs div { aspect-ratio: 1.2; display: grid; place-items: center; }
.bgs svg { width: 60%; height: auto; }
.bgs span { font-size: 12px; color: var(--ink-2); }
.home { background: #2a3d5c; padding: 32px 12px; display: grid; place-items: center; }
.home .ph { width: min(300px, 100%); padding: 30px 22px; border-radius: 36px; background: #1b2b47; box-shadow: 0 0 0 7px #0c0e11; display: grid; grid-template-columns: repeat(4, 1fr); gap: 18px 12px; }
.home .app { display: grid; justify-items: center; gap: 6px; font: 500 10.5px/1.1 -apple-system, system-ui, sans-serif; color: #fff; text-align: center; }
.home .app i, .home .app svg { width: 54px; height: 54px; border-radius: 12px; display: block; }
.home .app i { opacity: .7; }
.bar { display: flex; align-items: center; gap: 16px; height: 64px; padding: 0 24px; background: #fff; box-shadow: 0 1px 0 var(--rule); font-size: 15px; }
.bar .brand { display: flex; align-items: center; gap: 10px; }
.bar .brand svg { height: 34px; width: auto; }
.bar .sep { width: 1px; height: 28px; background: var(--rule); }
.crest { width: 24px; height: 28px; background: #d3202e; clip-path: polygon(0 0, 100% 0, 100% 64%, 50% 100%, 0 64%); flex: none; }
.bar .team b { display: block; font-weight: 800; line-height: 1.1; }
.bar .team small { color: var(--ink-2); font-size: 12.5px; }
.bar nav { display: flex; gap: 20px; margin-left: 24px; color: var(--ink-2); font-weight: 600; }
.bar nav .on { color: var(--ink); box-shadow: 0 3px 0 #d3202e; padding-bottom: 4px; }
.phonebar { width: 390px; max-width: 100%; display: flex; align-items: center; gap: 10px; height: 60px; padding: 0 14px; background: #fff; box-shadow: 0 0 0 1px var(--rule); }
.phonebar svg { width: 30px; height: 30px; flex: none; }
.phonebar .team { font-weight: 800; font-size: 15px; line-height: 1.1; }
.phonebar .team small { display: block; font-weight: 400; color: var(--ink-2); font-size: 12px; }
.phonebar .plus { margin-left: auto; width: 40px; height: 40px; background: var(--ink); color: #fff; display: grid; place-items: center; font-size: 22px; }
.login { background: var(--board); padding: 40px 12px; display: grid; place-items: center; }
.login, .chat, .jacket, .home { min-width: 0; }
.login .card { width: min(360px, 100%); background: #fff; padding: 32px 28px; display: grid; gap: 16px; box-shadow: 0 0 0 1px var(--rule); }
.login .card svg { width: 220px; height: auto; justify-self: center; }
.login label { font-size: 13px; font-weight: 600; display: grid; gap: 6px; }
.login .f { height: 44px; box-shadow: inset 0 0 0 1.5px var(--ink); background: #fff; }
.login .btn { height: 48px; background: var(--ink); color: #fff; display: grid; place-items: center; font-weight: 700; }
.chat { background: #e5ddd5; padding: 24px 16px; display: grid; justify-items: end; overflow: hidden; }
.bubble { width: min(340px, 100%); background: #dcf8c6; border-radius: 8px; padding: 4px; font-size: 14px; box-shadow: 0 1px 1px rgb(0 0 0 / .15); }
.bubble .prev { background: #f0f2f0; border-radius: 6px; overflow: hidden; }
.bubble .prev svg { display: block; width: 100%; height: auto; }
.bubble .prev p { padding: 8px 10px; font-size: 13px; }
.bubble .prev small { display: block; color: #667; }
.bubble > p { padding: 6px 6px 2px; }
.jacket { background: #c3c8ce; display: grid; place-items: center; padding: 24px 0 0; }
.jacket .jk { position: relative; width: min(380px, 100%); }
.jacket .jk > svg { width: 100%; display: block; }
.jacket .em { position: absolute; left: 58%; top: 22%; width: 28%; }
.jacket .em svg { width: 100%; height: auto; }
.list { list-style: disc; padding-left: 1.2em; display: grid; gap: 8px; max-width: 80ch; }
.final { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 24px; }
.final .rec { box-shadow: inset 0 0 0 3px var(--ink); }
code { font: 500 .88em/1.3 ui-monospace, Menlo, Consolas, monospace; background: var(--board); padding: 1px 4px; overflow-wrap: anywhere; }
table { border-collapse: collapse; width: 100%; font-size: 14px; }
th, td { text-align: left; padding: 8px 12px 8px 0; border-bottom: 1px solid var(--rule); vertical-align: top; }
.tw { overflow-x: auto; }
@media (max-width: 760px) { .sec { padding: 20px; } .final { grid-template-columns: 1fr; } .wm .row { grid-template-columns: 1fr; } .bar nav { display: none; } }
</style>
</head>
<body>
<div class="wrap">
<header class="intro">
  <p class="lab">Handball Intelligence · Logo · endgültige Fassung</p>
  <h1>Ein Wurf am Verteidiger vorbei, auf die Tafel gezeichnet</h1>
  <p>Lukas hat am 12. November 2026 «Mischung · Wurf · Tor, Torraum, 9 m» gewählt. Oben steht die ausgearbeitete Fassung mit allen Dateien und dem Härtetest, darunter der Weg dorthin: zehn Varianten, Anordnung, Farbe, Wortmarke, Kleinfassungen, Durchgänge.</p>
  <nav aria-label="Abschnitte"><a href="#gewaehlt">Die Fassung</a><a href="#haerte">Härtetest</a><a href="#dateien">Dateien</a><a href="#weg">Der Weg dorthin</a><a href="#varianten">Varianten</a><a href="#anordnung">Anordnung</a><a href="#farbe">Farbe</a><a href="#wortmarke">Wortmarke</a><a href="#klein">Klein</a><a href="#durchgaenge">Durchgänge</a></nav>
</header>

<section class="sec" id="gewaehlt">
  <h2>Die Fassung</h2>
  <p class="lead">Das sieht man: einen Spielzug, wie die Trainerin ihn an die Tafel malt. Oben das Tor mit dem Torraum und der gepunkteten 9-Meter-Linie, unten unsere Spielerin als Kreis, rechts ein Verteidiger als Kreuz, und ihr Lauf als geschwungener Pfeil am Verteidiger vorbei zum Torraum.</p>
  <div class="final"><div class="box rec">${fin("zeichen.svg", "", "Handball Intelligence, Zeichen")}</div><div class="box">${fin("wortmarke-zweizeilig.svg", "", "Handball Intelligence, Wortmarke zweizeilig")}</div></div>
  <h3>Alt und neu: dasselbe Zeichen</h3>
  <div class="grid3"><div><div class="box">${inl(D.chosen, "", "gewählte Variante v06")}</div><p class="cap">Gewählt: v06, wie sie auf der Seite stand.</p></div><div><div class="box">${fin("zeichen.svg", "", "ausgearbeitete Fassung")}</div><p class="cap">Ausgearbeitet: gleiche Anordnung, gleiche Linien, gleiche Farben.</p></div><div><div class="box"><div class="ovl">${inl(D.chosenInk, "", "v06 in Tinte")}${inl(D.finalInk, "", "neu in Tinte")}</div></div><p class="cap">Übereinandergelegt: alt hell, neu dunkel. Wo nur dunkel zu sehen ist, deckt sich beides.</p></div></div>
  <ul class="list">
    <li><b>Der Pfeil ist einmal gezeichnet:</b> ein fester Pfad aus zwei Bögen, der sich gegen Ende etwas mehr biegt, mit einem Pfeilkopf, dessen Arme leicht ungleich lang sind. Kein Zufallsgenerator mehr; er sieht in jeder Datei gleich aus.</li>
    <li><b>Strichstärken optisch ausgeglichen:</b> Der Kreis wirkte bei gleicher Stärke schwerer als das Kreuz. Er ist jetzt 24 statt 26 Einheiten stark und dafür 1 Einheit grösser; der Pfeil hat die Stärke des Kreises. Feld 10, Tor 22 hoch.</li>
    <li><b>Abstände:</b> Kreis und Kreuz um 2 bis 4 Einheiten zur Mitte gerückt, damit das Zeichen nicht links unten schwerer ist. Die Feldlinien setzen um Kreis, Kreuz und Pfeil mit 11 Einheiten Luft aus, wie beim Absetzen des Stifts.</li>
  </ul>
  <div class="grid3">
    <div><div class="box">${fin("wortmarke-quer.svg", "", "Wortmarke quer")}</div><p class="cap">Quer</p></div>
    <div><div class="box">${fin("wortmarke-gestapelt.svg", "", "Wortmarke gestapelt").replace("<svg ", '<svg style="max-height:260px" ')}</div><p class="cap">Gestapelt</p></div>
    <div><div class="box" style="background:#111316">${fin("wortmarke-zweizeilig-weiss.svg", "", "Wortmarke weiss")}</div><p class="cap">Weiss auf Tinte</p></div>
  </div>
  <div class="verdict"><p><b>Farbregel:</b> In der App nur Tinte <code>#111316</code> (oder Weiss auf dunklem Grund), denn dort gehören die Farben den Teams. Ausserhalb der App Markerblau <code>#1d47d1</code> für unsere Spielerin, den Lauf und «Intelligence», Markerrot <code>#e1251b</code> für den Verteidiger, Tinte für Feld und «Handball», Tafelweiss <code>#f7f8f6</code> als Grund. Auf einer Vereinsfarbe immer einfarbig.</p></div>
</section>

<section class="sec" id="haerte">
  <h2>Härtetest</h2>
  <h3>Grössen</h3>
  <div class="sizes">${[16, 24, 32, 64].map((s) => `<figure>${s <= 32 ? fin(s <= 16 ? "favicon-16.svg" : "favicon-32.svg", "", s + " px").replace("<svg ", `<svg style="width:${s}px;height:${s}px" `) : fin("zeichen.svg", "", "64 px").replace("<svg ", `<svg style="width:${s}px;height:${s}px" `)}<figcaption>${s} px</figcaption></figure>`).join("")}${[16, 24, 32, 64].map((s) => `<figure>${fin("zeichen-tinte.svg", "", s + " px einfarbig").replace("<svg ", `<svg style="width:${s}px;height:${s}px" `)}<figcaption>${s} px, grosses Zeichen einfarbig</figcaption></figure>`).join("")}</div>
  <p class="cap">Links die eigenen Kleinfassungen (bei 16 px ohne 9-Meter-Punkte, bei 24 und 32 px mit vier Punkten), rechts das grosse Zeichen verkleinert: unter 48 px verliert es die Punkte und der Torraum wird dünn, darum die eigenen Fassungen.</p>
  <h3>Auf Vereinsfarben</h3>
  <div class="bgs">${[["Blau", "#1f4fbf", "#ffffff"], ["Rot", "#d3202e", "#ffffff"], ["Gelb", "#f6c500", "#111316"], ["Weiss", "#ffffff", "#111316"], ["Schwarz", "#15171a", "#ffffff"], ["Grün", "#0f7a46", "#ffffff"]].map((c) => `<div style="background:${c[1]};box-shadow:inset 0 0 0 1px var(--rule)">${(c[2] === "#ffffff" ? O["zeichen-weiss.svg"] : O["zeichen-tinte.svg"]).replace("<svg ", '<svg aria-hidden="true" ')}</div>`).join("")}</div>
  <p class="cap">Auf Farbe immer einfarbig: Weiss auf Blau, Rot, Schwarz, Grün; Tinte auf Gelb und Weiss. Blau-Rot nie auf einer Vereinsfarbe.</p>
  <h3>Neben anderen Apps</h3>
  <div class="home"><div class="ph">${["#3a7bd5", "#2fb36e", "#f2a33a", "#8e5bd8", "#e0533c", null, "#5ac8fa", "#ffcc00", "#34c759", "#ff2d55", "#1c1c1e", "#af52de"].map((c) => c ? `<div class="app"><i style="background:${c}"></i>App</div>` : `<div class="app">${icon(O["app-icon.svg"], "")}Handball In…</div>`).join("")}</div></div>
  <h3>Im Kopf der App, links neben dem Vereinswappen</h3>
  <div class="bar"><span class="brand">${O["favicon-32-tinte.svg"].replace("<svg ", '<svg aria-hidden="true" style="width:32px;height:32px" ')}</span><span class="sep"></span><span class="crest" aria-hidden="true"></span><span class="team"><b>HC Zürichsee</b><small>Herren 1 · 3. Liga</small></span><nav><span class="on">Spiele</span><span>Szenen</span><span>Saison</span><span>Team</span></nav></div>
  <div class="phonebar">${O["favicon-32-tinte.svg"].replace("<svg ", '<svg aria-hidden="true" ')}<span class="crest" aria-hidden="true"></span><span class="team">Herren 1<small>HC Zürichsee</small></span><span class="plus" aria-hidden="true">+</span></div>
  <p class="cap">In der App steht nur das kleine Zeichen in Tinte vor dem Wappen des Vereins; die Farben gehören dort den Teams. Der Name der App steht nicht im Kopf: Die Trainerin weiss, wo sie ist; das Wappen ist wichtiger.</p>
  <div class="grid3">
    <div><div class="login"><div class="card">${O["wortmarke-gestapelt.svg"].replace("<svg ", '<svg role="img" aria-label="Handball Intelligence" ')}<label>E-Mail<span class="f"></span></label><label>Passwort<span class="f"></span></label><span class="btn">Anmelden</span></div></div><p class="cap">Anmeldeseite: die gestapelte Wortmarke.</p></div>
    <div><div class="chat"><div class="bubble"><div class="prev">${O["open-graph.svg"].replace("<svg ", '<svg role="img" aria-label="Vorschaubild" ')}<p><b>Rückzug nach Ballverlust</b><small>handballintelligence.ch</small></p></div><p>Schaut euch das bis Dienstag an.</p></div></div><p class="cap">Vorschau eines geteilten Links im Teamchat (Open-Graph-Bild 1200 × 630).</p></div>
    <div><div class="jacket"><div class="jk"><svg viewBox="0 0 400 300" aria-hidden="true"><path d="M110 20 L160 8 Q200 30 240 8 L290 20 L370 70 L340 300 L60 300 L30 70 Z" fill="#14213d"/><path d="M200 26 V300" stroke="#0a1328" stroke-width="4"/><path d="M160 8 Q200 30 240 8 L232 30 Q200 46 168 30 Z" fill="#0a1328"/></svg><div class="em">${O["zeichen-weiss.svg"].replace("<svg ", '<svg aria-hidden="true" ')}</div></div></div><p class="cap">Gestickt auf der Trainerjacke, einfarbig weiss.</p></div>
  </div>
</section>

<section class="sec" id="dateien">
  <h2>Dateien</h2>
  <p class="lead">Alles liegt in <code>docs/design/brand2/taktik/final/</code>. Regeln (Schutzraum, Mindestgrösse, Farben, was man nicht tut) im <code>README.md</code> daneben.</p>
  <ul class="list">
    <li>Zeichen: <code>zeichen.svg</code> (zweifarbig), <code>zeichen-tinte.svg</code>, <code>zeichen-tinte-akzent.svg</code> (Tinte, Pfeil blau), <code>zeichen-weiss.svg</code>, <code>zeichen-negativ.svg</code> (weiss auf Tinte), <code>zeichen-1024.png</code>.</li>
    <li>Wortmarke in Kanit ExtraBold Italic, Schrift als Pfade: <code>wortmarke-quer</code>, <code>-zweizeilig</code>, <code>-gestapelt</code>, je <code>.svg</code> (farbig), <code>-einfarbig.svg</code>, <code>-negativ.svg</code>, <code>-weiss.svg</code>.</li>
    <li>Favicon, eigene Zeichnungen auf dem Pixelraster: <code>favicon-32.svg</code> und <code>.png</code> (mit vier Punkten der 9-Meter-Linie), <code>favicon-16.svg</code> und <code>.png</code> (ohne 9-Meter-Linie), dazu <code>favicon-32-tinte.svg</code>, <code>favicon-32-weiss.svg</code>, <code>favicon-16-tinte.svg</code> für die App.</li>
    <li>App-Icon: <code>app-icon-1024.png</code>, <code>app-icon-512.png</code> (iOS, volle Fläche ohne Ecken), <code>app-icon-maske-1024.png</code>, <code>app-icon-maske-512.png</code> (Android adaptiv und Web «maskable», Zeichen in der sicheren Zone), <code>app-icon-einfarbig.svg</code> (Android «Designs»).</li>
    <li>Teilen: <code>open-graph.svg</code>, <code>open-graph.png</code> (1200 × 630).</li>
  </ul>
  <h3>Abstand zu bestehenden Zeichen</h3>
  <ul class="list">
    <li>Kreis, Kreuz und Pfeil sind die Sprache von Playbook-Apps im American Football und Basketball (zum Beispiel «Playmaker X», «X's & O's»). Darum nie ohne Handball-Feld, nie als «XO» geschrieben, nie auf Rasengrün oder Parkettbraun.</li>
    <li>Die Videoanalyse «Once Sport» setzt ein Play-Dreieck in ein O. Darum nie ein Play-Symbol im Kreis, und der Pfeil bleibt ein gezogener Strich.</li>
    <li>Keine rechtliche Prüfung. Vor einer Anmeldung als Marke: Recherche in Swissreg und EUIPO in den Klassen 9, 41 und 42.</li>
  </ul>
</section>

<header class="intro" id="weg" style="margin-top:32px">
  <p class="lab">Der Weg dorthin</p>
  <h1 style="font-size:clamp(36px,6vw,72px)">Zehn Varianten und ein Entscheid</h1>
  <p>So stand die Seite vor dem Entscheid, mit meinen damaligen Empfehlungen. Meine Empfehlung war der Durchbruch (v10); gewählt hat Lukas v06.</p>
</header>

<section class="sec" id="varianten">
  <h2>Zehn Varianten</h2>
  <p class="lead">Jede gross und bei 32 px (zweifarbig und Tinte). Unter den drei Gruppen steht, was die Gruppe gezeigt hat.</p>
  <h3>Strich</h3>
  <div class="grid5">${vcard("v01", "Alles von Hand: lebendig, aber Kreis und Kreuz wirken bei kleiner Grösse ungenau.")}${vcard("v02", "Alles geometrisch: sauber, aber ein Piktogramm wie aus einer Symbolbibliothek.")}${vcard("v03", "Mischung: Kreis und Kreuz gebaut, der Pfeil gezogen. Die Hand sitzt dort, wo sich etwas bewegt.")}</div>
  <div class="verdict"><p><b>Ergebnis Strich:</b> Mischung. Die Spielerinnen sind Marken auf der Tafel und dürfen genau sein; der Lauf ist die Handlung der Trainerin und soll nach Hand aussehen. Das unterscheidet das Zeichen am stärksten von einem Clipart-Symbol.</p></div>
  <h3>Was drin ist</h3>
  <div class="grid5">${vcard("v04", "Nur Kreis, Kreuz, Pfeil: Das ist American Football oder Basketball. Ohne Feld liest niemand Handball.")}${vcard("v05", "Nur Tor: ein Tor gibt es in vielen Sportarten; noch kein Handball.")}${vcard("v03", "Tor und Torraum: der Halbkreis mit gerader Mitte ist der Handball-Torraum. Ab hier liest man Handball.")}${vcard("v06", "Tor, Torraum und gestrichelte 9-Meter-Linie: eindeutig Handball, die gepunktete Linie gibt es in keinem anderen Sport.")}</div>
  <div class="verdict"><p><b>Ergebnis Inhalt:</b> Der Torraum ist das Minimum. Die gestrichelte 9-Meter-Linie überlädt nicht, weil sie aus Punkten besteht und leicht wirkt, und sie ist das stärkste Handball-Signal. Bei 16 px fällt sie weg.</p></div>
  <h3>Der Spielzug</h3>
  <div class="grid5">${vcard("v07", "Durchbruch zwischen zwei Verteidigern: der Grundzug im Handball, jede Spielerin kennt ihn. Symmetrisch, ruhig, mit Richtung.")}${vcard("v08", "Lauf an den Kreis: erzählt viel, aber der Pfeil liegt quer und das Zeichen kippt nach rechts.")}${vcard("v09", "Kreuzen im Rückraum: zwei Läufe, ein Kreuz. Fachlich am schönsten, als Zeichen zu voll; bei 32 px ein Knäuel.")}${vcard("v10", "Durchbruch mit 9-Meter-Linie: der Lauf geht zwischen den beiden Verteidigern über die gepunktete Linie zum Torraum.")}</div>
  <div class="verdict"><p><b>Ergebnis Spielzug (meine damalige Empfehlung, nicht gewählt):</b> Durchbruch. Zwei Kreuze sind eine Abwehr, kein einzelner Gegner; der Pfeil geht durch die Lücke, also durch das, was die Analyse findet. Er zeigt nicht nur nach oben, er sucht einen Weg.</p></div>
</section>

<section class="sec" id="anordnung">
  <h2>Anordnung</h2>
  <p class="lead">Dasselbe Zeichen hoch, quadratisch und quer. Quadratisch ist die Grundform; sie füllt das App-Icon ohne Rand, weil Torlinie und Torraum oben bis an die Kante gehen.</p>
  <div class="grid3"><div><div class="box">${inl(D.layout.hoch, "", "hoch")}</div><p class="cap">Hoch: für Banner im Hochformat und das Profilbild in Chats.</p></div><div><div class="box">${inl(D.layout.quadrat, "", "quadratisch")}</div><p class="cap">Quadratisch: die Grundform.</p></div><div><div class="box">${inl(D.layout.quer, "", "quer")}</div><p class="cap">Quer, das Feld gedreht: geht, aber das Tor rechts liest sich langsamer. Nur wo die Höhe fehlt.</p></div></div>
</section>

<section class="sec" id="farbe">
  <h2>Farbe</h2>
  <div class="grid3"><div><div class="box">${inl(D.colors[0], "", "zweifarbig")}</div><p class="cap">Zweifarbig wie die Skizze: blau wir, rot der Gegner. Gefällt, hat aber zwei Probleme: Blau und Rot sind Teamfarben, und ein rotes Kreuz heisst sonst «falsch».</p></div><div><div class="box">${inl(D.colors[1], "", "Tinte")}</div><p class="cap">Tinte: so steht es in der App. Dort gehören die Farben den Teams, das Logo nimmt keine.</p></div><div><div class="box">${inl(D.colors[2], "", "Tinte mit Akzent")}</div><p class="cap">Tinte mit Blau nur auf dem Pfeil: der Lauf ist das, was die App findet. Die Marke ausserhalb der App.</p></div></div>
  <div class="verdict"><p><b>Vorschlag:</b> In der App immer Tinte (oder Weiss auf dunklem Grund), damit die Vereinsfarben allein bleiben. Ausserhalb der App (Website, App-Icon, Teilen-Bild, Jacke) die zweifarbige Fassung: Markerblau <code>#1d47d1</code> für uns und den Lauf, Markerrot <code>#e1251b</code> für die Abwehr. Das Rot ist hier kein Fehler, weil es zwei Kreuze sind, eine Abwehr, und weil Blau-Rot die Farben der Filzstifte an jeder Tafel sind. Wo nur eine Farbe geht (Stick, Stempel), Tinte.</p></div>
</section>

<section class="sec" id="wortmarke">
  <h2>Wortmarke</h2>
  <p class="lead">«Handball Intelligence» in vier Schriften, je quer, zweizeilig und gestapelt. «Intelligence» trägt das Blau des Laufs.</p>
  ${D.wm.map((w) => `<div class="wm${w.id === "kanit" ? " rec" : ""}"><h3>${w.name}${w.id === "kanit" ? " · Empfehlung" : ""}</h3><p>${w.why}</p><div class="row">${inl(w.quer, "", w.name + " quer")}${inl(w.zwei, "", w.name + " zweizeilig")}${inl(w.stapel, "", w.name + " gestapelt")}</div></div>`).join("")}
  <div class="verdict"><p><b>Empfehlung: Kanit ExtraBold Italic, zweizeilig.</b> Die Schräge der Schrift läuft mit dem Pfeil, und sie ist die Schrift der App «Anlauf»: Logo und Titel in der App sprechen dieselbe Sprache. Archivo ist die ruhigere zweite Wahl, falls die App ihre Titelschrift später ändert.</p></div>
</section>

<section class="sec" id="klein">
  <h2>Klein: eigene Fassungen für 16 und 32 px</h2>
  <p class="lead">Das grosse Zeichen verkleinert reicht nicht: Der Torraum wird zur Linie, die Punkte verschwinden. Darum zwei eigene Zeichnungen auf dem Pixelraster: Tor, Torraum, Kreuz, unsere Spielerin, der Pfeil mit nur einem Bogen. Bei 32 px bleiben vier Punkte der 9-Meter-Linie, bei 16 px fällt sie ganz weg.</p>
  <div class="sizes">
    <figure>${fin("favicon-32.svg", "pxgrid", "Favicon 32 px, vergrössert")}<figcaption>32 px, auf 6-fach vergrössert</figcaption></figure>
    <figure>${fin("favicon-16.svg", "pxgrid", "Favicon 16 px, vergrössert")}<figcaption>16 px, auf 12-fach vergrössert</figcaption></figure>
    <figure>${fin("favicon-32.svg", "s32", "Favicon 32 px")}<figcaption>32 px</figcaption></figure>
    <figure>${fin("favicon-16.svg", "", "Favicon 16 px").replace('class=""', 'style="width:16px;height:16px"')}<figcaption>16 px</figcaption></figure>
    <figure>${icon(O["app-icon.svg"], "").replace("<svg ", '<svg style="width:180px;height:180px;border-radius:40px" ')}<figcaption>App-Icon iOS (Ecken von iOS)</figcaption></figure>
    <figure><div style="width:180px;height:180px;border-radius:50%;overflow:hidden">${icon(O["app-icon-maske.svg"], "").replace("<svg ", '<svg style="width:180px;height:180px" ')}</div><figcaption>Android, runde Maske</figcaption></figure>
    <figure><div style="width:180px;height:180px;border-radius:50%;overflow:hidden;background:#2f4f46">${icon(O["app-icon-einfarbig.svg"], "").replace("<svg ", '<svg style="width:180px;height:180px" ')}</div><figcaption>Android, einfarbig (Designs)</figcaption></figure>
  </div>
</section>

<section class="sec" id="durchgaenge">
  <h2>Zwei kritische Durchgänge</h2>
  <div class="tw"><table>
    <thead><tr><th>Frage</th><th>Erster Durchgang</th><th>Zweiter Durchgang, nach den Änderungen</th></tr></thead>
    <tbody>
      <tr><td>Sieht es aus wie ein Clipart-Symbol für «Strategie»?</td><td>Ja, die geometrische Fassung ohne Feld (v02, v04): Kreis, Kreuz, Pfeil gibt es in jeder Symbolbibliothek.</td><td>Nein mehr: der gezogene Pfeil, der Handball-Torraum und die gepunktete 9-Meter-Linie. Ohne diese drei wird es wieder Clipart; sie bleiben Pflicht.</td></tr>
      <tr><td>Was macht es zu unserem?</td><td>Zuerst nur der Pfeil von Hand, der aber zackig und kaputt aussah.</td><td>Der Spielzug auf dem Handballfeld: ein Wurf am Verteidiger vorbei über die 9-Meter-Linie zum Torraum. Das zeichnet keine andere Sportart so.</td></tr>
      <tr><td>Würde ein Verein es auf eine Trainerjacke sticken?</td><td>Die zweifarbige Fassung mit dünnen Linien nicht: Stick braucht kräftige Striche.</td><td>Ja, einfarbig weiss. Die Feldlinien sind 10 Einheiten stark (2 mm bei 10 cm Breite), Kreis und Pfeil 24, das Kreuz 26. Die 9-Meter-Punkte sind die Grenze; unter 6 cm Breite die 32-px-Fassung sticken.</td></tr>
      <tr><td>Kann eine zwölfjährige Handballerin sagen, was das ist?</td><td>«Ein Spielzug» ja, «Handball» nur mit Torraum.</td><td>«Ein Spielzug, wie die Trainerin ihn an die Tafel malt.»</td></tr>
    </tbody>
  </table></div>
</section>

</div>
</body>
</html>
`;
fs.writeFileSync(path.join(here, "index.html"), html);
console.log("index.html", Math.round(html.length / 1024), "kB");
