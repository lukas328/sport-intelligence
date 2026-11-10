# UX-Neustart

Alles für den Umbau der Oberfläche von `apps/web`. Stand: 10. November 2026. Umgesetzt ist davon
noch nichts.

| Datei | Wozu |
|---|---|
| `zielbild.html` | Das Bild: Gestaltungssystem, Realitätscheck, 13 Screens für Desktop und Handy. Im Browser öffnen. |
| `SPEC.md` | Die verbindliche Fassung für die Umsetzung: Prinzipien, Tokens, Bausteine, Navigation, Routen, jeder Screen, Wörter, Reihenfolge. |
| `ASSESSMENT.md` | Die Befunde aus den 66 Screenshots, pro Bereich. |
| `assets/halle.css` | Das CSS der Skizzen: Tokens und Bausteine zum Übertragen. |
| `assets/marker.js` | Die Filzstift-Striche als kleines Modul. |
| `assets/zielbild.js` | Zeichnet in den Skizzen Feld, Tafel, Diagramme und Symbole. Vorlage für Minifeld und Icons. |
| `assets/fonts/` | DSEG7 für die Anzeigetafel, mit Lizenz. |
| `src/screens/*.html` | Das Markup jedes Screens, einzeln lesbar. |
| `src/page.html`, `build.py` | Der Bericht und sein Build: `python3 docs/design/ux-reset/build.py` schreibt `zielbild.html` neu. |

## Vor dem Start

In `SPEC.md`, Abschnitt 14, stehen fünf Annahmen (Umfang, fünf Ziele, Wörter, Minifeld, Knöpfe in
Tinte). Wenn eine nicht passt, zuerst dort ändern.

## Auftrag an die UI-Session

Zum Kopieren:

> Lies `docs/design/ux-reset/SPEC.md` vollständig, dann `docs/design/ux-reset/README.md`, und
> öffne `docs/design/ux-reset/zielbild.html` im Browser (Playwright ist vorhanden), um die 13
> Screens an Desktop und Handy zu sehen. Das Markup jedes Screens steht in
> `docs/design/ux-reset/src/screens/`, das CSS dazu in `docs/design/ux-reset/assets/halle.css`.
>
> Baue die Oberfläche von `apps/web` nach dieser Spezifikation um. Arbeite in der Reihenfolge
> aus Abschnitt 13 der Spezifikation, jeder Schritt ein eigener Commit, der für sich läuft:
> Grundlage, Rahmen, Spiel, Szenen, Training und Team, Spieler und Eltern und Einstieg, Inhalt.
>
> Regeln:
> - Die Spezifikation gilt vor `docs/DESIGN.md` und ADR 023 / 024. Schreib ADR 025 und passe
>   `DESIGN.md` in Schritt 2 an.
> - Übertrage Tokens und Bausteine in `globals.css` und die React-Komponenten. Kopiere die
>   Klassen der Skizzen nicht eins zu eins.
> - Filzstift (Handschrift, Kreis, Haken, Strich, Tape) nur für Dinge, die ein Mensch getan hat.
>   Genau eine Anzeigetafel pro Screen. Die Vereinsfarbe nie auf Flächen oder Knöpfen.
> - Jeder Screen muss vollständig sein, wenn die Trainerin nichts von Hand getan hat.
> - Die Liste «Was wir nicht tun» in `zielbild.html` und Abschnitt 12 der Spezifikation sind die
>   Prüfliste. Baue sie als Lint-Regeln ein.
> - Alte Routen leiten um. Backend und API bleiben, wo es geht. Wo ein Screen Daten braucht, die
>   es noch nicht gibt (Teamnotiz, «gesehen von», «Bist du das?», Einladungslink, Zusage als
>   Normalfall), ergänze die API schmal und schreib es in den Commit.
> - Nach jedem Schritt: Tests, axe und die Screenshots (`docs/screens`) für die geänderten
>   Screens neu. Vergleiche sie mit dem Zielbild, bevor du weitergehst.
> - Was du nicht entscheiden kannst, kommt in `docs/OPEN_QUESTIONS.md`, mit deiner Annahme.
