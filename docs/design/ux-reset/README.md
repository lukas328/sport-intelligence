# UX-Neustart

Alles für den Umbau der Oberfläche von `apps/web`. Stand: 12. November 2026. Umgesetzt ist davon
noch nichts.

## Entschieden: Anlauf

**Die Richtung ist entschieden: Anlauf** (12. November 2026), mit Schrift A (Titel, Ziffern,
Namen und Navigation schräg, alles andere aufrecht) und dem Grund «Stoff». Das Resultat steht
schräg in der Vereinsfarbe, die Szene läuft auf der Taktikkamera, jede Linie ist ein gemessener
Weg. Der Ball erscheint nur bei der Spielerin, die ihn hält, und nur, wo er erkannt wurde.

| Datei | Wozu |
|---|---|
| `zielbild.html` | Das verbindliche Bild: alle 12 Screens an Desktop 1280 und Handy 390, dazu sieben Zustände. Umschaltbar nur die Vereinsfarbe. Im Browser öffnen. |
| `ANLAUF.md` | Das Aussehen: Idee, Farbmodell mit Gegner und Kollisionsregel, Zonen, Bedeutungsfarben, Schrift mit Lizenz, Formen, Bewegung, Datenquelle jeder Grafik, Qualitätsmassstab. |
| `SPEC.md` | Die verbindliche Fassung für die Umsetzung: Umfang, Prinzipien, Navigation, Routen, jeder Screen, Wörter, Lint-Regeln, Reihenfolge. Abschnitte 3 bis 5 verweisen auf `ANLAUF.md`. |
| `assets/anlauf.css` | Tokens und Bausteine zum Übertragen nach `globals.css` und in die Komponenten. |
| `assets/anlauf-farbe.js` | Das Farbmodell (Verein, Gegner, Kollision, Kontrast), Vorlage für `lib/color.ts`. |
| `assets/anlauf-feld.js` | Feld, Bündel, Zonen, Verlauf, Zeitleiste, Taktikkamera mit Ball, Videobild. Vorlage für die Grafik-Komponenten. |
| `assets/anlauf-demo.js` | Demo-Daten in der Form, die die API liefern muss. |
| `assets/anlauf-screens.js` | Markup und Wortlaut jedes Screens. |
| `src/zielbild.html`, `assets/zielbild.css`, `assets/zielbild.js`, `build.py` | Die Seite um die Screens und ihr Build: `python3 docs/design/ux-reset/build.py` schreibt `zielbild.html` neu. |
| `shots/` | Alle Screens als Bild, `bogen.jpg` (Desktop), `bogen-handy.jpg` (Handy und Zustände), `farben.jpg` (sechs Vereinsfarben auf Start und Video). |
| `ASSESSMENT.md` | Die Befunde aus den 66 Screenshots, pro Bereich. |

## Verworfene Kandidaten

Zum Nachlesen, nicht zum Umsetzen:

- `TRIKOT.md`: Richtung «Trikot», am 10. November gewählt und am 12. November durch Anlauf ersetzt.
- `archiv/halle/`: die frühere Richtung «Halle» mit ihrem Zielbild, den vier Richtungen
  (`richtungen.html`) und ihrem Build.
- `runde2/` (Einblendung, Spur), `runde3/abdruck/`, `mischpult/` (Runde 4) und `runde5/anlauf/`
  (die Skizze, aus der das Zielbild wurde; dort noch mit Schrift B und drei Gründen).

## Vor dem Start

In `SPEC.md`, Abschnitt 14, stehen sechs Annahmen (Kern ist die Spielauswertung für die Trainerin,
Spieler-Funktionen ausgeblendet, Einwilligung per Link, vier Ziele, «Sammlung», Minifeld). Wenn
eine nicht passt, zuerst dort ändern.

Mehrere Grafiken brauchen Daten, die die API noch nicht liefert (`ANLAUF.md`, Abschnitt 10):
Anläufe und Wurfpositionen pro Tor, Positionen pro Szene in Metern, Ballbesitz pro Zeitabschnitt,
die Bestätigung des Felds, die Gegnerfarbe pro Spiel, Themen pro Spiel, die Prüf-Fragen.

