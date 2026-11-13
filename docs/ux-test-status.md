# UX test, round 1: status per finding

Source: `docs/ux-test/runde1/BEFUNDE.md` on branch `claude/ux-test` (read only, not merged
here). One line per finding: **behoben** (commit), **teilweise** (what is done, what is open),
**nicht behoben** (reason) or **kein Fehler** (reason). Commits on `claude/trikot-ui`.

Comparison images of the rebuilt screens: `docs/screens/anlauf/vergleich/ux1-*.jpg`.

| # | Befund | Status | Runde 2 |
|---|---|---|---|
| B01 | Szenen zu Punkt 1 nicht erreichbar | behoben (07790d7): «n Szenen» öffnet genau die Szenen dieses Dings (`?thing=n`), Liste rechts, laufende gelb, «Nächste Szene», «Alle n abspielen»; die Zeitleisten-Liste heisst «Minute x bis y». Test `lib/thing-sequence.test.ts`. | Testerin: behoben. |
| B02 | «Suchen» endet beim Assistenten | behoben (07790d7): «Suchen» öffnet die Szenen-Suche; freie Eingaben in der Schnellsuche landen dort; `/assistant?q=` leitet mit der Frage um; Sätze werden Chips. Tests `lib/scene-words.test.ts`, e2e `data.spec`. | Testerin: behoben. |
| B03 | Spieltag: Einträge nach Neu laden weg | behoben (07790d7): Spieltag und Detail-Erfassung laden Marken und Ereignisse beim Öffnen vom Server, Resultat und Liste bleiben nach Neu laden; e2e `live.spec`, `m11.spec`. Die Doppelten der Testerin liegen nur in ihrer lokalen Datenbank; `scripts/seed.py` erzeugt keine Live-Ereignisse, es gibt dort nichts zu bereinigen. | Testerin: behoben (online). Danach: offline: behoben (eb50931, N01/N02). |
| B04 | «Am Bildschirm zeigen» tut nichts | behoben (a3fab6c): eigene Vollbild-Ansicht `collections/[id]/present` (Szenen nacheinander, Notizen als Tafel, Tasten, «Vollbild», «Schliessen» in e779fe1). e2e `collection.spec`. | Testerin: behoben. |
| B05 | Sammlung: keine Notiz, nichts entfernen, nichts umbenennen | behoben (a3fab6c): «Notiz dazu», «Nach oben/unten», «Entfernen», Titel antippen; sofort und der Reihe nach gespeichert. e2e `collection.spec`. | Testerin: behoben. |
| B06 | Sprache lässt sich nicht wechseln | behoben (a3fab6c): Sprachen ausgeschrieben im Konto-Menü, auf Anmeldung und im Einstieg; ohne Wahl gilt die Browsersprache. e2e `onboarding.spec` «language». | Testerin: behoben. |
| B07 | Nur Spielbericht: erfundene Läufe, leerer Verlauf | behoben (9b12b32): Tore ohne Zeit haben keine Reihenfolge, also keine Läufe, keinen Verlauf, keine Torflaute (`timeline.timed`); Quoten nur mit Fehlwürfen in derselben Richtung; nie erfasste Werte «-»; «Spielbericht» statt «Papierbericht». Zustand «Kein Video» in Tab Spiel (43d69c9). Tests metrics, e2e `analysis.spec`. | Testerin: behoben. |
| B08 | Tab Spiel: unter den drei Dingen das alte Produkt | behoben (43d69c9): Aktionen (Fürs Team, Highlights teilen, Als Bild für den Chat), «Punkt 1, geöffnet» auf der Taktikkamera, Telegramm, daneben Gegentore/Eigene Tore und drei Zahlen mit Quelle; alles Alte hinter «Mehr zum Spiel»; xG und Ballbesitz gestrichen. «Dazu üben» fehlt (es gibt keine Zuordnung Ding zu Übung in den Daten). Vergleich `ux1-spiel*.jpg`. | Testerin: teilweise. Danach: behoben (e5aaaf1): «Mehr zum Spiel» nur Verlauf, Highlights, Spieltag; Vergleich in Zahlen. |
| B09 | «Spiel öffnen» öffnet Video; Tabs nicht in der Adresse | behoben (07790d7): Standard Tab Spiel, `?tab=` in der Adresse, Zurück wechselt den Tab. | Testerin: behoben. |
| B10 | Nach dem Upload: Einrichtungs-Assistent im Tab Video | behoben (08e0274): Prüfen fragt Feld, Anwurf (pro Halbzeit, «Jetzt ist Anwurf» im Video), Tore und Personen. Im Tab Video keine Einrichtungsschritte mehr; «Einrichten von Hand» öffnet sie bei Bedarf (nichts gelöscht). | Testerin: teilweise. Danach: behoben (729d38f, N04): auch nach neuem Video keine Werkbank. |
| B11 | «Analyse läuft» spricht Technik | behoben (e779fe1): Titel «Die Analyse läuft.», drei Schritte in Trainerwörtern (Video gelesen, Spieler werden verfolgt, Drei Dinge werden gesucht), Minuten bis fertig sobald messbar, die technischen Schritte hinter «Einzelschritte». | Testerin: behoben. |
| B12 | Taktikkamera zeigt Positionen ohne bestätigtes Feld | behoben (9b12b32): bei offener Feldfrage keine Positionen, auch im Demo; «Stimmt das Feld?», Grund, «Feld prüfen»; nach «Ja, stimmt» erscheinen sie. Test `test_graphics.py`. | Testerin: behoben. |
| B13 | Prüfen zeigt das erkannte Feld nicht | behoben (08e0274): die Ecken (0,0), (40,0), (40,20), (0,20) werden aus der gespeicherten Kalibrierung ins Hallenbild projiziert, Viereck und Feldlinien darüber. Test: lib/field-corners.test.ts. | Testerin: behoben. |
| B14 | «Ecken verschieben» verlässt Prüfen | behoben (08e0274): vier Griffe im Prüfen-Screen (Maus, Finger, Pfeiltasten), Linien folgen sofort; «Passt» speichert die verschobenen Ecken als Kalibrierung (sonst Bestätigung), «Zurücksetzen» holt das erkannte Feld zurück. | Testerin: behoben. |
| B15 | Geteilte Seite nicht nach Zielbild | behoben (a3fab6c, 678f9af): Vereinskopf mit «geteilt von», Szenentitel, Umschalter Video | Taktik pro Torszene und Minifeld in der Liste aus den gemessenen Positionen (nur mit bestätigtem Feld; sonst leeres Feld). Test: test_shared_goal_scene_carries_its_tactics_camera. |
| B16 | «Fürs Team» enthält nicht die drei Dinge | behoben (a3fab6c): Entwurf aus den drei Dingen (je Notiz, dann genau seine Szenen, keine Doppelten); Seed gleich. | Testerin: behoben. |
| B17 | Teilen: Extra-Dialog, Link nur einmal sichtbar | behoben (a3fab6c): «Link teilen» erstellt und kopiert in einem Schritt, Link bleibt sichtbar und abrufbar (verschlüsselt gespeichert, Migration 0043), «Link sperren». e2e `collection.spec`. | Testerin: teilweise. Danach: behoben (44df486): Seite zeigt den neuen Link sofort. |
| B18 | «Suchen» öffnet die Schnellsuche | behoben (07790d7): Knopf «Suchen» öffnet die Szenen-Suche mit Fokus. | Testerin: behoben am Desktop, **neu kaputt** am Handy. Danach: behoben (e5aaaf1): Lupe in der Handy-Kopfzeile, Szenen öffnet mit Fokus. |
| B19 | Suchfeld versteht keine Sätze; Rohwerte | behoben (07790d7): Sätze werden Chips (de, fr, en); Kacheln mit Wörtern statt Rohwerten. | Testerin: teilweise. Danach: behoben (694d821): Gegner («gegen Stäfa») und Nummer («Nummer 11», auch über den Kader). |
| B20 | «letzte 3 Spiele» meint mit Video | behoben (07790d7): Chip heisst «letzte 3 mit Video». | Testerin: behoben. |
| B21 | «Alle 24 abspielen», «Als Tabelle» | behoben (e779fe1): «Alle n abspielen» spielt alle Szenen der Antwort über die Spiele hinweg als Folge im Vollbild; «Als Tabelle» zeigt dieselbe Antwort als Zeilen im selben Screen (`?view=table`); die alte Pivot-Tabelle bleibt unter `matrix?pivot=1`. | Testerin: behoben. |
| B22 | Spieltag ist die alte Detail-Erfassung | behoben (07790d7): grosse Tasten nach Zielbild, «Bisher», «Pro Spielerin erfassen» führt zur Detail-Erfassung. | Testerin: teilweise. Danach: behoben (1d90026, N14). |
| B23 | Tab Zahlen ist die alte Statistikseite | behoben (43d69c9, 3d540ec): Feld- und Tor-Tabelle, Gegentore nach Position, «Ziel im Tor» als schlichtes Raster, Phasen mit Quelle, Würfe/Quote nur mit erfassten Fehlwürfen, Rest hinter «Alle Zahlen». Jede Zahl (Tore, 7 m, 2 Min, Würfe, Paraden, Gegentore) öffnet ihre Szenen unter der Tabelle; Spalte «Bestätigt», wenn alle Tore der Person von Hand markiert oder bestätigt sind. Vergleich `ux1-zahlen*.jpg`. | Testerin: teilweise. Danach: behoben (e5aaaf1): «Bestätigt» nach Person. |
| B24 | «Übernehmen» wartet ohne Wort; Neu laden überspringt Schritt 2 | behoben (e779fe1): nur der gewählte Knopf dreht, Satz «Wir holen Spiele, Kader und Tabelle …»; Schritt 2 bleibt nach Neu laden, bis bestätigt oder «Das ist nicht mein Team». | Testerin: teilweise. Danach: behoben (faa1e82, N03). |
| B25 | Registrierung: Fehler auf Englisch, Bedingungen nicht verlinkt | behoben (e779fe1): Prüfung im Formular in der eigenen Sprache an jedem Feld, Kästchen markiert; «Nutzungsbedingungen» und «Datenschutzerklärung» verlinkt (handball-ai.ch/agb, /datenschutz). | Testerin: behoben. |
| B26 | Erster Screen ohne Aufgabe | behoben (e779fe1): beim letzten Spiel ohne Video Hauptknopf «Video hochladen», daneben «Demo-Spiel ansehen»; Zwei-Faktor als Punkt am Konto (B48). | Testerin: behoben. |
| B27 | Verein von Hand: Vierschritt-Assistent mit Einladungen | behoben (0e8eb3f): zwei Schritte, 1. Name und Trikot (acht Trikots wie beim handball.ch-Weg; Land, Wappen, eigene Farbe hinter «Mehr»), 2. Team, dann «Zum Team». Kader auf der Teamseite, Einladungen unter Verein › Teams und Rollen (beides unverändert vorhanden). | Testerin: behoben. |
| B28 | Leerer Verein: Formular-Karte, geratene Gegnerfarbe, falscher Leer-Satz | teilweise (e779fe1): Szenen sagen «Szenen gibt es nach dem ersten Video.»; die Gegnerfarbe wird nur gespeichert, wenn jemand sie wählt (war schon so), die Vorschau zeigt aber noch Rot; das Formular als Start ist geblieben. | Testerin: nicht geprüft. |
| B29 | Falsche oder kaputte Datei: keine Erklärung | behoben (e779fe1, 2cd4bf3): Erklärung und «Andere Datei wählen»; Glocke und Mail bei fehlgeschlagener Analyse oder Datei, mit Gegnername. | Testerin: teilweise. Danach: behoben (140e4c5): Textdatei wird vor dem Upload abgelehnt, mit Satz. |
| B30 | Team wechseln auf einer Spielseite | behoben (e779fe1): auf Seiten eines Spiels, einer Sammlung oder eines Gegners führt der Wechsel zu den Spielen des neuen Teams. | Testerin: behoben. |
| B31 | Gegnerfarbe nur über Umwege | behoben (3d540ec): ist die Farbe offen, fragt der Kopf mit fünf Trikots; ist sie bekannt, öffnet «Farbe von … ändern» im Kopf dieselben fünf Trikots, gespeichert beim Antippen. | Testerin: behoben. |
| B32 | Alte Routen ohne Umleitung, zwei auf 404 | behoben (e779fe1): `matrix` → Szenen als Tabelle (Pivot unter `?pivot=1`), `scouting` → Gegner, `feed`, `schedule`, `consents`, `assignments` (Verein und Team) → Spiele, solange keine Teamfunktionen an sind (Spieler und Eltern erreichen sie immer); schon vorher: `assistant`, `library`, `search`, `live`, `marks`, `paper`, `profile`, `settings`. `/club/federation` ist kein 404 mehr (Verband-Seite oder Erklärung). Nicht umgeleitet, weil sonst Funktionen verschwinden: `presentations` (Handy-Fernbedienung), `playlists` («Im Team teilen» für Spieler), beides kann die Sammlung noch nicht; `training`, `drills`, `plays`, `official`, `join-requests` (laut SPEC 6 ausserhalb der Navigation, aber erreichbar). 404 im App-Rahmen (B53). | Testerin: behoben (mit Ausnahmen der Bau-Session). |
| B33 | Einwilligung: Spieler vorbelegt | behoben (e779fe1): «Bitte wählen» zuerst, nichts vorbelegt; nach dem Senden Name gross bestätigt; Kästchen 24 px. | Testerin: behoben. |
| B34 | Spielerseite und Kader im alten Aufbau | behoben (10d70c5): Spielerseite mit Seitenkopf (Name als Titel, Nummer als Zahl), ohne Torvorlagen und ohne Anwesenheit, «Fehler» heisst «Ballverluste»; «Kader bearbeiten» im Seitenkopf. | Testerin: teilweise. Danach: behoben (e5aaaf1, N12). |
| B35 | Mehr-Menü voller alter Funktionen | behoben (e779fe1): Spieltag-Einträge nur vor dem Resultat, «Vorbereitung» weg (lebt im Gegner), «Matchkarte» ist jetzt «Als Bild für den Chat» in Tab Spiel. Geblieben: PDF, Gegner, Daten austauschen, Bearbeiten, Löschen. | Testerin: behoben. |
| B36 | Wörter im Tab Video | behoben (07790d7, e779fe1): Vereinsname statt «Wir», Positionen ausgeschrieben, «Minute 4 bis 11», ein «Teilen», «Person hervorheben». | Testerin: behoben. |
| B37 | Upload-Dialog bietet «Training» an | behoben (e779fe1): «Spiel \| Training» nur mit Teamfunktionen. Spielformat bleibt wählbar. |
| B38 | Öffentliche Startseite verspricht zu viel | behoben über Z1: ohne Sitzung führt «/» auf den öffentlichen Einstieg (/einstieg), die Versprechen stehen auf der Website (`apps/site`, eigene Session). | Testerin: behoben. |
| B39 | Doppelte Rückennummer auf der Kamera | behoben (9b12b32): eine Nummer pro Team und Moment; im Demo trägt nur der Torschütze eine Nummer. Test `test_graphics.py`. | Testerin: behoben. |
| B40 | Start: Nächster Gegner und Tabelle | behoben (10d70c5): drei Fakten aus der Tabelle (Rang und Punkte, Bilanz, Tore pro Spiel) und dem letzten Duell, darunter die Tabelle um beide Teams; ohne Tabelle und Duell nur Name und Datum, kein leeres Feld. | Testerin: teilweise. Danach: behoben (140e4c5): Gegner nur noch einmal. |
| B41 | Saison: Ballverluste mit Szenen, Rang fehlt | behoben (e779fe1, 10d70c5): Ballverluste ohne Szenen-Link; Rang im Titel oder in der Kopfzeile, sobald die Tabelle bekannt ist, Tabelle in der Seitenspalte. | Testerin: nicht geprüft. |
| B42 | Nächstes Spiel: Platzhalter, Kasten im Kasten | behoben (0e8eb3f): vor dem Spiel stehen Datum und Uhrzeit statt «-:-» im Kopf und im Streifen; Upload-Block ohne äusseren Kasten, Kamera-Auswahl hinter «Mehr». | Testerin: behoben. |
| B43 | Verein: «Verein» dreimal, roher Farbwähler | behoben (0e8eb3f): Abschnitt «Name, Trikot und Wappen», acht Trikots mit Vorschau im Spielkopf, eigene Farben hinter einem Klick, «Wappen» statt «Logo». | Testerin: behoben. |
| B44 | Ziele unter 44 px | teilweise (e779fe1): Team-Umschalter, «Video hochladen» in der Spielliste, Einwilligungs-Kästchen, Banner weg (B48). Namen im Team und Zahlen in Tabellen nicht. | Testerin: teilweise. Danach: behoben (140e4c5, 44df486): Feldecken 44 px, Zahlen in Tabellen 44 px; Rest wie Runde 1. |
| B45 | Prüfen am Handy | behoben (e779fe1): «Später weiter» auf einer Zeile, «Weiss nicht» links wie die anderen Antworten. | Testerin: behoben. |
| B46 | Anmelden und Registrieren als Karte | teilweise (e779fe1): keine Karten mehr (Anmelden, Registrieren, Passwort, Einladung); Keil und doppeltes «Anmelden» nicht angefasst. | Testerin: teilweise. Danach: teilweise (44df486): ein «Anmelden»; der Keil bleibt (Gestaltung des Seitenkopfs). |
| B47 | Onboarding-Wörter | teilweise (e779fe1): «Team suchen», «Das ist mein Team», «Ist das dein Team?», «Personen im Kader». «Hauptrunde - M2-02» kommt so aus handball.ch. | Testerin: teilweise. Danach: behoben (140e4c5, N25): Liga statt Gruppen-Kürzel. |
| B48 | Zwei-Faktor-Banner auf jedem Screen | behoben (e779fe1): Punkt am Konto und Eintrag «Zwei-Faktor-Anmeldung einrichten» im Konto-Menü. | Testerin: behoben. |
| B49 | Seitentitel fehlen | behoben (e779fe1): Team («Team · Herren 1») und Prüfen. | Testerin: teilweise. Danach: behoben (44df486). |
| B50 | «Zeichnen» statt «Unentschieden» | behoben (e779fe1): eigener Schlüssel `anlauf.drawResult`. | Testerin: nicht geprüft. |
| B51 | Taktikkamera am Handy zu klein | behoben (e779fe1): unter 640 px die angegriffene Hälfte (Tab Video und «Punkt 1, geöffnet»). | Testerin: behoben. |
| B52 | Szenen: Highlights-Satz falsch | behoben (e779fe1): «Vom Spiel gegen … gibt es noch keine Highlights.» mit Weg ins Spiel. Seitenleisten-Links bleiben (Spielzüge laut SPEC aus den Szenen erreichbar). | Testerin: behoben. |
| B53 | 404 ohne Rahmen | behoben (e779fe1): unbekannte Adressen in der App zeigen den 404 im App-Rahmen mit Seitenkopf. | Testerin: teilweise. Danach: behoben (694d821, N18) für unbekannte Adressen; unbekannte Spiel-IDs antworten weiter mit 200 (gestreamter Rahmen). |
| B54 | Abmelden ohne Rückmeldung; Upload-Race im Seed | behoben (a3fab6c, e779fe1): «Du bist abgemeldet.»; das Anlegen des Videos committet jetzt vor der Antwort. Ursache vermutlich: die Transaktion der Anfrage endet erst nach dem Senden der Antwort, ein sofortiges `POST /videos/<id>/parts` fand das Video noch nicht. Lokal nicht nachgestellt. | Testerin: behoben. |

