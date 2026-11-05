# Backlog: Vereine und Mannschaften aus den offiziellen Daten (CH zuerst, dann DE)

Stand 2026-11-05, Idee von Lukas, noch nicht umgesetzt. Ziel: Ein Trainer sucht "Thalwil", wählt
"Herren 1" aus der Liste der gemeldeten Mannschaften, und die App ist sofort mit Spielplan,
Gegnern, Hallen, Kader-Vorschlag und vergangenen Spielberichten befüllt. Spieler ordnen sich ihrer
Mannschaft zu, statt dass alles von Hand erfasst wird.

## Was es schon gibt
- handball.ch Matchcenter (öffentliche GraphQL-Schnittstelle): Vereine, Mannschaften, Ligen,
  Spiele mit Datum, Halle, Resultat, Spielprotokoll, Spielerstatistik mit Rückennummer (ab
  Saison 2023/24). Abruf im Repo: `ml/eval/fetch_handball_ch.py`, `ml/data/match_official.py`,
  Import pro Spiel: `apps/api/.../services/official_report.py`.
- DE: DHB-Spielberichte (PDF, sportradar) nur für die oberen Ligen; handball.net blockt
  automatische Abrufe (Cloudflare). Regionale Ligen (nuLiga/Handball4all) noch nicht geprüft.
- In der App: Organisation, Teams, Saisons, Kader, Einladungen (Trainer lädt Spieler ein),
  Verbandslizenzen (`services/federation.py`), Einwilligungen pro Spieler.

## Ablauf (Vorschlag)
**Phase 1: Trainer übernimmt eine gemeldete Mannschaft**
1. Registrieren, dann "Mannschaft suchen": Vereinsname oder Ort, Treffer aus handball.ch
   (Verein, Mannschaften mit Liga der aktuellen Saison).
2. Auswahl legt Organisation und Team an, verknüpft mit den offiziellen IDs (Verein, Mannschaft,
   Gruppe/Liga, Saison) und füllt vor:
   - Spielplan der Saison (Datum, Gegner, Heim/Auswärts, Halle), Resultate und Tabelle;
   - Kader-Vorschlag aus der Spielerstatistik (Name, Rückennummer, Einsätze), vom Trainer zu
     bestätigen, nicht automatisch sichtbar für andere;
   - vergangene Spiele mit Spielprotokoll als importierbare Berichte (Tore, Strafen, Schützen).
3. Nach jedem Spiel automatisch: Resultat, Spielprotokoll importieren, mit dem Video abgleichen
   (das gibt es schon pro Spiel, hier nur der automatische Auslöser).

**Phase 2: Spieler ordnen sich zu**
- Weg A (gibt es schon): Einladungslink vom Trainer.
- Weg B (neu): Spieler sucht die Mannschaft und stellt eine Beitrittsanfrage; die App schlägt
  den passenden Kader-Eintrag vor (Name, Nummer), der Trainer bestätigt mit einem Klick.
- Eltern bei Junioren nur über den Trainer (bestehende Familienfunktion).

**Phase 3: Laufender Abgleich**
- Täglicher Abgleich: neue Spiele, verschobene Termine, Kaderänderungen als Vorschläge.
- Saisonwechsel: neue Mannschaft/Liga zur gleichen Vereins-ID vorschlagen.

## Wer darf einen Verein oder eine Mannschaft anlegen?
Vorschlag:
- Pro offizieller Vereins-ID nur eine Organisation in der App. Wer einen schon übernommenen Verein
  sucht, stellt eine Zugangsanfrage an dessen Admins statt einen zweiten anzulegen.
- Die erste Person legt an und ist Admin, der Verein bleibt "nicht bestätigt", bis eins davon
  vorliegt: Mail-Adresse mit der Domain des Vereins, Bestätigung durch eine zweite Person mit
  Vereinsfunktion, Verbandslizenz (bestehend), oder Prüfung durch uns.
- Nicht bestätigte Vereine können alles nutzen, aber keine Daten von Spielern anderer Teams
  sehen und nichts öffentlich teilen.
- Mannschaften ohne offizielle Meldung (Plausch, Training, Auswahl) weiter von Hand.

