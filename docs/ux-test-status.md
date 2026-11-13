# UX test, round 1: status per finding

Source: `docs/ux-test/runde1/BEFUNDE.md` on branch `claude/ux-test` (read only, not merged
here). One line per finding: **behoben** (commit), **teilweise** (what is done, what is open),
**nicht behoben** (reason) or **kein Fehler** (reason). Commits on `claude/trikot-ui`.

Comparison images of the rebuilt screens: `docs/screens/anlauf/vergleich/ux1-*.jpg`.

| # | Befund | Status |
|---|---|---|
| B01 | Szenen zu Punkt 1 nicht erreichbar | behoben (07790d7): «n Szenen» öffnet genau die Szenen dieses Dings (`?thing=n`), Liste rechts, laufende gelb, «Nächste Szene», «Alle n abspielen»; die Zeitleisten-Liste heisst «Minute x bis y». Test `lib/thing-sequence.test.ts`. |
| B02 | «Suchen» endet beim Assistenten | behoben (07790d7): «Suchen» öffnet die Szenen-Suche; freie Eingaben in der Schnellsuche landen dort; `/assistant?q=` leitet mit der Frage um; Sätze werden Chips. Tests `lib/scene-words.test.ts`, e2e `data.spec`. |
| B03 | Spieltag: Einträge nach Neu laden weg | behoben (07790d7): Spieltag und Detail-Erfassung laden Marken und Ereignisse beim Öffnen vom Server, Resultat und Liste bleiben nach Neu laden; e2e `live.spec`, `m11.spec`. Die Doppelten der Testerin liegen nur in ihrer lokalen Datenbank; `scripts/seed.py` erzeugt keine Live-Ereignisse, es gibt dort nichts zu bereinigen. |
| B04 | «Am Bildschirm zeigen» tut nichts | behoben (a3fab6c): eigene Vollbild-Ansicht `collections/[id]/present` (Szenen nacheinander, Notizen als Tafel, Tasten, «Vollbild», «Schliessen» in e779fe1). e2e `collection.spec`. |
| B05 | Sammlung: keine Notiz, nichts entfernen, nichts umbenennen | behoben (a3fab6c): «Notiz dazu», «Nach oben/unten», «Entfernen», Titel antippen; sofort und der Reihe nach gespeichert. e2e `collection.spec`. |
| B06 | Sprache lässt sich nicht wechseln | behoben (a3fab6c): Sprachen ausgeschrieben im Konto-Menü, auf Anmeldung und im Einstieg; ohne Wahl gilt die Browsersprache. e2e `onboarding.spec` «language». |
| B07 | Nur Spielbericht: erfundene Läufe, leerer Verlauf | behoben (9b12b32): Tore ohne Zeit haben keine Reihenfolge, also keine Läufe, keinen Verlauf, keine Torflaute (`timeline.timed`); Quoten nur mit Fehlwürfen in derselben Richtung; nie erfasste Werte «-»; «Spielbericht» statt «Papierbericht». Zustand «Kein Video» in Tab Spiel (43d69c9). Tests metrics, e2e `analysis.spec`. |
| B08 | Tab Spiel: unter den drei Dingen das alte Produkt | behoben (43d69c9): Aktionen (Fürs Team, Highlights teilen, Als Bild für den Chat), «Punkt 1, geöffnet» auf der Taktikkamera, Telegramm, daneben Gegentore/Eigene Tore und drei Zahlen mit Quelle; alles Alte hinter «Mehr zum Spiel»; xG und Ballbesitz gestrichen. «Dazu üben» fehlt (es gibt keine Zuordnung Ding zu Übung in den Daten). Vergleich `ux1-spiel*.jpg`. |
| B09 | «Spiel öffnen» öffnet Video; Tabs nicht in der Adresse | behoben (07790d7): Standard Tab Spiel, `?tab=` in der Adresse, Zurück wechselt den Tab. |
| B10 | Nach dem Upload: Einrichtungs-Assistent im Tab Video | nicht behoben: die vier Einrichtungsschritte (Spielfeld, Anwurf, Tore, Spieler) sind heute der einzige Weg zu Anwurf und Spielerzuordnung; Prüfen fragt nur Feld und Tore. Sie wegzunehmen würde Funktionen löschen; erst wenn Prüfen auch Anwurf und Personen fragt. Die Werkbank mit Unter-Tabs (Ereignisse, Abwehrsysteme, Kommentare, Feedback) erscheint ohne Bühne weiterhin direkt; sie hinter «Mehr» zu legen braucht einen eigenen Player ausserhalb der Werkbank. «Wer ist das?» als Frage fehlt, weil die Analyse keine Personen-Boxen liefert. |
| B11 | «Analyse läuft» spricht Technik | behoben (e779fe1): Titel «Die Analyse läuft.», drei Schritte in Trainerwörtern (Video gelesen, Spieler werden verfolgt, Drei Dinge werden gesucht), Minuten bis fertig sobald messbar, die technischen Schritte hinter «Einzelschritte». |
| B12 | Taktikkamera zeigt Positionen ohne bestätigtes Feld | behoben (9b12b32): bei offener Feldfrage keine Positionen, auch im Demo; «Stimmt das Feld?», Grund, «Feld prüfen»; nach «Ja, stimmt» erscheinen sie. Test `test_graphics.py`. |
| B13 | Prüfen zeigt das erkannte Feld nicht | nicht behoben: braucht die vier erkannten Ecken der Kalibrierung als Viereck über dem Bild; die Kalibrierung liefert die Homographie, die Rückprojektion der Ecken ist noch nicht gebaut. |
| B14 | «Ecken verschieben» verlässt Prüfen | nicht behoben: die Ecken im Prüfen-Screen selbst verschieben braucht dieselbe Rückprojektion wie B13; der Weg führt weiter zur Kalibrierung im Spiel. |
| B15 | Geteilte Seite nicht nach Zielbild | teilweise (a3fab6c): ohne Produktkopf und «Anmelden», «geteilt von», Szenentitel. Video und Taktik pro Szene und Minifelder fehlen noch. |
| B16 | «Fürs Team» enthält nicht die drei Dinge | behoben (a3fab6c): Entwurf aus den drei Dingen (je Notiz, dann genau seine Szenen, keine Doppelten); Seed gleich. |
| B17 | Teilen: Extra-Dialog, Link nur einmal sichtbar | behoben (a3fab6c): «Link teilen» erstellt und kopiert in einem Schritt, Link bleibt sichtbar und abrufbar (verschlüsselt gespeichert, Migration 0043), «Link sperren». e2e `collection.spec`. |
| B18 | «Suchen» öffnet die Schnellsuche | behoben (07790d7): Knopf «Suchen» öffnet die Szenen-Suche mit Fokus. |
| B19 | Suchfeld versteht keine Sätze; Rohwerte | behoben (07790d7): Sätze werden Chips (de, fr, en); Kacheln mit Wörtern statt Rohwerten. |
| B20 | «letzte 3 Spiele» meint mit Video | behoben (07790d7): Chip heisst «letzte 3 mit Video». |
| B21 | «Alle 24 abspielen», «Als Tabelle» | behoben (e779fe1): «Alle n abspielen» spielt alle Szenen der Antwort über die Spiele hinweg als Folge im Vollbild; «Als Tabelle» zeigt dieselbe Antwort als Zeilen im selben Screen (`?view=table`); die alte Pivot-Tabelle bleibt unter `matrix?pivot=1`. |
| B22 | Spieltag ist die alte Detail-Erfassung | behoben (07790d7): grosse Tasten nach Zielbild, «Bisher», «Pro Spielerin erfassen» führt zur Detail-Erfassung. |
| B23 | Tab Zahlen ist die alte Statistikseite | teilweise (43d69c9): Feld- und Tor-Tabelle, Gegentore nach Position, «Ziel im Tor» als schlichtes Raster, Phasen mit Quelle, Würfe/Quote nur mit erfassten Fehlwürfen, Rest hinter «Alle Zahlen». Offen: Zahlen als Links zu ihren Szenen, Spalte «Bestätigt». Vergleich `ux1-zahlen*.jpg`. |
| B24 | «Übernehmen» wartet ohne Wort; Neu laden überspringt Schritt 2 | behoben (e779fe1): nur der gewählte Knopf dreht, Satz «Wir holen Spiele, Kader und Tabelle …»; Schritt 2 bleibt nach Neu laden, bis bestätigt oder «Das ist nicht mein Team». |
| B25 | Registrierung: Fehler auf Englisch, Bedingungen nicht verlinkt | behoben (e779fe1): Prüfung im Formular in der eigenen Sprache an jedem Feld, Kästchen markiert; «Nutzungsbedingungen» und «Datenschutzerklärung» verlinkt (handball-ai.ch/agb, /datenschutz). |
| B26 | Erster Screen ohne Aufgabe | behoben (e779fe1): beim letzten Spiel ohne Video Hauptknopf «Video hochladen», daneben «Demo-Spiel ansehen»; Zwei-Faktor als Punkt am Konto (B48). |
| B27 | Verein von Hand: Vierschritt-Assistent mit Einladungen | nicht behoben: der Weg von Hand braucht einen Umbau auf zwei Schritte (Name und Trikots, Kader optional); in dieser Runde nicht geschafft. |
| B28 | Leerer Verein: Formular-Karte, geratene Gegnerfarbe, falscher Leer-Satz | teilweise (e779fe1): Szenen sagen «Szenen gibt es nach dem ersten Video.»; die Gegnerfarbe wird nur gespeichert, wenn jemand sie wählt (war schon so), die Vorschau zeigt aber noch Rot; das Formular als Start ist geblieben. |
| B29 | Falsche oder kaputte Datei: keine Erklärung | teilweise (e779fe1): «Das Video liess sich nicht lesen.», was bleibt, «Andere Datei wählen». Glocke bei Fehlern und mit Spielnamen: nicht behoben (Mitteilungen im Backend). |
| B30 | Team wechseln auf einer Spielseite | behoben (e779fe1): auf Seiten eines Spiels, einer Sammlung oder eines Gegners führt der Wechsel zu den Spielen des neuen Teams. |
| B31 | Gegnerfarbe nur über Umwege | nicht behoben: Farbchip im Kopf antippbar mit fünf Trikots ist ein eigener Baustein; bleibt im Dialog «Spiel bearbeiten». |
| B32 | Alte Routen ohne Umleitung, zwei auf 404 | behoben (e779fe1): `matrix` → Szenen als Tabelle (Pivot unter `?pivot=1`), `scouting` → Gegner, `feed`, `schedule`, `consents`, `assignments` (Verein und Team) → Spiele, solange keine Teamfunktionen an sind (Spieler und Eltern erreichen sie immer); schon vorher: `assistant`, `library`, `search`, `live`, `marks`, `paper`, `profile`, `settings`. `/club/federation` ist kein 404 mehr (Verband-Seite oder Erklärung). Nicht umgeleitet, weil sonst Funktionen verschwinden: `presentations` (Handy-Fernbedienung), `playlists` («Im Team teilen» für Spieler), beides kann die Sammlung noch nicht; `training`, `drills`, `plays`, `official`, `join-requests` (laut SPEC 6 ausserhalb der Navigation, aber erreichbar). 404 im App-Rahmen (B53). |
| B33 | Einwilligung: Spieler vorbelegt | behoben (e779fe1): «Bitte wählen» zuerst, nichts vorbelegt; nach dem Senden Name gross bestätigt; Kästchen 24 px. |
| B34 | Spielerseite und Kader im alten Aufbau | nicht behoben: Umbau der Spielerseite (ohne Torvorlagen und Anwesenheit) nicht geschafft. |
| B35 | Mehr-Menü voller alter Funktionen | behoben (e779fe1): Spieltag-Einträge nur vor dem Resultat, «Vorbereitung» weg (lebt im Gegner), «Matchkarte» ist jetzt «Als Bild für den Chat» in Tab Spiel. Geblieben: PDF, Gegner, Daten austauschen, Bearbeiten, Löschen. |
| B36 | Wörter im Tab Video | behoben (07790d7, e779fe1): Vereinsname statt «Wir», Positionen ausgeschrieben, «Minute 4 bis 11», ein «Teilen», «Person hervorheben». |
| B37 | Upload-Dialog bietet «Training» an | behoben (e779fe1): «Spiel \| Training» nur mit Teamfunktionen. Spielformat bleibt wählbar. |
| B38 | Öffentliche Startseite verspricht zu viel | nicht behoben: die öffentliche Website baut eine eigene Session neu (`apps/site`, Branch `claude/site-anlauf`); hier tabu. |
| B39 | Doppelte Rückennummer auf der Kamera | behoben (9b12b32): eine Nummer pro Team und Moment; im Demo trägt nur der Torschütze eine Nummer. Test `test_graphics.py`. |
| B40 | Start: Nächster Gegner und Tabelle | nicht behoben: drei Fakten und Tabelle beim Nächsten Gegner brauchen Tabellen- und Berichtsdaten im Start; nicht geschafft. |
| B41 | Saison: Ballverluste mit Szenen, Rang fehlt | teilweise (e779fe1): Ballverluste ohne Szenen-Link («aus dem Spielbericht»). Rang und Tabelle in der Saison: nicht behoben. |
| B42 | Nächstes Spiel: Platzhalter, Kasten im Kasten | nicht behoben. |
| B43 | Verein: «Verein» dreimal, roher Farbwähler | nicht behoben. |
| B44 | Ziele unter 44 px | teilweise (e779fe1): Team-Umschalter, «Video hochladen» in der Spielliste, Einwilligungs-Kästchen, Banner weg (B48). Namen im Team und Zahlen in Tabellen nicht. |
| B45 | Prüfen am Handy | behoben (e779fe1): «Später weiter» auf einer Zeile, «Weiss nicht» links wie die anderen Antworten. |
| B46 | Anmelden und Registrieren als Karte | teilweise (e779fe1): keine Karten mehr (Anmelden, Registrieren, Passwort, Einladung); Keil und doppeltes «Anmelden» nicht angefasst. |
| B47 | Onboarding-Wörter | teilweise (e779fe1): «Team suchen», «Das ist mein Team», «Ist das dein Team?», «Personen im Kader». «Hauptrunde - M2-02» kommt so aus handball.ch. |
| B48 | Zwei-Faktor-Banner auf jedem Screen | behoben (e779fe1): Punkt am Konto und Eintrag «Zwei-Faktor-Anmeldung einrichten» im Konto-Menü. |
| B49 | Seitentitel fehlen | behoben (e779fe1): Team («Team · Herren 1») und Prüfen. |
| B50 | «Zeichnen» statt «Unentschieden» | behoben (e779fe1): eigener Schlüssel `anlauf.drawResult`. |
| B51 | Taktikkamera am Handy zu klein | behoben (e779fe1): unter 640 px die angegriffene Hälfte (Tab Video und «Punkt 1, geöffnet»). |
| B52 | Szenen: Highlights-Satz falsch | behoben (e779fe1): «Vom Spiel gegen … gibt es noch keine Highlights.» mit Weg ins Spiel. Seitenleisten-Links bleiben (Spielzüge laut SPEC aus den Szenen erreichbar). |
| B53 | 404 ohne Rahmen | behoben (e779fe1): unbekannte Adressen in der App zeigen den 404 im App-Rahmen mit Seitenkopf. |
| B54 | Abmelden ohne Rückmeldung; Upload-Race im Seed | behoben (a3fab6c, e779fe1): «Du bist abgemeldet.»; das Anlegen des Videos committet jetzt vor der Antwort. Ursache vermutlich: die Transaktion der Anfrage endet erst nach dem Senden der Antwort, ein sofortiges `POST /videos/<id>/parts` fand das Video noch nicht. Lokal nicht nachgestellt. |

