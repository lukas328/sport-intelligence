# GPU-Aufträge (Modal, lokale Sitzung)

Ablauf und Regeln: `docs/plans/gpu-jobs-local.md`. Die Cloud-Sitzung schreibt neue Aufträge unter
"Offen", die lokale Sitzung führt sie aus und verschiebt sie nach "Erledigt" (mit Dataset-Name,
Dauer, Kosten, Auffälligkeiten). Vor dem Commit `git pull --rebase`, danach pushen.

## Offen

(nichts)

## Erledigt

### 2. OWLv2-Pseudo-Labels für l01 bis l03 — Teilergebnis, gestoppt durch 11-h-Grenze, 2026-11-06
- Ergebnis: `lukasde1000/handball-gpu-owl-20261105-1449` (Status ready, 189 `segs/*.json` plus
  `bench_owl.json`). Auch auf dem Modal-Volume `handball-gpu-out`.
- Abdeckung: 189 von 300 Segmenten. l01 100/100, l02 89/100, l03 0/100. Offen: 11 aus l02, alle
  aus l03. Das Skript überspringt Fertiges nicht, ein Folgeauftrag muss die offenen Segmente
  also selbst auswählen, sonst wird l01 nochmals gerechnet.
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

