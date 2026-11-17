# QA-Nacht: Ende-zu-Ende-Prüfung nach dem Zusammenführen (17.11.)

Stand: Branch `claude/compassionate-pascal-n3gl03` mit allen sechs Strömen der Nacht, lokal
(eigene API und Web mit dem Code dieser Prüfung, dieselbe Datenbank). Mails: Konsole, Links aus
dem API-Log. Video: synthetisch (ffmpeg-Testbild, synthetischer Handball-Clip der E2E-Tests),
keine echten Personen.

## Was geprüft wurde

- **Rollen:** Trainer (Demo-Konto), neu registrierter Trainer (Verein von Hand, die Suche bei
  handball.ch ebenfalls), Spieler und Eltern, beide über das Einladen im Team eingeladen und
  über den Link registriert; Teamfunktionen an und wieder aus.
- **Seiten bei 390 px und 1280 px**, mit axe (WCAG 2 A/AA), Konsole, HTTP-Fehlern, waagrechtem
  Überlauf und Textprüfung (ß, lange Striche, Englisch, rohe Schlüssel, Mail-Versprechen):
  62 Seitenaufrufe als Trainer (Spiele, Upload, Spiel mit Spiel/Video/Zahlen, Prüfen, Szenen,
  Sammlungen, Sammlung, Spielzüge, Editor, Training, Übungen, Saison, Team, Kader-Vorschläge,
  Verein, Abo, Ich, Sicherheit, Daten, U17), 42 als Spieler, 14 als Eltern.
- **Abläufe:** Einstieg, Anmelden, Registrieren, Passwort vergessen bis zum neuen Passwort,
  Onboarding, erstes Spiel anlegen, Upload mit Fortschritt (Streifen oben, Spiel während der
  Analyse), Spiel nach der Analyse, Prüfen, Teilen (Dialog, Spielkarte, öffentliche Seite mit
  Link-Vorschau), Sammlung teilen, Gegner beobachten, Datei anhängen, Teamleben-Dialog, Glocke,
  Kontomenü.
- **E2E-Suite** (`pnpm --filter @handball/web test:e2e`) gegen den eigenen Stand.

## Behoben

| Befund | Schwere | Commit |
|---|---|---|
| Eltern landeten auf «Du bist noch in keinem Team» mit den ersten Schritten des Trainers: die Teamliste der API kannte Eltern nicht. Jetzt steht ihr Team mit der Rolle «parent» in der Liste (das Team selbst bleibt zu), die App öffnet Teamleben | 🔴 | 219a35d5 |
| Spieler: 403 auf `/teams/{id}/members` bei jedem Besuch der Teamseite; die Trainerbank wird nur noch für Trainer und Co-Trainer geladen | 🟡 | 219a35d5 |
| Hydrations-Warnung auf jeder Spielseite (useId in den Highlights): Highlights laden nur im Browser (sie stehen im zugeklappten «Mehr zum Spiel») | 🟡 | 219a35d5 |
| Eltern: «Jetzt einschätzen» (nur Spieler schätzen sich ein), Einwilligungstexte mit «dich» statt «dein Kind», Termine und Einwilligungen bei 390 px ein Wort pro Zeile | 🟡 | 219a35d5 |
| Szenen-Suche: abgelehnte Anfrage führte zu «Query data cannot be undefined» | ⚪ | 219a35d5 |
| «Etwa 40 Minuten danach» in den nächsten Schritten (ein ganzes Spiel dauert auf CPU Stunden, K13) | 🟡 | f3a3ffab |
| Fortschritt sagte während des Browser-Uploads «Du kannst die Seite schliessen» (das bricht den Upload ab) | 🟡 | f3a3ffab |
| Fortschrittsstreifen schnitt am Handy die Endzeit ab; jetzt zwei Zeilen | ⚪ | f3a3ffab |
| Leere Saison: zwei Werkzeuge statt eines nächsten Schritts; jetzt was dort wächst und «Video hochladen». Mit Videos, aber ohne Zahlen: «Noch keine Zahlen für die Saison» und «Zu den Spielen» statt «Noch kein Spiel gespielt» | 🟡 | f3a3ffab, 4155e16d |
| Spielkopf ohne Resultat mit grosser leerer Fläche; «Highlights teilen» ohne ein Tor | ⚪ | f3a3ffab |
| Teamsuche im Onboarding zeigte während der Abfrage bei handball.ch nichts | ⚪ | f3a3ffab |
| Textlinks sahen aus wie Text (Akzentfarbe ist Tinte): Anmelden, Registrieren, Hilfe und 20 Stellen in der App unterstrichen | 🟡 (Barrierefreiheit) | f3a3ffab |
| «Ein Bereich aus der früheren Version der App» auf Spielzüge und Gegner, beides seit heute Nacht neu (K23, K3) | 🟡 | f3a3ffab |
| Trainingstipps nur über Teamleben erreichbar, das standardmässig aus ist: Link «Trainingstipps dazu» unter «Was sich wiederholt»; Hinweis und Teamleben-Dialog sprechen von Tipps statt vom leeren Planer | 🟡 | f3a3ffab, 33becdf9 |
| Eltern ohne Teamfunktionen sahen Termine mit Zusagen auf der Übersicht | ⚪ | f3a3ffab |
| «über rechts aussen» in Szenentiteln, Demo und Website-Demo, sonst überall «aussen rechts» | ⚪ | f3a3ffab, 33becdf9 |
| «Teilen» vor dem Spiel (noch kein Bericht) | ⚪ | 33becdf9 |
| Rechnung «per E-Mail verschickt» auch ohne Mailversand (L2) | 🟡 | 33becdf9 |
| «Eigene Übungen von Handball Intelligence» neben «Eigene Übungen» des Vereins | ⚪ | 33becdf9 |

