# Linie

Runde 4, Feld 1: radikal reduziert, eine einzige grosse Geste. `index.html` im Browser öffnen;
Vereinsfarbe über die Knöpfe oder `?club=gelb`. Bilder in `shots/`, der Start in allen sechs
Farben in `shots/farben.jpg`.

## Leitidee

**Ein Spiel ist eine Linie.** Der Verlauf der Tordifferenz über sechzig Minuten, dick und
bildschirmbreit: über null in der Farbe des eigenen Vereins, darunter in der des Gegners. Sie ist
das einzige Bild der App, und sie ist überall. Alles andere ist Schrift auf Weiss.

## Wie sie gewählt wurde

Vier Leitideen als Start skizziert (`../skizzen/skizzen.jpg`):

| Idee | Urteil |
|---|---|
| **Linie**: der Verlauf als bildschirmbreite Linie in zwei Teamfarben | gewählt |
| Anteil: ein Balken im Verhältnis der Tore | ehrlich, aber Diagramm, kein Sport |
| Bogen: der Torraum als riesiger Bogen | sofort Handball, trägt aber keine Information |
| Zahl: das Resultat füllt den Bildschirm | Wucht, aber bekannt von jeder Sportseite; auf Arbeitsscreens bleibt nichts |

Die Linie gewinnt, weil sie als einzige von den vier **Spannung** zeigt, das, was ein Spiel
ausmacht: den Vorsprung, den Einbruch zwischen der 38. und 44. Minute, den Schlussspurt. Kein Spiel
sieht aus wie ein anderes. Und sie trägt durch alle Screens, weil sie dort jeweils eine Aufgabe hat.

## Regeln

1. **Eine Linie, ein Datensatz.** Sie ist immer der echte Verlauf, nie Schmuck. Am Start 18 px
   dick über die ganze Breite, im Spiel 12 px, im Video ist sie die Zeitleiste mit dem Abspielkopf,
   in den Zahlen ein Strich von 4 px, in jeder Spielzeile eine kleine Kurve. Ohne Video gibt es keine
   Linie, nur eine gepunktete Nulllinie.
2. **Zwei Farben, eine Bedeutung.** Über null der eigene Verein, unter null der Gegner. Ist eine
   Teamfarbe zu hell für Weiss (Gelb, Weiss), behält die Linie ihre Farbe und bekommt eine Paspel in
   der Zweitfarbe des Trikots. Kollidieren die Farben (Blau oder Grün gegen das petrolfarbene
   Thalwil), tritt der Gegner in Weiss an.
3. **Die drei Dinge sitzen auf der Linie.** Unter ihr stehen die Tore als Striche (unsere oben,
   ihre unten); die Tore, die zu Punkt 1 und 3 gehören, sind farbig, der Rest grau. Punkt 2 ist eine
   Klammer über der Phase. Im Text wiederholt ein kleines Zeichen (Strich oder Klammer), wo man ihn
   auf der Linie findet.
4. **Sonst nur Schrift.** Unbounded für Zahlen (breit, sportlich, kräftig), Hanken Grotesk für
   alles andere. Keine Flächen, keine Rahmen, keine Karten, keine Minifelder, keine Symbole ausser
   Suche und Plus. Gelb nur für Prüfen und die laufende Szene.
5. **Die Linie bewegt sich einmal.** Beim Öffnen zeichnet sie sich in 1,6 Sekunden von links nach
   rechts, wie das Spiel. Bei `prefers-reduced-motion` steht sie sofort.

## Zweiter Durchgang (Art Director)

- *Ist das Sport?* Am Start ja: Das Resultat in Teamfarben über einer Fieberkurve, die nach oben
  ausbricht, ist ein Spiel. Auf «Zahlen» trägt nur noch der dünne Strich und die Rückennummer in
  Vereinsfarbe.
- *Hat das Charakter?* Die Linie ist pro Spiel anders, und die Paspel macht sie für jeden Verein
  eigen. Die Typografie ist sehr gross und sehr ruhig zugleich.
- *Könnte das eine Vorlage sein?* Die grösste Gefahr: Eine Linie auf Weiss kennt man aus Börsen-Apps.
  Was dagegen hält, sind die zwei Farben und die Torstriche darunter. Ohne sie wäre es ein Kurs-Chart.
- Geändert nach dem ersten Durchgang: Linie dicker und höher (sie war neben dem Resultat zu klein),
  Gelb und Weiss mit Paspel statt Ausweichen auf Schwarz, Beschriftungen am Handy entfernt, wo sie
  sich überlagerten.

## Stärken

- Die reinste der bisherigen Richtungen: ein Mittel, konsequent. Schnell zu bauen und zu pflegen.
- Die Linie ist Information, nicht Dekoration. Sie erklärt das Spiel auf einen Blick.
- Funktioniert für jeden Verein, auch Weiss und Gelb.

## Risiken

- Nähe zum Finanz-Chart, siehe oben.
- Die drei Dinge haben kein Bild mehr (kein Minifeld). Wer die Szene sehen will, muss tippen.
- Spiele ohne Video haben keine Linie. Die Spielliste wird für Vereine ohne Video karg.
- Die Torstriche unter der Linie sind am Handy dicht; ob man sie dort lesen kann, sollte man am Gerät
  prüfen.
