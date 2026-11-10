# Sendung

**Leitidee: Dein Spiel geht auf Sendung. Die App spricht die Sprache der Sportübertragung, mit
Endstand-Tafel, Bauchbinden und Laufband, und dein Verein ist der Sender.**

Woher: die Grafik einer Live-Übertragung am Samstagabend. Jede Trainerin kennt sie aus dem
Fernsehen; die Grafik einer Übertragung ist das, was ein Amateurspiel nie hat. Die App gibt es ihm.

## Regeln

1. **Grafik auf Studio.** Der Grund ist das dunkle Studio (`#0b0f16`). Alles, was man lesen muss,
   sitzt auf weissen oder dunklen Tafeln mit harten Kanten. Keine Rundung, kein Schatten, kein
   Verlauf.
2. **Die Senderkante.** Jede Überschrift ist eine Tafel mit einer 6 px breiten Kante in der
   Vereinsfarbe links. Die Vereinsfarbe erscheint sonst nur dort, wo das eigene Team gemeint ist
   (Rangziffer, eigene Tore, eigene Spielerinnen).
3. **Eine Endstand-Tafel pro Spiel-Screen.** Zwei Zeilen wie im Fernsehen: Kante, Wappen, Name,
   Resultat. Der Sieger hat das weisse Resultatfeld. Darunter der Riemen «Endstand» mit Halbzeit,
   Datum, Halle. Klein auf Video und Zahlen.
4. **Erkenntnisse sind Bauchbinden.** Rang, Minifeld mit Telestrator-Pfeilen, die Aussage in
   Schmalschrift mit der Zahl als weisser Einschub, darunter der Riemen mit der Begründung.
5. **Wucht oben, Ruhe unten.** Start und Spiel sind Studio. Video bleibt Studio, aber die Grafik
   schrumpft auf den Score-Bug im Bild. Zahlen ist eine helle Statistikseite; nur der Kopf bleibt
   Studio.

## Erkennungszeichen

- **Endstand-Tafel** als Kopf jedes Spiels.
- **Laufband «Was ansteht»** am Fuss von Start: offene Fragen, laufende Analysen, nächstes Spiel.
  Läuft langsam, steht still bei reduzierter Bewegung.
- **Score-Bug im Video** mit dem Stand zu dieser Minute (17:15 in der 41.), wie bei einer
  Wiederholung.
- **Telestrator** auf den Minifeldern: weisse Pfeile und Ring, wie die Analyse in der Pause.
- Pfosten im Torraster rot-weiss gestreift wie das echte Handballtor.

## Stärken

- In zwei Sekunden Sport. Niemand hält es für eine Büro-App.
- Vereinsfarbe als «Senderfarbe» funktioniert für jede Farbe, auch Gelb und Schwarz (Schwarz wird
  zu Weiss auf Studio, siehe unten).
- Die Grafik ist streng modular: Tafel, Bauchbinde, Riemen, Bug. Leicht in Komponenten zu bauen.
- Das Video fühlt sich an wie eine Wiederholung, das macht den Kern stärker.

## Risiken

- Dunkel als Standard. Am Handy im hellen Hallenlicht schwächer; braucht einen hellen Modus, der
  nicht beliebig wirkt (Zahlen zeigt, wie).
- Grenze zu E-Sport und Wettanbieter-Grafik ist schmal. Hält nur, wenn es bei harten Kanten,
  wenig Farbe und echtem Inhalt bleibt.
- Schmalschrift in Grossbuchstaben nur für Teamnamen; sonst wird es laut.
- Schwarzer Verein: Studio ist schon dunkel, deshalb wird seine Kante weiss. Das ist ehrlich
  (schwarz-weiss), aber weniger Farbe.

## Schriften und Farben

- Saira Extra Condensed 700 und 800: Resultate, Namen, Überschriften, Rang. Saira Semi Condensed
  400 bis 700: alles Lesbare. Beide SIL OFL, Google Fonts.
- Raster: 4, 8, 12, 16, 24, 32, 48. Schriftskala: 12, 14, 16, 20, 28, 40, 64, 120.
- Studio `#0b0f16`, `#121925`, `#1b2433`, Kante `#2b3649`; Text auf Studio `#f3f5f8` und
  `#aab5c5` (über 8:1). Tafel weiss, Tinte `#0b0f16`. Zahlen-Grund `#e9edf2`.
- Signale: Sieg `#1f9d55`, Niederlage `#e5484d`, Achtung `#ffc21a` (gelbe Karte für «Prüfen»,
  markierte Phase). Immer mit Wort.
- Verein: Füllung, Text darauf, Linie auf Studio. Rot `#d3122c` / weiss / `#ff5a6b`; Blau
  `#1f4fd6` / weiss / `#7aa2ff`; Gelb `#ffcc00` / Tinte / `#ffcc00`; Schwarz `#f4f4f2` / Tinte /
  weiss.
