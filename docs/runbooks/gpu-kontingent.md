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

Quellen: [Serverless GPUs in Azure Container Apps](https://learn.microsoft.com/en-us/azure/container-apps/gpu-serverless-overview),
[Quota requests](https://learn.microsoft.com/en-us/azure/container-apps/quota-requests),
[Quotas](https://learn.microsoft.com/en-us/azure/container-apps/quotas).
