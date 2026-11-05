# GPU-Aufträge (Modal, lokale Sitzung)

Ablauf und Regeln: `docs/plans/gpu-jobs-local.md`. Die Cloud-Sitzung schreibt neue Aufträge unter
"Offen", die lokale Sitzung führt sie aus und verschiebt sie nach "Erledigt" (mit Dataset-Name,
Dauer, Kosten, Auffälligkeiten). Vor dem Commit `git pull --rebase`, danach pushen.

## Offen

### 1. Einrichtung prüfen (einmalig)
- Befehl: `modal run ml/gpu/smoke.py`
- Erwartet: `cuda: True`, eine GPU-Bezeichnung, Dateien aus `handball-ball-models`.
- Kosten: unter 0.05 USD.

### 2. OWLv2-Pseudo-Labels für die ersten lokalen Batches
- Befehl: `modal run ml/gpu/owl_pseudo.py --datasets handball-segs-l01,handball-segs-l02,handball-segs-l03 --gpu T4 --budget-h 11`
- Eingabe: die drei ersten Batches von Lukas' Computer (300 Segmente).
- Ergebnis: neues Kaggle-Dataset `handball-gpu-owl-<datum>`.
- Dauer: etwa 10 h auf einer T4; Kosten etwa 6 USD (im Gratis-Guthaben).
- Erst nach Auftrag 1 starten. Wenn Modal "budget" oder "spend limit" meldet: abbrechen und melden.

## Erledigt
(noch nichts)
