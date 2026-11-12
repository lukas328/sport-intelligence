# Ball-Detektion und -Tracking: Stand der Technik (Recherche)

Stand: 12.11.2026. Recherche per Web, GitHub (raw.githubusercontent.com), Kaggle-API und Hugging-Face-API.
Lizenzangaben stammen, wo vermerkt, direkt aus der LICENSE-Datei im Repo (Branch main oder master, abgerufen am 12.11.2026).
Zahlen sind die von den Autoren berichteten Werte auf ihren eigenen Benchmarks. Sie sind untereinander nur bedingt vergleichbar und sagen wenig über unsere Hallen aus.
Markierung **[nicht verifiziert]** = konnte nicht aus einer Primärquelle bestätigt werden.

Ausgangslage (zur Einordnung): Unser Modell v1 (ResNet18-Stem + layer1/layer2, 3 Frames, Heatmap mit Stride 4) erreicht ca. 35 % Top-1 innerhalb 12 px auf unbekannten Hallen; OWLv2 zero-shot 44 % Top-1 / 66 % Top-5. Ball ca. 8 bis 20 px bei 1280 px Breite.

---

## 1. Methoden für kleine, schnelle Bälle

### 1.1 Übersicht

| Methode | Jahr / Venue | Idee | Berichtete Genauigkeit | Rechenaufwand | Okklusion / Ball in der Hand / Kamerabewegung |
|---|---|---|---|---|---|
| TrackNet (v1) | arXiv 1907.03698, 07.2019 | VGG-artiger Encoder-Decoder, mehrere Frames rein, Gauss-Heatmap raus, 640x360 | Tennis (Universiade 2017): P 99.7 %, R 97.3 %, F1 98.5 %; 10-fach CV auf 9 weiteren Videos: P 95.3 %, R 75.7 %, F1 84.3 % | Original ca. 2.6 FPS (laut Sekundärquelle) | Lernt Trajektorie implizit über Mehrframe-Input; Broadcast-Kamera, aber kein expliziter Umgang mit Kamerabewegung |
| TrackNetV2 | ICPAI 2020 | U-Net, MIMO (3 Frames rein, 3 Heatmaps raus), kleinere Auflösung | Badminton, neues Spiel: Acc 85.2 %, P 97.2 %, R 85.4 % (Originalpaper, via TrackNetV4-Tabelle) | 11.3 M Parameter; 31.8 FPS (3-in-3-out, Originalpaper) | Keine spezielle Okklusionsbehandlung |
| MonoTrack | CVPRW (CVSports) 2022 | TrackNetV2-artig mit Residual-Verbindungen, Dice+BCE-Loss, 2.9 M Parameter; physikbasierte 3D-Rekonstruktion (Gravitation + Luftwiderstand, Fit gegen 2D-Detektionen) | Shuttle-Detektion Acc 84.0 % (TrackNetV2) auf 88.6 % | 2.9 M Parameter | Kein Okklusionsmodul; Physikmodell überbrückt Lücken; statische Kamera mit Kalibrierung vorausgesetzt |
| WASB (nttcom) | BMVC 2023, arXiv 2311.05237 | Kleines HRNet ohne Stem-Stride (hochaufgelöste Features), 3 Frames, Eingang 288x512, Heatmap pro Frame, Online-Tracker mit Bewegungsprädiktion als Gate | Tabelle unten, 5 Sportarten | 1.5 M Parameter; 15.8 bis 70 FPS je nach Datensatz und Step (4x V100 Testsystem) | Okklusion nur als Problem benannt, kein eigenes Modul; Basketball-Datensatz mit stark bewegter und zoomender Kamera, Ball oft in der Hand: dort am schwächsten (F1 80.6 bis 82.6) |
| TrackNetV3 | ACM MM Asia 2023 (Venue laut ACM-Link, Datum [nicht verifiziert]) | TrackNetV2-Tracker + Hintergrundschätzung + "InpaintNet", das Lücken in der Trajektorie rekonstruiert | Shuttlecock-Testsplit: Acc 97.51 %, P 97.79 %, R 99.33 %, F1 98.56 % (TrackNetV2 im selben Setup: Acc 94.98 %) | 25.1 FPS (Hardware nicht angegeben) | Okklusion explizit über Trajektorien-Inpainting; statische Kamera |
| TrackNetV4 | ICASSP 2025, arXiv 2409.14543 (09.2024) | Plug-in: Frame-Differenzbilder + lernbare "Motion Prompt"-Schicht, fusioniert mit visuellen Features | Tennis: F1 97.1 auf 97.5 (V2 +Motion); Shuttle: V2 F1 90.6 auf 91.4, V3 F1 97.5 auf 97.9 | Kaum Overhead (z. B. 163.3 auf 161.1 FPS) | Zielt auf Okklusion und geringe Sichtbarkeit; Frame-Differenz setzt (nahezu) statische Kamera voraus |
| TrackNetV5 (zwei verschiedene Arbeiten mit gleichem Namen) | NYCU 2025/26 bzw. arXiv 2512.02789 (12.2025) | R(2+1)D-Blöcke, Motion-Prompt bzw. Motion-Direction-Decoupling | Shuttle F1 98.47 (Lite: 98.06 bei 2.58 M Parametern) bzw. F1 0.9859 | Lite 2.58 M Parameter | **[nicht verifiziert, nur Abstracts gelesen]** |
| BlurBall | arXiv 2509.18387 (09.2025) | Auf WASB/HRNet aufgebaut + SE-Attention; Label in der Mitte der Bewegungsunschärfe, schätzt Blur mit | Tischtennis: F1 96.52 %, Acc 96.50 % | ähnlich WASB | Explizit Motion-Blur; Code-Lizenz **[nicht geprüft]** |
| TOTNet | arXiv 2508.09650 (08.2025) | 3D-Convs, sichtbarkeitsgewichteter Loss, Okklusions-Augmentation | RMSE 37.30 auf 7.19; Acc auf voll verdeckten Frames 0.63 auf 0.80 (Tennis, Badminton, Tischtennis) | **[nicht angegeben]** | Explizit Okklusion |

