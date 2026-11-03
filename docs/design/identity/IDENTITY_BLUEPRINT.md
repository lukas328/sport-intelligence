# Identity Blueprint: Die Halle

Ausführungsauftrag für Claude Code im Repo `sport-intelligence`.
Stand: 2026-11-03, geprüft gegen Commit `3ce0e79`.

Ablageort im Repo: `docs/design/identity/`. Dort liegen auch die Referenzen in `references/`.

## 0. Betriebsart

Lukas ist unterwegs und gibt nichts frei. Arbeite autonom, stelle keine Rückfragen und triff jede offene Entscheidung selbst.

- Arbeite auf dem Branch `identity/halle` ab aktuellem `main`.
- Halte Stand und nächsten Schritt in `docs/design/identity/PROGRESS.md` fest, Entscheidungen in `DECISIONS.md` im selben Ordner.
- Notiere die Startzeit. Ziel sind rund 3 Stunden. Reicht die Zeit nicht, gilt die Reihenfolge aus Abschnitt 6: Lieber wenige Screens konsequent als alle halb.
- Kein Merge nach `main`, kein Deployment, kein Force-Push.
- Am Ende steht ein offener Pull Request nach `main`.

### Verbote

Diese Arbeit läuft vollständig im Repo:

- Keine neuen Accounts, Abos, API-Keys oder Secrets.
- Keine externen Design-Tools, GUIs oder Dienste, also auch kein Figma, Mobbin oder Canva.
- Keine Bildgeneratoren und keine erfundenen Fotos oder Personen.
- Keine weiteren Plugins, Skills oder MCP-Server.
- Neue Abhängigkeiten nur aus npm und nur, wenn dieses Dokument sie nennt.
- Schriften nur mit SIL OFL und selbst gehostet, keine Anfragen an Font-Dienste.

## 1. Ziel

Die App soll sich anfühlen wie die Halle eines echten Vereins und nicht wie ein generiertes SaaS-Dashboard. Die UX, die Navigation und die Datenlogik bleiben erhalten. Dieser Auftrag ändert Identität, Hierarchie, Sprache und Momente.

Blindtest als Abnahme: Deckt man Logo und Vereinsnamen ab, muss ein Screenshot trotzdem sofort nach Handball aussehen und sich klar von einem Standard-Dashboard unterscheiden. Gleichzeitig muss die Vereinsfarbe den Eindruck spürbar verändern.

## 2. Befund

Der aktuelle Stand ist solide, wirkt aber aus diesen Gründen generiert:

| Merkmal | Ort | Problem |
|---|---|---|
| Fünf gleich grosse Kennzahlkacheln | `season/page.tsx` | Nichts ist wichtig, der Nutzer muss selbst interpretieren |
| Warmes Off-White, weisse Panels, ein Akzent | `globals.css`, `docs/DESIGN.md` | Aktueller Standard vieler Agenten |
| Archivo in breitem Schnitt | `app/layout.tsx` | Eigenwillig gemeint, inzwischen typisch |
| Runde Panels mit Hairline-Ring, Pillen-Buttons | `components/ui` | Gleiche Form auf jedem Screen |
| Lucide überall, auch als Navigation, Glitzer-Symbol für KI | 36 Dateien | Keine eigene Zeichensprache |
| Wenig Handball ausserhalb von Spielfeld und Torbild | Übersicht, Saison, Listen | Kein Bezug zum Sport auf den Einstiegsscreens |
| Diagramm mit einem einzigen Punkt | Saison | Wirkt leer und unüberlegt |
| Neutrale Texte | `apps/web/messages` | Keine Stimme, keine Aussage |

## 3. Die Idee

Die Dateien `references/halle-*.png` und `references/halle-*.html` sind das Zielbild und haben Vorrang vor den älteren Studien. Setze sie in den echten Komponenten um, nicht als Kopie. Zahlen und Platzhalter darin sind Beispiele. Die Studien zeigen die Herkunft der Mischung:

- Die Geometrie stammt aus `hallenboden-1440.png`.
- Die Arbeitsansichten stammen aus `matchblatt-1440.png`.
- Die Momente und die Vereinsfarbe stammen aus `vereinsposter-1440.png` und `matchkarte-540.png`.

