# Plakat

**Leitidee: Jedes Spiel ist ein Plakat. Zwei Teamfarben, eine riesige Zahl, ein strenges Raster.**

Synthese aus Piktogramm (Farbfelder, riesige Ziffern, Piktogramme, Raster), Trikot (zwei
Teamfarben pro Spiel), Kassette (die drei Dinge als Titelliste mit Laufzeiten, die leere Hülle
für «kein Video») und Halle (Minifeld, Kreise auf dem Feld, ruhige Tabellen).

Öffnen: `index.html` im Browser. Quelle: `src.html`, gebaut mit `python3 ../build.py`
(fügt `../common.js` ein). Bilder: `shots/`.

## Regeln

1. **Die Farbe gehört den Teams, und nur dem Kopf eines Spiels.** Heim- und Gastfarbe als flache
   Felder mit den Toren als riesige Ziffern. Überall sonst Schwarz auf Plakatpapier. Signalgelb
   heisst «schau hier» (Prüfen, markierte Phase, häufigste Ecke).
2. **Ein Raster aus 2-px-Linien teilt alles.** Navigation, Reiter, Kennzahlen und die drei Dinge
   sind Zellen. Keine Karten, keine Schatten, keine Rundung.
3. **Zahlen sind die Bilder.** Archivo in drei Breiten: 62 % für Ziffern, 100 % für Text,
   125 % für Etiketten.
4. **Die drei Dinge sind ein Programm**: Nummer, Piktogramm, die Zahl gross, das Minifeld, der
   Knopf mit Laufzeit.
5. **Das Plakat ist auch das Bild für den Chat.** «Als Plakat für den Chat» teilt genau diesen
   Kopf mit den drei Dingen.

## Stärken

- Am eigenständigsten: So sieht keine Sport-App aus, und trotzdem sofort Sport.
- Jedes Spiel sieht anders aus, weil die Gegnerfarbe wechselt. Die App bleibt dabei ruhig.
- Trägt am besten durch Arbeitsscreens: Zahlen und Video sind ein sauberes Raster.
- Das Plakat ist ein Produkt: teilbar, druckbar, ein Grund, die App zu zeigen.

## Risiken

- Braucht die Gegnerfarbe. handball.ch liefert sie nicht; ohne sie bleibt die rechte Hälfte
  grau, und das Plakat verliert die Hälfte seiner Wirkung.
- Gelbe, weisse oder ähnliche Teamfarben brauchen Regeln (Ziffern in Tinte, Kollisionsfarbe).
- Riesige Ziffern kosten Höhe; am Handy liegt der erste der drei Dinge knapp unter dem Falz.
- Swiss-Style ist eine bekannte Sprache. Der Reiz hängt an der Sorgfalt des Rasters.
