# GPU-Aufträge (Modal, lokale Sitzung)

Ablauf und Regeln: `docs/plans/gpu-jobs-local.md`. Die Cloud-Sitzung schreibt neue Aufträge unter
"Offen", die lokale Sitzung führt sie aus und verschiebt sie nach "Erledigt" (mit Dataset-Name,
Dauer, Kosten, Auffälligkeiten). Vor dem Commit `git pull --rebase`, danach pushen.

## Offen

### 13. Laufzeit und Kosten der Produkt-Analyse auf einer T4, 2026-11-17 (Integrations-Sitzung)
- Wozu: Entscheid GPU-Verarbeitung (Plan `docs/plans/produkt-analyse-integration.md` Schritte 3 und
  4). Die CPU-Kette braucht 4.4 x Videolänge (Plan Abschnitt 4); gesucht sind die Zeiten pro Stufe
  auf einer T4 mit und ohne Ballnetze und daraus die Kosten pro 60-Minuten-Spiel.
- Was läuft: `ml/integration/profile_variants.py` (der echte `run_analysis` mit lokalen Attrappen
  für S3 und API) auf 5 Minuten von AT_Cup_Feldkirch_Bregenz_2021 (`handball-segs-l10`), fünf
  Einstellungen nacheinander (cuda_image, cuda_ball_ens, cuda_ball_hrp1, cuda_ball_ens_lean,
  cpu_image) plus Kurzmessung der Ballnetze (fp32/fp16, Stapel 1/4/8). Die Ballnetze werden im
  Container aus `handball-ball-hrmodels` nach ONNX exportiert. Testphase: hr1/hrp1 enthalten
  DeepSport, hier wird nur gemessen.
- Befehl: `modal run --detach ml/gpu/profile_gpu.py --minutes 5 --tag game1`
- Fortsetzbar: jede fertige Einstellung liegt auf dem Volume `handball-gpu-out`
  (`handball-gpu-profile-game1/`); derselbe Befehl setzt fort. `--budget-min 90` hält vor einer
  weiteren Einstellung an, wenn 90 Minuten verbraucht sind.
- Erwartet: etwa 1 h auf einer T4, rund 0.70 USD (Obergrenze mit Budget: 1.5 h, etwa 1 USD).
- Ergebnis: Kaggle-Dataset `handball-gpu-profile-game1` (summary.json, je Einstellung ein JSON,
  bench_nets.json). Die Integrations-Sitzung holt es ab und trägt die Zahlen in den Plan ein.
- Bei "budget"/"spend limit" abbrechen und melden.
- **Stand lokale Sitzung 2026-11-17 mittags, läuft:** `handball-gpu-profile-game1` auf Kaggle
  **nicht verwenden**, das sind CPU-Zahlen. ONNX Runtime fand im debian_slim-Image
  `libcublasLt.so.12` nicht und rechnete still auf der CPU (`bench_nets.json`:
  `CPUExecutionProvider`); nur cuda_image und cuda_ball_ens wurden fertig, dann griff das Budget.
  Korrigiert in `profile_gpu.py` (Image wie `Dockerfile.cuda`, Abbruch wenn nicht auf der GPU).
  Neuer Lauf unter dem Namen `handball-gpu-profile-game1-gpu` (Volume und Kaggle), die
  Kurzmessung zeigt jetzt `CUDAExecutionProvider`. Ergebnis folgt unter "Erledigt".


Gemeinsam für 3 bis 10: OWLv2 wie Auftrag 2, Rechnung mit den gemessenen ~210 s pro Segment auf
einer T4 (inkl. Download) und 0.66 USD/h (7.23 USD für 11.0 h). `--budget-h 10` lässt Luft bis 11 h
für den Upload. Jeder Auftrag ist für sich, sie dürfen parallel laufen (Modal-Ausgabenlimit für
alle zusammen: etwa 33 USD). Vorher `git pull` (Auftrag 3 braucht `--resume-from`). Bei
"budget"/"spend limit" abbrechen und melden.

