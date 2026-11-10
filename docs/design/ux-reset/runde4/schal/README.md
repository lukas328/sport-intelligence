# Schal

Runde 4, Richtung B: verspielt und gezeichnet.

**Leitidee: Die App ist der Vereinsschal. Name, Resultat und die Zahl jedes Dings sind gestrickt,
in den zwei Garnen des Vereins. Alles, was man lesen muss, bleibt gesetzt.**

## Wie es dazu kam

Vier Leitideen, je als schneller Start skizziert (`skizzen.html`, `shots/skizzen.jpg`):

| Skizze | Leitidee | Urteil |
|---|---|---|
| 2a Druck | Handballfiguren in Bewegung, geschnitten wie Linoldruck, in Tinte und Vereinsfarbe. | Die Figuren wirken grob und sind nah an Piktogrammen. Gut gezeichnet bräuchte es eine Illustratorin, und es bliebe ein Bild neben dem Produkt. |
| 2b Baukasten | Die Linien des Feldes (Torraum, Ball, Tor, Neunmeterbogen) als Bausteine. | Kraftvoll, aber ein Plakat. Gibt dem Produkt kein Gesicht, nur einen Hintergrund. |
| 2c Maskottchen | Ein Ball mit Gesicht begleitet die Trainerin. | Erkennbar, aber kindlich; nach einer Woche nervt er. |
| 2d Schal | Die App strickt ihre Schrift und ihr Muster wie ein Fanschal. | gewählt |

Der Schal gewinnt, weil er aus dem Verein selbst kommt: Jeder Verein hat einen, er hängt in der
Halle und an der Garderobe, man trägt ihn, man schenkt ihn. Er hat zwei Farben, wie die
Vereinsfarbe hier funktioniert. Und er ist ein Raster, also kann er Zahlen tragen: Eine Masche ist
ein Tor.

## Fünf Regeln

1. **Gestrickt wird nur, was man auf einen Schal sticken würde:** das Resultat, die Zahl jedes
   der drei Dinge, das Zeichen des Vereins, der Schal des Gegners. Sätze, Tabellen und Knöpfe sind
   gesetzt.
2. **Eine Masche ist mindestens 6 px gross.** Darunter ist Strick nicht mehr lesbar; kleine
   Resultate in Listen stehen deshalb in Schrift.
3. **Zwei Garne.** Jedes gestrickte Stück hat genau zwei Farben: Grund und Motiv. Rot mit Weiss,
   Gelb mit Schwarz, Weiss mit Schwarz. Weisse Schals bekommen eine Kante in Tinte.
4. **Eine Masche zählt.** Wo Strick Daten zeigt, ist eine Masche eine Einheit: im Verlauf ein Tor
   Vorsprung, in den Phasen ein Tor, im Fortschritt ein Zehntel. Nie dekorative Maschen in
   Diagrammen.
5. **Laut am Kopf, ruhig darunter.** Start und Spiel öffnen mit dem Schal. Video und Zahlen haben
   nur den Schalrand oben; darunter normale Tabellen und das Bild.

## Erkennungszeichen

- **Der Schal mit dem Resultat**, grob gestrickt, mit Fransen an beiden Enden.
- **Aufnäher**: die Zahl jedes der drei Dinge als kleines gestricktes Stück; Knöpfe mit einer
  gestrichelten Naht innen.
- **Der gestrickte Verlauf**: alle fünf Minuten eine Säule, eine Masche pro Tor Vorsprung.
- **Der Gegnerschal** beim nächsten Gegner, in dessen Farben.
- Die aktive Navigation ist eine Reihe Maschen statt eines Strichs.

## Zwei Durchgänge als Art Director

Erster Durchgang. *Ist das Sport?* Ja, Fankultur. *Hat das Herz?* Ja. *Vorlage?* Nein, aber die
Hierarchie war falsch: Der Name «HC ZÜRICHSEE» war grösser gestrickt als das Resultat, und kleine
Resultate in Strick waren unlesbar. Geändert: Das Resultat allein, grob gestrickt; Regel 2 für die
Mindestgrösse; Listen in Schrift.

Zweiter Durchgang. *Könnte das eine Vorlage sein?* Unter dem Schal wurde es zu glatt. Geändert:
Aufnäher und Naht an den Knöpfen, Maschen als Zähler in Verlauf, Phasen und Fortschritt, der
Schalrand oben auf Video und Zahlen. Die Textschrift wechselte zu Figtree, weil Atkinson die Null
durchgestrichen zeichnet.

## Stärken

- Das stärkste Zeichen aller Runden: Man würde es sofort auf ein Shirt oder einen echten Schal
  drucken. Das Bild für den Chat ist ein Schal mit dem Resultat.
- Funktioniert mit jeder Vereinsfarbe, weil ein Schal immer zwei Farben hat; Weiss und Gelb
  brauchen keine Sonderfarbe, nur Tinte als zweites Garn.
- Verspielt, ohne kindlich zu sein: Es gibt keine Figur, keinen Witz, nur Material.
- Die Masche als Einheit macht Zahlen greifbar (19 Maschen gegen 14).

## Risiken

- Strick ist laut. Wenn er sich ausbreitet, wird es Weihnachtspullover. Regel 1 muss halten.
- Pixel-Strick hat eine kleine Schrift (5 x 7 Maschen); lange Namen gehen nicht.
- Unter dem Kopf ist die App eher schlicht; die Persönlichkeit hängt am Schal.
- Saisonal gelesen kann es nach Winter aussehen; im Sommer bei Beachhandball fremd.

## Schriften und Farben

- Gabarito 600 bis 800 für Titel, Zahlen, Knöpfe; Figtree 400 bis 700 für Text (beide SIL OFL,
  Google Fonts). Strick: eigene Masche, 5 x 7, in `lib/strick.js`.
- Raster 4, 8, 12, 16, 24, 32, 48, 64. Schriftskala 13, 15, 17, 20, 26, 34, 48, 56.
- Weiss `#fff`, Tinte `#1c1b1f`, zweite Tinte `#5b5860` (6,8:1), Linie `#e5e2e7`, Nacht `#18171b`.
- Achtung `#e8a900`, Sieg `#1d7a46`, Niederlage `#b3261e`, Gegner Rheinau `#2f6b4f`.
- Garne pro Verein (Grund, Motiv): Rot `#d3122c`/weiss, Blau `#1f4fd6`/weiss, Gelb `#ffcc00`/Tinte,
  Schwarz `#1c1b1f`/weiss, Weiss/Tinte mit Kante, Grün `#1b7a3e`/weiss.
