# UX-Test Runde 1, zweite Lieferung: Einstieg für ältere Trainer

Stand: 12. November 2026, App vom Branch `claude/trikot-ui` (Commit f78f8e8), Website-Konzept vom
Branch `claude/site-anlauf` (Commit 3da5b32). Gehört zu `BEFUNDE.md` (gleiche Nummern, gleiche
Schweregrade; die Befunde H01 bis H14 sind dort in der Gesamtzählung enthalten).

Aufbau wie in `BEFUNDE.md`: lokaler Stack, Produktions-Build, Playwright mit Chromium. Zusätzlich:
neue Konten für echte Vereine aus handball.ch (SG Wädenswil/Horgen, HC Rheintal), Messung von
Wörtern, Feldern und Entscheidungen pro Screen, Schriftgrössen und Kontraste im DOM, 200 % Zoom
(Desktop 1280 als 640 CSS-Pixel) und grosse Systemschrift am Handy (390 px bei 130 %, nachgestellt
als 300 CSS-Pixel Breite).

## Einstieg, wie er sein sollte

Der erste Eindruck und ein schlankes Onboarding haben Vorrang. Die Hauptperson dafür ist **Hans**, 58, Trainer seit zwanzig Jahren, WhatsApp und E-Banking, sonst
wenig Apps, Lesebrille, meistens am Handy, Systemschrift «gross». Wenn er nach zwei Minuten nichts
Nützliches sieht, ist er weg.

### Der heutige Weg, gemessen

Gemessen am Handy (390 px) mit einem neuen Konto für einen echten Verein aus handball.ch
(SG Wädenswil/Horgen, Männer 1. Liga). «Wörter» = sichtbarer Text im Hauptbereich, den man
überfliegen muss; «Entscheidungen» = Stellen, an denen Hans zwischen Möglichkeiten wählen muss.

| # | Screen | Wörter | Felder | Entscheidungen | Was Hans davon hat |
|---|---|---|---|---|---|
| 1 | Website «Video hochladen, alles andere passiert automatisch.» | 85 | 0 | 1 (Jetzt starten / Ich habe schon ein Konto) | ein Versprechen, kein Bild der App, kein Demo |
| 2 | Konto erstellen | 28 | 4 (Name, E-Mail, Passwort mind. 10 Zeichen, Häkchen) | 1 (Bedingungen akzeptieren, nicht lesbar) | nichts |
| 3 | «Willkommen · Mannschaft suchen» | 41 | 1 | 0 | nichts |
| 4 | Suchergebnis «Wädenswil» | 109 | 1 | 1 (welches von 8 Teams, Ligakürzel «Hauptrunde - M1-01») | er erkennt sein Team |
| 5 | «Das seid ihr, oder?» nach **13,4 s** Warten ohne Satz | 59 | 1 (8 Trikots) | 2 (Farbe; Stimmt / nicht mein Team) | **erster kleiner Nutzen**: Rang 4, 23 Spieler, letztes Spiel |
| 6 | Spiele (Start) «Das letzte Spiel, noch ohne Video.» | 180 | 0 | viele (40 Ziele) | Resultate, die er kennt; kein Rang, keine Tabelle, keine Torschützen |
| 7 | (nur wenn er «Spiel öffnen» tippt) Upload-Kasten | 55 | 3 | 2 | nichts |
| 8 | (nur wenn er «Saison» findet) «4 Siege in Folge.» | 121 | 0 | 0 | **echter Nutzen**: Serie, Tordifferenz pro Spiel, Tabelle |
| 9 | (nur wenn er «Team» findet) «20 im Kader. Bei 20 fehlt noch etwas.» | 136 | 0 | 0 | Schreck: 20 × gelb «Einwilligung fehlt», alle «Ohne Position» |

Summe bis zum ersten App-Screen (1 bis 6): **6 Screens, 6 Felder, 5 Entscheidungen, rund 500
Wörter, etwa 60 getippte Zeichen**. Maschinenzeit 22 Sekunden; für Hans realistisch 4 bis 5
Minuten (Lesen mit 150 Wörtern pro Minute rund 3,3 min, Tippen mit dem Daumen rund 40 s, Warten
13 s). Das erste, das ihm wirklich etwas bringt (Saison: Serie, Tabelle), liegt hinter einem
Reiter, den er nicht kennt. **Er sieht vor dem Abbruch nichts Nützliches.** Mit dem
Zwei-Faktor-Banner über jeder der 84 geprüften App-Seiten ist die erste Zeile, die er in der App
liest: «Als Vereinsadmin musst du die Zwei-Faktor-Anmeldung aktivieren.»

