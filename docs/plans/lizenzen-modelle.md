# Lizenzen der Modelle und Trainingsdaten im Produktpfad

Stand 2026-11-26. Inventar aller Modelle, Trainingsdaten und lizenzrelevanten Bibliotheken, die
für einen Kunden laufen (`apps/*`, `packages/*`, Images und Staging-Konfiguration). Quelle sind die
Angaben im Repository selbst (Modellkarten unter `ml/models/`, `ml/ball/LINEAGE.md`,
`ml/datasets/LICENSES.md`, ADR 003, ADR 028, `docs/plans/ball-stand-der-technik.md`, Dockerfiles,
Terraform). Das ist keine Rechtsberatung: was hier «unklar» heisst, braucht eine juristische
Prüfung, bevor ein zahlender Verein es bekommt.

Legende «kommerziell»: **ja** (Lizenz erlaubt es nach Angaben der Quelle), **nein** (nur Forschung
oder nicht-kommerziell), **unklar** (nicht geprüft oder widersprüchlich).

## 1. Kurzfassung

- **Sauber:** Personen-Detektor YOLOX-S und Nummern-OCR PP-OCRv4 (beide Apache-2.0, im Image),
  Tesseract für Einblendungen, alle Regel-Stufen (Kalibrierung, Taktik, Ereignisse, Audio), die
  Bibliotheken im Lockfile und Claude über die Anthropic-API.
- **Nicht auslieferbar, aber auf Staging aktiv:** das Ballnetz hrp1 (DeepSport, CC BY-NC-SA) und
  ReID FastReID (MSMT17, nur Forschung). Beide liegen nicht im Image, werden aber zur Laufzeit aus
  dem Bucket geladen (`infra/terraform/azure/main.tf:551`, `infra/azure/staging-env.json:2`). Die
  Aussage in `docs/OPEN_QUESTIONS.md` «kein ReID- und kein Ballmodell» stimmt für das Image, nicht für
  den Betrieb.
- **Ersatz:** Ball: `hr-nods` (hr1 ohne DeepSport, von Grund auf trainiert) liegt bereit, 68.2 %
  gegen 72.9 % für hr1 auf Ball-Testset 2, Unterschied nicht auflösbar. ReID: ausschalten (spart
  auch 56 % der CPU-Laufzeit, Audit Rang 2), eigenes Modell erst mit eigenen Spieler-Labels.
- **Fehlt:** der in ADR 003 versprochene CI-Schutz (kein `ultralytics`, keine NC-Modelle in der
  Produktion) existiert nicht.

## 2. Modelle

