# UX-Test Runde 2: Nachprüfung der Befunde aus Runde 1

Stand: 13. November 2026. App vom Branch `claude/trikot-ui` (Commit 465efb4), in `claude/ux-test`
zusammengeführt; Website vom Branch `claude/site-anlauf` (Commit ad87ce5), statisch gebaut und
lokal auf Port 3100 ausgeliefert, App-Adresse auf den lokalen Stack. Frische Datenbank, `make seed`,
Produktions-Build, Playwright mit Chromium (Desktop 1280, Handy 390, grosse Schrift als 300
CSS-Pixel bei Faktor 1,3).

Grundlage der Bau-Session: `docs/ux-test-status.md` auf `claude/trikot-ui`. Jede Zeile unten ist
von mir nachgestellt, nicht übernommen. Wo ich etwas nicht erneut prüfen konnte, steht das so da.

Status: **behoben** (bestätigt) · **teilweise** (was fehlt) · **offen** (nicht behoben) ·
**neu kaputt** (durch die Änderung schlechter geworden) · **nicht geprüft** (mit Grund).
Neue Befunde dieser Runde stehen in `BEFUNDE.md` (N01 …); hier wird nur auf sie verwiesen.

## Zuerst: alle P1 aus Runde 1

| # | Befund Runde 1 | Status | Nachgestellt, Beobachtung | Bild |
|---|---|---|---|---|
| B01 | Szenen zu Punkt 1 nicht erreichbar | **behoben** | Start › «9 Szenen» öffnet `?tab=video&thing=1`: Liste «Gegentore über rechts aussen · 9 Szenen», laufende gelb, «Nächste Szene» springt auf «Szene 2 von 9». Desktop und Handy. | `shots/v01-szenenfolge-punkt1.jpg` |
| B02 | «Suchen» mit Frage endet beim Assistenten | **behoben** | «Suchen» öffnet die Szenen-Suche mit Fokus; die Frage der Aufgabe ergibt «24 von 66 Gegentoren über rechts aussen». `/assistant?q=` leitet mit der Frage um. Grenzen der Worterkennung siehe B19. | `shots/v02-suchen-frage.jpg` |
| B03 | Spieltag: Einträge nach Neu laden weg | **behoben** (online) | «Tor wir», «Tor HSG Rheinau», Neu laden: 1:1 und beide Einträge bleiben. Offline siehe **N01** (Seite lässt sich ohne Netz nicht mehr öffnen) und **N02** (doppelter Eintrag nach Offline). | `shots/v22-spieltag.jpg` |
| B04 | «Am Bildschirm zeigen» tut nichts | **behoben** | Vollbild «Rückzug und rechter Flügel · 1 von 27», Notiz als Tafel, «Zurück», «Weiter», «Vollbild», «Schliessen». | `shots/v04-bildschirm-zeigen.jpg` |
| B05 | Sammlung: keine Notiz, nichts entfernen | **behoben** | «Notiz dazu», «Nach oben», «Nach unten», «Entfernen» pro Eintrag. Titel ändern nicht einzeln geprüft. | – |
| B06 | Sprache nicht wechselbar | **behoben** | Kontomenü: «Deutsch · English · Français»; auch im Einstieg und auf der Anmeldung. | `shots/v06-sprache-kontomenue.jpg` |
| H01 | Spieltag: Tasten verdecken Spieler bei niedrigem Fenster | **behoben** | Detail-Erfassung bei 844 × 390 und 640 × 400: an der Stelle von «1 Andrin» liegt «1 Andrin». | `shots/vh01-spieltag-quer.jpg` |
| H06 | Am Handy keine Meldung «fertig» | **behoben**, mit neuem Problem | Glocke in der Handy-Kopfzeile; Mail «Die drei Dinge gegen TSV Fortitudo Gossau 2 sind da» kam nach 13 s. Die Mail kommt aber auch, wenn keine drei Dinge gefunden wurden (**N05**). Bei unlesbarer Datei Mail «Das Video gegen … liess sich nicht lesen». | `shots/e02-hans-spiele-bis-mail.jpg` |