Bilder: `shots/e01-heute-bis-team.jpg` (Screens 1 bis 5), `shots/e02-heute-erster-blick.jpg`
(Screens 6 bis 9), `shots/e03-erstes-video.jpg` (erstes Video am Handy).

**Wo Hans abbricht:** am wahrscheinlichsten auf Screen 2 (Konto, bevor er irgendetwas gesehen
hat), sonst beim 13-Sekunden-Warten ohne Wort (Screen 4) oder auf Screen 6, weil dort nur steht,
was er schon weiss, und oben eine Warnung mit einem Wort, das er nicht kennt.

**Kann man die App vor dem Konto ansehen?** Nein. Kein Demo, keine Bilder der App auf der Website,
die Teamsuche verlangt eine Anmeldung (API antwortet ohne Konto 401). Schritt 2 verspricht «Als
Nächstes: das erste Video hochladen oder das Demo-Spiel ansehen», ein Demo-Spiel gibt es aber
nirgends (der Text-Schlüssel `tryDemo` hängt nur noch an der entfernten Checkliste).

**Was die Anmeldung verlangt:** Name, E-Mail, Passwort mit mindestens 10 Zeichen (Regel steht in
12 px darunter), Häkchen für nicht verlinkte Bedingungen. Die E-Mail muss nicht bestätigt werden,
um weiterzumachen (gut); der Hinweis steht nur in Ich.

**Was sich vordrängt, ohne mit seinem Ziel zu tun zu haben:** das Zwei-Faktor-Banner (jede Seite,
ab der ersten Sekunde), 20 gelbe «Einwilligung fehlt» und «Bei 20 fehlt noch etwas» im Team, die
Kamera-Auswahl («Hauptkamera, Torkamera links …») vor der Videodatei, «Spielformat» und vier
Trikotfarben im Upload-Dialog, «Kader bearbeiten» als grosser Knopf, die Systemstatus-Verlinkung
in der Kopfzeile. Alles davon kann warten, bis er die drei Dinge des ersten Spiels gesehen hat.

**Das erste Video:** Was er filmen soll, steht nur eingeklappt unter «Aufnahmetipps» und in
Fachwörtern («Mindestens 1080p, in Hallen mit 50-Hz-Licht 50 oder 100 fps»); dass ein Handy
reicht, steht nirgends. Welche Datei geht, steht nirgends (nur der Dateifilter). Am Handy steht
«Video hierher ziehen». Dass er die Seite nach dem Hochladen schliessen darf, ist als Text
vorhanden («Läuft im Hintergrund. Du kannst die Seite schliessen, wir melden uns, wenn es fertig
ist.», Schlüssel `processing.analysisHint`), wird aber nirgends angezeigt. Wie lange es dauert:
«Nach etwa 40 Minuten» steht vor dem Hochladen, danach nicht mehr; der Balken springt von 10 auf
15, 70 und zurück auf 5 Prozent. Dass es fertig ist, erfährt er nur über die Glocke. Am Handy gibt
es die Glocke nicht (weder in der Kopfzeile noch im Kontomenü); eine Mail oder eine Mitteilung
aufs Handy gibt es auch nicht. **Am Handy erfährt Hans also gar nicht, dass die Analyse fertig ist.** In der
Wartezeit sieht er eine Liste mit «Analyse-Version erstellen, Qualitätscheck, Vorschaubilder».

### Vorschlag: der schlankste Weg (drei Schritte bis zum ersten Aha)

Leitlinien nach gängiger Praxis: Nutzen vor Konto; ein Screen, eine Sache; ein Feld pro Schritt;
alles Aufschiebbare aufschieben; sofortiger Nutzen aus vorhandenen Daten; Wartezeit füllen.

