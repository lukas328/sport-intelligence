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
| W2 | Hero: Teamsuche «Wie heisst dein Team?» ersetzt den Knopf «Kostenlos starten», «Demo-Spiel ansehen» bleibt | Website, Start | offen, empfohlen |
| W3 | Hero: statt Laptop und Handy mit winziger Oberfläche ein grosser, lesbarer Ausschnitt «9 von 18 Gegentoren über aussen rechts» als Antwort auf die Headline | Website, Start | offen, empfohlen |
| W4 | «Die Preise sind noch nicht endgültig» unter dem Hauptknopf streichen (nur auf der Preisseite) | Website, Start | offen, empfohlen |
| W5 | Neue Abfolge: Hero, Problem, Was du bekommst, Demo, Filmen/Hochladen/Prüfen, Link in den Teamchat, Datenschutz, Preis, Abschluss | Website, Start | offen, empfohlen |
| W6 | «Profis haben Analysten. Du hast den Samstagabend.» direkt unter den Hero, mit zwei Sätzen zum Problem (Lukas: sehr gut, nach oben) | Website, Start | offen, empfohlen |
| W7 | Eigener kurzer Block, der die drei Dinge zeigt (Kernversprechen) | Website, Start | offen, empfohlen |
| W8 | Vision «Heute, als Nächstes, später» | Website, Start | ersetzt durch W32: keine Einschränkungen auf der Website |
| W9 | Aufwand ehrlich: «Mehr musst du nicht tun» → «Die Analyse schlägt vor, du bestätigst Tor für Tor» | Website | offen, empfohlen |
| W10 | «ein Tipp» wird als Hinweis gelesen: überall «einmal tippen» oder «antippen» | Website, App | offen, empfohlen |
| W11 | Preisüberschrift «Ein Preis pro Team» passt nicht zu drei Plänen, z. B. «Ab CHF 39 pro Team» | Website | offen, empfohlen |
| W12 | Demo: Ball zeigen, ohne Hinweis «noch nicht erkannt» (W32) | Website, Demo | offen |
| W13 | Farbwahl über die Demo setzen oder weglassen | Website, Start | offen, eher weglassen |
| W14 | Ratgeber-Block von der Startseite nehmen (Menü und Footer reichen) | Website, Start | offen, empfohlen |
| W15 | Zahlenreihe «1 / 0 / 3» streichen | Website, Start | offen, empfohlen |
| W16 | Handy-Ansicht: Legenden unter den Bildern wiederholen die gelben Marken, eines genügt | Website | offen, empfohlen |
| W17 | Navigation: vier Punkte (So funktioniert es, Demo, Preise, Fragen) in dunkler Schrift statt grauer Kursive | Website | offen, empfohlen; Ratgeber als 5. Punkt prüfen (beste Seite laut Lukas) |
| W18 | Fette Kursive nur für H1, H2 und Ziffern; H3, Navigation, Formulare normal | Website | offen, empfohlen |
| W19 | Screenshots als Ausschnitte in Originalhelligkeit statt abgedunkelter Gesamtansichten | Website | offen, empfohlen |
| W20 | Schritt 1: Diagramm auf Rahmengrösse, «fehlt» erklären («Ecke nicht im Bild») | Website | offen, empfohlen |
| W21 | Dunkler Block: leere rechte Hälfte am Desktop füllen (Schweiz-Hinweis oder Bild) | Website | offen, ergibt sich aus W5/W6 |
| W22 | Geschichte als Bogen einer Woche: Samstag 19 Uhr verloren 24:26 und nur ein Gefühl; Samstag 22 Uhr 9 von 18 über aussen rechts, alle Szenen am Stück; Dienstag vier Szenen im Teamchat und im Training genau das; drei Spiele später aussen rechts zu | Website, Start | offen, empfohlen als roter Faden |
| W23 | Der beste Text steht unter «Über uns» (Trainerin coacht, wechselt, redet mit dem Schiri, «Für diesen Abend bauen wir») → auf die Startseite | Website | offen, empfohlen |
| W24 | Ein echtes Bild aus der Halle (Handy auf Stativ auf der Tribüne), sonst nur Oberflächen | Website | offen, braucht ein Foto ohne erkennbare Personen (Lukas) |
| W25 | Gegner der Geschichte aussprechen: das Bauchgefühl, das 60-Minuten-Video, das niemand anschaut | Website | offen, empfohlen |
| W26 | Das Danach: was am Dienstag im Training passiert (Trainingstipps, Szenen im Chat) | Website | offen, empfohlen |
| W27 | Gutes Ende: Vorher und Nachher («Erst 9 von 18, drei Spiele später 3 von 22») statt «aussen rechts bleibt offen»; Demo-Daten dafür anpassen | Website, Demo, Produktbilder | offen, empfohlen (klar als Beispiel) |
| W28 | Teamchat als Wirkung: die Spieler sehen es selbst, statt es vom Trainer zu hören | Website | offen, empfohlen |
| W29 | Demo-Spiel als Niederlage statt «Gewonnen. Und drei Dinge zum Mitnehmen.» | Website, Demo, Produktbilder | offen, empfohlen |
| W30 | «noch nicht», «vorgesehen», «geschätzt» von der Website entfernen (W32) | Website | offen |
| W32 | **Entscheid Lukas (17.11.):** Die Website beschreibt das Produkt so, wie es beim Release sein wird: keine Hinweise wie «kommt bald», «noch nicht verfügbar», «noch nicht erkannt», «Preise noch nicht endgültig». Begründung: Testphase, Release erst, wenn alles passt. Bis zum Release gilt: Website nicht bewerben; Claude schlägt vor, Suchmaschinen bis dahin auszusperren (noindex) oder den Einstieg als Testphase zu kennzeichnen, damit niemand Funktionen erwartet, die noch nicht laufen | Website | offen, Schutz bis Release mit Lukas klären |
| W31 | Zeit als Anker «Samstag filmen, Sonntag wissen», nur wenn die Analysedauer es hergibt | Website | zurückgestellt, bis die Dauer gemessen ist |

