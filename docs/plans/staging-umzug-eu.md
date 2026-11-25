# Staging-Umzug in eine EU-Region mit serverloser GPU (Plan, Stand 2026-11-23)

Auftrag: Lukas-Entscheid 23.11., über die Hauptsitzung. Staging (heute Azure «hb-stg», Switzerland
North) zieht in eine EU-Region mit serverloser T4. Kandidaten: Italy North (bevorzugt, Nähe) und
Sweden Central. Nichts wird ohne Go der Hauptsitzung und Lukas' OK angewendet.

Grundlage: ADR 002 verlangt EU (die Schweiz wurde am 09.11. mit ADR 025 gewählt, nicht verlangt).
Switzerland North hat keine serverlose GPU (Azure-Doku «Serverless GPUs, supported regions»: T4 in
Italy North und Sweden Central ja, Switzerland North fehlt).

## 1. Regionen im Vergleich

Preise: Azure Retail Prices API, abgerufen am 23.11.2026, USD, Listenpreis ohne Rabatt.

| | Switzerland North (heute) | Italy North | Sweden Central |
|---|---|---|---|
| Serverlose T4 (Container Apps) | nein | ja | ja |
| Container Apps vCPU aktiv, pro vCPU-h | 0.086 | 0.122 (+42 %) | 0.086 |
| Container Apps Speicher aktiv, pro GiB-h | 0.011 | 0.014 (+33 %) | 0.011 |
| Container Apps vCPU im Leerlauf, pro vCPU-h | 0.011 | 0.014 | 0.011 |
| T4-GPU-Zähler, pro h | 0.374 | 0.342 | 0.342 |
| eine T4-Replika (Profil NC8as-T4: 8 vCPU, 56 GiB, 1 T4), pro h | | etwa 2.13 | etwa 1.64 |
| Analyse eines 10-min-Clips auf der T4 (1.55 x Videolänge aus Modal-Auftrag 15, plus etwa 3 min Kaltstart) | | etwa 0.66 | etwa 0.51 |
| Postgres Flexible B1ms, pro h | 0.0219 | 0.0199 | 0.0199 |
| Leerlaufkosten GPU (scale to zero) | | 0 | 0 |

Annahme bei der T4-Replika: Container Apps verrechnet beim GPU-Profil vCPU und Speicher der ganzen
Replika zu den Consumption-Preisen, dazu den GPU-Zähler. Das ist aus der Doku («billed based on
per-replica usage») und den Zählern geschlossen, nicht mit einer Rechnung belegt. Der erste echte Lauf
zeigt es in der Kostenanalyse.

Noch offen (nur mit Azure-Zugang prüfbar, Anfrage an die UX-Sitzung ist gestellt):
- Kontingent «Managed Environment Consumption T4 GPUs» in der Subscription je Region. Laut Doku ist
  es erst sichtbar, wenn dort eine Umgebung mit Workload-Profilen existiert. Notfalls legt Terraform
  eine leere Test-Umgebung an (kostet ohne Apps nichts) und löscht sie danach wieder.
- `az containerapp env workload-profile list-supported` je Region.
- Postgres Flexible B1ms je Region (`az postgres flexible-server list-skus`); der Preiszähler
  existiert in beiden Regionen.
- Key Vault, Log Analytics, Container Registry Basic, Storage (Azure Files für Redis-AOF) und Azure
  Communication Services sind in beiden Regionen Standarddienste. ACS ist ein globaler Dienst mit
  eigenem Datenstandort (heute «Switzerland», neu «Europe»).

Empfehlung: **Sweden Central**. Gleiche Preise wie heute für die Grundlast, eine T4-Stunde etwa
23 % billiger als in Italy North. Die Latenz aus der Schweiz (etwa 30 bis 40 ms statt 15 bis 20 ms)
merkt man bei einer Web-App mit Videos aus R2 kaum. Italy North kostet bei der Grundlast etwa 40 %
mehr, bei kleinem Staging-Volumen sind das wenige Franken im Monat. Entscheid bei Lukas.

## 2. Inventar (was liegt heute in Azure)

Aus dem Code (Terraform, ADR 002, 025):
- Videos und Artefakte liegen in **Cloudflare R2 (EU)**, nicht in Azure. Sie ziehen nicht um.
- In Azure: Postgres 16 (B1ms, 32 GiB, 14 Tage PITR), Redis als Container App mit AOF auf einer
  Azure-Files-Freigabe (nur die Job-Warteschlange), Key Vault (generierte und manuelle Secrets:
  R2-Token, OAuth usw.), Container Registry Basic (Images), Log Analytics (30 Tage), Communication
  Services (E-Mail, Domain mit SPF/DKIM), Budget-Alarm.

