# UX test, round 1: status per finding

Source: `docs/ux-test/runde1/BEFUNDE.md` on branch `claude/ux-test` (read only, not merged
here). One line per finding: **behoben** (commit), **teilweise** (what is done, what is open),
**nicht behoben** (reason) or **kein Fehler** (reason). Commits on `claude/trikot-ui`.

Comparison images of the rebuilt screens: `docs/screens/anlauf/vergleich/ux1-*.jpg`.

| # | Befund | Status | Runde 2 | Runde 3 |
|---|---|---|---|---|
| B01 | Szenen zu Punkt 1 nicht erreichbar | behoben (07790d7): «n Szenen» öffnet genau die Szenen dieses Dings (`?thing=n`), Liste rechts, laufende gelb, «Nächste Szene», «Alle n abspielen»; die Zeitleisten-Liste heisst «Minute x bis y». Test `lib/thing-sequence.test.ts`. | Testerin: behoben. | nicht erneut geprüft |
| B02 | «Suchen» endet beim Assistenten | behoben (07790d7): «Suchen» öffnet die Szenen-Suche; freie Eingaben in der Schnellsuche landen dort; `/assistant?q=` leitet mit der Frage um; Sätze werden Chips. Tests `lib/scene-words.test.ts`, e2e `data.spec`. | Testerin: behoben. | nicht erneut geprüft |
| B03 | Spieltag: Einträge nach Neu laden weg | behoben (07790d7): Spieltag und Detail-Erfassung laden Marken und Ereignisse beim Öffnen vom Server, Resultat und Liste bleiben nach Neu laden; e2e `live.spec`, `m11.spec`. Die Doppelten der Testerin liegen nur in ihrer lokalen Datenbank; `scripts/seed.py` erzeugt keine Live-Ereignisse, es gibt dort nichts zu bereinigen. | Testerin: behoben (online). Danach: offline: behoben (eb50931, N01/N02). | nicht erneut geprüft |
| B04 | «Am Bildschirm zeigen» tut nichts | behoben (a3fab6c): eigene Vollbild-Ansicht `collections/[id]/present` (Szenen nacheinander, Notizen als Tafel, Tasten, «Vollbild», «Schliessen» in e779fe1). e2e `collection.spec`. | Testerin: behoben. | nicht erneut geprüft |
| B05 | Sammlung: keine Notiz, nichts entfernen, nichts umbenennen | behoben (a3fab6c): «Notiz dazu», «Nach oben/unten», «Entfernen», Titel antippen; sofort und der Reihe nach gespeichert. e2e `collection.spec`. | Testerin: behoben. | nicht erneut geprüft |
| B06 | Sprache lässt sich nicht wechseln | behoben (a3fab6c): Sprachen ausgeschrieben im Konto-Menü, auf Anmeldung und im Einstieg; ohne Wahl gilt die Browsersprache. e2e `onboarding.spec` «language». | Testerin: behoben. | nicht erneut geprüft |
| B07 | Nur Spielbericht: erfundene Läufe, leerer Verlauf | behoben (9b12b32): Tore ohne Zeit haben keine Reihenfolge, also keine Läufe, keinen Verlauf, keine Torflaute (`timeline.timed`); Quoten nur mit Fehlwürfen in derselben Richtung; nie erfasste Werte «-»; «Spielbericht» statt «Papierbericht». Zustand «Kein Video» in Tab Spiel (43d69c9). Tests metrics, e2e `analysis.spec`. | Testerin: behoben. | nicht erneut geprüft |
| B08 | Tab Spiel: unter den drei Dingen das alte Produkt | behoben (43d69c9): Aktionen (Fürs Team, Highlights teilen, Als Bild für den Chat), «Punkt 1, geöffnet» auf der Taktikkamera, Telegramm, daneben Gegentore/Eigene Tore und drei Zahlen mit Quelle; alles Alte hinter «Mehr zum Spiel»; xG und Ballbesitz gestrichen. «Dazu üben» fehlt (es gibt keine Zuordnung Ding zu Übung in den Daten). Vergleich `ux1-spiel*.jpg`. | Testerin: teilweise. Danach: behoben (e5aaaf1): «Mehr zum Spiel» nur Verlauf, Highlights, Spieltag; Vergleich in Zahlen. | Testerin: behoben. |
| B09 | «Spiel öffnen» öffnet Video; Tabs nicht in der Adresse | behoben (07790d7): Standard Tab Spiel, `?tab=` in der Adresse, Zurück wechselt den Tab. | Testerin: behoben. | nicht erneut geprüft |
| B10 | Nach dem Upload: Einrichtungs-Assistent im Tab Video | behoben (08e0274): Prüfen fragt Feld, Anwurf (pro Halbzeit, «Jetzt ist Anwurf» im Video), Tore und Personen. Im Tab Video keine Einrichtungsschritte mehr; «Einrichten von Hand» öffnet sie bei Bedarf (nichts gelöscht). | Testerin: teilweise. Danach: behoben (729d38f, N04): auch nach neuem Video keine Werkbank. | Testerin: behoben. |
| B11 | «Analyse läuft» spricht Technik | behoben (e779fe1): Titel «Die Analyse läuft.», drei Schritte in Trainerwörtern (Video gelesen, Spieler werden verfolgt, Drei Dinge werden gesucht), Minuten bis fertig sobald messbar, die technischen Schritte hinter «Einzelschritte». | Testerin: behoben. | nicht erneut geprüft |
| B12 | Taktikkamera zeigt Positionen ohne bestätigtes Feld | behoben (9b12b32): bei offener Feldfrage keine Positionen, auch im Demo; «Stimmt das Feld?», Grund, «Feld prüfen»; nach «Ja, stimmt» erscheinen sie. Test `test_graphics.py`. | Testerin: behoben. | nicht erneut geprüft |
| B13 | Prüfen zeigt das erkannte Feld nicht | behoben (08e0274): die Ecken (0,0), (40,0), (40,20), (0,20) werden aus der gespeicherten Kalibrierung ins Hallenbild projiziert, Viereck und Feldlinien darüber. Test: lib/field-corners.test.ts. | Testerin: behoben. | nicht erneut geprüft |
| B14 | «Ecken verschieben» verlässt Prüfen | behoben (08e0274): vier Griffe im Prüfen-Screen (Maus, Finger, Pfeiltasten), Linien folgen sofort; «Passt» speichert die verschobenen Ecken als Kalibrierung (sonst Bestätigung), «Zurücksetzen» holt das erkannte Feld zurück. | Testerin: behoben. | nicht erneut geprüft |
| B15 | Geteilte Seite nicht nach Zielbild | behoben (a3fab6c, 678f9af): Vereinskopf mit «geteilt von», Szenentitel, Umschalter Video | Taktik pro Torszene und Minifeld in der Liste aus den gemessenen Positionen (nur mit bestätigtem Feld; sonst leeres Feld). Test: test_shared_goal_scene_carries_its_tactics_camera. | Testerin: behoben. |
| B16 | «Fürs Team» enthält nicht die drei Dinge | behoben (a3fab6c): Entwurf aus den drei Dingen (je Notiz, dann genau seine Szenen, keine Doppelten); Seed gleich. | Testerin: behoben. | nicht erneut geprüft |
| B17 | Teilen: Extra-Dialog, Link nur einmal sichtbar | behoben (a3fab6c): «Link teilen» erstellt und kopiert in einem Schritt, Link bleibt sichtbar und abrufbar (verschlüsselt gespeichert, Migration 0043), «Link sperren». e2e `collection.spec`. | Testerin: teilweise. Danach: behoben (44df486): Seite zeigt den neuen Link sofort. | Testerin: behoben. |
| B18 | «Suchen» öffnet die Schnellsuche | behoben (07790d7): Knopf «Suchen» öffnet die Szenen-Suche mit Fokus. | Testerin: behoben am Desktop, **neu kaputt** am Handy. Danach: behoben (e5aaaf1): Lupe in der Handy-Kopfzeile, Szenen öffnet mit Fokus. | Testerin: behoben. |
| B19 | Suchfeld versteht keine Sätze; Rohwerte | behoben (07790d7): Sätze werden Chips (de, fr, en); Kacheln mit Wörtern statt Rohwerten. | Testerin: teilweise. Danach: behoben (694d821): Gegner («gegen Stäfa») und Nummer («Nummer 11», auch über den Kader). | Testerin: behoben. |
| B20 | «letzte 3 Spiele» meint mit Video | behoben (07790d7): Chip heisst «letzte 3 mit Video». | Testerin: behoben. | nicht erneut geprüft |
| B21 | «Alle 24 abspielen», «Als Tabelle» | behoben (e779fe1): «Alle n abspielen» spielt alle Szenen der Antwort über die Spiele hinweg als Folge im Vollbild; «Als Tabelle» zeigt dieselbe Antwort als Zeilen im selben Screen (`?view=table`); die alte Pivot-Tabelle bleibt unter `matrix?pivot=1`. | Testerin: behoben. | nicht erneut geprüft |
| B22 | Spieltag ist die alte Detail-Erfassung | behoben (07790d7): grosse Tasten nach Zielbild, «Bisher», «Pro Spielerin erfassen» führt zur Detail-Erfassung. | Testerin: teilweise. Danach: behoben (1d90026, N14). | Testerin: behoben. |
| B23 | Tab Zahlen ist die alte Statistikseite | behoben (43d69c9, 3d540ec): Feld- und Tor-Tabelle, Gegentore nach Position, «Ziel im Tor» als schlichtes Raster, Phasen mit Quelle, Würfe/Quote nur mit erfassten Fehlwürfen, Rest hinter «Alle Zahlen». Jede Zahl (Tore, 7 m, 2 Min, Würfe, Paraden, Gegentore) öffnet ihre Szenen unter der Tabelle; Spalte «Bestätigt», wenn alle Tore der Person von Hand markiert oder bestätigt sind. Vergleich `ux1-zahlen*.jpg`. | Testerin: teilweise. Danach: behoben (e5aaaf1): «Bestätigt» nach Person. | Testerin: behoben. |
| B24 | «Übernehmen» wartet ohne Wort; Neu laden überspringt Schritt 2 | behoben (e779fe1): nur der gewählte Knopf dreht, Satz «Wir holen Spiele, Kader und Tabelle …»; Schritt 2 bleibt nach Neu laden, bis bestätigt oder «Das ist nicht mein Team». | Testerin: teilweise. Danach: behoben (faa1e82, N03). | Testerin: behoben. |
| B25 | Registrierung: Fehler auf Englisch, Bedingungen nicht verlinkt | behoben (e779fe1): Prüfung im Formular in der eigenen Sprache an jedem Feld, Kästchen markiert; «Nutzungsbedingungen» und «Datenschutzerklärung» verlinkt (handball-ai.ch/agb, /datenschutz). | Testerin: behoben. | nicht erneut geprüft |
| B26 | Erster Screen ohne Aufgabe | behoben (e779fe1): beim letzten Spiel ohne Video Hauptknopf «Video hochladen», daneben «Demo-Spiel ansehen»; Zwei-Faktor als Punkt am Konto (B48). | Testerin: behoben. | nicht erneut geprüft |
| B27 | Verein von Hand: Vierschritt-Assistent mit Einladungen | behoben (0e8eb3f): zwei Schritte, 1. Name und Trikot (acht Trikots wie beim handball.ch-Weg; Land, Wappen, eigene Farbe hinter «Mehr»), 2. Team, dann «Zum Team». Kader auf der Teamseite, Einladungen unter Verein › Teams und Rollen (beides unverändert vorhanden). | Testerin: behoben. | nicht erneut geprüft |
| B28 | Leerer Verein: Formular-Karte, geratene Gegnerfarbe, falscher Leer-Satz | teilweise (e779fe1): Szenen sagen «Szenen gibt es nach dem ersten Video.»; die Gegnerfarbe wird nur gespeichert, wenn jemand sie wählt (war schon so), die Vorschau zeigt aber noch Rot; das Formular als Start ist geblieben. | Testerin: nicht geprüft. | Testerin: teilweise (Szenen «0 Szenen aus 0 Spielen» mit Chips). Danach: behoben (36b2165, 69e8b53): ein Satz und «Video hochladen», Sammlungen und Spielzüge in der Seitenspalte; mit einer Frage (?q) bleibt die Suche. e2e `layout.spec`. |
| B29 | Falsche oder kaputte Datei: keine Erklärung | behoben (e779fe1, 2cd4bf3): Erklärung und «Andere Datei wählen»; Glocke und Mail bei fehlgeschlagener Analyse oder Datei, mit Gegnername. | Testerin: teilweise. Danach: behoben (140e4c5): Textdatei wird vor dem Upload abgelehnt, mit Satz. | Testerin: behoben. |
| B30 | Team wechseln auf einer Spielseite | behoben (e779fe1): auf Seiten eines Spiels, einer Sammlung oder eines Gegners führt der Wechsel zu den Spielen des neuen Teams. | Testerin: behoben. | nicht erneut geprüft |
| B31 | Gegnerfarbe nur über Umwege | behoben (3d540ec): ist die Farbe offen, fragt der Kopf mit fünf Trikots; ist sie bekannt, öffnet «Farbe von … ändern» im Kopf dieselben fünf Trikots, gespeichert beim Antippen. | Testerin: behoben. | nicht erneut geprüft |
| B32 | Alte Routen ohne Umleitung, zwei auf 404 | behoben (e779fe1): `matrix` → Szenen als Tabelle (Pivot unter `?pivot=1`), `scouting` → Gegner, `feed`, `schedule`, `consents`, `assignments` (Verein und Team) → Spiele, solange keine Teamfunktionen an sind (Spieler und Eltern erreichen sie immer); schon vorher: `assistant`, `library`, `search`, `live`, `marks`, `paper`, `profile`, `settings`. `/club/federation` ist kein 404 mehr (Verband-Seite oder Erklärung). Nicht umgeleitet, weil sonst Funktionen verschwinden: `presentations` (Handy-Fernbedienung), `playlists` («Im Team teilen» für Spieler), beides kann die Sammlung noch nicht; `training`, `drills`, `plays`, `official`, `join-requests` (laut SPEC 6 ausserhalb der Navigation, aber erreichbar). 404 im App-Rahmen (B53). | Testerin: behoben (mit Ausnahmen der Bau-Session). | nicht erneut geprüft |
| B33 | Einwilligung: Spieler vorbelegt | behoben (e779fe1): «Bitte wählen» zuerst, nichts vorbelegt; nach dem Senden Name gross bestätigt; Kästchen 24 px. | Testerin: behoben. | nicht erneut geprüft |
| B34 | Spielerseite und Kader im alten Aufbau | behoben (10d70c5): Spielerseite mit Seitenkopf (Name als Titel, Nummer als Zahl), ohne Torvorlagen und ohne Anwesenheit, «Fehler» heisst «Ballverluste»; «Kader bearbeiten» im Seitenkopf. | Testerin: teilweise. Danach: behoben (e5aaaf1, N12). | Testerin: behoben. |
| B35 | Mehr-Menü voller alter Funktionen | behoben (e779fe1): Spieltag-Einträge nur vor dem Resultat, «Vorbereitung» weg (lebt im Gegner), «Matchkarte» ist jetzt «Als Bild für den Chat» in Tab Spiel. Geblieben: PDF, Gegner, Daten austauschen, Bearbeiten, Löschen. | Testerin: behoben. | nicht erneut geprüft |
| B36 | Wörter im Tab Video | behoben (07790d7, e779fe1): Vereinsname statt «Wir», Positionen ausgeschrieben, «Minute 4 bis 11», ein «Teilen», «Person hervorheben». | Testerin: behoben. | nicht erneut geprüft |
| B37 | Upload-Dialog bietet «Training» an | behoben (e779fe1): «Spiel \| Training» nur mit Teamfunktionen. Spielformat bleibt wählbar. | nicht erneut geprüft |
| B38 | Öffentliche Startseite verspricht zu viel | behoben über Z1: ohne Sitzung führt «/» auf den öffentlichen Einstieg (/einstieg), die Versprechen stehen auf der Website (`apps/site`, eigene Session). | Testerin: behoben. | nicht erneut geprüft |
| B39 | Doppelte Rückennummer auf der Kamera | behoben (9b12b32): eine Nummer pro Team und Moment; im Demo trägt nur der Torschütze eine Nummer. Test `test_graphics.py`. | Testerin: behoben. | nicht erneut geprüft |
| B40 | Start: Nächster Gegner und Tabelle | behoben (10d70c5): drei Fakten aus der Tabelle (Rang und Punkte, Bilanz, Tore pro Spiel) und dem letzten Duell, darunter die Tabelle um beide Teams; ohne Tabelle und Duell nur Name und Datum, kein leeres Feld. | Testerin: teilweise. Danach: behoben (140e4c5): Gegner nur noch einmal. | Testerin: behoben. |
| B41 | Saison: Ballverluste mit Szenen, Rang fehlt | behoben (e779fe1, 10d70c5): Ballverluste ohne Szenen-Link; Rang im Titel oder in der Kopfzeile, sobald die Tabelle bekannt ist, Tabelle in der Seitenspalte. | Testerin: nicht geprüft. | Testerin: behoben. |
| B42 | Nächstes Spiel: Platzhalter, Kasten im Kasten | behoben (0e8eb3f): vor dem Spiel stehen Datum und Uhrzeit statt «-:-» im Kopf und im Streifen; Upload-Block ohne äusseren Kasten, Kamera-Auswahl hinter «Mehr». | Testerin: behoben. | nicht erneut geprüft |
| B43 | Verein: «Verein» dreimal, roher Farbwähler | behoben (0e8eb3f): Abschnitt «Name, Trikot und Wappen», acht Trikots mit Vorschau im Spielkopf, eigene Farben hinter einem Klick, «Wappen» statt «Logo». | Testerin: behoben. | nicht erneut geprüft |
| B44 | Ziele unter 44 px | teilweise (e779fe1): Team-Umschalter, «Video hochladen» in der Spielliste, Einwilligungs-Kästchen, Banner weg (B48). Namen im Team und Zahlen in Tabellen nicht. | Testerin: teilweise. Danach: behoben (140e4c5, 44df486): Feldecken 44 px, Zahlen in Tabellen 44 px; Rest wie Runde 1. | Testerin: teilweise (Namen in Teamlisten). Danach: behoben (685a605): Namen in Team-, Kader- und Saisonliste 44 px hoch. |
| B45 | Prüfen am Handy | behoben (e779fe1): «Später weiter» auf einer Zeile, «Weiss nicht» links wie die anderen Antworten. | Testerin: behoben. | nicht erneut geprüft |
| B46 | Anmelden und Registrieren als Karte | teilweise (e779fe1): keine Karten mehr (Anmelden, Registrieren, Passwort, Einladung); Keil und doppeltes «Anmelden» nicht angefasst. | Testerin: teilweise. Danach: teilweise (44df486): ein «Anmelden»; der Keil bleibt (Gestaltung des Seitenkopfs). | Testerin: teilweise (Keil). Danach: behoben (685a605): der Keil sitzt direkt unter dem Satz und dem Link, nicht mehr lose am Fuss. |
| B47 | Onboarding-Wörter | teilweise (e779fe1): «Team suchen», «Das ist mein Team», «Ist das dein Team?», «Personen im Kader». «Hauptrunde - M2-02» kommt so aus handball.ch. | Testerin: teilweise. Danach: behoben (140e4c5, N25): Liga statt Gruppen-Kürzel. | Testerin: teilweise («Hauptrunde»). Danach: behoben (36b2165), wie N25. |
| B48 | Zwei-Faktor-Banner auf jedem Screen | behoben (e779fe1): Punkt am Konto und Eintrag «Zwei-Faktor-Anmeldung einrichten» im Konto-Menü. | Testerin: behoben. | nicht erneut geprüft |
| B49 | Seitentitel fehlen | behoben (e779fe1): Team («Team · Herren 1») und Prüfen. | Testerin: teilweise. Danach: behoben (44df486). | Testerin: behoben. |
| B50 | «Zeichnen» statt «Unentschieden» | behoben (e779fe1): eigener Schlüssel `anlauf.drawResult`. | Testerin: nicht geprüft. | Testerin: nicht prüfbar (kein Unentschieden in den Daten). |
| B51 | Taktikkamera am Handy zu klein | behoben (e779fe1): unter 640 px die angegriffene Hälfte (Tab Video und «Punkt 1, geöffnet»). | Testerin: behoben. | nicht erneut geprüft |
| B52 | Szenen: Highlights-Satz falsch | behoben (e779fe1): «Vom Spiel gegen … gibt es noch keine Highlights.» mit Weg ins Spiel. Seitenleisten-Links bleiben (Spielzüge laut SPEC aus den Szenen erreichbar). | Testerin: behoben. | nicht erneut geprüft |
| B53 | 404 ohne Rahmen | behoben (e779fe1): unbekannte Adressen in der App zeigen den 404 im App-Rahmen mit Seitenkopf. | Testerin: teilweise. Danach: behoben (694d821, N18) für unbekannte Adressen; unbekannte Spiel-IDs antworten weiter mit 200 (gestreamter Rahmen). | Testerin: teilweise. Danach: behoben (879b7ad), wie N18. |
| B54 | Abmelden ohne Rückmeldung; Upload-Race im Seed | behoben (a3fab6c, e779fe1): «Du bist abgemeldet.»; das Anlegen des Videos committet jetzt vor der Antwort. Ursache vermutlich: die Transaktion der Anfrage endet erst nach dem Senden der Antwort, ein sofortiges `POST /videos/<id>/parts` fand das Video noch nicht. Lokal nicht nachgestellt. | Testerin: behoben. | nicht erneut geprüft |

