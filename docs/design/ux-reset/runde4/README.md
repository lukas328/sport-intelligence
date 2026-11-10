# Runde 4: Wärme und Menschen

Stand: 10. November 2026. Bisher war alles grafisch, kühl oder technisch (Plakat, Übertragung,
Daten, Tafel). Diese Runde sucht im Verein: das Mannschaftsfoto, die Kabine, das Vereinsheft, der
Schal am Geländer.

| Ordner | Leitidee |
|---|---|
| `profil/` | Das Team steht im Bild: Jede Person hat ihr Profil, und hinter jeder Zahl, die einem Menschen gehört, steht dieser Mensch. |
| `schal/` | Die App ist der Vereinsschal: Name, Resultat und die Zahl jedes Dings sind gestrickt, in den zwei Garnen des Vereins. |

Pro Ordner: `index.html` (eigenständig, im Browser öffnen, `?club=rot|blau|gelb|schwarz|weiss|gruen`
oder die Knöpfe oben), `README.md`, `skizzen.html` mit den verworfenen Leitideen, und `shots/` mit
den sechs Ansichten, `bogen.jpg`, `farben.jpg` (Start in allen sechs Vereinsfarben) und `skizzen.jpg`.

Quellen: `index.src.html` pro Ordner und die Bausteine in `lib/` (`profil.js` die Köpfe,
`strick.js` die Maschen, `figur.js` die Druckfiguren aus der verworfenen Skizze, `feld.js` Feld,
Diagramme und Daten). `python3 build.py` setzt sie zu den eigenständigen `index.html` zusammen,
`node shots.js <ordner> rot 2 "" farben` erzeugt die Bilder neu und meldet Elemente, die aus einem
Rahmen ragen.
