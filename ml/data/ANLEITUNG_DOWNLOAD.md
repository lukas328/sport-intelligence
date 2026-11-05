# Anleitung: Spiele vom eigenen Computer nach Kaggle bringen

Für Claude Code auf dem Computer von Lukas (Windows). Die Spiele liegen schon auf dem Computer
(etwa 230). Ziel: daraus Trainings-Segmente schneiden und direkt als private Kaggle-Datasets
hochladen. Google Drive braucht es dafür nicht mehr (Drive sperrt Downloads nach zu vielen Zugriffen).

Den Rest macht die Cloud-Seite: Spieluhr pro Segment lesen, Labels aus den offiziellen
Spielprotokollen (handball.ch), Training auf der Kaggle-GPU. Von Hand labeln ist nicht nötig.

## Was vorbereitet ist (Branch `vision/real-footage`)
- `ml/data/local_ingest.py`: schneidet pro Spiel fünf 3-Minuten-Segmente (bei 15/30/50/70/85 %
  der Spielzeit, 1280 breit), genau wie die Cloud-Pipeline, und lädt je 20 Spiele als ein privates
  Kaggle-Dataset `handball-segs-l01`, `-l02`, ... hoch. Die ganzen Videos bleiben auf dem Computer.
  Upload pro Spiel etwa 50 bis 100 MB, für 230 Spiele also etwa 15 bis 20 GB.
  Unterbrechen ist kein Problem: gleicher Befehl nochmals, es macht dort weiter.
- `ml/data/videos_next.csv` und `ml/data/download_games.ps1`: für später, um weitere Spiele mit
  offiziellem Protokoll herunterzuladen (Teil B).

## Teil A: die Spiele auf dem Computer hochladen
1. Repo holen bzw. aktualisieren: `git fetch origin vision/real-footage`, `git checkout
   vision/real-footage`, `git pull`.
2. Werkzeuge prüfen:
   - Python 3.10 oder neuer (`python --version`)
   - ffmpeg und ffprobe (`ffmpeg -version`; sonst `winget install Gyan.FFmpeg`, dann neues Fenster)
   - Kaggle CLI: `pip install kaggle`
3. Kaggle-Zugang: Lukas erstellt auf kaggle.com unter Settings, API, "Create New Token" eine
   `kaggle.json` und legt sie nach `%USERPROFILE%\.kaggle\kaggle.json`. Den Schlüssel nirgends
   anzeigen, in kein Repo und in keinen Chat kopieren. Test: `kaggle datasets list -m` zeigt
   u.a. `handball-segs-b01`.
4. Testlauf ohne Upload, mit 2 Spielen (Pfade anpassen; WORKDIR ist ein beliebiger Arbeitsordner
   mit ein paar GB Platz):
   `python ml/data/local_ingest.py "D:\Handball\Videos" "D:\Handball\ingest" --user lukasde1000 --max-games 2 --dry-run`
   Prüfen: in `D:\Handball\ingest\batch_l01` liegen `<Spielname>_s0.mp4` bis `_s4.mp4`, die
   Segmente laufen und zeigen Spielszenen. Danach den Arbeitsordner löschen.
5. Echter Lauf:
   `python ml/data/local_ingest.py "D:\Handball\Videos" "D:\Handball\ingest" --user lukasde1000`
   Dauer: grob 1 bis 3 Minuten pro Spiel (Schneiden), plus Upload. Ausgabe am Schluss:
   wie viele Spiele, welche fehlgeschlagen sind.
6. Melden: Anzahl Spiele, Namen der hochgeladenen Datasets (`handball-segs-lNN`) und die Liste
   der fehlgeschlagenen Spiele. Den Ordner `D:\Handball\ingest\uploaded` behalten (Index pro
   Dataset).

Wichtig zu den Dateinamen: Der Spielname ist der Dateiname ohne Endung. Wenn die Dateien so
heissen wie in `videos.csv` (Spalte `name`, z.B. `CH_NLB_SGWaedenswilHorgen_Emmen_2023-09-03`),
findet die Cloud-Seite die offiziellen Daten automatisch. Dateien nicht umbenennen, ausser um sie
an diese Namen anzugleichen. Liegt neben einem Video eine `<Name>.info.json`, wird sie mitgenommen.
Kurze Dateien (unter 15 Minuten, z.B. schon geschnittene Stücke) werden als ein einzelnes Segment
übernommen.

## Teil B: später weitere Spiele herunterladen
`ml/data/videos_next.csv` listet 60 Schweizer Spiele ab 2023/24 mit vollem offiziellem Protokoll.
Was davon noch nicht auf dem Computer ist:
1. `winget install yt-dlp.yt-dlp` (und `yt-dlp -U` für die neueste Version).
2. In `ml/data`: `.\download_games.ps1 -Csv videos_next.csv -Out "D:\Handball\Videos"`
   (zuerst mit `-Max 2` testen). Bei "confirm you are not a bot": Handy-Hotspot oder
   `-Browser chrome`. Keine anderen Umgehungen.
3. Danach Teil A, Schritt 5 nochmals ausführen: es verarbeitet nur die neuen Spiele.