Das System hat zwei Modi und eine klare Regel, wann welcher gilt:

| Modus | Zweck | Wo | Charakter |
|---|---|---|---|
| Bühne | Emotion, Überblick, ein Moment | Kopf von Übersicht, Saison und Spiel, Resultate, Teilen, Login, Landing | Vollflächige Vereinsfarbe, Spielfeldlinien, grosse Zahlen, eine Aussage |
| Werkbank | Konzentriertes Arbeiten | Tabellen, Video-Arbeitsplatz, Taktik, Formulare, Einstellungen | Ruhig, präzise, wie ein Spielbericht: Raster, Linien, klare Zahlen |

Regel: Pro Screen höchstens eine Bühne, und sie steht oben. Werkbank-Screens wie Einstellungen oder Formulare bekommen keine Bühne. Der Video-Arbeitsplatz bleibt ruhig, dort sind Video und Daten die Hauptsache.

## 4. Die Sprache

### Typografie

Installiere über npm die `@fontsource`-Dateien, kopiere nur die benötigten `woff2` nach `apps/web/src/fonts`, ergänze die OFL-Hinweise und entferne danach die npm-Pakete wieder. Binde sie mit `next/font/local` ein.

| Rolle | Schrift | Einsatz |
|---|---|---|
| Display | Big Shoulders Display 800, 900 | Bühne, Stand, Überschriften, grosse Zahlen |
| Text | Barlow 400, 500, 600 | Fliesstext und Bedienung |
| Daten | IBM Plex Mono 500, 600 | Tabellen, Zeiten, Statistik, kleine Marken |
| Handschrift | Reenie Beanie | Nur echte Trainernotizen, ab 24 px |

Archivo wird vollständig entfernt. Prüfe das Bundle- und das LCP-Budget. Lade nur die nötigen Schnitte.

### Farbe

- Die Bühne nutzt die rohe Vereinsfarbe als Fläche. Text ist Weiss oder Dunkel nach Kontrast, mit `clubTheme` und `contrastText` aus `lib/color.ts`.
- Die Tiefe entsteht aus der Vereinsfarbe, abgemischt mit Dunkel über `mix`. So bekommt jeder Verein seine eigene dunkle Fläche. Bei hellen Vereinsfarben wie Gelb entsteht dabei ein Olivton, dort gilt deshalb neutrales Dunkel `#14171c`.
- Die Neutraltöne werden leicht in Richtung Vereinsfarbe getönt. Das warme Off-White entfällt.
- Ein Signal-Token, Harzgelb `#ffd23f`, markiert genau eine Sache pro Screen, die Aufmerksamkeit braucht. Bei gelben oder sehr hellen Vereinsfarben fällt das Signal auf Dunkel zurück.
- Grün und Rot behalten ihre feste Bedeutung.
- Prüfe mindestens `#0b6bcb`, `#c8102e`, `#0f6b46`, `#003366`, `#111111`, `#ffd100`, jeweils hell und dunkel, mit Unit-Tests für Kontraste.

### Form

- Eckradius 2 bis 4 px, keine Panels mit 16 px und keine Pillen.
- Struktur entsteht über Raster, Linien, Fläche und Abstand, nicht über schwebende Karten.
- Keine Schatten ausser bei schwebenden Ebenen.
- Tabellen wirken wie ein Spielbericht: Linienraster, rechtsbündige Zahlen, Plex Mono.
- Klickbare Zahlen brauchen einen klaren Hover- und Fokuszustand, weil sie zu Clips führen.

### Spielfeld als Motiv

Baue `CourtLines`, ein dekoratives SVG mit `aria-hidden`, auf Basis von `packages/court`, damit die Geometrie echt bleibt:

- 6-m-Linie durchgezogen, 9-m-Linie gestrichelt, 7-m-Marke.
- Die Linien sind der Layoutrahmen, zum Beispiel steht der Stand im Torraum.
- Die Linien dürfen nicht durch Fliesstext laufen. Blende sie aus, wenn der Platz fehlt, etwa auf dem Handy.
- Keine Verläufe und keine Muster als reine Dekoration.

### Icons

