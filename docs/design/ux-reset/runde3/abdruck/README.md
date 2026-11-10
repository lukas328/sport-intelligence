# Abdruck

Runde 3, Schlussrunde. `index.html` im Browser öffnen (ohne Build, Google Fonts aus dem Netz). Die
Knöpfe oben wechseln die Vereinsfarbe (rot, blau, gelb, schwarz, weiss, grün), `?club=gelb` geht
auch. Bilder in `shots/`, alles auf einem Bild in `shots/bogen.jpg`. Neu gegenüber Runde 2:
`farben.jpg` (derselbe Start für Gelb, Weiss und Grün) und `gegner-unbekannt.jpg`.

## Leitidee

**Jedes Spiel hat ein Gesicht aus seinen eigenen Daten.**

Das Gesicht ist der Kopf jedes Spiels. Er ist in die beiden Teamfarben geteilt, Heim links wie auf
jeder Anzeigetafel. Auf jeder Hälfte stehen die Würfe dieses Teams als Linien vom Anlauf ins Tor:
kräftig für ein Tor, dünn für einen Fehlwurf. Darüber steht das Resultat, die Ziffern breit nach
ihrem Wert. Durch das Resultat läuft der Spielverlauf als eine Linie von Minute 0 bis 60, nach oben
heisst Führung. Ein Sieg mit acht Toren sieht anders aus als eine knappe Niederlage, und dasselbe
Gesicht wird zum Zeichen in der Spielliste und zum Bild für den Chat.

Woher die Teile kommen: der Abdruck und die Bündel aus «Spur», das grosse Resultat in Vereinsfarbe
mit dem Verlauf als Linie aus «Wurf», die zwei Teamfarben und das Raster aus «Plakat», die
Taktikkamera aus «Einblendung».

## Fünf Regeln

1. **Jedes Bild ist gemessen.** Das Gesicht (Würfe und Verlauf), die Bündel der drei Dinge (alle
   Szenen eines Punkts) und die Taktikkamera (eine Szene von oben mit Nummern und Wegen) kommen aus
   den Daten. Was nicht gemessen ist, wird nicht gezeichnet. Ohne Video gibt es nur die Torfolge
   als Treppe.
2. **Zwei Teams, zwei Farben.** Farbe heisst immer: eines der beiden Teams. Daneben gibt es nur
   Tinte, den Grund und Gelb für «schau hier» (Prüfen, die markierte Phase). Unbekannt heisst grau,
   nie geraten.
3. **Eine Linie trägt ihr Trikot.** Ist eine Teamfarbe auf dem Grund zu hell (Gelb, Weiss), bekommt
   ihre Linie eine Paspel in der Zweitfarbe des Trikots, und ihre Fläche bekommt eine Kante in
   Tinte. Kollidieren die beiden Teamfarben, trägt der Gegner seine Zweitfarbe.
4. **Ziffern nach Wert.** Wer mehr hat, steht breiter (Anybody, Breite 60 bis 150 %). Das gilt fürs
   Resultat, für die drei Dinge, die Phasen und das Torbild. Tempo kommt aus Breite und Bahn, nicht
   aus Schräglage.
5. **Wucht im Kopf, Ruhe darunter.** Nur der Kopf eines Spiels trägt Fläche und Bewegung. Darunter
   gliedert ein Raster aus 2-px-Linien in Tinte und feinen Trennlinien: keine Karten, keine
   Schatten, keine Rundung. Bewegung zeigt nur Reihenfolge: Das Gesicht zeichnet sich Wurf für Wurf
   in Spielreihenfolge, im Video der Laufweg mit der Szene. Bei `prefers-reduced-motion` steht alles
   sofort.

## Erkennungszeichen

- **Das Gesicht**: zwei Farbfelder, weisse Wurfbahnen, das gewichtete Resultat, die Verlaufslinie
  mit dem Ball am Schluss.
- **Das Bündel** für jedes der drei Dinge: neun Bahnen, die sich am Flügel sammeln, über den grauen
  übrigen Würfen.
- **Die gewichtete Ziffer.**

## Die sieben Punkte

1. **Grund.** Kein Beige mehr. Der Grund ist ein kühles Weiss mit einem Hauch der Vereinsfarbe
   (4,5 %): Bei Rot leicht rosig, bei Grün leicht mint, bei Gelb leicht cremig. Helle Trikots
   (Weiss, Gelb über 60 % Helligkeit) bekommen ein kühles Hallengrau `#eceef0`, damit die weisse
   Fläche steht. Die App gehört dem Verein, bevor eine Zahl gelesen ist. Schwarz-weiss wirkt sie
   nicht, weil der Kopf jedes Spiels zwei volle Farbflächen trägt.