| Schritt | Hans sieht / tut | Ersetzt heute |
|---|---|---|
| **1. «Wie heisst dein Team?»** auf der Website selbst, ein Feld, ohne Konto | tippt «Wädenswil», tippt sein Team an | Website-Text, Konto, «Willkommen · Mannschaft suchen» |
| **2. Sein Team, sofort** (ohne Konto): Wurf-Kopf des letzten Spiels in seinen Farben (Farbe aus dem handball.ch-Logo oder eine Frage mit 8 Trikots), Rang und Tabellenausschnitt, Serie («4 Siege in Folge»), Torschützen der Saison, nächster Gegner. Darunter ein Beispiel der drei Dinge aus dem Demo-Spiel, beschriftet «So sieht es nach deinem ersten Video aus». Ein Knopf: **«Das ist mein Team. Speichern»** | sieht innerhalb von 30 Sekunden Zahlen über sein eigenes Team | Screens 4 bis 9 |
| **3. Speichern = Konto**: nur E-Mail, dann Link per Mail oder 6-stelliger Code (kein Passwort, kein Häkchen; Bedingungen als Link im Satz «Mit Speichern akzeptierst du …») | tippt seine E-Mail, öffnet die Mail | Konto-Formular mit vier Feldern |
| danach: **Spiele** mit einer einzigen Aufgabe oben: «Lad das Video vom Spiel gegen Fortitudo hoch.» (Spiel schon gewählt) | – | «Spiel öffnen», Liste mit 40 Zielen |

Erstes Video im Vorschlag: Ein Screen «Video vom Spiel gegen Fortitudo Gossau», drei Zeilen mit
Bildchen (Handy reicht · quer, erhöht an der Mittellinie · ganzes Spiel, eine Datei), ein grosser
Knopf «Video wählen». Nach dem Hochladen: «Fertig hochgeladen. Du kannst die App schliessen. In etwa
40 Minuten bekommst du eine Mail und die drei Dinge.» Darunter, was es schon gibt: Telegramm und
Verlauf aus dem Spielbericht, Tabelle, nächster Gegner. Ein Balken, der nur vorwärts geht, mit
Minuten.

**Was wegfällt:** Passwort bei der Registrierung, Häkchen, «Willkommen»-Titel und Schrittanzeige,
«Mannschaft suchen»-Erklärsatz, Ligakürzel in der Trefferliste («Hauptrunde - M1-01»), das
Zwei-Faktor-Banner, Kamera-Auswahl, Spielformat und vier Trikotfelder im Upload, «Video hierher
ziehen» am Handy, «Oder per Link importieren» als gleichrangiger Weg, die technische Schrittliste.

**Was später kommt** (nach dem ersten Video, als ruhige Hinweise in Team oder Ich, nie als Banner):
Zwei-Faktor (als Punkt am Konto, Pflicht erst nach 14 Tagen, wie in OPEN_QUESTIONS Q-AUTH-2
schon angedacht), Einwilligungen (als ein Satz in Team: «Bevor du Szenen teilst: Einwilligungs-Link
in den Teamchat»), Wappen, Zweitfarbe, Trainerbank, Positionen im Kader, Passwort (optional in Ich).

**Was neu dazu muss:** Teamsuche und Teamvorschau ohne Konto; Demo-Spiel in den Farben des Teams;
Rang, Tabelle, Serie und Torschützen auf dem Start (heute nur in Saison, Torschützen beim echten
Verein gar nicht); Anmeldung per Mail-Link oder Code als Standard; Mail «Die drei Dinge sind da»;
Team ohne Alarm beim ersten Besuch («20 im Kader» ohne «Bei 20 fehlt noch etwas», solange kein
Video da ist).

| Massnahme | Mit der heutigen App sofort möglich (nur Web) | Braucht Arbeit an der API |
|---|---|---|
| Zwei-Faktor-Banner weg, Punkt am Konto | ja | nein |
| Rang, Tabelle, Serie, nächster Gegner auf den Start | ja (Daten der Saison-Seite) | nein |
| Torschützen beim echten Verein | nein | ja (handball.ch-Spielerstatistik pro Spiel übernehmen; heute fehlt «Wer trifft» beim echten Verein) |
| Upload-Dialog: Spiel vorgewählt, Kamera und Spielformat weg, Tipps offen in einfachen Worten, Satz «Du kannst schliessen» | ja (Text existiert schon) | nein |
| Balken nur vorwärts, Minuten | teilweise (Web glätten) | ja (Restzeit-Schätzung pro Job) |
| Mail «Die drei Dinge sind da» | nein | ja (Mailvorlage, Versand bei Analyse fertig) |
| Team ohne Alarm beim ersten Besuch | ja | nein |
| «Übernehmen» mit Satz und nur einem drehenden Knopf | ja | Dauer selbst (13 s) nur mit API (Kader und Spiele im Hintergrund nachladen) |
| Anmeldung per Mail-Link als Standard | teilweise (Magic Link gibt es unter «Ohne Passwort anmelden») | klein (Registrierung ohne Passwort zulassen) |
| Teamsuche und Vorschau ohne Konto | nein | ja (öffentlicher, gedrosselter Lese-Endpunkt auf den handball.ch-Cache) |
| Demo-Spiel in den Teamfarben | nein | ja (Demo-Spiel pro neuem Verein kopieren oder öffentlich lesbar machen) |

