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
   - Kalibrierung (grösster Blocker für Taktiktafel und Wurfzonen);
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
