# Handball Intelligence: das Logo «Taktik»

Gewählt von Lukas aus zwölf Ideen (12. November 2026), hier ausgearbeitet. `index.html` im Browser
öffnen: zehn Varianten, Anordnung, Farbe, vier Wortmarken, Kleinfassungen, Härtetest, zwei
kritische Durchgänge, Entscheid. Bilder der Abschnitte in `shots/`, die zehn Varianten als SVG in
`varianten/`, die fertigen Dateien in `final/`.

## Die Fassung

Gewählt von Lukas am 12. November 2026: Variante v06 «Mischung · Wurf · Tor, Torraum, 9 m». Meine
Empfehlung war der Durchbruch mit zwei Kreuzen (v10); sie ist damit vom Tisch.

**Zeichen** (`final/zeichen.svg`): ein Spielzug auf der Taktiktafel. Oben Torlinie und Tor, der
Handball-Torraum (Halbkreis mit gerader Mitte) und die gepunktete 9-Meter-Linie. Unten links unsere
Spielerin als Kreis, rechts ein Verteidiger als Kreuz, und ihr Lauf als geschwungener Pfeil am
Verteidiger vorbei über die 9-Meter-Linie zum Torraum. Kreis und Kreuz sind geometrisch, der Pfeil
ist von Hand gezeichnet. Die Feldlinien setzen um Kreis, Kreuz und Pfeil aus.

Ausgearbeitet gegenüber v06, ohne den Charakter zu ändern (Vergleich oben auf der Seite):
- Der Pfeil ist ein fester Pfad (`RUN` in `build.js`): zwei Bögen, die sich gegen Ende etwas mehr
  biegen, Pfeilarme leicht ungleich lang. Kein Zufallsgenerator mehr.
- Strichstärken optisch ausgeglichen: Kreis 24 statt 26 (Radius 33), Pfeil 24, Kreuz 26, Feld 10,
  Tor 22 hoch (Einheiten im Raster 512).
- Kreis und Kreuz 2 bis 4 Einheiten zur Mitte; die Feldlinien setzen mit 11 Einheiten Luft aus.

**Wortmarke** (`final/wortmarke-zweizeilig.svg`): «Handball Intelligence» in Kanit ExtraBold
Italic, der Titelschrift der App, «Intelligence» im Blau des Laufs. Dazu quer und gestapelt.

Das sieht man: «Ein Spielzug, wie die Trainerin ihn an die Tafel malt.»

## Farben

| Name | Wert | Wofür |
|---|---|---|
| Tinte | `#111316` | Feld, Wortmarke «Handball»; einfarbige Fassung |
| Markerblau | `#1d47d1` | unsere Spielerin, der Lauf, «Intelligence» |
| Markerrot | `#e1251b` | der Verteidiger |
| Tafelweiss | `#f7f8f6` | Grund des App-Icons und des Teilen-Bilds |

- **In der App:** nur Tinte (`zeichen-tinte.svg`, `favicon-32-tinte.svg`, `favicon-16-tinte.svg`)
  oder Weiss auf dunklem Grund (`zeichen-weiss.svg`, `favicon-32-weiss.svg`). Die Farben gehören in der App den Teams; das Logo nimmt keine.
- **Ausserhalb der App** (App-Icon, Website, Teilen-Bild, Jacke, Banner): die zweifarbige Fassung.
- **Auf einer Vereinsfarbe** immer einfarbig: Weiss auf Blau, Rot, Schwarz, Grün; Tinte auf Gelb
  und Weiss.

## Schutzraum und Mindestgrösse

- **Schutzraum:** rundherum mindestens die Breite des Tors im Zeichen (3 Meter im Massstab des
  Zeichens, 60 von 512 Einheiten, also knapp 12 % der Zeichenbreite). Bei der Wortmarke dieselbe
  Einheit, gemessen am Zeichen in der Wortmarke.
- **Mindestgrösse:** das volle Zeichen ab 48 px oder 15 mm Breite. Darunter die eigene
  32-px-Fassung (`favicon-32.svg`, bis 24 px; sie behält vier Punkte der 9-Meter-Linie), darunter
  die 16-px-Fassung (ohne 9-Meter-Linie). Die Wortmarke
  zweizeilig ab 140 px oder 35 mm Breite, quer ab 220 px oder 55 mm.
