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
