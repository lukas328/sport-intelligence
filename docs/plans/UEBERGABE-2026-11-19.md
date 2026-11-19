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
| Spielende in `scoreboard.play_intervals` | Helfer | läuft |
| Code health 2, 3, 9 (totes Gerüst, `system_access` als Kontextmanager, PDF im Thread) | Helfer | läuft |
| A22 Wurfort vorausgewählt, Website-Text | Helfer | läuft |
| Wurfzeit der Kandidaten (Versatz 2.8 s), nur auf Entwicklungsdaten gemessen, Endtest nicht zum Einstellen | Helfer | läuft |

## Was Lukas tun muss
- Den Branch `claude/affectionate-edison-lkw4r3` als PR nach main mergen, wenn die CI grün ist
  (diese Sitzung hat keinen GitHub-Zugriff für PRs). PR #104 ist darin enthalten und kann danach
  geschlossen werden.
- Erledigte Branches löschen: `claude/ecstatic-darwin-p0ss4x` (nur Merges), `claude/open-questions`
  (Inhalt in main), `claude/produkt-integration` (nach dem Merge), dazu die Design-Entwürfe
  `claude/trikot-zielbild`, `claude/design-runde2-sport`, `claude/design-runde2-video` (die
  gewählte Marke liegt in `docs/design/brand2/`).