- Zeichne eigene SVG-Icons für die wichtigsten Domänenobjekte und die Hauptnavigation: Spiel, Tor, Trikot, Taktik, Training, Szenen, Termine. Gleiches Raster, gleiche Strichlogik, kantig passend zur Form.
- Lucide bleibt nur für neutrale Bedienung wie Schliessen, Suche und Menü.
- Ersetze das Glitzer-Symbol. "Frag deine Daten" bekommt ein eigenes Zeichen oder gar keins.

### Stimme

Die Bühne trifft eine Aussage statt einer Beschriftung. Die Texte klingen wie jemand aus der Garderobe, kurz, direkt und ohne Marketing.

Regeln:

- Baue dafür deterministische Funktionen, zum Beispiel `seasonHeadline(stats)` und `matchHeadline(stats)`, mit Unit-Tests und Texten in `de-CH`, `en` und `fr`.
- Nutze vorhandene Erkenntnisse aus `/matches/{match_id}/insights`, wenn sie existieren. Dort sind die Belege bereits mit Filtern verknüpft.
- Jede Aussage muss aus echten Daten folgen. Erfinde nichts. Fehlt die Grundlage, zeige eine neutrale Überschrift.
- xG und andere Schätzungen bleiben als Schätzung erkennbar. Demo-Daten bleiben gekennzeichnet.
- Beispiel: Tore deutlich über xG ergibt "Mehr getroffen, als die Chancen hergaben." mit dem Beleg "22 Tore aus 14.3 erwarteten (geschätzt)".
- Passe auch leere Zustände und Erfolgsmeldungen an.

### Echte Inhalte

- Trainernotizen: Zeige echte Kommentare in Handschrift, wenn sie zum Moment passen. Gibt es keine, zeige nichts. Schreibe keine Notizen selbst.
- Standbilder: `has_poster` liefert echte Frames. Nutze sie in der Bühne oder in Listen nur, wenn Einwilligung und Rechte das erlauben. Bei `team.is_youth` oder unklarer Lage zeigst du das Bild nicht, und die Fläche bleibt Vereinsfarbe. Prüfe `consent` im bestehenden Code und in `docs/policy-matrix.md`. Lockere nichts.

### Momente

Baue zwei bis drei Momente, die Freude machen, keine Effekte:

1. Resultat nach einem Spiel: Der Stand zählt kurz hoch, dann steht er ruhig.
2. Analyse fertig: Die Meldung zeigt das Resultat in der Bühne statt eines generischen Toasts.
3. Matchkarte zum Teilen, siehe Slice 5.

Bewegung ist schnell und knapp, zeigt einen Zusammenhang und respektiert `prefers-reduced-motion`.

## 5. Harte Grenzen

- Navigation, Rollen, Rechte, Policies, Backend-Logik und Datenmodell bleiben unverändert.
- Jede Zahl führt weiterhin zu den Clips.
- WCAG 2.2 AA, Tastatur, Dark Mode, 390 px ohne horizontales Scrollen.
- Touch-Ziele und axe-Prüfungen bleiben grün.
- Bundle-Budgets: Startseite unter 250 kB, Routen unter 300 kB, LCP unter 2.5 s.
- UI auf de-CH mit "ss", keine langen Gedankenstriche, alle drei Sprachdateien pflegen.
- Bestehende Tests nur anpassen, wenn sich die beabsichtigte Gestaltung geändert hat. Ändere keine Tests, nur damit sie grün werden.

## 6. Reihenfolge

Committe klein. Nach jedem Schritt: `pnpm lint`, `pnpm typecheck`, `pnpm test`.

### Schritt 1: Ausgangslage

- Stack und Seed starten, Windows-Hinweise beachten (fehlt `make`, die Befehle aus dem `Makefile` direkt nutzen).
- Vorher-Screenshots unter `.ux-artifacts/before/` für Saison, Übersicht, Spielliste, Spiel, Login und Landing, je 1440 px und 390 px, hell und dunkel. Ergänze `.ux-artifacts/` in `.gitignore`, falls es fehlt.
- Lies `docs/DESIGN.md`, `references/` und `apps/web/src/lib/design-lint.test.ts`.

### Schritt 2: Fundament

