# GPU-Aufträge (Modal, lokale Sitzung)

Ablauf und Regeln: `docs/plans/gpu-jobs-local.md`. Die Cloud-Sitzung schreibt neue Aufträge unter
"Offen", die lokale Sitzung führt sie aus und verschiebt sie nach "Erledigt" (mit Dataset-Name,
Dauer, Kosten, Auffälligkeiten). Vor dem Commit `git pull --rebase`, danach pushen.

## Offen

### 15. Ballnetz im eigenen Thread mit uint8 im ganzen Job (T4), 2026-11-17 (Integrations-Sitzung), erst nach Freigabe von Lukas
- Wozu: Auftrag 14 hat das Ballnetz allein mit uint8-Eingabe bei 62 ms pro Bild gemessen (1280 px;
  960 px: 42 ms). Im Job kostete es 122 ms pro Bild, weil es nacheinander mit Kamera, YOLOX und
  Nummern lief. Seit PR #67 läuft das Netz in einem eigenen Thread. Im besten Fall dauert der Job
  dann max(Netz, Rest) statt der Summe: bei 1280 px auf jedem Bild etwa 1.55 x Videolänge und
  1.02 USD pro Spiel. Das ist zu messen (Plan, Abschnitt GPU-Profil).
- Was läuft: `ml/integration/profile_variants.py` (der echte `run_analysis`) auf 2 Minuten des
  Spiels aus den Aufträgen 13 und 14, YOLOX jedes 3. Bild, Nummern-Budget 0.3, in dieser
  Reihenfolge:
  - `lean_u8_1280_e1`, `lean_u8_960_e1`, `lean_u8_1280_e2`, `lean_u8_960_e2`: hrp1 uint8 bei
    1280 und 960 px, jedes bzw. jedes 2. Bild;
  - `cuda_lean`: ohne Netz, also der Rest;
  - `lean_ens_u8_1280_e1`: hr1 + hrp1, nur wenn die Zeit reicht.

  Testphase: hr1/hrp1 enthalten DeepSport, hier wird nur gemessen.
- Befehl (wie Auftrag 14): `modal deploy ml/gpu/profile_lean_gpu.py`, dann
  `modal.Function.from_name("handball-profile-lean", "run_t4").spawn(2, "handball-gpu-lean-u8", 25, "lean_u8_1280_e1,lean_u8_960_e1,lean_u8_1280_e2,lean_u8_960_e2,cuda_lean,lean_ens_u8_1280_e1")`.
- Fortsetzbar: Fertige Varianten liegen auf dem Volume `handball-gpu-out`
  (`handball-gpu-lean-u8/`), derselbe Aufruf setzt fort. Den Proxy schneidet der Job aus dem von
  Auftrag 14 auf dem Volume. Nach 25 Minuten startet keine neue Variante mehr. Eine laufende
  Variante wird 2.5 Minuten vor dem harten Modal-Ende (30 min) gestoppt, damit der Upload sicher
  kommt.
- Erwartet: etwa 22 Minuten auf einer T4, rund 0.25 USD (höchstens 30 Minuten, 0.33 USD).
- Ergebnis: Kaggle-Dataset `handball-gpu-lean-u8` (summary.json, je Variante ein JSON mit
  `observe_counters.ball_net_busy_ms`). Die Integrations-Sitzung holt es ab.
- Wichtig: In der ersten Logzeile muss `session ['CUDAExecutionProvider', ...]` stehen, sonst bricht
  das Skript ab. Bei "budget"/"spend limit" abbrechen und melden.

### 14. Ballnetz billiger auf der T4 (Kurzmessung), 2026-11-17 (Integrations-Sitzung), erst nach Freigabe von Lukas
- Wozu: Auftrag 13 hat das Ballnetz hrp1 auf der T4 mit 80 bis 120 ms pro Bild gemessen, dazu 21 ms
  CPU-Vorbereitung; Stapeln brachte nichts. Mit hrp1 auf jedem Bild kostet ein 60-Minuten-Spiel
  etwa 3 USD. Gesucht ist der billigere Weg (Plan `docs/plans/produkt-analyse-integration.md`,
  Abschnitt GPU-Profil T4).
