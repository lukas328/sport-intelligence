# Kalibrierung: Testsatz, Messung, Verbesserungen (ab 2026-11-16)

Auftrag: die automatische Spielfeld-Kalibrierung (`handball_vision.observe.auto_calibrate`, ADR 025)
verlässlich machen. Ohne sie gibt es keine Positionen in Metern, keine Taktiktafel, keine Wurfzonen.
Ein falsch akzeptiertes Feld ist schlimmer als keines. Werkzeuge: `ml/calib/` (Forschung; das
Produkt importiert nichts daraus).

## 1. Testsatz (eingefroren 2026-11-16)

- `ml/calib/testset.json`, erzeugt von `ml/calib/testset.py pick` (fester Seed): **70 Stücke à 90 s
  aus 67 Hallen**. Die 42 Spiele des Ball-Testsatzes 2 (`ml/ball/test_games.json`, 42 Hallen,
  Europa und USA, Amateur bis Länderspiel), 4 Spiele SG Wädenswil/Horgen (Club-Streams), 24 weitere
  Heimteams aus `ml/data/catalog.json`.
- Pro Spiel ein Segment aus s0, s1, s3, s4 (s2 liegt bei 50 % und ist oft die Pause), das Stück von
  20 s bis 110 s, wie die 39-Spiele-Messung im Nachtrag von ADR 025.
- **Aufteilung nach Halle:** 33 Stücke Entwicklung (`dev`), 37 Endtest (`test`). Auf dem Endtest
  wird nichts abgestimmt; er wird pro Pull Request höchstens einmal gemessen.
- Produktpfad 1:1 (`ml/calib/run.py`): Worker-Proxy (1280 px, 25 fps, crf 26), `observe()` mit
  YOLOX-S auf jedem 3. Bild, Linien auf jedem 90., dann `auto_calibrate`. Einschränkung: das
  Produkt sieht das ganze Spiel, der Test 90 s; das Panorama ist darum kleiner als im Betrieb.

## 2. Wahrheit

- Pro Stück ein Bild (feste Kamera) oder zwei (linkes und rechtes Schwenkende). Das Ende eines
  Schwenks zeigt ein Tor und prüft zugleich die Kamerabewegung.
- Gespeichert werden **Bildpunkt und Feldposition** der sichtbaren Feldpunkte (Ecken, Mittellinie,
  6-m- und 9-m-Enden, Pfostenfüsse, 7-m-Punkt; Namen wie `handball_court`). Keine Homographie als
  Wahrheit: so bleibt die Messung auch bei Linsenverzeichnung (Weitwinkel-Amateurkameras) ehrlich.
- Ablauf: Klickseite `ml/calib/labelling/feld.html` (Artifact mit Speicher). Wo das Produkt ein Feld
  gefunden hat, ist es als Vorschlag eingezeichnet; Lukas bestätigt, zieht Punkte zurecht oder setzt
  4 bis 6 grob neu, mit Feldlinien als Live-Overlay. Unklares wird übersprungen. Danach
  `ml/calib/truth.py pull`: jedes Bild wird an seinen Linienpixeln verfeinert (Homographie plus
  radiale Verzeichnung k1, k2); die verfeinerten Punkte gelten nur, wenn sie im Median höchstens
  6 px von den Klicks abweichen.
- Bekannte Verzerrung: Vorschläge des Produkts können die Wahrheit zu ihm hin ziehen. Die
  Verfeinerung an den Linien und die Prüfung durch Lukas begrenzen das; korrigierte und bestätigte
  Bilder werden getrennt gezählt.
- Zwei Runden: zuerst die Entwicklungs-Stücke, später der Endtest.

Klickseiten (privat, Lukas öffnet sie): Runde 1 Entwicklung
https://claude.ai/artifact/FzGnPSymLMh4WXNKc78Af2 (63 Bilder, 10 mit Vorschlag des Produkts), Runde 2
Endtest https://claude.ai/artifact/Ja1U5iHdYxrprRicPxHVfE (69 Bilder, bewusst ohne Vorschläge, damit
nichts die Wahrheit zum heutigen Stand hinzieht). Runde 2 wird erst nach Runde 1 freigegeben.

### Ablauf nach den Klicks (Minuten)

