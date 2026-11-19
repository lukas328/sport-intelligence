# Befunde Runde 5: externes Website-Review (19.11.2026)

Quelle: Review «Website-Review Handball Intelligence» vom 19.11.2026 (an Lukas, Desktop ca. 1100 px,
21 Punkte). Hier steht nur die Bewertung der Hauptsitzung: was zu unserer Lage passt, was nicht,
und warum. Grundsatz: nichts blind übernehmen, und nichts auf die Website schreiben, was das Produkt
heute nicht hält.

## Leitlinie (Lukas, 19.11.)
Die Website beschreibt das Produkt so, wie es beim Release sein wird (Vision), nicht den Stand der
Testphase. Darum werden Aufwand und Analysedauer nicht auf heutige Messwerte zurückgestuft. Erfunden
wird trotzdem nichts, was kein Produkt-Versprechen ist (z. B. Zitate von Pilotteams).

## Fakten, an denen die Vorschläge gemessen werden
- **Analysedauer:** Lukas' ganzer Lauf auf Staging (99 min Video, 2 vCPU) brauchte 3 h 33 min, also
  2.2 x Videolänge (`docs/plans/produkt-analyse-integration.md`). Ein Spiel mit etwa 70 min
  Aufnahme ist damit nach etwa 2.5 h fertig, dazu kommt der Upload. «Samstag, 22 Uhr» nach einem
  Spiel bis etwa 19 Uhr ist also knapp, aber ehrlich. Mit GPU wird es kürzer.
- **Eigener Aufwand:** nicht gemessen (Q-REC-SHOTZONE in `docs/OPEN_QUESTIONS.md`). Auf Lukas'
  99-min-Video waren es nach der Kürzung noch 122 Tor-Fragen. «Meist unter zehn Minuten» können wir
  heute **nicht** belegen.
- **Wurfort:** seit A22 (19.11.) schlägt die App den Wurfort vor, ein Tipp bestätigt.
- **Frag deine Spiele:** Ein Sprachmodell wird nur mit `HB_ANTHROPIC_API_KEY` genutzt; der ist
  heute aus (OPEN_QUESTIONS Punkt 12).
- **Pilotteams:** gibt es noch keine. Zitate oder Logos wären erfunden.