## Second delivery: entry for older coaches (H01 to H14, Z1 to Z8)

Source: `docs/ux-test/runde1/EINSTIEG.md` on `claude/ux-test`. Sheet of the new way on the phone
with large text and the numbers against today: `docs/screens/anlauf/einstieg-ablauf.jpg`.

Correction (round 2, N03): the sheet's «0 s waiting without a sentence» was measured with the
federation's answers already cached. Measured again with a cold cache (team not asked before,
local stack, phone 390 px): before the change 9 to 16 s with only «…»; after it the sentence «Wir
holen die Spiele von handball.ch.» and the head with name and league after 0.2 s, the team with
rank and table after 2.0 s, the scorers after 9.3 s (they fill in while the coach reads). Warm:
team after 0.5 s.

| # | Befund | Status | Runde 2 | Runde 3 |
|---|---|---|---|---|
| H01 | Spieltag: Tasten über dem Spielerraster bei niedrigem Fenster | behoben (a6e9c4c): Kopf und Tasten kleben erst ab 600 px Höhe; e2e prüft 844×390 und 640×400 (fand vorher «Tor» über «11 Lina»). | Testerin: behoben. | nicht erneut geprüft |
| H02 | Kein Nutzen auf dem Start vor dem ersten Video | behoben (1fd89b2): Rang und Serie, Tabellenausschnitt, Torschützen aus den Spielberichten, nächster Gegner; Aufgabe «Video hochladen». | Testerin: behoben. | nicht erneut geprüft |
| H03 | App vor dem Konto nicht ansehbar, Demo-Spiel fehlt | behoben (0a0d447, 1fd89b2): öffentlicher Einstieg /einstieg mit dem eigenen Team und den drei Dingen eines Demo-Spiels als Beispiel; «Demo-Spiel ansehen» auf dem Start. | Testerin: behoben. | nicht erneut geprüft |
| H04 | Team beim ersten Besuch: alles fehlt | behoben (3b57453): vor dem ersten Video keine Fehlt-Aufnäher, «Von handball.ch.», eine Liste statt «Ohne Position», ein Satz zur Einwilligung. | Testerin: behoben. Danach: behoben (44df486): Einwilligungen einmal in der Seitenspalte, kein Aufnäher pro Zeile. | Testerin: behoben. |
| H05 | Erstes Video: keine einfache Anleitung, Beruhigung nie gezeigt | behoben (3b57453): drei Sätze offen und Link auf die Filmanleitung der Website, «Video wählen» am Handy, Kamera und Technik hinter «Mehr», nach dem Upload «Du kannst die Seite schliessen …», Balken nur vorwärts. | Testerin: teilweise. Danach: behoben (3153fe3, 140e4c5): Link mit /de/, Satz bleibt sichtbar. | Testerin: behoben. |
| H06 | Am Handy erfährt man nicht, dass die Analyse fertig ist | behoben (2cd4bf3): Glocke in der Handy-Kopfzeile; Mail und Mitteilung mit Spielnamen bei fertiger und gescheiterter Analyse und bei unlesbarer Datei. Test `test_support.py`. | Testerin: behoben, mit neuem Problem. Danach: behoben (729d38f, N05). | Testerin: teilweise («1 Fragen», Zahl anders als am Start). Danach: behoben (d629e44, A02): eine Zahl für Mail, Start und Prüfen (`graphics.open_checks`), «1 Frage», «2 Fragen» in drei Sprachen; Start mit einem Satz und einem Schritt. Tests `test_support`, `test_identity_sync`, e2e `first-video.spec`. |
| H07 | Upload-Dialog verlangt zwei Dinge auf einmal | behoben (3b57453): zuerst nur die Spiele, das letzte oben; «Anderes Spiel» als eigener Schritt mit Gegner und Datum, der Rest hinter «Mehr». | Testerin: behoben. | nicht erneut geprüft |
| H08 | Schrift zu klein | behoben (a76ae8e): `text-xs` 14 px, nichts Gelesenes unter 14 px, Mono-Beschriftungen 13 px in voller Tinte, Achsen 13 px, Rückennummern ab 14 px; ANLAUF.md 6 und design-lint. Gemessen auf dem Einstieg: 0 Textstellen unter 14 px. | Testerin: behoben. | nicht erneut geprüft |
| H09 | Nur-Symbol-Knöpfe; Teamname verschwindet | behoben (2cd4bf3, 3b57453, a76ae8e): «Video», «Teilen», «Mehr» mit Wort; Teamname zweizeilig, das Wappen weicht unter 360 px. Die Glocke bleibt ein Symbol mit Zahl. | Testerin: behoben. | nicht erneut geprüft |
| H10 | Wörter, die Hans nicht versteht | behoben (a76ae8e, frühere Blöcke): Wortliste abgearbeitet (Paradenquote, Angriffseffizienz, Belege anzeigen, Baustelle, Spielformat, Taktik, Quellen, Wie gerechnet, Anlauf bis zur Wurfposition, Daten austauschen, Mannschaft, Übernehmen, Systemstatus); Fachwörter der Technik stehen hinter «Mehr». Positionskürzel auf den Minifeldern (RA, RL) bleiben dort aus Platzgründen; ausgeschrieben in Listen und Titeln. | Testerin: teilweise. Danach: behoben (44df486, 140e4c5): «Statistik», «Daten exportieren und importieren», «Status der App», «Frei 3/1» ersetzt. | Testerin: teilweise («Hauptrunde»). Danach: behoben (36b2165), wie N25. |
| H11 | Vereinsname uneinheitlich | behoben (1fd89b2): Kopf, Telegramm und Kamera nennen das Team wie die Kopfzeile (Teamname, ausser er ist generisch wie «Herren 1»). Test `own-name.test.ts`. | Testerin: behoben. | nicht erneut geprüft |
| H12 | Antwort in Prüfen nicht zurücknehmbar | behoben (a76ae8e): «Zurück» öffnet die letzte Antwort, «Beantwortet» mit «Antwort ändern». | Testerin: behoben. | nicht erneut geprüft |
| H13 | Was sich beim ersten Besuch vordrängt | behoben (1fd89b2, 3b57453): kein Banner mehr; Zwei-Faktor erst mit Video oder zweiter Person, als Aufgabe auf der Team-Seite und im Konto-Menü, sieben Tage wegklickbar (OPEN_QUESTIONS Q-AUTH-2b). | Testerin: behoben. | nicht erneut geprüft |
| H14 | Saison-Verlauf: Beschriftungen stossen zusammen | behoben (a76ae8e): Namen auf den Platz gekürzt, voller Name als Titel. | Testerin: nicht geprüft. | Testerin: teilweise (−20 ohne Zahl). Danach: behoben (685a605, A10): Massstab passt sich dem grössten Unterschied an, Balken und Zahl bleiben im Bild. |
| Z1 | Alte Startseite der App | behoben (1fd89b2): «/» leitet Angemeldete in die App, alle anderen auf /einstieg (mit q, farbe, lang). Erledigt damit auch B38. | Testerin: behoben. | nicht erneut geprüft |
| Z2 | Linke Spalte Anmelden/Registrieren | behoben (1fd89b2): Logo, «Dein Spiel. Und drei Dinge zum Mitnehmen.», Link zur Website. | Testerin: behoben. | nicht erneut geprüft |
| Z3 | /einstieg übernimmt q, farbe, lang | behoben (1fd89b2): nichts wird zweimal gefragt; der Suchsatz erklärt das Produkt nicht neu. | Testerin: behoben. | nicht erneut geprüft |
| Z4 | Versprechen: Nachricht, Beispielspiel | behoben (2cd4bf3, 1fd89b2): Mail und Glocke; das Beispiel der drei Dinge gibt es wirklich, als Beispiel beschriftet. | Testerin: teilweise. Danach: behoben (729d38f, N05). | Testerin: teilweise («1 Fragen», Zahl anders als am Start). Danach: behoben (d629e44, A02): eine Zahl für Mail, Start und Prüfen (`graphics.open_checks`), «1 Frage», «2 Fragen» in drei Sprachen; Start mit einem Satz und einem Schritt. Tests `test_support`, `test_identity_sync`, e2e `first-video.spec`. |
| Z5 | Laufdistanzen, Pässe, Ball | behoben (9b12b32, 3b57453): xG und Ballbesitz ganz weg; Laufleistung nur aus Video, hinter «Alle Zahlen» und «geschätzt». Torvorlagen: siehe B34. | Testerin: teilweise. Danach: behoben (e5aaaf1): Ballbesitz und Angriffe weg. | Testerin: behoben. |
| Z6 | Dauer der Analyse | behoben (3b57453): keine «40 Minuten» mehr; Minuten nur gemessen am laufenden Job, sonst «Du bekommst eine Mail». | Testerin: behoben. | nicht erneut geprüft |
| Z7 | Eine Filmanleitung | behoben (3b57453): Link auf handball-ai.ch/aufnahme/, im Upload nur drei Sätze. | Testerin: teilweise. Danach: behoben (3153fe3, N06). | Testerin: behoben. |
| Z8 | Testphase und Preis | behoben (d19b47f, 3b57453): neue Vereine starten die Testphase aus plans.json ohne Zahlungsdaten (Schalter `trial_on_signup`, OPEN_QUESTIONS Q-BILL-TRIAL); Verein › Abo zeigt «Testphase bis …» und was danach gilt. | Testerin: behoben. | nicht erneut geprüft |