2. **Tempo ohne Kursiv.** Die Schrift steht aufrecht. Tempo zeigen die Wurfbahnen, die Treppe des
   Verlaufs, die von links unten durch das Resultat steigt, und die Breite der Ziffern. Anybody
   wurde gewählt, weil sie die Breite als Achse hat; damit ist die Breite eine Aussage, kein Stil.
3. **Der Abdruck erklärt sich selbst.** Jede Hälfte steht in der Farbe ihres Teams, die Bahnen enden
   sichtbar in einem Tor, und die Zahl darunter sagt es in Worten: «26 Tore aus 45 Würfen». Eine
   Zeile «Jede Linie ein Wurf, vom Anlauf ins Tor» steht im Bild wie eine Bildzeile. Eine Legende
   braucht es nicht mehr.
4. **Gelb und Weiss.** Auf der eigenen Fläche werden Linien und Ziffern in Tinte gezeichnet. Auf dem
   Grund trägt eine gelbe Linie ihre schwarze Paspel und bleibt gelb. Die weisse Fläche bekommt eine
   Kante in Tinte. Getestet mit Rot, Blau, Gelb, Schwarz, Weiss, Grün (`farben.jpg` und die Knöpfe).
   Kollisionen: Blau oder Grün gegen das petrolfarbene Thalwil lassen Thalwil in Weiss antreten.
5. **Gegnerfarbe unbekannt.** Die Gästehälfte ist Hallengrau `#646b73` mit weissen Linien und der
   Zeile «Farbe nicht bekannt». Im Bild steht ein Knopf «Welche Farbe trägt Thalwil?» mit sechs
   Trikotfarben; die Wahl gilt für alle Spiele gegen diesen Gegner. Ist der eigene Verein schwarz,
   wird das Grau heller (`#8b9198`). Siehe `gegner-unbekannt.jpg`.
6. **Video und Zahlen.** Hell und ruhig, aber oben steht als Streifen dasselbe Gesicht ohne Bahnen:
   beide Farben, Namen, Resultat. Die Zeitleiste im Video spricht dieselbe Sprache wie das Gesicht
   (jedes Tor ein kleiner Wurf, wir oben, der Gegner unten), die Tabellen tragen Quoten als Balken in
   Vereinsfarbe, die Phasen zwei Farbbalken. Kein dunkles Dashboard; das Videobild ist das einzige
   Dunkle. Das Videobild hier ist eine Skizze, ein Knopf schaltet auf die Taktikkamera.
7. **Fünf Regeln**, oben. Weggelassen, weil keine Regel sie stützt: Echo-Ziffern, schräge Knöpfe,
   Piktogramme, Bauchbinden, das gekippte Feld.

## Schriften und Farben

- **Anybody** (SIL OFL, Breite 50 bis 150, Gewicht 500 bis 900): Resultat, Titel, Namen, Ziffern.
- **Schibsted Grotesk** (SIL OFL): Text, Tabellen, Knöpfe.
- Tinte `#15171a`, Text 2 `#545960`, Grund aus der Vereinsfarbe (siehe oben), Linien 16 % Tinte auf
  dem Grund. Gelb `#ffd23c` nur für Prüfen und die markierte Phase. Sieg `#17703f`, Niederlage
  `#a8261e`, immer mit Wort. Unbekannter Gegner `#646b73`.
- Trikots als Paar aus Farbe und Zweitfarbe, zum Beispiel Rot `#d3202e` mit Weiss, Gelb `#f6c500`
  mit Schwarz, Weiss mit Schwarz.
- Schriftskala 13, 15, 17, 22, 26, 30, 44, 64, dazu die Ziffern 72 bis 250. Abstände in 4er-Schritten
  (4, 8, 12, 16, 24, 32, 48, 64).

## Offen

- Das Gesicht am Handy ist dicht: 300 px Höhe für 79 Würfe, Resultat und Verlauf. Es funktioniert,
  ist aber an der Grenze. Möglich: am Handy nur die Tore zeichnen.
- Die Zeile «Jede Linie ein Wurf» steht nur auf dem Start. Ob man sie nach dem ersten Mal weglässt,
  sollte ein Test mit zwei, drei Trainerinnen zeigen.
- Die Kollisionsregel braucht die Zweitfarbe des Gegners. Ohne sie fällt er auf Tinte zurück.