## Bewertung pro Punkt
| Nr. | Vorschlag | Entscheid | Begründung |
|---|---|---|---|
| 1 | Aufwand einheitlich erzählen | **nein (Lukas, 19.11.)** | Die Website erzählt die Vision, so wie das Produkt beim Release sein wird («Du filmst, die Analyse macht den Rest»). Kein Zurückstufen auf den heutigen Stand der Testphase. Nur ein echter Widerspruch zwischen zwei Seiten wird angeglichen, und zwar in Richtung Vision. |
| 2 | Analysedauer als Zahl | **nein (Lukas, 19.11.)** | Wie Punkt 1: «Samstag, 22 Uhr» bleibt als Vision; keine Zahl aus der CPU-Testphase. |
| 3 | Ein Beispieluniversum | **umsetzen** | Widersprüchliche Zahlen (11 von 29 vs. 6 von 22, Saisonbalken 6/9/11) kosten Glaubwürdigkeit; kein Aufwand an Wahrheit. |
| 4 | Menü «Hilfe», Funktion überall «Frag deine Spiele» | **umsetzen** | Die URL ist schon `/hilfe/`; «Fragen» ist doppelt belegt. EN «Pricing», «Help». |
| 5 | Menschen zeigen | **Lukas** | Nur mit echten Namen und Fotos; hängt an der Firma (OPEN_QUESTIONS Punkt 1). |
| 6 | Mobile testen | **umsetzen (Teil)** | Mit Playwright auf Handy-Breiten prüfen und Fehler beheben (Querscroll, Mockups, Preistabelle). Das echte iPhone (Q-QA-1) bleibt bei Lukas. |
| 7 | Legal-Platzhalter, KI-Anbieter | **Lukas und Fachperson** | Hängt an Firma und Rechtsprüfung (OPEN_QUESTIONS Punkte 1, 2, 4). Die Liste der Prüfstellen aus dem Review unten übernehmen. |
| 8 | Einwilligung als Schritt 0; Nein und Gegnerteam erklären | **umsetzen, nur was der Code tut** | Schritt 0 ist eine echte Hürde. Was bei Nein passiert, wird aus dem Code beschrieben (z. B. Namen verborgen, `roster.visible_players`), nichts dazu erfunden. Rechtliche Wertung zum Gegnerteam bleibt bei der Fachperson. |
| 9 | Echte Stimmen | **später** | Es gibt noch keine Pilotteams. Erst nach dem Pilot, nur echte Zitate mit Einwilligung. |
| 10 | Animationen schneller, reduced motion | **umsetzen** | Klein, verbessert Lesbarkeit; `prefers-reduced-motion` ist ohnehin Pflicht. |
| 11 | «Aussen rechts ist zu» abfedern | **umsetzen** | Passt zur Haltung «jede Zahl mit ihrer Basis»; der Satz steht schon in der Demo. |
| 12 | Zeitmarke für «Was heisst das fürs Training?», Sonntag angleichen | **umsetzen** | Kleiner Bruch im roten Faden; Lukas mag die Wochen-Story, sie wird nur geschlossen, nicht umgebaut. |
| 13 | Preise: «ab CHF 39», Gratis-Plan nach Test, Karte | **teilweise** | «ab CHF 19.90 pro Team im Verein» oder «CHF 39 pro Team, Vereine ab CHF 199» ist reine Rechnung: umsetzen. Gratis-Plan nach dem Test in einer Zeile erklären: umsetzen. **Keine** Kartenzahlung bewerben, Stripe ist aus; dass die AGB die Karte nennen, kommt auf die Prüfliste. Preise bleiben als «noch nicht endgültig» markiert (Punkt 7 der offenen Fragen). |
| 14 | Teamsuche ankündigen; DHB/nuLiga nennen | **umsetzen** | Stärkster Moment der Website, ehrlich (Spielberichte per Link aus DHB, nuLiga, HLA sind gebaut). |
| 15 | Torhüter, Spielzüge, Highlights, PDF zeigen | **später, klein** | Sinnvoll, aber neues Material; zuerst 1 bis 4. Torhüter nur mit Hinweis «ab Plan Team». |
| 16 | Wiederholte Mockups kürzen | **nur Teamchat** | Lukas hat Start, Demo und «So funktioniert es» in Runde 4 selbst abgenommen. Nur das Teamchat-Mockup ausserhalb von Start und Demo verkleinern; der Rest bleibt, bis Lukas es anders will. |
| 17 | Bildrechte, fiktive Vereine, Mitbewerber-Vergleich | **prüfen** | Fiktive Vereinsnamen gegen die Teamsuche von handball.ch prüfen und bei einem Treffer umbenennen. Bildrechte und UWG-Vergleich auf die Prüfliste für Lukas. |
| 18 | Leerraum nach «Verloren. Aber warum?» | **umsetzen** | Klein. Die Hallenfotos aus U48 (Runde 4) dabei nicht entfernen. |
| 19 | Blog im Footer | **umsetzen** | Ein Link. |
| 20 | Kleinigkeiten (Link `?ding=1`, Sprachreihenfolge, 8 px Querscroll, 12/13 Spiele) | **umsetzen** | Echte Fehler. 12/13: prüfen, ob ein Spielbericht fehlt, oder ob der Satz «aus 12 Spielberichten» nur stimmt. |
| 21 | Einschübe kürzen; FR/EN gegenlesen | **teilweise** | Doppelte Erklärungen pro Seite kürzen; FR «2 contre 3» vs. DE «3 gegen 2» prüfen und angleichen. Muttersprachliches Gegenlesen bleibt bei Lukas. |
| 22 | Europa im Fokus (Lukas, 19.11.): Schritt 1 von `docs/plans/europa.md` fertig, Preise in EUR und CHF, ehrliche Teamsuche ohne Treffer | **umsetzen** | Preise EUR 39 / CHF 39 (EU3), umschaltbar auf «Preise», Vorgabe aus der Browsersprache. Keine `de-DE`-Variante jetzt (EU2). |
| 23 | Messen ohne Cookies: jeder Link in die App trägt `?src=<Ort>` | **umsetzen** | Das Versprechen «keine Cookies» bleibt; die App speichert `src` bei der Anmeldung (anderer Helfer). |
| 24 | Neue Seite «Für Vereine» für den Vorstand | **umsetzen** | Nur echte Produktfakten aus `packages/plans`, keine Stimmen. Verlinkt von «Preise» und im Footer. |
| 25 | «AGB» statt «Nutzungsbedingungen» | **umsetzen (Website), App: Helfer** | Die Website sagt durchgehend «AGB»; die App sagt «Nutzungsbedingungen» (`apps/web/messages/*.json`, `entry.terms` und weitere). Für den App-Helfer. |
| 26 | Sichtbarer Tastatur-Fokus (WCAG 2.4.7) | **umsetzen** | Mit Playwright per Tab geprüft. |