- Schriften, Tokens, Form und Vereinsfarben umsetzen.
- `Stage`, `CourtLines`, `MatchScore`, `DataTable` und `MetricLink` bauen.
- Button, Karte, Eingabefelder und Tabs auf die neue Form bringen.
- Sidebar in die neue Sprache bringen, die Struktur bleibt. Sie darf die dunkle Vereinsfläche nutzen.
- `design-lint.test.ts` und `docs/DESIGN.md` anpassen, damit die neue Sprache verbindlich wird.

### Slice 1: Saison

Das ist der Referenz-Screen.

- Bühne mit Aussage, letztem Resultat und höchstens einer primären Aktion.
- Kennzahlen als eine durchgehende Spielberichtszeile, die wichtigste per Signal markiert.
- Diagramm erst ab drei Spielen. Darunter ein ehrlicher Text, was ab dann sichtbar wird.
- Spieltabelle im Matchblatt-Stil.

### Slice 2: Übersicht

Die Bühne beantwortet die wichtigste Frage der Rolle. Trainer: letztes oder nächstes Spiel. Spieler: nächster Termin und neue Szenen. Eltern bekommen die ruhige Werkbank.

### Slice 3: Spiele und Spielkopf

- Spielliste wie ein Spielplan: Datum, Gegner, Resultat, Sieg oder Niederlage klar lesbar.
- Spielkopf mit Bühne. Der Video-Arbeitsplatz darunter bleibt ruhig.

### Slice 4: Erster Eindruck

Login, Registrierung, Onboarding und Landing im Bühnenmodus.

### Slice 5: Matchkarte

- Ein Button im Spiel erzeugt lokal ein PNG im Format 4:5.
- Nutze vorhandene Mittel im Browser, zum Beispiel SVG zu Canvas, ohne externen Dienst.
- Inhalt: Verein, Team, Datum, Stand, Gegner und höchstens zwei Kennzahlen. Keine Personen und keine Bilder.
- Nur für Rollen mit passenden Rechten, Demo-Daten mit Kennzeichnung.

### Slice 6: Werkbank-Durchgang

Roster, Einstellungen, Training, Taktik und restliche Listen auf Tokens und Form prüfen. Keine Bühnen hinzufügen.

### Schritt 7: Abschluss

- Dark Mode, 390 px und die sechs Vereinsfarben prüfen.
- `pnpm lint`, `pnpm typecheck`, `pnpm test`, Web-Build, Budget und relevante E2E-Specs ausführen.
- Nachher-Screenshots erstellen.
- Eine neue ADR mit der nächsten freien Nummer schreiben.
- `docs/design/identity/REPORT.md` schreiben: Was wurde geändert, was bleibt offen, Testergebnisse, Vorher und Nachher.
- Pull Request nach `main` öffnen. Aktualisierte Doku und Screenshots gehören in die Beschreibung, soweit möglich.

## 7. Review gegen den Durchschnitt

Nach Slice 1, nach Slice 3 und am Schluss startest du einen Agenten mit frischem Kontext. Er bekommt nur Screenshots, `references/` und diese Fragen:

1. Würde man ohne Logo erkennen, dass es um Handball geht?
2. Was davon hätte ein Standard-Dashboard genauso gemacht?
3. Was ist die eine Aussage dieses Screens?
4. Wirkt die Vereinsfarbe wie eine Identität oder nur wie ein Akzent?
5. Gibt es ein Element ohne Zweck?
6. Ist etwas schwerer lesbar oder bedienbar geworden?

Behebe konkrete Befunde. Pro Review höchstens drei Runden, damit keine Endlosschleife entsteht. Geschmack entscheidet nie gegen Lesbarkeit, Barrierefreiheit oder Ehrlichkeit der Daten.

Halte dich zurück: Die Lösung ist nicht mehr Dekoration. Wenn ein Element nur da ist, um "anders" zu wirken, entferne es.

## 8. Wenn etwas blockiert

Dokumentiere den Grund in `PROGRESS.md`, wähle die sichere Variante und arbeite weiter. Offene Punkte für Lukas kommen in `docs/design/identity/FOR_LUKAS.md`. Starte nichts, was gegen Abschnitt 0 verstösst.

Fertig ist der Auftrag, wenn das Fundament und mindestens die Slices 1 bis 3 umgesetzt sind, alle Prüfungen auf dem Branch bestehen, `REPORT.md` vorliegt und der Pull Request offen ist. Bleibt Zeit, folgen die Slices 4 bis 6.