## Round 2 (UX test): N01 to N31

Source: `docs/ux-test/runde2/BEFUNDE.md` on `claude/ux-test` (171a47c). The column «Runde 2» in
the tables above gives the tester's check of round 1 and what was done after it.

| # | Befund | Status | Runde 3 |
|---|---|---|---|
| N01 | Spieltag ohne Netz nicht wieder zu öffnen (P1) | behoben (eb50931): Service Worker im neuen Spieltag, Seite, Tasten und Liste auf dem Handy; e2e offline | Testerin: behoben. |
| N02 | Offline-Eintrag doppelt | behoben (eb50931): Uploads einzeln, Server speichert pro Spiel und Handy-Kennung einmal; API-Test, e2e | Testerin: behoben. |
| N03 | Einstieg: 16 s nur «…» | behoben (faa1e82): Kopf und Satz nach 0,2 s, Team nach 2,0 s (kalt), «langsam» mit «Trotzdem speichern»; e2e | Testerin: behoben. |
| N04 | Tab Video nach erstem Video: alte Erfassung | behoben (729d38f): schlichte Bühne, Werkbank nur auf Wunsch; e2e mit neuem Video | Testerin: behoben. |
| N05 | Mail «drei Dinge» ohne drei Dinge | behoben (729d38f): Mail und Glocke nach Ergebnis, Start zeigt den nächsten Schritt; API-Tests | Testerin: teilweise («1 Fragen», Zahl anders als am Start). Danach: behoben (d629e44, A02): eine Zahl für Mail, Start und Prüfen (`graphics.open_checks`), «1 Frage», «2 Fragen» in drei Sprachen; Start mit einem Satz und einem Schritt. Tests `test_support`, `test_identity_sync`, e2e `first-video.spec`. |
| N06 | Filmanleitung ohne Sprachpfad | behoben (3153fe3): alle Website-Links mit /de, /fr, /en aus der Konfiguration; Test | Testerin: behoben. |
| N07 | Geteilte Minifelder unlesbar | behoben (3153fe3): eigener Massstab; Test | Testerin: behoben. |
| N08 | Handy: «Suchen» fehlt | behoben (e5aaaf1): Lupe in der Kopfzeile, Wort ab 440 px, Szenen mit Fokus; e2e | Testerin: behoben. |
| N09 | Team belegt: Sackgasse | behoben (3153fe3): Hinweis in der Vorschau, danach Stand und zwei Wege; e2e | Testerin: behoben. |
| N10 | Tippfehler finden nichts | behoben (694d821): ein Buchstabe Abstand, «Meintest du …?»; Test | Testerin: behoben. |
| N11 | Grosse Schrift: Namen und E-Mail laufen aus dem Bild | behoben (3153fe3): Umbruch nach «/», Streifen bricht um, E-Mail umbrechbar | Testerin: teilweise (Kopfzeile «S / G.»). Danach: behoben (5b392d4, A01): Name mit mindestens zwei Zeilen Platz, «Video» wird zum Plus, Wappen und Lupe weichen unter 360 px; e2e bei 300 px. |
| N12 | Wurfquote falsch, «Bestätigt» leer, 7 m 0/0 | behoben (e5aaaf1): Würfe ohne geblockte wie die Quote (BRIEF 4.8), 7 m leer ohne Versuch, «Bestätigt» nach Person; Tests | Testerin: behoben. |
| N13 | «1 Frage» wird zu sechs | behoben (140e4c5): «1 Frage offen, danach Fragen zu den Personen im Bild» | Testerin: behoben. |
| N14 | Spieltag: Uhr, Rückgängig, kleine Tasten, Link | behoben (1d90026): Spieluhr, «Zurücknehmen» (auch auf dem Server), «2 Minuten», «Time-out», «Link teilen»; API-Test, e2e | Testerin: behoben. |
| N15 | Anmeldelink 15 Minuten | behoben (3153fe3): 24 Stunden, einmal; OPEN_QUESTIONS Q-AUTH-LINK; Test | Testerin: behoben. |
| N16 | Spiel in der Zukunft verlangt das Video | behoben (140e4c5): öffnet auf Spiel mit «Vor dem Spiel», Gegnerfakten, «Spieltag starten» | Testerin: behoben. |
| N17 | Feldecken-Griffe zu klein | behoben (140e4c5): 44 px Trefferfläche, Fadenkreuz beim Ziehen | Testerin: behoben. |
| N18 | App-404 mit HTTP 200 | teilweise (694d821): unbekannte Adressen 404; unbekannte IDs unter bekannten Pfaden noch 200 | Testerin: teilweise (Spiel-ID 200). Danach: behoben (879b7ad): das Lade-Gerüst des ganzen Vereinsbereichs startete den Strom vor notFound(); es gilt nur noch für den Vereinsstart. Unbekannte Spiel-, Team- und Sammlungs-IDs antworten 404; e2e `layout.spec`. |
| N19 | Drosselung beschuldigt handball.ch | behoben (faa1e82) | Testerin: behoben. |
| N20 | Anrede mit dem Teil vor dem @ | behoben (729d38f): «Hallo»; Test | Testerin: behoben. |
| N21 | Gleiche Adresse: zweiter Verein | behoben (694d821) für den Weg mit Teamnamen (Team in den bestehenden Verein); ein anderes handball.ch-Team ist ein anderer Verein | Testerin: behoben. |
| N22 | Abgelaufener oder doppelter Link | behoben (694d821): angemeldet direkt weiter, sonst «Neuen Link an … schicken» mit derselben Teamwahl | Testerin: teilweise (kein Weg zur Teamwahl). Danach: behoben (879b7ad): «Zurück zur Teamwahl» mit dem gewählten Team, ein verstümmelter Link sagt «ungültig oder abgelaufen» statt «Felder prüfen»; e2e `entry.spec`. Echter Ablauf nach 24 Stunden weiter nicht nachgestellt. |
| N23 | Szenenfolge anders als Liste | behoben (694d821): Liste und Folge gleich (neuestes Spiel zuerst, im Spiel in Spielfolge) | Testerin: behoben. |
| N24 | Alte Sätze nach der Analyse | behoben (729d38f, 140e4c5): «Die Analyse ist fertig.», Schliessen-Satz bleibt sichtbar | Testerin: behoben. |
| N25 | Fachwörter «Hauptrunde - M1-01», «Frei 3/1» | behoben (140e4c5): Liga statt Gruppe, «3 (1 vom 7-m)»; Test | Testerin: teilweise («Hauptrunde - M1-01»). Danach: behoben (36b2165, A04): Liga statt Gruppencode in Saison, Onboarding, Eingang und bei neu importierten Spielen; ein Cup behält seinen Namen. Schon gespeicherte Spiele behalten ihren alten Wettbewerb. |
| N26 | Unbekannte Gegnerfarbe: leeres Kästchen | behoben (140e4c5): Frage mit fünf Trikots, auch wenn das Trikot ohne Farbe gespeichert ist | Testerin: behoben. |
| N27 | Beispiel der Website findet nichts | Website-Sache (erfundener Demo-Verein im Beispiel, an die Website-Session gemeldet); in der App sucht «Wädenswil Herren 1» jetzt den Verein über den Ort, Teamwörter («Herren», «1», «U15») stören nicht mehr; Test | Testerin: behoben. |
| N28 | Website und App widersprechen sich bei der Datei | geprüft: Ein Spiel kann mehrere Hauptdateien haben, Zeitleiste und Auswertung (drei Dinge, Szenen, Prüfen) laufen nur über die erste. App sagt das jetzt so; der Satz für die Website ist gemeldet | Testerin: behoben. |
| N29 | Neue Notiz landet ganz unten | behoben: «Notiz danach» an jedem Eintrag, das Feld öffnet sich dort und speichert an dieser Stelle; e2e | Testerin: behoben. |
| N30 | «Entfernen» ohne Rückgängig | behoben: «Entfernt. Rückgängig» für sieben Sekunden, «Entfernen» etwas abgesetzt; e2e | Testerin: behoben. |
| N31 | «eigene Tags» auf der Szenen-Seite | behoben: «Stichwörter» statt «Tags» | Testerin: behoben. |
| – | Legende «Weg zum Wurf» ohne gezeichneten Weg (Teil 3, Aufgabe 3) | behoben: die Legende zeigt nur, was gezeichnet ist | nicht erneut geprüft |

