# Auftrag: Analyse auf der Grafikkarte (eigene Sitzung)

Aus dem Livegang-Test vom 16.11. (`docs/ux-test/livegang/BEFUNDE.md`). Lukas will die Analyse-Logik
in einer eigenen Sitzung umsetzen, getrennt von den UI- und UX-Verbesserungen.

## Ausgangslage (Azure-Logs, 16.11.)

- **Einlesen zu langsam:** Ganzes Spiel einlesen (Video umwandeln) dauerte 1 h 39 min (15:07 bis 17:46 UTC), weil `hb-stg-worker` nur 1 CPU und 2 GB hat. Etwa 1,5-mal so lang wie das Spiel selbst, bevor die Analyse überhaupt beginnt
  Vorschlag: Worker grösser (2 bis 4 CPU) oder Umwandeln auf den Analyse-Worker legen.
- **Analyse auf der CPU:** Die Analyse läuft auf `hb-stg-gpu-worker` ohne Grafikkarte (4 CPU, 8 GB, `HB_GPU_BACKEND=local`). Ein 5-Minuten-Clip braucht so etwa 20 Minuten, ein ganzes Spiel also mehrere Stunden. Für echte Trainer nicht tragbar

## Entscheid und Plan

**entschieden (Lukas, 16.11.): GPU kommt als Feature.** Plan: Azure Container Apps «Serverless GPU» (NVIDIA T4) in Switzerland North, Videos bleiben in der Schweiz, skaliert auf null (zahlt nur, solange ein Spiel rechnet). Preise Azure (Retail-API, 16.11., USD): T4 0.000104/s = 0.37/h, dazu vCPU 0.000024/s und Speicher 0.000003/GiB·s. Mit 4 vCPU und 16 GiB etwa 0.90 USD pro Stunde (mit 8 vCPU und 56 GiB etwa 1.70). Pro Spiel geschätzt CHF 0.50 bis 1.50 bei 30 bis 90 Minuten Rechenzeit (Ziel P10: unter 45 Minuten, unter CHF 2); A100 (0.000756/s) wäre schneller, pro Spiel ähnlich teuer. Zu tun: CUDA-Image bauen und ausrollen (`apps/gpu-worker/Dockerfile.cuda` mit `onnxruntime-gpu` gibt es schon, es wird nur nirgends gebaut), GPU-Profil und Skalieren nach Warteschlange (KEDA Redis) in Terraform, GPU-Kontingent in Azure beantragen (Support-Ticket, Lukas), dann ein echtes Spiel messen und den Preis pro Spiel im Bericht festhalten. **Effizienz-Hebel** (erst messen, wo die Zeit hingeht, dann die grössten zuerst): nur Spielzeit rechnen (Aufwärmen, Pause, Timeouts überspringen, spart ein Drittel), weniger Bilder pro Sekunde für die Erkennung (z. B. 10 statt 25 bis 30, Verfolgung füllt dazwischen), kleinere Bildgrösse und nur das Feld, Video direkt auf der Grafikkarte lesen (NVDEC) statt vorher auf der CPU umzuwandeln (löst auch B1), Erkennung in Stapeln und mit halber Genauigkeit (FP16, TensorRT), teure Teile wie Rückennummern nur auf ausgewählten Bildern, Modelle im Image (kein Laden beim Start), zwei Dateien eines Spiels parallel auf zwei Karten (gleiche Kosten, halbe Zeit). Grob geschätzt zusammen 3- bis 5-mal schneller und günstiger

## Was die UI-Sitzung dafür erwartet

Fortschritt mit Schritt, Prozent und geschätzter Restzeit, damit Spiel, Start und Kopf ihn zeigen
können (K6, K13, K22 in der Befundliste). Wenn die Analyse dafür neue Felder liefert, bitte in der
API beschreiben.
