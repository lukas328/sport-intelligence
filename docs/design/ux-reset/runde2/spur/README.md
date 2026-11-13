> **Verworfener Kandidat.** Entschieden ist «Anlauf» (12. November 2026), siehe `../../ANLAUF.md` und `../../zielbild.html`.

# Spur

Runde 2, Richtung B. Feld: das Bild und die Bewegung. `index.html` im Browser öffnen (ohne Build,
Google Fonts aus dem Netz); `?club=blau|gelb|schwarz` oder die Knöpfe oben wechseln die Vereinsfarbe.
Bilder in `shots/`, alle sechs Ansichten auf einem Bild in `shots/bogen.jpg`.

## Leitidee

**Jedes Spiel hinterlässt eine Spur: Aus allen Würfen mit ihrem Anlauf entsteht eine Form, die nur
dieses Spiel hat, und diese Form ist sein Gesicht.**

Kein Spiel gleicht dem anderen, also sieht auch kein Spiel in der App aus wie das andere. Die Form
ist keine Dekoration, sondern das Wurfbild beider Teams in einem.

## Regeln

1. **Linie vor Fläche.** Information wird als Bahn gezeichnet: Anlauf und Wurf, Laufweg, Verlauf.
   Keine Kacheln, keine Karten, keine Symbole. Flächen sind nur Grund; Gliederung kommt aus Linien
   in Tinte (1,5 px für Kopf, 1 px für Zeilen).
2. **Jedes Spiel hat seinen Abdruck.** Jede Linie ein Wurf, vom Anlauf bis zum Tor; kräftig wenn er
   drin war, dünn wenn nicht; wir in Vereinsfarbe nach rechts, der Gegner in seiner Farbe nach links.
   Der Abdruck ist Titelbild auf dem Start, Kopf des Spiels, Zeichen in der Spielliste und Bild für
   den Chat. Läuft die Analyse, ist er erst teilweise gezeichnet. Ohne Video gibt es nur die
   Torfolge aus dem Spielbericht als Treppe: weniger Daten, einfachere Form.
3. **Jedes der drei Dinge ist das Bündel seiner Szenen.** Neun Gegentore über rechts aussen sind
   neun Bahnen, die sich am Flügel sammeln; die übrigen Würfe stehen grau dahinter.
4. **Ziffern werden nach ihrem Wert gesetzt.** Wer mehr Tore hat, steht breiter (Anybody, Breite
   50 bis 150). 26:18 sieht anders aus als 23:22. Auch das Torbild in «Zahlen» setzt jede Zahl so
   gross, wie sie ist.
5. **Bewegung zeigt Reihenfolge.** Beim Öffnen zeichnet sich der Abdruck Wurf für Wurf in
   Spielreihenfolge, im Video zieht sich der Laufweg mit der Szene. Fährt man über eines der drei
   Dinge, bleiben im Abdruck nur seine Linien stehen. Mit `prefers-reduced-motion` steht alles
   sofort.

## Erkennungszeichen

- **Der Abdruck.** Das Bild, an dem man ein Spiel wiedererkennt, ohne den Gegner zu lesen.
- **Die gewichtete Ziffer.** Der Spielstand in zwei Breiten.
- **Die Spielkurve.** Der Verlauf als Treppe in Vereinsfarbe, jedes Gegentor ein kleiner Wurf
  unter der Linie; dieselbe Sprache auf der Zeitleiste im Video.

## Stärken

- Am meisten Individualität: Jedes Spiel und jeder Verein sieht anders aus, ohne dass jemand
  etwas gestaltet. Das Bild entsteht aus den Daten.
- Hell, ruhig, gross gesetzt; Tabellen und Video bleiben sachlich, die Wucht sitzt in Ziffern und
  Linien.
- Der Abdruck taugt als Teilbild und Vorschau im Chat, es braucht kein Standbild und keine
  Einwilligung.
- Zwei Teamfarben statt einer Markenfarbe auf allem; Kollisionsregel: Liegt die Farbe des Gegners
  zu nah an unserer, wird er in Tinte gezeichnet.

## Risiken

- Der Abdruck muss gelesen werden lernen. Ohne Legende ist er schön, aber stumm; die Legende muss
  bleiben.
- Bei wenigen Würfen (Jugend, kurzes Video) wird die Form dünn. Untergrenze nötig, darunter nur
  Torfolge.
- Gelbe Vereine: Die Linien werden zu Ocker abgedunkelt, damit sie auf hellem Grund 3:1 halten.
  Das ist richtig, sieht aber weniger nach dem Verein aus.
- Gewichtete Ziffern sind ungewohnt; bei 5:1 wird die 1 sehr schmal.

## Schriften und Farben

- **Anybody** (SIL OFL, Breite 50 bis 150, Gewicht 400 bis 900): Titel, Ziffern, Namen.
- **Schibsted Grotesk** (SIL OFL): Text, Tabellen, Knöpfe.
- Grund `#efebe3`, Tinte `#141518`, Text 2 `#55585e`, Linien `#cdc7bb`. Vereinsfarbe `--club`,
  für Linien `--club-line` (abgedunkelt bis 3:1 auf dem Grund), für Text `--club-on-light` (4.5:1).
  Gegner `--opp` aus seinen Trikotfarben (hier `#0f7a6c`). Markierung (Phase, Prüfen) `#ffd23c`.
  Sieg und Niederlage immer als Wort.
- Schriftskala 13, 15, 17, 22, 30, 44, 64, dazu die Ziffern 92 bis 150. Abstände in 4er-Schritten
  (4, 8, 12, 16, 24, 32, 48).