### Zusätzliche Messungen für Hans

**Lesbarkeit (Schriftgrösse und Kontrast, gemessen im DOM):**

| Screen | Text unter 14 px | Kleinste Grössen | Kontrast unter 4,5:1 |
|---|---|---|---|
| Website, Anmelden | 0 | – | 0 |
| Konto erstellen | 1 | «Mindestens 10 Zeichen.» 12 px | 0 |
| Einstieg Schritt 1 | 4 | «Mindestens drei Buchstaben.» 12 px; «Schritt 1 von 2», «Team finden», «Bestätigen» 13 px | 0 |
| Einstieg Schritt 2 | 5 | «Von handball.ch», «Das Wappen könnt ihr später hochladen.», «So sieht euer letztes Spiel aus», Kick-Zeile 13 px | 0 |
| Start (Handy) | 24 | Kick-Zeile, Namen im Kopf, «1 von 3» (Plex Mono), «Alle 9», «Szene 7:46», Legende «Anlauf bis zur Wurfposition …» je 13 px | 0 |
| Spiel, Tab Spiel (Handy) | 63 | Achsen 10 px; «Belege anzeigen», «aus 5 Würfen», «Vergleich mit 5 Spielen», Erklärzeilen 12 px | 0 |
| Spiel, Tab Video (Handy) | 29 | Kopfzeile 12 px, «Positionen aus dem Video» 12 px Plex Mono; Rückennummern auf der Kamera rund 8 px | im SVG nicht zuverlässig messbar; nach Augenmass bei 8 px unlesbar |

Der Kontrast ist überall ausser auf der Kamera in Ordnung (`--ink-2` mit 6,1:1 trägt). Das Problem
für Hans ist die Grösse: 13 px ist die Standardgrösse für alles Zweitrangige, und genau dort
stehen die Erklärungen («Anlauf bis zur Wurfposition, von dir bestätigt»), die Zeitangaben und die
Basis der Zahlen.

**200 % Browser-Zoom (Desktop 1280 auf 640 CSS-Pixel) und grosse Systemschrift am Handy (390 px
bei 130 %, nachgestellt als 300 CSS-Pixel Breite):** Website, Anmelden, Einstieg, Start, Spiel und
Prüfen brechen nicht, nichts läuft seitlich über. Zwei Dinge gehen verloren: am Handy verschwindet
der Teamname in der Kopfzeile (nur noch Wappen und Pfeil, `shots/h08b-grosse-schrift-start.jpg`),
und das Zwei-Faktor-Banner schneidet «Einrichten» ab. **Der Spieltag bricht** (H01): Ist das
Fenster niedriger als etwa 550 px (Handy quer, Laptop mit 200 % Zoom), legen sich die Aktionstasten
über das Spielerraster.

**Nur-Symbol-Knöpfe ohne Wort (Handy):** Suchen (Lupe), Video hochladen (+), Konto («SL»),
Team wechseln (Pfeil), im Spiel Teilen (Symbol) und Mehr («…»). Alle haben eine
Bildschirmleser-Beschriftung, aber kein sichtbares Wort. Gesten ohne Alternative: keine gefunden.
Zu dicht stehende Ziele: Spielerraster im Spieltag (4 px Abstand), Antworttasten in Prüfen gut.

**Sicherheit beim Tun:** «Spiel löschen» fragt richtig nach («Spiel mit allen Videos und Daten
endgültig löschen?»). Rückgängig gibt es im Spieltag (aber siehe B03). Eine Antwort in Prüfen
lässt sich nicht zurücknehmen und nicht mehr ansehen (H12). Fehlermeldungen beim Upload haben
keinen Ausweg (B29). Abmelden ohne Rückfrage ist richtig.

---

## Website und Einstieg der App: passt es zusammen?

Gelesen: `docs/site/KONZEPT.md` auf `origin/claude/site-anlauf` (Stand 3da5b32), dazu die Links der
Website in `apps/site/src/lib/site.ts`. Die Website selbst habe ich nicht gestartet; der Abgleich
beruht auf dem Konzept und der App, wie sie heute läuft.

**Was gut zusammenpasst**