### 3. OWLv2 Rest von l01 bis l03 (111 Segmente: 11 aus l02, 100 aus l03)
- Befehl: `modal run --detach ml/gpu/owl_pseudo.py --datasets handball-segs-l02,handball-segs-l03 --resume-from handball-gpu-owl-20261105-1449 --gpu T4 --budget-h 8`
- `--resume-from` übernimmt die 189 fertigen Segmente (zuerst vom Modal-Volume, sonst aus dem
  Kaggle-Dataset); das neue Dataset enthält dann alle 300 zusammen.
- Dauer etwa 6.5 h, Kosten etwa 4.3 USD.

### 11. Ball-Testset 2 in Originalauflösung (lokale Sitzung, kein GPU nötig), 2026-11-12
- Frage von Lukas: Verlieren wir Bälle, weil wir zu stark verkleinern? Ingest skaliert jedes Segment
  auf 1280 breit (crf 25), das Produkt erkennt auf 640×640. Viele Originale sind 1920×1080 oder mehr.
- Auftrag: Für die 252 Bilder von Testset 2 (`ml/ball/testset_pick.py`, Liste `items.json` der
  Hauptsitzung, Felder game, video, frame, gap) die drei Bilder (frame-gap, frame, frame+gap) aus dem
  **Originalvideo** schneiden (Zeit = Segmentstart + frame/fps, Segmentstart aus `library.json`),
  als PNG ohne neue Kompression. Dazu Breite, Höhe und fps des Originals pro Spiel notieren.
- Ablage: Kaggle-Dataset `lukasde1000/handball-ball-testset2-native` (privat), Inhalt
  `t/<id>_<0|1|2>.png` und `native.json` [{id, w, h, fps, t_s}]. Nur echte Testset-Spiele, nichts
  anderes hochladen; die Spiele bleiben aus jedem Training (`ml/ball/test_games.json`).
- Auswertung macht die Hauptsitzung (CPU): r7 auf 640 / 1280 / nativ, gleiche Labels skaliert.
- Aufwand: ein paar Minuten CPU plus Upload von ~1 GB. Fehlt ein Original, Spiel in `native.json`
  mit `"missing": true` aufführen statt raten.

## Stand 2026-11-09 nachts (Hauptsitzung)
Ball-Testset 2 (177 Bälle, 42 neue Hallen, `ml/ball/README.md`) zeigt: Runde 6 mit den OWL-Labels
ist in neuen Hallen klar besser als Runde 3 (29 % gegen 15 %). Die OWL-Labels helfen also; die
Aufträge 4 bis 10 laufen darum jetzt, aber **auf Kaggle aus der Hauptsitzung** (Gratis-Kontingent),
nicht auf Modal: Kernels `handball-owl-r7-1` und `-2`, 144 Segmente aus l04 bis l13 (zwei pro Spiel,
ohne die Testspiele aus `ml/ball/test_games.json` und deren Hallen). **Die lokale Sitzung führt 4
bis 10 nicht aus.** Auftrag 3 (l02/l03 auf Modal) bleibt bei der lokalen Sitzung, falls er schon
läuft oder Azure Pause hat; sonst hat Azure Vorrang.
Regel für alle Ball-Trainings: die Spiele aus `ml/ball/test_games.json` und Spiele derselben
Heimhalle nie verwenden.

## Zurückgestellt (erst nach der Auswertung von Ball-Runde 6, 2026-11-09 abends)
GPU-Budget ist knapp (Modal-Gratisguthaben 30 USD pro Monat). Die Aufträge 4 bis 10 zusammen kosten
etwa 28 USD. Sie laufen erst, wenn Runde 6 zeigt, dass die OWL-Labels das Ballnetz verbessern, und
dann zuerst auf Kaggle (Gratis-Kontingent) statt Modal, soweit Kaggle-Stunden übrig sind. Die
Cloud-Sitzung verschiebt sie dann wieder nach "Offen". Bis dahin: nur Auftrag 3 ausführen.

