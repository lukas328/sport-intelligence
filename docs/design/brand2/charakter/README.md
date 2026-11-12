# Handball Intelligence: Zeichen mit Charakter

Logo-Runde 2, Feld Charakter und Herz. `index.html` im Browser öffnen: sechs Ideen, je eine Tafel
mit Zeichen, Wortmarke, App-Icon, 32 px, einfarbig, negativ und einer echten Situation; am Ende die
Rangfolge mit Begründung.

| Datei | Wozu |
|---|---|
| `marks.py` | Die sechs Zeichen als SVG-Funktionen; wandelt Schrift mit fontTools in Pfade um. |
| `build.py` | Baut `index.html` und `logos/*.svg` (`python3 build.py`, braucht `pip install fonttools`). |
| `fonts/` | Die verwendeten Schriften, alle SIL OFL von Google Fonts. |
| `logos/` | Pro Idee: `-zeichen`, `-wortmarke`, `-wortmarke-gestapelt`, `-app-icon`, `-einfarbig`. Ohne Schriftabhängigkeit. |
| `shots/` | Jede Tafel als Bild und `seite.jpg` mit allem. |

Rangfolge: 1 Fuchs, 2 Abklatschen, 3 hi, 4 Murmeli, 5 Wimpel, 6 Harzabdruck. Rausgeflogen: Griff
(Hand am Ball, nach zwei Runden immer noch ein Handschuh) und Teamkreis (Team von oben, las sich
nach drei Runden als Kette).