- Botschaft und Persona sind dieselben: Hans, Handy, drei Dinge mit Szenen, ehrlich.
- Die Website zeigt ohne Konto, was man bekommt (Demo-Spiel in der Farbe des Besuchers, drei
  Dinge, Taktikkamera). Das füllt die grösste Lücke von heute (H03) von aussen.
- Die Website hat eine echte Filmanleitung (`/aufnahme/`) in einfachen Worten, mit Hallenplan und
  Aushang. Genau das fehlt in der App beim ersten Video (H05).
- Der Sprach-Parameter funktioniert: «Kostenlos starten» führt auf `/register?lang=fr`, die App
  merkt sich die Sprache im Cookie und zeigt die Registrierung auf Französisch (geprüft). Das ist
  heute der einzige Weg, die Sprache zu wählen (B06).
- Gleiche Gestaltung (Stoff, Kanit, Hanken, keine Karten, keine Rundungen) und gleiches
  Vokabular (SPEC 9).

**Wo es bricht oder doppelt erklärt wird**

| Stelle | Website sagt | App macht | Folge für Hans | Vorschlag |
|---|---|---|---|---|
| Nachricht, wenn fertig | «Wenn die Analyse fertig ist, bekommst du eine Nachricht.» (Start und So funktioniert es) | keine Mail, am Handy keine Glocke (H06) | das erste Versprechen wird gebrochen | Mail bauen oder den Satz auf der Website streichen, bis es sie gibt |
| Dauer | bewusst keine Zeit (offene Frage Q-SITE-2) | «Nach etwa 40 Minuten bekommst du die drei Dinge» im Upload-Block | widersprüchlich | eine Aussage für beide; in der App mit Restzeit des laufenden Jobs |
| Demo-Spiel | Konzept 6.7: «die App hat ein Demo-Spiel erst nach der Anmeldung» | die App hat gar keins, verspricht es aber in Schritt 2 (H03) | Annahme der Website stimmt nicht | Satz in der App streichen; Demo der Website auch aus der App verlinken |
| Trikotfarbe | Besucher wählt auf der Website die Farbe seines Teams, `?farbe=rot` geht ins Demo | Einstieg fragt die Farbe in Schritt 2 noch einmal; der Link «Kostenlos starten» trägt nur `?lang=` | doppelte Frage | `?farbe=` an `/register` weitergeben und in Schritt 2 vorwählen |
| Erste Seite | Website ist der Einstieg (Kopf, Demo, Kostenlos starten) | die App hat unter `/` eine **eigene, alte** Startseite («Video hochladen, alles andere passiert automatisch … Spielzüge … Ohne manuelles Tagging … Spieler und Eltern antworten direkt in der App», B38) | zwei Websites mit verschiedenen Versprechen | App-`/` auf die Website oder auf die Anmeldung umleiten |
| Linke Spalte bei Konto erstellen und Anmelden | – | wiederholt den alten Website-Titel und die alte Unterzeile | dritter Text für dieselbe Sache | streichen; nur das Formular, darüber ein Satz «Ein Konto für dein Team.» |
| Erklärung beim Suchen | Website erklärt die drei Schritte | Einstieg erklärt noch einmal «Such dein Team in den offiziellen Daten von handball.ch. Spiele, Resultate und Spieler kommen gleich mit.» | doppelt, 20 Wörter mehr | nur «Wie heisst dein Team?» |
| Filmen | `/aufnahme/`: «1080p, wenn möglich 50 Bilder pro Sekunde», Handy reicht | App: «Mindestens 1080p, in Hallen mit 50-Hz-Licht 50 oder 100 fps», eingeklappt | zwei Fassungen derselben Anleitung | App verlinkt auf `/aufnahme/` und zeigt nur drei Zeilen |
| Testphase | «30 Tage alles gratis, ohne Kreditkarte» | Abo-Seite zeigt «Gratis · CHF 0 · aktueller Plan»; Konzept beschreibt Gratis als «ohne automatische Analyse»; in der App steht nirgends «Testphase, noch 30 Tage» | Hans weiss nicht, ob sein erstes Video analysiert wird | Testphase in der App sichtbar machen (eine Zeile in Verein › Abo, kein Banner) |
| Was es kann | «Das noch nicht: Laufdistanzen genau messen; keine Pässe; Paraden von Hand» | Tab Zahlen zeigt «Laufleistung 0.66 km», Spielerseite «Torvorlagen», Tab Spiel «xG» und «Ballbesitz» (B08, B23, B34) | die Ehrlichkeit der Website wird in der App widerlegt | die nicht gemessenen Werte in der App entfernen |
| Schriftgrösse | nichts unter 16 px, Fliesstext 18 bis 19 px, hält 200 % Zoom | App: viel 13 px, Hinweise 12 px, Achsen 10 px (H08) | Sprung nach unten beim Wechsel von der Website in die App | App-Minimum für Lesetext auf 15 px anheben |
| Kopfzeile | «Anmelden» und «Kostenlos starten», auf dem Handy «Menü» als Wort | öffentliche App-Seiten: «Systemstatus» und «Anmelden» bzw. «Zur App» | ungleich, «Systemstatus» sagt Hans nichts | gleiche Kopfzeile wie die Website, Systemstatus in den Fuss |

