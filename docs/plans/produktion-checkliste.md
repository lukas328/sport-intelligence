# Produktion: Checkliste für Lukas

Ziel: die App als Pilot auf Azure (Schweiz Nord) unter deiner Domain, Videos auf Cloudflare R2.
Technische Anleitung: `infra/terraform/azure/README.md` (PR 7). Kosten Pilot: etwa CHF 40–80 pro Monat.

**Wichtig zu Geheimnissen:** Keine Passwörter, Tokens oder Schlüssel in diese Datei, ins Repo oder in
einen Chat. Sie kommen nur an zwei Orte:
- in `terraform.tfvars` und `backend.hcl` **auf deinem Computer** (beide sind vom Repo ausgeschlossen),
  und das nur für die nicht-geheimen Werte unten;
- in den **Azure Key Vault**, eingetippt mit `read -rsp` (siehe README Schritt 4), für die geheimen.

Ausgeführt wird alles am besten von **deiner lokalen Claude-Sitzung**: Azure-Anmeldung, Terraform und
Docker laufen auf deinem Computer. Gib ihr: "Lies docs/plans/produktion-checkliste.md und
infra/terraform/azure/README.md und führe mich durch das Pilot-Deployment."

## 1. Entscheide (bitte hier eintragen)
| Frage | Antwort |
|---|---|
| Domain der App (z. B. `app.deinedomain.ch`) | |
| Absender-Mail (z. B. `noreply@deinedomain.ch`) | |
| Wer bekommt Kosten- und Störungs-Mails | |
| Was geht zuerst live: nur Website / App für Test-Trainer / mit Video-Analyse | |
| Monatliches Kostenlimit Azure (Standard 80) | |

## 2. Konten und Werkzeuge (abhaken)
- [ ] Azure-Konto mit Abonnement (hast du)
- [ ] Domain bei Cloudflare, DNS bei Cloudflare (hast du)
- [ ] Cloudflare R2 aktiviert (im Cloudflare-Dashboard unter R2)
- [ ] Mail-Anbieter mit SMTP, Vorschlag Postmark (ADR 009), Domain dort bestätigt (SPF, DKIM, DMARC)
- [ ] Auf deinem Computer: Azure CLI, Terraform ≥ 1.9, Docker Desktop

## 3. Werte sammeln (nicht geheim, kommen in `terraform.tfvars` auf deinem Computer)
| Wert | Woher |
|---|---|
| `subscription_id` | `az account show --query id -o tsv` nach `az login` |
| `app_domain` | Entscheid oben |
| `alert_emails`, `operator_emails` | Entscheid oben |
| `s3_endpoint_url` | Cloudflare R2: `https://<account-id>.eu.r2.cloudflarestorage.com` |
| `s3_access_key` | Cloudflare R2 → API-Token erstellen → "Access Key ID" |
| `email_from` | Entscheid oben |
| `smtp_host`, `smtp_port` | Postmark: `smtp.postmarkapp.com`, 587 |
| `smtp_username` | Postmark: Server-Token |
| `storage_account_name` (in `backend.hcl`) | README Schritt 2 erzeugt ihn |

## 4. Geheimnisse (nur in den Key Vault eintippen, README Schritt 4)
| Name im Key Vault | Woher |
|---|---|
| `hb-s3-secret-key` | Cloudflare R2 → derselbe API-Token → "Secret Access Key" |
| `hb-smtp-password` | Postmark: Server-Token (Postmark nutzt ihn als Passwort) |
| später optional: Google-/Apple-Login, Stripe, Anthropic-API, Sentry | README "Optional settings" |

## 5. Ablauf (die lokale Sitzung führt dich durch)
1. `az login`, Abonnement prüfen.
2. Speicher für den Terraform-Zustand anlegen (README Schritt 2), `backend.hcl` und `terraform.tfvars` ausfüllen.
3. Registry und Key Vault anlegen, die vier Images bauen und hochladen (README Schritt 3).
4. Die zwei Geheimnisse in den Key Vault tippen (Schritt 4).
5. `terraform apply`, danach den Migrations-Job starten (Schritt 5).
6. DNS bei Cloudflare: CNAME und TXT für die Domain (Schritt 6), Zertifikat binden.
7. Erster Login, Verein anlegen, ein Testvideo hochladen.

## 6. Was danach noch fehlt (macht die Haupt-Sitzung)
- Automatisches Deployment per GitHub Actions (statt Images von Hand).
- Video-Analyse mit GPU: im Pilot rechnet die Analyse auf der CPU (langsam). Für Tempo braucht es einen
  GPU-Anbieter (z. B. Modal); das ist noch nicht eingebaut.
- Backups ausser Haus und Alarme (`infra/monitoring/alerts.md`).
- Datenschutz-Texte und Impressum auf der Domain.