### 4. OWLv2 l04 (100 Segmente)
- Befehl: `modal run --detach ml/gpu/owl_pseudo.py --datasets handball-segs-l04 --gpu T4 --budget-h 10`
- Dauer etwa 5.8 h, Kosten etwa 3.9 USD.

### 5. OWLv2 l05 (100 Segmente)
- Befehl: `modal run --detach ml/gpu/owl_pseudo.py --datasets handball-segs-l05 --gpu T4 --budget-h 10`
- Dauer etwa 5.8 h, Kosten etwa 3.9 USD.

### 6. OWLv2 l06 (100 Segmente)
- Befehl: `modal run --detach ml/gpu/owl_pseudo.py --datasets handball-segs-l06 --gpu T4 --budget-h 10`
- Dauer etwa 5.8 h, Kosten etwa 3.9 USD.

### 7. OWLv2 l07 (100 Segmente)
- Befehl: `modal run --detach ml/gpu/owl_pseudo.py --datasets handball-segs-l07 --gpu T4 --budget-h 10`
- Dauer etwa 5.8 h, Kosten etwa 3.9 USD.

### 8. OWLv2 l08 (100 Segmente)
- Befehl: `modal run --detach ml/gpu/owl_pseudo.py --datasets handball-segs-l08 --gpu T4 --budget-h 10`
- Dauer etwa 5.8 h, Kosten etwa 3.9 USD.

### 9. OWLv2 l09 (100 Segmente)
- Befehl: `modal run --detach ml/gpu/owl_pseudo.py --datasets handball-segs-l09 --gpu T4 --budget-h 10`
- Dauer etwa 5.8 h, Kosten etwa 3.9 USD.

### 10. OWLv2 l10 und l11 (130 Segmente)
- Befehl: `modal run --detach ml/gpu/owl_pseudo.py --datasets handball-segs-l10,handball-segs-l11 --gpu T4 --budget-h 10`
- Dauer etwa 7.6 h, Kosten etwa 5.0 USD.

Summe 3 bis 10: 841 Segmente, etwa 49 GPU-Stunden, etwa 32 USD. Falls ein Auftrag an die
10-h-Grenze stösst: unter "Erledigt" die fehlenden Segmente nennen, der Rest folgt wie bei
Auftrag 3 (mit `--resume-from <Dataset des Teillaufs>`).

## Erledigt

### 12. Vorlabels für den Wurf-Goldstandard (61 Wurf-Clips), erledigt 2026-11-17
- Ergebnis: `lukasde1000/handball-gpu-prelabel-shots` (Status ready, hochgeladen 2026-11-17 02:16
  UTC): `clips/w00.mp4` bis `w60.mp4`, `hrp1/pre.json` und `hr1/pre.json` (je 61 Clips, dazu die
  13 `part_NN.json`). OWLv2 auf jedem 4. Bild steckt in `hrp1/pre.json` (`owl_every` 4), `hr1`
  hat kein OWL. Auch auf dem Modal-Volume `handball-gpu-out` unter `handball-gpu-prelabel-shots/`.
- Kosten laut `modal billing report`: 8.76 USD gesamt. Davon 4.27 USD für den ersten Lauf (alte
  Fassung, zweimal preempted, jedes Mal von vorne, gestoppt ohne Ergebnis), 1.14 USD für vier
  kurze Läufe der neuen Fassung (siehe unten), 3.35 USD für den Lauf, der fertig wurde (2026-11-16
  22:24 bis 2026-11-17 02:17, etwa 3.9 h auf einer T4, Pakete 2 bis 12 von hrp1 und alle von hr1).