**Fazit:** Website und App erzählen dieselbe Geschichte, aber die App hält drei Versprechen der
Website heute nicht (Nachricht wenn fertig, Demo-Spiel, ehrliche Zahlen), und an vier Stellen wird
dasselbe zweimal erklärt oder gefragt (App-Startseite, linke Spalte der Anmeldung, Suchsatz,
Trikotfarbe). Der schlankste gemeinsame Weg: Website mit Demo und Farbe → «Kostenlos starten» mit
`?lang=` und `?farbe=` → in der App nur noch Team suchen und bestätigen → Start mit Rang und einer
Aufgabe.

---

## Befunde H01 bis H14

**H01 · P1 · Spieltag: Aktionstasten verdecken das Spielerraster bei niedrigem Fenster**
- Route: `{m}/matchday`. Gerät: Handy quer (844 × 390), Desktop mit 200 % Zoom (640 × 400 CSS),
  jedes Fenster unter etwa 550 px Höhe.
- Nachstellen: Spieltag öffnen, Handy quer halten.
- Erwartet: Spieler wählbar.
- Passiert: «Tor, Fehlwurf, Gehalten, Pfosten, Ballverlust, 2 Min» liegen über den Spielerfeldern;
  an der Stelle von «1 Andrin» liegt «Tor» (geprüft mit `elementFromPoint`). Bei 640 × 400 sind
  nur Noah, Levin und Mattia zu sehen, darunter eine leere Fläche. Ab etwa 600 px Höhe korrekt.
- Screenshot: `shots/h12-spieltag-quer.jpg`
- Vorschlag: Das Spielerraster nicht in einem Bereich mit fester Höhe oder `sticky` stapeln;
  Playwright-Prüfung bei 844 × 390 und 640 × 400 ergänzen.

**H06 · P1 · Am Handy erfährt man nicht, dass die Analyse fertig ist**
- Route: alle. Gerät: Handy.
- Nachstellen: Video hochladen, App schliessen, später öffnen.
- Erwartet: eine Nachricht, wenn die drei Dinge da sind (Mail oder Mitteilung), und in der App
  ein sichtbarer Hinweis.
- Passiert: Die Glocke («Mitteilungen») ist am Handy ausgeblendet (0 × 0 px), auch im Kontomenü
  (Ich, Verein, Hilfe, Feedback geben, Abmelden) fehlt sie. Eine Mail «Analyse fertig» gibt es
  nicht. Auf dem Start ändert sich nur die Zeile in der Spielliste.
- Screenshot: `shots/e02-heute-erster-blick.jpg` (Kopfzeile ohne Glocke)
- Vorschlag: Mail «Die drei Dinge gegen Fortitudo sind da» mit Link; am Handy die Glocke in die
  Kopfzeile oder ins Kontomenü; auf dem Start den Titel «Die Analyse ist fertig.» für einen Tag.

**H02 · P2 · Kein Nutzen auf dem Start vor dem ersten Video**
- Route: `{t}/matches` direkt nach dem Einstieg. Gerät: beide.
- Erwartet: sofortiger Nutzen aus den handball.ch-Daten (Rang, Tabelle, Serie, Torschützen,
  nächster Gegner).
- Passiert: Titel «Das letzte Spiel, noch ohne Video.», Hauptknopf «Spiel öffnen» (führt zum
  Upload-Kasten), darunter zwölf Resultate, die der Trainer kennt. Rang, Tabelle und Serie gibt es,
  aber nur in Saison («4 Siege in Folge.»); Torschützen gibt es beim echten Verein gar nicht.
  Nächster Gegner ist ein leeres Minifeld.
- Screenshot: `shots/h02-start-ohne-nutzen.jpg`, `shots/h10-saison-echter-verein.jpg`
- Vorschlag: Ohne Video oben «Rang 4. Vier Siege in Folge.» mit Tabellenausschnitt und nächstem
  Gegner; darunter eine Aufgabe «Lad das Video vom Spiel gegen Fortitudo hoch.»