## Round 3 (UX test): A01 to A10

Source: `docs/ux-test/runde3/ABNAHME.md` on `claude/ux-test` (b3f6879): 44 behoben, 14 teilweise,
0 offen, 2 nicht prüfbar, 10 new findings without P1. The column «Runde 3» above gives the
tester's check and what was done after it.

| # | Befund | Status |
|---|---|---|
| A01 | Handy, grosse Schrift: Teamname «S / G.» (P2) | behoben (5b392d4): siehe N11; Glockenzahl neben der Glocke |
| A02 | Nach einem Video ohne Tore: zwei Zahlen, vier Sätze (P2) | behoben (d629e44): eine Zahl, ein Satz, ein Schritt; kein «Fürs Team» ohne Szenen; «Spielbericht hinzufügen» nur ohne Bericht (`has_report`); Liste «Analyse fertig, 2 Fragen offen» |
| A03 | Spieltag: Uhrzeit neben der Spieluhr | behoben (c72f425): Spielzeit der Uhr beim Eintrag, Uhrzeit klein dahinter (auf dem Handy, das erfasst hat) |
| A04 | «Hauptrunde - M1-01» in der Saison | behoben (36b2165): siehe N25 |
| A05 | Veralteter Hinweis bei «Mehr zum Spiel»; «Highlights teilen» vor dem Spiel | behoben (c72f425): Hinweis nennt, was drin ist; vor dem Spiel weder «Mehr zum Spiel» noch «Highlights teilen» |
| A06 | Prüfen nennt den Verein | behoben (c72f425): der Teamname wie überall (`ownName`) |
| A07 | Altes Produkt hinter Umwegen | teilweise (c72f425): Spielzüge, Sammlungen alter Art, «Zum Zeigen» und Gegner-Profil sagen in einer Zeile, dass sie aus der früheren Version stammen; Spielzüge ohne zweite Tab-Ebene, mit Weg zurück zu Szenen. Nicht neu gebaut, nichts gelöscht: Entscheid in OPEN_QUESTIONS Q-OLD-AREAS |
| A08 | Szenenfolge mit Videozeit | behoben (c72f425): Treffer tragen die Spielzeit (`clock_s`), die Folge zeigt sie wie die Kacheln |
| A09 | Platzhalter-Block beim Laden | behoben (c72f425): ohne Resultat bleibt die Stelle leer statt «-:-» |
| A10 | Negativer Balken ohne Zahl | behoben (685a605): siehe H14 |

