# Übergabe an die nächste Hauptsitzung

Stand 2026-11-09. Diese Datei ist der Einstieg für eine neue Claude-Sitzung. Erst diese Datei lesen,
dann `docs/plans/backlog.md`.

## Stand
- **main enthält alles.** PRs 2 bis 14 sind gemergt, keine offenen Branches mit Arbeit. CI ist grün
  und braucht pro PR etwa 7 Minuten (Python-Tests parallel, Caches, eigener Job für Lint und Typen).
- **Produkt:** Upload, Analyse (Spieler, Teams, Spielfeld, Torkandidaten, Würfe, Nummern, Ball als
  Forschung), offizielle Daten (Spielberichte per Link, Mannschaft von handball.ch übernehmen),
  Saison-Statistik, Berichte, Trainingsplanung, Abrechnung. Pilot-Infrastruktur für Azure liegt in
  `infra/terraform/azure/`, noch nicht ausgerollt.
- **Code-Prüfung vor der Übergabe** (PR 12, 13): die gefundenen Fehler sind behoben, die grösseren
  Umbauten stehen in `docs/plans/backlog.md` unter "Code health".

## Sitzungen und wer was macht
| Sitzung | Wo | Aufgabe |
|---|---|---|
| **Hauptsitzung** (Cloud) | dieses Repo | Backend, Analyse, Datenpipeline, Modell-Entscheide, PRs mergen, andere Sitzungen koordinieren |
| **UI-Sitzung** (Cloud) | dieses Repo | Web-App; Einstieg `docs/design/workspace/BACKLOG.md` ("Open after PR 8") und `docs/plans/ui-match-workspace.md` |
| **Lokale Sitzung** (Lukas' PC) | lokaler Klon | GPU-Aufträge auf Modal (`ml/gpu/JOBS.md`), Uploads (`ml/data/local_ingest.py`), Azure-Pilot (`docs/plans/produktion-checkliste.md`) |

Regeln zwischen den Sitzungen: jede Sitzung arbeitet auf ihrem eigenen Branch und macht PRs; nur
die Hauptsitzung merged, und nur bei grüner CI. GPU-Aufträge stehen ausschliesslich in
`ml/gpu/JOBS.md`; die lokale Sitzung arbeitet sie der Reihe nach ab und trägt das Ergebnis ein.

## Prioritäten diese Woche (mit Lukas abgestimmt, 2026-11-09)
1. **Modell-Training geht weiter** (läuft im Hintergrund, kostet GPU-Zeit, kaum Tokens): Ball
   Runde 6 (OWLv2-Pseudolabels) liegt mit 33 % gleichauf mit Runde 3 und wurde nicht übernommen (Details `ml/ball/README.md`). Das Testset mit 40 Bällen ist zu klein, um zu entscheiden; erst vergrössern, dann wieder GPU-Zeit. Aufträge 4 bis 10 in `ml/gpu/JOBS.md` bleiben zurückgestellt; GPU-Aufträge nur über `ml/gpu/JOBS.md`, Kaggle vor Modal.
2. **Test-Umgebung auf Azure unter Lukas' Domain**, mit allem (Website, App, Video-Analyse auf CPU),
   damit Lukas selbst testen kann. Dort läuft auch der End-to-End-Test: ein ganzes Spiel (60 Minuten,
   mit Matchblatt) hochladen und messen (Dauer, Speicher, Fehler, Kosten pro Spiel).
3. **Was der Trainer sieht, auf echtem Material gut machen:** Torkandidaten und Würfe mit
   Ein-Klick-Bestätigung, Spielfeld bei Stream-Kameras (Klick-Kalibrierung pro Halle wiederverwenden).
   Die Fehler aus dem Test auf Azure haben Vorrang.
4. **GPU-Entscheid für den Betrieb** aus der Messung in 2: reicht CPU im Pilot, oder Modal einbauen.
5. **Nebenher (Helfer):** Namen in der Anwesenheitsliste nach `roster.visible_players`;
   `official_report.py` aufteilen (Plan im Backlog "Code health").

## Startaufträge (sofort beim Start ausführen, nicht nur lesen)
**Hauptsitzung** ("Lies docs/plans/HANDOVER.md und starte deine Startaufträge"):
1. Datenstand von Kaggle wiederherstellen und die Hintergrundprozesse starten (Abschnitt unten).
2. Ball: das Testset auf etwa 200 Bälle vergrössern: aus den hochgeladenen Spielen Frames aus Hallen wählen, die noch nicht im Test sind, OWLv2-Vorschläge als Vorbelegung (Kaggle-GPU), Lukas bestätigt sie auf der Labeling-Seite (`ml/ball/labelling/`). Erst danach neue Trainingsläufe.
3. Zwei Helfer in eigenen Worktrees und Branches losschicken: Anwesenheitsliste (Priorität 5,
   mit Test wie `apps/api/tests/test_official_names.py`) und Aufteilen von `official_report.py`
   (reine Verschiebung, Tests bleiben unverändert grün). PRs bei grüner CI mergen.
4. Bereit sein für den Test auf Azure: sobald die lokale Sitzung die Umgebung hochgezogen hat, die
   Fehler, die Lukas meldet, als Erstes beheben; beim ganzen Spiel die Messung auswerten.

**Lokale Sitzung** (auf Lukas' PC, "Lies docs/plans/HANDOVER.md, docs/plans/produktion-checkliste.md
und infra/terraform/azure/README.md und führe mich durch die Test-Umgebung"):
1. Mit Lukas die Entscheide der Checkliste ausfüllen, dann Schritt für Schritt Azure aufsetzen,
   Images bauen und hochladen, DNS bei Cloudflare, erster Login.
2. Danach den nächsten offenen Auftrag aus `ml/gpu/JOBS.md`.

**UI-Sitzung** ("Lies docs/plans/HANDOVER.md und docs/design/workspace/BACKLOG.md und starte"):
1. Prüfrunde über die neuen Screens (offizielle Daten, Würfe, Onboarding) wie ein Trainer.
2. Browser-Tests (e2e) für Würfe und offizielle Daten.
3. Die Punkte unter "Open after PR 8", zuerst "Passt" für ein Spielfeld aus der Halle und Clips ohne
   Video. Fehler aus dem Test auf Azure haben Vorrang.

## Was Lukas macht
1. Die lokale Sitzung starten und mit ihr die Test-Umgebung hochziehen (Domain, Mail, Alarme
   entscheiden; Geheimnisse nur in Key Vault oder `terraform.tfvars` auf dem PC).
2. Selbst testen und Fehler der Hauptsitzung (Backend) oder UI-Sitzung (Bildschirme) melden.
3. Ein ganzes Spiel mit Matchblatt in der Test-Umgebung hochladen.
4. Branches löschen, die die Hauptsitzung als erledigt meldet (die Sitzung kann keine Remote-Branches
   löschen).

## Datenstand und Hintergrundprozesse
Die Cloud-Sitzung ist flüchtig: alles ausserhalb des Repos ist mit ihr weg. Darum:
- **Kaggle ist der gemeinsame Speicher** (Konto `lukasde1000`): Segmente `handball-segs-bNN` (Cloud)
  und `handball-segs-lNN` (Lukas' Uploads), GPU-Ergebnisse `handball-gpu-<job>-<datum>`, Ballmodell
  `handball-ball-models`, und der Stand der Uhr-Erkennung `handball-library-state`
  (`library.json`, `index/`, `info/` und der Ingest-Zustand).
- **Wiederherstellen:** `handball-library-state` herunterladen, `library/` und `ingest/` nach
  `$HANDBALL_SCRATCH/` legen (`HANDBALL_SCRATCH` auf einen eigenen Ordner setzen; der
  Standardwert zeigt auf den Ordner der alten Sitzung), dann
  `python -I ml/data/library.py --watch 900` im Hintergrund und stündlich
  `python ml/data/match_official.py` (schreibt `ml/data/catalog.json` nur bei echter Änderung;
  die Änderung committen).
- Kaggle-CLI in der Cloud: `KAGGLE_USERNAME=lukasde1000`, `KAGGLE_KEY` setzt der Proxy ein
  (beliebiger Platzhalter), `REQUESTS_CA_BUNDLE=/root/.ccr/ca-bundle.crt`.
- **Modal geht nur aus der lokalen Sitzung** (der Proxy der Cloud lässt gRPC nicht durch).
- **GPU sparsam:** Kaggle etwa 30 h pro Woche gratis, Modal 30 USD pro Monat. Erst messen, Kaggle vor
  Modal, Checkpoints, lieber kleine Aufträge. Zurückgestellte Aufträge in `ml/gpu/JOBS.md`.

## Arbeitsregeln (gelten weiter)
- Merge nur bei grüner CI; kein Deploy, kein Force-Push.
- Keine Geheimnisse in Repo oder Chat; Testdaten mit erfundenen Namen. Offizielle Spielberichte mit
  echten Namen bleiben im (privaten) Repo unter `ml/`, nicht in Test-Fixtures.
- Fremde PyTorch-Checkpoints nur mit `weights_only=True`. Bot-Sperren nicht umgehen (handball.net
  ist gesperrt).
- Texte: de-CH mit "ss" (nie "ß"), keine langen Gedankenstriche; de-CH, en und fr pflegen.
- Commits als "Claude <noreply@anthropic.com>" mit den Trailern der Sitzung; keine Modellnamen im
  Repo. Nur eigene Dateien committen, nie halbfertige Arbeit von Helfern.
- Löschen auf Kaggle macht Lukas.
- Der Ordner `ml/` ist Forschung (von Lint ausgenommen); Produktcode importiert nichts daraus.

## Wo was steht
- `docs/plans/backlog.md`: Prioritäten, Entscheide, Code health
- `docs/plans/produktion-checkliste.md`: Pilot auf Azure
- `docs/plans/ui-match-workspace.md`, `docs/design/workspace/BACKLOG.md`: UI
- `docs/plans/federation-onboarding.md`, `docs/plans/data-sources-de.md`: offizielle Daten
- `docs/adr/`: Entscheide (u. a. 027 Rückennummern, 003 Lizenzen der Trainingsdaten)
- `ml/README.md`: Forschungsordner, `ml/gpu/JOBS.md`: GPU-Warteschlange
