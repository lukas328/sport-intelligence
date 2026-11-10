# Hallenlicht

Runde 4, Feld 2: Material und Raum. `index.html` im Browser öffnen; Vereinsfarbe über die Knöpfe
oder `?club=weiss`. Bilder in `shots/`, der Start in allen sechs Farben in `shots/farben.jpg`.

## Leitidee

**Die App ist die Halle von der Tribüne aus: ein Boden mit Glanz, Licht von oben, und was zählt,
liegt darin.** Der Kopf jedes Spiels ist das Feld in echter Perspektive: Holz, die Torräume in den
Farben beider Teams gemalt, das Resultat auf dem Boden wie das Logo im Mittelkreis, die Lampen
spiegeln sich im Lack. Darunter liegen die Dinge als Gegenstände im selben Licht: die drei Dinge als
Magnete auf der Taktiktafel der Trainerin, die Zahlen auf einem Bogen an der Wand.

## Wie sie gewählt wurde

Vier Leitideen als Start skizziert (`../skizzen/skizzen.jpg`):

| Idee | Urteil |
|---|---|
| **Hallenlicht**: das Feld von der Tribüne, Holz, Glanz, gemaltes Resultat | gewählt, als Raum |
| **Taktiktafel**: alles liegt auf der Magnettafel | aufgenommen, als Gegenstand im Raum |
| Netz: Inhalt hinter dem Tornetz, Schärfe als Tiefe | stört beim Lesen, wird Effekt |
| Harz: Ballleder, geprägte Ziffern | Kostüm, schlecht lesbar |

Hallenlicht und Taktiktafel zusammen, weil sie dieselbe Welt sind: der Raum (die Halle) und das
Werkzeug darin (die Tafel). Beides kennt jede Trainerin, beides ist im Browser sauber baubar (CSS-3D
und SVG, keine Bilder, kein Glas-Effekt).

## Regeln

1. **Ein Licht, von oben.** Jeder Schatten fällt nach unten, jedes Glanzlicht sitzt oben. Drei
   Schattengrössen (`--sh-1` bis `--sh-3`) für drei Höhen: Knopf, Bogen, Tafel. Verläufe gibt es nur
   als Licht (Lampen im Lack, Glanz auf Magneten, Abfall des Lichts zum Hallenrand), nie als Fläche.
2. **Farbe ist Farbe auf Material.** Die Teamfarben sind auf das Holz gemalt (Torräume) oder als
   Magnete gegossen. Auf Wänden, Knöpfen und Text gibt es keine Vereinsfarbe. Gelb heisst «schau
   hier» (Prüfen, die häufigste Ecke, die laufende Szene).
3. **Die Taktiktafel ist das Bild einer Szene.** Aluminiumrahmen, Emaille, Magnete in den Teamfarben,
   Pass gepunktet, Wurf mit Pfeil in Filzstift. Gegentore nach Position sind Magnete, deren Grösse die
   Zahl ist; das Wurfbild sind Magnete für Tore und Kreuze für Fehlwürfe.
4. **Für das Video geht das Licht runter.** Die Videoseite ist dunkel, die Zeitleiste ist eine
   Schiene mit Magneten für die Tore (wir oben, sie unten) und einem Knopf als Abspielkopf.
5. **Wo gearbeitet wird, ist es ein Bogen Papier.** Tabellen liegen auf einem weissen Bogen mit
   leichtem Schatten, Rückennummern sind kleine Magnete. Das Tor in «Zahlen» hat gestreifte Pfosten
   wie in jeder Halle.

## Zweiter Durchgang (Art Director)

- *Ist das Sport?* Mehr als jede andere Richtung: Man sieht die Halle, bevor man ein Wort liest.
- *Hat das Charakter?* Ja, und er ist warm: Holz, Licht, die Tafel der Trainerin. Jeder Verein sieht
  seine Farbe auf dem eigenen Torraum.
- *Könnte das eine Vorlage sein?* Der Start nicht. Die Zahlen-Seite (Bogen mit Tabelle) und die
  Zeilen der Spielliste sind nahe an einer gewöhnlichen hellen App; dort tragen nur Rückennummern,
  Magnetpaare und das gestreifte Tor.
- Geändert nach dem ersten Durchgang: Magnete weniger glänzend (sie sahen wie Murmeln aus), das Feld
  auf der Spielseite höher gesetzt (das Resultat war abgeschnitten), die Pfosten des Tors richtig
  gestreift (Latte quer, Pfosten längs), helle Ringe um die Farbpunkte im dunklen Kopf (Schwarz war
  unsichtbar).

## Stärken

- Der stärkste erste Eindruck aller Runden für «das ist Handball».
- Die Vereinsfarbe wirkt als Material, nicht als Akzent: Auch Weiss und Gelb sehen gut aus
  (`farben.jpg`).
- Die Taktiktafel ist ein Bild, das jede Trainerin selbst benutzt. Sie erklärt sich ohne Legende.

## Risiken

- Aufwendig und heikel: Perspektive, Licht und Schatten müssen in jeder Grösse stimmen. Am Handy ist
  das Feld eng; das Resultat trägt, die Torräume sind angeschnitten.
- Glanz und Schatten können schnell kitschig werden. Die Regel «ein Licht, drei Schatten» muss als
  Lint durchgesetzt werden.
- Viel Höhe für den Kopf. Auf kleinen Laptops liegen die drei Dinge unter dem Falz.
- Leistung: CSS-3D und Mischmodi sind auf alten Android-Geräten langsamer. Fallback wäre ein
  vorgerendertes Bild des Felds pro Verein.
