# Backlog und Prioritäten (Backend und Analyse)

Stand 2026-11-05. Ziel des Produkts: Video hochladen, automatisch die Schlüsselsituationen
(Tore, Würfe, wer den Ball hat, wohin der Wurf geht, Spielzüge) und pro Spieler auswerten. Die UI
macht eine eigene Sitzung (`docs/plans/ui-match-workspace.md`).

## Läuft gerade
| Thema | Stand |
|---|---|
| Würfe als Vorschläge (wie Torkandidaten) | Messung und Einbau laufen |
| Mannschaft aus handball.ch übernehmen (Phase 1 bis 3) | Backend fertig (64bade8, fab3011), UI-Sitzung baut die Screens |
| 1. Kalibrierung für Stream-Kameras | läuft (messen, dann verbessern, Klick-Kalibrierung pro Halle) |
| 6. Spielberichte per Link aus nuLiga (DE, AT) und HLA-PDF | läuft |
| Backend-Prüfung auf Fehler bei echtem Material (Teil-Videos, ganze Spiele, Rechte) | läuft, erste Fixes gepusht |
| Torkandidaten im Produktpfad messen | läuft |
| Uploads von Lukas verarbeiten, schneller machen | läuft |
| Ball Runde 5 / 5b (OWLv2-Labels) | Kaggle, Auswertung danach |

## Als Nächstes (Reihenfolge)
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
4. **Ball Runde 6** mit OWLv2-Labels aus den neuen Spielen (Modal über die lokale Sitzung), danach
   "Wer hat den Ball" pro Spieler neu trainieren.
5. **Rückennummern breit messen** auf den neuen Spielen mit Matchblatt (ab 2023/24), Schwellen
   einstellen; Spieler-Statistik aus bestätigten Ereignissen prüfen.
6. **Spielberichte per Link aus nuLiga (DE, AT) und HLA-PDF (AT)** importieren, ohne Vertrag
   (`docs/plans/data-sources-de.md`).
7. **Spielzüge.** Angriffe gibt es schon als Phasen; erkennen, welche Auslösung gespielt wurde
   (Muster in den Spuren), Verknüpfung mit dem Taktikboard. Braucht 1 und 4.

## Reihenfolge der Starts
2 (ganzes Spiel) sobald die Upload-Verarbeitung fertig ist; 3 (Torzone) nach den Würfen;
4 (Ball Runde 6) nach der Auswertung von Runde 5 als Auftrag in `ml/gpu/JOBS.md`; 5 (Nummern) wenn
genug hochgeladene Spiele mit Matchblatt verarbeitet sind; 7 (Spielzüge) nach 1 und 4.
Kleine Lücke aus dem Onboarding: Namen offizieller Kader-Einträge ohne Einwilligung auch in
Ereignis- und Statistik-Ansichten verbergen (mit 5).

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

## Nach dem Merge der UI-Branch
- `apps/api/tests/test_report_pdf.py::test_insight_texts_match_the_web_app` wieder für
  `zones.long_range` und `zones.empty_goal` einschalten: die Web-Texte sind im UI-Branch
  `claude/exciting-franklin-g1ecgw` angepasst; die Prüfung erst nach dessen Merge in main scharf
  stellen, sonst schlägt sie im Backend-Branch fehl.

## Später / wartet
- Datenanfragen DHB und BHV (Entwürfe in `docs/plans/outreach-data-de.md`), Partnerschaft SHV.
- Eigenes ReID-Modell statt MSMT (Lizenz) vor einem kommerziellen Start.
- Rollen-, Holder- und Ballmodelle nur mit kommerziell nutzbaren Daten neu trainieren (ADR 003).
