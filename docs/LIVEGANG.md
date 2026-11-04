# Weg zum Livegang

Stand 2026-11-04. Checkliste für den Owner: was entschieden, gekauft, geprüft und gebaut werden muss, bis
die Plattform als stabile Web-App für echte Vereine läuft. Technische Details stehen in `GO_LIVE.md`
und `docs/OPEN_QUESTIONS.md`; diese Datei verweist dorthin.

**Für andere Sessions:** Wer einen Punkt erledigt, hakt ihn hier ab (☐ → ✅) und ergänzt `GO_LIVE.md`.

Legende: 🔴 blockiert den Livegang · 🟡 vor dem Pilot nötig · ⚪ kann warten · **Empfehlung** = mein Vorschlag

---

## 1. Entscheidungen, die nur du treffen kannst

| | Frage | Empfehlung | Warum es zählt |
|---|---|---|---|
| ☐ 🔴 | **Produktname** (Q-PROD-1) | Vor dem Domainkauf festlegen; "Handball AI" ist sehr nah an *handball.ai* (Markenrisiko) | Domain, App-IDs (`ch.handballai.app`), E-Mail-Absender und Store-Einträge hängen daran |
| ☐ 🔴 | **Firma** (GmbH, Einzelfirma?), MWST, Währungen CHF/EUR (Q-PROD-3, Q-ADD-3) | Firma vor dem ersten zahlenden Verein; Treuhand für MWST fragen | Impressum, Verträge, Stripe, QR-Rechnung (IBAN), Apple-Konto brauchen eine Firma |
| ✅ | Hosting | Azure West Europe für App, Datenbank, Secrets, Monitoring; Cloudflare R2 (EU) für Videos (ADR 002) | |
| ☐ 🟡 | **E-Mail-Anbieter** (Q-INFRA-3) | **Azure Communication Services** (alles in Azure, Daten in Europa, Kosten fast null) statt Postmark | Login-Links und Einladungen |
| ☐ 🟡 | **GPU** | **Zuerst ohne GPU**: Analyse auf CPU, etwa 2 × Videolänge (60-min-Spiel ≈ 2 h, grob 1 € pro Spiel). GPU später | GPU kostet mehr und ist schwerer zu beschaffen; für den Pilot reicht CPU |
| ☐ 🟡 | **Umgebungen** | Staging + Produktion; Staging skaliert nachts auf null | Neue Versionen erst auf Staging testen |
| ☐ 🟡 | **Preise** (Q-PROD-4) | Platzhalter in `packages/plans/plans.json` prüfen | Website und Abo-Seite zeigen sie |
| ☐ 🟡 | **Automatische Ereignisse zu schwach?** (Q-ADD-1) | Start mit "assistiert": Tore aus Live-Erfassung, Spielbericht oder Score-Einblendung; Automatik als Bonus | Bälle und Würfe erkennt die Analyse noch nicht |
| ☐ ⚪ | Handy-Apps zum Start oder später (Q-M11-3) | **Später.** Web-App läuft auf dem Handy; Apps nach dem Pilot | Apple 99 $/Jahr, Google 25 $ einmalig, Firmenkonto mit D-U-N-S-Nummer |
| ☐ ⚪ | Zusatzdienste (Q-ADD-4) | Zum Start keine: Fehler und Logs in Azure; Sentry, PostHog, Crisp, Statusseite später | Weniger Konten, weniger Datenschutz-Aufwand |
| ☐ ⚪ | KI-Funktionen (Q-M10-1, Q-M11-1) | Anthropic-Key erst, wenn Datenassistent oder Spielbericht-Foto gebraucht werden | Ohne Key sind sie aus, alles andere läuft |
| ☐ ⚪ | Kleinere Produktfragen | Q-AUTH-2 (2FA nach 14 Tagen), Q-ROLES-2 (wer wen einlädt), Q-LEGAL-2 (Jugend-Einwilligung durch den Verein), Q-LEGAL-3 (Rohvideo 24 Monate), Q-DATA-4 (Trainings-Opt-in) | Annahmen in `OPEN_QUESTIONS.md` bestätigen oder ändern |

## 2. Konten und Käufe