## Second delivery: entry for older coaches (H01 to H14, Z1 to Z8)

Source: `docs/ux-test/runde1/EINSTIEG.md` on `claude/ux-test`. Sheet of the new way on the phone
with large text and the numbers against today: `docs/screens/anlauf/einstieg-ablauf.jpg`.

Correction (round 2, N03): the sheet's «0 s waiting without a sentence» was measured with the
federation's answers already cached. Measured again with a cold cache (team not asked before,
local stack, phone 390 px): before the change 9 to 16 s with only «…»; after it the sentence «Wir
holen die Spiele von handball.ch.» and the head with name and league after 0.2 s, the team with
rank and table after 2.0 s, the scorers after 9.3 s (they fill in while the coach reads). Warm:
team after 0.5 s.

| # | Befund | Status | Runde 2 |
|---|---|---|---|
| H01 | Spieltag: Tasten über dem Spielerraster bei niedrigem Fenster | behoben (a6e9c4c): Kopf und Tasten kleben erst ab 600 px Höhe; e2e prüft 844×390 und 640×400 (fand vorher «Tor» über «11 Lina»). | Testerin: behoben. |
| H02 | Kein Nutzen auf dem Start vor dem ersten Video | behoben (1fd89b2): Rang und Serie, Tabellenausschnitt, Torschützen aus den Spielberichten, nächster Gegner; Aufgabe «Video hochladen». | Testerin: behoben. |
| H03 | App vor dem Konto nicht ansehbar, Demo-Spiel fehlt | behoben (0a0d447, 1fd89b2): öffentlicher Einstieg /einstieg mit dem eigenen Team und den drei Dingen eines Demo-Spiels als Beispiel; «Demo-Spiel ansehen» auf dem Start. | Testerin: behoben. |
| H04 | Team beim ersten Besuch: alles fehlt | behoben (3b57453): vor dem ersten Video keine Fehlt-Aufnäher, «Von handball.ch.», eine Liste statt «Ohne Position», ein Satz zur Einwilligung. | Testerin: behoben. Danach: behoben (44df486): Einwilligungen einmal in der Seitenspalte, kein Aufnäher pro Zeile. |
| H05 | Erstes Video: keine einfache Anleitung, Beruhigung nie gezeigt | behoben (3b57453): drei Sätze offen und Link auf die Filmanleitung der Website, «Video wählen» am Handy, Kamera und Technik hinter «Mehr», nach dem Upload «Du kannst die Seite schliessen …», Balken nur vorwärts. | Testerin: teilweise. Danach: behoben (3153fe3, 140e4c5): Link mit /de/, Satz bleibt sichtbar. |
| H06 | Am Handy erfährt man nicht, dass die Analyse fertig ist | behoben (2cd4bf3): Glocke in der Handy-Kopfzeile; Mail und Mitteilung mit Spielnamen bei fertiger und gescheiterter Analyse und bei unlesbarer Datei. Test `test_support.py`. | Testerin: behoben, mit neuem Problem. Danach: behoben (729d38f, N05). |
| H07 | Upload-Dialog verlangt zwei Dinge auf einmal | behoben (3b57453): zuerst nur die Spiele, das letzte oben; «Anderes Spiel» als eigener Schritt mit Gegner und Datum, der Rest hinter «Mehr». | Testerin: behoben. |
| H08 | Schrift zu klein | behoben (a76ae8e): `text-xs` 14 px, nichts Gelesenes unter 14 px, Mono-Beschriftungen 13 px in voller Tinte, Achsen 13 px, Rückennummern ab 14 px; ANLAUF.md 6 und design-lint. Gemessen auf dem Einstieg: 0 Textstellen unter 14 px. | Testerin: behoben. |
| H09 | Nur-Symbol-Knöpfe; Teamname verschwindet | behoben (2cd4bf3, 3b57453, a76ae8e): «Video», «Teilen», «Mehr» mit Wort; Teamname zweizeilig, das Wappen weicht unter 360 px. Die Glocke bleibt ein Symbol mit Zahl. | Testerin: behoben. |
| H10 | Wörter, die Hans nicht versteht | behoben (a76ae8e, frühere Blöcke): Wortliste abgearbeitet (Paradenquote, Angriffseffizienz, Belege anzeigen, Baustelle, Spielformat, Taktik, Quellen, Wie gerechnet, Anlauf bis zur Wurfposition, Daten austauschen, Mannschaft, Übernehmen, Systemstatus); Fachwörter der Technik stehen hinter «Mehr». Positionskürzel auf den Minifeldern (RA, RL) bleiben dort aus Platzgründen; ausgeschrieben in Listen und Titeln. | Testerin: teilweise. Danach: behoben (44df486, 140e4c5): «Statistik», «Daten exportieren und importieren», «Status der App», «Frei 3/1» ersetzt. |
| H11 | Vereinsname uneinheitlich | behoben (1fd89b2): Kopf, Telegramm und Kamera nennen das Team wie die Kopfzeile (Teamname, ausser er ist generisch wie «Herren 1»). Test `own-name.test.ts`. | Testerin: behoben. |
| H12 | Antwort in Prüfen nicht zurücknehmbar | behoben (a76ae8e): «Zurück» öffnet die letzte Antwort, «Beantwortet» mit «Antwort ändern». | Testerin: behoben. |
| H13 | Was sich beim ersten Besuch vordrängt | behoben (1fd89b2, 3b57453): kein Banner mehr; Zwei-Faktor erst mit Video oder zweiter Person, als Aufgabe auf der Team-Seite und im Konto-Menü, sieben Tage wegklickbar (OPEN_QUESTIONS Q-AUTH-2b). | Testerin: behoben. |
| H14 | Saison-Verlauf: Beschriftungen stossen zusammen | behoben (a76ae8e): Namen auf den Platz gekürzt, voller Name als Titel. | Testerin: nicht geprüft. |
| Z1 | Alte Startseite der App | behoben (1fd89b2): «/» leitet Angemeldete in die App, alle anderen auf /einstieg (mit q, farbe, lang). Erledigt damit auch B38. | Testerin: behoben. |
| Z2 | Linke Spalte Anmelden/Registrieren | behoben (1fd89b2): Logo, «Dein Spiel. Und drei Dinge zum Mitnehmen.», Link zur Website. | Testerin: behoben. |
| Z3 | /einstieg übernimmt q, farbe, lang | behoben (1fd89b2): nichts wird zweimal gefragt; der Suchsatz erklärt das Produkt nicht neu. | Testerin: behoben. |
| Z4 | Versprechen: Nachricht, Beispielspiel | behoben (2cd4bf3, 1fd89b2): Mail und Glocke; das Beispiel der drei Dinge gibt es wirklich, als Beispiel beschriftet. | Testerin: teilweise. Danach: behoben (729d38f, N05). |
| Z5 | Laufdistanzen, Pässe, Ball | behoben (9b12b32, 3b57453): xG und Ballbesitz ganz weg; Laufleistung nur aus Video, hinter «Alle Zahlen» und «geschätzt». Torvorlagen: siehe B34. | Testerin: teilweise. Danach: behoben (e5aaaf1): Ballbesitz und Angriffe weg. |
| Z6 | Dauer der Analyse | behoben (3b57453): keine «40 Minuten» mehr; Minuten nur gemessen am laufenden Job, sonst «Du bekommst eine Mail». | Testerin: behoben. |
| Z7 | Eine Filmanleitung | behoben (3b57453): Link auf handball-ai.ch/aufnahme/, im Upload nur drei Sätze. | Testerin: teilweise. Danach: behoben (3153fe3, N06). |
| Z8 | Testphase und Preis | behoben (d19b47f, 3b57453): neue Vereine starten die Testphase aus plans.json ohne Zahlungsdaten (Schalter `trial_on_signup`, OPEN_QUESTIONS Q-BILL-TRIAL); Verein › Abo zeigt «Testphase bis …» und was danach gilt. | Testerin: behoben. |