**H03 · P2 · Die App lässt sich vor dem Konto nicht ansehen; das versprochene Demo-Spiel fehlt**
- Route: `/`, `/onboarding`. Gerät: beide.
- Passiert: Website ohne Bild der App und ohne Demo; Teamsuche nur mit Konto (API 401). Schritt 2
  sagt «Als Nächstes: das erste Video hochladen oder das Demo-Spiel ansehen.», ein Demo-Spiel gibt
  es danach nirgends.
- Screenshot: `shots/e01-heute-bis-team.jpg`
- Vorschlag: siehe «Einstieg, wie er sein sollte»; bis dahin den Satz zum Demo-Spiel streichen.

**H04 · P2 · Team beim ersten Besuch: alles fehlt**
- Route: `{t}` (echter Verein, direkt nach dem Einstieg). Gerät: Handy.
- Passiert: «20 im Kader. Bei 20 fehlt noch etwas.», «Tor 0 · Rückraum 0 · Flügel und Kreis 0 ·
  Ohne Position 20», bei allen 20 gelb «Einwilligung fehlt», grosser Knopf «Kader bearbeiten».
  Für Hans liest sich das wie «du hast alles falsch gemacht».
- Screenshot: `shots/h04-team-alles-fehlt.jpg`
- Vorschlag: Vor dem ersten Video «20 im Kader, von handball.ch.» ohne Fehlt-Wörter; Positionen
  ohne Angabe nicht als eigene Gruppe; Einwilligung erst, wenn es Szenen zum Teilen gibt.

**H05 · P2 · Erstes Video: keine Anleitung in einfachen Worten, Beruhigung nie gezeigt**
- Route: Upload-Dialog und `{m}` nach Upload. Gerät: Handy.
- Passiert: Tipps eingeklappt unter «Aufnahmetipps», Inhalt «Mindestens 1080p, in Hallen mit
  50-Hz-Licht 50 oder 100 fps»; kein «Handy reicht», kein Wort zu Dateiart und Grösse; am Handy
  «Video hierher ziehen»; vor der Datei die Wahl «Kamera: Hauptkamera, Torkamera links, Torkamera
  rechts, Weitere Kamera». Der vorhandene Satz «Läuft im Hintergrund. Du kannst die Seite
  schliessen, wir melden uns, wenn es fertig ist.» (`processing.analysisHint`) wird nirgends
  verwendet. Der Fortschritt springt 10 → 15 → 70 → 5 %.
- Screenshot: `shots/e03-erstes-video.jpg`
- Vorschlag: drei Zeilen mit Bildchen offen über dem Knopf, Kamera-Wahl weg (Hauptkamera als
  Standard, weitere später), den Satz zum Schliessen nach dem Hochladen zeigen, Balken nur vorwärts.

**H07 · P2 · Upload-Dialog verlangt zwei Dinge auf einmal**
- Route: «Video hochladen» (+). Gerät: Handy.
- Passiert: im selben Dialog die Liste «Zu welchem Spiel gehört das Video?» und darunter das ganze
  Formular «Oder ein neues Spiel anlegen» mit Spiel | Training, Gegner, Anpfiff, Heim/Auswärts,
  Wettbewerb, Halle, Spielformat, vier Trikotfarben und Schiedsrichter.
- Screenshot: `shots/e03-erstes-video.jpg` (erstes Bild)
- Vorschlag: zuerst nur die Liste (das letzte Spiel oben, vorausgewählt); «Anderes Spiel» öffnet
  einen eigenen Screen mit Gegner und Datum.

**H08 · P2 · Schrift zu klein für ältere Augen**
- Route: Start, Spiel, Einstieg, Anmeldung. Gerät: beide.
- Passiert: siehe Tabelle «Lesbarkeit» oben: 24 Textstellen unter 14 px auf dem Start, 63 im Tab
  Spiel (bis 10 px), Hinweise unter Feldern 12 px, Rückennummern auf der Kamera rund 8 px. Der
  Kontrast ist in Ordnung.
- Screenshot: `shots/h08-grosse-schrift-spiel.jpg`
- Vorschlag: 15 px als kleinste Textgrösse für alles, was gelesen werden muss (Kick-Zeile,
  Legenden, Hinweise, Basis der Zahlen); 13 px nur für reine Achsenbeschriftung.