WASB-Benchmark (Tabelle 2 im Paper, Toleranz 4 px, Werte F1 / AP / FPS):

| Methode (Parameter) | Fussball | Tennis | Badminton | Volleyball | Basketball |
|---|---|---|---|---|---|
| TrackNetV2 (11.3 M) | 86.6 / 77.2 / 66 | 89.4 / 80.6 / 55 | 90.5 / 83.6 / 77 | 83.6 / 72.3 / 18 | 78.8 / 64.6 / 28 |
| MonoTrack (2.9 M) | 85.2 / 78.6 / 58 | 92.1 / 87.3 / 64 | 90.9 / 84.9 / 76 | 85.1 / 72.1 / 20 | 80.8 / 65.3 / 32 |
| WASB Step=3 (1.5 M) | 88.3 / 83.6 / 56 | 94.0 / 91.0 / 58 | 91.6 / 88.5 / 70 | 86.5 / 79.9 / 18 | 80.6 / 71.5 / 30 |
| WASB Step=1 (1.5 M) | 88.2 / 86.2 / 24 | 95.6 / 94.2 / 35 | 93.1 / 91.6 / 34 | 88.0 / 83.2 / 16 | 82.6 / 77.1 / 22 |

Wichtig für uns: Der Basketball-Datensatz (NBA, 1920x1080, bewegte und zoomende Broadcast-Kamera, mittlere Ballverschiebung 33.7 px/Frame, 275'328 annotierte Bilder) ist der Fall, der Handball am nächsten kommt. Dort liegen alle Verfahren bei F1 um 80, also deutlich unter den Racket-Sportarten.

### 1.2 Mannschaftssportarten

- **Fussball:** SoccerNet-Tracking (2022/2023) enthält Tracklets für Spieler, Schiedsrichter und Ball auf der Hauptkamera; Metrik HOTA, Klassen werden nicht unterschieden. Ballspezifische Detektoren: FootAndBall (VISAPP 2020, Code MIT), DeepBall (Baseline in WASB). SoccerNet-Challenges 2024/2025 (Ball Action Spotting, Game State Reconstruction) arbeiten mit Ball-Ereignissen bzw. Spielzustand, nicht mit Pixel-Ballpositionen als Hauptaufgabe.
  - https://github.com/SoccerNet/sn-tracking ; https://arxiv.org/abs/2508.19182 ; https://github.com/jac99/FootAndBall
- **Basketball:** DeepSportRadar (ACM MMSports 2022) Ball-3D-Lokalisierung: Schätzung des Balldurchmessers in Pixeln bei bekannter (Oracle-)Ballposition, Metrik MADE/MAE. BallSeg (arXiv 2007.11876) als Segmentierungs-Detektor, Baseline in WASB. Die DeepSport-Arbeiten (Van Zandycke et al.) nutzen ballistische Modelle für 3D-Trajektorien aus einer Kamera.
  - https://github.com/DeepSportradar/ball-3d-localization-challenge ; https://github.com/gabriel-vanzandycke/deepsport
- **Volleyball:** Ball-Annotationen zum Volleyball-Datensatz von Ibrahim et al. (CVPR 2016), verwendet in WASB.
- **Handball:** Keine öffentliche Arbeit mit grossem, ballannotiertem Videodatensatz gefunden. Bekannt:
  - Host, Pobar, Ivašić-Kos (J. Imaging 2023, doi 10.3390/jimaging9040080): YOLO/Mask R-CNN für Spieler und Ball, DeepSORT/BoT-SORT; Ball als schwierigste Klasse. https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10144022/
  - IntechOpen-Kapitel 2022 (Uni Rijeka): YOLOv3/Mask R-CNN + DeepSORT; PBD-Handball mit nur 394/27 Bildern. https://www.bib.irb.hr:8443/1120471/download/1120471.75342.pdf
  - Alwi et al. 2020: YOLOv2/v3, Faster R-CNN für Ball beim Wurf; 98.3 % sichtbar, 76.2 % bei Verdeckung. https://www.academia.edu/68664220/
  - Burić et al. 2019 (SCITEPRESS): vortrainiertes YOLO findet Personen gut, Ball problematisch. https://www.scitepress.org/Papers/2019/75820/pdf/index.html
  - Katsioulas & Maglogiannis 2026 (Preprint, nicht begutachtet): Broadcast-Handball, Detektion + MOT + Homographie. https://www.preprints.org/frontend/manuscript/7e8e582b9854f5c898aec073ba538eb8/download_pub

### 1.3 Wer behandelt was?

- **Okklusion:** TrackNetV3 (Inpainting der Trajektorie), TOTNet (sichtbarkeitsgewichteter Loss, Okklusions-Augmentation), TrackNetV4 (Bewegungskarten). WASB nur indirekt über Tracking-Gate.
- **Ball in der Hand:** Keine der Racket-Methoden. Am ehesten abgedeckt durch die Basketball-Daten in WASB (dort aber ohne eigenes Modul). In der Praxis wird "Ball in der Hand" über Ballbesitz-Fusion mit Spieler- und Pose-Tracking gelöst (siehe Abschnitt 4), nicht über den Balldetektor allein.
- **Kamerabewegung:** WASB wurde auf Basketball mit bewegter/zoomender Kamera evaluiert. TrackNetV4-Frame-Differenzen und MonoTrack-Physik setzen statische bzw. kalibrierte Kamera voraus; für Schwenks muss vorher global stabilisiert werden (z. B. Homographie/ECC zwischen Frames) **[eigene Einschätzung]**.

---

## 2. Lizenzen der Repos und Gewichte

Geprüft per LICENSE-Datei auf raw.githubusercontent.com bzw. HF-/Kaggle-API am 12.11.2026.

| Repo / Artefakt | Lizenz (LICENSE-Datei) | Gewichte | Bewertung für uns |
|---|---|---|---|
| nttcom/WASB-SBDT | MIT (LICENSE.md, "Copyright (c) 2023 NTT Communications Corporation") | Google-Drive-Links in MODEL_ZOO.md (WASB, TrackNetV2, MonoTrack, ResTrackNetV2, DeepBall, BallSeg je Sportart). Keine separate Lizenzangabe für Gewichte | Code ok. **Gewichte unklar:** MIT-Text spricht nur von "Software"; trainiert auf Datensätzen mit unklaren bzw. Forschungs-Bedingungen (NBA, Volleyball, TrackNet-Tennis/Badminton). Nur nach rechtlicher Prüfung nutzen |
| qaz812345/TrackNetV3 | MIT, deckt explizit "software, pretrained model checkpoints" ab | Google Drive, laut LICENSE MIT | Code und Gewichte ok. Trainingsdaten (Shuttlecock-Datensatz) Lizenz **[unklar]**; Domäne Badminton |
| TrackNetV4/TrackNetV4 | MIT (2025) | Datensatz nur unter "Research-Only Data Use Agreement" | Code ok, Datensatz nicht |
| AugustRushG/TOTNet | MIT (2024) | **[nicht geprüft]** | Code ok |
| yastrebksv/TrackNet (inoffizielle TrackNet-v1-Implementierung) | **Keine LICENSE-Datei** | Google Drive, ohne Bedingungen | Nicht nutzen (alle Rechte vorbehalten) |
| ChgygLin/TrackNetV2-pytorch | **Keine LICENSE-Datei** | aus TF-Gewichten des Originals konvertiert | Nicht nutzen |
| Offizielles TrackNet/TrackNetV2 (nol.cs.nctu.edu.tw, GitLab) | **[nicht erreichbar / nicht verifiziert]** | | Unklar |
| MonoTrack | Kein offizielles Code-Repo gefunden; Reimplementierung in WASB-SBDT (MIT) | Gewichte in WASB Model Zoo (siehe oben) | Architektur über WASB-Code nutzbar |
| BlurBall | **[nicht geprüft]** | | |
| jac99/FootAndBall | MIT ("Copyright (c) 2020 Sport Algorithmics and Gaming") | Gewichtslizenz nicht separat; trainiert auf ISSIA-CNR u. a. | Code ok |
| gabriel-vanzandycke/deepsport | **CC BY-NC-ND 4.0** | | Nicht kommerziell, ausgeschlossen |
| DeepSportradar/ball-3d-localization-challenge | **Keine LICENSE-Datei** (Abschnitt "License" leer) | | Unklar |
| DeepSportradar/instance-segmentation-challenge | Apache-2.0 (Copyright 2022 SportRadar) | | Code ok, Daten nicht (siehe 3) |
| google OWLv2 (google-research/scenic; HF google/owlv2-*) | Apache-2.0 (Repo-LICENSE und HF-Tag) | Apache-2.0 | ok |
| facebook/dinov2 | Apache-2.0 (Repo und HF-Tag) | Apache-2.0 | ok |
| facebook/dinov3 | Eigene "DINOv3 License" (19.08.2025) | | Nicht Apache/MIT/BSD, nach unseren Regeln ausgeschlossen |
| facebook/cotracker3 (HF) | CC BY-NC 4.0 | | Ausgeschlossen |
| facebook/sam2.1 (HF) | Apache-2.0 | | ok |
| timm/resnet18.a1_in1k, timm/hrnet_w18_small.ms_in1k (HF) | Apache-2.0 bzw. MIT (HF-Tag) | ImageNet-1k-trainiert | ok laut Tag; ImageNet-Nutzungsbedingungen der Bilder sind ein bekannter Graubereich **[rechtlich nicht geprüft]** |

---

## 3. Öffentliche Datensätze mit Ball-Annotationen

### 3.1 Handball

| Datensatz | Inhalt | Ball? | Lizenz | Kommerziell? |
|---|---|---|---|---|
| EIGD-H (mm4spa/eigd, 2021) | HBL 2019/20, 5 Spiele x 5 Sequenzen x 5 min, unbearbeiteter Broadcast 1280x720@30 fps, Kinexon-Positionsdaten (20 Hz, inkl. Ball laut Paper **[Ballposition nicht verifiziert]**), Ereignisannotationen | Indirekt (Positionsdaten, keine Pixel-Labels) | CC BY-NC-SA 4.0 | Nein |
| TeamTrack (AtomScott, CVPRW 2024) | Handball Seitenansicht Fisheye, 6K, 30 min, Nagoya University; auch Fussball/Basketball | Laut Paper/README nur Personen-Boxen, Ball nicht erwähnt | Kaggle: MIT; Code-Repo: MIT | Ja, aber kein Ball; nützlich für Spieler-Tracking in Hallen |
| UNIRI Handball Action Dataset (Kaggle-Reupload mexwell/handball-action-dataset) | 751 Clips, Training, GoPro statisch, Full HD | Nein (Aktionslabels) | Kaggle: CC BY 4.0 (Reupload, Herkunft/Rechte des Originals **[unklar]**) | Formal ja, Provenienz prüfen |
| PBD-Handball (Uni Rijeka) | 394 + 27 Bilder, Spieler und Ball | Ja | **[unklar]** | Unklar |
| Roboflow Universe (z. B. "handball-ball-detection", "Handball Detection" Victor Collado) | kleine Community-Sets, Boxen Ball/Spieler | Ja | je Projekt verschieden, oft CC BY 4.0 **[nicht einzeln verifiziert]**; Bildherkunft oft Broadcast-Screenshots | Riskant |
| "Play by play" (PubMed 39845149) | Positionsdaten Handball/Basketball | Nein (kein Video) | **[nicht geprüft]** | |

Fazit Handball: Kein öffentlicher, kommerziell nutzbarer Handball-Datensatz mit Ball-Pixel-Labels gefunden. Eigene Daten bleiben die Hauptquelle.

### 3.2 Andere (Hallen-)Ballsportarten

| Datensatz | Ball-Annotation | Lizenz | Kommerziell? |
|---|---|---|---|
| DeepSportRadar Basketball-Instants (Kaggle, 700+ Bilder, Ball 3D über 2 Keypoints) | Ja | CC BY-NC-SA 4.0 (Kaggle-API) | Nein |
| Ballistic-Raw-Sequences (Kaggle, Van Zandycke) | Ja (Sequenzen) | CC BY-NC-SA 4.0 (Kaggle-API) | Nein |
| NBA-Datensatz (Yan et al., SAM, ECCV 2020) mit WASB-Ball-Labels | Ja, 275k Bilder | Projektseite nicht erreichbar, Bedingungen **[nicht verifiziert]**; vermutlich Forschungszweck, Quelle sind NBA-Broadcasts | Wahrscheinlich nein |
| Volleyball (Ibrahim et al., SFU) + Ball-Annotationen | Ja | Repo deep-activity-rec: BSD-2-Clause (bezieht sich auf Code); Videos aus YouTube-Broadcasts, Datensatz-Bedingungen **[unklar]** | Unklar, eher nein |
| SportsMOT (MCG-NJU, ICCV 2023), Basketball/Volleyball/Fussball | Nur Spieler | CC BY-NC 4.0, Weitergabe nur mit schriftlicher Erlaubnis | Nein |
| SoccerNet-Tracking 2023 (HF, nicht gated) | Ja (Ball-Tracklets) | Keine Lizenz auf HF angegeben; Broadcast-Material, andere SoccerNet-Teile NDA-gated | **[unklar]**, eher nein |
| SoccerNet GSR 2025 (HF) | Spielzustand | HF-Tag GPL-3.0 | Nicht Apache/MIT/BSD |
| TrackNet Tennis (19'835 Frames, 1280x720) und Shuttlecock/TrackNetV2 (55'563 Frames) | Ja | **[unklar]** (Hosting NYCU) | Unklar |
| TrackNetV4 Multi-Ball-Datensatz | Ja | Research-Only Data Use Agreement | Nein |
| TTA (TOTNet, Tischtennis Paralympics, 9'159 Samples) | Ja | **[nicht angegeben]** | Unklar |

Fazit: Praktisch alle ballannotierten Sport-Datensätze sind nicht-kommerziell oder rechtlich unklar. Für ein kommerzielles Produkt sind sie höchstens für interne Forschung/Benchmarking denkbar (rechtlich abklären). Sicherer Weg: eigene Labels plus Pretraining auf generischen, permissiv lizenzierten Gewichten (ImageNet/COCO/OWLv2).

---

## 4. Best Practices Multi-Object-Tracking im Mannschaftssport

### 4.1 Typische Pipeline (Industrie und Forschung)

1. **Personen-Detektor** (COCO-vortrainiert, auf Sportdaten feinjustiert).
2. **Tracker** mit Bewegungsmodell (Kalman), Kamerabewegungs-Kompensation (GMC) und optional Re-ID-Features.
3. **Re-ID / Team-Zuordnung:** Appearance-Embeddings (OSNet, CLIP/SigLIP-artige Features) plus Clustering der Trikotfarben; Rückennummern-Erkennung zum Zusammenführen langer Tracks (SoccerNet Game State Reconstruction, arXiv 2404.11335).
4. **Ball-Detektor** separat (Heatmap, mehrere Frames), weil generische Detektoren kleine Bälle schlecht finden (vgl. Handball-Arbeiten oben).
5. **Ball-Tracking** mit physikalischem Filter: Kalman mit konstanter Geschwindigkeit/Beschleunigung im Bild, Gating von Kandidaten (WASB), Trajektorien-Ergänzung (TrackNetV3 Inpainting), bei kalibrierter Kamera ballistischer 3D-Fit (MonoTrack: Gravitation + Luftwiderstand, Fit über Reprojektionsfehler; DeepSport-Arbeiten).
6. **Ballbesitz-Fusion:** Ist der Ball nicht sichtbar oder nah an einem Spieler, wird er dem Spieler mit minimalem Abstand (Hand-Keypoints aus Pose, z. B. RTMPose) über mehrere Frames mit Hysterese zugeordnet; die Ballposition wird dann aus der Spielerposition/Hand geschätzt. Übergänge (Pass/Wurf) erzeugen neue ballistische Segmente. Diese Fusion ist üblich, aber selten als Paper dokumentiert **[Praxisbeschreibung, keine Benchmarkquelle]**. Beispiel-Code mit Ball- und Spielertracking: roboflow/sports (MIT).

### 4.2 Detektoren (permissiv)

| Detektor | Lizenz (geprüft) | Berichtet (COCO val) | Hinweis |
|---|---|---|---|
| RT-DETR / RT-DETRv2 (lyuwenyu/RT-DETR) | Apache-2.0; HF PekingU/rtdetr_* Apache-2.0 | R18: 46.5 AP, 217 FPS (T4); R18 mit Objects365-Pretraining 49.2 AP; RT-DETRv2-S 48.1 AP | Objects365-Variante: Lizenz der Objects365-Daten **[nicht geprüft]** |
| D-FINE (Peterande/D-FINE) | Apache-2.0; HF ustc-community/dfine-* Apache-2.0 | D-FINE-N 42.8 AP @ 472 FPS (T4) | Gute Wahl für kleine Objekte laut Autoren **[nicht verifiziert]** |
| RTMDet (open-mmlab/mmdetection) | Apache-2.0 | tiny 41.1 AP, 4.8 M Parameter; s 44.6 AP | Gewichte über download.openmmlab.com |
| RF-DETR (roboflow/rf-detr) | Apache-2.0 für Nano/Small/Medium/Large, Seg und Keypoint; Atto/Femto/Pico/XL/2XL unter PML 1.0 (kommerzielles Self-Hosting nur mit Enterprise) | siehe README | Nur `pip install rfdetr`, nicht `[plus]` |
| LW-DETR (Atten4Vis) | Apache-2.0 | | |
| YOLOX (Megvii) | Apache-2.0 | | Detektor in Deep-EIoU |
| DEIM (ShihuaHuang95/DEIM) | Apache-2.0 | | |
| **Nicht verwenden:** Ultralytics YOLOv8/11/26 (AGPL-3.0), YOLOv10 (AGPL-3.0), YOLOv9 (GPL-3.0), mmyolo (GPL-3.0), DEIMv2 (eigene Lizenz, nur nicht-kommerziell, Stand LICENSE.md 2026) | | | |

### 4.3 Tracker

| Tracker | Lizenz (geprüft) | Berichtet | Hinweis |
|---|---|---|---|
| ByteTrack (ifzhang bzw. FoundationVision) | MIT | | Assoziation auch niedrig-konfidenter Boxen, gut bei Okklusion |
| BoT-SORT (NirAharon) | MIT | MOT17 test: 80.5 MOTA, 80.2 IDF1, 65.0 HOTA | Kamerabewegungs-Kompensation (GMC) + Re-ID, wichtig für schwenkende Kameras |
| OC-SORT (noahcao) | MIT | DanceTrack test: 55.1 HOTA | Beobachtungszentriert, robust bei nichtlinearer Bewegung |
| Deep-OC-SORT (GerardMaggiolino) | MIT | | OC-SORT + Appearance |
| Deep-EIoU (hsiangwei0903) | **Keine LICENSE-Datei** | SportsMOT 77.2 HOTA, SoccerNet-Tracking 85.4 HOTA (arXiv 2306.13074) | Stärkster Sport-Tracker in der Liste, aber Code nicht lizenziert: Algorithmus (Expansion-IoU + Deep Features) selbst nachimplementieren |
| torchreid / deep-person-reid (KaiyangZhou), OSNet | MIT | | Re-ID-Backbone |
| fast-reid (JDAI-CV) | Apache-2.0 | | Re-ID |
| roboflow/supervision | MIT | | Enthält ByteTrack-Implementierung und Utilities |
| **Nicht verwenden:** boxmot (AGPL-3.0), SoccerNet sn-gamestate/tracklab (GPL-3.0) | | | |

---

## 5. Preise Labelling-Dienste (Punkt/Keypoint, kleines Objekt in Video)

| Anbieter | Öffentliche Preisangabe | Standort / Datenverarbeitung | Quelle |
|---|---|---|---|
| Label Your Data | Keypoints ab USD 0.015 pro Objekt; Boxen ab USD 0.02; Stundenabrechnung typischerweise USD 6 pro Annotator-Stunde; kostenloser Pilot | Büros in Wilmington (US) und Nikosia (Zypern, EU); Ort der Verarbeitung, GDPR/ISO auf Preisseite **nicht angegeben** | https://labelyourdata.com/pricing (abgerufen 12.11.2026) |
| AnnotationBox | USD 5 bis 7 pro Annotator-Stunde; Box USD 0.04 bis 0.07; Keypoints "etwas höher", ohne Zahl | Büros Indien, USA, UK; keine EU-Verarbeitung angegeben | https://annotationbox.com/pricing/ |
| CVAT.ai Annotation Services | Kein Stückpreis öffentlich; Projektbudget ab USD 5'000 bis 9'900 (nur Annotation), Mengenrabatt 5 bis 30 % | Badges "GDPR & CCPA compliant", "EU AI Act compliant"; Datenstandort nicht angegeben | https://cvat.ai/blog/outsourcing-data-annotation-cost (25.07.2024) |
| Humans in the Loop | Preise nur auf Anfrage | Sofia, Bulgarien (EU), eigene Angabe "GDPR-compliant"; Datenspeicherort nicht bestätigt | https://humansintheloop.org/the-crucial-role-of-gdpr-compliant-data-annotation-for-the-procurement-persona/ |
| Marktübersicht (basic.ai) | USD 3 bis 60 pro Stunde, Managed Teams meist USD 3 bis 12; Keypoints USD 0.01 bis 0.05 pro Punkt (DeeLab), USD 0.012 bis 0.020 (Tech AI); US-Workforce bis ca. USD 25 bis 29 pro Stunde (Quadrant, iMerit) | | https://www.basic.ai/blog-post/how-much-do-data-annotation-services-cost-complete-guide |
| Schweiz | Kein Schweizer Annotationsdienst mit öffentlicher Preisliste gefunden. Lightly (Zürich) bietet Kuratierung und inzwischen Labeling an, Preise/Hosting **[nicht verifiziert]** | | https://europeanpurpose.com/category/data-labeling-platforms |

Grobe Umrechnung für uns **[eigene Schätzung]**: Ein Ballklick pro Frame (plus Sichtbarkeits-Flag: sichtbar / verdeckt / in der Hand / ausserhalb) mit Interpolationshilfe schafft ein Annotator erfahrungsgemäss 150 bis 400 Frames pro Stunde. 10'000 Frames entsprechen damit ca. 25 bis 70 Stunden, also ca. USD 150 bis 450 bei USD 6/h (Offshore) bzw. USD 150 bis 500 bei USD 0.015 bis 0.05 pro Punkt. EU-Verarbeitung dürfte deutlich teurer sein; ein Marketing-Blog nennt +15 bis 25 % für GDPR/AI-Act (https://www.index.dev/blog/data-annotation-europe-market-trends, nicht unabhängig belegt).

Minderjährige im Video: Kein Anbieter mit öffentlicher Preisseite garantiert dort explizit EU- oder CH-Verarbeitung. Vor Vergabe zwingend: AVV/DPA, Speicher- und Zugriffsort (EU/CH), Unterauftragnehmer, Löschfristen; Alternative ist Annotation auf eigener Instanz (z. B. selbst gehostetes CVAT in CH/EU) mit Fremd-Annotatoren nur per Remote-Zugriff. Die Schweiz hat einen EU-Angemessenheitsbeschluss, d. h. EU-Verarbeitung ist aus CH-Sicht grundsätzlich zulässig (revDSG; Details rechtlich prüfen).

---

## 6. Empfehlung

### 6.1 Architektur für Ball-Modell v2

**WASB-artiges HRNet-Heatmap-Netz mit hochaufgelöster Ausgabe, 3 bis 5 Frames, plus kamerakompensiertem Bewegungskanal und physikbasiertem Tracker mit Ballbesitz-Zustand.** Konkret:

1. **Backbone/Head:** WASB-Architektur (MIT-Code, 1.5 M Parameter) oder HRNet-W18-small (timm, MIT) mit Ausgabe in Stride 1 oder 2 statt Stride 4. Begründung: Bei 8 bis 20 px Ball und 12 px Toleranz kostet Stride 4 (mit 288x512-artiger Eingabe effektiv noch gröber) zu viel Lokalisierungsgenauigkeit; WASB entfernt genau deshalb den Stem-Stride. Eingabe-Auflösung eher 720p-Crops/Tiles als 512 px Breite, da der Ball sonst unter ca. 4 px fällt.
2. **Bewegung:** TrackNetV4-artiger Motion-Kanal (Frame-Differenzen, MIT), aber erst nach globaler Bildregistrierung (Homographie/ECC aus Hallenboden-Features), sonst dominieren Schwenks und Zooms.
3. **Labels und Loss:** Gauss-Heatmap, Ballmittelpunkt in der Mitte der Unschärfe (BlurBall-Konvention); zusätzlicher Sichtbarkeits-Kopf (sichtbar / verdeckt / in der Hand), sichtbarkeitsgewichteter Loss und Okklusions-Augmentation (TOTNet-Idee).
4. **Tracking-Stufe:** Kandidaten Top-k pro Frame; Kalman bzw. Ballistik-Fit pro Flugsegment; Zustandsmaschine "Flug / in der Hand (Spieler-ID) / Boden / unbekannt", gespeist von Spieler-Tracks (D-FINE oder RT-DETR + BoT-SORT/ByteTrack, Re-ID mit OSNet) und Hand-Keypoints. Damit werden "Ball in der Hand"-Frames nicht vom Detektor erzwungen, sondern aus dem Besitz abgeleitet.
5. **Teacher:** OWLv2 (Apache-2.0) bleibt Teacher für Pseudo-Labels; Top-5-Kandidaten von OWLv2 mit dem Tracker zeitlich konsistent filtern, bevor sie als Trainingslabels dienen. OWLv2-Score als zusätzlicher Kanal/Ensemble ist eine günstige Zwischenstufe.

Alternativ als Vergleich: ein permissiver Detektor (D-FINE-N oder RT-DETRv2-S, Apache-2.0) auf hochaufgelösten Tiles für die Klasse Ball. Erwartung: schlechter bei Blur und 8 px Bällen als Mehrframe-Heatmaps (vgl. YOLOv7 mit F1 68 vs. TrackNet ca. 91 auf Shuttlecock), aber schnell aufsetzbar.

### 6.2 Legal nutzbare Startgewichte

Sicher im Sinne der Kriterien (Apache/MIT/BSD laut LICENSE bzw. HF-Tag):
- **timm HRNet-W18-small (MIT)** bzw. **timm ResNet18 (Apache-2.0)**, ImageNet-1k. Hinweis: ImageNet-Bildrechte sind ein allgemeiner Graubereich, in der Industrie aber Standard **[rechtlich nicht geprüft]**.
- **DINOv2 (Apache-2.0)** als stärkerer Feature-Extraktor/Teacher, falls ein ViT-Backbone gewünscht.
- **OWLv2 (Apache-2.0)** als Teacher bzw. für Distillation.
- **D-FINE, RT-DETR/RT-DETRv2, RTMDet, RF-DETR N/S/M/L (Apache-2.0)**, COCO (enthält Klasse "sports ball").
- **TrackNetV3-Checkpoints (MIT, explizit inkl. Checkpoints):** legal, aber Badminton mit statischer Kamera, Transfernutzen gering **[eigene Einschätzung]**.

Unklar, nur nach rechtlicher Prüfung:
- **WASB-Gewichte** (Repo MIT, aber Gewichte nicht ausdrücklich lizenziert und auf Forschungsdaten trainiert). Besonders interessant wären die Basketball- und Volleyball-Gewichte als Initialisierung; ohne Freigabe nur für interne Experimente.

Ausgeschlossen: DINOv3, CoTracker3, DEIMv2, alle Ultralytics/YOLOv8-11/YOLOv10/YOLOv9, mmyolo, boxmot, deepsport (CC BY-NC-ND), Gewichte trainiert auf SportsMOT/DeepSportRadar/EIGD-H.

### 6.3 Benötigte Label-Menge (Schätzung)

Referenzgrössen aus der Literatur: TrackNet Tennis 19'835 Frames, TrackNetV2 Badminton 55'563 Frames (18 Videos), WASB-Basketball 275'328 Bilder; Fussball in WASB nur 4 Trainingsclips. Diese Modelle wurden alle auf wenigen, homogenen Umgebungen trainiert und generalisieren schlecht auf neue Szenen (TrackNet v1: F1 98.5 % auf bekanntem Spiel, 84.3 % in Kreuzvalidierung auf neuen Videos).

**[Eigene Schätzung, nicht belegt]** für unseren Fall (viele Hallen, schwenkende Kameras):
- **Minimum für einen klaren Sprung über OWLv2 (Ziel > 60 % Top-1 @12 px auf unbekannten Hallen):** ca. 3'000 bis 5'000 verifizierte Frames, verteilt auf mindestens 30 bis 50 Hallen (ca. 100 Frames pro Spiel, als kurze zusammenhängende Clips von 5 bis 10 Frames, damit der Mehrframe-Input sinnvoll ist), plus die gefilterten OWLv2-Pseudo-Labels aus 200 Spielen und die bestehenden Hand-Klick-Pfade.
- **Für robuste Produktion:** ca. 10'000 bis 20'000 verifizierte Frames aus 80+ Hallen, inkl. gezielt schwerer Fälle (Ball in der Hand, Verdeckung, Blur, Zoom). Mehr Vielfalt an Hallen ist wichtiger als mehr Frames pro Halle.
- **Validierung:** feste Testmenge von mindestens 1'000 Frames aus 10+ Hallen, die nie im Training vorkommen.
- Die vorhandenen 300 verifizierten Bälle reichen nur als Testset bzw. für Kalibrierung, nicht als Trainingsbasis.

Kosten dafür (aus Abschnitt 5): 5'000 bis 20'000 Frames entsprechen ca. 15 bis 130 Annotator-Stunden, offshore grob USD 100 bis 1'000; mit EU/CH-Verarbeitung und Qualitätskontrolle eher ein Mehrfaches **[Schätzung]**.

---

## Quellen (Auswahl, abgerufen 12.11.2026)

- TrackNet: https://arxiv.org/abs/1907.03698
- TrackNetV2 (ICPAI 2020), Zahlen via TrackNetV4-Paper: https://arxiv.org/html/2409.14543
- TrackNetV3: https://github.com/qaz812345/TrackNetV3 (LICENSE: https://raw.githubusercontent.com/qaz812345/TrackNetV3/master/LICENSE)
- TrackNetV4: https://arxiv.org/abs/2409.14543 ; https://tracknetv4.github.io ; https://github.com/TrackNetV4/TrackNetV4
- TrackNetV5: https://people.cs.nycu.edu.tw/~yushuen/data/TracknetV5_26.pdf ; https://arxiv.org/abs/2512.02789
- MonoTrack: https://arxiv.org/abs/2204.01899 (HTML-Version für Details)
- WASB: https://arxiv.org/abs/2311.05237 ; https://github.com/nttcom/WASB-SBDT (LICENSE.md, MODEL_ZOO.md, GET_STARTED.md)
- BlurBall: https://arxiv.org/abs/2509.18387
- TOTNet: https://arxiv.org/abs/2508.09650 ; https://github.com/AugustRushG/TOTNet
- SoccerNet: https://github.com/SoccerNet/sn-tracking ; https://www.soccer-net.org/data ; https://huggingface.co/datasets/SoccerNet/SN-Tracking-2023 ; https://arxiv.org/abs/2508.19182
- DeepSportRadar: https://github.com/DeepSportradar/ball-3d-localization-challenge ; https://www.kaggle.com/datasets/deepsportradar/basketball-instants-dataset
- EIGD: https://github.com/mm4spa/eigd ; https://arxiv.org/abs/2108.11149
- TeamTrack: https://arxiv.org/abs/2404.13868 ; https://github.com/AtomScott/TeamTrack ; https://www.kaggle.com/datasets/atomscott/teamtrack
- SportsMOT: https://github.com/MCG-NJU/SportsMOT ; https://huggingface.co/datasets/MCG-NJU/SportsMOT
- Volleyball: https://github.com/mostafa-saad/deep-activity-rec
- Deep-EIoU: https://arxiv.org/abs/2306.13074 ; https://github.com/hsiangwei0903/Deep-EIoU
- ByteTrack https://github.com/ifzhang/ByteTrack ; BoT-SORT https://github.com/NirAharon/BoT-SORT ; OC-SORT https://github.com/noahcao/OC_SORT ; Deep-OC-SORT https://github.com/GerardMaggiolino/Deep-OC-SORT
- RT-DETR https://github.com/lyuwenyu/RT-DETR ; D-FINE https://github.com/Peterande/D-FINE ; RTMDet https://github.com/open-mmlab/mmdetection/tree/main/configs/rtmdet ; RF-DETR https://github.com/roboflow/rf-detr ; DEIMv2 https://github.com/Intellindust-AI-Lab/DEIMv2
- Ultralytics (AGPL) https://github.com/ultralytics/ultralytics ; boxmot (AGPL) https://github.com/mikel-brostrom/boxmot
- roboflow/sports https://github.com/roboflow/sports ; supervision https://github.com/roboflow/supervision
- OWLv2 https://huggingface.co/google/owlv2-base-patch16-ensemble ; DINOv2 https://github.com/facebookresearch/dinov2 ; DINOv3 https://github.com/facebookresearch/dinov3
- Labelling: https://labelyourdata.com/pricing ; https://annotationbox.com/pricing/ ; https://cvat.ai/blog/outsourcing-data-annotation-cost ; https://www.basic.ai/blog-post/how-much-do-data-annotation-services-cost-complete-guide ; https://humansintheloop.org/

## Offene Punkte / nicht verifiziert

- Lizenz der WASB-Gewichte und der zugrundeliegenden Datensätze (NBA/SAM, Volleyball, TrackNet-Tennis/Badminton).
- Offizielle TrackNet/TrackNetV2-Repos (NYCU-GitLab) nicht erreichbar.
- Lizenz BlurBall-Code, TOTNet-Gewichte und TTA-Datensatz.
- Ob EIGD-H die Ballposition in den Kinexon-Daten enthält.
- Objects365-Lizenz (relevant für Objects365-vortrainierte RT-DETR/D-FINE-Varianten); COCO-only-Varianten bevorzugen.
- Konkrete EU/CH-Verarbeitungszusagen der Labelling-Anbieter (nur über Angebot/DPA klärbar).
- Alle Label-Mengen- und Kostenschätzungen in 6.3 sind eigene Schätzungen.