| | Was | Wo | Kosten (grob) | Wann |
|---|---|---|---|---|
| ☐ 🔴 | **Domain** | **Cloudflare Registrar** (Einkaufspreis, DNS gratis). Bietet Cloudflare die Endung nicht an (bei `.ch` prüfen): bei Infomaniak oder Hostpoint kaufen und die Nameserver auf Cloudflare stellen | 10 bis 40 € pro Jahr | Nach dem Namen |
| ☐ 🔴 | **Azure** | Subscription; ein Setup-Skript für die Cloud Shell (baue ich) richtet den Zugang für GitHub ein | siehe Abschnitt 5 | Vor dem ersten Deploy |
| ☐ 🔴 | **Cloudflare** | Konto, R2 aktivieren (Kreditkarte nötig, 10 GB gratis), API-Token erstellen | 0,015 $ pro GB und Monat, Auslieferung gratis | Vor dem ersten Deploy |
| ☐ 🟡 | **GitHub Secrets** | Repository → Settings → Secrets and variables → Actions: R2-Token. Azure braucht nur 3 nicht-geheime IDs (Anleitung folgt) | 0 | Vor dem ersten Deploy |
| ☐ 🟡 | **Firmen-Bankkonto** (IBAN für QR-Rechnung) | Bank | | Vor der ersten Rechnung |
| ☐ ⚪ | **Stripe** (Kartenzahlung, Q-BILL-1) | stripe.com, zuerst Testmodus | Gebühr pro Zahlung | Bevor du Geld verlangst |
| ☐ ⚪ | Google- und Apple-Login (Q-AUTH-1) | Google Cloud Console, Apple Developer | 0 bzw. 99 $/Jahr | Optional |
| ☐ ⚪ | Apple Developer, Google Play, Expo (Q-M11-3) | | siehe oben | Mit den Handy-Apps |

**Secrets:** Alles Geheime liegt in **Azure Key Vault**: Datenbank-Passwörter, App-Schlüssel, R2-Token,
Stripe-Keys. Die App-Schlüssel (`HB_SECRET_KEY`, `HB_ENCRYPTION_KEY`, `HB_INTERNAL_TOKEN`) und die
Datenbank-Passwörter erzeugt die Infrastruktur selbst; die musst du nie sehen. Kosten: wenige Cent im Monat.

## 3. Was du dir anschauen solltest

| | Was | Wo |
|---|---|---|
| ☐ 🔴 | **Lokaler Test mit einem echten Spielvideo** (läuft gerade): Analysedauer, Erkennung, Bedienung | `docker compose up -d --build`, dann http://localhost:3000 |
| ☐ 🔴 | **Rechtstexte durch eine Juristin oder einen Juristen prüfen lassen** (Videos von Minderjährigen!): AGB, Datenschutz, Impressum, Hallenhinweis, Einwilligungstexte | `apps/site/content/legal/`, `/{de,fr,en}/aufnahme/` |
| ☐ 🔴 | **Datenschutz-Folgenabschätzung** (Video von Minderjährigen) und Verzeichnis der Verarbeitungstätigkeiten | fehlt noch; Vorlage kann ich entwerfen |
| ☐ 🟡 | **Auftragsverarbeitungsverträge** (AVV/DPA) mit Microsoft, Cloudflare (und später Anthropic, Stripe) akzeptieren; Unterauftragsverarbeiter in die Datenschutzerklärung | jeweils im Konto |
| ☐ 🟡 | **Aufnahme-Anleitung** für Vereine (Kamera fest, ganzes Feld): ist sie verständlich? | Website `/de/aufnahme/`, Hilfe-Artikel |
| ☐ 🟡 | **Neues Design** (zwei laufende Branches, siehe Abschnitt 7) | Screenshots in `docs/design/identity/screens/` (Branch `vision/real-footage`) |
| ☐ 🟡 | **Usability-Test** mit 3 bis 5 Personen: 2 Trainer, 2 Spieler, 1 Elternteil (Q-UX-1) | Ablauf in `docs/progress/A4.md` |
| ☐ ⚪ | Lizenzen der Trainingsdaten (Q-ML-2), nur falls eigene Modelle trainiert werden | `ml/datasets/LICENSES.md` |

## 4. Was technisch noch fehlt (baue ich)

In dieser Reihenfolge. Nichts davon braucht eine Entscheidung von dir, ausser wo vermerkt.

