# UX-Neustart

Alles für den Umbau der Oberfläche von `apps/web`. Stand: 10. November 2026. Umgesetzt ist davon
noch nichts.

| Datei | Wozu |
|---|---|
| `zielbild.html` | Das Bild: Fokus, Gestaltungssystem, 12 Screens für Desktop und Handy. Im Browser öffnen. |
| `SPEC.md` | Die verbindliche Fassung für die Umsetzung: Prinzipien, Tokens, Bausteine, Navigation, Routen, jeder Screen, Wörter, Reihenfolge. |
| `richtungen.html` | Vier alternative Gestaltungsrichtungen zum Abwägen (Konsole, Trikot, Piktogramm, Kassette), je am Start-Screen. Quellen in `richtungen/`. |
| `ASSESSMENT.md` | Die Befunde aus den 66 Screenshots, pro Bereich. |
| `assets/halle.css` | Das CSS der Skizzen: Tokens und Bausteine zum Übertragen. |
| `assets/marker.js` | Die Filzstift-Striche als kleines Modul. |
| `assets/zielbild.js` | Zeichnet in den Skizzen Feld, Tafel, Diagramme und Symbole. Vorlage für Minifeld und Icons. |
| `assets/fonts/` | DSEG7 für die Anzeigetafel, mit Lizenz. |
| `src/screens/*.html` | Das Markup jedes Screens, einzeln lesbar. |
| `src/page.html`, `build.py` | Der Bericht und sein Build: `python3 docs/design/ux-reset/build.py` schreibt `zielbild.html` neu. |

## Vor dem Start

**Die Gestaltungsrichtung ist noch nicht entschieden.** `zielbild.html` und `SPEC.md` beschreiben
die Richtung «Halle». `richtungen.html` stellt ihr vier Alternativen gegenüber. Aufbau, Umfang und
Wörter gelten für jede Richtung; Aussehen, Tokens und Bausteine werden nach der Wahl angepasst. Die
UI-Session startet erst danach.

In `SPEC.md`, Abschnitt 14, stehen sechs Annahmen (Kern ist die Spielauswertung für die Trainerin,
Spieler-Funktionen ausgeblendet, Einwilligung per Link, vier Ziele, «Sammlung», Minifeld). Wenn
eine nicht passt, zuerst dort ändern.

## Auftrag an die UI-Session

Zum Kopieren:

> Lies `docs/design/ux-reset/SPEC.md` vollständig, dann `docs/design/ux-reset/README.md`, und
> öffne `docs/design/ux-reset/zielbild.html` im Browser (Playwright ist vorhanden), um die 12
> Screens an Desktop und Handy zu sehen. Das Markup jedes Screens steht in
> `docs/design/ux-reset/src/screens/`, das CSS dazu in `docs/design/ux-reset/assets/halle.css`.
>
> Baue die Oberfläche von `apps/web` nach dieser Spezifikation um. Arbeite in der Reihenfolge
> aus Abschnitt 13 der Spezifikation, jeder Schritt ein eigener Commit, der für sich läuft:
> Grundlage, Rahmen, Spiel, Szenen, Saison und Team und Einstieg, Inhalt.
>
> Regeln:
> - Die Spezifikation gilt vor `docs/DESIGN.md` und ADR 023 / 024. Schreib ADR 025 und passe
>   `DESIGN.md` in Schritt 2 an.
> - Übertrage Tokens und Bausteine in `globals.css` und die React-Komponenten. Kopiere die
>   Klassen der Skizzen nicht eins zu eins.
> - Der Umfang ist Abschnitt 1 der Spezifikation: Spielauswertung für die Trainerin. Baue keine
>   Kommunikation, keine Zusagen, keine Termine. Was es davon gibt, kommt hinter die
>   Team-Einstellung «Teamfunktionen» (standardmässig aus) und wird nicht gelöscht.
> - Der Rahmen ist der Hallenboden, der Inhalt ein Blatt darauf. Das gelbe Blatt nur für die
>   drei Dinge. Genau eine Anzeigetafel pro Screen. Die Vereinsfarbe nie auf Flächen oder
>   Knöpfen. Filzstift (Handschrift, Kreis, Haken, Tape) nur für Dinge, die ein Mensch getan hat.
> - Jeder Screen muss vollständig sein, wenn die Trainerin nichts von Hand getan hat.
> - Die Liste «Was wir nicht tun» in `zielbild.html` und Abschnitt 12 der Spezifikation sind die
>   Prüfliste. Baue sie als Lint-Regeln ein.
> - Alte Routen leiten um. Backend und API bleiben, wo es geht. Wo ein Screen Daten braucht, die
>   es noch nicht gibt (Themen über mehrere Spiele, Gegentore nach Position, Vorschau für
>   geteilte Links, Einwilligung per Link), ergänze die API schmal und schreib es in den Commit.
> - Nach jedem Schritt: Tests, axe und die Screenshots (`docs/screens`) für die geänderten
>   Screens neu. Vergleiche sie mit dem Zielbild, bevor du weitergehst.
> - Was du nicht entscheiden kannst, kommt in `docs/OPEN_QUESTIONS.md`, mit deiner Annahme.