- **Stick:** einfarbig, ab 6 cm Breite das volle Zeichen, darunter die 32-px-Fassung.

## Was man nicht tun soll

- Kreis, Kreuz und Pfeil ohne Torraum zeigen. Ohne Feld ist es American Football oder Basketball.
- Die Spielerinnen oder den Pfeil umfärben, zum Beispiel in die Vereinsfarbe.
- Das Zeichen drehen, spiegeln oder den Pfeil nach unten zeigen lassen. Die quere Fassung (Feld um
  90 Grad gedreht) nur dort, wo die Höhe fehlt.
- Weitere Spielerinnen oder Kreuze, Ball, Schatten, Verläufe oder einen Rahmen dazufügen.
- Den Pfeil neu zeichnen, glätten oder durch ein Pfeil-Symbol ersetzen. Er ist die Hand im Zeichen und ein fester Pfad.
- Ein Play-Dreieck in den Kreis setzen (Nähe zu «Once Sport»), das Zeichen «XO» nennen oder auf
  Rasengrün und Parkettbraun stellen (Nähe zu Playbook-Apps anderer Sportarten).
- Die zweifarbige Fassung auf eine Vereinsfarbe legen.

## Dateien in `final/`

| Datei | Was |
|---|---|
| `zeichen.svg`, `zeichen-tinte.svg`, `zeichen-tinte-akzent.svg`, `zeichen-weiss.svg`, `zeichen-negativ.svg`, `zeichen-1024.png` | das Zeichen in allen Farben |
| `wortmarke-quer*.svg`, `wortmarke-zweizeilig*.svg`, `wortmarke-gestapelt*.svg` | je farbig, `-einfarbig`, `-negativ` (auf Tinte) und `-weiss` (transparent); Schrift als Pfade |
| `favicon-16.svg`, `favicon-16.png`, `favicon-32.svg`, `favicon-32.png` | eigene Zeichnungen auf dem Pixelraster, zweifarbig; 32 px mit vier 9-Meter-Punkten, 16 px ohne |
| `favicon-32-tinte.svg`, `favicon-32-weiss.svg`, `favicon-16-tinte.svg` | dieselben für die App (Tinte, Weiss) |
| `app-icon.svg`, `app-icon-1024.png`, `app-icon-512.png` | iOS: volle Fläche, ohne Ecken (iOS rundet selbst) |
| `app-icon-maske.svg`, `app-icon-maske-1024.png`, `app-icon-maske-512.png` | Android adaptiv und Web-Manifest «maskable»: Zeichen in der sicheren Zone (Kreis mit 80 % Durchmesser) |
| `app-icon-einfarbig.svg` | Android «Designs» (einfarbiges Symbol, transparent) |
| `open-graph.svg`, `open-graph.png` | Vorschau geteilter Links, 1200 × 630 |

## Bauen

```
npm i opentype.js@1.3.4
node docs/design/brand2/taktik/build.js    # Varianten, final/*.svg, data.json
node docs/design/brand2/taktik/page.js     # index.html
node docs/design/brand2/taktik/render.js   # final/*.png, shots/
```

Schriften in `fonts/`, alle SIL Open Font License: Kanit, Archivo, Familjen Grotesk, Bricolage
Grotesque.

## Abstand zu bestehenden Zeichen

Kurze Suche im Netz, keine rechtliche Prüfung. Kreis, Kreuz und Pfeil sind die Sprache von
Playbook-Apps im American Football und Basketball (zum Beispiel «Playmaker X», «X's & O's»). Die
Videoanalyse «Once Sport» setzt ein Play-Dreieck in ein O. Davon halten der Handball-Torraum, die
9-Meter-Linie, der gezogene Pfeil und die Regeln oben Abstand. Vor einer Markenanmeldung: Recherche
in Swissreg und EUIPO, Klassen 9, 41 und 42.

## Was noch nicht sauber ist

- Die 16-px-Fassung ist auf dem Raster gezeichnet, aber nicht auf jedem Bildschirm und in jedem
  Browser geprüft.
- Die 9-Meter-Punkte sind beim Stick unter 6 cm Breite zu fein; dafür gibt es die 32-px-Fassung.
- Die Wortmarke ist mit den Abständen von Kanit gesetzt, nicht von Hand ausgeglichen.
- Keine rechtliche Markenprüfung.