- Auffälligkeiten:
  - Erster Lauf: etwa 0.79 s pro Bild mit OWL auf jedem 2. Bild, statt der geplanten etwa 0.28 s.
  - **`modal run --detach` reicht auf diesem PC nicht.** Der Firmen-Proxy kappt die Verbindung zu
    Modal etwa alle 20 bis 25 Minuten (WinError 10013/10054). Stürzt der lokale Client dabei ab,
    bricht Modal den laufenden Aufruf ab ("Received a cancellation signal"), trotz `--detach`.
    Bei Paketen von etwa 20 Minuten kam der Lauf so in vier Anläufen nur durch 2 Pakete.
  - Lösung, die funktioniert hat: `modal deploy ml/gpu/prelabel_clips.py`, dann
    `modal.Function.from_name("handball-prelabel", "run_t4").spawn(<clips_json>, "hrp1:ballhrp,hr1:ballhr", "handball-gpu-prelabel-shots", 4, 5)`.
    Der Aufruf läuft dann ohne lokale Verbindung weiter. Danach `modal app stop handball-prelabel`.
    Für lange Jobs von diesem PC aus künftig so starten.
- Die Labels selbst sind nicht geprüft, nur Vollständigkeit und Upload. Auswertung: Cloud-Sitzung.

### 2. OWLv2-Pseudo-Labels für l01 bis l03 — Teilergebnis, gestoppt durch 11-h-Grenze, 2026-11-06
- Ergebnis: `lukasde1000/handball-gpu-owl-20261105-1449` (Status ready, 189 `segs/*.json` plus
  `bench_owl.json`). Auch auf dem Modal-Volume `handball-gpu-out`.
- Abdeckung: 189 von 300 Segmenten. l01 100/100, l02 89/100, l03 0/100. Offen: 11 aus l02, alle
  aus l03. Für den Rest gibt es jetzt `--resume-from` (2026-11-09): übernimmt die 189 fertigen
  Segmente, rechnet nur die 111 offenen, das neue Dataset enthält dann alle 300. Vorschlag:
  `modal run --detach ml/gpu/owl_pseudo.py --datasets handball-segs-l02,handball-segs-l03 --resume-from handball-gpu-owl-20261105-1449 --gpu T4 --budget-h 8`
  (etwa 6.5 h, gut 4 USD). Lokal getestet ist nur die Übernahme-Logik, nicht ein Lauf auf Modal.
- Dauer: 39609 s (11.0 h) auf einer T4, Lauf ohne `--bench`.
- Kosten laut Modal: 7.23 USD (Stand 2026-11-06 früh, kann noch nachlaufen), statt ~6 USD geplant.
- Auffälligkeiten: ~210 s pro Segment statt der angenommenen ~120 s (30 Bursts pro Segment), für
  Planungen also 210 s rechnen. Kaggle zeigt die Dateien einzeln unter `segs/`, nicht als `result.zip`.
- Die Labels selbst sind nicht geprüft, nur Anzahl und Upload. Auswertung: Cloud-Sitzung.

### 1. Einrichtung prüfen (einmalig) — erledigt 2026-11-05
- Ergebnis: `cuda: True`, Tesla T4, `handball-ball-models/ball_best.pt` geladen. Kein Upload.
- Kosten: wenige Rappen (mehrere Anläufe, siehe unten).
- Auffälligkeiten, behoben in `ml/gpu/common.py`:
  - Kaggle-Zugang ist ein neuer Token (`~/.kaggle/access_token`, KGAT_…), keine kaggle.json.
    Das Modal-Secret `kaggle` enthält darum `KAGGLE_USERNAME` und `KAGGLE_API_TOKEN` (kein
    `KAGGLE_KEY`). Image jetzt `kaggle==2.2.5`, `kagglesdk==0.1.38`, plus `six` (fehlte).
  - `REPO = parents[2]` brach im Container ab (dort liegt common.py in /root).
  - `handball-ball-models` hat bei Kaggle kein Gesamt-Archiv (Grösse 0): der Download als Ganzes
    gibt 404. `kaggle_download` lädt dann Datei für Datei.
  - `owl_pseudo.py` schreibt die Ergebnisse zusätzlich auf das Modal-Volume `handball-gpu-out`
    (geht bei einem gescheiterten Upload nicht verloren) und wird mit `modal run --detach` gestartet.