| | Was | Warum |
|---|---|---|
| ☐ 🔴 | **Azure-Infrastruktur als Code** (`infra/terraform/azure`): Container Apps, Postgres mit Zeitpunkt-Wiederherstellung, Redis, Key Vault, Container Registry, Log Analytics, Budget-Alarm | `infra/terraform` ist noch leer |
| ☐ 🔴 | **Deploy-Workflow** in GitHub Actions: Images bauen, Migrationen, Staging, danach Produktion per Knopf | Es gibt nur `ci.yml` |
| ☐ 🔴 | **Cloud-Shell-Setup-Skript** für dich: GitHub-Zugang per OIDC, Speicher für den Terraform-Zustand | Damit du nur ein Skript ausführst |
| ☐ 🔴 | **Datenbank-Rolle `handball_app` in Produktion anlegen** (heute nur lokal per SQL-Datei) | Ohne sie schlagen die Migrationen fehl |
| ☐ 🔴 | **Videos direkt aus R2 ausliefern** (ADR 002 Punkt 7). Heute liefert der API-Server jedes Videosegment aus | Sonst bezahlst du den Video-Traffic doch bei Azure, und der Server wird zum Engpass |
| ☐ 🔴 | **R2-Anbindung für die App** (Buckets, CORS, `region=auto`, Prüfsummen-Einstellung für boto3) | Bisher nur für Testvideos benutzt |
| ☐ 🟡 | **E-Mail über Azure Communication Services** (SMTP-Konfiguration, DNS-Einträge SPF, DKIM und DMARC) | Entscheidung oben |
| ☐ 🟡 | **Platzhalter ersetzen**: Firmenname, Adresse und Beispiel-IBAN in `apps/api/src/handball_api/core/config.py`, Domain `handball-ai.ch` (web, site, mobile, Support-Adresse) | Braucht Name, Firma und Domain von dir |
| ☐ 🟡 | **Backups ausser Haus** (R2-Bucket mit Objektsperre), monatlicher Wiederherstellungstest, Alarme in Azure Monitor nach `infra/monitoring/alerts.md` | Backups der Datenbank sind in Azure eingebaut, die Kopie ausser Haus fehlt |
| ☐ 🟡 | **Marketing-Website** (`apps/site`, statisch) auf Cloudflare Pages oder Azure Static Web Apps (beide gratis) | |
| ☐ 🟡 | **Analyse-Worker** skaliert nur bei Arbeit hoch (pro Spiel bezahlen statt dauernd) | Kosten |
| ☐ ⚪ | Externer Penetrationstest auf Staging (Umfang in `docs/security/pentest-scope.md`) | Vor dem breiten Launch, nicht vor dem Pilot |
| ☐ ⚪ | GPU-Worker (CUDA-Image gibt es im Branch `vision/real-footage`) | Wenn 2 h pro Spiel zu langsam sind |

## 5. Infrastruktur auf einen Blick

| Teil | Wo | Grobe Kosten pro Monat (Pilot) |
|---|---|---|
| Web-App, API, Worker | Azure Container Apps | 30 bis 50 € |
| Videoanalyse | Azure Container Apps, nur bei Arbeit | etwa 1 € pro Spiel |
| Datenbank | Azure Database for PostgreSQL, kleinste Stufe, mit Backups | 15 bis 25 € |
| Redis (Job-Warteschlange) | Azure | 10 bis 15 € |
| Secrets | Azure Key Vault | unter 1 € |
| Images | Azure Container Registry Basic | etwa 5 € |
| Logs und Alarme | Azure Log Analytics / Monitor | 5 bis 10 € |
| E-Mail | Azure Communication Services | unter 1 € |
| Videos | Cloudflare R2 (EU) | 0 bis 15 € (1 TB ≈ 15 $), Auslieferung gratis |
| Domain und DNS | Cloudflare | 1 bis 3 € (Jahrespreis umgerechnet) |
| **Summe Produktion** | | **etwa 70 bis 120 €** |
| Staging zusätzlich | wie oben, kleiner, nachts aus | 30 bis 50 € |

Die Werte sind Schätzungen. Vor dem Bestellen prüfe ich sie mit dem Azure-Preisrechner und lege einen
Budget-Alarm an, der dich per Mail warnt.

**Warum nicht alles bei Cloudflare oder alles bei Azure?** Azure verrechnet jedes ausgelieferte GB,
R2 nicht. Videos sind der grösste Kostenblock, deshalb gehen nur sie zu Cloudflare. Alles andere ist auf
Azure, damit du eine Plattform für Betrieb, Secrets und Kosten hast. Die Domain kaufst du bei Cloudflare,
weil dort DNS gratis ist und sich die Video-Domain später einfach davorschalten lässt.

## 6. Reihenfolge

1. **Jetzt:** lokaler Test mit echtem Video (du). Name und Firma klären (du).
2. **Danach:** Domain kaufen, Azure- und Cloudflare-Konto (du, etwa 1 h). Gleichzeitig baue ich
   Infrastruktur, Deploy-Workflow, Videoauslieferung über R2 und E-Mail.
3. **Staging live:** Setup-Skript ausführen, Secrets eintragen (du, etwa 15 min). Ich deploye und teste.
4. **Vor dem Pilot:** Rechtstexte geprüft, AVVs akzeptiert, Usability-Test, Platzhalter ersetzt.
5. **Pilot:** 2 bis 3 Vereine, 4 Wochen (`GO_LIVE.md`, "Launch").
6. **Danach:** Zahlungen (Stripe), Handy-Apps, GPU, Pentest, Zusatzdienste.

## 7. Laufende Arbeiten in anderen Branches (Stand 2026-11-04)

- `vision/real-footage` (26 Commits vor `main`, enthält `identity/halle`): Analyse echter Videos (YOLOX-Detektor,
  automatische Kalibrierung, Tore aus der Score-Einblendung, CUDA-Image, ADR 024 bis 026) und das neue Design.
  **Muss noch nach `main`**; beim Mergen bitte diese Datei aktualisieren (GPU und Analysezeiten).
- `identity/halle`: neues visuelles Design, in `vision/real-footage` bereits enthalten.
- Hinweis: Es gibt zwei ADRs mit der Nummer 020 (`020-event-baseline.md`, `020-moving-cameras.md`).
