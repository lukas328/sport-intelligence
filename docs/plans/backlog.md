# Backlog und Prioritäten (Backend und Analyse)

Stand 2026-11-09. Ziel des Produkts: Video hochladen, automatisch die Schlüsselsituationen
(Tore, Würfe, wer den Ball hat, wohin der Wurf geht, Spielzüge) und pro Spieler auswerten. Die UI
macht eine eigene Sitzung (`docs/plans/ui-match-workspace.md`).

## Läuft gerade
Stand 2026-11-19: Prioritäten in `docs/plans/HANDOVER.md`, Entscheide und Änderungen vom 19.11. in
`docs/plans/UEBERGABE-2026-11-19.md`. Die Liste "Als Nächstes" unten ist vom 9.11.; Punkt 1
(Kalibrierung) ist jetzt die Klick-Kalibrierung pro Halle, Punkt 2 (ganzes Spiel) ist auf Staging
gelaufen (99 min), die GPU-Frage ist entschieden (später Azure).

Stand 2026-11-09: `docs/plans/HANDOVER.md` (Verlauf). Fertig seit dem 5.11.:
Würfe als Vorschläge, Mannschaft aus handball.ch (Phase 1 bis 3), Spielberichte per Link (nuLiga,
HLA), Kalibrierung mit Gründen und Hallen-Wiederverwendung, Rückennummern breit gemessen,
Code-Prüfung vor der Übergabe. Ball Runde 6: gleichauf mit Runde 3, nicht übernommen.

## Nächste Aufgaben (Stand 20.11., nach PR #105)
Die eine Liste für alle Sitzungen. Wer etwas anfängt, schreibt «läuft (Sitzung, Datum)» dazu; wer
fertig ist, streicht es und trägt das Ergebnis im passenden Plan ein.

**A. Aus der Cloud-Sitzung machbar (Hauptsitzung)**
1. **Weniger Fragen: bessere Tor-Kandidaten.** *20.11.: Ballpfad als Bestätigung geprüft, hilft nicht (AUC 0.81 mit und ohne Ball, Dev, `produkt-analyse-integration.md` «Ballpfad als Bestätigung»). Offen bleibt die Zeit ohne Spiel; Daten dafür kommen aus `observe_queue`. 25.11. Pausen Variante 2 gemessen (Dev, 65 Segmente): die Halbzeitpause nennt das Produkt zu 98 % Spiel, Hebel ist «keine laufende Uhr über Minuten = Pause». 23.11.: rund 160 von 860 Segmenten beobachtet; für die Pausen-Messung fehlt der Entscheid Hallentafel in der Warteschlange (empfohlen) oder nur Dev-Spiele mit Uhr aus dem Bericht (`UEBERGABE-2026-11-23.md`).* Präzision heute 29 %, auf Lukas' 99-min-Video 122
   Fragen. Die Regel «Tore aus dem Spielbericht» spart kaum Fragen (Kandidaten nahe Berichtstoren
   waren schon verdeckt). Hebel: Pausen, Einspielen und Nachspiel ohne Fragen (Pausenerkennung ohne
   Hallentafel über die `no_play`-Regel), Tor-Kandidaten mit Ballpfad bestätigen. Braucht für die
   Messung Daten von Kaggle oder Staging.
2. **Wurfort-Schätzung messen.** *25.11. (Analyse-Sitzung): kein Staging-Zugang aus der Cloud; dazu werden abgelehnte Schätzungen nicht gespeichert, die Trefferquote ist so nicht rechenbar. Vorschlag `attributes.estimated_zone` (`produkt-analyse-integration.md`, «Wurfzeit auf Dev, Fehlalarme und Pausen» Punkt 5).* Seit A22 werden bestätigte Schätzungen als
   `attributes.confirmed_estimate` gespeichert; daraus die Trefferquote der Schätzung auswerten
   (Staging-Daten), dann entscheiden, wann der Wurfort ganz automatisch sein darf.
3. **Spieltag neu denken (A21).** Seit Runde 4 aus der App genommen; Konzept mit Lukas: was der
   Trainer am Spielfeldrand wirklich erfasst.
4. **Go-live-Punkte mit Code** (`GO_LIVE.md`): ~~HLS-Segmente direkt aus R2~~ erledigt 20.11.
   (`HB_MEDIA_DIRECT`, ADR 002 Nachtrag; Lukas: R2-CORS-Regel prüfen, README Azure Schritt 7); Overlays im Player für bewegte Kameras (ADR 020); Alarme und Proben im
   Monitoring vorbereiten.
5. **Europa Schritt 2 vorbereiten** (`docs/plans/europa.md`): Währung EUR in Abrechnung und Rechnung
   (heute nur CHF), `de-DE` erst mit dem ersten deutschen Verein.

