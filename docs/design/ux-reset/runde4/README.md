# Runde 4

Zwei neue Richtungen aus zwei Feldern, die bisher fehlten. Je `README.md`, eine eigenständige
`index.html` (ohne Build zu öffnen, nur Google Fonts aus dem Netz, Vereinsfarbe über die Knöpfe oder
`?club=rot|blau|gelb|schwarz|weiss|gruen`) und `shots/` mit den sechs Ansichten, `bogen.jpg` (alle
Ansichten) und `farben.jpg` (der Start mit allen sechs Vereinsfarben).

| Ordner | Feld | Leitidee |
|---|---|---|
| `linie/` | radikal reduziert, eine Geste | Ein Spiel ist eine Linie. |
| `hallenlicht/` | Material und Raum | Die App ist die Halle von der Tribüne aus. |
| `skizzen/` | beide | die vier Leitideen pro Feld als schnelle Start-Skizzen, `skizzen.jpg` |

Bauen: `python3 docs/design/ux-reset/runde4/build.py` (setzt `common.js` ein: Rahmen,
Vereinsfarben mit Kontrast- und Kollisionsregel, Spieldaten). Bilder:
`node docs/design/ux-reset/runde4/shots.js <ordner>`.
