# R4: Websites, die Lust aufs Ausprobieren machen

Stand 16. November 2026. Grundlage für K24 (Startseite neu). Angesehen wurden die Startseiten von
acht Produkten: vier aus der Sport-Videoanalyse, eine Sport-App und drei Software-Produkte, die für
gute Produktseiten bekannt sind. Gezählt sind die sichtbaren Wörter im Hauptteil, ohne Menü und
Fusszeile (geschätzt aus dem Seitentext).

Zum Vergleich: unsere alte Startseite hatte **rund 740 Wörter** im Hauptteil, 11 Abschnitte, und
das erste Produktbild kam erst nach dem Kopf, der Farbwahl und den «drei Dingen».

## Die Beispiele

| Produkt | Kopf (Versprechen) | Wörter | Was auffällt |
|---|---|---|---|
| Veo (Kamera und Analyse, Fussball und andere) | «Record, analyse, and livestream every match» | ca. 700 | Drei Schritte direkt nach dem Kopf («Capture, analyse, and share … in three simple steps»), dann je Produkt ein Block mit Bild (Laptop- und Handy-Rahmen). Zitate von Trainern mit Namen. Sportart wechselt im Kopf. |
| Hudl (Video und Daten, alle Ebenen) | «Change the Way You See the Game» | ca. 500 | Ein Satz Vision («Powered by video, data and AI…»), dann sechs Bereiche als Karten, je ein Satz und ein Bild. Bewegte Collage im Kopf. Kundengeschichten tragen das Storytelling. |
| Spiideo (Kameras, Analyse, Übertragung) | «Sports video for the automation age» | ca. 900 | Viel für Verbände und Profis: Logo-Wand, Reiter nach Zielgruppe, Sportarten-Raster. Wirkt gross, aber auch voll. Gegenbeispiel für «zu viele Zielgruppen auf einer Seite». |
| Catapult (Leistungsdaten, Profisport) | «Unleash Potential» | ca. 350 | Sehr wenig Text, Vision nur angedeutet, dafür Zahlen (Länder, Sportarten, Teams). Ohne Produktbild bleibt unklar, was man bekommt. |
| Strava (Sport-App) | «Community-Powered Motivation» | ca. 500 (ohne Wiederholungen) | Registrieren direkt im Kopf. Drei Funktionen, je zwei, drei Sätze neben echten App-Bildern im Handy-Rahmen. Kurze Vertrauenszeile («kostenlos, alle Geräte»). |
| Linear (Software für Produktteams) | «The product development system for teams and agents» | ca. 300 | Ein echtes Produktbild sofort unter dem Kopf, das wie die App aussieht. Jeder Abschnitt: eine Überschrift, ein bis drei Sätze, ein grosses UI-Bild. Ruhige, kurze Animationen. |
| Raycast (Mac-Werkzeug) | «Your shortcut to everything.» | ca. 750 | Zweiter Satz als Haltung: «It's not about saving time. It's about feeling like you're never wasting it.» Danach Funktionen als Bild mit einer Zeile. Gleicher Aufruf oben und unten. |
| Things (Aufgaben-App) | «the award-winning personal task manager» | ca. 800 (davon mehr als die Hälfte Pressezitate) | Ein Video ganz oben, Geräte-Collage, wenig eigener Text. Vertrauen über Auszeichnungen und Zitate. |

Arc (Browser) war als Beispiel vorgesehen, die Seite ist aber zum Abschiedsbrief geworden (Arc wird
eingestellt) und taugt nicht mehr als Vorbild.

## Was alle guten Seiten gemeinsam haben

1. **Ein Versprechen in fünf bis acht Wörtern**, darunter ein Satz, was man bekommt. Kein Absatz.
2. **Das Produkt sofort zeigen**: ein echtes App-Bild (oder ein kurzes Video) im ersten Bildschirm,
   meist im Geräte-Rahmen (Handy, Laptop, Browser). Linear, Strava und Veo zeigen das echte UI,
   nicht eine Illustration.
3. **Ein Hauptknopf**, oben und unten gleich beschriftet («Get started», «Buy now», «Download»),
   daneben höchstens ein zweiter («Demo», «Book a call»).