App, Analyse und Prüfen (Lukas' echter Lauf, 17.11.):

| # | Befund | Wo | Stand |
|---|---|---|---|
| A1 | Während und nach der Analyse lässt sich nichts löschen oder abbrechen: kein «Upload abbrechen» für den hängenden Upload (DE_3Liga_HSGKonstanz…mp4, «seit 1070 Min. kommt nichts mehr an, 32 MB von 3.1 GB»), kein «Datei entfernen» für den gescheiterten Lauf (CH_NLB_SGHorgen…mp4). Die API kann es (`DELETE /v1/orgs/{org}/videos/{id}`), die App bietet es nur versteckt in «Das Spiel in N Teilen» und nicht für hängende Uploads. Nötig: pro Datei im Fortschritt «Upload abbrechen» bzw. «Datei entfernen», mit Rückfrage | Spiel, Fortschritt | behoben (Stream T, a6be8ccb, 11528d6c): pro Datei im Fortschritt «Upload abbrechen» (laufend oder hängend, Uploader oder Staff) bzw. «Datei entfernen» (angekommen oder gescheitert, nur Staff), mit Rückfrage; die Spielseite zeigt eine gescheiterte Datei auch Tage später; eine einzelne Datei lässt sich im Tab Video entfernen; danach stimmt der Spielstatus |
| A2 | Kopfzeile «Upload unterbrochen, Hochladen: 1 %» widerspricht dem Balken (etwa 40 %) und mischt beide Dateien: pro Datei eine klare Zeile, oben eine stimmige Zusammenfassung | Fortschrittsleiste | behoben (Stream T, 11528d6c): oben eine Zeile für alle Dateien («2 Dateien: 1 Upload unterbrochen, 1 fertig»), darunter eine Zeile pro Datei; der Balken zeigt beim Hochladen den Upload, sonst den ganzen Weg, und fehlt, solange eine Datei hängt |
| A3 | Fehlermeldung zu allgemein: Grund in Nutzersprache («Video zu lang für die Testumgebung: 99 Min., Grenze 6 h Rechenzeit») und was hilft (kürzer schneiden); «Analyse neu starten» nicht anbieten, wenn es sicher wieder scheitert | Spiel, Fortschritt | behoben (Stream T, a6be8ccb, 11528d6c): Grund in Nutzersprache mit dem, was hilft («Das Video ist zu lang für die Analyse: 99 Min. Video, sie darf höchstens 6 Std. rechnen», kürzer schneiden, Link «So filmst du gut»); nach Timeout, unlesbarer oder zu kurzer Datei kein «Analyse neu starten»; ein zweimal stummer Rechner hat einen eigenen Grund |
| A4 | Hängender Upload (1070 Min. ohne neuen Teil) gilt nicht von selbst als abgebrochen: nach einer Frist als abgebrochen markieren und entfernen lassen | Upload, Watchdog | behoben (Stream T, a6be8ccb): 6 Std. ohne neuen Teil gilt als abgebrochen (im Fortschritt sofort, der Watchdog bricht den Upload in der Ablage ab und markiert die Datei); danach «Datei entfernen» |
| A5 | Zwei verschiedene Spiele (Horgen und Konstanz) hängen am selben Spiel: gewollt (mehrere Dateien pro Spiel) oder Bedienfehler? Beim Hochladen auf ein Spiel mit anderer Datei warnen, wenn Dateiname oder Länge nicht passen | Upload | behoben (Stream T, 11528d6c): Entscheid: mehrere Dateien pro Spiel bleiben gewollt; nennt der Dateiname andere Teams oder ein anderes Datum als eine Datei im Spiel, sagt der Upload das, ohne zu blockieren |
| A6 | 150 offene Fragen, obwohl die Analyse «nichts gefunden» hat; kein «alle überspringen». Konzept: höchstens etwa 10 Fragen pro Spiel, nach Nutzen sortiert, gebündelt (eine Frage pro Spieler statt pro Szene), «alle überspringen», keine Fragen wenn kaum etwas gefunden wurde, dafür klare Meldung, was fehlt (z. B. Spielfeld nicht erkannt) | Prüfen, Glocke | behoben (Stream T, a6be8ccb, 11528d6c, d0163da3): höchstens 10 Fragen pro Spiel (Feld, Anwurf, die stärksten Tormomente), mit Resultat nur etwa 1,5 × die noch fehlenden Tore, schon bekannte Tore werden nicht gefragt; «Weiss nicht» bleibt gespeichert, «Für dieses Spiel fertig» legt alle weg und beruhigt die Glocke; der Rest unter «Mehr prüfen» (je 10); Personen eine Frage pro Spieler, höchstens 3; findet die Analyse zu wenig (Feld nicht erkannt, kaum Spieler, kaum Spiel), keine Torfragen, dafür Grund und was hilft |
| A7 | Start: «Die Analyse hat noch keine Tore gefunden. 159 Fragen helfen ihr weiter.» schiebt die Arbeit auf den Trainer. Stattdessen ehrliche Meldung mit Grund (Feld nicht erkannt, Video zu lang) und höchstens wenige gezielte Fragen (siehe A6) | Start | behoben (Stream T, 11528d6c): der Start nennt den Grund und was hilft («Ecken setzen», «So filmst du gut») oder sagt «Noch keine Tore bestätigt. 10 gezielte Fragen, etwa 4 Minuten» |
| A8 | Widerspruch: Spielliste «Analyse fertig, 159 Fragen offen», im Spiel «Die Analyse hat nicht geklappt» (zwei Dateien, eine fertig, eine gescheitert). Status pro Spiel fasst beides zusammen, z. B. «1 von 2 Teilen analysiert» | Spiele, Spiel | behoben (Stream T, 11528d6c, d0163da3): die Spielliste fasst alle Dateien zusammen («1 von 2 Teilen analysiert, 1 Teil gescheitert», «noch nicht ganz hochgeladen») und nennt den Grund einer gescheiterten Analyse |
| A9 | Gelber Hinweis «Upload unterbrochen: HC Goldach-Rorschach 2 · weiter mit derselben Datei» bleibt auf jeder Seite stehen, auch nach Stunden, lässt sich nicht wegklicken: «Verwerfen» und nach einer Frist von selbst weg (vgl. A4) | Fortschrittsleiste | behoben (Stream T, a6be8ccb, 11528d6c): «Verwerfen» blendet den Hinweis aus und bietet an, den Upload abzubrechen; nach 6 Std. ohne neuen Teil verschwindet er von selbst |
| A10 | Grosse leere grüne Fläche oben auf der Startseite: Platz ohne Inhalt, das Wichtige rutscht nach unten | Start | behoben (Stream T, d0163da3): der Kopf der Startseite hält ohne Resultat keinen Platz für eins frei, er bleibt kurz und das Wichtige rückt nach oben |

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
