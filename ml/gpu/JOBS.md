# GPU-Aufträge (Modal, lokale Sitzung)

Ablauf und Regeln: `docs/plans/gpu-jobs-local.md`. Die Cloud-Sitzung schreibt neue Aufträge unter
"Offen", die lokale Sitzung führt sie aus und verschiebt sie nach "Erledigt" (mit Dataset-Name,
Dauer, Kosten, Auffälligkeiten). Vor dem Commit `git pull --rebase`, danach pushen.

## Offen

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

