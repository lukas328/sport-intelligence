# Produkt-Analyse: Integration der Forschung (Stand 2026-11-16)

Auftrag von Lukas (2026-11-16): den aktuellen besten Stand jetzt ins Produkt bringen und die Analyse
als ganzes Produkt denken, nicht nur den Ball. Testphase: Lizenzen sind vorerst egal (die Ballnetze
ab Runde 3 enthalten DeepSport, nur Forschung; vor einem echten Livegang braucht es Netze ohne
DeepSport, siehe `docs/plans/tracking-strategie.md` Abschnitt 9). Massstab: **Kosten unter etwa
1 Euro pro Spiel**; die Dauer ist zweitrangig.

Rollen: Die **Hauptsitzung** (Ball-Forschung, Projektleitung, Merges nach `main`) koordiniert. Die
**Kalibrierungs-Sitzung** (Zweig `claude/kalibrierung`, ab 2026-11-16) übernimmt Schritt 5, Kalibrierung, parallel und mit eigenem Plan in `docs/plans/kalibrierung.md`; sie meidet `observe()`, Ball und Job-Runner. Die
**Integrations-Sitzung** setzt diesen Plan um, auf ihrem eigenen Zweig, mit Pull Requests; die
Hauptsitzung merged bei grüner CI. Die **UX-Sitzung** besitzt Website und Deploy-Workflow
(`infra/`, `.github/workflows/deploy.yml`, `wrangler.jsonc`, `apps/site`): Änderungen an Infra und
Deploy vorher über die Hauptsitzung abstimmen.

## 1. Die Analyse-Kette heute (Kartierung 2026-11-16, mit Dateiverweisen)

- **Ablauf:** Upload → `handball_worker.ingest.run_ingest` (Queue `pipeline`, CPU-Worker): Proxy
  1280 px, 25 fps, crf 26 (`apps/worker/src/handball_worker/media/transcode.py`) → API
  `_enqueue_analysis` (`apps/api/src/handball_api/services/videos.py`) → `handball_gpu_worker.analysis.run_analysis`
  (Queue `gpu`) → Ergebnis über `/internal/jobs/{id}` → `_apply_analysis_result`.
- **Lernender Pfad** (`apps/gpu-worker/src/handball_gpu_worker/analysis.py` `_run_learned`):
  Beobachtungsdurchlauf `handball_vision.observe.observe` (Kamerabewegung jedes Bild; YOLOX-S
  COCO alle `HB_DETECT_EVERY`=3 Bilder, Personen und "sports ball" ab 0.15; Rückennummern PP-OCR;
  ReID und Rollen nur wenn die ONNX-Dateien da sind, im Image fehlen sie) → Spieluhr
  (Overlay/Hallentafel) → Kalibrierung (Klickpunkte, Hallenreferenz, automatisch) → Tracking und
  Teams (`observe.track`, `pipeline._finish`) → Ball (`ballpossession.from_observations` mit
  `balltrack.track`) → Tor- und Wurf-Kandidaten (`goalcandidates`, ohne Ball) → Torwurf-Positionen
  (`shots`) → Ereignisse (`events.detect_events`, nur Positionen) → Payload.
- **Ball:** YOLOX findet den Ball "praktisch nie" (`ml/models/yolox-coco.md`); der Produkt-Tracker
  `balltrack` schafft auf Gold v1 selbst mit den Forschungskandidaten nur 32 %. Der Ballpfad wird
  **nicht gespeichert**; `result.extra["ball"]` (Ballbesitz, Pässe) landet in
  `video_assets.analysis["stats"]`, liest aber niemand; die Taktik-Kamera der Web-App bekommt immer
  `"ball": []` (`apps/api/src/handball_api/services/graphics.py`).
- **Hardware:** Der "GPU-Worker" auf Azure Staging ist ein CPU-Container (2 vCPU, 4 GiB,
  `infra/terraform/azure/main.tf`). `apps/gpu-worker/Dockerfile.cuda` (onnxruntime-gpu,
  `HB_DETECT_EVERY=1`) wird nirgends gebaut oder deployt. Kein torch in den Images. Die
  Kostenabrechnung `GpuBackend` wird für die Analyse umgangen.
- **Laufzeit heute:** etwa 2 x Videolänge auf 4 CPU-Kernen (`docs/runbooks/deploy.md`); auf
  Staging (2 vCPU) langsamer. Ein ganzes echtes Spiel auf Staging ist noch nie gelaufen
  (`docs/plans/azure-staging.md`).
- **Schwach oder ungemessen:** Kalibrierung (Feld in 7 bis 8 von rund 40 Spielen richtig, ADR 025
  Nachtrag, `ml/ball/LINEAGE.md` Abschnitt 7); Spieler-Tracking auf echten Spielen nie gemessen
  (synthetisch MOTA 0.40, IDF1 0.30); Ereignisse ohne Ball (Würfe, Paraden, Ballverluste fehlen);
  Rückennummern und ReID nicht ausgeliefert.

## 2. Was die Forschung liefert (Stand 2026-11-16, Details `ml/ball/LINEAGE.md`)

- Ballnetze mit 3 Bildern Eingabe (Bild t-G, t, t+G; G = 2 bei 25/30 fps, 3 bei 50/60 fps):
  BallHR `ml/ball/ballhr.py` (hr1) und BallHRP `ml/ball/ballhrp.py` (hrp1, timm HRNet-W18).
  Gewichte: Kaggle-Dataset `handball-ball-hrmodels` (`ball_hr1.pt`, `ball_hrp1.pt`). Ausgabe:
  Heatmap in Stride 4, Spitzen wie `ml/gold/kaggle/prelabel_gpu.py` `peaks()`.
- Tracker v2 `ml/gold/tracker.py` (Doppelbild-Schritt, längere Lücken für schnelle Bälle, gelernte
  Bewertung `ml/gold/tracker_rescore.py`, Gewichte ohne OWLv2 `ml/gold/data/tracker_rescore_noowl.json`,
  Sicherheit pro Punkt `track_clip_conf`). Auf Gold v1 mit hr1 + hrp1 ohne OWLv2: 80.0 % aller
  Bälle [74.7, 84.9], 83.3 % der schnellen [75.2, 90.1].
- CPU-Zeit pro Bild (4 Kerne, gemessen 2026-11-16): BallNet3 219 ms (1280 px) / 127 ms (960 px);
  BallHR 475 / 271 ms; BallHRP 886 / 501 ms. Ein Spiel hat bei 25 fps etwa 90 000 Bilder: auf der
  CPU nicht machbar, das Ballnetz braucht eine GPU.

## 3. Plan der Integrations-Sitzung (in dieser Reihenfolge)

1. **Messen, bevor gebaut wird.**
   - Die heutige Produktkette (YOLOX-Ball plus `balltrack`) einmal auf Gold v1 messen (CPU,
     `ml/gold/eval_ball.py` als Vorbild). Das ist die Vergleichszahl.
   - Laufzeit pro Stufe für ein echtes Spiel lokal: Werte aus `timings_s`.
2. **Ball v2 ins Produkt, hinter einem Schalter** (`HB_BALL_MODEL`; ohne die Datei bleibt der alte
   Weg).
   - **ONNX-Export** von hr1 (und hrp1) mit fp16-Variante: einmalig in `ml/`, mit torch in einer
     eigenen Umgebung. Die Modelldatei kommt mit SHA-Prüfung ins CUDA-Image, wie YOLOX.
   - **Ballkandidaten in `observe()`:** Ringpuffer für die 3 Bilder, Ballnetz auf jedem 2. Bild
     und nur im Spiel (die Pausenerkennung gibt es). Batching über mehrere Bilder.
   - **Kandidaten speichern** in `observations.npz`, damit Neuberechnungen ohne GPU gehen.
   - **Tracker v2 und Bewertung nach `packages/vision`** übernehmen (das Produkt importiert nichts
     aus `ml/`), mit Tests:
     - Adapter Bild- und Leinwand-Koordinaten;
     - Fenster pro Spielabschnitt statt pro Clip;
     - Sicherheit und "weiss nicht".
   - **`ballpossession`** auf den neuen Pfad umstellen; die Tests in
     `packages/vision/tests/test_ballpossession.py` und `test_balltrack.py` anpassen.
   - **Ballpfad speichern** (z. B. als Parquet wie `tracks.parquet`) und an `graphics.py` für die
     Taktik-Kamera liefern.
3. **GPU-Verarbeitung.**
   - Das CUDA-Image in CI bauen.
   - Ausführungsort wählen, mit Kosten pro Spiel als Kriterium: Azure Container Apps mit
     serverloser GPU, oder das GpuBackend `modal` umsetzen (Modal-Guthaben vorhanden, Jobs bisher
     nur aus der lokalen Sitzung).
   - Den Ausführungsort mit der UX-Sitzung abstimmen, weil Infra und Deploy bei ihr liegen.
   - Die Kostenabrechnung für die Analyse einschalten.
4. **Effizienz** bis unter 1 Euro pro Spiel:
   - fp16 und Batching;
   - Ballnetz auf jedem 2. Bild, kleinere Eingabe;
   - YOLOX mit `HB_DETECT_EVERY` so selten wie vertretbar;
   - Kamerabewegung (dominiert auf der GPU laut Runbook);
   - nur ein Netz statt Ensemble, wenn der Verlust klein ist.
   - Rückennummern billiger (vorgezogen 2026-11-17, Staging-Timeout): Gate pro Spielerbox und
     Zeitbudget `HB_NUMBER_BUDGET`, siehe Abschnitt 4. Kostet etwa ein Viertel der sicher
     gelesenen Nummern. Auf der GPU `NUMBER_EVERY` wieder dichter stellen, dort ist die
     Laufzeit nicht der Engpass (Entscheid Hauptsitzung).
   - Jede Änderung mit Laufzeit, Kosten und Gold-Wert dokumentieren.