## E2E-Suite

Angepasst, wo sich das Verhalten heute Nacht gewollt geändert hat (40d01bc6): leere Szenen und
Sammlungen vor dem ersten Video (K8), «Einheit selbst planen» und leere Glocke (K21, K8),
Onboarding endet auf Spiele und «Diesem Team beitreten» (K17), «Als Spieler beitreten» (K18).
Stabiler: Video erst wählen, wenn React zuhört (d3edb3ac, ein zu früh gewählter File-Input
wurde nie hochgeladen), auf Listen und Speichern warten, axe von oben (der klebende Kopf
verdeckt beim Scrollen die Mail-Zeile). Letzter voller Lauf (beide Projekte, 3 Worker):
48 bestanden, 44 übersprungen (laufen nur in einem Projekt), 9 rot: 7 davon brauchen Mailpit
(`account` Mail-Link und Passwort, `onboarding` Einladen, `entry` ohne Passwort und Team in der
App, `family`, `player` ab dem Einladungslink; kein Mailpit im lokalen Stack, bis dorthin
grün), `matchday-offline` und `m11` unter Last; einzeln danach grün (`m11` mit derselben
Hydrations-Wartezeit für den Datei-Input, e35b081b).

API-Tests: 430 bestanden. Web: Typecheck, Lint, 285 Unit-Tests grün. Website: Build und Tests grün.

## Zweiter Durchgang (17.11., morgens)

Alle offenen Punkte der Nacht behoben. Geprüft mit eigener API ohne Mailversand
(`HB_MAIL_ENABLED=false`) und eigenem Web, bei 390 px und 1280 px.

