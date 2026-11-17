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

## App-Review (externe Sitzung, Desktop 900 px, 17.11.)

Von Lukas weitergegeben. Nicht alles ist korrekt: Spalte «Einschätzung» sagt, ob der Punkt stimmt und was wir tun.
Priorität: P1 vor dem nächsten Test, P2 bald, P3 wenn Zeit, ✗ nicht übernehmen.

| # | Befund | Prio | Einschätzung |
|---|---|---|---|
| R1 | «Demo-Spiel ansehen» legt ein Spiel an, das in Spielliste, «Das letzte Spiel», Saison («nach zehn Spielen»), «Was sich wiederholt», Trainingstipps und als Vorauswahl im Upload-Dialog auftaucht | P1 | stimmt vermutlich: `is_demo` wird nur in der Abrechnung ausgeschlossen. Demo aus allen Auswertungen, Listen und Auswahlen nehmen, im Demo sichtbar «Das ist ein Beispiel» und ein Weg zurück |
| R2 | Spiel ohne Video, «Aus: Spielbericht», zeigt trotzdem Würfe pro Spieler, Wurfquote 49 % und Ballverluste 16; Kurzbericht «16 Paraden», Kennzahl «20 Paraden»; Trainingstipps «3 von 7 Siebenmetern», Tabelle 3 von 6 | P1 | stimmt: Quellenlogik prüfen (der offizielle Bericht hat keine Würfe), eine Zahl pro Sache, gleiche Quelle überall |
| R3 | Torschützen: Übersicht «Liam Krause 58 aus 10 Spielberichten», «Mehr zur Saison» 6, Kader 6, Sean Krause im Kader ohne Tore | P1 | stimmt vermutlich: Spielerwerte ziehen nur einen Bericht; Torschützen aus allen offiziellen Berichten, überall gleich |
| R4 | Torhüter-Tabelle mischt beide Teams (#16 ohne Namen, Gegner-TW, ein Feldspieler), eigener TW #12 fehlt | P1 | stimmt: nur eigenes Team, Torhüter aus Kader-Position |
| R5 | Mitteilungen: Link auf gelöschtes Spiel ergibt 404 («159 Fragen»), «Video gegen HC Goldach-Rorschach 2 liess sich nicht auswerten» für ein Spiel, das es nicht gibt, «Spielbericht ist da» doppelt, Öffnen markiert alles gelesen, 404-Seite ohne Kopf und Navigation | P1 | stimmt: Mitteilungen beim Löschen mitlöschen, Dubletten zusammenfassen, gelesen erst beim Anklicken, 404 innerhalb der App mit Kopf |
| R6 | «Suchen» im Kopf führt ohne Videos auf eine leere Szenen-Seite ohne Suchfeld | P2 | stimmt: Suchfeld immer zeigen, ohne Daten mit Satz «Suche findet Szenen ab dem ersten Video» |
| R7 | Gegner-Zuordnung bricht bei Namensvarianten («SG Horgen/Wädenswil 1» vs «… (M2)»): falsches letztes Resultat | P2 | stimmt: Gegner über handball.ch-ID bzw. normalisierten Namen ohne Klammerzusatz zuordnen |
| R8 | Screenreader-Text «28 zu 28, Zeichnen» | P3 | prüfen: der Katalog sagt «Unentschieden», vermutlich falscher Schlüssel; schnell |
| R9 | Hero auf Spiele und Spiel: lange Headline wird von der Schräge abgeschnitten, Tordifferenz-Linie läuft durch den Text, «Wädens-/wil» | P2 | stimmt, am Handy schlimmer: Schrift skalieren, Linie unter den Text |
| R10 | Formular-Validierung auf Browser-Englisch («Please fill out this field») im Spielzug-Editor | P3 | stimmt: eigene deutsche Meldungen |
| R11 | Verlauf-Chart kürzt Gegner zu «Handball», «Horgen/.», «+11» oben abgeschnitten | P3 | stimmt: Kurznamen aus dem Vereinsnamen, Label nicht abschneiden |
| R12 | Wurfort-Halbfelder riesig bei Daten nur aus dem Spielbericht (nur «3 / 7 m»); Vorlagen-Bilder mit Leerraum | P3 | stimmt: ohne Positionsdaten eine Zeile statt Halbfeld |
| R13 | Spielverlauf endet bei etwa 41 Min., Achse bis 60 | P2 | prüfen: fehlende Torfolge oder Achse; Achse ans Datenende oder Lücke kennzeichnen |
| R14 | Spielzug-Editor: Werkzeugleiste nicht sticky, Seite heisst «Spielzüge» statt «Neuer Spielzug», Tab-Titel nur «Handball Intelligence», «starte mit einer Vorlage» ohne Vorlagen-Knopf im Editor | P2 | stimmt: alles umsetzen |
| R15 | Farblogik «Wir»: in Vorlagen wechselt, welche Farbe angreift; eigene Trikotfarbe für «Wir» und Legende | P2 | teilweise: «Wir» bleibt eine Farbe; Vorlagen prüfen, dass «Wir» immer die eigene Rolle ist (Angriff oder Abwehr); eigene Trikotfarbe nur, wenn der Kontrast reicht (K23) |
| R16 | Video-Tab: Gegner-Farbfelder brechen um, Icons «Eigene Feldspieler/Torhüter» blau/orange trotz grünem Heimtrikot, unklar ob klickbar | P3 | stimmt: eigene Farben zeigen, Umbruch richten |
| R17 | Spiel-Kopf beim Tab «Spiel» gross, bei «Video»/«Zahlen» kompakt | ✗ | gewollt (Arbeitsfläche im Video); nicht ändern |
| R18 | Verein-Seiten: im Tab nichts aktiv, kein Zurück | P2 | stimmt: aktiver Zustand und Zurück |
| R19 | «Hilfe und Anleitungen» verlässt die App im selben Tab | P3 | stimmt: neuer Tab |
| R20 | «Die drei Dinge» nirgends erklärt; im Demo «1 von 2 / 2 von 2» | P1 | stimmt: ein Satz an erster Stelle, was die drei Dinge sind (wie W7 auf der Website), Demo zeigt drei |
| R21 | Verein bestätigen widersprüchlich («eine zweite Person» und Knopf «Ich bestätige»); Teilen blockiert ohne Link zur Bestätigung; «So geht es weiter» verspricht Teilen | P2 | stimmt: Bestätigung als Schritt mit Link in «So geht es weiter», Knopf nur für die zweite Person |
| R22 | Demo zeigt «Kein Video, lad das Video hoch» neben «Positionen aus dem Video»; «Im Tor: ?» | P2 | stimmt: Demo ohne Upload-Box, Platzhalter weg |
| R23 | «Telegramm» wird als Messenger gelesen | P3 | stimmt: «Kurzbericht» |
| R24 | «… von handball.ch oder so, wie du sie eingetragen hast» liest sich umgangssprachlich | P3 | stimmt: umformulieren |
| R25 | Saison › Gegner: «HC Stammheim 1, Samstag» ohne Datum, Vergangenheit oder Zukunft unklar | P3 | stimmt: «Nächste Gegner» mit Datum |
| R26 | Tordifferenz-Leiste dreimal mit gleichen Daten | P3 | stimmt: einmal, mit Datum und Gegner |
| R27 | Karte «Tore pro Spiel 27.7, Gegentore 25.8» mischt Label und Nebeninfo | P3 | stimmt: zwei Zeilen |
| R28 | Verband: «Gegner stehen nur mit Nummer» ohne Begründung | P3 | stimmt: ein Satz warum (Datenschutz, unbestätigter Verein) |
| R29 | Abo: «Limiten sind in dieser Installation nicht aktiv» ist ein Entwickler-Satz | P2 | stimmt: entfernen oder Kundensprache |
| R30 | Hilfe «Erste Schritte»: «noch nicht gemessen» | P3 | Website; mit W32 vermutlich schon entfernt, prüfen |
| R31 | Trainingstipps: Zusammenhang Befund und Übung unklar, «aus euren letzten 2 Spielen» obwohl nur das Demo analysiert ist | P2 | stimmt: Zeile «Warum diese Übung»; Demo raus (R1) |
| R32 | Haupt-Aktion überall gleich stark (Video hochladen, Demo, Spiel öffnen, + Video, pro Zeile, So geht es weiter) | P2 | stimmt: eine primäre Aktion im Hero, Rest sekundär |
| R33 | Vor dem Upload fehlen Antworten: Formate, Grösse, Dauer, Analyseminuten, was passiert beim Zuklappen | P2 | stimmt: kurzer Info-Block im Upload-Dialog (Dauer erst nennen, wenn gemessen) |
| R34 | Knöpfe im leeren Zustand aktiv, die nichts tun («Szenen neu erstellen», «Neue Highlights», «Tore als Szenen ansehen», «Zu den Szenen») | P2 | stimmt: ausblenden oder mit Hinweis deaktivieren |
| R35 | Spiel ohne Video: «Die Szenen findest du unter Video», dort ist nur der Upload | P3 | stimmt: Text je nach Zustand |
| R36 | «So geht es weiter» lässt sich ausblenden, aber nicht zurückholen; kein Fortschritt | P2 | teilweise: Haken gibt es schon (D); Zurückholen im Kontomenü oder Hilfe ergänzen |
| R37 | Kader: warum er wichtig ist und Torhüter markieren fehlt | P3 | stimmt |
| R38 | Fortschrittsbalken nicht gesehen | ✗ | gibt es (K6), erscheint nur bei laufendem Upload oder Analyse |
| R39 | Spielkarte und Kurzbericht prominenter als «das kannst du heute schon» | P3 | sinnvoll |
| R40 | Seitenwechsel 2 bis 4 s ohne Ladeanzeige | P2 | stimmt: Skelette bzw. loading.tsx je Bereich |
| R41 | Handy-Ansicht nicht getestet | P1 | nächste Runde auf 390 px |

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
