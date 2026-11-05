# Anleitung: nächste Spiele herunterladen und in den Drive-Ordner legen

Diese Anleitung ist für Claude Code auf dem Computer von Lukas (Windows, PowerShell). Ziel: die
Spiele aus `ml/data/videos_next.csv` als ganze Videos in den geteilten Google-Drive-Ordner legen.
Den Rest (Schneiden, Spieluhr lesen, Labels aus den offiziellen Logs, Upload nach Kaggle) macht
die Pipeline in der Cloud automatisch.

## Was schon vorbereitet ist
- `ml/data/videos_next.csv`: 60 Schweizer Spiele ab Saison 2023/24 mit vollem offiziellem
  Spielprotokoll (handball.ch), die noch nicht verarbeitet sind, meiste Tore zuerst.
  Format `url;start;end;name` (Strichpunkt).
- `ml/data/download_games.ps1`: lädt jedes Spiel als ganzes Video (720p, mp4) plus
  `<name>.info.json` und benennt die Dateien exakt nach der Spalte `name`.
- Drive-Ordner: https://drive.google.com/drive/folders/1-KG572KNR-KK4NL4qMaVplL9KFlSm_AY

Es ist reines Rohmaterial: keine Labels von Hand nötig. Die Labels kommen aus den offiziellen
Protokollen, darum ist der Dateiname wichtig.

## Schritte
1. Repo aktualisieren: `git fetch origin vision/real-footage` und `git checkout vision/real-footage`
   (oder `git pull`), dann in den Ordner `ml/data` wechseln.
2. Werkzeuge prüfen, falls nötig installieren:
   `winget install yt-dlp.yt-dlp` und `winget install Gyan.FFmpeg`, danach ein neues PowerShell-
   Fenster. `yt-dlp -U` holt die neueste Version (YouTube ändert oft etwas).
3. Zielordner: den Drive-Ordner über "Google Drive für Desktop" als lokalen Ordner verwenden
   (z.B. `G:\Meine Ablage\...` oder eine Verknüpfung zum geteilten Ordner). Prüfen, dass dort
   genug Platz ist: etwa 1 bis 2 GB pro Spiel, 60 Spiele also 60 bis 120 GB.
   Wenn der Platz nicht reicht: mit `-Max 15` in Etappen arbeiten.
4. Zuerst ein Test mit 2 Spielen:
   `.\download_games.ps1 -Csv videos_next.csv -Out "<Drive-Ordner>" -Max 2`
   Prüfen: im Ordner liegen `<name>.mp4` und `<name>.info.json`, das Video läuft, Dauer etwa
   60 bis 120 Minuten.
5. Dann alle: dasselbe ohne `-Max`. Das Skript überspringt, was schon da ist, und kann jederzeit
   neu gestartet werden.
6. Falls YouTube "confirm you are not a bot" meldet (VPN, Firmennetz): über einen Handy-Hotspot
   laufen lassen, oder `-Browser chrome` (bzw. `edge`, `firefox`) anhängen, dann nutzt yt-dlp die
   angemeldete YouTube-Sitzung (langsamer, mit Pausen). Keine anderen Umgehungen.

## Regeln
- Dateinamen nicht ändern, keine Zusätze wie `.f298` oder `(1)`. Nur `<name>.mp4` und
  `<name>.info.json`.
- Keine Teilstücke hochladen: das Skript lädt zuerst in einen Temp-Ordner und verschiebt erst
  fertige Videos.
- Spiele, die nicht klappen (privat, gelöscht), einfach auslassen; das Skript listet sie am Ende.

## Ausserdem: vier gesperrte Videos
Google Drive sperrt den Download dieser vier Dateien ("too many users have downloaded"). Im
Drive-Ordner bei jeder "Kopie erstellen", die Kopie exakt auf den alten Namen umbenennen (ohne
"Kopie von"), dann das Original löschen:
- `CH_NLB_SGWaedenswilHorgen_Staefa_2023-04-22.mp4`
- `CH_NLB_SGWaedenswilHorgen_Staefa_2023-12-02.mp4`
- `CH_NLB_SGWaedenswilHorgen_TVBirsfelden_2023-09-09.mp4`
- `CH_NLB_SGWaedenswilHorgen_TVMoehlin_2023-10-14.mp4`

## Am Schluss melden
Wie viele Spiele hochgeladen sind und welche nicht geklappt haben. Die Cloud-Pipeline holt neue
Dateien alle 10 Minuten ab.
