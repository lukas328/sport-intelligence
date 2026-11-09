# Zusammenarbeit: Cloud-Sitzung und lokale Sitzung (GPU über Modal)

Für Claude Code auf dem Computer von Lukas. Zwei Sitzungen arbeiten am gleichen Repo und an den
gleichen Daten, ohne sich in die Quere zu kommen.

## Wer macht was
| | Cloud-Sitzung (claude.ai, Container) | Lokale Sitzung (Computer von Lukas) |
|---|---|---|
| Aufgabe | Analyse-Code, Daten-Pipeline, Auswertung, Benchmarks | GPU-Läufe über Modal, Upload der eigenen Spiele |
| Läuft dauerhaft | Ingest (Drive), `library.py` (liest neue Kaggle-Batches), stündlicher Abgleich mit handball.ch | nichts dauerhaft; Jobs auf Anfrage |
| Darf ändern | alles ausser `ml/gpu/` Ergebnisse und `local_ingest.py` | `ml/gpu/` (Job-Skripte, Protokoll), `ml/data/local_ingest.py`, `ml/data/ANLEITUNG_DOWNLOAD.md` |
| GPU | nur Kaggle (Kontingent) | Modal (Guthaben), eigene GPU falls vorhanden |

Modal geht aus der Cloud-Sitzung nicht (deren Netzwerk-Proxy lässt gRPC nicht durch), darum
startet nur die lokale Sitzung Modal-Jobs.

## Gemeinsame Ablage: Kaggle
Alle Daten und Ergebnisse liegen als private Kaggle-Datasets im Konto `lukasde1000`; beide Seiten
lesen und schreiben dort. Namen:
- `handball-segs-bNN` (Cloud-Ingest), `handball-segs-lNN` (lokaler Upload): Segmente, nie ändern.
- `handball-ball-*`: Trainingsdaten und Modelle des Ballnetzes (`handball-ball-models` enthält
  `ball_best.pt`, das jeweils beste Modell).
- `handball-gpu-<job>-<datum>`: Ergebnis eines GPU-Laufs (neu, eins pro Lauf).
Ein Ergebnis wird nie überschrieben, nur neu angelegt; "das beste Modell" wechselt nur die
Cloud-Sitzung nach einem Benchmark.

## Ablauf eines GPU-Laufs
1. Die Cloud-Sitzung schreibt einen Auftrag in `ml/gpu/JOBS.md` (Abschnitt "Offen"): Job-Name,
   Skript in `ml/gpu/`, Eingabe-Datasets, erwartete Dauer und Kosten, Befehl. Commit und Push.
2. Lukas sagt der lokalen Sitzung: "Führe die offenen Jobs in ml/gpu/JOBS.md aus."
3. Die lokale Sitzung: `git pull`, Job mit `modal run ml/gpu/<skript>.py ...` starten. Das Skript
   lädt die Eingaben von Kaggle, rechnet auf der GPU und lädt das Ergebnis als neues Dataset
   `handball-gpu-<job>-<datum>` hoch. Dann trägt sie unter "Erledigt" ein: Dataset-Name, Dauer,
   Kosten laut Modal, Auffälligkeiten. Commit und Push.
4. Die Cloud-Sitzung holt das Ergebnis, wertet aus und entscheidet den nächsten Auftrag.

## Regeln gegen Konflikte
- Vor jedem Commit `git pull --rebase` auf `vision/real-footage`, danach sofort pushen.
- Jede Seite ändert nur ihre Dateien (Tabelle oben). `ml/gpu/JOBS.md`: die Cloud-Sitzung schreibt
  nur unter "Offen", die lokale Sitzung verschiebt Einträge nach "Erledigt".
- Kein Force-Push, kein Merge nach `main`, keine Löschungen auf Kaggle oder GitHub ohne Lukas.
- Schlüssel bleiben lokal: Kaggle in `%USERPROFILE%\.kaggle\kaggle.json`; Kaggle-Zugang für
  Modal-Jobs als Modal-Secret `kaggle` (Variablen `KAGGLE_USERNAME`, `KAGGLE_KEY`), angelegt mit
  `modal secret create kaggle KAGGLE_USERNAME=lukasde1000 KAGGLE_KEY=...` (Wert aus kaggle.json,
  nicht in Chat oder Repo).
- Ausgabenlimite in Modal gesetzt lassen; jeder Auftrag nennt die erwarteten Kosten.

## Einrichtung (einmal, lokale Sitzung)
1. `pip install modal kaggle` und prüfen: `modal profile current`, `kaggle datasets list -m`.
2. Modal-Secret `kaggle` wie oben anlegen.
3. Test: `modal run ml/gpu/smoke.py` (zeigt die GPU, liest ein kleines Kaggle-Dataset, lädt nichts
   hoch). Ergebnis in `ml/gpu/JOBS.md` unter "Erledigt" eintragen, committen, pushen.