## Die Punkte, die die Bau-Session ausdrücklich zum Nachprüfen nennt

| Punkt | Ergebnis |
|---|---|
| Prüfen mit Feld-Ecken (Griffe, «Passt», «Zurücksetzen») | **funktioniert**: Viereck über dem Hallenbild, vier gelbe Griffe, Ziehen mit der Maus und am Handy, «Zurücksetzen» wird nach dem Ziehen aktiv, «Passt» speichert. Griffe nur 22 × 22 px (**N17**). Nach «Passt» wachsen die Fragen von 1 auf 6 (**N13**). `shots/v13-feld-ecken.jpg` |
| Anwurf in Prüfen | **nicht geprüft**: Das Demo stellt keine Anwurf-Frage; nach dem Testvideo kamen «Wer ist das?»-Fragen. |
| Tab Video ohne Assistent; findet man «Einrichten von Hand»? | **teilweise**: Beim Demo-Spiel ist der Tab Video sauber, «Einrichten von Hand» steht dort nicht und auch nicht im Mehr-Menü. Nach dem **ersten eigenen Video** zeigt der Tab Video am Handy dagegen wieder die alte Erfassung (Unter-Tabs «Ereignisse · Abwehrsysteme · …», «Ereignis erfassen», «Tastenkürzel», «Anwurf setzen»), darüber der Link «Einrichten von Hand: Feld, Anwurf, Tore, Personen» (**N04**). |
| Geteilter Link mit Video \| Taktik und Minifeldern | **teilweise**: Vereinskopf, «geteilt von Sandra», Abschnitte nach Punkt, laufende Szene gelb, «Nächste Szene», «Alle 24 Szenen», Gültigkeit. Umschalter heisst «Video \| Feld von oben» und erscheint erst mit bestätigtem Feld (richtig). Die Minifelder in der Liste sind unlesbare blaue Flächen (**N07**). `shots/v15-geteilt-feld.jpg` |
| Verein von Hand in zwei Schritten am Handy | **behoben**: «Kein Team gefunden» › «Mit dem Teamnamen weiter» › Teamname › E-Mail. `shots/v27-hand-zwei-schritte.jpg` |
| Nächster Gegner mit drei Fakten und Tabelle (handball.ch-Team) | **teilweise**: Bei SG Wädenswil/Horgen stehen unten «Rang 6, 8 Punkte aus 7 Spielen · 3 Siege, 2 Unentschieden, 2 Niederlagen · Wirft im Schnitt 30 Tore» und die Tabelle um beide Teams. Weiter oben steht derselbe Gegner ein zweites Mal, nur mit Datum. `shots/vh02-start-echter-verein.jpg` |
| Datum statt Platzhalter vor dem Spiel | **behoben**: «Di., 17. Nov. 19:30» im Streifen. Das Spiel öffnet aber im Tab Video und verlangt schon vor dem Anpfiff das Video (**N16**). `shots/v42-naechstes-spiel.jpg` |
| Zahlen öffnen ihre Szenen, Spalte «Bestätigt» | **teilweise**: Ein Klick auf «7» bei Tim Baumann zeigt «Tore: Tim Baumann» mit den Szenen und «Abspielen». Die Spalte «Bestätigt» ist bei allen leer, obwohl die Quellenzeile «42 von 44 Toren von dir bestätigt» sagt. `shots/v23-zahlen-szenen.jpg` |
| Gegnerfarbe im Kopf | **behoben**: «Farbe von TSV Thalwil-Gattikon ändern» öffnet fünf Trikots im Kopf. Ist die Farbe offen (echter Verein), steht ein leeres Kästchen mit demselben Link statt der Frage «Welche Farbe trägt …?» (P3, N26). `shots/v31-gegnerfarbe.jpg` |
| Verein mit Trikotwahl | **behoben**: «Name, Trikot und Wappen», acht Trikots, Vorschau im Kopf, eigene Farben hinter einem Klick. `shots/v43-verein-trikots.jpg` |
| Spielerseite | **teilweise**: Seitenkopf mit Name und Nummer, keine Torvorlagen, «Ballverluste». Wurfquote **85 %** bei 17 Toren aus 21 Würfen (richtig wären 81 %), «7 m 0/0» als Nullen (**N12**). `shots/v34-spielerseite.jpg` |