## Second delivery: entry for older coaches (H01 to H14, Z1 to Z8)

Source: `docs/ux-test/runde1/EINSTIEG.md` on `claude/ux-test`. Sheet of the new way on the phone
with large text and the numbers against today: `docs/screens/anlauf/einstieg-ablauf.jpg`.

| # | Befund | Status |
|---|---|---|
| H01 | Spieltag: Tasten über dem Spielerraster bei niedrigem Fenster | behoben (a6e9c4c): Kopf und Tasten kleben erst ab 600 px Höhe; e2e prüft 844×390 und 640×400 (fand vorher «Tor» über «11 Lina»). |
| H02 | Kein Nutzen auf dem Start vor dem ersten Video | behoben (1fd89b2): Rang und Serie, Tabellenausschnitt, Torschützen aus den Spielberichten, nächster Gegner; Aufgabe «Video hochladen». |
| H03 | App vor dem Konto nicht ansehbar, Demo-Spiel fehlt | behoben (0a0d447, 1fd89b2): öffentlicher Einstieg /einstieg mit dem eigenen Team und den drei Dingen eines Demo-Spiels als Beispiel; «Demo-Spiel ansehen» auf dem Start. |
| H04 | Team beim ersten Besuch: alles fehlt | behoben (3b57453): vor dem ersten Video keine Fehlt-Aufnäher, «Von handball.ch.», eine Liste statt «Ohne Position», ein Satz zur Einwilligung. |
| H05 | Erstes Video: keine einfache Anleitung, Beruhigung nie gezeigt | behoben (3b57453): drei Sätze offen und Link auf die Filmanleitung der Website, «Video wählen» am Handy, Kamera und Technik hinter «Mehr», nach dem Upload «Du kannst die Seite schliessen …», Balken nur vorwärts. |
| H06 | Am Handy erfährt man nicht, dass die Analyse fertig ist | behoben (2cd4bf3): Glocke in der Handy-Kopfzeile; Mail und Mitteilung mit Spielnamen bei fertiger und gescheiterter Analyse und bei unlesbarer Datei. Test `test_support.py`. |
| H07 | Upload-Dialog verlangt zwei Dinge auf einmal | behoben (3b57453): zuerst nur die Spiele, das letzte oben; «Anderes Spiel» als eigener Schritt mit Gegner und Datum, der Rest hinter «Mehr». |
| H08 | Schrift zu klein | behoben (a76ae8e): `text-xs` 14 px, nichts Gelesenes unter 14 px, Mono-Beschriftungen 13 px in voller Tinte, Achsen 13 px, Rückennummern ab 14 px; ANLAUF.md 6 und design-lint. Gemessen auf dem Einstieg: 0 Textstellen unter 14 px. |
| H09 | Nur-Symbol-Knöpfe; Teamname verschwindet | behoben (2cd4bf3, 3b57453, a76ae8e): «Video», «Teilen», «Mehr» mit Wort; Teamname zweizeilig, das Wappen weicht unter 360 px. Die Glocke bleibt ein Symbol mit Zahl. |
| H10 | Wörter, die Hans nicht versteht | behoben (a76ae8e, frühere Blöcke): Wortliste abgearbeitet (Paradenquote, Angriffseffizienz, Belege anzeigen, Baustelle, Spielformat, Taktik, Quellen, Wie gerechnet, Anlauf bis zur Wurfposition, Daten austauschen, Mannschaft, Übernehmen, Systemstatus); Fachwörter der Technik stehen hinter «Mehr». Positionskürzel auf den Minifeldern (RA, RL) bleiben dort aus Platzgründen; ausgeschrieben in Listen und Titeln. |
| H11 | Vereinsname uneinheitlich | behoben (1fd89b2): Kopf, Telegramm und Kamera nennen das Team wie die Kopfzeile (Teamname, ausser er ist generisch wie «Herren 1»). Test `own-name.test.ts`. |
| H12 | Antwort in Prüfen nicht zurücknehmbar | behoben (a76ae8e): «Zurück» öffnet die letzte Antwort, «Beantwortet» mit «Antwort ändern». |
| H13 | Was sich beim ersten Besuch vordrängt | behoben (1fd89b2, 3b57453): kein Banner mehr; Zwei-Faktor erst mit Video oder zweiter Person, als Aufgabe auf der Team-Seite und im Konto-Menü, sieben Tage wegklickbar (OPEN_QUESTIONS Q-AUTH-2b). |
| H14 | Saison-Verlauf: Beschriftungen stossen zusammen | behoben (a76ae8e): Namen auf den Platz gekürzt, voller Name als Titel. |
| Z1 | Alte Startseite der App | behoben (1fd89b2): «/» leitet Angemeldete in die App, alle anderen auf /einstieg (mit q, farbe, lang). Erledigt damit auch B38. |
| Z2 | Linke Spalte Anmelden/Registrieren | behoben (1fd89b2): Logo, «Dein Spiel. Und drei Dinge zum Mitnehmen.», Link zur Website. |
| Z3 | /einstieg übernimmt q, farbe, lang | behoben (1fd89b2): nichts wird zweimal gefragt; der Suchsatz erklärt das Produkt nicht neu. |
| Z4 | Versprechen: Nachricht, Beispielspiel | behoben (2cd4bf3, 1fd89b2): Mail und Glocke; das Beispiel der drei Dinge gibt es wirklich, als Beispiel beschriftet. |
| Z5 | Laufdistanzen, Pässe, Ball | behoben (9b12b32, 3b57453): xG und Ballbesitz ganz weg; Laufleistung nur aus Video, hinter «Alle Zahlen» und «geschätzt». Torvorlagen: siehe B34. |
| Z6 | Dauer der Analyse | behoben (3b57453): keine «40 Minuten» mehr; Minuten nur gemessen am laufenden Job, sonst «Du bekommst eine Mail». |
| Z7 | Eine Filmanleitung | behoben (3b57453): Link auf handball-ai.ch/aufnahme/, im Upload nur drei Sätze. |
| Z8 | Testphase und Preis | behoben (d19b47f, 3b57453): neue Vereine starten die Testphase aus plans.json ohne Zahlungsdaten (Schalter `trial_on_signup`, OPEN_QUESTIONS Q-BILL-TRIAL); Verein › Abo zeigt «Testphase bis …» und was danach gilt. |

## Tests

- vitest: `thing-sequence`, `scene-words`, `telegram`, design lint and the rest.
- pytest: metrics (`test_goals_without_time_have_no_runs_and_no_course`,
  `test_ratios_need_attempts_in_their_own_direction`), graphics (unique numbers, demo court rule),
  sharing (token in the listing).
- e2e: `collection.spec` (new), `data.spec` (B02, B21), `live.spec` and `m11.spec` (B03), `analysis.spec`
  (B07, B08), `onboarding.spec` (B06), `training.spec` (team functions).
- axe (WCAG 2.2 AA) after block 4: 11 pages (Spiele, Spiel/Video/Zahlen, Prüfen, Team, Saison,
  Szenen, Sammlungen, Kader bearbeiten, Spieltag) in all six check colours at 1280 and 390 px: no
  violations.
- Red before this work and not touched: `apps/api/tests/test_official.py::test_daily_tick_syncs_and_imports_reports`.
