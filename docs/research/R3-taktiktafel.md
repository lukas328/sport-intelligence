# R3: Digitale Taktiktafel, Best Practices

Stand 16.11.2026. Auftrag aus `docs/ux-test/livegang/BEFUNDE.md` (R3, gehört zu K23). Grundlage für
den Umbau von `apps/web/src/components/tactics/board.tsx` und `play-editor.tsx`.

## Angeschaute Produkte

| Produkt | Sportart | Was auffällt |
|---|---|---|
| Coach Tactic Board: Handball++ (Bluelinden, iOS/Android) | Handball | Ganzes Feld, halbes Feld, Trainingsfeld, leere Tafel; Linienarten durchgezogen, gepunktet, gebogen, Prellen-Linie; Animationsmodus mit Pause und Export; Redo als eigene Funktion nachgereicht; Dunkel- und Hellmodus, mehrere Feldfarben, Teamfarben wählbar; Export Bild, PDF, früher MP4; «einfacherer Zugriff auf überlappende Spieler» als eigenes Release-Thema |
| Pocket Coach Board Handball | Handball | Ablauf «Spieler wählen, ziehen, Laufweg zeichnen, Play drücken»; Vorlagen für Abwehrsysteme, Schnelle Mitte, 2. Welle, Standards |
| Handball Playbook Board | Handball | Spieler und Ball mit dem Finger schieben, Wiedergabe-Tempo einstellbar, «automatischer Aufnahmemodus» (jede Bewegung wird zur Animation) |
| TacticHand | Handball | Nur 3D-Betrachter für Spielzüge aus einer anderen Software: zeigt, wie wichtig das Teilen an Spieler ist |
| easy2coach Tactics | Fussball u. a. | Ziehen und Ablegen, Laufwege als Pfeile und Kurven, «mehrere Animationsschritte pro Zeichnung», Teilen per WhatsApp, Mail, Link; PNG, PDF, MP4; über 600 Vorlagen zum Kopieren und Anpassen |
| tactical-board.com | viele, auch Beachhandball | Browser, Schema als Bild, Animation als Video, Teilen per Link, Hintergrundfarbe wählbar |
| TacticalPad | Fussball u. a. | Notizblock, eigene Felder; in Bewertungen fehlt ein «Rückgängig» und eine bessere Ablage mit Vorlagen |
| FastDraw (Hudl) | Basketball, Eishockey, Fussball | Mehrphasige Spielzüge, «FastBuild» schiebt die Spieler automatisch ans Ende ihrer Laufwege in die nächste Phase; Spielzug spiegeln mit einem Klick; Verteidiger per Vorlage; farbige Flächen für Übungen; Spielbuch an die Handys der Spieler |
| HockeyShare, Hockey Coach Vision, Sportplan Animator | Eishockey, Hockey | Getrennte Modi Zeichnen und Animieren, Zeitleiste, Aktionsobjekte (Lauf, Pass, Schuss), Export MP4, teils 3D |
| CoachThem Sketchpad | mehrere | Linien rasten in 45-Grad-Schritten ein, Ankerpunkte nachträglich verschieben, Ausrichten-Hilfen, Export als PNG |

## Was gute Tafeln gemeinsam haben

**Bedienung**

1. Die Tafel ist die Hauptsache. Werkzeuge stehen am Rand, nicht in Formularen. Der Ablauf heisst
   überall gleich: Spieler ziehen, Laufweg zeichnen, abspielen (Pocket Coach, easy2coach).
2. Ziehen ist der Normalfall, ohne Werkzeugwahl. Gezeichnet wird mit einem gewählten Werkzeug, der
   Pfeil beginnt am Spieler.
3. Phasen statt Einzelbilder: «nächste Phase» übernimmt die Lage und schiebt jeden Spieler ans Ende
   seines Laufwegs, der Ball folgt dem Pass (FastDraw FastBuild). Das haben wir schon (`nextFrame`).
4. Rückgängig und Wiederholen sind Pflicht; ihr Fehlen ist die häufigste Klage (TacticalPad,
   Handball++ hat Redo nachgereicht).
5. Überlappende Spieler müssen greifbar bleiben (eigenes Release-Thema bei Handball++).
6. Vorlagen als Startpunkt, die man kopiert und anpasst (easy2coach 600+, FastDraw PlayBank).
   Spiegeln (links und rechts tauschen) spart doppelte Arbeit (FastDraw).

**Darstellung**

1. Helles Feld oder kräftige Linien; die besseren Apps lassen Feldfarbe und Teamfarben wählen,
   weil dunkle Felder auf Handy und Beamer schlecht lesbar sind.
2. Linienarten sind sportübergreifend gleich: Laufweg durchgezogen mit Pfeilspitze, Pass
   gestrichelt, Prellen als Zickzack oder Welle, Sperre als Linie mit Querbalken (Basketball- und
   Handball-Lehrmittel, Handball++ «dribble line»). Unterschied über das Muster, nicht nur über die
   Farbe: so bleibt es auch für Farbenblinde und im Schwarzweissdruck lesbar.
3. Eigene und gegnerische Spieler unterscheiden sich in Farbe **und** Helligkeit; Farbpaare wie
   Blau und Orange (Okabe-Ito-Palette) bleiben bei allen häufigen Farbsehschwächen unterscheidbar.
   WCAG 1.4.11 verlangt für Grafiken, die man zum Verstehen braucht, 3:1 gegenüber der Umgebung;
   ein dunkler Rand um jede Marke sichert das auf jedem Untergrund.
