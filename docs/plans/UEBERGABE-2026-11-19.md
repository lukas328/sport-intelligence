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
| 2026-11-19 | Hauptsitzung | Keine offenen GPU-Aufträge; 12 bis 15 erledigt, 11 und 3 zurückgestellt. | `ml/gpu/JOBS.md` |

## Änderungen dieser Sitzung
| Was | Commit / Branch | Stand |
|---|---|---|
| PR #104 (Wurf-Endtest) in den Sitzungsbranch gemergt | Merge im Sitzungsbranch | erledigt |
| `ml/gpu/JOBS.md` aufgeräumt (12 bis 15 nach "Erledigt", 3 und 11 zurückgestellt) | Sitzungsbranch | erledigt |
| `docs/OPEN_QUESTIONS.md` Punkt 12: GPU-Entscheid | Sitzungsbranch | erledigt |
| Spielende in `scoreboard.play_intervals`: lief die Uhr zuletzt, zählt das Spiel bis zum Videoende, höchstens bis zum Ende der Halbzeit (neuer Parameter `half_s`, Standard 30:00; Jugend mit kürzeren Halbzeiten hat nur eine lockerere Obergrenze). Halbzeitende (30:00 oder 0:00) und stehende Uhr wie bisher. Lesungen nach dem letzten Lauf, die nicht die Matchuhr sein können (Strafzeit, Fehllesung), blockieren die Regel nicht mehr. 3 neue Tests, `packages/vision` 218 grün | `2783a798` | erledigt |
| Code health 2, 3, 9 (totes Gerüst, `system_access` als Kontextmanager, PDF im Thread) | Helfer | läuft |
| A22 Wurfort vorausgewählt, Website-Text | Helfer | läuft |
| Wurfzeit der Kandidaten: Ursache gefunden, **kein Fix**. Die Kandidatenzeit ist der Spitzenwert des "Spiel dreht"-Musters (Rücklauf, Abwurf), nicht der Abwurf; der Versatz 1.5 s wurde gegen das Spielprotokoll gelernt, das etwa 3 s nach dem Abwurf liegt; dazu schwankt die Verzögerung je nach Ausgang (Tor 0.9 s, gehalten 1.8 s, daneben 2.6 s). Ohne Abwurf-Markierungen auf Dev lässt sich nichts ehrlich korrigieren, der Endtest darf nicht dafür herhalten. Clips sind nicht betroffen (Start 8 s vor der Spitze). `shot_segments_eval.py score` schreibt jetzt `per_shot`. Nächste Schritte im Plan, Abschnitt "Wurfzeit der Kandidaten (2026-11-19)" | `1d199c84` | Diagnose erledigt, Fix wartet auf Daten |
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
