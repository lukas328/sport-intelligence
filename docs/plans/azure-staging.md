# Test-Umgebung auf Azure (Stand 2026-11-09)

Aufgesetzt von der lokalen Sitzung nach `infra/terraform/azure/README.md`. Für Lukas und die Hauptsitzung.

## Was läuft
| | |
|---|---|
| Adresse | https://test.handball-intelligence.com (Zertifikat von Azure, DNS bei Cloudflare, graue Wolke) |
| Abo | "Azure subscription 1" (Pay-As-You-Go), Region Schweiz Nord |
| Ressourcengruppe | `rg-hb-stg` (App), `rg-hb-tfstate` (Terraform-Zustand, `sthbtfstate72432`, Schlüssel `staging.tfstate`) |
| Registry, Key Vault, Postgres | `acrhbstg1tovl`, `kv-hbstg1tovl`, `psql-hbstg1tovl` (B1ms, 7 Tage Backup) |
| Images | Tag `af4a539`, gebaut in der Registry mit `infra/terraform/azure/acr-build.yaml` |
| Speicher | vorläufig R2-Bucket `handball-testdata` für Videos und Ergebnisse (siehe offene Punkte) |
| Mail | `HB_EMAIL_BACKEND=console`: Mails stehen im Log, nichts wird verschickt |
| Budget-Alarm | 50 pro Monat, Mails an `lukasdech@gmx.de` |
| Test-Konto | Zugangsdaten in Lukas' Notizordner (`04_Nebenprojekte/handball-intelligence-staging-testkonto.txt`), nicht im Repo |

## Test von Anfang bis Ende (synthetisches Video, 60 s)
Registrieren, Verein, Mannschaft, Spiel und Upload über die öffentliche API (via Web-Proxy), dann Ingest und
Analyse automatisch: Ingest etwa 60 s, Analyse auf der CPU 33 s, 76 Spuren, keine Kalibrierung nötig.
**Noch offen:** ein ganzes Spiel (60 min, echtes Material, mit Matchblatt). Auf dem PC liegt kein echtes
Material, nur auf Kaggle.

## Befunde für die Hauptsitzung
1. **Registrierung bricht mit 500 ab, wenn der Mailversand scheitert** (`services/auth.py:189` →
   `send_email_verification` → SMTP-Login schlägt fehl). Die Bestätigungs-Mail sollte die Registrierung nicht
   blockieren (Fehler loggen, später erneut senden oder über den Worker schicken).
2. **Bootstrap braucht einen R2-Admin-Token** (`CreateBucket`, `PutBucketCors`). Mit einem Token, der nur
   Objekte lesen und schreiben darf, scheitert der Migrations-Job am Ende, obwohl die Migration selbst
   durchläuft. Vorschlag: vorhandene Buckets ohne CORS-Recht mit Warnung durchlassen statt abzubrechen.
3. Videos und Ergebnisse teilen sich gerade einen Bucket. Das geht, weil beide den Präfix
   `{org}/{match}/{video}/` nutzen; beim Löschen eines Videos verschwinden dann aber auch die Ergebnisse im
   selben Präfix (gewollt, aber nur zufällig richtig).

## Was Lukas noch tun muss
1. **R2 in der EU:** im Cloudflare-Dashboard die Buckets `hb-videos` und `hb-artifacts` mit Jurisdiktion
   **EU** anlegen und auf `hb-videos` CORS setzen (Origin `https://test.handball-intelligence.com`, Methoden
   PUT, GET, HEAD, Header `*`, ETag freigeben). Oder dem R2-Token "Admin Read & Write" geben, dann macht es
   der Migrations-Job. Danach in `terraform.tfvars` den `.eu.`-Endpoint und die Bucket-Namen zurücksetzen.
   **Ohne CORS geht der Upload aus dem Browser nicht** (Skripte und die API gehen).
2. **Postmark** (oder ein anderer SMTP-Anbieter): Konto anlegen, Domain bestätigen (SPF, DKIM, DMARC bei
   Cloudflare), Server-Token als `smtp_username` und in den Key Vault (`hb-smtp-password`), dann
   `extra_env` ohne `HB_EMAIL_BACKEND` und `terraform apply`.
3. Selbst registrieren mit `lukasdech@gmx.de` (steht in `operator_emails`), den Bestätigungs-Link findet
   die Sitzung im Log, solange Mail auf `console` steht.

## Pausieren und wieder starten
Die Umgebung ist pausiert (`paused = true`, Postgres gestoppt). Wieder starten aus `infra/terraform/azure`:

```bash
az postgres flexible-server start -g rg-hb-stg -n psql-hbstg1tovl
```

Dann in `terraform.tfvars` `paused = false` setzen und `terraform apply`. Pausieren umgekehrt. Azure startet
einen gestoppten Postgres nach 7 Tagen von selbst wieder.

## Kosten (grob)
Pausiert: Registry ~ CHF 5, Postgres-Speicher ~ CHF 4, Rest Rappen. Laufend kommen Postgres-Rechenzeit
(~ CHF 13 pro Monat) und die Container dazu (gpu-worker 2 vCPU, 4 GiB ist der grösste Posten).

## Hinweise zum Arbeiten von Lukas' PC aus
- Kein Admin: Azure CLI als ZIP unter `%LOCALAPPDATA%\Programs\AzureCLI`, kein Docker (darum `az acr run`).
- Firmen-Proxy (Qualys) prüft TLS mit: der Azure CLI das Windows-Zertifikat mitgeben (`REQUESTS_CA_BUNDLE`).
- Das Verzeichnis hat Sicherheitsstandards: Anmeldung mit Code reicht nicht für Key Vault und Storage, es
  braucht `az login` im Browser mit MFA.
- PowerShell 5.1: Terraform-Argumente mit `=` und Punkt in Anführungszeichen setzen (`'-out=x.tfplan'`).