## Round 2 (UX test, delivery 1): N01 to N26

Source: `docs/ux-test/runde2/BEFUNDE.md` on `claude/ux-test` (171a47c). The column «Runde 2» in
the tables above gives the tester's check of round 1 and what was done after it.

| # | Befund | Status |
|---|---|---|
| N01 | Spieltag ohne Netz nicht wieder zu öffnen (P1) | behoben (eb50931): Service Worker im neuen Spieltag, Seite, Tasten und Liste auf dem Handy; e2e offline |
| N02 | Offline-Eintrag doppelt | behoben (eb50931): Uploads einzeln, Server speichert pro Spiel und Handy-Kennung einmal; API-Test, e2e |
| N03 | Einstieg: 16 s nur «…» | behoben (faa1e82): Kopf und Satz nach 0,2 s, Team nach 2,0 s (kalt), «langsam» mit «Trotzdem speichern»; e2e |
| N04 | Tab Video nach erstem Video: alte Erfassung | behoben (729d38f): schlichte Bühne, Werkbank nur auf Wunsch; e2e mit neuem Video |
| N05 | Mail «drei Dinge» ohne drei Dinge | behoben (729d38f): Mail und Glocke nach Ergebnis, Start zeigt den nächsten Schritt; API-Tests |
| N06 | Filmanleitung ohne Sprachpfad | behoben (3153fe3): alle Website-Links mit /de, /fr, /en aus der Konfiguration; Test |
| N07 | Geteilte Minifelder unlesbar | behoben (3153fe3): eigener Massstab; Test |
| N08 | Handy: «Suchen» fehlt | behoben (e5aaaf1): Lupe in der Kopfzeile, Wort ab 440 px, Szenen mit Fokus; e2e |
| N09 | Team belegt: Sackgasse | behoben (3153fe3): Hinweis in der Vorschau, danach Stand und zwei Wege; e2e |
| N10 | Tippfehler finden nichts | behoben (694d821): ein Buchstabe Abstand, «Meintest du …?»; Test |
| N11 | Grosse Schrift: Namen und E-Mail laufen aus dem Bild | behoben (3153fe3): Umbruch nach «/», Streifen bricht um, E-Mail umbrechbar |
| N12 | Wurfquote falsch, «Bestätigt» leer, 7 m 0/0 | behoben (e5aaaf1): Würfe ohne geblockte wie die Quote (BRIEF 4.8), 7 m leer ohne Versuch, «Bestätigt» nach Person; Tests |
| N13 | «1 Frage» wird zu sechs | behoben (140e4c5): «1 Frage offen, danach Fragen zu den Personen im Bild» |
| N14 | Spieltag: Uhr, Rückgängig, kleine Tasten, Link | behoben (1d90026): Spieluhr, «Zurücknehmen» (auch auf dem Server), «2 Minuten», «Time-out», «Link teilen»; API-Test, e2e |
| N15 | Anmeldelink 15 Minuten | behoben (3153fe3): 24 Stunden, einmal; OPEN_QUESTIONS Q-AUTH-LINK; Test |
| N16 | Spiel in der Zukunft verlangt das Video | behoben (140e4c5): öffnet auf Spiel mit «Vor dem Spiel», Gegnerfakten, «Spieltag starten» |
| N17 | Feldecken-Griffe zu klein | behoben (140e4c5): 44 px Trefferfläche, Fadenkreuz beim Ziehen |
| N18 | App-404 mit HTTP 200 | teilweise (694d821): unbekannte Adressen 404; unbekannte IDs unter bekannten Pfaden noch 200 |
| N19 | Drosselung beschuldigt handball.ch | behoben (faa1e82) |
| N20 | Anrede mit dem Teil vor dem @ | behoben (729d38f): «Hallo»; Test |
| N21 | Gleiche Adresse: zweiter Verein | behoben (694d821) für den Weg mit Teamnamen (Team in den bestehenden Verein); ein anderes handball.ch-Team ist ein anderer Verein |
| N22 | Abgelaufener oder doppelter Link | behoben (694d821): angemeldet direkt weiter, sonst «Neuen Link an … schicken» mit derselben Teamwahl |
| N23 | Szenenfolge anders als Liste | behoben (694d821): Liste und Folge gleich (neuestes Spiel zuerst, im Spiel in Spielfolge) |
| N24 | Alte Sätze nach der Analyse | behoben (729d38f, 140e4c5): «Die Analyse ist fertig.», Schliessen-Satz bleibt sichtbar |
| N25 | Fachwörter «Hauptrunde - M1-01», «Frei 3/1» | behoben (140e4c5): Liga statt Gruppe, «3 (1 vom 7-m)»; Test |
| N26 | Unbekannte Gegnerfarbe: leeres Kästchen | behoben (140e4c5): Frage mit fünf Trikots, auch wenn das Trikot ohne Farbe gespeichert ist |

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
- axe (WCAG 2.2 AA) after block 6: 14 pages (Spiele, Spiel/Video/Zahlen, Prüfen, Team, Saison,
  Szenen, Sammlungen, Kader bearbeiten, Spieltag, Nächstes Spiel, Verein, Spielerseite) in all six
  check colours at 1280 and 390 px: 168 of 168 without violations. Public: Einstieg (team preview,
  `?farbe=` in all six colours) and the club by hand (both steps) at 1280 and 390 px: no violations
  after the shirt green was set to the checked green (#12804a; #138a4b gave 4.4:1 under white).
- Screens of block 6: `docs/screens/anlauf/runde2/` (Prüfen with the court is shown on a stand-in
  hall image: the local stack has no analysed video; the shared page shows the empty field because
  the demo court is not yet confirmed, as in the app).
- Red before this work and not touched: `apps/api/tests/test_official.py::test_daily_tick_syncs_and_imports_reports`.