5. **Danach die übrigen Stufen**, priorisiert nach Nutzen fürs Produkt:
   - Kalibrierung (grösster Blocker für Taktiktafel und Wurfzonen); Kalibrierungs-Sitzung, Stand
     2026-11-17 (`docs/plans/kalibrierung.md`): Testsatz 70 Stücke in 67 Hallen mit Klick-Wahrheit;
     heute auf der Entwicklung 1 von 30 Feldern richtig, 5 falsch akzeptiert; strengere Feldprüfung
     senkt die falsch akzeptierten auf 0 von 30 (richtig bleibt 1); Endtest 2026-11-18 (28 Stücke in
     26 Hallen): vor der Prüfung 1 richtig, 7 falsch akzeptiert, mit Prüfung 0 richtig, 2 falsch
     akzeptiert (7 %); Empfehlung Linien-Klicks pro Halle (Draft-PR #81);
   - Ereignisse mit Ball (Würfe, Paraden, Ballverluste aus Ballpfad plus Wurf-Kandidaten);
   - Spieler-Tracking auf echten Spielen messen;
   - Rückennummern und ReID ins Image.

Jeder Schritt: Pull Request mit grüner CI, Messwerte im PR und hier nachgetragen.

## 4. Stand und Messwerte (nachgeführt)

### Schritt 1: die heutige Kette gemessen (2026-11-16)

**Ball auf Gold v1** (`ml/gold/eval_product_ball.py`, 42 Clips, 12 px, 95 % Bootstrap über Clips):
`observe()` mit YOLOX-S "sports ball" (Schwelle 0.15, jedes 3. Bild wie im CPU-Image), Ballpfad genau
wie `ballpossession.from_observations` (Leinwand, `balltrack`, `min_score` 0.35), ohne Uhr-Filter.

| Mass | alle | schnelle |
|---|---|---|
| Ballpfad trifft den Ball | **0.2 %** [0.0, 0.7] | 0.3 % [0.0, 1.0] |
| Pfad gibt überhaupt einen Punkt | 1.0 % | 0.7 % |
| YOLOX-Box am Ball (beobachtete Bilder) | 2.7 % [0.8, 5.0] | 6.6 % [2.1, 11.7] |

Die heutige Kette liefert also praktisch keinen Ball. YOLOX auf jedem Bild (CUDA-Image) wurde nicht
gerechnet: bei 2.7 % Detektor-Treffern kann daraus kein brauchbarer Pfad werden.

**Laufzeit pro Stufe** (`ml/integration/profile_analysis.py`: `run_analysis` lokal, S3 und Reporter
durch lokale Attrappen ersetzt, Einstellungen des CPU-Images; 4 CPU-Kerne; Video: 15 min aus
AT_Cup_Feldkirch_Bregenz_2021, 5 Segmente zu 3 min, mit der Produkt-Umwandlung auf 1280 px / 25 fps):
| Stufe | Sekunden | Anteil | x Videolänge |
|---|---|---|---|
| Proxy-Umwandlung (Ingest, CPU-Worker) | 111 | eigener Job | 0.12 |
| Beobachtung gesamt (`observe`) | 3 928 | 100 % | 4.36 |
| davon Rückennummern (PP-OCR, alle 6 Bilder) | 2 560 | 65 % | 2.84 |
| davon YOLOX (alle 3 Bilder) | 850 | 22 % | 0.94 |
| davon Kamerabewegung (jedes Bild) | 256 | 7 % | 0.28 |
| davon Hallentafel lesen | 155 | 4 % | 0.17 |
| davon Linien, Trikotfarben | 35 | 1 % | 0.04 |
| Kalibrierung | 11 | | 0.01 |

Lesart: Die CPU-Kette braucht etwa **4.4 x Videolänge**, ein 60-Minuten-Spiel also rund 4.4 h auf 4
Kernen (das Runbook nennt 2 x; seither kamen Rückennummern und Hallentafel dazu). Zwei Drittel davon
sind die Rückennummern. Die Kalibrierung brach mit `flat_view` ab (Kamera zu flach, Klickpunkte
nötig); Tracking, Ball und Ereignisse liefen deshalb nicht und fehlen hier. Sie sind nach dem
Kalibrierungsteil billig (Sekunden bis Minuten), müssen aber auf einem Spiel mit Kalibrierung
nachgemessen werden. Während der Messung liefen zeitweise kurze Tests mit 1 bis 2 Threads mit; die
Zahlen sind eher etwas zu hoch. Der Hebel Rückennummern gehört zu Schritt 4.

### Schritt 2: Ball v2 hinter dem Schalter (Code fertig, gleicher PR)

- **Tracker-Port** `packages/vision/handball_vision/balltrack2.py` (Tracker v2 mit Bewertung ohne
  OWLv2): auf allen 11 752 Gold-Bildern dieselben Punkte wie `ml/gold/tracker.py`
  (`ml/integration/parity_tracker.py`; Regressionstest mit Clip g10 in
  `packages/vision/tests/test_balltrack2.py`). Über ganze Videos läuft er in 8-s-Fenstern
  (`track_windows`, so lang wie die Gold-Clips): auf Gold identisch.

| Variante (Gold v1, ohne OWLv2) | alle | schnelle | 50/60 fps |
|---|---|---|---|
| hr1 + hrp1, jedes Bild (Standard) | **80.0 %** [74.1, 85.0] | **83.3 %** [74.9, 90.0] | 75.3 % |
| hr1 + hrp1, Netz nur jedes 2. Bild | 74.4 % [68.4, 79.7] | 72.5 % [63.4, 80.7] | 66.9 % |
| nur hrp1 | 76.1 % [70.1, 81.4] | 78.3 % [67.8, 86.6] | 69.9 % |
| nur hrp1, jedes 2. Bild | 69.2 % | 67.5 % | 63.2 % |
| nur hr1 | 70.9 % [63.5, 77.4] | 79.3 % [69.8, 87.0] | 62.1 % |

  Folgerung: Das Ballnetz läuft auf jedem Bild (`HB_BALL_EVERY=1`); jedes 2. Bild kostet 6 Punkte,
  bei schnellen Bällen 11.
- **ONNX-Export** `ml/ball/export_onnx.py` (Sigmoid im Graphen, Batch und Grösse dynamisch,
  Checkpoint mit `weights_only=True`): Abweichung zu torch 1e-7 (fp32), 1e-4 (hr1 fp16) und 6e-4
  (hrp1 fp16). Gegenprobe auf Gold-Clip g10 mit dem Produkt-Pfad (`ballnet.BallCandidates` auf dem
  Clip-Video): stärkster ONNX-Punkt in 382 von 394 Bildern unter den 5 Kaggle-Kandidaten, der
  Tracker trifft gleich viele Gold-Bälle (7 von 27, nur hr1, schwerer Clip). Die Abweichungen kommen
  vom neu kodierten Clip-Video (crf 20). CPU: hr1 etwa 1.6 s pro Bild mit einem Thread.
- **Schalter** `HB_BALL_MODEL` (Entscheid Hauptsitzung 2026-11-16): lokale Dateien oder Schlüssel im
  Artifacts-Bucket (z. B. `models/ball/ball_hrp1-<sha12>.onnx`), `HB_BALL_MODEL_SHA256` in derselben
  Reihenfolge (für Schlüssel Pflicht), Cache in `HB_BALL_CACHE_DIR`. Zwei Einträge = Ensemble, einer =
  Einzelnetz. Fehlt etwas oder stimmt die SHA nicht: alter YOLOX-Weg, Warnung im Log und
  `stats.ball_model_status`. Kein Download im Image-Build, keine Änderung an Build, CI oder ACR.
- **Ballkandidaten in `observe()`** (`ballnet.BallCandidates`: Ringpuffer für Bild t-G, t, t+G,
  Stapel von `HB_BALL_BATCH`), gespeichert in `observations.npz` (`ball_cands`, gerundet auf 0.01 px
  und 1e-4, damit eine Neuberechnung denselben Pfad gibt). `ballpossession` nimmt sie, wenn
  vorhanden (`ball_model: "ballnet"`), sonst YOLOX (`"yolox"`); `versions.ball` nennt die Netze.
- **Lizenz (Testphase):** hr1 und hrp1 enthalten DeepSport (nicht kommerziell). Vermerkt in
  `ballnet.py`, `export_onnx.py` und den Settings; vor einem Livegang durch Netze ohne DeepSport
  ersetzen (`tracking-strategie.md` Abschnitt 9, Prio 6).
- **Schritt 2b (Ballpfad und Taktik-Kamera):** Mit Ballnetz schreibt der Worker den Pfad als
  `analysis/ball.bin` (float32-Zeilen t_ms, x, y in Proxy-Bildpixeln, Sicherheit; etwa 1.4 MB pro
  Spiel) und meldet ihn als `ball_path` (wird in `video_assets.analysis` übernommen). Die
  Taktik-Kamera bekommt `ball` als Halter-Abschnitte aus `stats.ball.possessions`, nur wenn
  `ball_model == "ballnet"`: Der YOLOX-Weg (0.2 % auf Gold) wird nicht angezeigt. Halter ohne Team
  oder Rückennummer bleiben eine Lücke. Feldpositionen des Balls (in der Luft nicht aus der
  Boden-Homografie) folgen mit den Ereignissen in Schritt 5.
- **Offen in Schritt 2:** Netze in den Staging-Bucket laden (Skript, nur mit Freigabe von Lukas);
  GPU-Laufzeit messen (Schritt 3); ein echtes Spiel mit Kalibrierung und Ballnetz durchrechnen.

### Rückennummern und Hallentafel billiger (vorgezogen 2026-11-17)

Anlass: Auf Staging (2 vCPU) brach die Analyse von Lukas' ganzem Spiel nach dem RQ-Timeout von
6 h ab, im Stack die Texterkennung (`hallboard.py`, `numbers.py`). Im CPU-Profil (Abschnitt
oben) sind die Rückennummern zwei Drittel der Beobachtung.

**Was geändert ist:**
- `numbers.NumberGate` (Schalter `HB_NUMBER_GATE`, Standard an): Spielerboxen werden von
  Nummernbild zu Nummernbild verknüpft. Gelesen wird eine Box nur in diesen Fällen:
  - sie ist neu;
  - die Nummer ist noch nicht gesetzt (6 sichere Lesungen);
  - nach einem Fehlversuch nach höchstens 0.5 s wieder;
  - eine gesetzte Nummer wird alle 5 s nachgeprüft;
  - höchstens 6 Boxen pro Nummernbild.
- `HB_NUMBER_BUDGET` (Standard 0.75): höchstens so viele CPU-Sekunden Rückennummern pro
  Videosekunde; darüber werden Nummernbilder ausgelassen (Zähler `number_frames_skipped`).
- Hallentafel: Die Ganzbildsuche ohne Fund wartet zunehmend länger (4 s bis 60 s, ein Fund setzt
  zurück), dazu ein Budget von 10 % der Videozeit (`stats.skipped`, `stats.seconds` in der
  Zusammenfassung).
- Zähler pro Lauf in `stats.observe_counters` (gelesene Crops, angebotene und gelesene Boxen,
  ausgelassene Nummernbilder).

**Messung** (4 CPU-Kerne, `ml/integration/profile_analysis.py`). Qualität auf Ebene der Lesungen
aus `observations.npz`:
- sichere Lesungen (Konfidenz ab 0.8);
- Nummern mit mindestens 3 sicheren Lesungen, denn die Abstimmung pro Spur braucht 3.

Spuren mit Nummer liessen sich nicht vergleichen: Auf beiden Spielen scheitert die Kalibrierung
über die ganze Länge, ohne Feld gibt es kein Tracking. Die Kalibrierung aus einem einzelnen
40-s-Fenster von Bregenz-Schwaz ist laut Kalibrierungs-Sitzung vermutlich ein Glückstreffer und
wird für keine Messung verwendet.

| Lauf | x Videolänge | Rückennummern s | Crops | sichere Lesungen | Nummern mit ≥ 3 |
|---|---|---|---|---|---|
| Bregenz-Schwaz 15 min, ohne Gate | 2.33 | 1 294 | (alle) | 123 | 13 |
| mit Gate (erste Fassung, verworfen) | 1.33 | 412 | | 40 | 6 |
| **mit Gate** | **1.68** | **687** | 30 867 | 71 | **10** |
| mit Gate und Budget 0.75 | 1.61 | 626 | 28 284 | 65 | 9 |
| Feldkirch-Bregenz 3 min, ohne Gate | 2.47 | 252 | 11 110 | 701 | 21 |
| **mit Gate** | **1.88** | **142** | 6 002 | 321 | **16** |

Lesart:
- **Laufzeit:** Die Rückennummern kosten etwa die Hälfte (minus 44 bis 47 %), die ganze
  Analyse ein Viertel bis ein Drittel weniger.
- **Nummernverlust:** Er ist echt und wird bewusst in Kauf genommen. Die Nummern mit mindestens
  3 sicheren Lesungen fallen auf etwa drei Viertel (Bregenz 13 auf 10, Feldkirch 21 auf 16).
- **Warum kein Gate verlustfrei ist:** Die Nachspielung des Gates auf den Lesungen ohne Gate
  (Rasterversuch über Rückzug, Nachprüfung, Obergrenze) zeigt es. Die lesbaren Momente (Rücken zur
  Kamera, scharf) sind kurz und nicht vorhersagbar. Bei gleichen Kosten ist das Gate etwas besser
  als einfach seltener lesen (`NUMBER_EVERY` 12: 14 statt 16 auf Feldkirch, 9 statt 10 auf
  Bregenz).
- **Hallentafel:** Auf Feldkirch (kein TV-Overlay, Hallentafel-Pfad) gibt es gleich viele
  Uhr-Lesungen (148 ohne, 145 mit den neuen Grenzen). Die Kosten dort sind klein (16 s auf 3 min);
  die Grenzen schützen Aufnahmen, auf denen die Tafel nie gefunden wird.
- **Entscheid Hauptsitzung 2026-11-17:** Ein abgebrochenes Spiel liefert gar keine Nummern, das
  wiegt schwerer. Darum Gate und Budget als Standard.
- **Grobe Hochrechnung für Staging (2 vCPU, etwa doppelt so langsam):**
  - Rückennummern höchstens 0.75 x Videolänge, durch das Budget gedeckelt;
  - YOLOX und Kamera auf 4 Kernen etwa 0.8 bis 0.9 x, auf 2 vCPU etwa 1.7 x;
  - ein 60-min-Spiel damit etwa 2.5 bis 3 h, unter dem Timeout von 6 h.
  - Ungemessen auf Staging selbst.

### Schritt 3 vorbereitet: CUDA-Image mit Ballnetz (2026-11-17, ohne Deploy)

- `apps/gpu-worker/Dockerfile.cuda` hat jetzt die GPU-Einstellungen:
  - YOLOX auf jedem Bild;
  - Rückennummern wieder dicht: `HB_NUMBER_EVERY=3`, kein Gate, kein Budget (Entscheid
    Hauptsitzung; gegen die gemessenen Kosten pro Spiel aus Modal-Auftrag 13 zu prüfen);
  - Ballnetz auf jedem Bild, Cache unter `/tmp/handball-models`.

  Die Netze kommen zur Laufzeit aus dem Artifacts-Bucket (`HB_BALL_MODEL`,
  `HB_BALL_MODEL_SHA256`), nicht aus dem Image.
- Lokal gebaut (Image 7.7 GB) und im Container auf der CPU geprüft: 6 s Video, beide Netze
  (fp16) aus einem Dateipfad. Ergebnis:
  - `ball_model_status: ok`, `versions.ball: ball_hr1_fp16+ball_hrp1_fp16`;
  - Ballkandidaten auf 148 von 150 Bildern in `observations.npz`.

  Ohne GPU brauchen die Netze dort etwa 1 s pro Bild (beide zusammen). Die GPU-Laufzeit misst
  Modal-Auftrag 13.
- Hinweise zum lokalen Build:
  - Docker Hub antwortete mit 429; die Basis-Images kamen von `nvcr.io` und
    `mirror.gcr.io`, das Dockerfile bleibt bei den Original-Namen.
  - Der Build in dieser Umgebung braucht `--network host`, weil der Proxy auf 127.0.0.1
    lauscht.
- Offen, mit der UX-Sitzung abzustimmen:
  - das CUDA-Image in der CI bauen (Grösse 7.7 GB, Laufzeit);
  - den Ausführungsort bestimmen (Azure Serverless T4, `docs/plans/gpu-analyse.md`).

### Schritt 5 vorbereitet: ReID und Rollen aus dem Bucket (2026-11-17)

- `HB_REID_MODEL` und `HB_ROLE_MODEL` können jetzt wie die Ballnetze Schlüssel im
  Artifacts-Bucket sein, mit `HB_REID_MODEL_SHA256` bzw. `HB_ROLE_MODEL_SHA256`
  (`analysis.resolve_models`, gemeinsamer Cache).
  - Fehlt die Datei oder stimmt die SHA nicht, bleibt der Schritt aus, wie heute ohne Datei.
  - Status in `stats.reid_model_status` und `stats.role_model_status`.
- Wozu: ReID überträgt eine einmal gelesene Rückennummer auf andere Stücke derselben Person
  (ADR 027) und gleicht so einen Teil des Nummernverlusts durch das Gate aus. Auf dem
  NLB-Clip 2017 stieg die Spielzeit mit Nummer von 1 716 s auf 2 375 s
  (`ml/models/reid-fastreid.md`).
- `reid.onnx` aus FastReID BoT-R50 (`ml/scripts/export_reid.py`, jetzt mit `dynamo=False` für
  neuere torch-Versionen): 94 MB, SHA-256
  `6f3e1b1d05347d36adcf09ecb0d759bd36b73748248800ede5f46849679e16f0`.
  - 162 ms pro Crop auf 4 CPU-Kernen. Mit `HB_REID_EVERY=30` (einmal pro Sekunde, etwa 15
    Spieler im Bild) wären das etwa 2.5 CPU-Sekunden pro Videosekunde, also nur fürs
    CUDA-Image.
  - Testphase: Die Gewichte sind auf MSMT17 trainiert (nur nichtkommerzielle Forschung,
    Q-ML-5); nicht für einen Livegang.
- Rollen-Klassifikator (`ml/roles`): nur der Ladeweg ist vorbereitet. Kein Modell, weil er auf
  unseren Clips Spieler in dunklen Trikots oft für Schiedsrichter hält (`ml/roles/README.md`);
  vor einem Einsatz braucht er die Abstimmung über die ganze Spur.
- Hochladen in den Staging-Bucket (mit den Ballnetzen) erst nach Lukas' Freigabe.

### Schritt 5, Wurf-Ereignisse: erster Befund (2026-11-17)

Frage: Ist der Wurf der schnellste Ball seines Clips?
- Daten: die 41 Entwicklungs-Würfe aus `ml/gold/shot_clips.json`. Die Test-Würfe werden vor allem
  anderen verworfen und nie gelesen.
- Ballpfad: der Produkt-Tracker (`balltrack2`, ohne OWLv2) auf den Kandidaten von hr1 und hrp1
  aus Modal-Auftrag 12.
- Prüfung: Liegt der schnellste anhaltende Ball im Fenster von 3 s vor bis 1 s nach der
  Protokollzeit? Das Fenster deckt 4 der 9 bis 10 s ab, Zufall ergibt also etwa 0.4.
- Skript: `ml/integration/shot_speed_check.py`.

| Raum | Sicherheit | anhaltend über | schnellster Ball nahe der Protokollzeit |
|---|---|---|---|
| Bild | alle | 1 Schritt | 18 / 41 |
| Bild | ab 0.3 | 4 Schritte | 5 / 41 |
| Leinwand (Kamera herausgerechnet) | alle | 4 Schritte | 19 / 41 |
| Leinwand | ab 0.3 | 8 Schritte | 14 / 41 |

Lesart:
- **Ergebnis:** Die Geschwindigkeit allein erkennt den Wurf nicht, nicht besser als Zufall.
- **Mögliche Gründe:**
  - Pässe, Gegenstösse und Kameraschwenks sind ebenso schnell.
  - Der Tracker ist auf den 50/60-fps-Würfen schwächer.
  - Die Protokollzeit ist nur auf Sekunden genau und sagt nicht, wo der Abwurf liegt.
- **Nächster Schritt mit Lukas' Ja/Nein-Antworten:** Abwurfbild und Zielpunkt als Wahrheit nehmen
  und eine Wurfform prüfen: Flug in Richtung Tor, endet am Tor oder beim Torhüter, dazu die
  Wurf-Kandidaten aus `goalcandidates` (Kamera und Spieler).
- **Bis dahin:** keine Produktänderung, weil Raten ohne Wahrheit nichts bringt.

### Freigaben vom 2026-11-17: Modelle im Staging-Bucket, Schutz ohne GPU

- Hochgeladen in den R2-Bucket `handball-testdata` (Staging), per Rückdownload mit SHA geprüft:
  - `models/ball/ball_hr1_fp16-a99d126f7fc6.onnx`;
  - `models/ball/ball_hrp1_fp16-37153d8dfc83.onnx`;
  - `models/reid/reid-6f3e1b1d0534.onnx`.

  Testphase: Die Ballnetze enthalten DeepSport, ReID ist auf MSMT17 trainiert.
- Die Staging-Einstellungen (`HB_BALL_MODEL`, `HB_BALL_MODEL_SHA256`, `HB_REID_MODEL`,
  `HB_REID_MODEL_SHA256`) setzt die UX-Sitzung in Terraform. Eine Änderung gibt eine neue
  Revision, darum erst nach Lukas' laufendem Spiel.
- **Schutz:** Ballnetz und ReID laufen nur, wenn ONNX Runtime CUDA nutzen kann.
  - Ohne GPU bleiben sie aus, Status `no_gpu`. Ohne GPU bräuchte ein ganzes Spiel mit Ballnetz
    Tage.
  - Auf der CPU nur mit `HB_BALL_ALLOW_CPU=1`, und dann nur für Videos bis `HB_BALL_MAX_MINUTES`
    (Standard 3). Längere Videos bekommen den Status `too_long_for_cpu`.
  - Probelauf auf Staging (ohne GPU, kurzer Clip): `HB_BALL_ALLOW_CPU=1` dazusetzen.
- Das Log `analysis_done` meldet jetzt `ball_model_status`, `reid_model_status` und die Zähler der
  Beobachtung (`number_crops`, `number_frames_skipped`, angebotene und gelesene Boxen). Die
  UX-Sitzung liest nur Logs.

### CPU-Testeinstellung für den Ball auf Staging (2026-11-17)

Linie von Lukas: Bis das Produkt fertig ist, wird auf Staging nur mit Ausschnitten von 5 bis 10 min
ohne GPU getestet. Die Einstellung unten ist eine **Test-Einstellung** und trifft 63.5 % statt
80 %. Der Produktwert gilt erst mit GPU: Ensemble hr1 + hrp1 auf jedem Bild.

- **Gold v1 pro Einstellung** (Zeile «Product port and cost variants» in `ml/ball/LINEAGE.md`):
  - hrp1 bei 960 px auf jedem 3. Bild: 63.5 % [57.3, 69.4], schnelle 64.8 %.
  - Ensemble auf jedem Bild: 80.0 %.
  - hrp1 bei 1280 px auf jedem 3. Bild: 65.3 %.
  - hr1 bei 960 px auf jedem 3. Bild: 53.9 %.
- **Kosten pro Netzlauf auf 2 Kernen:** hrp1 1.0 s (1280) bzw. 0.53 s (960), hr1 0.81 bzw.
  0.47 s. fp16 ist auf der CPU nicht schneller.
- **Neu im Code:**
  - `HB_BALL_WIDTH`: Eingabebreite des Netzes.
  - `HB_BALL_EVERY > 1`: Der Tracker läuft auf der ausgedünnten Folge mit fps / k und füllt
    dazwischen auf. Vorher hätte er leere Bilder gesehen.
  - `HB_BALL_MAX_MINUTES` Standard 12, weil die Testclips 10:02 und 10:09 lang sind.
  - Spielphasen, die weniger als 20 % des Videos abdecken, sperren den Ball nicht mehr
    (`clock_too_sparse`).
  - Der Zeitbudget-Test der Hallentafel läuft mit einer Fake-Uhr.

**Ganze Kette auf den Testclips** (`testclips/sghorgen-h1-30m00-10min.mp4` und
`-h2-65m00-10min.mp4`). Lokal je auf 2 Kernen gerechnet, zwei Läufe gleichzeitig auf einer
4-Kern-Maschine:

| Lauf | x Videolänge | Beobachtung s | Ballnetz s | YOLOX s | Rückennummern s | Spuren |
|---|---|---|---|---|---|---|
| H1 ohne Ballnetz | 2.38 | 1 403 | | 625 | 457 | 310 |
| H2 ohne Ballnetz | 2.37 | 1 374 | | 617 | 452 | 283 |
| H1 mit Ballnetz (hrp1, 960, jedes 3.) | **7.97** | 4 791 | 3 307 | 679 | 457 | 308 |
| H2 mit Ballnetz | **8.01** | 4 761 | 3 298 | 677 | 452 | 287 |

Lesart:
- **Laufzeit:** Mit Ballnetz braucht ein 10-min-Clip etwa 80 min, nicht 66. Das Netz kostete hier
  0.65 s pro Lauf statt 0.53 s, vermutlich weil zwei Läufe sich den Speicher teilten. Für
  Ball-Tests auf Staging sind 5-min-Ausschnitte (etwa 40 min) die bessere Wahl.
- **Ballnetz-Status:** ok, `versions.ball: ball_hrp1_fp16`.
- **Ballpfad mit der Uhr-Sperre** (vor der neuen Regel):
  - H1: Punkte auf 53 % der Bilder (31 % mit Sicherheit ab 0.3).
  - H2: nur 1 %, weil die Hallentafel in H2 nur 39-mal gelesen wurde (6 s «Spiel»).
- **Ballpfad ohne Sperre:** 98 % der Bilder in beiden Clips (59 % bzw. 49 % mit Sicherheit ab
  0.3). Mit der neuen 20-%-Regel gilt das für H2. H1 bleibt gesperrt (54 % Abdeckung), obwohl der
  ganze Clip im Spiel liegt: Die Pausenerkennung aus der Hallentafel ist lückenhaft, das ist offen.
- **Ballbesitz H1** (mit Sperre): 176 Besitzphasen, 57 bzw. 32 Pässe. Ungeprüft.
- **Rückennummern:** Das Budget liess etwa die Hälfte der Nummernbilder aus. Spuren über 10 s
  mit Nummer: 3 bis 6 %.
- **Kalibrierung:** Auf beiden Clips greift die Auto-Kalibrierung, auf dem ganzen 99-min-Video
  nicht (`camera_motion`). Ob das Feld stimmt, prüft die Kalibrierungs-Sitzung.

**Werte für Terraform (gpu-worker, nur für Ball-Tests auf Staging):**
- `HB_BALL_MODEL=models/ball/ball_hrp1_fp16-37153d8dfc83.onnx`
- `HB_BALL_MODEL_SHA256=37153d8dfc832e683283b43229d35ea5fd1a257757c689d1b05ffb81fd9779f5`
- `HB_BALL_ALLOW_CPU=1`, `HB_BALL_WIDTH=960`, `HB_BALL_EVERY=3` (`HB_BALL_MAX_MINUTES` bleibt
  beim Standard 12).
- `HB_REID_MODEL` auf Staging nicht setzen: `HB_BALL_ALLOW_CPU=1` gilt auch für ReID und kostet
  auf der CPU etwa 2.5 CPU-Sekunden pro Videosekunde.

### Lukas' erster ganzer Lauf auf Staging (Asset c498a0c4, 99 min, 2026-11-17)

- **Laufzeit:** Start 05:00:37 durch den Watchdog, Dateien um 08:33. Etwa 3 h 33 min für 99 min
  Video, also 2.2 x Videolänge auf 2 vCPU, mit #50.
- **Kalibrierung:** gescheitert mit `camera_motion` (Zoom bis 6.5 x, 165 Schnitte). Darum keine
  Spuren und keine Tore aus dem Tracking.
- **Rückennummern:** 7 500 Lesungen, davon 3 504 sicher; 34 Nummern mit mindestens 3 sicheren
  Lesungen. Mangels Spuren keiner Spur zugeordnet.
- **159 offene Fragen:** genau die Tor-Kandidaten mit Rate 1 oder 2 (81 + 78, also 16 pro
  10 min). Dazu 165 mit Rate 4 und 466 Wurf-Kandidaten.
- **Uhr und Spielstand:** 924 Uhr-Lesungen, aber Spielphasen nur von 12:50 bis 40:50 und von
  87:30 bis 92:10. Ohne Spielstand-Verlauf gibt es auch keine Tore aus der Tafel.

### GPU-Profil auf einer T4 (Modal-Auftrag 13, Dataset `handball-gpu-profile-game1-gpu`, 2026-11-17)

5 min von AT_Cup_Feldkirch_Bregenz_2021, `run_analysis` wie im Produkt. ONNX Runtime lief für alle
Netze auf CUDA (geprüft). Das erste Dataset ohne `-gpu` sind CPU-Zahlen und gilt nicht.
Kosten pro 60-min-Spiel: Modal T4 0.66 USD/h, Azure T4 mit 4 vCPU und 16 GiB 0.90 USD/h.

| Einstellung | s für 5 min | Ballnetz | YOLOX | Rückennummern | Kamera | USD Modal / Azure |
|---|---|---|---|---|---|---|
| `cuda_image` (YOLOX jedes Bild, kein Ball) | 496 | | 126 | 216 | 84 | 1.09 / 1.49 |
| + hrp1 jedes Bild | 1 378 | 890 | 106 | 216 | 93 | 3.03 / 4.13 |
| + Ensemble jedes Bild | 1 873 | 1 369 | 109 | 216 | 103 | 4.12 / 5.62 |
| Ensemble, YOLOX jedes 3. Bild | 1 755 | 1 347 | 37 | 216 | 84 | 3.86 / 5.26 |

- Die Rückennummern liefen mit Gate und Budget 0.75. Das Modal-Image nimmt die ENV-Werte aus
  `Dockerfile.cuda` nicht; dort wären Gate und Budget aus, dann wäre es noch teurer.
  216 s für 300 s Video ist genau das Budget.
- **Ballnetz auf der T4:** hr1 80 ms und hrp1 99 ms pro Bild (fp16, Stapel 1). Grössere Stapel
  sind nicht schneller. Lokal kostet die Vorbereitung eines Bildes auf der CPU 21 ms (3
  Farbumwandlungen, 32 MB float32 pro Bild). Die GPU ist also kaum ausgelastet; für dieses Netz
  sind 10 bis 20 ms zu erwarten.
- **Ziel unter 1 Euro** (etwa 1.08 USD; auf Azure etwa 72 min Rechenzeit pro Spiel, also etwa
  360 s pro 5 min Video). Hebel, grob geschätzt:
  1. YOLOX nur jedes 3. Bild: 126 auf 37 s.
  2. Rückennummern-Budget auf der GPU 0.3 statt 0.75: 216 auf etwa 90 s. Der Nummernverlust
     ist zu messen; heute halbiert schon das Budget von 0.75 die Nummernbilder.
  3. Ballnetz schneller machen, Ziel unter 20 ms pro Bild für beide Netze:
     - Vorbereitung in den Graphen verlegen (uint8-Eingabe, Umordnen und Normieren auf der GPU);
     - IO-Binding;
     - TensorRT-Ausführung prüfen.
     Ohne das kostet das Ensemble auf jedem Bild allein etwa 3 USD pro Spiel.
  4. Kamerabewegung (84 s) läuft auf der CPU, bleibt fix.

  Ohne Ball liegt man mit 1 und 2 bei etwa 290 s pro 5 min, also 0.63 USD auf Modal und
  0.86 USD auf Azure. Mit Ball geht es nur mit 3.
- **Nächster GPU-Auftrag** (Vorschlag, braucht Freigabe): Kurzmessung des Ballnetzes auf der T4
  in den Varianten CUDA, CUDA mit IO-Binding, TensorRT fp16, uint8-Eingabe mit Vorbereitung im
  Graphen. Etwa 15 min, unter 0.20 USD.

### Offen: lückenhafte Pausenerkennung über die Hallentafel

- Die Spielphasen (`play.json`) kommen aus den Uhr-Lesungen der Hallentafel. Ist die Tafel lange
  nicht im Bild, fehlen Lesungen, und die Phasen haben Lücken:
  - Testclip H1: 54 % des Clips gelten als Spiel, obwohl der ganze Clip im Spiel liegt.
  - Testclip H2: 1 %.
  - Lukas' 99-min-Video: die zweite Halbzeit fast ganz ohne Spielphase.
- Folgen:
  - Ballpfad und Ballbesitz werden ausserhalb der Phasen verworfen; seit #61 nur, wenn die
    Phasen mindestens 20 % des Videos abdecken.
  - Die Tor-Kandidaten nutzen eigene Regeln ohne Ball (Kamera geparkt, Spieler zusammen).
- Einschätzung: Die Uhr nur als Beleg für Pausen verwenden, nicht als Bedingung für Spiel. Also
  als Spiel gilt alles ausser:
  - Zeiten, in denen die Uhr nachweislich steht (zwei Lesungen mit gleicher Zeit mehr als einige
    Sekunden auseinander);
  - der `no_play`-Regel der Tor-Kandidaten (Kamera geparkt, Spieler zusammengedrängt).

  Das ist ein eigener kleiner Schritt in `scoreboard.play_intervals`; dort arbeitet heute niemand
  sonst. Messbar auf den Testclips und auf den Dev-Segmenten mit Protokollzeiten (Pausen kennt das
  Protokoll als Timeouts und Halbzeit).

### Weniger Tor-Kandidaten (Punkt 8, 2026-11-17)

Zwei Regeln in `goalcandidates.from_observations` (Standardliste = Rate 1 und 2, die heute als
Fragen erscheinen):
- **Einspielen:** Liest die Analyse die Matchuhr (Hallentafel oder Einblendung), gilt die Zeit vor
  dem ersten Uhrlauf von mindestens 30 s als kein Spiel (20 s Spielraum davor; nur wenn dieser
  Lauf mindestens 2 min nach Videobeginn liegt). Das gilt auch für die Wurf-Kandidaten. Spätere
  Lücken der Uhr werden nicht genutzt, weil die Tafel oft minutenlang nicht im Bild ist
  (Abschnitt Pausenerkennung).
- **Mindestwert:** Ein Kandidat mit Wert unter 1.2 (robuster z-Wert) fällt aus der Standardliste und
  behält nur Rate 4. Er erscheint also weiter, wenn der Trainer mehr Kandidaten verlangt.

Gemessen mit `ml/goals`-Logik: Treffer, wenn ein Kandidat 3 s vor bis 8 s nach der Protokollzeit
liegt. Grundlage sind 25 Dev-Segmente mit Würfen, 75 min, 42 protokollierte Tore. Alle Segmente
liegen im Spiel und haben keine Uhr, darum greift dort nur der Mindestwert.

| | Kandidaten/min (Dev) | Tore gefunden, Rate ≤ 2 | Tore gefunden, Rate ≤ 4 | Lukas' 99 min, Rate ≤ 2 |
|---|---|---|---|---|
| vorher | 1.96 | 40/42 | 42/42 | 159 |
| Mindestwert | 1.88 | 40/42 | 42/42 | 142 |
| + Einspielen (mit `play.json` des Laufs) | 1.88 | 40/42 | 42/42 | 122 |

- In Lukas' Video beginnt der erste Uhrlauf bei 12:48. Davor lagen 20 Fragen; mit dem Mindestwert
  sind es insgesamt 37 Fragen weniger (−23 %).
- Nicht übernommen: Ohne Feld nur Rate 1. Das wären 81 statt 159 Fragen, aber auf den
  Dev-Segmenten nur noch 28 von 42 Toren. Ein höherer Mindestwert von 1.5 kostet schon ein Tor
  (39/42). Weniger Fragen ohne Torverlust gibt es nur über die Zeit ausserhalb des Spiels, also
  über Einspielen, Pausen und Nachspiel. Dafür braucht es eine bessere Pausenerkennung.

### Ballnetz billiger auf der T4 (Modal-Auftrag 14, Dataset `handball-gpu-bench-ballnet`, 2026-11-17)

3 min des Spiels aus Auftrag 13, T4, ONNX Runtime 1.22 mit CUDA und TensorRT 10.9. hrp1 fp16.

Ballnetz allein, 120 echte Dreiergruppen, ms pro Bild (Vorbereitung auf der CPU + Netz):

| | 1280 px | 960 px | stärkster Kandidat wie Produkt |
|---|---|---|---|
| Produkt heute (float-Eingabe) | 21 + 71 = 92 | 15 + 40 = 55 | |
| uint8 mit Vorbereitung im Graphen (`ml/ball/onnx_u8.py`) | 17 + 46 = 62 | 14 + 28 = 42 | 100 % |
| uint8 + IO-Binding | 17 + 46 = 62 | 16 + 29 = 45 | 100 % |
| TensorRT fp16, float-Eingabe | 40 + 62 = 101 | 25 + 31 = 55 | 99.2 % / 100 % |

- uint8 spart ein Drittel. IO-Binding bringt nichts dazu.
- TensorRT ist nicht schneller als CUDA fp16 und braucht einmalig 379 s für den Engine-Bau. Die
  uint8-Variante scheiterte an einem fehlenden Shape-Profil für den Teilgraphen, den ONNX Runtime
  an TensorRT gab. Die Korrektur (Cast zuerst, #65) ist nicht nachgemessen; ein Nachlauf lohnt
  nicht, weil auch die float-Variante keinen Gewinn zeigt. Die erwarteten 10 bis 20 ms waren zu
  optimistisch: 46 ms ist die Rechenzeit von hrp1 bei 1280 x 704 auf einer T4.

Ganzer Job, YOLOX jedes 3. Bild, Rückennummern-Budget 0.3 (Kosten pro 60-min-Spiel, Modal T4
0.66 USD/h, Azure T4 0.90 USD/h):

| Einstellung | s für 180 s | x Videolänge | USD Modal / Azure |
|---|---|---|---|
| `cuda_lean` ohne Ball | 182 | 1.01 | 0.67 / 0.91 |
| `cuda_lean_hrp1`, hrp1 jedes Bild, float-Eingabe | 727 | 4.0 | 2.66 / 3.63 |

- In `cuda_lean`: Kamerabewegung 54 s (CPU), Rückennummern 54 s (genau am Budget), YOLOX 32 s,
  Einblendung 13 s.
- Im Job kostet das Ballnetz 122 ms pro Bild statt 92 in der Kurzmessung (Puffer, Stapel,
  Spitzen, CPU geteilt mit den anderen Stufen): Faktor 1.33.

Schätzung mit uint8 im Produkt (Kurzmessung x 1.33, übrige Stufen 178 s pro 180 s wie oben),
Gold-Werte aus `ml/ball/LINEAGE.md`:

| Ballnetz | x Videolänge | USD Modal / Azure | Gold alle Bälle |
|---|---|---|---|
| 1280 px, jedes Bild | 3.1 | 2.02 / 2.76 | 76.1 % |
| 960 px, jedes Bild | 2.4 | 1.58 / 2.15 | nicht gemessen |
| 1280 px, jedes 3. Bild | 1.7 | 1.11 / 1.51 | 65.3 % |
| 960 px, jedes 2. Bild | 1.7 | 1.11 / 1.52 | nicht gemessen |
| 960 px, jedes 3. Bild (CPU-Testeinstellung) | 1.5 | 0.96 / 1.31 | 63.5 % |

- Unter 1 Euro (etwa 1.08 USD) mit Ball liegt nur 960 px jedes 3. Bild, und nur auf Modal.
- Umgesetzt (PR nach #65), ohne neue GPU-Ausgaben:
  1. Das Produkt nimmt uint8-Netze an: `BallNet` erkennt den Eingangstyp, auch gemischt im
     Ensemble. Die Kandidaten sind gleich (Test). Für Staging braucht es eine uint8-Datei im Bucket
     (`ml/ball/onnx_u8.py` auf die heutige Datei).
  2. Das Ballnetz läuft in einem eigenen Thread (`BallCandidates`, höchstens 2 wartende Stapel).
     ONNX Runtime gibt den GIL frei, also rechnet die GPU, während der Hauptfaden Kamerabewegung,
     YOLOX und Rückennummern macht. `timings_s["ball_net"]` ist jetzt nur noch die Wartezeit des
     Hauptfadens, die reine Netzzeit steht in `observe_counters["ball_net_busy_ms"]`.
     Im besten Fall wird die Laufzeit max(Netz, übrige Stufen) statt der Summe: für 1280 px auf
     jedem Bild mit uint8 etwa 279 s Netz gegen 178 s, also 1.55 x und 1.02 USD pro Spiel auf
     Modal. Gemessen ist das noch nicht; es braucht einen kurzen GPU-Lauf (Freigabe Lukas).

### Adaptives Ballnetz bewertet (CPU-Simulation, 2026-11-17)

Idee: Ein dünner Grundtakt läuft überall (hrp1, 960 px, jedes 3. oder 4. Bild). Dicht, also jedes
Bild, nur dort, wo es zählt: um Wurf-Kandidaten (#65) oder wo der dünne Pfad einen schnellen Ball,
einen unsicheren Tracker oder keinen Punkt zeigt. Simuliert mit `ml/integration/adaptive_ball.py`
aus gespeicherten Netz-Kandidaten, ohne GPU. Der dünne Pfad wird in jedem dichten Fenster durch
`balltrack2.track` auf den dichten Kandidaten ersetzt, mit 0.5 s Rand.

**Gold v1** (alle Bälle; Grundtakt 960 px jedes 3. Bild, dicht 1280 px jedes Bild; die Gold-Clips
haben keine Wurf-Kandidaten):

| Regel | dichte Bilder | alle | schnell |
|---|---|---|---|
| nur Grundtakt | 0 % | 63.5 % | 64.8 % |
| Ball schneller als 900 px/s | 49 % | 70.1 % | 72.8 % |
| kein Punkt | 35 % | 68.5 % | 67.5 % |
| unsicher (unter 0.3) oder kein Punkt | 93 % | 75.9 % | 77.4 % |
| alles dicht | 100 % | 76.1 % | 78.3 % |
| Vergleich: gleichmässig 1280 jedes 2. Bild | 50 % | 69.2 % | |

Die Auslöser konzentrieren den Gewinn nicht: Er wächst etwa wie der dichte Anteil. Im dünnen Takt
springt der Tracker oft, darum löst auch eine Schwelle von 3 000 px/s noch auf 19 % der Bilder aus.

**41 Wurf-Dev-Clips** (nur `split: dev`): Ball-Gold gibt es dort nicht. Gemessen wird der Anteil
der Bilder von 3 s vor bis 1 s nach der Protokollzeit, in denen der Pfad höchstens 12 px vom dichten
Pfad entfernt liegt (1280 px, jedes Proxy-Bild, also jedes 2. Bild dieser 50/60-fps-Clips). Die
Clips liegen um Würfe herum, darum sind die dichten Anteile dort höher als im ganzen Spiel. Die
Spalte "Spiel" rechnet mit der Fensterabdeckung pro Spielminute aus den 25 Dev-Segmenten.

| Regel (Grundtakt jedes 3. Bild) | gleich wie dicht, Wurf-Fenster | dichte Bilder: Clips / Spiel |
|---|---|---|
| nur Grundtakt | 35 % | 0 / 0 % |
| Wurf-Kandidaten Rate 2, Fenster −3/+1 s | 62 % | 34 / 13 % |
| Wurf-Kandidaten Rate 4, −3/+1 s | 64 % | 40 / 26 % |
| Wurf-Kandidaten Rate 2, Fenster −5/+3 s | 77 % | 66 / 26 % |
| Wurf-Kandidaten Rate 4, −5/+3 s | 82 % | 77 / 52 % |
| Ball schneller als 600 px/s | 85 % | 67 % / nicht gemessen |
| Rate 2 −3/+1 s, dazu schnell (900) oder kein Punkt | 90 % | 76 % / nicht gemessen |

Grundtakt jedes 4. Bild: 1 bis 2 Punkte weniger bei den Wurf-Fenstern, bei den anderen Regeln
mehr.

**Kosten pro 60-min-Spiel** (Modal; Formel wie oben: Kurzmessung uint8 x 1.33, übrige Stufen
0.99 x; Spielanteil 80 %; die dichten Fenster brauchen einen zweiten Decode-Durchgang, weil die
Wurf-Kandidaten erst nach dem ganzen Video feststehen; der ist hier nicht mitgerechnet):

| Variante | USD | gleich wie dicht, Wurf-Fenster |
|---|---|---|
| 960 jedes 3., dicht 960 um Rate 2 (−3/+1 s) | 1.03 | etwa 62 % |
| 960 jedes 3., dicht 960 um Rate 2 (−5/+3 s) | 1.09 | etwa 77 % |
| 960 jedes 4., dicht 960 um Rate 2 (−5/+3 s) | 1.03 | etwa 76 % |
| 960 jedes 3. ohne Fenster | 0.96 | 35 % |
| 960 jedes Bild, nacheinander (heute) | 1.58 | 100 % (bei 960) |
| 960 jedes Bild mit Thread, bester Fall max(Netz, Rest) | 0.69 | 100 % (bei 960) |
| 1280 jedes Bild mit Thread, bester Fall | 1.02 | 100 % |

Einschätzung:
- Adaptiv nach Geschwindigkeit oder Unsicherheit lohnt nicht.
- Wurf-Fenster kommen unter 1.08 USD, erhalten in den Wurf-Fenstern aber nur 62 bis 77 % des
  dichten Pfads. Dazu kämen ein zweiter Durchgang und mehr Code.
- Hält der Thread, was er im besten Fall verspricht (Auftrag 15), ist gleichmässig dicht bei 960 px
  billiger und besser als jede adaptive Variante. Darum zuerst Auftrag 15 messen. Adaptiv mit
  Wurf-Fenstern (−5/+3 s) bleibt die Rückfalloption, falls der Thread wenig bringt.

### Ballnetz im Thread im ganzen Job (Modal-Auftrag 15, Dataset `handball-gpu-lean-u8`, 2026-11-17)

2 min des Spiels aus den Aufträgen 13 und 14, T4, `run_analysis` wie im Produkt. YOLOX jedes 3.
Bild, Nummern-Budget 0.3, hrp1 fp16 mit uint8-Eingabe, das Netz im eigenen Thread (#67). Kosten
pro 60-min-Spiel: Modal T4 0.66 USD/h, Azure T4 mit 4 vCPU und 16 GiB 0.90 USD/h. "Netz" ist
`ball_net_busy_ms`, "Warten" die Zeit, die der Hauptfaden auf das Netz wartete.

| Variante | s für 120 s | USD Modal / Azure | Netz | Warten | verdeckt | Gold alle / schnell |
|---|---|---|---|---|---|---|
| ohne Ballnetz (`cuda_lean`) | 127 | 0.70 / 0.95 | | | | |
| hrp1 1280 jedes Bild | 225 | 1.24 / 1.69 | 197 s (66 ms/Bild) | 83 s | 58 % | 76.1 / 78.3 % |
| hrp1 1280 jedes 2. Bild | 153 | 0.84 / 1.14 | 102 s | 2.5 s | 98 % | 69.2 % / etwa 67 % |
| **hrp1 960 jedes Bild** | **158** | **0.87 / 1.18** | 127 s (42 ms/Bild) | 14 s | 89 % | **73.0 / 81.3 %** |
| hrp1 960 jedes 2. Bild | 137 | 0.75 / 1.02 | 66 s | 2.8 s | 96 % | 65.6 / 69.2 % |
| hr1 + hrp1 1280 jedes Bild | 315 | 1.73 / 2.36 | 287 s | 170 s | 41 % | 80.0 % (Ensemble) |

- Zum Vergleich hrp1 mit float-Eingabe ohne Thread (Auftrag 14): 4.0 x Videolänge, 2.66 USD.
- Gold bei 960 px neu gemessen: hrp1 ONNX auf den Gold-Clips, jedes Bild, 73.0 % [66.5, 79.0],
  schnelle Bälle 81.3 % [71.7, 88.8], 50/60 fps 64.3 %. Jedes 2. Bild: 65.6 %, schnell 69.2 %.
  Gemessen auf der CPU mit der fp32-Datei; uint8 und fp16 geben auf der T4 denselben stärksten
  Kandidaten (Auftrag 14).
- Der Thread verdeckt das Netz fast ganz, solange es nicht länger braucht als der Rest (127 s für
  120 s Video). Bei 1280 px auf jedem Bild ist es länger, darum wartet der Hauptfaden 83 s.
- Der Rest ist mit dem Netz im Thread etwas langsamer (YOLOX 30 statt 21 s, die GPU wird geteilt).

**Empfehlung für das Produkt (GPU):** hrp1 mit uint8-Eingabe, 960 px, jedes Bild, Netz im Thread.
- 0.87 USD pro Spiel auf Modal, also unter 1 Euro; auf Azure 1.18 USD.
- Gold 73.0 %, schnelle Bälle 81.3 %: bei den schnellen Bällen besser als 1280 px auf jedem Bild,
  weil das Netz bei 960 px die Bewegungsunschärfe offenbar besser verträgt. Würfe und harte Pässe
  bekommen so jedes Bild.
- Für Azure unter 1.08 USD bliebe nur 960 px jedes 2. Bild (1.02 USD, Gold 65.6 %).
- Umsetzung:
  - Die uint8-Datei liegt im Staging-Bucket `handball-testdata` (Freigabe b), per Rückdownload mit
    SHA geprüft: `models/ball/ball_hrp1_fp16_u8-8efd55d05333.onnx`, SHA-256
    `8efd55d0533301889c0b3715bff3fa708a9e4f9be3b2d8162a4c56377a70253f`. Erzeugt mit
    `ml/ball/onnx_u8.py` aus `ball_hrp1_fp16-37153d8dfc83.onnx`; im Produkt (`BallNet`, 960 px)
    gibt sie auf echten Bildern dieselben Kandidaten wie die float-Datei.
  - `Dockerfile.cuda`: `HB_BALL_WIDTH=960`, `HB_BALL_EVERY=1` als Standard. `HB_BALL_MODEL` und
    `HB_BALL_MODEL_SHA256` setzt die UX-Sitzung über Terraform.
  - Offen: Der Preis von 0.87 USD gilt mit YOLOX jedes 3. Bild und Nummern-Budget 0.3. Das
    GPU-Image hat noch YOLOX auf jedem Bild und Nummern ohne Gate und Budget (Entscheid vom
    2026-11-17). Damit wird es teurer: Auftrag 13 kostete schon ohne Ball 1.09 USD.
  - Staging ohne GPU behält die CPU-Testeinstellung (jedes 3. Bild).
  - Testphase: hrp1 enthält DeepSport und ist vor Go-live zu ersetzen.
- Damit ist das adaptive Rechnen mit Wurf-Fenstern (Abschnitt oben) nicht mehr nötig: Es wäre
  teurer (1.03 bis 1.09 USD) und schlechter.

### Rückennummern und Spuren: GPU-Einstellung (Entscheid Lukas 2026-11-17)

Frage: Was kostet das volle Nummern-Lesen auf der GPU, und was bringt es? Gemessen auf der CPU mit
`ml/integration/profile_analysis.py` auf Lukas' 10-min-Clip A (kalibriert). Das Budget der T4 ist
auf der CPU nachgebildet: Ein Torso kostet auf 2 Kernen 35.5 ms, auf der T4 21.4 ms (Auftrag 15).
Budget 0.3 auf der T4 entspricht also 0.5 auf der CPU, 1.0 entspricht 1.7.

| | GPU-Image bisher | schlank | Mittelweg (Entscheid) |
|---|---|---|---|
| YOLOX | jedes Bild | jedes 3. Bild | jedes 3. Bild |
| Rückennummern | jedes 3. Bild, ohne Gate und Budget | Gate, Budget 0.3 (T4) | Gate, Budget 1.0 (T4) |
| gelesene Torsos pro Videosekunde A / B | 159 / 191 | 14 / 16 | 51 / 52 |
| Spuren ab 10 s A / B | 242 / 224 | 209 / 193 | 206 / 202 |
| davon mit Nummer, Clip A | 19 (7.9 %) | 7 (3.3 %) | 12 (5.8 %) |
| davon mit Nummer, Clip B | 24 (10.7 %) | 9 (4.7 %) | 18 (8.9 %) |
| verschiedene Nummern ab 10 s A / B | 16 / 19 | 7 / 8 | 11 / 15 |
| USD pro Spiel Modal / Azure, mit Ballnetz 960 | etwa 2.9–3.3 / 3.9–4.5 | 0.87 / 1.18 | etwa 1.22 / 1.67 |

- Kosten:
  - GPU-Image bisher: Auftrag 13 ohne Nummern ergibt 0.93 x Videolänge. Dazu kommen die Nummern
    mit 161 Torsos/s x 21.4 ms = 3.45 x. Zusammen etwa 4.4 x. Das Ballnetz ist im Thread ganz
    verdeckt.
  - schlank: gemessen in Auftrag 15.
  - Mittelweg: `cuda_lean` (1.06 x) ohne dessen Nummern (0.30 x) plus die gemessenen 51
    Torsos/s x 21.4 ms = 1.09 x, zusammen etwa 1.85 x. Das Ballnetz (1.06 x) bleibt verdeckt.
- Auf diesem Video lesen beide Varianten wenige Nummern (Halle, Abstand). Das volle Lesen findet
  aber mehr als doppelt so viele. Fast alle Mehrkosten gehen ins Nummern-Lesen, nicht in YOLOX.
- **Entscheid Lukas (2026-11-17), GPU-Standard für die Testphase:**
  - YOLOX jedes 3. Bild;
  - Nummern-Gate an, Nummern-Budget 1.0;
  - Ballnetz hrp1 uint8, 960 px, jedes Bild;
  - geschätzt 1.27 USD pro Spiel auf Modal.

  Umgesetzt in `apps/gpu-worker/Dockerfile.cuda`. Staging (CPU) bleibt unverändert.
- Der Mittelweg holt 60 % (A) bzw. 75 % (B) der Spuren mit Nummer des vollen Lesens und gut
  70 % der verschiedenen Nummern, für rund 40 % der Kosten. Die Erkennung auf jedem Bild gibt etwa
  10 % mehr lange Spuren.

### Pausenerkennung über die Hallentafel verbessert (2026-11-18)

Befund: Auf Lukas' Clips H1 und H2 (je 10 min) habe ich die Uhr-Lesungen ausgewertet, so wie das
Produkt sie liest (`HallBoardReader` auf jedem Bild). Die Tafel war oft genug lesbar (H1: 118
Lesungen, H2: 39), aber `scoreboard.play_intervals` verlor die Läufe aus drei Gründen:
1. **Fehllesungen in Folge:** Die Sekundenziffer wird oft mehrmals hintereinander falsch gelesen
   (z. B. 5 als 9, 15:59 statt 15:55). Bisher wurde nur eine einzelne Fehllesung übersprungen.
2. **Andere Anzeigen dazwischen:** Strafzeit-Uhren zählen herunter (1:59, 1:58; 0:14 bis 0:09),
   eine zweite Anzeige läuft etwa sechs Minuten hinter der Matchuhr her (H1, Minute 8). Sie
   brachen die Läufe der Matchuhr und standen an deren Rändern im Weg.
3. **Neustart nach stehender Uhr:** Eine Uhr, die lange stand und dann weiterlief, passte nicht
   mehr zum ersten Wert des Laufs (H2: 8:56 steht, läuft ab 40 s weiter).

Änderungen in `scoreboard.play_intervals` / `_clock_runs`:
- bis zu 4 Fehllesungen in Folge zwischen zwei passenden Lesungen werden übersprungen;
- zählt eine Richtung klar mehr (mindestens 3 x so viel Uhrzeit), werden die Läufe der anderen
  Richtung (Strafzeiten) weggelassen und die Läufe neu gesucht;
- ein Lauf darf mit stehender Uhr beginnen; verglichen wird mit dem letzten Wert, bevor die Uhr
  wieder lief;
- eine Lücke von mindestens 30 s, in der die Uhr mindestens die Hälfte der Zeit lief, gilt ganz
  als Spiel (Tafel aus dem Bild, Spiel lief weiter). Wo die kurzen Halte in der Lücke lagen, weiss
  man nicht. Für die Ball-Sperre ist es besser, einen losen Ball zu behalten, als echtes Spiel zu
  verwerfen.

Messung: Die Matchuhr selbst ist die Wahrheit. Zwischen ihrer ersten und letzten Lesung lief sie
auf H1 480 s (20:51 bis 28:51), auf H2 312 s (8:56 bis 14:08). Verglichen wird, wie viel Video in
dieser Spanne als Spiel gilt:

| | H1: Spiel in der Spanne (Uhr lief 480 s) | H2 (Uhr lief 312 s) |
|---|---|---|
| vorher | 322 s (67 %) | 5 s (2 %) |
| nachher, ohne Füllen der Lücken | 481 s (100 %) | 315 s (101 %) |
| nachher, mit Füllen (Standard) | 538 s (112 %) | 442 s (142 %) |

- Ohne Füllen stimmt die Summe genau. Die Spielzeit einer Lücke wird dann aber an deren Rändern
  angesetzt, also teils an der falschen Stelle.
- Mit Füllen zählen auch die kurzen Halte in solchen Lücken als Spiel: H2 hat 7 min ohne Tafel,
  darin lief die Uhr 289 von 416 s.
- Die Regel `clock_too_sparse` (Spiel unter 20 % des Videos: keine Sperre) greift auf H1 und H2
  nicht mehr. Die Ball-Sperre wirkt damit jetzt auch auf H2.
- Nicht gemessen: die Wirkung auf Ballpfad und Ballbesitz (braucht einen neuen Lauf), und Lukas'
  99-min-Video (dessen Lesungen sind nicht gespeichert).
- Rückfall, falls die Tafel ganz fehlt: Er ist schon da (`clock_too_sparse` sperrt dann nicht).
  Für eine eigene Pausenerkennung ohne Tafel bietet sich die `no_play`-Regel der Tor-Kandidaten
  an (Kamera geparkt, Spieler zusammengedrängt). Das ist ein eigener Schritt.

**Nachtrag: Lukas' ganzes 99-min-Video.** Die Tafel ohne Zeitbudget gelesen, 906 Lesungen. Ein
erster Lauf mit dem Budget von 10 % übersprang auf der ausgelasteten Maschine 678 Lesungen und fand
nach Minute 60 nichts mehr; das Budget hängt von der echten Uhr ab.
- Lesungen pro 10 min: keine bis Minute 10, dann 30 / 3 / 97 / 568 / 73 (Pause, Uhr bei 0:00) /
  25 / keine (Minute 70 bis 80) / 61 / 49.
- Erste Halbzeit läuft ab 12:48 Video, zweite ab etwa 64 min; nach 92.3 min keine Lesung mehr.
- Spiel laut `play_intervals`: vorher 21.1 min, nachher 48.2 min (ohne Füllen 44.0). In den
  gelesenen Spannen lief die Uhr etwa 54 min (erste Halbzeit 0:39 bis 30:00, zweite 1:55 bis
  26:29).
- Spielende (2026-11-19): Lief die Uhr bei der letzten Lesung und wurde danach keine stehende Uhr
  gelesen, gilt das Video bis zum Ende als Spiel, höchstens aber bis die Uhr das Ende der Halbzeit
  erreicht (`half_s`, Standard 30:00; rückwärts 0:00). Die Halbzeitlänge kennt das Produkt nicht,
  darum der Standard der Erwachsenen; bei kürzeren Halbzeiten ist die Grenze nur lockerer.
  Lesungen danach, die nicht diese Uhr sein können (zählt zurück oder schneller als das Video,
  z. B. eine Strafzeit), halten das Spiel nicht an. Zeigt die letzte Lesung eine stehende Uhr oder
  das Ende der Halbzeit (30:00 bzw. 0:00), bleibt es bei 7.5 s.

### Teamzuordnung: Torhüterfarbe als Feldfarbe (Staging 2026-11-17, #82, #83)

- Befund: In `stats.ball.possessions` war das Team fast immer `home_gk`. Gesendet wurden `home`
  #1f4fd6 (die alte, nicht gewählte Vereinsfarbe) und `home_gk` #f59e0b, kein Away-Kit. Die Teams
  spielten in Gelb/Schwarz und Rot/Weiss; das Torhüter-Gelb passte auf alle gelben Feldspieler.
- #82: Ein `_gk`-Label, das meist mehr als zwei Spuren gleichzeitig tragen, ist eine Feldfarbe.
- #83: Eine nicht gewählte eigene Farbe wird nicht gesendet, und die Farbgruppen trennen die
  Teams auch mit einem oder ohne Team-Kit.
- Clip A mit den Staging-Kits, Besitzphasen: vorher home_gk 177 / home 10; mit #82 home 187; mit
  #82 und #83 home 86 / away 79, dazu Torhüter 19 und Schiri 3. Referenz mit passenden Kits:
  home 61 / away 92, dazu Torhüter 15 und Schiri 6.

### Staging-Befunde aus den Logs (UX-Diagnose 2026-11-18)

- DB-Spitze am 17.11. 08:53 bis 08:58: Die API wurde vom HTTP-Scaler auf 2 Replikas gehoben, alle
  11 TooManyConnections fallen in dieses Fenster. Kein Deploy, kein Job. Rechnerisch sind das nur
  2 x 2 x (4+1) = 20 Verbindungen. Ob das Limit des B1ms-Servers tiefer liegt oder andere
  Verbindungen mitzählen, ist offen, weil die Postgres-Logs nicht in Log Analytics landen.
  Nächste Schritte: application_name pro API-Prozess (Produkt); Postgres-Diagnose nach Log
  Analytics, Pool bzw. Replikas an die Slots koppeln (Terraform, UX).
- Die "stündlichen Neustarts" der Worker sind Deploys (7 Revisionen am Nachmittag und Abend). Redis
  wird dabei ersetzt und hat keine Persistenz; ein Job, der nur in der Warteschlange stand, geht
  verloren, und der Watchdog nimmt nur laufende Jobs wieder auf. Nächste Schritte: Watchdog auch
  für wartende Jobs ohne RQ-Job (Produkt); Redis nicht bei jedem Deploy ersetzen oder AOF
  (Terraform, UX).

### Wurf-Endtest mit der Produktkette (2026-11-19, einmalige Freigabe von Lukas)

42 Endtest-Segmente (`ml/gold/shot_endtest_segments.json`, 42 Spiele in 42 nie trainierten Hallen,
je 3 min), Lukas' Markierungen eingefroren (`ml/gold/data/shot_endtest_marks.json`: 130 Würfe, 76
Tore, 41 gehalten, 13 daneben; Runde 1 nicht verwendet). Produktkette im CPU-Testsetting (hrp1 960
px auf jedem 3. Bild, YOLOX jedes 3. Bild, `ml/integration/shot_segments_eval.py`), der Observe-Schritt
als 4 Kaggle-CPU-Kernels (`ml/integration/kaggle/shot_endtest_push.py`; der Container der Sitzung wird im
Leerlauf freigegeben, der erste 18-h-Lauf brach ab). Nur gemessen, nichts darauf eingestellt.
95 %-Intervalle: Bootstrap über die 42 Spiele. Ergebnis: `ml/gold/data/shot_endtest_result.json`.

| Mass | Wert | 95 % |
|---|---|---|
| Wurf-Kandidaten (Rate <= 4), Wurf gefunden, ±2 s um die geschätzte Zeit | 20.8 % | 12.5 bis 29.9 % |
| dasselbe, Fenster der Kandidaten (Peak 3 s vor bis 8 s nach der Markierung) | **84.6 %** | 74.5 bis 92.4 % |
| davon Tore / gehalten / daneben (−3/+8 s) | 88.2 / 78.0 / 84.6 % | 78 bis 96 / 61 bis 92 / 62 bis 100 % |
| Präzision der Wurf-Kandidaten (−3/+8 s; ±2 s) | 25.8 % (6.3 %) | 21.7 bis 29.8 % |
| Wurf-Kandidaten pro Minute | 3.39 | 3.00 bis 3.75 |
| Tor-Kandidaten (Rate <= 2), Tore gefunden (−3/+8 s; ±2 s) | 75.0 % (6.6 %) | 63.4 bis 85.1 % |
| Präzision der Tor-Kandidaten (−3/+8 s) | 29.1 % | 22.7 bis 35.7 % |
| Tor-Kandidaten pro Minute | 1.56 | 1.36 bis 1.75 |
| Ballpfad-Abdeckung ±1.5 s um jeden Wurf | **97.8 %** | 96.8 bis 98.5 % |
| Würfe mit Ballpunkt auf mindestens der Hälfte der Bilder | 100 % | |

Lesart:
- ±2 s verfehlt fast alles, weil die geschätzte Zeit der Kandidaten systematisch neben der
  Markierung liegt: im Median 2.8 s danach (Quartile 0.6 und 4.3 s, 114 Würfe mit einem Kandidaten in
  −5/+6.5 s). Die Kandidaten wurden für das Fenster −3/+8 s gebaut (`ml/goals/shot_eval.py`); dort
  finden sie 85 % der Würfe. Für Clips (7 s vor, 3 s nach dem Peak) reicht das, für eine genaue
  Wurfzeit nicht. Das Fenster −3/+8 s wurde vor dem Blick auf die Endtest-Zahlen aus der Doku
  gewählt (Dev-Segment), nicht auf dem Endtest.
- Abdeckung heisst: der Ballpfad hat einen Punkt, nicht dass er richtig liegt. Der Endtest hat keine
  Ballmarkierungen; die Trefferquote misst gold v1 (hrp1 960 jedes 3. Bild: 63.5 %). Das Ziel 85 bis
  90 % Abdeckung ist erreicht, über die Richtigkeit sagt es nichts.
- Nicht gemacht: die GPU-Einstellung (jedes Bild), auch nicht genähert (Budget). Laufzeit auf Kaggle
  (4 Kerne, ein Prozess): im Mittel 1266 s pro 3-min-Segment, 7.0 x Videolänge.

### Wurfzeit der Kandidaten (2026-11-19)

Frage: Warum liegt die geschätzte Wurfzeit der Wurf-Kandidaten im Endtest im Median 2.8 s nach
Lukas' Markierung, und lässt sie sich ohne Verlust an Recall genauer machen?

Wie die Zeit entsteht (`goalcandidates.shot_candidates`):
- Der Kandidat ist der Peak von `shot_score` = rz(Kosinus zur Wurf-Vorlage) + rz(Kosinus zur
  Tor-Vorlage) + rz(Flaute danach), auf dem 10-Hz-Raster aus Kameraschwenk und Personen-Bewegung.
  Beide Vorlagen (Fenster 2 s vor bis 3 s nach dem Peak) zeigen dasselbe: die Kamera schwenkt
  anhaltend in eine Richtung, die Spieler laufen schnell und werden langsamer. Das ist das Kippen
  des Spiels nach dem Angriff (Rücklauf, Abwurf des Torhüters, Anwurf), nicht der Abwurf selbst.
- Die Wurfzeit ist Peak minus `shot_offset_s` = 1.5 s (`data/shot_template.json`). Diese 1.5 s sind
  der Median von Peak minus **Protokollzeit** auf den Dev-Daten, nicht minus Abwurf.

Diagnose (zwei Anteile):
- **Systematisch: die Bezugszeit.** Dev (28 Segmente, 7 Spiele, 93 Würfe aus den offiziellen
  Spielberichten, leave-one-game-out, gespeichert in `shot_template.json`): Peak minus Protokollzeit
  im Median +1.5 s. Endtest (gespeicherter Bericht oben, Markierung = Abwurf auf etwa 1 s): Peak minus
  Markierung im Median 1.5 + 2.8 = 4.3 s. Liegt der Peak in beiden Sätzen gleich zum Spiel, kommt der
  Protokolleintrag rund 3 s nach dem Abwurf (Schluss aus zwei Datensätzen, nicht gemessen). Das passt
  zu den Protokollen der 3. Liga, die 4 bis 6 s hinter der Anzeige liegen (`ml/goals/README.md`), und
  zu `pick_shots.py` / `shot_check.py`, die den Wurf vor der Protokollzeit suchen.
- **Veränderlich: das Kippen folgt dem Wurf nicht im festen Abstand.** Dev, Peak minus Protokollzeit
  nach Ausgang: Tore +0.9 s, gehalten +1.8 s, daneben +2.6 s (IQR 2.6 bis 3.5 s). Endtest: Quartile
  0.6 und 4.3 s, also 3.7 s Breite bei Markierungen auf etwa 1 s; die Streuung kommt vom Signal, nicht
  von den Markierungen.

Warum keine Korrektur eingebaut ist:
- **Konstante Verschiebung:** Auf Dev gibt es keine Abwurfzeiten, nur Protokollzeiten; damit lernt
  man wieder die 1.5 s von heute. Die Konstante aus dem Endtest zu nehmen hiesse, auf dem Endtest
  einzustellen. Selbst die ideale Konstante brächte bei 3.7 s Quartilbreite nur etwa die Hälfte der
  114 Würfe mit einem Kandidaten in ±2 s (grob, aus den gespeicherten Endtest-Quartilen gelesen,
  nicht verwendet).
- **Auf den Ballpfad setzen** (schnellste Ballbewegung zum Tor vor dem Peak): Für die Dev-Segmente
  ist kein Ballnetz-Ergebnis gespeichert (`ml/goals/README.md`, Shots/Data), und die privaten
  Kaggle-Daten waren aus dieser Sitzung nicht erreichbar (403, kein Schlüssel eingesetzt). Die einzige
  Dev-Prüfung dazu (41 Dev-Wurfclips, oben «Wurf-Ereignisse: erster Befund») fand den Wurf über die
  Ballgeschwindigkeit nicht besser als Zufall.
- **Die API rechnet mit der Protokollzeit:** `goal_ms` dient auch zum Zuordnen der Spielbericht-Einträge
  (`services/goal_candidates.py`, Fenster 8 bis 20 s). Eine auf den Abwurf verschobene Zeit müsste
  dort die Protokoll-Verzögerung wieder dazurechnen.
- Für die Clips reicht die heutige Zeit: der Abwurf liegt im Median 4.3 s und im oberen Quartil 5.8 s
  vor dem Peak, der Clip beginnt 8 s davor.

Geändert: nur Doku und Messung. In `goalcandidates.py` sagt der Kommentar zu `offset_s` jetzt, dass er
auf die Protokollzeit bezogen ist. `ml/integration/shot_segments_eval.py score` schreibt pro Wurf den
Abstand des nächsten Kandidaten-Peaks zur Markierung (`per_shot` in score.json), damit eine auf Dev
festgelegte Methode später auf dem Endtest ohne neuen Lauf der Kette gemessen werden kann. Der
gespeicherte `shot_endtest_result.json` hat keine Werte pro Wurf.

Nächster Schritt:
1. Abwurfzeiten auf Dev: Lukas markiert mit der Seite «Würfe markieren» die Abwürfe der 41
   Dev-Wurfclips (`ml/gold/shot_clips.json`, split dev, ein Klick pro Clip) oder der 28
   Protokoll-Segmente (93 Würfe). Damit: Konstante auf Dev, und der Ballpfad als Anker (letzte schnelle
   Bewegung Richtung des Tors, auf das die Kamera schaut, im Fenster 6 s bis 0.5 s vor dem Peak, mit
   Sicherheit aus Geschwindigkeit und Abdeckung), beides gegen ±2 s auf Dev.
2. Dafür die Beobachtungen der Dev-Segmente mit Ballnetz (CPU-Testeinstellung wie im Endtest) als
   Kaggle-CPU-Kernel rechnen; die Sitzung braucht dazu den Kaggle-Zugang.
3. Erst danach: die festgelegte Methode einmal auf dem Endtest melden (aus `per_shot` und den
   gespeicherten Kandidaten), und die API-Zuordnung zum Spielbericht auf die neue Zeit anpassen.

### Tore aus dem Spielbericht ohne Frage (Livegang L1, 2026-11-19)

Frage: Welche Tor-Kandidaten kann die App mit dem offiziellen Spielbericht selbst beantworten, ohne
je ein falsches Tor zu setzen?

Was vorher schon galt (`services/goal_candidates.py`, `services/checks.py`, `services/graphics.py`):
- Ein Tor des Spielberichts deckt jeden Tor-Kandidaten in 20 s um seine gespeicherte Videozeit
  («schon erfasst», keine Frage). Diese Zeit ist beim Import aus der Uhr gerechnet, meist ab dem
  Anwurf der Halbzeit (`video_from_clock`). Nach einem Time-out liegt sie eine Minute zu früh, am
  Ende einer Halbzeit oft mehrere Minuten. Dann deckt das Tor den falschen Kandidaten, und der
  richtige wird gefragt.
- Ein Spielbericht-Tor mit Videozeit zählt als platziert (`goals_missing`). Hat jedes Tor des
  Resultats eine Zeit im Video, fragt die Hauptrunde gar keinen Tor-Moment mehr; die Kandidaten
  warten unter «Mehr prüfen».
- Das Tor selbst bleibt an der geschätzten Zeit, ohne Clip und ohne genaue Szene.

Neu (`goal_candidates.auto_accept`, nach jeder Analyse und jedem Import des Spielberichts): Ein Tor
des Spielberichts wird ohne Frage auf einen Kandidaten gelegt, nur wenn alles davon gilt:
1. Die Matchuhr wurde zu dieser Spielzeit im Video gelesen: die Zeit liegt in einem Lauf der
   gelesenen Uhr (Einblendung oder Hallentafel, `match_clock.read_ms`, Lesungen alle 2 s). Aus
   dem Anwurf gezählt, zwischen zwei Läufen geschätzt oder von zwei Läufen verschieden gelesen:
   nie.
2. Kein anderes Tor des Spielberichts (beide Teams) liegt 20 s Spielzeit oder näher.
3. Genau ein Tor-Kandidat (jede Rate, nur verworfene nicht gezählt) liegt 8 s vor bis 13 s nach
   der Spielberichtszeit, und dieser liegt 3 s vor bis 8 s nach ihr (Peak minus Spielberichtszeit;
   das Fenster, in dem die Messungen in `ml/goals` einen Kandidaten als dieses Tor zählen).
4. Der Kandidat ist unberührt (offen, nicht «Weiss nicht»), schlägt nicht das andere Team vor, und
   an seinem Moment ist sonst nichts bekannt (ein Tor von Hand, aus der Einblendung, ein bestätigter
   Wurf, ein schon gelegter Spielbericht-Eintrag).
5. Der Trainer hat diese Übernahme nicht schon einmal zurückgenommen.

Gespeichert wie die Bestätigung des Trainers: der Spielbericht-Eintrag bekommt die Zeit des
Kandidaten (`attributes.video`, mit `auto: "report"`), der Kandidat ist bestätigt, ohne Prüfer und
ohne Zeitpunkt (er verbraucht keine Frage der Runde). Prüfen zeigt diese Tore unter «Beantwortet»
mit «aus dem Spielbericht übernommen» und «Rückgängig», die Kandidatenliste mit demselben Hinweis.
Zurückgenommen geht das Tor an seine Zeit aus der Uhr zurück und ist mit `auto_declined` markiert:
nie wieder automatisch, auch nicht nach einem neuen Import. Bestätigt der Trainer es selbst, ist es
seine Antwort. Alles andere bleibt eine Frage wie bisher.

Gemessen: Echte Spiele mit Spielbericht, gelesener Uhr und gespeicherten Kandidaten liegen in diesem
Repository nicht; eine Zahl für Lukas' Video oder andere echte Spiele gibt es darum nicht. In
Lukas' 99 min las die Analyse die Uhr nur über einen Teil des Spiels (oben); nur dort könnte die
Regel greifen. In den Tests (synthetisch, `tests/test_goal_auto_accept.py`):
- Spielbericht-Beispiel mit einem durchgehenden Uhrlauf: 3 von 7 Kandidaten übernommen; die
  Fragen in Prüfen bleiben gleich (1 Tor-Frage mit und ohne Regel), weil die Kandidaten an
  Spielbericht-Toren schon vorher als «schon erfasst» galten. Neu ist, dass die Tore an der Zeit
  des Kandidaten liegen.
- Dasselbe mit einer Minute Uhrstillstand nach 03:30: ohne Regel 1 Tor-Frage (der Kandidat von
  04:02 gilt nach der 20-s-Regel als das um eine Minute zu früh geschätzte Tor von 04:53, der von
  04:53 wird gefragt); mit Regel 0 Fragen, beide Tore an ihrem Kandidaten.

Nicht gemacht: Kandidaten ohne Spielbericht-Tor in der Nähe aus der Standardliste nehmen
(Herabstufen auf Rate 4). Die Stufe gibt es, aber für einen «tiefen Wert» fehlt eine auf Daten
festgelegte Schwelle, und mit vollständigem Spielbericht fragt die Hauptrunde ohnehin höchstens
1.5 mal die Tore ohne Platz im Video. Ein Spielbericht-Tor, dessen Zeit aus der Uhr geschätzt ist,
kann dort fehlen, wo es wirklich fiel; ein Herabstufen würde dann genau das echte Tor verstecken.

Offen: Die Regel braucht die gelesene Uhr. Wo die Tafel minutenlang nicht im Bild ist (Abschnitt
Pausenerkennung), bleibt es bei Fragen. Bessere Tor-Kandidaten (Präzision 29 %) sind ein eigener
Auftrag.

### Ballpfad als Bestätigung der Tor-Kandidaten (A1, 2026-11-20)

Frage: Trennt der Ballpfad echte Tore von Fehlalarmen, so dass die Quote der Tor-Kandidaten (2 pro
Spielminute) sinken darf?

Daten: 49 Dev-Segmente aus 13 Spielen mit offiziellem Spielbericht (113 Tore, `ml/data/segment_labels`),
beobachtet wie der Wurf-Endtest (hrp1 960 px jedes 3. Bild, YOLOX jedes 3. Bild), Kaggle-Kernels
`handball-shot-dev-0` bis `-4`. Endtest nicht angeschaut. Merkmale pro Kandidat (alle 568 bis Rate 4)
in `ml/integration/goal_ball_cues.py`, Auswertung `goal_ball_cues_eval.py`. Ball als Azimut auf dem
Kamerazylinder, Spielfeld zwischen dem 3. und 97. Perzentil des Balls (keine Kalibrierung nötig).

| Merkmal | AUC (Tor gegen Fehlalarm) |
|---|---|
| Wert der Kandidaten heute (`score`) | **0.81** |
| Ballgeschwindigkeit 6 s vor dem Peak (95. Perzentil) | 0.67 |
| Ball nahe einem Torende 4 s vor dem Peak | 0.55 |
| Anwurf: Ball ruhig nahe der Mitte, 2 bis 25 s nach dem Peak | 0.53 |

Kombiniert (logistische Regression, Spiel für Spiel ausgelassen), Tore gefunden / Präzision bei
1, 1.5 und 2 Kandidaten pro Spielminute:

| | 1 / min | 1.5 / min | 2 / min |
|---|---|---|---|
| nur `score` (heute) | 0.56 / 0.45 | 0.71 / 0.42 | 0.85 / 0.34 |
| `score` + Ballgeschwindigkeit | 0.58 / 0.47 | 0.71 / 0.43 | 0.83 / 0.34 |
| alle Merkmale | 0.58 / 0.46 | 0.70 / 0.42 | 0.83 / 0.34 |

Ergebnis: **Der Ballpfad hilft den Tor-Kandidaten nicht.** Die Ballgeschwindigkeit trägt allein etwas,
steckt aber schon im heutigen Wert (Kamera und Spieler kippen mit dem schnellen Ball). Das
Anwurf-Muster ist im Ballpfad nicht zu sehen; der Pfad stimmt auf gold v1 nur zu etwa 64 %, und bei
ruhigem Ball an der Mittellinie fehlt dem Netz oft der Kontrast. Nichts eingebaut, nicht auf dem
Endtest gemessen. Eine tiefere Quote kostet so Tore: 1.5 pro Minute spart ein Viertel der Fragen und
verliert 14 von 100 Toren.

Was bleibt für weniger Fragen: Zeit ohne Spiel (Pausen, Einspielen, Nachspiel). Dafür beobachtet die
Warteschlange `ml/integration/kaggle/observe_queue.py` die übrigen Segmente der Bibliothek, darunter
die Halbzeiten der 13 Dev-Spiele.

### Wurfzeit auf Dev, Fehlalarme und Pausen (Analyse-Sitzung, 2026-11-25)

Nur Dev-Daten, Endtest nicht angeschaut. Daten: 49 Dev-Segmente aus 13 Spielen (Kernels
`handball-shot-dev-0` bis `-4`, wie im Wurf-Endtest beobachtet), 171 Würfe aus den Spielberichten.
Skripte `ml/integration/shot_time_dev.py` (Merkmale und Auswertung), `ml/integration/pause_dev.py`.

**1. Dev-Abwurfmarken gibt es noch nicht.** Die Seite «Würfe markieren» enthält nur die 42
Endtest-Segmente; «Würfe Ball prüfen» hat Ball-Urteile auf den 41 Dev-Clips, aber keine Abwurfzeit.
Ohne Abwurf auf Dev lässt sich die Wurfzeit nicht ehrlich wählen: gegen die Spielbericht-Zeit
gemessen liegt die heutige Methode schon bei 58 % in ±2 s (Versatz 1.35 s, Spiel für Spiel
ausgelassen), weil sie auf diese Zeit eingestellt ist; im Endtest gegen Lukas' Abwurf sind es 21 %.
Neu: die Seite **«Abwürfe Dev»** (https://claude.ai/artifact/X1AUB2nXAkX9eVTV977paz, Quelle
`ml/gold/labelling/release_dev.html`, Clips `ml/gold/release_dev_clips.py`): pro Dev-Wurf ein Clip
von 12 s (9 s vor bis 3 s nach der Spielbericht-Zeit), Bild für Bild, ein Klick beim Abwurf, 175
Würfe. Gespeichert in der db-Sammlung `releases` (`t_s` = Sekunde im Segment). Danach
`shot_time_dev.py eval FEAT.pkl MARKS.json` vergleicht die Methoden mit ±2 s und Bootstrap über die
Spiele; die gewählte Methode wird dann einmal auf dem Endtest gemessen.

**2. Ballpfad als Abwurf-Anker, gegen die Spielbericht-Zeit (nur Vorprüfung):**

| Methode (Versatz Spiel für Spiel ausgelassen) | in ±2 s der Spielbericht-Zeit | Wurf im Fenster −3/+8 s |
|---|---|---|
| Kandidaten-Peak (heute) | 57.9 % (50.0 bis 64.8) | 91.8 % |
| letzter schneller Ball (90. Perzentil) 6 bis 0.5 s vor dem Peak | 54.4 % (43.3 bis 64.2) | 88.9 % |
| dasselbe, 98. Perzentil | 46.8 % (37.5 bis 54.3) | 71.3 % |

Streuung (IQR) gegen die Spielbericht-Zeit: Peak 3.0 s, Ball-Anker 2.9 bis 3.3 s. Der Ballpfad macht
die Zeit gegen den Spielbericht nicht genauer. Ob er gegen den echten Abwurf hilft, zeigen erst die
Marken; der Spielbericht selbst streut um einige Sekunden. Ergebnis: `ml/integration/results/shot_time_dev_logref.json`.

**3. Fehlalarme der Wurf-Kandidaten und Ballpfad:** 568 Kandidaten bis Rate 4 auf Dev, 28.9 % nahe
einem Wurf. Kandidaten-Wert allein AUC 0.823, mit Ballgeschwindigkeit, Anteil schneller Ball und
Abdeckung 0.825 (logistische Regression, Spiel für Spiel ausgelassen). Wie bei den Tor-Kandidaten
(A1) hilft der Ballpfad nicht; nichts eingebaut. Die Rate bleibt der Hebel (3.9 pro Minute auf Dev).

**4. Pausen, Variante 2 (Uhr der Dev-Spiele):** Wahrheit pro Segment aus der im Video gelesenen
Uhr, über den Spielbericht auf Halbzeiten gelegt (Segment in der Halbzeit: Anteil laufende Uhr;
ganz vor Anpfiff, in der Pause oder nach Schluss: 0). 65 Segmente (49 aus den Dev-Kernels, 16 aus der
Warteschlange q059, q060, q067). Produkt: `play_s` aus `goalcandidates.from_observations`.

| Segmente | Anzahl | Uhr läuft (Anteil) | Produkt sagt «Spiel» | Fehler (Median) |
|---|---|---|---|---|
| in einer Halbzeit | 51 | 77 % | 95 % | 0.13 |
| Halbzeitpause | 11 | 0 % | **98 %** | 1.00 |
| vor Anpfiff / nach Schluss | 1 / 2 | 0 % | 0 % (eins ohne Ergebnis) | 0 |

Lesart: Die `no_play`-Regel (Spieler stehen still oder in einer Gruppe) erkennt die Halbzeitpause
fast nie. Im Bild (Stäfa s2 angeschaut): Einblendung «Pausenstand», Wiederholungen von Szenen der
ersten Halbzeit und Einwerfen der Spieler; das sieht für Kamera und Bewegung wie Spiel aus. In der
Halbzeit nennt das Produkt auch Time-outs und Unterbrüche meist Spiel (95 % statt 77 %). Hebel: keine
laufende Uhr über mehrere Minuten (Einblendung oder Hallentafel) als Pause werten, die
Spielbericht-Zeiten der Halbzeiten nutzen, wo ein Bericht da ist. Die 11 Pausen-Segmente sind 3 min
lang; eine ganze Pause dauert 10 bis 15 min, auf Lukas' 99-min-Video also grob 20 bis 30 Wurf- und
Tor-Fragen, die so wegfallen könnten (Schätzung aus den Raten, nicht gemessen). Ergebnis:
`ml/integration/results/pause_dev.json`.

**5. Wurfort-Schätzung (A2):** Aus dieser Sitzung kein Zugang zu Staging. Dazu eine Lücke im Produkt:
`set_spot` speichert nur bestätigte Schätzungen (`confirmed_estimate`). Wählt der Trainer eine andere
Zone oder tippt einen Punkt, wird die Schätzung überschrieben; die Zahl der abgelehnten Schätzungen
fehlt damit, und eine Trefferquote lässt sich aus den gespeicherten Daten nicht rechnen (nur nachträglich,
indem `fill_one` für beantwortete Würfe aus den Spuren neu gerechnet wird). Vorschlag: die geschätzte
Zone beim Antworten mitspeichern (`attributes.estimated_zone`).

**Nachtrag 25.11.: Pause zwischen zwei Uhr-Läufen im Produkt (`goalcandidates.clock_breaks`).** Eine
Lücke von mindestens 2 min zwischen zwei Läufen der Matchuhr gilt als kein Spiel (10 s Rand an
beiden Enden), zusätzlich zu Kamera geparkt, Spieler zusammen und Einspielen. Begründung: Eine Tafel,
die bei laufendem Spiel aus dem Bild ist, überbrückt `scoreboard.play_intervals` schon (Uhr lief
mindestens die Hälfte der Lücke); eine übrig bleibende lange Lücke heisst, die Uhr stand. Vor dem
ersten und nach dem letzten Lauf greift die Regel nicht. Ausgabe neu `clock_break_ms`; die Strecken
stehen auch in `no_play_ms` (Prüfen zeigt sie so schon an). Tests in `test_goalcandidates.py`.

Messung auf den 65 Dev-Segmenten, vorher (ohne Uhr) und nachher (mit den zwei Halbzeiten aus dem
Spielbericht als Uhr-Läufe; Annahme: das Produkt liest die Uhr vor und nach der Pause):

| Segmente | Uhr läuft | Produkt vorher | Produkt nachher |
|---|---|---|---|
| in einer Halbzeit (51) | 77 % | 95 % (Fehler 0.13) | 92 % (Fehler 0.10) |
| Halbzeitpause (11) | 0 % | 98 % | **0 %** |
| vor Anpfiff / nach Schluss (3) | 0 % | 0 % | 0 % |

Kein Halbzeit-Segment verliert echtes Spiel; die drei, die sich ändern (Anfang einer Halbzeit),
liegen danach näher an der Uhr. Grenze der Messung: Die Uhr-Läufe sind aus dem Spielbericht
genähert, nicht vom Produkt gelesen; ob die Tafel in echten Videos um die Pause lesbar ist, zeigt erst
ein ganzer Lauf (Lukas' 99-min-Video: Uhr bei 0:00 in der Pause gelesen, `Nachtrag` oben, dort
also wirksam). Ergebnis: `ml/integration/results/pause_dev.json`.

### Wurfzeit: Methode auf Dev gewählt, Endtest einmal gemessen (Analyse-Sitzung, 2026-11-26)

**Wahrheit auf Dev: LLM-Marken, nicht Lukas'.** Lukas markiert nicht mehr (Entscheid der
Hauptsitzung vom 25.11.). Die Abwürfe der 175 Dev-Würfe hat Claude per Bildsicht gesetzt: zwei
unabhängige Durchgänge mit verschiedenem Raster und verschiedener Reihenfolge, ohne Zugriff
aufeinander, und ein dritter Blick auf jeden Wurf, bei dem die beiden mehr als 0.4 s auseinander
lagen oder nur einer einen Wurf fand. Abwurf = letztes Bild mit dem Ball in der Hand.
- Übereinstimmung: 128 Würfe innerhalb 0.4 s (Median der Abweichung 0.04 s), 15 weiter auseinander,
  18 nur in einem Durchgang, 14 in keinem (meist Spielbericht-Einträge ohne sichtbaren Wurf,
  z. B. «leeres Tor», Schnitte, Wiederholungen).
- Ergebnis eingefroren in `ml/gold/data/shot_release_dev_llm.json` (sha256
  cca0c66c243925d1c2de76bba51afa80cdc3001d3044f98ffe6d238c94005521): 94 sichere, 65 unsichere,
  16 nicht sichtbare Würfe. Zusammenführung `ml/gold/merge_release_marks.py`.
- Der Spielbericht kommt im Median 3.9 s nach dem Abwurf (IQR 3.2 bis 4.7 s).

**Methodenwahl (nur Dev, 94 sichere Marken, 13 Spiele, Versatz Spiel für Spiel ausgelassen):**

| Methode | in ±2 s des Abwurfs | mit unsicheren Marken (159) |
|---|---|---|
| Kandidaten-Peak minus fester Versatz | **74.5 %** (62.4 bis 86.4), Versatz 4.96 s | 71.7 % |
| letzter schneller Ball (Ballpfad, 90. Perzentil) | 77.7 % (66.2 bis 87.5) | 67.3 % |
| dasselbe, 98. Perzentil | 58.5 % | 50.9 % |

Gewählt: Peak minus fester Versatz. Der Ballpfad ist mit sicheren Marken innerhalb des Rauschens
gleich, mit den unsicheren schlechter und hängt am Ballnetz. Versatz über ganz Dev 4.96 s, im
Produkt 5.0 s (`shot_template.json`, Version 2026-11-26.s2). Die API ordnet Wurf-Kandidaten dem
Spielbericht jetzt mit `goal_ms` + 4 s zu (`SHOT_LOG_DELAY_MS`), sonst unverändert. Ein bestätigter
Wurf liegt damit beim Abwurf statt bei der Spielbericht-Zeit.

**Endtest, einmal mit der eingefrorenen Methode** (Lukas' Marken, 41 von 42 Segmenten: bei
`AT_Challenge_Lauterach_HandballTirol_2021_s1` fehlen die gespeicherten Beobachtungen, 129 Würfe;
Kandidaten mit dem heutigen Produktcode aus den gespeicherten Beobachtungen neu gerechnet;
`ml/gold/data/shot_endtest_result_release.json`):

| Mass | vorher (19.11., Versatz 1.5 s) | jetzt (Versatz 5.0 s) |
|---|---|---|
| Würfe mit Kandidat in ±2 s | 20.8 % | **55.8 %** (46.8 bis 65.6) |
| davon Tore / gehalten / daneben | | 61.3 / 48.8 / 46.2 % |
| Präzision in ±2 s | 6.3 % | 17.3 % |
| Fenster −3/+8 s (Peak), Würfe / Tore | 84.6 / 88.2 % | 84.5 / 88.0 % |
| Wurf-Kandidaten pro Minute | 3.39 | 3.37 |

Lesart: Die Mehrheit der Würfe liegt jetzt in ±2 s (Ziel erreicht), Fehlalarme und Rate sind
gleich (nur die Zeit ist verschoben). Dev 74.5 % gegen Endtest 55.8 %: LLM-Marken auf Dev gegen
Lukas' Marken (etwa 1 s genau) in 42 neuen Hallen; die Streuung des Kippens nach dem Wurf bleibt
(Abschnitt «Wurfzeit der Kandidaten»). Der Endtest ist damit für die Wurfzeit verbraucht.

**Ball: hr-nods (ohne DeepSport) gegen hr1 auf Ball-Testset 2** (`ml/gold/eval_ball_test2.py`,
eingefrorene LLM-Labels, 85 Bälle und 30 Bilder ohne Ball, `ml/ball/LINEAGE.md` T5):

| Netz | Top-1 in 12 px | gefunden bei 0.5 | Bilder ohne Ball mit Peak ≥ 0.5 |
|---|---|---|---|
| hr1 (mit DeepSport) | 72.9 % (64.0 bis 82.1) | 62.4 % | 10 % |
| hr-nods (ohne DeepSport) | 68.2 % (57.1 bis 79.8) | 58.8 % | 10 % |

Paarweise: 9 Bälle nur hr1, 5 nur hr-nods; kein gesicherter Unterschied. Ein auslieferbares Netz
kostet höchstens wenige Punkte. Ergebnis `ml/integration/results/ball_test2_hr1_vs_hrnods.json`.
### Laufzeit eines ganzen Spiels auf CPU (Produkt-Audit Punkt 2, 2026-11-26)

Das Audit (`docs/plans/produkt-audit-2026-11.md`) rechnete aus zwei 8-min-Läufen auf Staging 7 bis
8 h Analyse für ein ganzes Spiel hoch, über dem RQ-Timeout von 6 h. Nachgeprüft:

- **ReID lief nur auf kurzen Clips.** `HB_BALL_ALLOW_CPU=1` (Staging, für Ball-Tests) schaltete auch
  ReID auf der CPU ein, aber nur bis `ball_max_minutes` (12 min). Die 8-min-Läufe hatten darum ReID
  (34 von 60 min), ein ganzes Spiel nie. Neu läuft ReID nur mit GPU, unabhängig vom Schalter
  (`load_embedder`); 8-min-Testläufe auf Staging werden damit etwa doppelt so schnell.
- **Messung** (`ml/integration/profile_analysis.py`, Code von heute, Staging-Einstellungen inklusive
  Ballnetz-Schalter, 2 Kerne wie der Staging-Worker; Video: die zwei 10-min-Testclips SG Horgen H1
  und H2 hintereinander, 20 min, mit der Produkt-Umwandlung):

| Stufe | s | x Videolänge |
|---|---|---|
| Proxy-Umwandlung (eigener Job, Ingest) | 230 | 0.19 |
| Analyse gesamt | 2 980 | **2.46** |
| davon YOLOX (alle 3 Bilder) | 1 412 | 1.17 |
| davon Rückennummern | 909 | 0.75 (Budget-Deckel) |
| davon Kamerabewegung | 349 | 0.29 |
| davon Hallentafel | 78 | 0.06 |
| davon Linien | 48 | 0.04 |

  - Ballnetz: `too_long_for_cpu` (aus, wie für jedes Video über 12 min), ReID nicht geladen.
  - Die Kalibrierung scheiterte auf dem zusammengesetzten Video (Schnitt zwischen den Halbzeiten);
    Tracking, Stitching und Ereignisse fehlen darum. Auf den Einzelclips kosteten sie zusammen etwa
    6 s pro 10 min (Tabelle «Ganze Kette auf den Testclips»), fallen also nicht ins Gewicht.
  - Während etwa 2 min lief ein Testlauf mit, die Zahl ist eher etwas zu hoch.
- **Hochgerechnet:** 60 min Spiel etwa 2.5 h, 99 min etwa 4.1 h Analyse auf 2 vCPU, unter 6 h. Das
  passt zu Lukas' ganzem Lauf auf Staging (99 min, 2.2 x, 17.11.). Das Budget pro Job ist ohnehin
  `max(6 h, 3 x Videolänge + 1 h)` (`services/video_jobs.job_budget_s`).
- **Ingest** (1 vCPU, eigener Job): Gemessen auf einer Quelle 1080p50 mit 15 Mbit/s, 120 s, auf
  einem Kern: HLS-Leiter 323 s, Proxy 97 s, zusammen 419 s (3.5 x Videolänge, wie Staging mit
  3.6 x). Neu entstehen HLS und Proxy in einem ffmpeg-Lauf mit einem Decode: 371 s (3.1 x, minus
  11 %), Dateien identisch (gleiche Bildzahl und Grösse). Ein 99-min-Video braucht so etwa 5.1 h
  Umwandlung plus Thumbnails, knapp unter 6 h. Mehr vCPU für den Worker wäre der grössere Hebel;
  Entscheid der Hauptsitzung (26.11.): vorerst nicht, die GPU löst die Analyse-Laufzeit.

### Seiten aus Anwurf-Formationen (Audit Punkt 4, Vorschlag 1, 2026-11-26)

Idee: Ohne Torhüter die Spielrichtung aus den Anwürfen ableiten. Dabei stehen beide Teams in der
eigenen Hälfte und fast still, wie `events.refine_teams` solche Momente schon sucht; die Labels
links der Mittellinie sagen dann, wer links verteidigt. Offline geprüft auf drei Staging-Läufen
aus dem Testbucket (Homographie zurückgerechnet, `ml/integration/staging_offline/`, siehe #147):

| Lauf | Momente streng (≥ 10 Spieler, je ≥ 4 pro Hälfte, Median < 1 m/s) | locker (≥ 8, je ≥ 3, < 1,5 m/s) | Seite wie Torhüter |
|---|---|---|---|
| H (8 min) | 1 | 27 Bins | ja (1 von 1) |
| fbdc76e6 (5 min) | 0 | 0 | - |
| 56fcc216 (5 min) | 0 | 0 | - |

Ergebnis: Mit schwenkenden Vereinskameras ist eine Anwurf-Formation fast nie ganz im Bild. Die
Kamera zeigt eine Hälfte, und selten sind genug Spieler auf beiden Seiten getrackt. Als zweite
Quelle für die Seiten trägt das nicht. Nicht ins Produkt übernommen (eine Übereinstimmung ist
kein Beleg). Bessere Kandidaten für Seiten ohne Torhüter: die Hallentafel (Seitenwechsel zur
Halbzeit) zusammen mit einem Hinweis des Trainers, auf welcher Seite er beginnt, oder die
Angriffsrichtung aus der Bewegung beider Teams über längere Abschnitte.
