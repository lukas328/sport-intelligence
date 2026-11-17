# Livegang: Befunde, zweite Runde

Ab 2026-11-17, nach dem Umbau der ersten Runde (`BEFUNDE.md`, Prüfbericht `QA-NACHT.md`).
Wie in der ersten Runde: **erst sammeln, dann in einem Rutsch umsetzen** (Wunsch von Lukas).
Quelle: K = Lukas beim Probieren, Q = Claude beim Prüfen.

Schwere: 🔴 blockiert einen Trainer · 🟡 stört · ⚪ Kleinigkeit.

## Von Lukas

Website-Feedback (aus einer anderen Sitzung, von Lukas weitergegeben, 17.11.):

| # | Befund | Wo | Stand |
|---|---|---|---|
| W1 | 2x-Produktbilder luden auf hochauflösenden Bildschirmen nicht (`@` im Dateinamen, Cloudflare leitet mit 307 um) | Website | behoben 17.11. (PR #58, `-2x.webp`) |
| W2 | Hero: Teamsuche «Wie heisst dein Team?» ersetzt den Knopf «Kostenlos starten», «Demo-Spiel ansehen» bleibt | Website, Start | behoben 17.11. (5a132ba0): Teamsuche im Hero, schickt an `/einstieg?q=` (die App liest `q`), «Demo-Spiel ansehen» daneben |
| W3 | Hero: statt Laptop und Handy mit winziger Oberfläche ein grosser, lesbarer Ausschnitt «9 von 18 Gegentoren über aussen rechts» als Antwort auf die Headline | Website, Start | behoben 17.11. (5a132ba0): neues Produktbild `hero-thing`, Ausschnitt der ersten Karte aus der App, Callout als HTML |
| W4 | «Die Preise sind noch nicht endgültig» unter dem Hauptknopf streichen (nur auf der Preisseite) | Website, Start | behoben 17.11. (5a132ba0, 8eb50c92): Preiszeile ohne Vorbehalt; der Vorbehalt ist nach W32 überall weg |
| W5 | Neue Abfolge: Hero, Problem, Was du bekommst, Demo, Filmen/Hochladen/Prüfen, Link in den Teamchat, Datenschutz, Preis, Abschluss | Website, Start | behoben 17.11. (5a132ba0): Hero, Problem, drei Dinge, Demo, Filmen/Hochladen/Prüfen, Teamchat, drei Spiele später, Datenschutz, Preis, Abschluss |
| W6 | «Profis haben Analysten. Du hast den Samstagabend.» direkt unter den Hero, mit zwei Sätzen zum Problem (Lukas: sehr gut, nach oben) | Website, Start | behoben 17.11. (5a132ba0): dunkler Block direkt unter dem Hero, zwei Sätze aus «Über uns», «Für diesen Abend bauen wir» |
| W7 | Eigener kurzer Block, der die drei Dinge zeigt (Kernversprechen) | Website, Start | behoben 17.11. (5a132ba0): «Samstag, 22 Uhr: Drei Dinge fürs nächste Training», die drei Dinge des Demo-Spiels |
| W8 | Vision «Heute, als Nächstes, später» | Website, Start | ersetzt durch W32: keine Einschränkungen auf der Website |
| W9 | Aufwand ehrlich: «Mehr musst du nicht tun» → «Die Analyse schlägt vor, du bestätigst Tor für Tor» | Website | behoben 17.11. (5a132ba0, 8eb50c92): «Die Analyse schlägt vor, du bestätigst Tor für Tor» auf Start, So funktioniert es, Fragen |
| W10 | «ein Tipp» wird als Hinweis gelesen: überall «einmal tippen» oder «antippen» | Website, App | Website behoben 17.11. (5a132ba0, 8eb50c92): «antippen», «einmal tippen», «Tippe auf»; App offen: `entry.colourHint` «Ein Tipp genügt», `spot.why` «Tipp, von wo geworfen wurde.» (übrige «Tipp:» sind Hinweise) |
| W11 | Preisüberschrift «Ein Preis pro Team» passt nicht zu drei Plänen, z. B. «Ab CHF 39 pro Team» | Website | behoben 17.11. (5a132ba0): «Ab CHF 39 pro Team.» (aus `packages/plans`) |
| W12 | Demo: Ball zeigen, ohne Hinweis «noch nicht erkannt» (W32) | Website, Demo | behoben 17.11. (5a132ba0, 8eb50c92): Legende «Ball: wer ihn hat», kein «noch nicht erkannt» |
| W13 | Farbwahl über die Demo setzen oder weglassen | Website, Start | behoben 17.11. (5a132ba0): Farbwahl von der Startseite genommen (bleibt im Demo-Spiel) |
| W14 | Ratgeber-Block von der Startseite nehmen (Menü und Footer reichen) | Website, Start | behoben 17.11. (5a132ba0): Ratgeber-Block weg, Ratgeber im Menü |
| W15 | Zahlenreihe «1 / 0 / 3» streichen | Website, Start | behoben 17.11. (5a132ba0): Zahlenreihe weg |
| W16 | Handy-Ansicht: Legenden unter den Bildern wiederholen die gelben Marken, eines genügt | Website | behoben 17.11. (5a132ba0): unter 28rem Breite nur die Wörter unter dem Bild, keine Nummern und Pfeile auf dem Bild |
| W17 | Navigation: vier Punkte (So funktioniert es, Demo, Preise, Fragen) in dunkler Schrift statt grauer Kursive | Website | behoben 17.11. (5a132ba0): So funktioniert es, Demo-Spiel, Preise, Fragen, Ratgeber in dunkler, aufrechter Schrift; «Filmen» im Fuss |
| W18 | Fette Kursive nur für H1, H2 und Ziffern; H3, Navigation, Formulare normal | Website | behoben 17.11. (5a132ba0, 8eb50c92): fette Kursive nur H1, H2, Ziffern; H3, Navigation, Formulare und Listen-Links aufrecht |
| W19 | Screenshots als Ausschnitte in Originalhelligkeit statt abgedunkelter Gesamtansichten | Website | behoben 17.11. (5a132ba0): keine Abdunklung mehr, Ausschnitte (Saison unter dem Titel geschnitten) |
| W20 | Schritt 1: Diagramm auf Rahmengrösse, «fehlt» erklären («Ecke nicht im Bild») | Website | behoben 17.11. (5a132ba0): Hallenplan füllt den Rahmen, «Ecke nicht im Bild» (auch Filmen-Seite und Ratgeber) |
| W21 | Dunkler Block: leere rechte Hälfte am Desktop füllen (Schweiz-Hinweis oder Bild) | Website | behoben 17.11. (5a132ba0): rechts der Abend als Bild: 16:18, das Gefühl, das Video bei 0:00; Schweiz-Hinweis beim Datenschutz |
| W22 | Geschichte als Bogen einer Woche: Samstag 19 Uhr verloren 24:26 und nur ein Gefühl; Samstag 22 Uhr 9 von 18 über aussen rechts, alle Szenen am Stück; Dienstag vier Szenen im Teamchat und im Training genau das; drei Spiele später aussen rechts zu | Website, Start | behoben 17.11. (5a132ba0): roter Faden mit Zeitmarken Samstag 19 Uhr, Samstag 22 Uhr, Dienstag, drei Spiele später; Ergebnis 16:18 statt 24:26, damit «9 von 18» aus dem App-Bild stimmt |
| W23 | Der beste Text steht unter «Über uns» (Trainerin coacht, wechselt, redet mit dem Schiri, «Für diesen Abend bauen wir») → auf die Startseite | Website | behoben 17.11. (5a132ba0): Text im Problem-Block |
| W24 | Ein echtes Bild aus der Halle (Handy auf Stativ auf der Tribüne), sonst nur Oberflächen | Website | offen, braucht ein Foto ohne erkennbare Personen (Lukas) |
| W25 | Gegner der Geschichte aussprechen: das Bauchgefühl, das 60-Minuten-Video, das niemand anschaut | Website | behoben 17.11. (5a132ba0): «ein Gefühl und ein Video von 60 Minuten, das niemand anschaut» |
| W26 | Das Danach: was am Dienstag im Training passiert (Trainingstipps, Szenen im Chat) | Website | behoben 17.11. (5a132ba0): «Dienstag, vor dem Training: Vier Szenen in den Teamchat», im Training genau das |
| W27 | Gutes Ende: Vorher und Nachher («Erst 9 von 18, drei Spiele später 3 von 22») statt «aussen rechts bleibt offen»; Demo-Daten dafür anpassen | Website, Demo, Produktbilder | behoben 17.11. (5a132ba0): «Erst 9 von 18, drei Spiele später 3 von 22» mit zwei Feldern, als erfundenes Beispiel markiert |
| W28 | Teamchat als Wirkung: die Spieler sehen es selbst, statt es vom Trainer zu hören | Website | behoben 17.11. (5a132ba0): Chat-Bild mit Antwort eines Spielers «Gesehen. Ich bin zu spät rüber.» |
| W29 | Demo-Spiel als Niederlage statt «Gewonnen. Und drei Dinge zum Mitnehmen.» | Website, Demo, Produktbilder | behoben 17.11. (ec5f3324, 5a132ba0): Website-Demo verloren 16:18, «Verloren. Und drei Dinge zum Mitnehmen.»; App-Seed (26:18 gewonnen) unverändert, kein Bild zeigt «Gewonnen» oder ein Resultat |
| W30 | «noch nicht», «vorgesehen», «geschätzt» von der Website entfernen (W32) | Website | behoben 17.11. (8eb50c92): siehe W32 |
| W32 | **Entscheid Lukas (17.11.):** Die Website beschreibt das Produkt so, wie es beim Release sein wird: keine Hinweise wie «kommt bald», «noch nicht verfügbar», «noch nicht erkannt», «Preise noch nicht endgültig». Begründung: Testphase, Release erst, wenn alles passt. Bis zum Release gilt: Website nicht bewerben; Claude schlägt vor, Suchmaschinen bis dahin auszusperren (noindex) oder den Einstieg als Testphase zu kennzeichnen, damit niemand Funktionen erwartet, die noch nicht laufen | Website | entschieden: kein noindex, Website zeigt Vision und fertiges Produkt in vernünftigem Mass; umgesetzt 17.11. (8eb50c92): Vorbehalte auf allen Seiten, in llms.txt und strukturierten Daten weg, keine neuen Zahlen; Rechtstexte bleiben als Entwurf markiert |
| W31 | Zeit als Anker «Samstag filmen, Sonntag wissen», nur wenn die Analysedauer es hergibt | Website | zurückgestellt, bis die Dauer gemessen ist |

App, Analyse und Prüfen (Lukas' echter Lauf, 17.11.):

| # | Befund | Wo | Stand |
|---|---|---|---|
| A1 | Während und nach der Analyse lässt sich nichts löschen oder abbrechen: kein «Upload abbrechen» für den hängenden Upload (DE_3Liga_HSGKonstanz…mp4, «seit 1070 Min. kommt nichts mehr an, 32 MB von 3.1 GB»), kein «Datei entfernen» für den gescheiterten Lauf (CH_NLB_SGHorgen…mp4). Die API kann es (`DELETE /v1/orgs/{org}/videos/{id}`), die App bietet es nur versteckt in «Das Spiel in N Teilen» und nicht für hängende Uploads. Nötig: pro Datei im Fortschritt «Upload abbrechen» bzw. «Datei entfernen», mit Rückfrage | Spiel, Fortschritt | offen 🔴 |
| A2 | Kopfzeile «Upload unterbrochen, Hochladen: 1 %» widerspricht dem Balken (etwa 40 %) und mischt beide Dateien: pro Datei eine klare Zeile, oben eine stimmige Zusammenfassung | Fortschrittsleiste | offen 🟡 |
| A3 | Fehlermeldung zu allgemein: Grund in Nutzersprache («Video zu lang für die Testumgebung: 99 Min., Grenze 6 h Rechenzeit») und was hilft (kürzer schneiden); «Analyse neu starten» nicht anbieten, wenn es sicher wieder scheitert | Spiel, Fortschritt | offen 🟡 |
| A4 | Hängender Upload (1070 Min. ohne neuen Teil) gilt nicht von selbst als abgebrochen: nach einer Frist als abgebrochen markieren und entfernen lassen | Upload, Watchdog | offen 🟡 |
| A5 | Zwei verschiedene Spiele (Horgen und Konstanz) hängen am selben Spiel: gewollt (mehrere Dateien pro Spiel) oder Bedienfehler? Beim Hochladen auf ein Spiel mit anderer Datei warnen, wenn Dateiname oder Länge nicht passen | Upload | offen, prüfen |
| A6 | 150 offene Fragen, obwohl die Analyse «nichts gefunden» hat; kein «alle überspringen». Konzept: höchstens etwa 10 Fragen pro Spiel, nach Nutzen sortiert, gebündelt (eine Frage pro Spieler statt pro Szene), «alle überspringen», keine Fragen wenn kaum etwas gefunden wurde, dafür klare Meldung, was fehlt (z. B. Spielfeld nicht erkannt) | Prüfen, Glocke | offen 🔴, Konzept folgt |
| A7 | Start: «Die Analyse hat noch keine Tore gefunden. 159 Fragen helfen ihr weiter.» schiebt die Arbeit auf den Trainer. Stattdessen ehrliche Meldung mit Grund (Feld nicht erkannt, Video zu lang) und höchstens wenige gezielte Fragen (siehe A6) | Start | offen 🔴 |
| A8 | Widerspruch: Spielliste «Analyse fertig, 159 Fragen offen», im Spiel «Die Analyse hat nicht geklappt» (zwei Dateien, eine fertig, eine gescheitert). Status pro Spiel fasst beides zusammen, z. B. «1 von 2 Teilen analysiert» | Spiele, Spiel | offen 🟡 |
| A9 | Gelber Hinweis «Upload unterbrochen: HC Goldach-Rorschach 2 · weiter mit derselben Datei» bleibt auf jeder Seite stehen, auch nach Stunden, lässt sich nicht wegklicken: «Verwerfen» und nach einer Frist von selbst weg (vgl. A4) | Fortschrittsleiste | offen 🟡 |
| A10 | Grosse leere grüne Fläche oben auf der Startseite: Platz ohne Inhalt, das Wichtige rutscht nach unten | Start | offen 🟡 |

## Noch offen aus der ersten Runde

| # | Punkt | Wo | Stand |
|---|---|---|---|
| Q1 | Szene als Videodatei teilen und «Das Spiel in 60 Sekunden» (K20): braucht die Analyse-Pipeline | Teilen | offen, gehört zur Analyse-Arbeit |
| Q2 | Szenentitel in Sammlungen lauten «Gegentor über aussen rechts» (Text aus `zoneFrom`), glätten | Sammlungen | offen ⚪ |
| Q3 | Chat-Vorschauen (WhatsApp, Signal, iMessage) auf einem echten Handy prüfen | Teilen | offen, Test durch Lukas |
| Q4 | Spieltag offline: Neuladen ohne Netz lokal unter `next dev` nicht bestätigt, in der echten App prüfen | Spieltag | offen, prüfen |
| Q5 | Login und Hauptflüsse in Produktion mit echtem Konto durchgehen (Claude hat kein Konto, nur öffentliche Seiten geprüft) | App | offen, Test durch Lukas |
| Q6 | «Gegner beobachten» (K3): wie gut es ist, hängt an der Analyse | Upload, Gegner | offen, nach dem Analyse-Fix prüfen |

## Entscheide und Aufgaben für Lukas

| # | Punkt | Stand |
|---|---|---|
| E1 | GPU-Kontingent bei Azure beantragen (Serverless T4, Switzerland North), siehe `docs/plans/gpu-analyse.md` | zurückgestellt (17.11.): bis das Produkt fertig ist, auf Staging nur Ausschnitte von 5 bis 10 min auf CPU |
| E2 | Mail-Anbieter (Empfehlung Azure Communication Services), danach `HB_MAIL_ENABLED=true` | offen |
| E3 | Cloudflare: «Builds for non-production branches» ausschalten (sonst roter Check auf jedem neuen Zweig) | offen |
| E4 | CUDA-Image des gpu-workers in der CI bauen (Vorschlag der Hauptsitzung) | zurückgestellt (17.11.), wie E1 |
| E5 | Staging-Variablen für Ballnetz und Wiedererkennung: schlanke CPU-Variante wird gemessen (ein Netz, `HB_BALL_ALLOW_CPU=1`, `HB_BALL_MAX_MINUTES=10`, `HB_BALL_EVERY=3`); endgültige Werte kommen von der Hauptsitzung | wartet, noch nicht setzen |
| E6 | Aufräumen: alte Zweige, Testkonto `e2e-entry…`, DNS `test.` und `asuid.test` (Löschen war für Claude gesperrt) | offen |
| E7 | Optional: Partnerschaft J+S und SHV für die Übungsbibliothek anfragen (`docs/research/R1-uebungsbibliothek.md`) | offen |

## Betrieb

| # | Punkt | Stand |
|---|---|---|
| B1 | App-Feinschliff (#57) gemergt, Deploy wartet auf den laufenden Analyse-Lauf (zweite Halbzeit, vom Watchdog um 05:00 UTC neu gestartet) | wartet |
| B2 | Danach testet Lukas mit Ausschnitten von 5 bis 10 min statt ganzer Spiele | offen |