4. **Drei Schritte** für den Ablauf (Veo: aufnehmen, analysieren, teilen). Jeder Schritt ein Bild,
   ein Satz.
5. **Abschnitte nach einem Muster**: Überschrift, ein bis drei Sätze, grosses Bild. 300 bis 700
   Wörter für die ganze Seite. Details liegen auf Unterseiten («Learn more →»).
6. **Haltung und Vision in einem Satz**, nicht in einem Abschnitt (Raycast, Hudl).
7. **Vertrauen kurz**: eine Zeile oder drei kleine Punkte (kostenlos, Datenschutz, Geräte), dazu
   Kundenstimmen, sobald es sie gibt.
8. **Bewegung sparsam**: Bilder gleiten beim Scrollen herein, ein Produktbild läuft langsam durch,
   nichts blinkt. Wer «weniger Bewegung» eingestellt hat, sieht alles still (bei den angesehenen
   Seiten nicht überall sauber gelöst).

## Was wir übernehmen

| Übernehmen | So bei uns |
|---|---|
| Versprechen plus ein Satz | «Nach dem Spiel wissen, woher die Tore kamen.» Ein Satz darunter: Handy oder Kamera, jedes Tor als Szene, drei Dinge fürs Training. |
| Echtes Produktbild im ersten Bildschirm | Startseite der App im Handy-Rahmen, das Bild läuft langsam nach unten (Resultat, dann die drei Dinge), dahinter das Spiel am Computer. Echte Bildschirmfotos aus der App mit dem Demo-Verein (`apps/site/scripts/app-screens.mjs`). |
| Ein Hauptknopf | «Kostenlos starten» oben, in der Mitte und unten; «Demo-Spiel ansehen» als zweiter Knopf. Die Team-Suche ohne Konto bleibt, aber am Schluss. |
| Drei Schritte mit Bild | «Filmen. Hochladen. Prüfen.»: Hallenplan, Upload-Dialog, Prüf-Frage aus der App. |
| Abschnitt = Überschrift, ein Satz, Bild | «Was du nach jedem Spiel bekommst»: Szene im Video, Szenen-Suche, Saison. Je ein Satz. |
| Demo zum Anfassen | Die Taktikkamera läuft live auf der Startseite, mit Ball und handballtypischen Laufwegen, Farbe wählbar. |
| Vision in einem Satz | «Profis haben Analysten. Du hast den Samstagabend.» Zwei kurze Sätze dazu, Link «Über uns». |
| Vertrauen kurz | Drei Punkte: Video gehört dem Verein, Einwilligung per Link, Schweizer Datenschutz. Link auf «Was es kann und was nicht». |
| Preis kurz | Eine Zahl (CHF pro Monat), Gratis-Zeit, Link «Alle Preise». |
| Bewegung sparsam | Hereingleiten beim Scrollen (IntersectionObserver, nur was unter dem Bildschirm liegt), das Handy-Bild läuft langsam durch; bei `prefers-reduced-motion` alles still. Keine Bibliothek. |

## Was wir bewusst nicht übernehmen

- **Logo-Wände und Kundenzitate**: Wir haben noch keine echten Kunden, die wir zitieren dürfen.
  Erfundene Stimmen kommen nicht in Frage. Sobald es Pilotvereine gibt, kommt ein Zitat zwischen
  Teilen und Vertrauen.
- **Zahlen ohne Beleg** (Catapult, Hudl): Wir nennen nur, was gemessen ist.
- **Viele Zielgruppen auf einer Seite** (Spiideo): Die Startseite spricht die Trainerin an. Vorstand
  und Eltern finden ihre Antworten unter «Daten und Einwilligung» und «Preise».
- **Autoplay-Video mit Ton** und schwere Animationsbibliotheken: Die Seite soll auf einem alten
  Handy in der Halle schnell laden.

## Quellen

Abgerufen am 16. November 2026:

- https://www.veo.com/
- https://www.hudl.com/
- https://www.spiideo.com/
- https://www.catapult.com/
- https://www.strava.com/
- https://linear.app/
- https://www.raycast.com/
- https://culturedcode.com/things/
- https://arc.net/ (nicht verwendet, siehe oben)
