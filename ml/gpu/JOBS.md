# GPU-Aufträge (Modal, lokale Sitzung)

Ablauf und Regeln: `docs/plans/gpu-jobs-local.md`. Die Cloud-Sitzung schreibt neue Aufträge unter
"Offen", die lokale Sitzung führt sie aus und verschiebt sie nach "Erledigt" (mit Dataset-Name,
Dauer, Kosten, Auffälligkeiten). Vor dem Commit `git pull --rebase`, danach pushen.

## Offen

### 2. OWLv2-Pseudo-Labels für die ersten lokalen Batches
- Befehl: `modal run ml/gpu/owl_pseudo.py --datasets handball-segs-l01,handball-segs-l02,handball-segs-l03 --gpu T4 --budget-h 11`
- Eingabe: die drei ersten Batches von Lukas' Computer (300 Segmente).
- Ergebnis: neues Kaggle-Dataset `handball-gpu-owl-<datum>`.
- Dauer: etwa 10 h auf einer T4; Kosten etwa 6 USD (im Gratis-Guthaben).
- **Läuft seit 2026-11-05 ~15:55 (lokale Sitzung, Modal, detached).** Gemessen ~210 s pro Segment
  statt ~120 s, darum stoppt die 11-h-Grenze nach etwa 185 von 300 Segmenten (~6.5 USD). Rest als
  Folgeauftrag. Ergebnis zusätzlich auf dem Modal-Volume `handball-gpu-out`.
- Erst nach Auftrag 1 starten. Wenn Modal "budget" oder "spend limit" meldet: abbrechen und melden.

## Erledigt

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

