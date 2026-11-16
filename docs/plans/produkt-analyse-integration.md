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