| # | Stufe | Modell, Datei | Weg ins Produkt | Code / Gewichte | Trainingsdaten | Kommerziell | Heute | Ersatz | Aufwand |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Personen (und Ball «sports ball») | YOLOX-S COCO, `/models/yolox_s.onnx` | im Image: Release 0.1.1rc0 von Megvii-BaseDetection/YOLOX, SHA-256 geprüft (`apps/gpu-worker/Dockerfile:26`) | Apache-2.0 (`ml/models/yolox-coco.md`) | COCO 2017: Annotationen CC BY 4.0, Bilder von Flickr unter den Lizenzen der Urheber | **ja** (ADR 003); COCO-Bilder rechtlich nicht geprüft, Nutzung von COCO-Gewichten ist branchenüblich | aktiv | - | - |
| 2 | Rückennummern, Hallenuhr | PP-OCRv4 det + rec, `/models/ch_PP-OCRv4_*.onnx` | im Image, aus dem Wheel `rapidocr_onnxruntime==1.4.4` (`Dockerfile:32-41`) | PaddleOCR Apache-2.0, RapidOCR Apache-2.0 (`ml/models/ppocr-v4.md`) | von PaddleOCR, in der Modellkarte nicht genannt | **ja** | aktiv | - | - |
| 3 | Spielstand und Uhr der Einblendung | Tesseract `eng` | Systempaket `tesseract-ocr` (`Dockerfile:50`) | Apache-2.0 (`scoreboard.py:5`) | von Tesseract | **ja** | aktiv | - | - |
| 4 | Ball (Ball v2) | hrp1, `models/ball/ball_hrp1_fp16-37153d8dfc83.onnx` (Staging CPU), `..._u8-8efd55d05333.onnx` (GPU-Standard) | nicht im Image; zur Laufzeit aus dem Artefakt-Bucket mit SHA-256 (`main.tf:551-552`, `variables.tf:253`) | eigener Code; Backbone timm `hrnet_w18` mit ImageNet-Gewichten (Lizenz der Gewichte nicht geprüft) | Runde-10-Mischung, darin **DeepSport (CC BY-NC-SA 4.0)**, TeamTrack (MIT), eigene Labels, OWLv2-Pseudolabels (Apache-2.0) (`ml/ball/LINEAGE.md` D1 bis D14) | **nein** (DeepSport); ImageNet-Gewichte unklar | aktiv auf Staging | `hr-nods` | S (Upload, Terraform-Variable), M für Qualität |
| 5 | Ball (Alternative) | hr1, `models/ball/ball_hr1_fp16-a99d126f7fc6.onnx` | im Bucket hochgeladen (`docs/plans/produkt-analyse-integration.md:341`) | eigener Code, von Grund auf trainiert | wie 4 (DeepSport) | **nein** | nicht konfiguriert | `hr-nods` | S |
| 6 | Wiedererkennung | FastReID BoT-R50 `msmt_bot_R50.pth`, `models/reid/reid-6f3e1b1d0534.onnx` | nicht im Image; Staging setzt `HB_REID_MODEL` (`infra/azure/staging-env.json:2-3`) | Code und Gewichte Apache-2.0 (`ml/models/reid-fastreid.md`) | **MSMT17, nur nicht-kommerzielle Forschung** | **nein** | aktiv auf Staging (Lauf U: 33.9 min von 60) | ausschalten; später eigenes Modell auf eigenen Spieler-Crops (`ml/reid`: bisher «nicht gut genug») | S (aus), L (eigenes) |
| 7 | Rolle (Spieler, Torhüter, Schiedsrichter) | ResNet18, `/models/roles.onnx` | nicht im Image; Staging `HB_ROLE_MODEL=""` (aus) | timm ResNet18 Apache-2.0, ImageNet-Gewichte (unklar) | vier Roboflow-Projekte «CC BY 4.0» (`ml/roles/README.md`); Herkunft der Bilder nicht geprüft, ein Roboflow-Satz hat Bilder unter EIGD-Bedingungen (`ml/datasets/LICENSES.md`) | **unklar** (ADR 028: «eigenes», README: «research, not shipped») | aus | auf eigenen Torhüter- und Schiedsrichter-Labels neu trainieren, oder Farbregel behalten | M |
| 8 | Torkandidaten, Würfe | Vorlagen `data/goal_template.json`, `shot_template.json` | im Paket | eigener Code | eigene Einblendungs-Tore und Wurf-Labels | **ja** (eigene Daten) | aktiv | - | - |
| 9 | Kalibrierung, Taktik, Ereignisse, Audio-Abgleich, Belastung | Regeln (Hough, ICP, FFT, Geometrie) | im Paket | eigener Code | keine | **ja** | aktiv | - | - |
| 10 | Papierberichte, Assistent, Spieltexte | Claude über die Anthropic-API (`anthropic` 2.4.0; `core/paper_vision.py`, `core/assistant_llm.py`, `core/text.py`) | API-Aufruf mit `HB_ANTHROPIC_API_KEY` | kommerzielle API-Bedingungen von Anthropic | - | **ja** (kommerzielle API); Auftragsverarbeitung und Datenfluss gehören zu Q-INFRA-1 / Datenschutz | aktiv | - | - |

Nicht im Produkt, nur Forschung: Pose (RTMPose über rtmlib, Apache-2.0), OWLv2 (Apache-2.0, nur
als Lehrer für Pseudolabels), Ball-Verifier v1/v2, Ballhalter-Klassifikator, ReID-Eigenversuch.
Die Gold- und Trainingslabels, die Claude erstellt und der Produktverantwortliche geprüft hat
(D12, D13), gelten als eigene Daten.

## 3. Bibliotheken (Produkt-Lockfile `uv.lock`)