1. Antworten holen: Artifact-Datenbank, Sammlung `truth`, als Dateien nach `<scratch>/answers1`.
2. `ml/calib/truth.py pull <scratch>/answers1/truth ml/calib/truth_dev.json --cache <cache> --overlays <scratch>/ov1`
   (Verfeinerung an den Linien, Overlays zur Kontrolle).
3. `ml/calib/evaluate.py ml/calib/results_base.json ml/calib/truth_dev.json --split dev --rows`
   (Klassen pro Stück, Anteile mit Intervallen).
4. `ml/calib/features.py ml/calib/results_base.json <cache> <scratch>/feat.json`, dann
   `ml/calib/features.py separate <scratch>/feat.json ml/calib/results_base.json ml/calib/truth_dev.json`:
   wie gut jedes Merkmal richtige von falschen Feldern trennt (AUC, Schwelle, die alle richtigen
   behält). Merkmale: die eigenen Prüfwerte des Produkts (Torpfosten, Linien, Boden, Leute auf
   dem Feld, Kamerahöhe, Blickwinkel), Übereinstimmung der projizierten Feldlinien mit den Linien
   jedes Bildes (Median und Minimum über die Bilder, also auch die Schwenkenden) und deren Spitze
   gegen das um 1.5 m verschobene Feld.

Geprüft mit künstlichen Klicks (Produkt-Felder als Wahrheit): die Kette läuft in unter einer
Minute und ergibt für diese Felder 0.1 m.

### Runde 1 (2026-11-17) und Runde 1b

Lukas hat in Runde 1 20 Bilder bearbeitet (15 mit Punkten, 5 übersprungen) und dann aufgehört: auf
Schwenkkameras sind kaum genug der benannten Punkte zu sehen, die Mittellinie fehlt oft, es dauert
lang und ist oft nicht eindeutig. Antworten: `ml/calib/data/round1_answers.json`.

Prüfung der Klicks (`ml/calib/clicks.py`, ein Modell durch alle Klicks): 8 der 15 Bilder sind
stimmig (Median 1 bis 4 px), 7 nicht (zu wenige Punkte für eine Gegenprobe oder 7 bis 740 px
Widerspruch). Nur die stimmigen zählen; sie decken 5 Stücke ab (c009, c013, c014, c018, c025).