## Für Lukas (nicht von der Sitzung lösbar)
- Über uns mit Namen und Fotos, Kontakt mit Adresse (nach der Firmengründung).
- Prüfliste für die Rechtsprüfung (aus dem Review): Platzhalter in Impressum und Datenschutz; KI-Anbieter
  für «Frag deine Spiele», falls der Key eingeschaltet wird (dann gilt «Daten in der Schweiz und der
  EU» nicht mehr uneingeschränkt); Gegnerteam und Anwesende; Nein zur Videoanalyse; Altersgrenze 16
  in EU-Ländern; Vertragspartner Verein bei Anmeldung durch eine Trainerin; AGB nennen Spieler-Profile
  und Kartenzahlung; Nutzung der handball.ch-Daten; Mitbewerber-Vergleich (UWG); Bildrechte (Foto mit
  Nr. 14, Hero-Hintergrund); absolute Aussagen («Original nach 90 Tagen gelöscht», «sieben Tage
  vorher benachrichtigt»).
- Ein iPhone- und ein Android-Test von Hand.

## Umsetzung
Ein Helfer setzt die Punkte «umsetzen» nach A22 um (die Wurfort-Sätze hat A22 schon angepasst).
Stand pro Punkt wird hier nachgetragen.

## Stand Umsetzung (19.11.)
| Nr. | Stand | Was gemacht ist, oder warum nicht |
|---|---|---|
| 1, 2 | nein (Lukas) | Nicht angefasst: Aufwand und Analysedauer bleiben die Vision. |
| 3 | erledigt | Ein Beispieluniversum: Die Saison vor dem Demo-Spiel (So funktioniert es: Rotdorn 6, Wirbelstern 9, Nachtwind 11, zusammen 26 von 77) und die Spiele danach (Start und Demo) haben jetzt verschiedene Gegner: SG Blitzfang 4, HSG Funkenflug 4, TV Silberpfeil 3 (`apps/site/src/lib/week.ts`, ein Test hält beide zusammen). Das Beispiel auf der Teamseite der App ist jetzt das Demo-Spiel der Website, 11 von 29 statt 6 von 22 (`apps/web/public/example/graphics.json` aus `demoGoals`, mit Test). |
| 4 | erledigt | Menü «Hilfe» (fr «Aide», en «Help»), en «Pricing». Die Funktion heisst überall «Frag deine Spiele»; die Szenensuche ist «Frag deine Spiele: Szenen suchen» (Bild auf So funktioniert es, Anleitung), das Mockup auf der Startseite heisst «Frag deine Spiele». Die App selbst sagt noch «Fragen»/«Suchen»/«Szenen suchen»: für den App-Helfer. |
| 5 | Lukas | offen |
| 6 | erledigt (Playwright), Gerätetest bei Lukas | Alle 155 Seiten (de, fr, en) bei 375 und 768 px: kein horizontales Scrollen. Angeschaut: Preistabelle (Handy: eine Zeile pro Merkmal über drei Spalten; 768 px: Tabelle lesbar), «Für Vereine», So funktioniert es (Schritt 0 stapelt jetzt auf dem Handy), Startseite (Loch nach «Verloren» zu). Saisonkarte im App-Rundgang am Handy eng, aber lesbar; nicht geändert, weil das Layout auf dem Desktop abgenommen ist. |
| 7 | Lukas und Fachperson | offen; Prüfliste oben. |
| 8 | erledigt | Schritt 0 «Vorher: das Team fragen» auf So funktioniert es, mit Links zu Daten und zur Anleitung. Daten-Seite: was ein Nein im Code bewirkt (keine eigene Szenenliste, «Einwilligung fehlt» im Kader, Szenen fehlen in Highlights, öffentliches Teilen gesperrt; niemand wird unkenntlich gemacht), Namen aus dem offiziellen Kader nur fürs Trainerteam bis zur Einwilligung (`roster._without_official_only`), und ein Satz zum Gegnerteam ohne rechtliche Wertung. |
| 9 | später | offen |
| 10 | erledigt | Auslösen bei etwa 15 % sichtbar (oder 15 % des Bildschirms bei hohen Blöcken), 0.35 s, Staffel 50 ms; bei `prefers-reduced-motion` nichts. |
| 11 | erledigt | «Eine Beobachtung, kein Beweis …» steht auf der Startseite unter «Aussen rechts ist zu». |
| 12 | erledigt | «Was heisst das fürs Training?» hat «Sonntag, 10 Uhr»; die Einsicht in der Demo auch. |
| 13 | erledigt (teilweise) | «Gratis starten, dann CHF/EUR 39 pro Team», darunter «Im Verein … also ab 19.90 pro Team»; Zeile zum Gratis-Plan nach dem Test aus `packages/plans` und `billing.py` (2 Spiele pro Saison, die aus dem Test zählen mit; 10 GB; ohne Analyse). Keine Karte mehr in «Wie bezahle ich?». Die AGB nennen die Karte noch (Prüfliste). «Noch nicht endgültig» steht nicht auf der Website: Lukas hat am 17.11. entschieden, dass die Website ohne «noch nicht» auskommt (BEFUNDE-2 W32, `PRICES_FINAL`); die Preise bleiben in OPEN_QUESTIONS Punkt 7 offen. |
| 14 | erledigt | Unter der Teamsuche: was man bei Schweizer Teams sofort sieht, und Spielberichte per Link von DHB, nuLiga, HLA. |
| 15 | später | offen |
| 16 | erledigt | Teamchat-Bild auf «Daten» und «Über uns» klein (16rem, ohne Pfeile); gross nur auf Start und Demo. So funktioniert es behält es als Teil des Rundgangs. |
| 17 | geprüft | Offline gegen `ml/data/official` (153 Spiele), die handball.ch-Fixtures und alle Teamlisten im Repo: kein Treffer für Tannengrün, Nachtwind, Wirbelstern, Rotdorn, Silberpfeil, Blitzfang, Funkenflug. Online nicht geprüft. Bildrechte und UWG bleiben auf der Prüfliste. |
| 18 | erledigt | Weniger Abstand und ein niedrigerer Fotostreifen; das Foto aus U48 bleibt. |
| 19 | erledigt | Blog im Footer ab dem ersten eigenen Beitrag. |
| 20 | erledigt | Link mit `?ding=1`; Sprachen DE · EN · FR wie in der App; 8 px Querscroll: das Einstiegslayout der App hatte ab 768 px 24 px Rand, `.bleed-x` zieht 32 px heraus, jetzt `md:px-8`. 12 vs. 13: kein fehlender Bericht, die API holt höchstens die letzten 12 Berichte (`SCORER_GAMES`); der Satz sagt jetzt «aus den letzten 12 Spielberichten». |
| 21 | erledigt (teilweise) | Übung heisst in allen Sprachen 3 gegen 2 (Website, App-Bibliothek, `packages/tactics`). Doppelte Erklärungen gekürzt (So funktioniert es Schritt 4, «Für diesen Abend bauen wir» nur noch einmal auf Über uns). Gegenlesen durch Muttersprachler bleibt bei Lukas. |
| 22 | erledigt | Preise in EUR und CHF, Umschalter auf «Preise» und «Für Vereine» (`?cur=`, Vorgabe CHF bei Schweizer Browsersprache, sonst EUR; nichts gespeichert), JSON-LD mit beiden Währungen. Teamsuche ohne Treffer (App): sagt, dass Spielplan und Resultate heute nur für Schweizer Teams kommen und andere ihr Team von Hand anlegen und Berichte per Link holen (DHB, nuLiga, HLA). Schritt 1 von europa.md war sonst schon umgesetzt. |
| 23 | erledigt | `?src=` an allen Links und Formularen in die App: header, menu, login, team-search, team-search-end, home-price, pricing, pricing-table, how, demo, about, clubs, guide (Liste in `apps/site/README.md`, Test). |
| 24 | erledigt | `/vereine/` in de, fr, en: was der Verein bekommt, Team und Verein nebeneinander aus `packages/plans`, Daten und Einwilligung, Kontakt. Im Footer und von «Preise» verlinkt, in Sitemap und llms.txt. |
| 25 | erledigt (Website) | Website sagt «AGB»; «Free-Plan» in den AGB heisst jetzt «Gratis-Plan». Für den App-Helfer: die App sagt «Nutzungsbedingungen». |
| 26 | erledigt | Per Tab mit Playwright über 7 Seiten bei 1280 und 375 px (1647 Fokusse): überall ein Ring. Einzige Lücke war Tinte auf Tinte (Knopf «Nochmals abspielen» in der Demo); jetzt weisser Ring mit Tintenrand auf jedem dunklen Grund. |