**Ehrlichkeit, gezielt gesucht** (alle Seiten, aufgeklappte Abschnitte):

| Gesucht | Ergebnis |
|---|---|
| xG | **weg** (nirgends sichtbar; nur noch Schlüssel in `messages`). |
| Ballbesitz in Prozent | als Prozent **weg**; hinter «Mehr zum Spiel» stehen aber weiter «Ballbesitz im Spielverlauf» und «Alle Angriffe … Angriffe aus den Positionen im Video erkannt, geschätzt» (siehe B08). |
| Läufe ohne Torzeiten | **weg** (Spiel nur mit Spielbericht: keine Läufe, kein Verlauf). |
| Positionen ohne bestätigtes Feld | **weg** auf Kamera und geteilter Seite. Geschätzte Wurfpunkte in Bündeln und Zonen bleiben sichtbar; die Legende «Weg zum Wurf, von dir bestätigt» steht auch, wenn kein Weg gezeichnet ist (P3). |
| «etwa 40 Minuten» | **weg**. |
| Laufleistung | nur hinter «Alle Zahlen», mit «geschätzt» und dem Hinweis, dass das Video weniger als eine Halbzeit zeigt. In Ordnung. |

## Alle übrigen Befunde

| # | Befund Runde 1 | Status | Beobachtung |
|---|---|---|---|
| B07 | Nur Spielbericht: erfundene Läufe | **behoben** | Kein Lauf, kein Verlauf, Block «Kein Video», Telegramm, drei Zahlen mit Quelle. `shots/v07-nur-spielbericht.jpg` |
| B08 | Tab Spiel: altes Produkt unter den drei Dingen | **teilweise** | Oben nach Zielbild (Aktionen, «Punkt 1, geöffnet», Telegramm, Zonen, drei Zahlen). Hinter «Mehr zum Spiel» unverändert alt: zweite Drei-Dinge-Liste mit «Daran arbeiten», «Daraus trainieren», «Übungen dazu», «Ballbesitz im Spielverlauf», «Alle Angriffe», «Laufleistung ansehen», «Feedback · Notizen 0 von 37 · weiter mit Andrin Gerber». «Dazu üben» fehlt. `shots/v08-tab-spiel.jpg`, `shots/v08b-mehr-zum-spiel.jpg` |
| B09 | «Spiel öffnen» öffnet Video; Tabs nicht in der Adresse | **behoben** | Standard Spiel; `?tab=zahlen` in der Adresse; Zurück wechselt den Tab. |
| B10 | Einrichtungs-Assistent im Tab Video | **teilweise** | Siehe oben: beim Demo weg, nach einem neuen Video wieder da (**N04**). |
| B11 | «Analyse läuft» spricht Technik | **behoben** | «Die Analyse läuft.», drei Schritte in Trainerwörtern. Danach erscheint aber noch der alte Satz «Analyse fertig. Statistik und Szenen stehen bereit.» (P3). |
| B12 | Positionen ohne bestätigtes Feld | **behoben** | Kamera zeigt «Stimmt das Feld? … Feld prüfen»; nach «Passt» erscheinen die Positionen. |
| B13 | Prüfen zeigt das Feld nicht | **behoben** | Viereck und Feldlinien über dem Bild. |
| B14 | «Ecken verschieben» verlässt Prüfen | **behoben** | Griffe im Prüfen-Screen (siehe N17 zur Grösse). |
| B15 | Geteilte Seite nicht nach Zielbild | **teilweise** | Aufbau stimmt; Minifelder kaputt (**N07**); Titel der Gegenstoss-Szenen gekürzt auf «Gegentor»; Zeiten eine Sekunde anders als in der App (35:50 statt 35:51). |
| B16 | «Fürs Team» enthält nicht die drei Dinge | **behoben** | Entwurf: Notiz «Punkt 1 …», dann die 9 + 4 + 11 Szenen, keine Doppelten. |
| B17 | Teilen: Extra-Dialog, Link einmal sichtbar | **teilweise** | «Link teilen» erstellt und kopiert in einem Schritt, «Link kopiert». Die Seitenleiste zeigt danach weiter «Noch nicht geteilt.» |
| B18 | «Suchen» öffnet Schnellsuche | **behoben** am Desktop, **neu kaputt** am Handy | Am Handy ist «Suchen» aus der Kopfzeile verschwunden (**N08**). |
| B19 | Suchfeld versteht keine Sätze | **teilweise** | Ereignis, Position und Zeitraum werden zu Chips. «Paraden gegen Stäfa» ergibt alle 41 Paraden, «Tore von Nummer 11» alle 72 Tore: Gegner und Nummern werden nicht erkannt. |
| B20 | «letzte 3 Spiele» meint mit Video | **behoben** | Chip «letzte 3 mit Video». |
| B21 | «Alle abspielen», «Als Tabelle» | **behoben** | Folge im Vollbild «24 Szenen aus der Suche · 1 von 24»; Tabelle im selben Screen («Als Kacheln» zurück). Die Folge beginnt mit «TV Rüti · 0:15», die Liste mit Thalwil 56:55 (P3). `shots/v21-folge.jpg` |
| B22 | Spieltag ist die alte Erfassung | **teilweise** | Grosse Tasten, «Bisher», «Pro Spielerin erfassen». Es fehlen «2 Minuten», «Time-out», «zurücknehmen» und «Link teilen»; die Uhr zeigt die Uhrzeit des Handys statt der Spielzeit (**N14**). |
| B23 | Tab Zahlen ist alt | **teilweise** | Feld- und Tor-Tabelle, Zonen, Ziel im Tor, Phasen; Zahlen öffnen Szenen. Spalte «Bestätigt» leer (siehe oben). |
| B24 | «Übernehmen» wartet ohne Wort | **teilweise** | Der alte Weg ist ersetzt. Im neuen Einstieg steht nach dem Antippen des Teams 16 Sekunden lang nur «…» (**N03**). |
| B25 | Registrierung: Englisch, Bedingungen | **behoben** | «Bitte gib deinen Namen ein.», «Das ist keine E-Mail-Adresse.», «Bitte akzeptiere die Bedingungen.» |
| B26 | Erster Screen ohne Aufgabe | **behoben** | «Video hochladen» als Hauptknopf, «Demo-Spiel ansehen». |
| B27 | Verein von Hand: vier Schritte | **behoben** | Zwei Schritte. |
| B28 | Leerer Verein: Karte, geratene Farbe | **nicht geprüft** | Ein Verein ganz ohne Spiele entsteht jetzt nur über «Mit dem Teamnamen weiter»; den leeren Start danach habe ich in dieser Runde nicht angesehen. Bau-Session: teilweise. |
| B29 | Falsche Datei ohne Erklärung | **teilweise** | Kaputtes Video: «Das Video liess sich nicht lesen. Diese Datei ist kein Video, das wir lesen können (MP4, MOV, MKV) …», «Andere Datei wählen», Mail. Eine Textdatei ergibt weiter «Etwas ist schiefgelaufen. Bitte versuch es nochmals.» mit «Fortsetzen». `shots/v29-textdatei.jpg` |
| B30 | Team wechseln auf Spielseite | **behoben** | Wechsel führt auf die Spiele der U17. |
| B31 | Gegnerfarbe über Umwege | **behoben** | Siehe oben. |
| B32 | Alte Routen | **behoben** (mit Ausnahmen der Bau-Session) | `matrix`, `assistant`, `scouting`, `feed`, `schedule`, `consents`, `assignments` leiten um; `/club/federation` zeigt «Verband». Geblieben wie angekündigt: `presentations`, `playlists`, `training`, `drills`, `plays`, `official`, `join-requests`. |
| B33 | Einwilligung: Spieler vorbelegt | **behoben** | «Bitte wählen» zuerst. |
| B34 | Spielerseite alt | **teilweise** | Siehe oben (**N12**). |
| B35 | Mehr-Menü | **behoben** | «Spielbericht als PDF, Gegner-Profil, Daten exportieren und importieren, Spiel bearbeiten, Spiel löschen». |
| B36 | Wörter im Tab Video | **behoben** | «Tor HC Zürichsee 5:08», «Rückraum rechts», «Minute 4 bis 11», ein «Teilen». |
| B37 | Upload bietet Training | **behoben** | Dialog zeigt nur Spiele ohne Video und «Oder ein neues Spiel anlegen». |
| B38 | Alte Startseite der App | **behoben** | `/` leitet ohne Sitzung auf `/einstieg` (mit `q` und `farbe`). |
| B39 | Doppelte Rückennummer | **behoben** | Auf der Kamera nur noch der Torschütze mit Nummer. |
| B40 | Start: nächster Gegner, Tabelle | **teilweise** | Tabelle und Fakten da; Gegner doppelt (siehe oben). |
| B41 | Saison: Ballverluste, Rang | **nicht geprüft** | Nicht erneut angesehen. |
| B42 | Nächstes Spiel: Platzhalter | **behoben** | Datum und Uhrzeit (siehe N16). |
| B43 | Verein: roher Farbwähler | **behoben** | Trikots. |
| B44 | Ziele unter 44 px | **teilweise** | Wie angekündigt; neu die Feldecken-Griffe 22 px (**N17**). |
| B45 | Prüfen am Handy | **behoben** | «Später weiter» einzeilig, Antworten links. |
| B46 | Anmelden als Karte | **teilweise** | Keine Karte mehr; Keil und doppeltes «Anmelden» geblieben (wie angekündigt). |
| B47 | Onboarding-Wörter | **teilweise** | «Hauptrunde - M1-01» steht jetzt sogar auf dem Start über der Tabelle. |
| B48 | Zwei-Faktor-Banner | **behoben** | Kein Banner; Punkt am Konto und Menüeintrag «Zwei-Faktor-Anmeldung einrichten · In sieben Tagen wieder erinnern». |
| B49 | Seitentitel | **teilweise** | Team und Prüfen ja; die Vollbild-Sammlung heisst nur «Handball Intelligence». |
| B50 | «Zeichnen» statt «Unentschieden» | **nicht geprüft** | Kein Unentschieden in den geprüften Daten. |
| B51 | Kamera am Handy zu klein | **behoben** | Angegriffene Hälfte, Punkte gross. |
| B52 | Highlights-Satz falsch | **behoben** | «Vom Spiel gegen TSV Thalwil-Gattikon gibt es noch keine Highlights. Im Spiel erstellen». |
| B53 | 404 ohne Rahmen | **teilweise** | Rahmen und Seitenkopf da; die Seite antwortet mit HTTP 200 statt 404 (P3). |
| B54 | Abmelden ohne Rückmeldung | **behoben** | «Du bist abgemeldet.» Upload-Race im Seed trat bei `make seed` nicht auf. |
| H02 | Kein Nutzen vor dem ersten Video | **behoben** | Start: «Rang 4. 4 Siege in Folge.», Tabelle, Torschützen aus 12 Spielberichten, nächster Gegner. |
| H03 | Nicht ansehbar vor Konto; Demo fehlt | **behoben** | Website mit Demo; `/einstieg` zeigt das eigene Team ohne Konto; «Demo-Spiel ansehen» auf dem Start. |
| H04 | Team-Alarm beim ersten Besuch | **behoben** | Vor dem ersten Video ohne Fehlt-Aufnäher. Nach dem ersten Video wieder «20 im Kader. Bei 20 fehlt noch etwas.» mit 20 × «Einwilligung fehlt» (so gewollt; für Hans dennoch ein Schreck direkt nach dem ersten Erfolg). |
| H05 | Erstes Video ohne einfache Anleitung | **teilweise** | Drei Sätze offen, «Video wählen». «Ausführliche Filmanleitung» zeigt auf `https://handball-ai.ch/aufnahme/`; die Website liefert die Seite unter `/de/aufnahme/`, `/aufnahme/` gibt 404 (**N06**). «Du kannst die Seite schliessen …» ist nur rund 4 Sekunden sichtbar, dann ersetzt vom nächsten Schritt. |
| H07 | Upload-Dialog: zwei Dinge auf einmal | **behoben** | Erst nur die Spiele, «Oder ein neues Spiel anlegen» als Link. |
| H08 | Schrift zu klein | **behoben** | Start und Spiel: nur noch «1 von 3» in 13 px Mono; Einstieg 0 Stellen unter 14 px; Laufleistung-Tabellenköpfe 13 px. |
| H09 | Nur-Symbol-Knöpfe | **behoben** | «+ Video», «Teilen», «Mehr» mit Wort. Siehe N08 (Suchen am Handy weg). |
| H10 | Wörter für Hans | **teilweise** | Viele weg. Geblieben oder neu: «Hauptrunde - M1-01», «Statistik», «Daran arbeiten», «Daraus trainieren», «Daten exportieren und importieren», «Status der App» (öffentlicher Kopf), «Frei 3/1» im Telegramm. |
| H11 | Vereinsname uneinheitlich | **behoben** | Kopf, Telegramm und Kopfzeile nennen «SG Wädenswil/Horgen». |
| H12 | Prüfen-Antwort nicht zurücknehmbar | **behoben** | «Zurück» über der Frage. |
| H13 | Vordrängen beim ersten Besuch | **behoben** | Kein Banner; nichts zu Einwilligung vor dem ersten Video. |
| H14 | Saison-Verlauf Beschriftungen | **nicht geprüft** | Saison des echten Vereins nicht erneut angesehen. |
| Z1 | Alte Startseite der App | **behoben** | wie B38. |
| Z2 | Linke Spalte Anmelden | **behoben** | «Dein Spiel. Und drei Dinge zum Mitnehmen.» und «Was die App kann: handball-ai.ch». |
| Z3 | q, farbe, lang kommen an | **behoben** | Website › «Wie heisst dein Team?» › `/einstieg?q=Wädenswil&farbe=rot`, Trikot Rot vorgewählt, Treffer schon da; `lang` wird als Cookie gesetzt und aus der Adresse entfernt. Nichts wird zweimal gefragt. |
| Z4 | Versprechen Nachricht, Beispielspiel | **teilweise** | Mail und Beispiel da; die Mail verspricht drei Dinge auch ohne Ergebnis (**N05**). |
| Z5 | Laufdistanzen, Pässe, Ball | **teilweise** | xG weg, Laufleistung gekennzeichnet; «Ballbesitz im Spielverlauf» und «Alle Angriffe» hinter «Mehr zum Spiel». |
| Z6 | Dauer der Analyse | **behoben** | Keine «40 Minuten». |
| Z7 | Eine Filmanleitung | **teilweise** | Link vorhanden, Ziel vermutlich falsch (**N06**). |
| Z8 | Testphase | **behoben** | Neuer Verein: «Team · Testphase bis 13.12.2026. Danach gilt der Gratis-Plan …»; das erste Video wurde analysiert (Testbild, 13 s bis «fertig»). |

## Zählung

| | Anzahl |
|---|---|
| bestätigt behoben | 50 |
| teilweise | 21 |
| offen | 0 |
| neu kaputt | 1 (B18 am Handy; dazu die neuen Befunde N01, N04, N07 in `BEFUNDE.md`) |
| nicht geprüft | 4 (B28, B41, B50, H14); dazu die Anwurf-Frage in Prüfen |

Gezählt über die 76 Zeilen B01 bis B54, H01 bis H14 und Z1 bis Z8 (B48 einmal). B18 zählt als
«behoben» (Desktop) und als «neu kaputt» (Handy), ist aber in der Summe nur einmal enthalten, unter
«neu kaputt».