**H09 · P2 · Nur-Symbol-Knöpfe; bei grosser Schrift verschwindet der Teamname**
- Route: Kopfzeile, Spiel. Gerät: Handy.
- Passiert: Lupe, +, «SL», Pfeil, Teilen-Symbol, «…» ohne sichtbares Wort. Bei 130 % Schrift ist
  in der Kopfzeile nur noch Wappen und Pfeil zu sehen, der Teamname fehlt.
- Screenshot: `shots/h08b-grosse-schrift-start.jpg`
- Vorschlag: «+» als «Video» beschriften, Teilen und Mehr mit Wort; Teamname vor den Symbolen
  behalten, notfalls das Logo weglassen.

**H10 · P2 · Wörter, die Hans nicht versteht**
- Auf den ersten Screens und im Spiel: «Tagging» (Website), «Zwei-Faktor-Anmeldung»,
  «Vereinsadmin» (auf allen 84 App-Seiten), «Systemstatus», «Mannschaft» neben «Team», «Hauptrunde -
  M1-01», «Übernehmen», «Anlauf bis zur Wurfposition», «dünner Strich: zum Tor», «Taktik»,
  «Quellen», «Wie gerechnet?», «xG», «Paradenquote», «Angriffseffizienz», «Ballbesitz geschätzt»,
  «Belege anzeigen», «Baustelle», «Spielformat», «Hauptkamera», «Torkamera», «per Link
  importieren», «Verarbeitung», «Analyse-Version erstellen», «Qualitätscheck», «Vorschaubilder»,
  «RR», «RL», «RA», «KM», «Tags», «CSV», «Matchkarte», «Daten austauschen».
- Zwei Dinge gleichzeitig: Konto erstellen + Bedingungen akzeptieren; Trikotfarbe + Team bestätigen;
  Spiel wählen + neues Spiel anlegen (H07).
- Kürzbare Sätze (Beispiele): «Such dein Team in den offiziellen Daten von handball.ch. Spiele,
  Resultate und Spieler kommen gleich mit.» → «Wie heisst dein Team?»; «Verein und Team sind in
  fünf Minuten angelegt. Das erste Spielvideo kann gleich danach hochgeladen werden.» → streichen;
  «Bis das Feld bestätigt ist, zeigen wir keine Wege und keine Positionen.» → «Stimmt das Feld?».
- Vorschlag: Liste als Prüfliste für die Texte in `messages/de-CH.json` verwenden.

**H12 · P2 · Antwort in Prüfen lässt sich nicht zurücknehmen**
- Route: `{m}/check`. Gerät: beide.
- Passiert: Nach «Ja, stimmt» kommt «Alles geprüft.» ohne Weg, die Antwort zu sehen oder zu ändern.
  Wer sich vertippt, kann es nicht korrigieren.
- Screenshot: `shots/a04-pruefen.jpg` (drittes Bild)
- Vorschlag: «Zurücknehmen» für die letzte Antwort einige Sekunden lang; in Prüfen eine Liste
  «Beantwortet» mit Ändern.

**H13 · P2 · Was sich beim ersten Besuch vordrängt (ersetzt B48)**
- Route: alle App-Seiten. Gerät: beide.
- Passiert: «Als Vereinsadmin musst du die Zwei-Faktor-Anmeldung aktivieren. Einrichten» über
  jeder der 84 geprüften App-Seiten, ab der ersten Sekunde nach dem Einstieg, am Handy abgeschnitten;
  dazu «Systemstatus» in der Kopfzeile der öffentlichen Seiten, 20 × «Einwilligung fehlt» (H04),
  Kamera-Auswahl und Trikotfelder im Upload (H05, H07).
- Screenshot: `shots/e02-heute-erster-blick.jpg`
- Vorschlag: Banner weg, Punkt am Konto; Zwei-Faktor erst nach dem ersten Video und frühestens
  nach einigen Tagen als ruhiger Hinweis in Ich.

**H11 · P3 · Vereinsname uneinheitlich**
- Echter Verein: Kopfzeile «SG Wädenswil/…» (abgeschnitten), Wurf-Kopf «HC Wädenswil», Team-Seite
  «SG Wädenswil/Horgen». Für Hans sind das drei Vereine. `shots/e02-heute-erster-blick.jpg`.

**H14 · P3 · Saison-Verlauf: Beschriftungen stossen zusammen**
- Mit echten Daten am Handy stehen «Unterstrass» und «Andelfingen» ohne Abstand nebeneinander,
  «Pfadi» sitzt über der Nulllinie. `shots/h10-saison-echter-verein.jpg`.