4. Beschriftung in der Marke (Position oder Nummer), gross und fett; lieber weniger Zeichen als
   kleine Schrift.
5. Hochformat auf dem Handy: das halbe Feld mit dem Tor oben (wie in den Handball-Lehrmitteln),
   das ganze Feld hochkant statt winzig quer. Querformat für die grosse Ansicht.

**Teilen**

Bild (PNG, PDF), Video (MP4) und Link sind Standard; der Link braucht kein Konto (tactical-board,
easy2coach). Spieler sehen nur, nicht bearbeiten (TacticHand als Gegenbeispiel: nur Betrachter,
dafür aber für alle).

## Was sie schlecht machen

- Werkzeugleisten mit 20 kleinen Symbolen ohne Text; man weiss nicht, in welchem Modus man ist.
- Kein Rückgängig, oder nur «letzten Pfeil löschen».
- Zeichnen und Ansehen sind nicht getrennt: beim Antippen verschiebt man aus Versehen Spieler.
- Kleine Marken auf dem ganzen Feld im Hochformat, Beschriftungen unter 10 px.
- Vorlagen, die fachlich nicht stimmen (Spieler im Torraum, Abwehr im Rückraum).
- Funktionen hinter Abo-Schranken (Video-Export, Vorlagen), Werbung in der Tafel.

## Was wir übernehmen (umgesetzt in K23)

| Punkt | Umsetzung |
|---|---|
| Tafel als Hauptansicht, Ansehen und Bearbeiten getrennt | Spielzug öffnet in «Ansehen» mit grosser Tafel und Abspielen; Trainer schalten auf «Bearbeiten» |
| Ziehen als Normalfall, Werkzeuge mit Text | Werkzeugleiste «Ziehen, Laufweg, Pass, Prellen, Sperre, Ball» mit Symbol und Wort, 44 px hoch |
| Rückgängig und Wiederholen | Schaltflächen und Tastatur (Strg+Z, Strg+Umschalt+Z, Strg+Y) über alle Änderungen |
| Phasen mit Übernahme der Laufwege | bestehendes `nextFrame`, Zeitleiste mit Abspielen und Pause, Tempo 0,5×, 1×, 2× |
| Eigenes Farbschema mit geprüftem Kontrast | helles Feld, Torraum leicht blau, Linien in Tinte; wir blau, Gegner orange, beide mit dunklem Rand; Ball gelb mit Rand; Kontrast im Test geprüft |
| Linienarten über Muster | Laufweg durchgezogen, Pass gestrichelt, Prellen Zickzack, Sperre mit Querbalken |
| Hochformat | halbes Feld mit Tor oben; ganzes Feld auf schmalen Bildschirmen hochkant; «Grosse Ansicht» füllt den Bildschirm (Handy quer) |
| Überlappen verhindern | Vorlagen mit Mindestabstand (Test), Marken bleiben im Feld, Trefferfläche 44 px |
| Vorlagen fachlich korrekt | alle Positionen aus der Geometrie von `@handball/court` (6-m- und 9-m-Linie um die Pfosten), nur Torhüter im Torraum, Test dafür |
| Spieler hinzufügen und entfernen | «+ Wir», «+ Gegner», Löschen, Beschriftung ändern |
| Spiegeln | «Spiegeln» tauscht links und rechts (Positionen, Laufwege, Beschriftung LA und RA, RL und RR) |
| Teilen als Video | gehört zu K20 und Teilen (Strom E1); die Tafel ist dafür vorbereitet (gleiche Darstellung im geteilten Link) |

## Quellen

- Coach Tactic Board: Handball++, App Store: https://apps.apple.com/app/id861263159
- Pocket Coach Board Handball, App Store: https://apps.apple.com/app/id6755515245
- Handball Playbook Board: https://mwm.ai/apps/handball-tactics-board/6749554963
- TacticHand: https://apps.apple.com/us/app/id425365232
- easy2coach Tactics: https://www.easy2coach.net/en/tactics/
- tactical-board.com, Beachhandball: https://tactical-board.com/uk/beach-handball
- TacticalPad, App Store: https://apps.apple.com/app/id512949303
- FastDraw (Hudl): https://www.hudl.com/products/fastmodel und https://www.hudl.com/blog/how-fastdraw-elevates-your-playbook
- HockeyShare Diagrammer: https://v2.hockeyshare.com/support/kb/drill-diagrammer
- Hockey Coach Vision: https://hockeycoachvision.com
- Sportplan Animator: https://www.sportplan.net/drills/Hockey/Hockey-Coaching-Animator.jsp
- CoachThem Sketchpad: http://www.coachthem.com/blogs/blog/1527878-sketchpad-drill-drawing-features
- Taktikboard Handball, Rezension Friedrich Plus: https://www.friedrich-verlag.de/friedrich-plus/sekundarstufe/sport/laufen-springen-werfen/nuetzlicher-digitaler-unterrichtshelfer-im-handball-7349
- WCAG 2.1, 1.4.11 Nicht-Text-Kontrast: https://www.w3.org/WAI/WCAG21/Understanding/non-text-contrast.html
- Okabe-Ito-Palette (Farbsehschwäche): https://www.datawrapper.de/blog/colorblindness-part2