## Real-video test (E01 to E12): the data-to-interface path

Source: `docs/ux-test/echttest/BERICHT.md` on the test branch (two NLB clips, code @ 1b62a5c).
Twelve «Fehler in Oberfläche und Datenweg», fixed without new recognition; the recognition's own
weaknesses are in OPEN_QUESTIONS.md (Q-REC-*).

| # | Befund | Status |
|---|---|---|
| E01 | Bestätigte Tore kommen nicht in «Spiel» und «Video» an | behoben (b573f30): die Grafik führt jedes bestätigte Tor, auch ohne Wurfposition und Nummer (shot = null); das Setzen des Anwurfs rechnet clock_s fürs ganze Video nach. Resultat, Verlauf, Torliste und Szene da; Bündel und Minifeld zeigen «ohne Position». Tests `test_a_confirmed_goal_without_spot…`, e2e `real-normal.spec` |
| E02 | Taktikkamera sagt «keine Positionen», obwohl Spuren da sind | behoben (b573f30): Positionen, sobald das Feld bestätigt ist und die Szene Spuren hat; fehlt die Spielzeit, die Videozeit (video_s). vitest `cameraScene` |
| E03 | Verschobene Feldecken lassen sich nicht speichern (422), Fehler verschluckt | behoben (d75afc2): die API nimmt Bildpunkte ausserhalb des Bildes; eine Antwort zählt nur, wenn gespeichert wurde; Fehler werden angezeigt. Solange reprojection_px 0 ist, gilt das Feld nie als sicher. Tests: Ecken ausserhalb, e2e |
| E04 | Vierter Griff nicht erreichbar, Hallenbild klein, Linien dick | behoben (d75afc2): Feldfrage über die volle Breite, Bild zoombar, Linien 2 px halbtransparent; eine Ecke ausserhalb hat ihren Griff am Rand auf ihrer Linie. vitest `handleAt` |
| E05 | «Wer ist das?» ohne Rahmen (Panorama-Homographie aufs bewegte Bild) | behoben (ad434ff): Personenfragen nur mit fester Kamera, wo die Bild-Homographie passt; bei schwenkender Kamera nicht gestellt. Offen: Rahmen mit Kamerabewegung (Q-REC-PERSONBOX) |
| E06 | «Analyse fertig», während sie läuft | behoben (ad434ff): die Grafik trägt den Analysezustand; «fertig» nur bei ready, in Video-Tab, Start und Liste |
| E07 | Zahl der Fragen widerspricht sich; Wurf-Kandidaten gezählt, nie gefragt | behoben (ad434ff): eine Quelle (die checks des Servers) für Mail, Zähler und Prüfen; Wurf-Kandidaten zählen nicht; 51 Fragen auf das Nötige gekürzt, der Rest «Wenn du magst: n weitere». Test `test_one_question_per_moment…` |
| E08 | «Die Tore aus dem Spielbericht stehen schon im Verlauf» ohne Bericht | behoben (ad434ff): der Satz nur mit Spielbericht |
| E09 | Trikotfarbe aus dem Einstieg gilt nicht fürs Spiel; erfundene Gegnerfarbe an die Analyse | behoben (e7fd773): neues Spiel nimmt die Vereinsfarbe; die Gegnerfarbe geht an die Analyse nur, wenn gesagt; sonst vor dem Hochladen abgefragt. Test `test_a_new_match_takes_the_club_colour…` |
| E10 | Nach bestätigten Toren kein Resultat im Kopf; Achse 0 bis 60 | behoben (b573f30): die Tore im Video als Resultat («Tore im Video»); der Verlauf über die Minuten, die das Video abdeckt (span). e2e `real-normal.spec` |
| E11 | Hallenname geraten («Horgen Waldegg») | behoben (e7fd773): die übliche Heimhalle hilft nur beim Übertragen des Feldes, wird nicht als Hallenname gezeigt. Test `test_halls` |
| E12 | Überlappende Kandidatenfenster: ein Tor doppelt | behoben (ad434ff): überlappende Fenster sind ein Moment, einmal gefragt und gezählt; ein Moment mit bestätigtem Tor nicht erneut. Test `test_one_question_per_moment…` |