## Datenschutz
Offizielle Daten sind öffentlich, aber Namen von Spielerinnen und Spielern (oft minderjährig)
werden in der App nur als Vorschlag für den Trainer genutzt, bis die Person beitritt oder ihre
Einwilligung vorliegt (bestehende Einwilligungs-Logik). Keine öffentlichen Spielerprofile aus
offiziellen Daten.

## Offene Fragen (Lukas)
1. Nutzung der handball.ch-Schnittstelle im Produkt: Sie ist öffentlich, aber nicht dokumentiert.
   Für den Betrieb besser eine Erlaubnis oder Partnerschaft mit dem SHV einholen.
2. ~~Wer bestätigt Vereine~~: entschieden, siehe unten.
3. Deutschland: Welche Quelle? DHB nur oben; regional nuLiga/Handball4all prüfen, oder in DE zuerst
   ohne Vorbefüllung starten.
4. ~~Kader-Vorschlag mit Statistik~~: entschieden, siehe unten.

## Entscheide (Lukas, 2026-11-05)
1. **Übernommene offizielle Spiele zählen zur Spiel-Limite des Plans.** Gratis-Plan: 2 Spiele pro
   Saison und Mannschaft. Mit eingeschalteter Abrechnung (`HB_BILLING_ENFORCE`) legt die Übernahme
   (und jede Erstbefüllung, auch bei neuer Saison oder genehmigter Zugangsanfrage) Spiele nur bis
   zur Limite an: zuerst die nächsten anstehenden Spiele, dann die zuletzt gespielten. Die übrigen
   werden Vorschläge `match_new` mit `reason: "plan_limit"`; solange die Limite erreicht ist, zeigt
   die Vorschlagsliste `blocked: "plan_limit"` und Annehmen gibt 402 `plan-limit-matches`. Nach
   einem Upgrade lassen sie sich annehmen (gespielte Spiele bringen Resultat und Spielbericht als
   Vorschlag mit). Die Antwort der Übernahme meldet `prefill.matches_held_back`. Ohne Abrechnung
   wie bisher (alle Spiele). Umsetzung: `services/official.py` (`_held_back`), `billing.matches_left`.
2. **Vereins-Bestätigung bleibt grosszügig.** Eine zweite Person mit Vereinsfunktion (Vereins-Admin
   oder Trainer, nicht die Person, die übernommen hat, mit bestätigter Mail-Adresse) genügt; keine
   Vereins-Domain nötig und keine Prüfung jedes Vereins durch uns. Die übrigen Wege (Mail-Domain
   des Vereins, Verbandslizenz, Prüfung durch uns) bleiben zusätzlich. So umgesetzt in
   `services/org_verification.py`, keine Änderung nötig.
3. **Kader-Vorschlag mit wählbarer Statistik.** Name, Rückennummer und Einsätze wie bisher, dazu
   im Vorschlag `stats` aus der offiziellen Spielerstatistik, soweit vorhanden: Spiele, Tore, 7-m-Tore
   und -Versuche, 2-Minuten-Strafen, bei Torhütern Paraden und Würfe aufs Tor (`null`, wo handball.ch
   keinen Wert liefert; `stats` null ohne Einsatz). Gerechnet über die gelesenen Spiele der laufenden
   Saison (die letzten 10 gespielten, wie die Einsätze). Der Trainer entscheidet in der UI, ob sie
   angezeigt werden; die Wahl gilt pro Mannschaft für alle ihre Organisatoren
   (`PATCH .../official {roster_stats}`, Standard aus). Datenschutz unverändert: Vorschläge sehen
   nur die Organisatoren der Mannschaft. Statistik der Vorsaison (andere offizielle Team-ID) ist
   noch nicht drin.

## Technische Skizze
- Neue Felder: `organizations.official_ref` (Anbieter, Vereins-ID), `teams.official_ref`
  (Mannschafts-ID, Gruppen-ID, Saison), `matches.official_game_id`; eindeutig pro Anbieter+ID.
- Suchendpunkt `GET /v1/official/teams?q=` (Cache, kurze Antwortzeit, Rate-Limit gegenüber
  handball.ch), Übernahme `POST /v1/official/teams/{id}/claim`, Beitrittsanfragen
  `POST /v1/teams/{id}/join-requests`, Abgleich als Job im Worker (täglich).
- Wiederverwendung: Abruf und Parser aus `fetch_handball_ch.py` / `official_report.py` in ein
  gemeinsames Modul `handball_api/integrations/handball_ch.py` ziehen.
