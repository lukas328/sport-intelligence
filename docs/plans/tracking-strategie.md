# Strategie: Tracking auf Produktniveau (Ball, Spieler, Würfe)

Stand 2026-11-12, Hauptsitzung. Entwurf zur Entscheidung durch Lukas. Ersetzt das bisherige
Vorgehen "Ballnetz Runde um Runde verbessern".

## 1. Ausgangslage, ehrlich

- **Ball:** Auf Testset 2 (177 Bälle, 42 neue Hallen) ist der Ball nur in einem Drittel der Bilder
  der stärkste Punkt. Bei 25 % Fehlalarmen finden wir 25 % der Bälle. Acht Trainingsrunden haben
  das kaum verschoben (Runde 8: kein messbarer Gewinn, `ml/ball/README.md`). Das ist weit weg von
  einem nutzbaren Produkt.
- **Warum:** Das Ballnetz ist sehr klein (ResNet18-Stamm, nur die ersten zwei Stufen, drei Bilder
  auf 1280 px). Es sieht einen Fleck, aber keinen Zusammenhang. Dazu kommen wenige echte Labels:
  rund 300 von Hand bestätigte Bälle plus verrauschte OWLv2-Pseudo-Labels.
- **Das Signal ist da:** OWLv2, ein grosses allgemeines Modell ohne Handball-Training, hat den Ball
  in 66 % der Bilder unter seinen Top 5. Unser Schüler liegt unter seinem Lehrer.
- **Spieler, Feld, Uhr:** Personenerkennung (YOLOX-S), Tracking, automatische Kalibrierung über
  eine Draufsicht, Rückennummern und Spieluhr existieren (ADR 025 bis 028). Ihre Genauigkeit ist
  auf echten Spielen aber nicht systematisch gemessen. Für die Taktiktafel muss das gleich streng
  geprüft werden wie der Ball.
- **Daten:** 226 Spiele, alle auf 1280 px heruntergerechnet (crf 25), meist schwenkende
  Übertragungskameras. Für kleine, schnelle Bälle ist das die schwierigste Ausgangslage.

## 2. Was das Produkt braucht (Anwendungsfälle und Genauigkeit)

| Anwendungsfall | Was gemessen werden muss | Zielgenauigkeit (Vorschlag) |
|---|---|---|
| Taktiktafel, Laufwege, Laufmetriken | Jede Spielerin und jeder Spieler in Feldkoordinaten, über das ganze Spiel, mit Identität | Position ±0.5 m, Identität über 90 % der Spielzeit richtig |
| Ballbesitz, Phasen, Gegenstoss | Wer hat den Ball, Team pro Sekunde | Team richtig in 95 % der laufenden Spielzeit |
| Pässe, Ballpfade, Spielzüge | Ballposition im Feld über die Zeit, Passgeber und Empfänger | 85 % der Pässe erkannt, Ballpfad ±1 m |
| Würfe, Wurfzone, Wurfart | Wurfmoment, Werferposition, Werfer | 95 % der Würfe erkannt, Zone richtig in 90 % |
| Torhüteranalyse: wohin, wo pariert | Ballposition in der Torebene (3 × 2 m) beim Torlinien-Durchgang, Torhüterposition | Torzone (3 × 3 Raster) richtig in 85 %, mit Torkamera mehr |
| Ballgeschwindigkeit | Ballposition in 3D über wenige Bilder nach dem Abwurf | ±10 % |

Wichtig: Diese Zahlen sind Vorschläge. Sie werden in Phase 0 mit echten Messungen und mit dem,
was Trainerinnen und Trainer wirklich brauchen, festgelegt.

## 3. Grundsätze

1. **Messen am Anwendungsfall, nicht am Einzelbild.** Jede Stufe bekommt einen festen
   Goldstandard aus Hallen, die nie im Training sind, und eine Kennzahl pro Anwendungsfall
   (Tabelle oben). Kein Modell kommt ins Produkt, ohne dort besser zu sein.
2. **Wenige starke Kernmodelle statt vieler kleiner.** Ein starkes Ballmodell, ein starkes
   Personenmodell, Kalibrierung, Tracking. Darüber eine Fusionsschicht (Physik, Ballbesitz,
   Spielregeln), die die Einzelbilder zu einem stimmigen Spielverlauf verbindet. So arbeiten auch
   die etablierten Anbieter: Fehler einzelner Bilder werden über die Zeit und den Zusammenhang
   korrigiert.
