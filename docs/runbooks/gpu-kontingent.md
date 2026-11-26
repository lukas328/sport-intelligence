# T4-GPU-Kontingent für Staging (Sweden Central) beantragen

Staging läuft seit dem 24.11.2026 in Sweden Central (`rg-hbeu-stg`, Umgebung `cae-hbeu-stg`). Die
Analyse läuft dort auf der CPU, bis die serverlose T4-GPU freigeschaltet ist. Das Kontingent gilt pro
Container-Apps-Umgebung und wird in deren Quota-Seite beantragt, nicht über die allgemeine
Quota-Seite des Abos.

## 1. Zuerst nachsehen, ob schon Kontingent da ist
Laut Microsoft haben Pay-as-you-go- und Enterprise-Kunden T4- und A100-Kontingent standardmässig.

1. Azure Portal öffnen: <https://portal.azure.com/#view/HubsExtension/BrowseResource/resourceType/Microsoft.App%2FmanagedEnvironments>
2. Die Umgebung **cae-hbeu-stg** anklicken.
3. Links unter **Settings** auf **Quota** gehen.
4. Die Zeile **Managed Environment Consumption T4 GPUs** suchen.
   - Steht dort ein Limit von 1 oder mehr: nichts beantragen, weiter mit Schritt 3.
   - Steht dort 0: Schritt 2.
   - Fehlt die Zeile ganz: Bescheid geben (dann stimmt Region oder Umgebungstyp nicht).

## 2. Erhöhung beantragen
1. Auf derselben Seite die Zeile **Managed Environment Consumption T4 GPUs** auswählen.
2. Im Fenster **New Quota Request** bei **New limit** `1` eintragen.
3. Falls ein Begründungsfeld erscheint, diesen Text verwenden:

   > Serverless T4 GPU for video analysis in a staging environment (Azure Container Apps job,
   > max. 1 concurrent execution, scale to zero). Expected usage: a few short test runs per week.

4. **Submit**. Die Anfrage wird entweder sofort erfüllt oder an den Azure Support weitergeleitet
   (dann kommt eine Mail, meist innert 1 bis 3 Werktagen).

Nicht verwechseln: «Subscription NCA 100 GPUs» auf der Abo-Quota-Seite ist das Kontingent für fest
zugewiesene GPUs und hier nicht gemeint.

## 3. GPU einschalten (macht die Hauptsitzung)
Sobald das Limit mindestens 1 ist: Workflow **Deploy** mit `stack = eu`, `mode = deploy`,
`gpu = on`. Danach läuft jede Analyse als GPU-Job (höchstens 1 gleichzeitig, im Leerlauf 0 Kosten,
Längengrenze 15 min, eigenes Budget 30 mit Alarm bei 20).

**Was der Plan mit `gpu = on` vorhat** (Plan-Run 45850105723, 26.11.: 2 neu, 1 geändert, 1 weg):
- neu: Job `hbeu-stg-gpu` auf dem Profil `gpu-t4` (`Consumption-GPU-NC8as-T4`, 8 CPU, 56 GiB),
  Image `hb-gpu-worker-cuda:<tag>`, Befehl `python -m handball_gpu_worker --burst`;
  - Start durch KEDA auf der Redis-Liste `rq:queue:gpu` (ab 1 Eintrag, Abfrage alle 30 s,
    höchstens 1 Ausführung, keine Wiederholung, Zeitgrenze 4 h);
  - Ballnetz hr-nods uint8 (`ball_hrnods_fp16_u8-1bbacb7bca86`), ReID leer,
    `HB_ANALYSIS_MAX_MINUTES = 15`;
- neu: Budget `budget-hbeu-stg-gpu` 30 pro Monat, Mail bei 66 % (20) und 100 %;
- geändert: Umgebung `cae-hbeu-stg` bekommt das Workload-Profil `gpu-t4` (in-place);
- weg: die CPU-App `hbeu-stg-gpu-worker` (beide nehmen dieselbe Warteschlange `gpu`).

**Was der Plan nicht zeigt:** Terraform prüft weder das T4-Kontingent noch, ob das CUDA-Image da
ist. Ein Plan mit `gpu = on` ist ohne Nebenwirkung (die Einstellungsdatei wird nur beim Apply
gespeichert).

**Checkliste am GPU-Tag**
1. Status-Lauf (`mode = status`): Zeile «GPU-Kontingent: X von Y -> gpu=on möglich» abwarten.
   Bei «nicht möglich» nicht weiter: das Apply scheitert sonst beim Workload-Profil.
2. Keine Analyse in Arbeit: die Deploy-Sperre bricht sonst ab (`force_busy` nicht verwenden).
3. Deploy mit `gpu = on`. Reihenfolge im Lauf:
   - Der Schritt «Images» baut zuerst das CUDA-Image (bis 2 h). Scheitert er, bricht der Lauf vor
     dem Apply ab, und es ist nichts geändert.
   - Erst danach entfernt das Apply die CPU-App und legt Profil und Job an.
4. Prüfen:
   - Job `hbeu-stg-gpu` vorhanden, Budget vorhanden.
   - Einen kurzen Clip (unter 15 min) hochladen: nach höchstens etwa 1 min startet eine
     Ausführung.
   - Im Log steht der CUDA-Provider (kein `no_gpu`) und `ball_model_status ok`, am Ende
     `analysis_done`.
   - Kosten des Probelaufs im Budget ansehen (Ziel unter 30).

**Rückfall:** Deploy mit `gpu = off`. Das legt die CPU-App wieder an und entfernt Job und
GPU-Profil; die Analyse läuft wieder auf der CPU.
- Scheitert das Apply mittendrin (z. B. Kontingent), wird die Einstellung nicht gespeichert
  (der Schritt «Remember what is deployed» läuft nur nach einem erfolgreichen Apply). Der nächste
  Deploy mit `gpu = keep` stellt dann ebenfalls die CPU-App wieder her.
- In der Lücke ohne Worker gehen keine Analysen verloren:
  - Sie warten in der Redis-Liste `rq:queue:gpu`; der Trainer sieht «wartet auf einen Worker»
    mit Minuten.
  - Ein Job, der aus der Warteschlange verschwunden ist, wird nach 5 min neu eingereiht
    (`QUEUED_CHECK_S` in `services/progress.py`).
  - Wartende Jobs bricht keine Zeitgrenze ab.

Quellen: [Serverless GPUs in Azure Container Apps](https://learn.microsoft.com/en-us/azure/container-apps/gpu-serverless-overview),
[Quota requests](https://learn.microsoft.com/en-us/azure/container-apps/quota-requests),
[Quotas](https://learn.microsoft.com/en-us/azure/container-apps/quotas).
