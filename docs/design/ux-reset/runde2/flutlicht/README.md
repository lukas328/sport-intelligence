# Flutlicht

**Leitidee: Die App ist die Halle am Spielabend. Dunkel, und nur was zählt, leuchtet.**

Synthese aus Konsole (Tafel, Lämpchen, das Dunkle fürs Video), Trikot (zwei Teamfarben als
Bande), Halle (Minifeld, Kreise auf dem Feld, ruhige Tabellen), Kassette (Laufzeit an allem, was
Video ist) und Piktogramm (eine Figur pro Art von Szene).

Öffnen: `index.html` im Browser. Quelle: `src.html`, gebaut mit `python3 ../build.py`
(fügt `../common.js` und die LED-Schrift ein). Bilder: `shots/`.

## Regeln

1. **Licht hat Bedeutung.** Bernstein ist die Tafel: Stand und «schau hier» (Prüfen, markierte
   Phase, aktives Ziel). Rot ist die Uhr. Grün heisst fertig. Die zwei Teamfarben sind die zwei
   Teams. Alles andere ist Grau auf Schwarz.
2. **Eine Tafel pro Screen.** Am Start hängt sie über die ganze Breite, im Spiel steht sie über
   den Reitern, bei Video und Zahlen schrumpft sie auf eine Zeile. Darunter läuft die **Bande**
   in beiden Teamfarben, wie die LED-Banden am Spielfeldrand.
3. **Lämpchen statt Etiketten** für Zustände, immer mit dem Wort daneben: fertig, läuft,
   kein Video, bestätigt, geschätzt.
4. **Gezählt wird gross und schmal** (Saira, 62 % Breite). Was Video ist, trägt seine Laufzeit.
5. **Wo gearbeitet wird, leuchtet nichts.** Tabellen, Video und Listen sind grau auf schwarz;
   Farbe steht dort nur als Magnet, Linie oder Lämpchen.

Schriften: Doto (Punktmatrix, nur Teamnamen auf der Tafel), DSEG7 (Stand und Uhr), Saira
(Köpfe, Ziffern, Navigation), Sofia Sans (Sätze).

## Stärken

- Der stärkste erste Eindruck: Die Tafel ist sofort Sport, sofort Spielabend.
- Video ist zu Hause. Auf dunklem Grund tritt alles hinter das Bild zurück.
- Jede Farbe hat genau eine Bedeutung; der Zustand eines Spiels ist ohne Lesen erkennbar.
- Trägt bis in die Zahlen: Die Tabellen bleiben ruhig.

## Risiken

- Nur dunkel. Am Handy in einer hellen Halle oder am Laptop tagsüber anstrengender als hell.
  Ein helles Thema wäre eine eigene Gestaltungsaufgabe.
- Nahe an «Dark-Mode-Dashboard». Den Unterschied machen allein Tafel, Bande und Lämpchen; ohne
  sie wird es generisch.
- Doto und DSEG7 sind laut. Sie dürfen nur auf der Tafel stehen, sonst wird es Kostüm.
- Teamfarben auf Schwarz brauchen pro Verein eine hellere Textvariante (hier von Hand gesetzt).
