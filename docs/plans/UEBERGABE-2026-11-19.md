# Übergabe: Hauptsitzung vom 2026-11-19

Diese Datei hält fest, was die Hauptsitzung am 19.11. entschieden und geändert hat, damit eine
spätere Sitzung (oder die frühere, sobald sie wieder Tokens hat) nahtlos weitermachen kann.
Einstieg danach wie immer: `docs/plans/HANDOVER.md`.

## Ausgangslage
- Die bisherige Hauptsitzung hatte keine Tokens mehr. Lukas hat diese Sitzung als neue
  Hauptsitzung eingesetzt, mit freier Hand: selbst entscheiden, priorisieren, Helfer verteilen.
- Stand von main beim Start: `c52f78b` (PR #103). Offen war PR #104 (Wurf-Endtest, nur Doku und
  `ml/`), seine Commits sind in den Branch dieser Sitzung gemergt.
- Arbeitsbranch dieser Sitzung: `claude/affectionate-edison-lkw4r3`. Helfer arbeiten in eigenen
  Worktrees; ihre Commits werden in diesen Branch gemergt.
- Testumgebung in der Cloud: Postgres 16 lokal (`service postgresql start`, Superuser
  `handball/handball`), damit laufen die API-Tests ohne Docker.

## Entscheide
| Datum | Wer | Entscheid | Wo umgesetzt |
|---|---|---|---|
| 2026-11-19 | Lukas | GPU kommt später von Azure, nicht von Modal. Dafür zieht wahrscheinlich die ganze Umgebung aus Switzerland North in eine andere Azure-Region. Das macht Lukas selbst, nicht jetzt. Bis dahin: Staging auf CPU, kein Modal-Backend bauen. | `docs/OPEN_QUESTIONS.md` Punkt 12, `ml/gpu/JOBS.md` |
| 2026-11-19 | Hauptsitzung | A22 Wurfort: Die Schätzung ist bei «Von wo?» vorausgewählt, ein Tipp bestätigt sie, nur bestätigte zählen für die drei Dinge. Website-Text entsprechend. Voll automatisch erst, wenn die Schätzung verlässlich ist. | Helfer A22 (siehe unten) |
| 2026-11-19 | Hauptsitzung | Spielende in der Pausenerkennung: lief die Uhr zuletzt und wurde danach keine stehende Uhr gelesen, zählt das Spiel bis zum Videoende weiter (mit Obergrenze). | Helfer Spielende |
| 2026-11-19 | Lukas | Die Website erzählt die Vision des fertigen Produkts (Aufwand, «Samstag, 22 Uhr»), nicht den Stand der Testphase. Keine Zahlen aus der CPU-Testphase auf die Website. | `BEFUNDE-5-website-review.md` |
| 2026-11-19 | Hauptsitzung | App-Review: beobachtete Spiele neutral (kein «Wir»), Szenen beobachteter Spiele in «Szenen» mit Filter, eigener Abschnitt in der Spieleliste, Onboarding-Schritt 1 erledigt bei jedem analysierten Video; aus «die drei Dinge» wird «die drei Muster» (Lukas), als letzter Schritt in App und Website. | `BEFUNDE-6-app-review.md` |
| 2026-11-19 | Lukas | Schwerpunkt Europa (wie `docs/plans/europa.md`): Website mit EUR und CHF, ehrliche Teamsuche ausserhalb der Schweiz. Wirkung der Website messen mit `?src=` an jedem App-Link; Lukas wäre auch mit Cookies einverstanden, die Hauptsitzung bleibt bei «keine Cookies» (Verkaufsargument), weil `?src=` dafür reicht. Seite «Für Vereine», «Gemacht mit Handball Intelligence» auf geteilten Szenen. Launch-Zeitpunkt Rückrunde Januar: Vorschlag des Reviews, Entscheid bei Lukas. | `BEFUNDE-5-website-review.md` |
| 2026-11-19 | Hauptsitzung | Keine offenen GPU-Aufträge; 12 bis 15 erledigt, 11 und 3 zurückgestellt. | `ml/gpu/JOBS.md` |