Aus der Datenbank (offen, kommt aus dem Diag-Lauf der UX-Sitzung): Anzahl Organisationen,
Nutzer (davon echte, ohne Testkonten), Spiele, Videos, Jobs, DB-Grösse.

## 3. Migrationsplan

Leitlinie: neue Umgebung parallel aufbauen, testen, dann umschalten; die alte bleibt bis nach dem
Smoke-Test stehen und ist der Rückweg.

Schritt A, Terraform (ein PR, nichts angewendet):
1. Zweiter State-Key (z. B. `staging-eu.tfstate`) und eigene tfvars. Der Name der Ressourcengruppe
   ist heute `rg-hb-stg` und muss in derselben Subscription eindeutig sein: `name` bekommt für den
   neuen Stack einen anderen Wert (z. B. `hbeu`), oder ein neuer Variablen-Suffix.
2. `location` = Zielregion; ACS mit `data_location = "Europe"`.
3. GPU-Worker: Workload-Profil `Consumption-GPU-NC8as-T4` in der Umgebung, App `gpu-worker` darauf
   mit dem Mittelweg-Image (`Dockerfile.cuda`), `min_replicas = 0`, `max_replicas = 1`, Scale-Regel
   KEDA «redis» auf die Länge der GPU-Warteschlange (`rq:queue:gpu`). Ballnetz hrp1 uint8 960
   (Key/SHA wie #76), ReID wie heute. Ein CPU-Worker für Einlesen und Kurzes bleibt.
4. Längengrenze: Analyse auf der GPU nur bis z. B. 15 min Video (neue Einstellung neben
   `ball_max_minutes`), längere Videos mit klarer Meldung ablehnen oder auf der CPU ohne Ballnetz.
5. Budget-Alarm für den GPU-Anteil bei 20 und 30 EUR (Budget mit Filter auf die GPU-App bzw. die
   Zähler, zusätzlich zum bestehenden Gruppenbudget).

Schritt B, Aufbau (mit Go):
1. `terraform apply` des neuen Stacks (etwa 30 min, Postgres etwa 10 min davon).
2. Images in die neue Registry übernehmen (`az acr import` aus der alten).
3. Manuelle Secrets aus dem alten Key Vault in den neuen kopieren (Skript mit `az keyvault secret
   show/set`, läuft bei Lukas oder im Workflow, nie im Chat). Generierte Secrets werden neu erzeugt;
   der App-Signaturschlüssel wird übernommen, sonst sind alle abgemeldet.
4. GPU-Kontingent prüfen bzw. beantragen (Lukas), erster GPU-Lauf mit einem kurzen Clip.

Schritt C, Umschalten (Wartungsfenster):
1. Alte Umgebung auf Wartung (Web zeigt Hinweis, Worker auf 0), damit nichts mehr schreibt.
2. `pg_dump -Fc` aus der alten DB, `pg_restore` in die neue (Testdaten, wenige MB: Minuten), danach
   Migrationen-Job laufen lassen (Rolle `handball_app`), Zeilenzahlen vergleichen.
3. Warteschlange: laufende Jobs vorher fertig werden lassen; Redis-Inhalt zieht nicht um (der
   Watchdog stellt verlorene Jobs neu ein).
4. Smoke-Test auf der Standard-Adresse der neuen Umgebung (Login per Link, Spiel öffnen, Video aus
   R2 abspielen, kurzer Analyse-Lauf auf der GPU).
5. DNS: CNAME von `app.handball-intelligence.com` und `asuid`-TXT auf die neue Umgebung, verwaltetes
   Zertifikat binden (README Schritt 6). OAuth-Redirect-URIs bleiben gleich (gleiche Domain).
6. E-Mail: neue ACS-Domain verifizieren, SPF/DKIM-Einträge ersetzen (oder die alte ACS-Ressource bis
   dahin weiterverwenden).

Schritt D, Abbau (erst nach erfolgreichem Smoke-Test und einigen Tagen Betrieb): alte Umgebung mit
`paused = true` stehen lassen, dann `terraform destroy` des alten Stacks; Key-Vault-Soft-Delete
beachten (7 Tage).

Rückweg: bis Schritt D steht die alte Umgebung. DNS zurück auf die alte Umgebung, Worker hoch; Daten,
die in der neuen DB in der Zwischenzeit entstanden sind, per `pg_dump` zurück (bei Staging
vertretbar).

Dauer und Ausfall (Schätzung): Terraform-PR und Review 1 Tag; Aufbau und Tests 0.5 Tage; Umschalten
mit Wartungsfenster etwa 30 bis 60 min Ausfall (DB-Kopie Minuten, DNS und Zertifikat der Rest).

## 4. Texte zum Datenstandort, die angepasst werden müssen (Umsetzung UX-Sitzung)

- `apps/site/src/messages/de.ts`, `en.ts` und `fr.ts`: Zeile 195/197 («Daten in der Schweiz und der EU»),
  597/598 («Die App und ihre Datenbank laufen auf Servern in der Schweiz ...»), 729/730
  («Datenstandort: App und Datenbank in der Schweiz ...»), 773/774 («Die Daten liegen in der Schweiz
  und der EU ...»). «Entwickelt in der Schweiz» bleibt.
- `apps/site/content/help/{de,en,fr}/datenschutz-und-loeschen.mdx` Zeile 5.
- Doku: `docs/LIVEGANG.md` (Zeilen 7, 26, 28), `docs/adr/025-azure-app-hosting.md` (Region, neuer
  Nachtrag), `docs/adr/002-hosting-region.md` (Nachtrag), `infra/terraform/azure/README.md` und
  `variables.tf` (`location`-Beschreibung), `terraform.tfvars.example`.
- Datenschutzerklärung und Liste der Unterauftragsverarbeiter: Region von Azure (Microsoft) nennen.

## 5. Entscheide und Umsetzung (2026-11-23)

- Region: **Sweden Central** (Hauptsitzung, Lukas hat die Wahl überlassen).
- GPU als **Container-Apps-Job mit Ereignis-Auslöser** statt als App: KEDA startet eine Ausführung,
  solange die Redis-Liste `rq:queue:gpu` nicht leer ist; der Worker läuft mit `--burst` und endet,
  wenn die Warteschlange leer ist. Eine App würde KEDA beim Herunterskalieren mitten in einer
  Analyse beenden (der Job ist dann schon aus der Liste); eine Job-Ausführung läuft zu Ende. Höchstens
  eine Ausführung, im Leerlauf nichts.
- Die Audio-Synchronisation zweier Kameras läuft ebenfalls über die GPU-Warteschlange und weckt die
  T4 kurz (Kaltstart, wenige Rappen).
- Secrets: `hb-secret-key` (Sitzungen) und `hb-encryption-key` (verschlüsselte Spalten) schreibt
  Terraform nur einmal; der Bootstrap kopiert die Werte der alten Umgebung, sonst wären Sitzungen und
  verschlüsselte Daten nach dem DB-Umzug ungültig.
- Längengrenze: `HB_ANALYSIS_MAX_MINUTES` (15) im GPU-Job; längere Videos enden sofort mit dem Code
  `too_long` und einer Meldung in der App («Schneide das Video kürzer ...»), neu starten wird nicht
  angeboten.
- Registry Basic: das CUDA-Image ist gross (einige GB pro Tag); alte Tags von Zeit zu Zeit löschen,
  sonst wächst der Speicher über die 10 GB im Preis.

## 6. Abschluss (2026-11-24)

Ablauf und Messwerte:
- Aufbau Sweden Central: dritter Bootstrap-Lauf grün (Run 45235594879). Die zwei ersten scheiterten an
  der fehlenden Postgres-Firewall-Regel im gezielten Apply (#111) und an einem halb aufgebauten State
  (#112).
- DB-Umzug: Run 45253681754, 23.11. 19:57 UTC. Dump 0.67 MB; Zeilen alt | neu identisch
  (organizations 3, users 5, org_memberships 3, teams 3, matches 29, video_assets 7,
  processing_jobs 17, events 1585, alembic_version 1).
- DNS (Cloudflare, mit Lukas' OK, 24.11. 12:27 UTC): CNAME app auf
  `hbeu-stg-web.lemonmoss-a4ad245c.swedencentral.azurecontainerapps.io`; zusätzlicher TXT
  `ms-domain-verification=d3695dad-…`. `asuid.app` war schon richtig. Rückweg-CNAME:
  `hb-stg-web.victorioussky-d3bd8932.switzerlandnorth.azurecontainerapps.io`.
- Deploy stack=eu (Run 45394191027): Zertifikat gebunden 12:40 UTC, Mail-Domain 4 von 4 verifiziert,
  `mail_live`, Health 200 über die Domain. Smoke-Test grün (Login, Spiele, Spiel, Szenen, Spieltag,
  Video; Laptop und Handy).
- Alte Umgebung pausieren: der erste Lauf (45396182436) scheiterte im Plan, weil move-db den Ingress
  der alten Web-App abgeschaltet hatte und Terraform ihre Custom Domain ohne Ingress nicht lesen kann.
  Der Workflow schaltet den Ingress vor dem Plan wieder ein (PR zu diesem Abschnitt), dann Pause:
  Apps auf 0, Postgres gestoppt, Domain-Bindung der alten App entfernt. Abbau nach einigen Tagen
  stabilem Betrieb, mit Lukas' OK. Rückweg bis dahin: CNAME zurück, Deploy stack=ch mit
  state=resume.
- GPU: noch aus (`gpu = false`). Nach Freigabe des T4-Kontingents ein Deploy stack=eu mit gpu=on.

Ausfall: 23.11. 19:57 bis 24.11. 12:40 UTC, etwa 16.7 h. Die eigentliche Umschaltung (DNS,
Zertifikat) dauerte 13 min. Der Rest war Warten: Die Sitzungen wurden über Nacht neu gestartet, und
der Cloudflare-Zugang lag nicht bei der Sitzung, die den CNAME umstellen sollte.

Lehren für künftige Umzüge:
- DB-Kopie und DNS-Umstellung direkt hintereinander, ohne Pause dazwischen. Das Wartungsfenster erst
  beginnen, wenn alle Beteiligten bereit sind.
- Vorher prüfen, wer die DNS-Schreibrechte wirklich hat, und den Weg testen (Lesezugriff auf die
  Zone genügt als Probe).
- Die TXT-Einträge (asuid, Domain-Verifizierung) vorab setzen; sie stören die alte Umgebung nicht.
- Erste Läufe auf einer neuen Umgebung mit gezieltem Apply prüfen alle Abhängigkeiten (Firewall)
  und den halben State bei Wiederholung.
- Was ein Skript an Terraform vorbei ändert (Ingress aus für die Wartung), muss der nächste Lauf
  wieder herstellen, bevor Terraform plant.

## 7. Abbau der ersten Umgebung (rg-hb-stg)

Nur mit Lukas' OK (geplant 28.11.). Spätestens am 1.12. entscheiden: Azure startet einen gestoppten
Postgres nach 7 Tagen von selbst wieder (gestoppt am 24.11.), dann kostet er wieder.

Was wegfällt: alles in `rg-hb-stg` (Container-Apps, Registry, Postgres mit seinen Backups, Vault,
Mail-Dienst, Redis-Speicher, Log Analytics, Budget). Der Weg zurück (CNAME zurück, Deploy stack=ch
mit state=resume) geht danach nicht mehr. Die Daten liegen seit dem 23.11. in der EU-Datenbank
(Zeilenzahlen identisch, Abschnitt 6) und laufen dort weiter. Nicht betroffen: der Terraform-State
(`rg-hb-tfstate`), R2, Cloudflare, die EU-Umgebung `rg-hbeu-stg`.

Vorher prüfen:
1. Die EU-Umgebung lief einige Tage stabil (Alarme ruhig, Smoke-Test grün).
2. Nichts zeigt mehr auf die alte Umgebung: CNAME `app` auf `…swedencentral.azurecontainerapps.io`,
   Mail aus der EU-Umgebung (`mail_live`).
3. Keine Analyse läuft (Regel: nichts ausrollen während einer Analyse; der Abbau berührt die
   EU-Umgebung nicht, trotzdem nicht gleichzeitig mit einem EU-Deploy, die Workflow-Concurrency
   reiht ohnehin ein).

Ausführen: Actions → Deploy → Run workflow mit mode `teardown`, stack `ch`, confirm `rg-hb-stg`.
Das Skript `infra/azure/teardown-ch.sh`
- bricht ab, wenn confirm nicht der Name der Ressourcengruppe aus dem ch-State ist, wenn es die
  EU-Gruppe wäre, wenn `app` noch auf die alte Umgebung zeigt oder `https://app…/api/healthz` nicht
  200 antwortet;
- listet die Ressourcen der Gruppe (Log und Artefakt `teardown-<run>`) und löscht die ganze Gruppe
  (10 bis 30 min);
- löscht den alten Vault endgültig aus dem Soft Delete (fehlt das Recht, nur eine Warnung: Azure
  entfernt ihn nach 7 Tagen);
- verschiebt `staging.tfstate` und `staging.tfvars` nach `tfstate/archive/<datum>-…`. Ein späterer
  Lauf mit stack `ch` bricht dann bei «Settings and state» ab, statt eine neue Umgebung zu planen.

Danach von Hand (eigener PR beziehungsweise Cloudflare):
- Workflow: Standard-Stack auf `eu` (heute `ch`; ein Push mit `[deploy]` ginge sonst auf den
  gelöschten Stack und bräche ab), später den Stack `ch` und `move-db` ganz entfernen.
- Cloudflare: den alten TXT `ms-domain-verification` der ersten Umgebung löschen (der neue beginnt
  mit `d3695dad`), `asuid.app` bleibt. Den Rückweg-CNAME aus Abschnitt 6 hier als ungültig vermerken.
- Kosten: im Cost Management nach einigen Tagen prüfen, dass für `rg-hb-stg` nichts mehr anfällt.