| Befund | Schwere | Was jetzt gilt | Commit |
|---|---|---|---|
| Datenbank-Commit nach der Antwort | 🟡 | `DbDep` nutzt `Depends(get_session, scope="function")`: FastAPI schreibt fest, wenn der Endpunkt und das Serialisieren der Antwort fertig sind, vor dem ersten Byte. Mandanten-Kontext bleibt transaktionslokal. Test prüft die Reihenfolge Endpunkt, Commit, Antwort; ganze API-Suite grün | ca945d6b |
| Video vor der Hydration gewählt, geht still verloren | 🟡 | Upload, Dateien zum Spiel, Kader-CSV und alle Dateifelder lesen beim Start, was der Input schon hält, und machen damit weiter (einmal, auch unter StrictMode) | 24535eff |
| Trainingstipps nur unter Teamleben | 🟡 | Entscheid: eigener Platz unter Saison, `…/season/tips` («Saison › Trainingstipps»), für Trainer und Co-Trainer, mit oder ohne Teamleben. Erreichbar über den Knopf im Saison-Kopf, «Trainingstipps dazu» unter «Was sich wiederholt» und die Suche. Im Trainingsplan (Teamleben) bleiben sie oben. Eine geplante Einheit verlinkt dorthin; «Als Aufgabe an die Spieler» nur mit Teamleben. Navigation unverändert: vier Ziele, Saison ohne Tabs | cd892a0a |
| Eltern-Hinweis nennt Termine, wenn sie aus sind | ⚪ | Hinweis hängt an der Einstellung: ohne Teamfunktionen «neue Szenen aus den Spielen» | 38fb4fff |
| «Spieler/innen» neben «Spieler» | ⚪ | Ein Wort pro Rolle (Trainer, Co-Trainer, Spieler, Eltern): Zähler, Beschriftungen, Hinweise, Positionen («Torhüter», «Feldspieler»), PDF-Spielbericht; fr «joueur» in Rollen und Zählern. Der Hilfeartikel «Rollen und Rechte» (Website, de/fr/en) listete noch elf Rollen, jetzt die vier | 955d685c |
| Sammlung am Handy: vier Textlinks pro Eintrag | ⚪ | Zwei Pfeile und «…» mit «Notiz danach» und «Entfernen» (abgesetzt, «Rückgängig» bleibt). 44-px-Ziele, mit Tastatur bedienbar, Namen mit der Nummer des Eintrags für Screenreader | 3df1fb5a |
| Anpfiff-Feld mit der aktuellen Minute | ⚪ | Entscheid: ein von Hand angelegtes Spiel ist meist das gerade gespielte (künftige kommen von handball.ch). Vorschlag liegt deshalb in der Vergangenheit, wo das Spiel auf den Upload öffnet: tagsüber die letzte volle Stunde, nachts und vor neun Uhr gestern 18:00. Pflichtfeld wie bisher | b0c65c08 |
| «Spieltag starten» Tage vorher prominent | ⚪ | Vorn nur am Spieltag, ab drei Stunden vor bis drei Stunden nach dem Anpfiff; vorher in «Mehr» und ruhig unter «Vor dem Spiel» | 3edd8749, 6bb5d04f |
| «Text für den Chat» leer bis zur Vorschau | ⚪ | Steht sofort aus dem, was die Seite weiss (Spiel: Teams, Gegner, Resultat; Szene, Spielzug, Liste, Szenen eines Spielers: Titel). Die Vorschau verfeinert ihn, solange nichts von Hand geändert wurde | 17d5a264 |
| Durchgang ohne Mailversand | ⚪ | Einstieg «Speichern» mit Passwort, Anmelden ohne Link-Angebot, Passwort vergessen über den Support, Spieler einladen mit Link zum Kopieren, Abo, Ich, Sicherheit, Verein: ohne Mail-Versprechen. Gefunden und behoben: Aufgaben «Zusätzlich per E-Mail» (nur noch mit Mailversand, auch in der API), Feedback «Wir melden uns per E-Mail», Verbandseinladung «gesendet» ohne Mail und ohne anderen Weg (API gibt jetzt den Link zurück, ohne Mail zum Kopieren) | f3148a9b |
| Toter Code: Startseiten von Trainer und Spieler («N Termine beantworten») | ⚪ | Die Vereinswurzel zeigt nur noch die Übersicht der Eltern und den Fall ohne Team; die unerreichbaren Startseiten von Trainer und Spieler sind entfernt, ein veralteter Teamwechsel leitet zum Start weiter. Spieler finden Termine, Aufgaben und Szenen in den Tabs von Teamleben | 38fb4fff |

Tests: API 432 bestanden. Web: Typecheck, Lint, 293 Unit-Tests grün. Website: Build und 34 Tests
grün. E2E gegen den eigenen Stand: `collection` und `official` grün; `live` bis zum Spieltag
grün, danach rot beim Neuladen offline (im Dev-Server gibt es keinen Service Worker; im
Produktions-Build prüfen).

## Offen

| Befund | Schwere |
|---|---|
| Nur im Dev-Server gesehen, nicht reproduzierbar: einmal 500 auf `/s/…` (next-intl-Kontext), Turbopack-Modulfehler nach Dateiänderungen | ⚪ |
| Szenentitel in Sammlungen heissen noch «Gegentor über aussen rechts» (Zonen-Text `zoneFrom`), sonst überall «aussen rechts» | ⚪ |

Bilder (nur Demo- und synthetische Inhalte): `qa/eltern-uebersicht-390.png`,
`qa/saison-ohne-zahlen-390.png`.