## Änderungen dieser Sitzung
| Was | Commit / Branch | Stand |
|---|---|---|
| PR #104 (Wurf-Endtest) in den Sitzungsbranch gemergt | Merge im Sitzungsbranch | erledigt |
| `ml/gpu/JOBS.md` aufgeräumt (12 bis 15 nach "Erledigt", 3 und 11 zurückgestellt) | Sitzungsbranch | erledigt |
| `docs/OPEN_QUESTIONS.md` Punkt 12: GPU-Entscheid | Sitzungsbranch | erledigt |
| Spielende in `scoreboard.play_intervals`: lief die Uhr zuletzt, zählt das Spiel bis zum Videoende, höchstens bis zum Ende der Halbzeit (neuer Parameter `half_s`, Standard 30:00; Jugend mit kürzeren Halbzeiten hat nur eine lockerere Obergrenze). Halbzeitende (30:00 oder 0:00) und stehende Uhr wie bisher. Lesungen nach dem letzten Lauf, die nicht die Matchuhr sein können (Strafzeit, Fehllesung), blockieren die Regel nicht mehr. 3 neue Tests, `packages/vision` 218 grün | `2783a798` | erledigt |
| Code health 2, 3, 9: totes Gerüst gelöscht (`handball_worker/pipeline/`, GPU-Worker `jobs.py` und `backends/`; Integrationstest schickt jetzt `os.getpid` an die GPU-Queue); `async with system_access(session, reason=...)` an allen ungeschützten Stellen, Grund wird geloggt (info, eine Zeile pro Media-/Job-Aufruf: bei Log-Volumen auf debug senken); reportlab-PDFs per `asyncio.to_thread`. Offen gelassen: Einstellung `HB_GPU_BACKEND` (für das spätere GPU-Backend). Nach dem Merge: 886 Python-Tests grün | `6f574ed2`, `77ef89df`, `2827e14d`, `d5336b8d` | erledigt |
| A22 Wurfort: «Von wo?» wählt die Schätzung vor (gelb, gestrichelt, «Vorschlag»), ein Tipp in diese Zone bestätigt; die API übernimmt dann den geschätzten Punkt als Trainerpunkt (`zone_source`/`position_source` «coach», Methode in `attributes.confirmed_estimate`), unbestätigt zählt weiter nichts. An allen drei Stellen (Prüfen, Wurfort nachtragen, Wurfort ändern). Website- und Hilfetexte de/fr/en. API 508, Web 411, Site 95 Tests grün; Site-Build und e2e nicht gelaufen | `2161ec58`, `8f299f20`, `63e94d4c` | erledigt |
| Wurfzeit der Kandidaten: Ursache gefunden, **kein Fix**. Die Kandidatenzeit ist der Spitzenwert des "Spiel dreht"-Musters (Rücklauf, Abwurf), nicht der Abwurf; der Versatz 1.5 s wurde gegen das Spielprotokoll gelernt, das etwa 3 s nach dem Abwurf liegt; dazu schwankt die Verzögerung je nach Ausgang (Tor 0.9 s, gehalten 1.8 s, daneben 2.6 s). Ohne Abwurf-Markierungen auf Dev lässt sich nichts ehrlich korrigieren, der Endtest darf nicht dafür herhalten. Clips sind nicht betroffen (Start 8 s vor der Spitze). `shot_segments_eval.py score` schreibt jetzt `per_shot`. Nächste Schritte im Plan, Abschnitt "Wurfzeit der Kandidaten (2026-11-19)" | `1d199c84` | Diagnose erledigt, Fix wartet auf Daten |
| App-Review vom 19.11. bewertet; Block 1 (beobachtete Spiele, Zahlen) beim Helfer | `docs/ux-test/livegang/BEFUNDE-6-app-review.md` | läuft |
| App-Block 2: Video als Standard (Wahl gemerkt), Player fixiert links, Szenen vor/zurück (Tasten N/P), Szenenende mit «Nächste Szene», «Zeichnen» öffnet die Werkbank am aktuellen Moment, nur ein Video-Element bei geschlossener Werkbank, Legende nur in «Feld von oben», «Szene merken» als Umschalter, Loop-Vorschau im Wurfort-Dialog; Prüfen zeigt den ganzen Clip (L2, BUG-14); L3: Fragen hinter «Mehr prüfen» blieben in der DB, waren aber nicht mehr erreichbar, jetzt «Prüfen · n weitere» und Glocke verlinkt. Web 415 Tests, Typecheck grün; e2e nicht gelaufen | `65501c30` bis `35d9afec` | erledigt |
| Website-Review vom 19.11. Punkt für Punkt bewertet (was passt, was nicht, was nur Lukas kann) | `docs/ux-test/livegang/BEFUNDE-5-website-review.md` | bewertet, Umsetzung nach A22 |