**Runde 1b** (`ml/calib/labelling/feld2.html`, https://claude.ai/artifact/1VT7cj8DGNM9Lv8o3evq5b):
- Linien-Modus: Linie wählen (Seitenlinien, Torlinien, Mittellinie, 6 m, 9 m; Tasten 1 bis 9), dann
  zwei oder mehr Klicks irgendwo auf der Linie; der Klick rastet auf die nächste erkannte Linie
  ein (Linienmaske pro Bild, Shift oder Ziehen schaltet es aus).
- Mehr benannte Anhalter: Wechselmarken (15.5 und 24.5 m, nah und fern), 4-m-Marken, dazu alle
  bisherigen.
- Live-Feld aus Punkten und Linien, auch wenn die geraden Linien allein das Feld nicht festlegen
  (beide Seitenlinien und eine Torlinie legen 6 der 8 Freiheitsgrade fest): die offenen Richtungen
  werden durchsucht, die Bogen-Klicks entscheiden, dann eine nichtlineare Anpassung. Gleiches
  Verfahren in Python für die Wahrheit. Geprüft mit künstlichen Klicks aus einem echten Bild:
  exakt (0.05 px) ohne Rauschen; mit 2 bis 4 px Rauschen liegt die Wahrheit im Median 0.07 bis
  0.11 m, höchstens 0.39 m daneben.
- Wahrheit pro Bild: ein 1-m-Raster von Feldpunkten, das das angepasste Modell nahe den Klicks ins
  Bild legt; nur Punkte, die beim Stören jedes Klicks um 2 px um höchstens 0.3 m wandern.
  Verzeichnung wird erst ab 16 Gleichungen mitgeschätzt (mit wenigen Punkten erklärt ein
  verzeichnetes Modell auch falsch benannte Punkte).
- Reihenfolge: zuerst das Hauptbild jedes der 28 offenen Stücke (Mitte des Schwenks, bei fester
  Kamera das einzige Bild), danach die Schwenkenden. Die 5 Stücke mit stimmiger Wahrheit fehlen,
  Bilder aus Runde 1 sind mit Lukas' Punkten vorausgefüllt.
- Runde 2 (Endtest) wird vor der Freigabe auf dieselbe Seite umgestellt.

## 3. Metrik (`ml/calib/evaluate.py`)

- Fehler pro Wahrheitspunkt: Bildpunkt → Kamerabewegung → Kalibrierung → Feld, Abstand zur wahren
  Feldposition in Metern (gekappt bei 50 m). Pro Stück der Median.
- Klassen pro Stück: **richtig** (Feld akzeptiert, Median ≤ 1 m), **falsch akzeptiert** (Median
  > 1 m), **abgelehnt** (`needs_calibration`, mit `calibration_info.reason`).
- Anteile mit 95-%-Intervallen per Bootstrap über Hallen (2000 Ziehungen). Dazu: Anteil falsch unter
  den akzeptierten, Median-Fehler der akzeptierten.
- Eigene Messgrösse Verzeichnung: k1 der verfeinerten Wahrheit pro Stück; Anteil der Stücke mit
  starker Verzeichnung und Fehler mit und ohne Korrektur.

## 4. Messungen

### 4.1 Basis: Produkt heute (`main` e089b570, 2026-11-17)

Was `auto_calibrate` auf den 70 Stücken meldet (noch ohne Wahrheit, also ohne richtig/falsch):

| | Entwicklung (33) | Endtest (37) | alle (70) |
|---|---|---|---|
| Feld akzeptiert | 6 | 9 | 15 (21 %) |
| `no_floor` | 10 | 12 | 22 |
| `flat_view` | 8 | 8 | 16 |
| `court` | 8 | 4 | 12 |
| `camera_motion` | 1 | 3 | 4 |
| `few_people` | 0 | 1 | 1 |

62 Stücke haben eine bewegte Kamera (14 akzeptiert), 8 eine feste (1 akzeptiert). Auf
Sicht: bei akzeptierten Feldern liegt das Feld in der Schwenkmitte ungefähr richtig, an den
Schwenkenden daneben (Kamerabewegung). Fehler in Metern und der Anteil falsch akzeptiert folgen mit
der Wahrheit (Runde 1: Entwicklung, 63 Bilder).

### 4.2 Diagnose ohne Wahrheit (Entwicklung, 2026-11-17)

- **`flat_view` ist echt:** Die Brennweite der bewegten Kamera um den Faktor 0.5 bis 1.2 zu
  verändern, ändert den Blickwinkel kaum (c001, c014, c038: 7 bis 9 Grad). Die Kameras stehen
  tatsächlich tief (2.8 bis 4 m, Bankhöhe oder Tribüne unten). 7 der 33 Entwicklungs-Stücke.
- **`no_floor` kommt von der Kamerabewegung:** Die Linien eines einzelnen Bildes liegen im Median zu
  40 bis 66 % auf zwei Bodenrichtungen, alle Bilder zusammen nur zu 15 bis 33 % (alle 9
  `no_floor`-Stücke der Entwicklung; ein gutes Stück, c067: 84 % gegen 67 %). Die Drehungen sind
  zwischen den Bildern um etwa ein Grad oder mehr daneben, wie im Nachtrag von ADR 025 für die
  SGWH-Streams beschrieben, aber hier in fast allen Hallen.

Erste Wahrheit (Runde 1, 5 Stücke mit stimmigen Klicks): 4 abgelehnt (c009 `court`, c013
`no_floor`, c014 `flat_view`, c018 `court`), 1 falsch akzeptiert (c025: im Median 6.8 m daneben,
auf 132 Wahrheitspunkten). Zu wenig, um einen Prüfschritt zu eichen.

Vorläufige Sichtprüfung der 6 heute akzeptierten Entwicklungs-Felder (keine Wahrheit, nur zum
Entwickeln): c008 und c061 falsch, c040 und c067 plausibel, c025 und c039 in der Schwenkmitte nah,
an den Schwenkenden daneben. Die heutigen Prüfungen (Kamerahöhe, Leute auf dem Feld, Torpfosten)
lassen also falsche Felder durch.

### 4.3 Konzept: tiefe Kameras (`flat_view`), noch kein Code

Heute: Bodenlage aus den Linienrichtungen, Massstab aus der Grösse der Leute, dann eine Draufsicht
und die Feldsuche darin. Unter etwa 10 Grad Blickwinkel ist das schlecht gestellt: ein Zehntelgrad
Fehler in der Bodenlage verschiebt Punkte in 25 m Entfernung um Meter, und die ferne Hälfte ist in
der Draufsicht auf wenige Pixel gestaucht. 7 der 33 Entwicklungs-Stücke (Bankhöhe, Tribüne unten,
Fernsehkamera mit Schnitten) betrifft das.

Vorschlag: das Feld direkt **im Bild** anpassen, pro Linienbild.
- Unbekannte: Kameraort (x, y, z) und Verzeichnung k1 gemeinsam für das Stück; Drehung und
  Brennweite pro Bild, Startwert aus der Kamerabewegung. Für eine feste Kamera ein Satz.
- Ziel: zweiseitiger Chamfer-Abstand zwischen den projizierten Handball-Linien und den Linien des
  Bildes (nur die Linienfarbe des Handballfeldes; die Farbe ist Teil der Hypothese), dazu Torpfosten
  und Spielerfüsse im Feld als weiche Bedingungen.
- Start: ein Raster von Kameraorten entlang der nahen Seitenlinie (x 0 bis 40 m, y -2 bis -12 m,
  z 2 bis 6 m), Blick zur Feldmitte, plus der Kandidat der Draufsicht, wo es einen gibt; jeweils
  lokal optimieren (mehrere Starts, weil die Linien entlang einander gleiten).
- Handball-eigene Formen gegen Verwechslungen auf Mehrsport-Böden: 6-m-Bogen mit geradem Stück,
  gestrichelte 9-m-Linie, Tore.
- Prüfung: dieselben Merkmale wie in 2 (Übereinstimmung mit den Bildlinien, scharfe Spitze,
  Schwenkenden), geeicht an der Wahrheit.
- Nebeneffekt: eine Anpassung pro Bild braucht keine über alle Bilder stimmige Kamerabewegung und
  kann darum auch bei `no_floor` helfen (Abschnitt 4.2).

Aufwand grob: klassische Anpassung im Bild 3 bis 5 Arbeitstage plus Messung auf der Wahrheit.
Langfristig robuster wäre ein gelerntes Modell für Feldlinien oder Feld-Keypoints (synthetische
Hallenbilder plus etwa 300 gelabelte Bilder, einige GPU-Stunden): 1 bis 2 Wochen, GPU nur nach
Rücksprache.

### 4.4 Fall: Fernsehbild mit Zoom und Schnitten (`camera_motion`): geparkt

**Entscheid 2026-11-17 (Hauptsitzung): geparkt, 4 bis 5 Tage, 70 bis 85 % Abdeckung.** Nur 4 von 70
Stücken, das Produkt zielt auf Vereinskameras; Vorrang hat die strengere Feldprüfung, danach tiefe
Kameras. Die App zeigt für diesen Fall eine klare Meldung (UX-Sitzung).

Anlass: der erste echte Staging-Lauf (NLB 2017, 99 min) scheitert mit `camera_motion`: Brennweite
1.4 Bildbreiten, Zoom bis x6.5, 165 Schnitte, Schwenk 107 Grad. Im Testsatz 4 von 70 Stücken (c012
und drei im Endtest), dazu Fernsehbilder, die heute mit anderem Grund scheitern (c054, Olympia).

Heute rechnet die Kamerabewegung über Schnitte hinweg weiter (`cuts` zählt die Bilder ohne Anschluss)
und baut ein Panorama, das die Halle mehrfach zeigt; die Prüfung `check_motion` lehnt dann zu Recht ab.

Vorschlag "pro Einstellung":
1. Das Video an den Schnitten in Einstellungen teilen; jede Einstellung bekommt ihre eigene
   Kamerabewegung und ihr eigenes Hallenbild (kurze Einstellungen unter etwa 3 s fallen weg).
2. Die Einstellungen nach Kamera gruppieren: Hallenbilder gegeneinander mit `hallmatch` (SIFT, eine
   Homographie, gleiche Kamera am gleichen Ort; ADR 025 Nachtrag 2). Die Hauptkamera ist die Gruppe
   mit der meisten Spielzeit.
3. Das Feld einmal für die Hauptkamera bestimmen: automatisch auf ihrer längsten, weitesten
   Einstellung, oder mit Klickpunkten einmal pro Spiel; dann über die Hallen-Homographien auf jede
   Einstellung dieser Kamera übertragen. Andere Kameras (hinter dem Tor, Nahaufnahmen, Wiederholungen)
   bekommen keine Positionen und werden als solche markiert.

Abdeckung: in Fernsehbildern zeigt die Hauptkamera erfahrungsgemäß den grössten Teil der Spielzeit,
Wiederholungen und Nahaufnahmen fallen meist in Unterbrechungen; geschätzt 70 bis 85 % der Spielzeit,
zu messen als Anteil der Spielbilder (Pausenerkennung), die der Hauptkamera zugeordnet werden.
Risiken: starker Zoom innerhalb einer Einstellung (die Brennweite der Bewegung ist bei reinem
Schwenk schlecht bestimmt), Fehlschnitte bei schnellem Schwenk, und die Prüfung gegen falsche Felder
(Abschnitt 4.2) gilt hier genauso.

Aufwand grob: Teilen an Schnitten und Bewegung pro Einstellung 1 bis 2 Tage, Gruppieren mit
`hallmatch` und Übertragen 1 bis 2 Tage, Messung (Abdeckung und Fehler auf den Testsatz-Stücken mit
Schnitten, dazu das Staging-Video) 1 Tag: zusammen etwa 4 bis 5 Arbeitstage. Berührt den
Beobachtungsdurchlauf (Kamerabewegung) nur über deren Ergebnis; `observe()` selbst bleibt.

### 4.5 Fernseh-Clips Horgen 2017 (10 min), Sichtprüfung 2026-11-17

Die Integrations-Sitzung fand auf zwei 10-min-Ausschnitten des Staging-Videos (Horgen 2017, NLB)
ein automatisches Feld (310 bzw. 283 Spuren), auf dem ganzen Video nicht (`camera_motion`). Feld
des Produkts auf je 4 Bildern über die Kamerabewegung gelegt: grob plausibel (Orientierung, ferne
Seitenlinie an der Wand, Mittellinie durch den Mittelkreis in h2), aber die 6-m-Bögen liegen
teils sichtbar neben den Toren, geschätzt 1 bis 3 m. Messung: die 8 Bilder hängen als Zusatz in
Runde 1b (direkt nach den 28 Hauptbildern), Produkt-Abbildung in `ml/calib/data/horgen_product.json`.
Die Halle `SGHorgen` gehört im Testsatz zum Endtest: diese Bilder nur zur Prüfung, nicht zum
Abstimmen.

### 4.6 Zwischenauswertung Runde 1b (2026-11-17, 49 Bilder gespeichert)

Klicks: 29 Bilder mit Klicks, 20 übersprungen. Stimmig (`clicks.py`: Median <= 5 px, Maximum
<= 20 px, mindestens 10 Gleichungen; ein Ausreisser-Klick über 15 px darf wegfallen, höchstens
ein Fünftel): 16 Bilder; 3 haben zu wenige Klicks für eine Gegenprobe, 10 widersprechen sich
(meist ein bis zwei Klicks auf einer Nachbarlinie). Zusammen mit Runde 1: Wahrheit für 15
Entwicklungs-Stücke.

Heutige Auto-Kalibrierung auf diesen 15 Stücken (Entwicklung, `results_base.json`):

| Klasse | Stücke | Anteil (95 % über Hallen) |
|---|---|---|
| richtig (Median <= 1 m) | 0 | 0 % |
| falsch akzeptiert | 3 (c008 28.0 m, c025 6.8 m, c039 5.9 m) | 20 % [0, 40] |
| abgelehnt | 12 (4 `flat_view`, 4 `no_floor`, 3 `court`, 1 `camera_motion`) | 80 % [60, 100] |

Alle akzeptierten Felder mit Wahrheit sind falsch.

Horgen-Fernseh-Clips (nur Prüfung, Endtest-Halle): h1 im Median 0.65 m (p90 0.99 m, 1 Bild mit
Wahrheit), h2 0.96 m (p90 1.43 m; 3 Bilder: 0.18, 1.03, 1.41 m). Die Sichtschätzung (1 bis 3 m)
war zu streng; die Felder sind an der Grenze zu "richtig".

Erster grober Vorschlag für die strengere Prüfung (noch nicht geeicht, 3 falsche gegen 2
fast richtige Felder): akzeptieren nur mit Torpfosten-Treffer `goal_score` >= 0.45, Linien
`line_score` >= 1.0 und Boden `floor_fit` >= 0.45. Das lehnt c008 (Torpfosten 0.32), c025 (0.37)
und c039 (Boden 0.35) ab und behält beide Horgen-Felder (0.74/1.30/0.64, 0.55/1.22/0.55). Von
den 15 heute akzeptierten Feldern im ganzen Testsatz blieben 3 (c003, c030, c067).

## 5. Was nicht geholfen hat

| Was | Wo | Zahlen | Warum verworfen |
|---|---|---|---|
| Schwelle `MIN_VIEW_DEG` von 10 auf 3 Grad | 6 `flat_view`-Stücke der Entwicklung | 3 Felder neu akzeptiert, alle 3 auf Sicht falsch (Linien neben den Feldlinien) | Die Draufsicht ist bei tiefer Kamera unzuverlässig; die Schwelle schützt zu Recht. Tiefe Kameras brauchen eine Anpassung im Bild. |
| Brennweite bewegter Kameras skalieren (0.5 bis 1.2) | c001, c014, c038 | Blickwinkel bleibt bei 7 bis 9 Grad; c038 bei 1.2 akzeptiert, ohne Prüfung | Nicht die Ursache von `flat_view`. |
| Radiale Verzeichnung k1 (-0.3 bis +0.06) auf den Liniensegmenten | 9 `no_floor`-Stücke und c000 | Bodenanteil ändert sich um höchstens 0.03, keines erreicht 0.35 | Nicht die Ursache von `no_floor`; die Kamerabewegung ist es. |
| Drehung jedes Linienbildes nachkorrigieren (höchstens 3 Grad pro Achse, `ml/calib/motion_refine.py`, `run.py calibrate --refine`) | 33 Entwicklungs-Stücke, Hallenbild neu gerechnet | Bodenanteil steigt (z. B. 0.18 auf 0.34); Felder 6 auf 8: neu c009, c013, c038, verloren c025; auf Sicht c009 und c038 falsch, c013 unklar; Korrekturen im Median 2 bis 3 Grad | Mehr falsch akzeptierte Felder; die Korrektur passt jedes Bild an die Linien an, auch an die falschen (Überanpassung). Verworfen. |
| Kalibrierung auf dem besten Fenster (8 Linienbilder, etwa 29 s, höchster Bodenanteil; Idee der Integrations-Sitzung, `ml/calib/experiments/best_window.py`) | 33 Entwicklungs-Stücke | Felder 6 auf 8: neu c013, c033, c038, c048, c051, weg c008, c039, c040; alle 5 neuen auf Sicht falsch (c051 höchstens teilweise) | Der hohe Bodenanteil im Fenster kommt auch von wenigen Linien (Überanpassung), die Feldsuche findet dort ebenso falsche Felder. Verworfen. Muster aus drei Versuchen: jede Lockerung bringt vor allem falsch akzeptierte Felder; zuerst braucht es einen Prüfschritt. |
| Prüfwert "Feldlinien auf erkannten Segmenten" (Anteil der projizierten Feldlinien innerhalb 4 px der gespeicherten Liniensegmente, Median über die Linienbilder) | 6 akzeptierte Entwicklungs-Stücke und die 3 neuen | alle 0.07 bis 0.17; die auf Sicht falschen (c008 0.08, c009 0.12, c038 0.17) nicht tiefer als die plausiblen (c040 0.08, c067 0.14) | Die gespeicherten Segmente sind zu dünn; ein Prüfwert braucht die Linien der Bilder selbst. Neu mit der Wahrheit. |