- Was läuft: (1) `ml/integration/bench_ballnet.py`: hrp1 allein auf 120 echten Dreiergruppen, bei
  1280 und 960 px: wie im Produkt, uint8-Eingabe mit Vorbereitung im Graphen
  (`ml/ball/onnx_u8.py`), dasselbe mit IO-Binding, TensorRT fp16 (uint8- und float-Eingabe).
  (2) `ml/integration/profile_variants.py`: der ganze Produkt-Job auf 3 Minuten des Spiels aus
  Auftrag 13 mit YOLOX auf jedem 3. Bild und Nummern-Budget 0.3, ohne Ballnetz (`cuda_lean`) und
  mit hrp1 auf jedem Bild (`cuda_lean_hrp1`). Testphase: hrp1 enthält DeepSport, hier wird nur
  gemessen.
- Befehl (wie Auftrag 12 auf diesem PC): `modal deploy ml/gpu/bench_ballnet_gpu.py`, dann
  `modal.Function.from_name("handball-bench-ballnet", "run_t4").spawn(3, "handball-gpu-bench-ballnet", 25, "cuda_lean,cuda_lean_hrp1")`.
  Alternativ `modal run --detach ml/gpu/bench_ballnet_gpu.py`.
- Fortsetzbar: jede fertige Variante liegt auf dem Volume `handball-gpu-out`
  (`handball-gpu-bench-ballnet/`, auch der TensorRT-Cache); derselbe Aufruf setzt fort. Stopp:
  nach 25 Minuten startet keine neue Variante mehr, nach 30 Minuten beendet Modal die Funktion
  sicher.
- Erwartet: etwa 25 Minuten auf einer T4, rund 0.30 USD (höchstens 30 Minuten, 0.35 USD).
- Ergebnis: Kaggle-Dataset `handball-gpu-bench-ballnet` (bench.json, bench_summary.json,
  cuda_lean.json, cuda_lean_hrp1.json, summary.json). Die Integrations-Sitzung holt es ab.
- Wichtig: In der ersten Logzeile muss `session ['CUDAExecutionProvider', ...]` stehen, sonst bricht
  das Skript selbst ab. Fehlt `TensorrtExecutionProvider` unter "available", laufen die übrigen
  Varianten trotzdem; bitte melden. Bei "budget"/"spend limit" abbrechen und melden.

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


Gemeinsam für 3 bis 10: OWLv2 wie Auftrag 2, Rechnung mit den gemessenen ~210 s pro Segment auf
einer T4 (inkl. Download) und 0.66 USD/h (7.23 USD für 11.0 h). `--budget-h 10` lässt Luft bis 11 h
für den Upload. Jeder Auftrag ist für sich, sie dürfen parallel laufen (Modal-Ausgabenlimit für
alle zusammen: etwa 33 USD). Vorher `git pull` (Auftrag 3 braucht `--resume-from`). Bei
"budget"/"spend limit" abbrechen und melden.

### 12. Vorlabels für den Wurf-Goldstandard (61 Wurf-Clips), 2026-11-16, Vorrang
- Wozu: Würfe aufs Tor sind das neue Hauptmass für den Balltracker. Die 61 Clips
  (`ml/gold/shot_clips.json`, Würfe aus den offiziellen Spielprotokollen, `ml/gold/pick_shots.py`)
  brauchen die Kandidaten der vier neuen Ballnetze und OWLv2. Kaggle-GPU ist bis Samstag
  aufgebraucht, Lukas gibt dafür Modal-Guthaben frei (23 CHF übrig).
- **Neu ab 2026-11-16 abends (nach drei Abbrüchen durch Modal-Preemption ohne Ergebnis):** Das Skript
  schreibt jetzt nach jedem Paket von 5 Clips auf das Volume `handball-gpu-out` und macht nach einer
  Unterbrechung dort weiter. Derselbe Befehl nochmals setzt ebenfalls fort. Nur noch hr1 und hrp1,
  OWLv2 auf jedem 4. Bild. Erwartet etwa 3.5 h auf einer T4, rund 2.5 USD.
- Befehl: `modal run --detach ml/gpu/prelabel_clips.py --clips ml/gold/shot_clips.json --tag shots`
  (Ergebnis-Dataset `handball-gpu-prelabel-shots`, ohne Datum). Unterbricht Modal den Lauf und startet
  ihn nicht selbst neu: denselben Befehl nochmals ausführen.
- Eingaben: `handball-segs-l01`, `-l02`, `-b01`, `-b03`, `-b04`, `handball-ball-hrmodels` (die
  Netze hr1, hrp1, hr2, hrp2). Ergebnis: Dataset `handball-gpu-prelabel-shots-<datum>`.
- Bei "budget"/"spend limit" abbrechen und melden. Die Cloud-Sitzung holt das Ergebnis selbst ab.

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