3. **Daten sind der Engpass, nicht GPU-Zeit.** Die Industrie gewinnt mit grossen, sauber
   gelabelten Datensätzen. Wir bauen einen Datenmotor: das Modell schlägt vor, ein Mensch
   korrigiert nur, und die Korrekturen fliessen ins nächste Training.
4. **Auflösung und Bildrate dort, wo es zählt.** Kaskade wie im BRIEF 6.3: das ganze Spiel auf
   dem Analyse-Proxy, aber Würfe und Torlinien-Momente aus dem Original in voller Auflösung und
   Bildrate. Dafür muss das Original erhalten bleiben.
5. **Jede Aufnahme muss gehen.** Vereine filmen mit dem, was sie haben: schwenkende Kameras,
   Zoom, 720p bis 4K (Entscheid 2). Die Modelle werden auf genau diese Vielfalt trainiert und
   pro Kameraart und Auflösung gemessen. Mehr Auflösung hilft, ist aber keine Bedingung.
6. **Nur saubere Lizenzen.** Code und Gewichte mit Apache-2.0, MIT oder BSD. Kein AGPL
   (zum Beispiel Ultralytics YOLO). Fremde Gewichte nur mit `weights_only=True`.

## 4. Technischer Aufbau (Zielbild)

1. **Personen:** Detektor auf den Analyse-Proxy-Bildern, nachtrainiert auf Handball (Spieler,
   Torhüter, Schiris, Publikum am Rand). Tracking mit Bewegungsmodell und Wiedererkennung
   (Trikot, Nummer). Ergebnis: Tracks in Feldkoordinaten.
2. **Feld und Kamera:** Kalibrierung pro Bild (Homographie bzw. Kamerapose), auch bei Schwenk und
   Zoom. Liefert Feldkoordinaten, Torebene, und welche Bildteile Feld sind.
3. **Ball, Erkennung:** ein Mehrbild-Heatmap-Modell nach dem Stand der Technik für kleine,
   schnelle Bälle (Bauart wie TrackNet bzw. WASB: mehrere Bilder plus Hintergrundbild, tiefes
   Netz mit hoher Auflösung, zum Beispiel HRNet). Es sieht den Zusammenhang (Hand, Wurfbewegung,
   Flugbahn), nicht nur einen Fleck. Ausgabe: Ballkandidaten pro Bild mit Sichtbarkeit (frei, in
   der Hand, verdeckt).
4. **Ball, Verfolgung und Ballbesitz (Fusion):** ein Tracker, der die Kandidaten mit Flugphysik
   (Wurfparabel, maximale Geschwindigkeit) und mit den Spieler-Tracks verbindet. Ist der Ball nicht
   sichtbar, ist er meist bei einer Person; der Ballbesitz-Zustand überbrückt diese Lücken. Ein
   Modell pro Spielerausschnitt ("hält den Ball, ja oder nein", mit Körperhaltung) stützt das.
5. **Ereignisse:** Wurf, Pass, Ballverlust und so weiter aus Ballpfad, Ballbesitz und Spieleruhr.
   Offizieller Spielbericht und Anzeigetafel als Abgleich und für Labels.
6. **Wurf-Feinanalyse:** um jeden erkannten Wurf ein Zeitfenster aus dem Original in voller
   Auflösung und Bildrate. Ball im Tor-Ausschnitt verfolgen, Durchgang durch die Torebene
   bestimmen (Torzone), Torhüterposition und Parade-Art. Optional mit Torkamera
   (`goal_cam_left/right` im Datenmodell vorgesehen).

## 5. Datenstrategie

- **Goldstandard (zuerst):** etwa 40 Clips von 10 Sekunden aus mindestens 20 Hallen, die nie
  ins Training gehen. Pro Bild: Ballposition und Sichtbarkeit, ballführende Person, Würfe mit
  Torzone. Dazu Spielerpositionen in einigen Bildern pro Clip. Das ist der Massstab für alle
  Entscheide.
- **Dichte Labels statt Einzelklicks:** Ballpfade in Clips, das Modell schlägt den Pfad vor,
  der Mensch korrigiert nur Abweichungen (Keyframes, Interpolation dazwischen). Ziel für das
  erste starke Ballmodell: 20'000 bis 50'000 Bilder aus 100 und mehr Hallen.