Plus: der Normalfall (Analyse findet kein Tor, Kandidaten vorhanden) als e2e `real-normal.spec`:
hochladen, Analyse, Prüfen (Feld, Anwurf, drei Tore), danach Resultat, Verlauf, Torliste und
Positionen.

## Second real-video test (F3 to F6 and smaller findings)

The report listed F3 to F6 by name; F1 and F2 were not part of it (nothing open under these
numbers here). Commits: 8d4c92c (F4), 8aa9aa3 (F3, F6, track times in the API), 649256c (F5),
86929b1, 68c7e3d (smaller findings).

| # | Befund | Status |
|---|---|---|
| F4 | Drei von acht Toren nie gefragt (überlappende 14-s-Fenster als ein Moment, Ketten) | behoben (8d4c92c): derselbe Moment nur bei Torzeiten unter 5 s Abstand und derselben vorgeschlagenen Seite, gemessen am ersten Kandidaten der Gruppe; keine Ketten; jeder Kandidat steht in checks oder more_checks. Test `test_goals_twelve_seconds_apart_are_two_goals` mit den acht Zeiten |
| F3 | Nach verschobener Ecke hält Prüfen die alte Liste, «Alles geprüft» trotz offener Fragen | behoben (8aa9aa3): nach dem Feld-Speichern wartet Prüfen sichtbar («Das Feld wird übernommen …»), lädt die Fragen des Servers neu; «Alles geprüft» nur, wenn der Server nichts mehr offen meldet. Antworten auf Tore überleben eine neue Analyse (neue Kandidaten im selben Moment werden nicht neu angelegt). Tests `test_answers_survive_a_new_analysis_after_a_moved_court`, e2e `real-normal.spec` «a moved corner» |
| F5 | Taktikkamera zeigt mehr Punkte als gleichzeitig Spuren existieren | behoben (8aa9aa3, 649256c): der Szenen-Endpunkt liefert pro Spur Zeitstempel (ts); gezeichnet wird eine Spur nur, solange sie existiert, mit Ein- und Ausblenden. vitest `camera-presence` (zu keinem Zeitpunkt mehr Punkte als gleichzeitig existierende Spuren) |
| F6 | Quellenzeile nennt «Spielbericht» ohne Spielbericht | behoben (8aa9aa3): die Grafik trägt has_report (Tore aus handball.ch oder Papierbericht); «Spielbericht» nur dann. Tests `test_graphics`, `test_events` |
| Start | Nach fertiger Analyse gehört das Spiel in den Kopf | behoben (68c7e3d): die Grafik trägt analysis_at; ein Spiel mit frischer Analyse (bis 7 Tage) steht im Kopf, bis es geöffnet wurde, und solange es offene Fragen hat, mit Resultat aus dem Video und nächstem Schritt. vitest `fresh-match`, e2e `real-normal.spec` |
| Spiel-Tab | Direkt nach der Analyse leer | behoben (68c7e3d): der eine Satz und «n Fragen beantworten». e2e `real-normal.spec` |
| Video-Tab | Zeitstrahl über 60 Minuten, fünftes Tor fehlt in der Szenenliste | behoben (68c7e3d): der Zeitstrahl läuft über die Minuten des Videos (span, beschriftet «Minute a» und «Minute b»); ein kurzes Video ist eine Phase mit allen Toren. e2e `real-normal.spec` |
| Kopf 1280 px | «Tore im Video» halb verdeckt | behoben (68c7e3d): auf breiten Schirmen über dem Resultat, nicht mehr unter ihm auf dem Verlauf |
| Torfrage | Ohne suggested_side ein Knopf vorgewählt | behoben (8aa9aa3): ohne Vorschlag ist kein Knopf hervorgehoben |
| Szene zeigen | Öffnete die Szene nicht im Video-Tab | behoben (68c7e3d): «Szene zeigen» im Spiel-Tab öffnet den Video-Tab an dieser Szene (?tab=video&scene=). e2e `real-normal.spec` |
| Mail | Link aufs Spiel statt auf Prüfen | behoben (86929b1): bei offenen Fragen führt der Link nach Prüfen. Test `test_identity_sync` |
| Restzeit | Anfangs zu tief | behoben (68c7e3d): erst nach dem ersten Viertel der Stufe, als Spanne nach oben («noch etwa 4 bis 6 Minuten») |
| Konsole | MISSING_MESSAGE search.type_yellow_card | behoben (86929b1): alle zwölf Ereignisarten der API in de-CH, en und fr; die Szenenliste übersetzt sie auch statt den Rohnamen zu zeigen |