## Auftrag an die UI-Session

Zum Kopieren:

> Lies `docs/design/ux-reset/SPEC.md` vollständig, dann `docs/design/ux-reset/ANLAUF.md` und
> `docs/design/ux-reset/README.md`, und öffne `docs/design/ux-reset/zielbild.html?still` im
> Browser (Playwright ist vorhanden), um alle 12 Screens an Desktop und Handy und die sieben
> Zustände zu sehen; schalte dort die sechs Vereinsfarben durch. Markup und Wortlaut stehen in
> `docs/design/ux-reset/assets/anlauf-screens.js`, Tokens und Bausteine in `assets/anlauf.css`,
> das Farbmodell in `assets/anlauf-farbe.js`, die Grafiken in `assets/anlauf-feld.js`.
>
> Baue die Oberfläche von `apps/web` nach dieser Spezifikation um. Arbeite in der Reihenfolge
> aus Abschnitt 13 der Spezifikation, jeder Schritt ein eigener Commit, der für sich läuft.
>
> Regeln:
> - Die Spezifikation gilt vor `docs/DESIGN.md` und ADR 023 / 024. Schreib ADR 025 und passe
>   `DESIGN.md` in Schritt 2 an.
> - Übertrage Tokens, Farbmodell und Grafiken in `globals.css`, `lib/color.ts` und
>   React-Komponenten. Kopiere die Klassen der Skizzen nicht eins zu eins. Die Schriften
>   (Kanit, Hanken Grotesk, IBM Plex Mono, alle OFL) werden selbst gehostet.
> - Der Umfang ist Abschnitt 1 der Spezifikation: Spielauswertung für die Trainerin. Keine
>   Kommunikation, keine Zusagen, keine Termine; was es davon gibt, kommt hinter die
>   Team-Einstellung «Teamfunktionen» (standardmässig aus) und wird nicht gelöscht.
> - Zwei Teams, zwei Farben, sonst Tinte. Die Vereinsfarbe nur im Wurf-Kopf, im Streifen, im
>   Keil des Seitenkopfs, in der aktiven Marke, auf eigenen Linien und Ziffern. Knöpfe und Links
>   in Tinte. Gelb nur für «schau hier», immer mit Wort.
> - Schräg nur Titel, Ziffern, Namen und Navigation. Text, Tabellen, Formulare aufrecht.
> - Gezeichnet wird nur, was gemessen ist: Positionen, Anläufe, Torfolge. Kein Ballflug, keine
>   Passlinie, kein 3x3 aus dem Video. Der Ball nur als Markierung bei der Spielerin, die ihn hält,
>   und nur in den Abschnitten, in denen er erkannt wurde; sonst «Ball in dieser Szene nicht
>   erkannt». Geschätzt gestrichelt, bestätigt durchgezogen.
> - Jeder Screen muss vollständig sein, wenn die Trainerin nichts von Hand getan hat, und jeder
>   hat die Zustände aus 7.13.
> - Die Liste «Was wir nicht tun» in `zielbild.html` und Abschnitt 12 der Spezifikation sind die
>   Prüfliste. Baue sie als Lint-Regeln ein.
> - Alte Routen leiten um. Backend und API bleiben, wo es geht. Die Daten aus `ANLAUF.md`,
>   Abschnitt 10, ergänzt du schmal in der API und schreibst es in den Commit; fehlt ein Feld,
>   zeigt der Screen den dort beschriebenen Ersatz.
> - Nach jedem Schritt: Tests, axe und die Screenshots (`docs/screens`) für die geänderten
>   Screens in mindestens Blau, Gelb und Weiss neu. Vergleiche sie mit dem Zielbild, bevor du
>   weitergehst.
> - Was du nicht entscheiden kannst, kommt in `docs/OPEN_QUESTIONS.md`, mit deiner Annahme.