**B. Braucht Lukas oder die lokale Sitzung**
1. Kalibrierung per Klick Ende-zu-Ende auf Staging mit echtem Clip, danach Deploy
   (`docs/plans/kalibrierung.md` Abschnitt 6).
2. Wurfzeit: Lukas markiert die Abwürfe der 175 Dev-Würfe auf der Seite «Abwürfe Dev»
   (https://claude.ai/artifact/X1AUB2nXAkX9eVTV977paz, etwa 45 min); danach Methode auf Dev wählen,
   Auswertung bereit (`ml/integration/shot_time_dev.py eval`). Vorprüfung gegen die Spielbericht-Zeit:
   Ballpfad-Anker nicht genauer, Ballpfad senkt die Wurf-Fehlalarme nicht (25.11.).
3. Ball: Fehlalarme zerlegt (25.11., Lukas' 574 Urteile auf den Dev-Wurfclips ausgewertet: Tracker nur
   37 % richtig, falsche Punkte vor allem Personenteile und Gegenstände an der Bank;
   `ml/ball/LINEAGE.md` Abschnitt 6). Offen: Lukas schaut die 111 Punkte nochmals an, die nach Ball
   aussehen; neues Testset ohne Ringe mit Bildern ohne Ball (Kaggle-Zugang in der Cloud geht wieder).
4. Echter Handy-Test (iPhone, Android) von Website und App.
5. Entscheide: Saison-Titel als Geschichte oder «Fakten zuerst» (TXT-08); mehr als drei Muster pro
   Spiel; Launch zur Rückrunde im Januar; die 🔴-Punkte in `docs/OPEN_QUESTIONS.md` (Firma, Recht,
   Einwilligung Jugend, AVV).
6. GPU auf Azure mit Umzug der Region (Lukas, später).
7. R2-CORS-Regel auf `hb-videos` (GET, HEAD, PUT von der App-Domain), sonst spielen Safari und Chrome
   die Videos nicht direkt aus R2; Anleitung `infra/terraform/azure/README.md` Schritt 7.

## Als Nächstes (Stand 2026-11-09, Verlauf)
1. **Kalibrierung für Stream-Kameras.** Auf allen vier geprüften Wädenswil/Horgen-Clips scheiterte
   die automatische Spielfeld-Erkennung (flache Sicht). Ohne Spielfeld keine Positionen, kein
   Ballbesitz pro Team, kein Bank-Filter, schlechtere Nummern. Erst messen, wie oft das auf allen
   hochgeladenen Spielen passiert, dann verbessern oder die Klick-Kalibrierung pro Halle einmal
   machen und für alle Spiele dieser Halle wiederverwenden.
2. **Ein ganzes Spiel end-to-end.** Ein 60-Minuten-Spiel echt durch Upload, Analyse, Torkandidaten,
   Würfe, Nummern und offiziellen Bericht laufen lassen: Dauer, Speicher, Fehler. Dazu die Frage,
   wo die Analyse im Betrieb rechnet (GPU-Worker: Kosten pro Spiel).
3. **Wohin der Wurf geht.** Beim Bestätigen eines Tors oder Wurfs die Torzone mit einem Klick
   erfassen (Raster 3x3), Wurfposition auf dem Feld aus den Spuren; Auswertung pro Spieler und
   Torhüter. Automatische Torzone erst, wenn der Ball gut genug ist.
4. **Ball:** Runde 6 (OWLv2-Labels) liegt gleichauf mit Runde 3 (33 %). Zuerst das Testset auf etwa
   200 Bälle vergrössern, dann weiter trainieren und "Wer hat den Ball" pro Spieler neu trainieren.
5. **Rückennummern**: breit gemessen (2026-11-09, 12 Spiele aus mindestens 11 Hallen, ADR 027):
   94 % der gelesenen Nummernzeit auf dem Matchblatt, Rollen-Schwelle der ReID 0.75 -> 0.45,
   Farb-Schwellen bleiben. Offen: Spieler-Statistik aus bestätigten Ereignissen prüfen;
   Schiedsrichter und Staff am Spielfeldrand in TV-Streams (Schweiz - Island: halbe Nummernzeit).
6. **Spielberichte per Link aus nuLiga (DE, AT) und HLA-PDF (AT)** importieren, ohne Vertrag
   (`docs/plans/data-sources-de.md`).
7. **Spielzüge.** Angriffe gibt es schon als Phasen; erkennen, welche Auslösung gespielt wurde
   (Muster in den Spuren), Verknüpfung mit dem Taktikboard. Braucht 1 und 4.

## Reihenfolge der Starts
2 (ganzes Spiel) sobald die Upload-Verarbeitung fertig ist; 3 (Torzone) nach den Würfen;
4 (Ball Runde 6) nach der Auswertung von Runde 5 als Auftrag in `ml/gpu/JOBS.md`; 5 (Nummern) wenn
genug hochgeladene Spiele mit Matchblatt verarbeitet sind; 7 (Spielzüge) nach 1 und 4.
Kleine Lücke aus dem Onboarding: Namen offizieller Kader-Einträge ohne Einwilligung in Ereignis-
und Statistik-Ansichten verbergen: erledigt (Ereignisliste, Tor-Abgleich, Wurf-Vorschläge,
PDF-Bericht, Anwesenheitsliste für Analysten und Assistenztrainer; `roster.visible_players`).

## Entscheide von Lukas (offen)
- keine

## Entscheide von Lukas (entschieden, 2026-11-05)
- Übernommene offizielle Spiele zählen zur Spiel-Limite des Plans: bis zur Limite werden Spiele
  angelegt (nächste anstehende, dann zuletzt gespielte), der Rest wird Vorschlag mit Grund
  `plan_limit`, nach einem Upgrade annehmbar. Umgesetzt.
- Vereins-Bestätigung bleibt grosszügig: eine zweite Person mit Vereinsfunktion (Admin oder
  Trainer) genügt, keine Vereins-Domain, keine Prüfung durch uns. So umgesetzt.
- Kader-Vorschlag: Name, Nummer, Einsätze und dazu wählbare Statistik (Tore, 7 m, 2 Minuten,
  Spiele, Paraden bei Torhütern); der Trainer blendet sie in der UI ein oder aus. Umgesetzt.
  Details in `docs/plans/federation-onboarding.md` (Entscheide).

## Aus der Code-Prüfung (2026-11-05)
1. Erledigt (2026-11-09): Indizes auf die neuen Fremdschlüssel (`goal_candidates.event_id` und
   `reviewed_by_id`, join/access requests, suggestions, `organizations.claimed_by_id`), Migration
   0034; Test: keine Fremdschlüssel ohne Index in diesen Tabellen.
2. Erledigt (2026-11-09): `run_due` mit Savepoint pro Team und Spiel (ein Fehler rollt nur dieses
   zurück, Team erst wieder beim nächsten Tagesabgleich); Spiele ohne Protokoll werden nach 1, 2,
   4, ... bis 24 Stunden wieder gefragt (`matches.official_report_tries`/`_retry_at`, Migration
   0035), das jüngste Spiel zuerst.
3. Erledigt (2026-11-09): Doppelklick auf Beitritts-/Zugangsanfragen gibt 409 (Anlegen: Savepoint
   und IntegrityError; Entscheiden und Zurückziehen: Zeilensperre FOR UPDATE).
4. Erledigt (2026-11-09): `official_cache` hält Antworten einen Monat, Spieler-Statistik eines
   Spiels ein Jahr; der stündliche Abgleich löscht ältere.
5. Erledigt (2026-11-09): `team_data.load` liest die gewünschten Saisons (Matrix: `season_ids`,
   sonst aktuelle und letzte Saison) und nur die nötigen Spalten; `timeline_videos` ohne die
   Analyse-JSON (Formationen per `analysis->formations`); `halls.references` per DISTINCT ON.
6. Erledigt (2026-11-09): `_download` folgt nur Weiterleitungen auf denselben https-Host und Port;
   der handball.ch-Client reserviert Startzeiten statt eine Sperre über den HTTP-Aufruf zu halten;
   Videolänge einmal pro Spiel gelesen (`feed.generate`, dort lag die Abfrage pro Eintrag) und
   die Clips von Fokus und Feed in einem Schritt gespeichert.
7. Echte Spielernamen im Repo: `ml/data/official/*.json` (öffentliche Spielprotokolle).
   Entschieden (Lukas, 2026-11-05): bleiben vorerst im Repo, die Daten sind öffentlich online;
   Repo bleibt privat. Test-Fixtures nutzen weiter erfundene Namen.

## Code health (from the review before handover)
Kleine Fixes aus dem Review sind im Branch `chore/backend-cleanup` erledigt (GPU-Minuten,
blockierende Aufrufe, ffmpeg-Timeouts, gemeinsame SSRF-Prüfung, Fixture-Namen, Media-Helfer,
Reporter, doppelte Helfer, Doku, Worker-Settings, Job-Vertragstest). Offen, für später:

1. ~~`services/official_report.py` aufteilen~~ **erledigt** (Branch `helper/split-official-report`):
   Parser und Abrufe in `integrations/official_reports/` (`base`, `handball_ch`, `dhb`, `nuliga`,
   `hla`, `http`, Quellenerkennung `locate`/`detect` im `__init__`); Vergleich und Prüfung in
   `services/official_comparison.py`; `apply` in Schritte zerlegt (`_known`, `_add_entries`,
   `_settle_video_goals`, `_write_result`). `official_report` exportiert weiter alle Namen, die
   Code und Tests nutzen; die Abruffunktionen und `_pdf_text` bleiben dort ersetzbar.
2. ~~Totes Gerüst löschen~~ **erledigt**: `handball_worker/pipeline/` sowie `jobs.py` und
   `backends/` im GPU-Worker sind weg, samt ihren Tests. Der Integrationstest prüft die GPU-Queue
   mit einer gewöhnlichen Funktion. `HB_GPU_BACKEND` bleibt in Einstellungen und Infra stehen
   (Schalter für ein späteres Modal-Backend, ADR 025), wird aber heute nicht gelesen.
3. ~~Systemzugriff als Kontextmanager~~ **erledigt**: `async with system_access(ctx.db,
   reason=...)` in `core/db.py` schaltet die RLS-Umgehung beim Verlassen des Blocks wieder aus,
   auch bei einer Ausnahme; jede Umgehung loggt ihren Grund (`system_access`). Umgestellt sind
   die ungeschützten Paare (sessions, sharing, consent_links, videos, profiles, federation, orgs,
   Watchdog in progress) und der Mahnlauf, der jetzt einmal für den ganzen Lauf statt in der
   Schleife einschaltet. Stellen mit try/finally und `invitations._by_token` (über mehrere
   Funktionen) bleiben wie sie sind.
4. ~~`services/official.py` aufteilen~~ **erledigt**: Paket `services/official/` mit `claim`
   (Suche und Übernahme), `sync`, `suggestions`, `access` (Zugangsanfragen) und `_base`
   (Einstellungen); der Worker-Tick bleibt im `__init__`, das alle bisherigen Namen exportiert
   (Tests ersetzen `sync_team`, `import_report` und `REPORT_BATCH` dort).
5. ~~`services/videos.py` aufteilen~~ **erledigt**: Nachbarmodule `video_uploads`, `video_jobs`,
   `video_callbacks`, `video_media`, `video_analysis`, `video_tracks` und `video_base`.
   `apply_job_update` wertet über `ON_SUCCEEDED`/`ON_FAILED` je Job-Art aus. Die Importe in
   Funktionen (progress, highlights, graphics, marks, shot_positions, goal_candidates) stehen
   jetzt oben, ebenso `media_prefix`/`job_budget_s` in highlights, halls, shot_positions,
   graphics und progress. `videos.py` exportiert alle Namen und behält den Link-Import.
6. ~~`handball_vision/pipeline.py` aufteilen~~ **erledigt**: gemeinsames `_track_frames` für
   feste und bewegte Kamera, Video lesen in `video_io.py`, Zuordnung über Nummern und Aussehen
   in `identity.py`; `pipeline` exportiert die Namen weiter.
7. ~~`workspace.tsx` zerlegen~~ **erledigt**: `analysis-panel.tsx`, `identity-panel.tsx` (mit
   `ownTracks`), `camera-switch.tsx` und `formations-card.tsx` neben der Werkbank; das Laden
   (Kommentare, Clips, Zeichnungen, Analyse, Playlists, Ereignisse, Tor- und Wurfkandidaten,
   offizielle Tore) steckt im Hook `use-workspace-data.ts`. Texte und Test-IDs sind gleich
   geblieben, `workspace.tsx` hat noch gut 800 Zeilen.
8. ~~Gemeinsamer Helfer `run_artifact_job`~~ **erledigt**: `handball_worker/artifacts.py`
   (Arbeitsordner, Download, Upload, Rückmeldung an die API) für Export und Reels; die Reels
   nutzen damit auch `HB_WORK_DIR`.
9. ~~PDF-Erzeugung mit reportlab im Thread~~ **erledigt**: Spielbericht, Scouting, Präsentation,
   Trainingsplan und Rechnungen (Verein und Verband) laufen per `asyncio.to_thread`; die Daten
   werden vorher in der async-Funktion gelesen, `invoices.render_pdf` ist jetzt async.
10. ~~Kleine N+1-Abfragen~~ **erledigt**: Präsentations-Export liest Videos und die neuste
    Kalibrierung je Video in je einer Abfrage (die Dateien je Spiel einmal), `profiles.mine` die
    Profile, `official_report` die Wurfkandidaten beim Umhängen.
11. Die echten Namen sind aus `dhb_76839.txt` und `hla_70984286.txt` entfernt, stehen aber noch
    in der Git-Geschichte. Falls nötig vor einer Veröffentlichung des Repos die Geschichte
    bereinigen.

## Später / wartet
- Datenanfragen DHB und BHV (Entwürfe in `docs/plans/outreach-data-de.md`), Partnerschaft SHV.
- Eigenes ReID-Modell statt MSMT (Lizenz) vor einem kommerziellen Start.
- Rollen-, Holder- und Ballmodelle nur mit kommerziell nutzbaren Daten neu trainieren (ADR 003).