## Third real-video test (G1 to G9)

Confirmed fixed on the real video in the third test: F3, F6, the start head, the step in the
Spiel tab, the timeline, «Tore im Video», no preselected answer, «Szene zeigen», the mail link,
the time left, MISSING_MESSAGE, and E01 to E07, E09, E11. Commits: 03cebf8 (G1), b0108c6 (G2),
0ee59dc (G3), 57ab015 (G4, G5), 493534d (G6), e75bcee (G7), 3bbc512 (G8), d291be1 and 5fa23d2
(G9).

| # | Befund | Status |
|---|---|---|
| G1 | Echte Tore nur unter «Wenn du magst», Resultat und «Alles geprüft» sehen endgültig aus | behoben (03cebf8): solange Tor-Momente offen sind, kein «Alles geprüft»; nach den wichtigsten Fragen «Die wichtigsten Momente sind geprüft. n weitere könnten Tore sein.» mit «Weiter prüfen» als Hauptknopf und «Später». Kopf auf Start, Spiel und Video: «bisher bestätigt · n Momente offen», der Zähler «Prüfen n» bleibt; erst ohne offene Momente «Tore im Video». Die Mail nennt die wichtigsten Fragen und sagt, dass weitere Momente folgen können. Personenfragen gesondert. Tests `test_support` (Mail), e2e `real-normal.spec` |
| G2 | Ein Tor in zwei Fragen, doppelt bestätigbar | behoben (b0108c6): liegt ein bestätigtes Tor derselben Seite im Ausschnitt der Frage, nennt die Frage es («In diesem Ausschnitt liegt das Tor von 2:06 …») mit «Nein, dasselbe Tor» als Hauptknopf und «Ja, noch ein Tor». Der Ausschnitt liegt enger: 10 s vor der Kandidatenzeit bis 2 s danach. vitest `goal-window`, e2e `real-normal.spec` |
| G3 | Taktikkamera: Zuschauer und Bank als Spieler, Fenster nach dem Tor, gespiegelt | behoben (0ee59dc): nur Positionen im Feld (1 m Rand); die Szene läuft von 8 s vor dem Tor bis 2 s danach; nicht mehr gespiegelt, die rechte Hälfte hat eigene Ansichten (die Bündel bleiben normiert); unter der Kamera «Positionen geschätzt; es können Personen neben dem Feld darunter sein.». Q-REC-OFFCOURT notiert. Tests `test_scene_shows_only_the_court_unmirrored`, Fenster in `test_graphics`, vitest `camera-view`, e2e |
| G4 | Zweite Mail nach jedem gespeicherten Feld | behoben (57ab015): der Lauf nach einer Feldkorrektur in Prüfen schickt weder Mail noch Mitteilung. Test `test_answers_survive_a_new_analysis_after_a_moved_court` |
| G5 | Gemerkte Gegnerfarbe geht nicht an die Analyse | behoben (57ab015): die für den Gegner gemerkte Farbe geht als away-Kit an die Analyse. Test `test_the_remembered_opponent_colour_goes_to_the_analysis` |
| G6 | «Wer trifft» der Saison zählt anders als der Start | behoben (493534d): mit Verknüpfung zu handball.ch zeigt die Saison dieselbe Zählung aus den Spielerstatistiken der Spielberichte wie der Start; ohne Verknüpfung die eigenen Ereignisse. e2e `season-scorers.spec` |
| G7 | «Neues Spiel» füllt die Gegnerfarbe rot vor, Warnung «Ähnliche Farben» | behoben (e75bcee): die Gegnerfarbe bleibt leer (gestricheltes Trikot), bis jemand sie wählt, und wird bis dahin nicht verglichen. e2e `family.spec` |
| G8 | Übergangener Anwurf bleibt als «Prüfen 1» ohne Ausweg | behoben (3bbc512): Antwort «Der Anwurf ist nicht im Video», danach optional «Welche Spielminute zeigt der Anfang?» (leer erlaubt); ohne Anwurf zeigt der Video-Tab den Zeitstrahl über die Videozeit und die Szenen mit Videozeiten, jede einmal. Tests `test_a_throw_off_not_in_the_video_is_not_asked_again`, e2e `real-normal.spec` «a moved corner» |
| G9 | Reste: «So rechnen wir» nennt den Spielbericht ohne Bericht (E08); Spielverlauf 0 bis 60 (E10); Feldfrage am Handy | behoben (d291be1, 5fa23d2): ohne Bericht «Die Tore kommen aus dem Video …»; der Spielverlauf unter «Mehr zum Spiel» läuft über die Minuten des Videos; die Feldfrage bei 390 px selbst geprüft: alle Griffe auf dem Bildschirm, ein Finger zieht die Ecke (Touch-Ereignisse), die Seite scrollt dabei nicht. e2e `real-normal.spec` |

