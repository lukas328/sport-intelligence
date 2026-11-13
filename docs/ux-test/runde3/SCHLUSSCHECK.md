# Schlusscheck nach der Abnahme

Stand: 13. November 2026. App `claude/trikot-ui` (Commit 45afd14), Website wie in der Abnahme
(7907501). Frische Datenbank, `make seed`, Produktions-Build, Playwright mit Chromium (Desktop 1280,
Handy 390, grosse Schrift als 300 CSS-Pixel bei Faktor 1,3). Nur Nachprüfen, keine neue Suche.

## Urteil

Alle zehn Befunde der Abnahme und alle 14 Zeilen, die dort «teilweise» waren, sind behoben oder
bewusst entschieden; neu kaputt gegangen ist nichts, ausser dass bei grosser Schrift die Lupe aus der
Handy-Kopfzeile weicht und die Mail bei genau einer offenen Frage das Verb in der Mehrzahl lässt
(beides P3). Ich würde Hans die App jetzt ohne Vorbehalt für die Oberfläche geben; offen bleibt nur,
was in drei Runden nie prüfbar war (echtes Hallenvideo, echte Geräte, echtes Postfach).

## Tabelle

| # | Befund | Abnahme | Schlusscheck | Beobachtung |
|---|---|---|---|---|
| A01 | Kopfzeile bei grosser Schrift «S / G.» | P2 | **behoben** | 300 px: «SG Wädenswil/ Horgen» zweizeilig bzw. «HC Rheintal», Glocke, «+», Konto; 390 px: Wappen, Name, Glocke, Lupe, «+», Konto. Bei 300 px fehlt die Lupe (Suchen nur über den Reiter Szenen, P3). `shots/s01-kopf-300-390.jpg` |
| A02 | Video ohne Tore: zwei Zahlen, vier Sätze | P2 | **behoben** | Mail «Sie hat noch keine Tore gefunden. 2 Fragen an dich helfen ihr weiter», Start ein Satz «Die Analyse hat noch keine Tore gefunden. 2 Fragen helfen ihr weiter.» mit «Fragen beantworten», Liste «Analyse fertig, 2 Fragen offen», Prüfen «2 Fragen · Frage 1 von 2». Kein «Fürs Team», kein «Spielbericht hinzufügen» bei vorhandenem Bericht. Mehrzahl in der App de/fr/en über ICU-Plural richtig. In der Mail bleibt bei genau einer Frage das Verb in der Mehrzahl («1 Frage an dich helfen», «1 question for you help», «1 question pour toi l'aident»; Vorlage `mail_templates.py`, im Code gesehen, nicht im Postfach), P3. `shots/s02-start-ohne-tore.jpg` |
| A03 | Spieltag: Uhrzeit neben Spieluhr | P3 | **behoben** | Eintrag «00:03 · 08:53 · Tor wir»: Spielzeit vorn, Uhrzeit klein dahinter. `shots/s04-spieltag-zeit.jpg` |
| A04 | «Hauptrunde - M1-01» in der Saison | P3 | **behoben** | «Saison 2026/27 · Männer 1. Liga · nach neun Spielen · Rang 10, 4 Punkte» |
| A05 | Hinweis «Mehr zum Spiel», Highlights vor dem Spiel | P3 | **behoben** | Hinweis «Spielverlauf, Highlights, Marken vom Spieltag»; künftiges Spiel ohne «Mehr zum Spiel» und ohne «Highlights teilen» |
| A06 | Prüfen nennt den Verein | P3 | **behoben** (plausibel) | «Prüfen · HC Rheintal gegen KJS Schaffhausen»; bei diesem Verein sind Verein und Team gleich benannt, den Unterschied konnte ich nicht noch einmal zeigen |
| A07 | Altes Produkt hinter Umwegen | P3 | **entschieden** | Spielzüge und «Zum Zeigen» sagen oben «Ein Bereich aus der früheren Version der App. Alles bleibt hier erreichbar, Neues kommt unter Szenen und Spiele.»; Spielzüge ohne zweite Tab-Ebene. Entscheid in OPEN_QUESTIONS Q-OLD-AREAS. `shots/s06-spielzuege-hinweis.jpg` |
| A08 | Szenenfolge mit Videozeit | P3 | **behoben** | Liste «7:46 … Thalwil», Folge «TSV Thalwil-Gattikon · 7:46» |
| A09 | Platzhalter-Block beim Laden | P3 | **behoben** | erster Text nach 0,15 s ohne «-:-»-Block (kalt, HC Rheintal) |
| A10 | Negativer Balken ohne Zahl | P3 | **behoben** | «−1 Pfader, −6 Andelf., +2 Flawil, −9 Unters. …» alle mit Zahl |
| N05 | Mail ohne drei Dinge | teilweise | **behoben** | wie A02 |
| N11 | Grosse Schrift: Namen | teilweise | **behoben** | wie A01 |
| N18 / B53 | 404 mit HTTP 200 | teilweise | **behoben** | unbekannte Spiel-, Team- und Sammlungs-ID sowie unbekannte Adresse: alle HTTP 404 |
| N22 | Ungültiger Link ohne Weg zur Teamwahl | teilweise | **behoben** | «Der Link ist ungültig oder abgelaufen.» mit «Zurück zur Teamwahl» und «Anmelden». Echter Ablauf nach 24 h weiter nicht nachstellbar. `shots/s03-link-ungueltig.jpg` |
| N25 / B47 / H10 | «Hauptrunde - M1-01» | teilweise | **behoben** | wie A04 |
| B28 | Leerer Verein | teilweise | **behoben** | Szenen: «Szenen gibt es nach dem ersten Video.» mit «Video hochladen». `shots/s05-leer-szenen.jpg` |
| B44 | Ziele unter 44 px | teilweise | **unverändert, angekündigt** | Feldecken und Tabellenzahlen 44 px; Namen in Teamlisten wie bisher |
| B46 | Keil auf Anmelden | teilweise | **entschieden** | Gestaltung des Seitenkopfs, bleibt |
| H06 / Z4 | Meldung «fertig» | teilweise | **behoben** | wie A02 |
| H14 | Saison-Verlauf | teilweise | **behoben** | wie A10 |
| – | Erstes Video ohne Tore (Punkt der Bau-Session) | teilweise | **behoben** | wie A02 |
| – | Grosse Schrift 300 px | teilweise | **behoben** | wie A01 |
| – | Abgelaufener Link | teilweise | **behoben** | wie N22 |

**Neu kaputt?** Start, Tab Spiel, Spiel nur mit Spielbericht: ohne Fehler im Browser, Titel wie
erwartet. Szenen ohne Video (leerer Verein): richtiger Satz. Einstieg: kalt erster Text nach 0,15 s,
Rang nach 1,2 bis 1,8 s, warm nach 0,15 s; Website › Einstieg › Mail › Spiele › Video › Mail ohne
Unterbruch. Gefunden nur die zwei P3 oben (Lupe bei 300 px, Verb in der Mail bei einer Frage). Der
Upload vom Start aus öffnet jetzt zuerst den Spiel-Dialog (das letzte Spiel oben); das ist ein Tipp
mehr, aber klar.