## Was Lukas tun muss
- Für die Wurfzeit: auf den 41 Dev-Wurfclips je den Abwurf anklicken (ein Klick pro Clip). Ohne
  diese Wahrheit lässt sich die Wurfzeit nicht ehrlich verbessern.
- Kaggle in der Cloud-Sitzung: Der Proxy hat am 19.11. keine Kaggle-Zugangsdaten eingesetzt
  (private Datasets 403). Prüfen, ob das Kaggle-Geheimnis in der Umgebung noch hinterlegt ist.
- Website-Review: die Punkte unter "Für Lukas" in `docs/ux-test/livegang/BEFUNDE-5-website-review.md`.
- Den Branch `claude/affectionate-edison-lkw4r3` als PR nach main mergen, wenn die CI grün ist
  (diese Sitzung hat keinen GitHub-Zugriff für PRs). PR #104 ist darin enthalten und kann danach
  geschlossen werden.
- Erledigte Branches löschen: `claude/ecstatic-darwin-p0ss4x` (nur Merges), `claude/open-questions`
  (Inhalt in main), `claude/produkt-integration` (nach dem Merge), dazu die Design-Entwürfe
  `claude/trikot-zielbild`, `claude/design-runde2-sport`, `claude/design-runde2-video` (die
  gewählte Marke liegt in `docs/design/brand2/`).

## Warteschlange
Stand 19.11. abends: Punkte 1 (App-Block 3) und 2 (L1) sind gestartet, laufen als Helfer. Am Nachmittag
hat ein Ausgabenlimit (5 h) alle Helfer gestoppt; sie wurden nach dem Zurücksetzen fortgesetzt.
Offen bleiben 3 bis 5.

Falls die Sitzung abbricht: hier weitermachen. Laufende Helfer stehen oben mit «läuft»; ihre
Arbeit liegt nur in lokalen Worktrees und geht mit dem Container verloren, also neu starten.
1. App-Block 3 (`docs/ux-test/livegang/BEFUNDE-6-app-review.md`, Abschnitt Umsetzung Punkt 3 und L5):
   UX-05, UX-06, UX-08 bis UX-11, UI-01, UI-03, UI-04, BUG-22, TXT-02, TXT-04, TXT-05, TXT-08,
   LEGAL-01, dazu `?src=` bei der Registrierung speichern, «Gemacht mit Handball Intelligence» auf
   geteilten Szenen, «AGB» statt «Nutzungsbedingungen», Werkbank nur hinter «Einrichten von Hand»,
   oben auf jeder Spielseite die nächste Aufgabe.
2. L1 «nicht jedes Tor markieren»: Tor-Kandidaten, die klar zu einem Tor im offiziellen Spielbericht
   passen, ohne Frage übernehmen (`apps/api/src/handball_api/services/goal_candidates.py`, heute nur
   Vorschlag); erst nach Block 2, weil derselbe Code die offenen Fragen zählt.
3. «die drei Dinge» wird «die drei Muster» (en «the three patterns», fr «les trois tendances") in App,
   Website, Demo und Hilfe; nur sichtbare Texte, URLs bleiben. Als letzter Schritt.
4. UI-Check der ganzen Spielanalyse (L5) nach Block 1 bis 3.
5. Danach aus `HANDOVER.md`: Kalibrierung per Klick auf Staging, Ball, übrige Code-Health-Punkte.