Open (recognition, not interface): Q-REC-OFFCOURT (people beside the court, goalkeepers in
another colour), Q-REC-SIDES, Q-REC-CANDTIME, Q-REC-SCOREBOARD, Q-REC-PERSONBOX (see
OPEN_QUESTIONS.md).

## Fourth real-video test (H1 to H10)

Report: docs/ux-test/echttest/BERICHT.md, «Vierter Durchlauf». G1 to G8 are confirmed on the real
video; the court question on a phone (part of G9) was not fixed and is fixed now.

| # | Finding | Status |
|---|---|---|
| H1 | Corner handle under the zoom button, the enlarged court could not be moved (390 px) | fixed (434799e, 7dd0a09) |
| H2 | Goal question named the scoreboard although none was read | fixed (434799e) |
| H3 | «Beantwortet» without times | fixed (434799e) |
| H4 | Prüfen head «0 Fragen» with open moments; list row without the open moments | fixed (434799e) |
| H5 | Longest phase without an own goal counted from the whistle, not from the video's start | fixed (bd9fa7a) |
| H6 | Zahlen intro named a match report that does not exist | fixed (bd9fa7a) |
| H7 | Confirmed goals get no shot position, the three things never appear | open: «Von wo?» in Prüfen (Q-REC-SHOTZONE) |
| H8 | One scene with three different times (8:15, 8:14, video 0:15) | open |
| H9 | Season: 12 matches in the head, 8 in the table, the last 10 in the course, unsaid | open |
| H10 | «Welche Spielminute zeigt der Anfang?» is ambiguous at 8:15; «Zurück» at question 1 | open |

## Tests

Round 3: API 352 passed (3 deselected). Web unit tests 205 passed. ESLint clean again (11
warnings from before removed). e2e: the full run had 6 failures; 5 came from this round's
changes (Szenen before the first video hid «Mehr», the side links and the asked search; the inbox
test expected the group) and are fixed; `shots.spec` failed once in the full run and passed in the
rerun with the other five (11 passed), so it looks timing-dependent, not changed here. New tests:
e2e `first-video.spec` (A02), `layout.spec` (A01 at 300 px, N18 404s, B28), `entry.spec` (N22),
`matchday-offline.spec` (game time, A03); pytest mail plural and one count (`test_support`,
`test_identity_sync`), `has_report` (`test_events`), league name (`test_official_names`),
`clock_s` in search hits (`test_tags`); vitest `headName`. axe (WCAG 2.2 AA): 15 app pages incl.
Spielzüge in two kit colours at 1280 and 390 px, 60 of 60 clean; sign-in, registration, the
invalid link page and the public entry clean.

Round 2: API 350 passed; web unit tests 204 passed; e2e 46 passed (the rest are skips by project:
phone-only or desktop-only flows). New tests: `test_a_mark_uploaded_twice_is_stored_once_per_match`,
`test_the_last_mark_can_be_taken_back`, `test_prufen_asks_for_the_throw_off_until_it_is_set`,
`test_after_the_analysis_the_mail_promises_only_what_is_there`, `test_a_goal_names_its_scorer_for_the_confirmed_column`,
`test_a_shirt_number_finds_the_events_of_that_player`, `test_a_typo_is_a_letter_away`,
`test_the_sign_in_link_lasts_a_day_and_says_so`, `test_public_config_gives_the_website_and_support_addresses`;
web `season-line`, `mini-field`, `video-file`, `scene-words`, `telegram`, client-core `forget`; e2e
`matchday-offline.spec` (network off, clock, take back), `phone-search.spec`, `entry.spec` (slow federation,
occupied team), `match.spec` (new video: no old capture tools).

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
