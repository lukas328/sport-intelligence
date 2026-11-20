# Lokaler Stack ohne Docker

Für wen: Cloud-Sitzungen (und alle anderen ohne Docker-Daemon oder mit gesperrten Image-Pulls).
Ziel: der ganze Stack wie in `infra/docker-compose.yml` als normale Prozesse, damit die
Browser-Tests (`apps/web/e2e`), Screenshots und die Produktbilder der Website laufen.
So am 20.11.2026 in einer Cloud-Sitzung gestartet (4 CPU, 15 GB RAM), alles unten ist erprobt.

| Dienst | Hier | In compose |
|---|---|---|
| Postgres 16 | `service postgresql` (vorinstalliert), Rollen `handball` und `handball_app` wie in `infra/postgres/init` | `postgres:16-alpine` |
| Redis | `service redis-server` (vorinstalliert) | `redis:7-alpine` |
| S3 | SeaweedFS 4.50 als Binary `weed` auf Port 9000, Daten unter `/tmp/handball-local/s3`; ohne `weed` ein moto-Server (nur im Speicher) | SeaweedFS 4.50 |
| E-Mail | Mailpit 1.27 als Binary (SMTP 1025, Web 8025); ohne `mailpit` landen Mails in `api.log` | Mailpit |
| API, Worker, GPU-Worker | `uv run handball-api`, `handball-worker`, `handball-gpu-worker` | eigene Images |
| Web | `next start` nach einem Build (oder `next dev` mit `HB_WEB_DEV=1`) auf Port 3000 | eigenes Image |

Alles startet `scripts/local-stack.sh`. Logs und Daten liegen in `/tmp/handball-local`
(änderbar mit `HB_LOCAL_RUN`).

## Einmalig: Binaries holen
Beide kommen von GitHub-Releases (über den Proxy erlaubt; `dl.min.io` dagegen antwortet 410, MinIO
gibt es nicht mehr als freies Binary).

```bash
mkdir -p /root/.local/bin "$TMPDIR/dl" && cd "$TMPDIR/dl"
curl -sSL -o sw.tgz https://github.com/seaweedfs/seaweedfs/releases/download/4.50/linux_amd64.tar.gz
tar xzf sw.tgz -C /root/.local/bin weed
curl -sSL -o mp.tgz https://github.com/axllent/mailpit/releases/download/v1.27.0/mailpit-linux-amd64.tar.gz
tar xzf mp.tgz -C /root/.local/bin mailpit
weed version && mailpit version   # mailpit meldet einen Fehler beim Update-Check, das ist egal
```

`/root/.local/bin` ist in Cloud-Sitzungen schon im `PATH`. Das Skript nimmt `weed` und `mailpit`,
sobald sie im `PATH` liegen; sonst moto und Konsolen-Mails wie bisher.

## Starten
```bash
uv sync --all-packages && pnpm install          # einmalig pro Worktree
pnpm --filter @handball/web build               # etwa 1,5 min; ohne Build: HB_WEB_DEV=1 davor
scripts/local-stack.sh up                       # Datenbank, Migrationen, Buckets, alle Prozesse, etwa 1 min
uv run python scripts/seed.py                   # = make seed, etwa 3 min (synthetische Videos durch die echte Pipeline)
```

Anmelden auf <http://localhost:3000/login> mit `demo@handball-demo.ch` / `demo-handball-2026`
(Verein «HC Tannengrün», drei Spiele mit Video, zwei mit Spielbericht).

Prüfen:
- `curl -s localhost:8000/readyz` meldet database, redis und storage «ok».
- `scripts/local-stack.sh status` zeigt s3, mail, api, worker, gpu-worker und web «running».
- Mails: <http://localhost:8025>.

## Nach Änderungen
- Web-Code: `pnpm --filter @handball/web build`, dann `scripts/local-stack.sh restart-web`
  (startet `next start` auf dem neuen Build). Mit `HB_WEB_DEV=1 scripts/local-stack.sh restart-web`
  stattdessen `next dev` mit leerem Cache (der Cache liest `apps/web/messages/*.json` sonst nicht
  neu). Bis 20.11. löschte `restart-web` immer den Build und startete `next dev`: die e2e liefen
  danach unbemerkt gegen den Entwicklungsserver. Für e2e immer den Build nehmen; welcher läuft,
  zeigt `ps aux | grep "next (dev|start)"`.
- Backend: `scripts/local-stack.sh restart-api` (mit Migrationen).
- Neu anfangen: `scripts/local-stack.sh down`, `su postgres -c "dropdb handball"`,
  `rm -rf /tmp/handball-local/s3`, dann `up` und Seed. Mit moto unbedingt so: nach `down` sind die
  Videos weg, die Zeilen in der Datenbank nicht.

## Nach einem Neustart des Containers
Am 20.11. erprobt: Postgres läuft nach dem Neustart wieder, alle anderen Dienste nicht.
`scripts/local-stack.sh up` startet sie in etwa 1 min neu. Datenbank, SeaweedFS-Daten
(`/tmp/handball-local/s3`) und der Web-Build bleiben erhalten, also kein neuer Seed und kein neuer
Build nötig. Mit moto statt SeaweedFS sind die Videos weg (dann neu anfangen, siehe oben).

## Tests
- Browser-Tests: `cd apps/web && npx playwright test --trace off --workers 2`. Chromium liegt
  vorinstalliert in `/opt/pw-browsers` (`PLAYWRIGHT_BROWSERS_PATH`), passend zu Playwright 1.63.
  Mehr als 2 Worker lohnen sich mit 4 CPU nicht, weil die Analyse der hochgeladenen Videos
  dieselben Kerne braucht. Ein Lauf dauert gegen den Build etwa 7 bis 10 Minuten (20.11.:
  121 Tests, davon 49 nur in einem der beiden Projekte und dort übersprungen).
- API-Tests: `uv run pytest apps/api -n auto -q` brauchen nur Postgres
  (`HB_TEST_ADMIN_DSN`, Standard `postgresql://handball:handball@localhost:5432/postgres`).
- Vitest (`pnpm --filter @handball/web test`) braucht nichts.
- Produktbilder der Website: `pnpm --filter @handball/site shots`
  (`apps/site/scripts/product-shots/README.md`).

## Stolpersteine
- `pgrep -f` im Skript sucht die Prozesse an ihrer Kommandozeile. Steht dieselbe Zeichenkette in
  der Kommandozeile der aufrufenden Shell (zum Beispiel in einem Heredoc im selben Befehl), meint
  das Skript, der Dienst laufe schon. Das Skript dann in einem eigenen Befehl aufrufen.
- `capture.mjs --colours` färbt den Demo-Verein der Reihe nach um und setzt ihn erst am Ende
  zurück. Bricht der Lauf ab, bleibt der Verein in einer fremden Farbe. Zurück auf Grün:
  `psql postgresql://handball:handball@localhost:5432/handball -c "update organizations set primary_color='#10684a', secondary_color='#ffffff' where name='HC Tannengrün'"`
  und dasselbe für `matches.kit_own` der Spiele des Vereins (ausser beobachteten Spielen).
- `service redis-server start` meldet `ulimit: error setting limit`; Redis läuft trotzdem.
- Ohne Mailpit scheitern die e2e-Specs, die Links aus Mails lesen (`e2e/helpers.ts`,
  `linkFromMail`): account, entry, family, onboarding, player.