| Bibliothek | Version | Lizenz (bekannt, nicht im Repo vermerkt) | Bemerkung |
|---|---|---|---|
| onnxruntime | 1.31.1 | MIT | das CUDA-Image installiert `onnxruntime-gpu>=1.20,<1.24` ungesperrt (`Dockerfile.cuda:35`) |
| opencv-python-headless | 4.14.0.94 | Apache-2.0 | |
| numpy, scipy | 2.5.4, 1.18.1 | BSD-3 | Zuordnung im Tracker über scipy, kein ByteTrack/boxmot |
| av (PyAV) | 19.0.2 | BSD-3; bindet FFmpeg (LGPL/GPL je nach Build) | FFmpeg-Build der Wheels prüfen |
| pillow, pyarrow, reportlab | 13.0.0, 26.0.0, 5.1.0 | HPND, Apache-2.0, BSD | |
| anthropic | 2.4.0 | MIT | |

Nicht im Lockfile: torch, timm, ultralytics (AGPL-3.0, nach ADR 003 verboten), paddle, rapidocr
(nur die Modelldateien aus dem Wheel), boxmot, transformers. Kein Paket im Repo trägt ein
`license`-Feld, es gibt keine `THIRD_PARTY`- oder `NOTICE`-Datei. Schriften liegen mit OFL-Texten
bei.

## 4. Widersprüche in der Dokumentation

1. `docs/OPEN_QUESTIONS.md` (Beantwortet, Q-ML-5, Q-ML-6): «kein ReID- und kein Ballmodell». Für das
   Image richtig; Staging lädt hrp1 und ReID zur Laufzeit. In diesem PR präzisiert.
2. ADR 003 verspricht ab M3 einen CI-Check gegen `ultralytics` in Produktions-Lockfiles. Es gibt ihn
   nicht (`.github/workflows/`).
3. Rollenmodell: ADR 028 nennt es «eigenes (Roboflow-Daten CC BY 4.0)», `ml/roles/README.md` und der
   Audit «nur Forschung». Solange es aus ist, ohne Folgen; vor dem Einschalten klären.
4. `ml/datasets/LICENSES.md`: keine Zeile ist geprüft («Verified: no»), TeamTrack «to check». hr-nods
   hängt an TeamTrack (MIT laut Kaggle); dass die Ball-Labels dort zum MIT-Umfang gehören, ist laut
   `ball-stand-der-technik.md` 3.1 nicht abgeglichen.

## 5. Was vor dem ersten zahlenden Verein zu tun ist

Reihenfolge nach Aufwand und Wirkung:

1. **ReID aus** in jeder Umgebung mit echten Vereinsvideos: `HB_REID_MODEL=""` (Staging-Variable,
   Terraform). Kosten: die Identitäts-Hilfe über Erscheinung fällt weg (lokaler Lauf Horgen H1: 4 von
   138 Tracks über Erscheinung zugeordnet); Gewinn: rund die Hälfte der CPU-Laufzeit. Aufwand S, Sache der
   Hauptsitzung (Infrastruktur).
2. **Ball auf hr-nods umstellen:** Gewichte exportieren (`ml/ball/export_onnx.py`, fp16 und u8),
   in den Bucket, SHA-256 in Terraform. Danach auf Gold v1 mit Tracker messen (heute nur Ball-Testset
   2). Aufwand S bis M. Bis dahin bleibt Ball v2 Testbetrieb (`ballnet.py` Lizenzhinweis).
3. **CI-Schutz:** ein Test, der (a) `ultralytics`, `torch`, `boxmot` im Produkt-Lockfile ablehnt und
   (b) Modell-Schlüssel in `infra/` gegen eine Freigabeliste prüft (`hr1`, `hrp1`, `reid-*` sind dort
   «nur Test»). Aufwand S.
4. **Juristisch prüfen lassen** (einmalig, ein Termin): ImageNet-Startgewichte (betrifft hrp1 und
   das Rollenmodell, nicht hr1 und hr-nods), COCO-Bilder hinter YOLOX, TeamTrack-Ball-Labels, FFmpeg
   im PyAV-Wheel.
5. **Später:** eigenes ReID auf eigenen Spieler-Crops (L, erst mit Labels aus Prüfen), Rollenmodell
   auf eigenen Labels (M).

## 6. Offene Punkte

In `docs/OPEN_QUESTIONS.md` als 🔴 eingetragen: 4a (Ball, bestand), 4b (ReID auf Staging), 4c
(Rechtsprüfung der Startgewichte und Datensätze, CI-Schutz).
