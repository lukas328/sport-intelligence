# Produkt-Analyse: Integration der Forschung (Stand 2026-11-16)

Auftrag von Lukas (2026-11-16): den aktuellen besten Stand jetzt ins Produkt bringen und die Analyse
als ganzes Produkt denken, nicht nur den Ball. Testphase: Lizenzen sind vorerst egal (die Ballnetze
ab Runde 3 enthalten DeepSport, nur Forschung; vor einem echten Livegang braucht es Netze ohne
DeepSport, siehe `docs/plans/tracking-strategie.md` Abschnitt 9). Massstab: **Kosten unter etwa
1 Euro pro Spiel**; die Dauer ist zweitrangig.

Rollen: Die **Hauptsitzung** (Ball-Forschung, Projektleitung, Merges nach `main`) koordiniert. Die
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
- **Offen in Schritt 2:** Ballpfad speichern (Parquet) und an `graphics.py` liefern; Netze in den
  Staging-Bucket laden (Skript, nur mit Freigabe von Lukas); GPU-Laufzeit messen.