- **Wer labelt:** Lukas allein schafft das nicht (geschätzt 1 Minute pro 3-Sekunden-Clip mit
  Vorschlägen, also etwa 10 Stunden für 30'000 Bilder). Optionen: Lukas plus Helfer aus dem
  Verein, oder ein bezahlter Label-Dienst mit unserer Anleitung und unserem Werkzeug.
  Entscheid nötig.
- **Pseudo-Labels mit Prüfung:** OWLv2 bzw. das jeweils beste Modell plus Ball-Tracker auf allen
  226 Spielen. Nur Pfade, die physikalisch stimmig sind, gehen als Labels ins Training.
  Stichproben werden von Menschen geprüft.
- **Würfe und Torzonen:** pro Wurf ein Klick auf ein Torschema. Tore und Würfe stehen teilweise
  im offiziellen Bericht, das hilft beim Finden.
- **Originale behalten:** Für neue Daten das Original (oder mindestens 1920 px) speichern, nicht
  nur den 1280-px-Proxy. Job 11 in `ml/gpu/JOBS.md` misst zuerst, wie viel das bringt.

## 6. Fahrplan mit Entscheidungspunkten

| Phase | Inhalt | Dauer (grob) | Entscheid am Ende |
|---|---|---|---|
| 0. Fundament | Anwendungsfälle und Zielwerte festlegen; Goldstandard-Clips auswählen und labeln (Werkzeug mit Modellvorschlägen); Lizenzprüfung der Kandidaten; Messung Auflösung (Job 11); Messung der heutigen Spieler-, Kalibrierungs- und Ballwerte auf dem Goldstandard | 1 bis 2 Wochen | Zielwerte, Label-Tempo |
| 1. Ballmodell v2 | Mehrbild-Modell nach Stand der Technik, trainiert auf vorhandenen Daten plus geprüften Pseudo-Labels; Vergleich auf dem Goldstandard gegen heute und gegen OWLv2 | 2 bis 3 Wochen | Bauart fix, Datenmotor starten |
| 2. Datenmotor | Label-Werkzeug für dichte Ballpfade mit Modellvorschlägen; wöchentliche Schleife: labeln, trainieren, messen | laufend | Ab wann reichen die Werte? |
| 3. Fusion | Ball-Tracker mit Physik und Ballbesitz über die Spieler-Tracks; Kennzahlen pro Anwendungsfall | 2 bis 4 Wochen | Pässe und Ballbesitz produktreif? |
| 4. Wurf-Feinanalyse | Wurfmomente, Originalauflösung um den Wurf, Torebene, Torzone, Torhüter | 3 bis 4 Wochen | Torhüteranalyse produktreif? |
| 5. Produktion | Export nach ONNX bzw. TensorRT, Kaskade, Kosten pro Spiel (BRIEF 6.3: unter CHF 2, 60 Minuten in 45 Minuten auf einer L4) | 2 Wochen | Freigabe |

Spieler-Tracking und Kalibrierung laufen parallel mit derselben Messdisziplin (Phase 0 misst,
danach gezielt nachtrainieren).

## 7. Was ab sofort anders ist

- Keine weiteren Trainingsrunden nach dem alten Muster (kleines Netz, Einzelbild-Labels).
- Die Label-Runde "Ball oder nicht? 3" ist vorbereitet, hat aber keine Priorität mehr. Die
  Klick-Funktion (Ball anderswo) wandert in das neue Pfad-Werkzeug.
- Nächster Schritt: Phase 0. Erste Aufgaben der Hauptsitzung:
  1. Lizenzen und Stand der Technik der Ball-Modelle prüfen (TrackNet-Familie, WASB, weitere).
  2. Goldstandard-Clips auswählen: Hallen, die nie im Training waren, mit Würfen auf das Tor.
  3. Pfad-Label-Werkzeug mit Modellvorschlägen bauen (Basis: `ml/ball/labelling/paths.html`).
  4. Heutige Werte von Spieler-Tracking und Kalibrierung auf diesen Clips messen.

## 8. Entscheide (Lukas, 2026-11-12)

1. **Reihenfolge:** offen, grösster Mehrwert bei Taktiktafel und Ballpfaden. Diese zwei zuerst,
   die Torhüteranalyse danach (sie baut auf dem Ballpfad auf).
2. **Kein Aufnahme-Standard:** Vereine filmen, wie sie filmen. 1080p ist gut zu haben, auf 720p
   dürfen mehr Fehler passieren. Die Modelle müssen mit Schwenk, Zoom und schwacher Qualität
   umgehen; der Goldstandard enthält darum alle Kameraarten und Auflösungen, und wir messen pro
   Auflösung getrennt.
3. **Labeln:** Lukas labelt selbst, etwa eine Stunde pro Tag. Alles wird vorgelabelt
   (Modellvorschläge plus Prüfung durch die Hauptsitzung), Lukas klickt nur noch durch und
   korrigiert. Ein Label-Dienst bleibt eine Option, falls es zu langsam geht (Offerte nötig;
   Datenschutz: Spielvideos mit Minderjährigen nur mit Auftragsverarbeitungsvertrag und in
   der Schweiz oder EU).
4. **Originale:** ja, Originalvideos werden gespeichert, wenn es nötig ist.
5. **Zeit:** Dauert eine Phase länger, dauert sie länger. Massstab ist der Goldstandard, nicht
   der Kalender.

## 9. Ball-Roadmap (Stand 2026-11-16, mit Lukas abgestimmt)

**Ziel:** Würfe aufs Tor und harte Pässe richtig verfolgen, denn dort steckt die spielentscheidende
Information. Etwa 80 % über alle Bälle reichen, wenn diese Szenen stimmen. Zielmarke für schnelle
Bälle und Würfe: 85 bis 90 %. 95 % ist kein Ziel (Verdeckung, Messgrenze).

**Stand (Gold v1, 42 Clips, 12 px, Tracker mit hr1 + hrp1, Details `ml/ball/README.md`, Herkunft aller Versionen `ml/ball/LINEAGE.md`):**
alle Bälle 84.0 %, schnelle 86.0 % (Mittag: je 77 %). Gebracht haben es die Doppelbild-Korrektur,
längere Lücken für schnelle Bälle und die gelernte Bewertung der Kandidaten. Restfehler bei
schnellen Bällen: 8.5 % Tracker wählt falsch, 5.4 % kein Detektor sieht den Ball.

**Metriken (gelten ab jetzt für jede Auswertung):**
1. Recall, Precision und F1 bei 12 px, dazu 25 px; für alle, schnelle und gehaltene Bälle.
   Heute gibt der Tracker fast immer einen Punkt aus (Recall = Precision), er sagt nie "weiss
   nicht". Darum:
2. Sicherheit pro Tracker-Punkt und Precision-Recall-Kurve; berichtet wird zusätzlich der Recall
   bei 95 % Precision.
3. Bilder ohne Ball werden mitgelabelt, mit Sichtbarkeitsstufe (sichtbar, teilweise verdeckt, ganz
   verdeckt, ausserhalb des Bildes). Gold v1 hat nur 14 solche Bilder, erfundene Bälle sind dort
   kaum messbar.
4. Pro Wurf: Anteil der Würfe, deren Flug vom Abwurf bis Tor oder Torhüter durchgehend verfolgt
   wird; Fehler am Abwurf- und am Zielpunkt; Spurwechsel auf ein anderes Objekt pro Wurf.

**Priorisierung (2026-11-16, Hauptsitzung im Auftrag von Lukas).** Massstab: Würfe und schnelle
Bälle verlässlich verfolgen, mit einem auslieferbaren System (ohne OWLv2, ohne DeepSport), ehrlich
gemessen. Was nicht darauf einzahlt, wird geparkt oder verworfen. Begründungen zu den Einwänden:
`ml/ball/LINEAGE.md` Abschnitt 11.

**Jetzt (diese Woche, nur CPU und Labeln):**
| Prio | Was | Warum zuerst |
|---|---|---|
| 1 | **Wurf-Endtest festlegen und labeln:** mindestens 100 Würfe aus mindestens 15 nie trainierten Hallen (Gold- und Testset-2-Hallen), durch Anschauen gefunden; gelabelt **ohne Kandidatenringe** und mit Sichtbarkeitsstufen; Lukas prüft Ja/Nein | Ohne ihn ist keine Entscheidung belastbar. Ohne Ringe zu labeln misst zugleich die Verzerrung der Labels (ersetzt den separaten Verzerrungstest). **Stand 17.11.:** Runde 1 von Lukas geprüft: 76 Würfe aus 33 Hallen (212 Kandidaten). Runde 2 mit 215 weiteren Kandidaten liegt bereit (längere Clips). Danach Abwurf und Ballpositionen ohne Ringe. |
| 2 | **Auslieferbarer Tracker:** Bewertung ohne OWLv2 neu lernen; das ist ab jetzt die Hauptzahl (heute 78.6 % statt 84.0 % mit OWLv2) | Nur was ins Produkt kann, zählt. |
| 3 | **Sicherheit pro Punkt und "weiss nicht"** im Tracker, mit Precision-Recall-Kurve | Ein falscher Punkt mitten im Wurf ist schlimmer als eine Lücke; ohne das ist keine Analyse verlässlich. |
| 4 | Entwicklungssatz: die 61 protokollierten Würfe vorlabeln (Lukas prüft danach) | Zum Verbessern des Trackers auf Würfen, ohne den Endtest zu verbrauchen. |
| 5 | hr2 und hrp2 messen (läuft schon, nur auswerten) | billig, schliesst einen offenen Punkt |

**Danach (GPU-Woche ab Samstag, Kontingent vorher mit Lukas klären):**
| Prio | Was |
|---|---|
| 6 | Netze **ohne DeepSport**, in 2 Folds über die Trainings-Clips (auslieferbar, saubere Kandidaten für die Tracker-Bewertung, zusammen ein Ensemble); ein Vergleichslauf mit DeepSport |
| 7 | Tracker-Bewertung auf den Fold-Kandidaten neu lernen; Messung auf Gold v1 und einmal auf dem Wurf-Endtest; Zwischenfazit mit Lukas |

**Später (nur wenn das Zwischenfazit es verlangt):** gezielte Daten aus neuen Hallen und schwierigen
Szenen; Spielerboxen im Tracker; Netz-Generation 2 mit TOTNet-Ideen (erst wenn der Endtest 2 Punkte
auflösen kann); Übernahme ins Produkt mit Tests.

**Geparkt oder verworfen:**
- OWLv2 im Tracker fürs Produkt: verworfen (zu teuer). Bleibt Werkzeug fürs Vorlabeln.
- Eigene DeepSport-Ablation: verworfen, steckt in Prio 6.
- Separater Verzerrungstest mit 5 Gold-Clips: verworfen, steckt in Prio 1.
- Gold v1 erweitern oder weiter darauf feinjustieren: verworfen. Gold v1 bleibt Entwicklungssatz,
  Unterschiede unter etwa 4 Punkten werden dort nicht mehr entschieden.
- Ensembles mit mehr als zwei Netzen, Runde 10 im Ensemble, weitere Parameter-Suchen: verworfen.
- Verifier, Spielfeldmaske: bleiben verworfen (Abschnitt 7 der Lineage).
- Auftrag 11 (Originalauflösung): geparkt, bis Würfe im Endtest gemessen sind.
- 95 % als Ziel: verworfen; Zielmarke Würfe 85 bis 90 % im Endtest.
- Kalibrierung (findet das Feld nur in 8 von 42 Gold-Clips): eigene Baustelle ausserhalb des Balls,
  Lukas entscheidet, wann.

**Quelle der Wahrheit:** `ml/ball/LINEAGE.md`. Jede Prüfung unseres Vorgehens arbeitet von dort aus;
was eine Prüfung erschliessen musste, weil es fehlte, wird dort nachgetragen, und jeder Einwand
bekommt in Abschnitt 11 eine Bewertung, Belege und eine Massnahme.

**Grundsätze:** Gold wird nicht zum Anpassen verwendet (höchstens mit Kreuzvalidierung über
Clips), Lernen auf den Trainings-Clips. GPU zuerst Kaggle, Modal nur mit Freigabe von Lukas über
die lokale Sitzung. Würfe aus Hallen, die im Training vorkamen, sind etwas leichter als Gold v1
(lauter neue Hallen); das wird bei jedem Wurf-Ergebnis erwähnt. Gold v1 ist seit 2026-11-16 ein
Entwicklungssatz (stark für den Tracker benutzt); sauberer Endtest ist der eingefrorene Teil des
Wurf-Goldstandards (20 Würfe, 4 Hallen, `split: test` in `ml/gold/shot_clips.json`).
