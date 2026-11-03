#!/usr/bin/env bash
# Restore test (M9): dump the local compose database, restore it into a throw-away Postgres and
# compare row counts per table, the migration revision and the row-level-security policies.
# Run monthly against a production backup as well (docs/runbooks/backup-restore.md).
set -euo pipefail
cd "$(dirname "$0")/../.."
work="$(mktemp -d)"
trap 'docker rm -f hb-restore-test >/dev/null 2>&1 || true; rm -rf "$work"' EXIT
db() { docker compose exec -T postgres psql -U handball -d handball -At -c "$1"; }

echo "1/4 dump"
docker compose exec -T postgres pg_dump -U handball -d handball --format=custom > "$work/db.dump"
ls -lh "$work/db.dump" | awk '{print "    size", $5}'

echo "2/4 restore into a fresh Postgres 16"
docker run -d --name hb-restore-test -e POSTGRES_PASSWORD=restore -e POSTGRES_USER=handball \
  -e POSTGRES_DB=handball postgres:16-alpine >/dev/null
until docker exec hb-restore-test pg_isready -U handball -d handball >/dev/null 2>&1; do sleep 1; done
sleep 2
# roles referenced by grants and policies must exist before the restore
docker exec hb-restore-test psql -U handball -d handball -q -c "CREATE ROLE handball_app NOLOGIN" || true
docker exec -i hb-restore-test pg_restore -U handball -d handball --no-owner --exit-on-error < "$work/db.dump"
rdb() { docker exec hb-restore-test psql -U handball -d handball -At -c "$1"; }

echo "3/4 compare"
tables="SELECT string_agg(table_name, ' ' ORDER BY table_name) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE'"
fail=0
for t in $(db "$tables"); do
  a="$(db "SELECT count(*) FROM \"$t\"")"; b="$(rdb "SELECT count(*) FROM \"$t\"")"
  if [ "$a" != "$b" ]; then echo "    MISMATCH $t: $a vs $b"; fail=1; fi
done
rev_a="$(db "SELECT version_num FROM alembic_version")"; rev_b="$(rdb "SELECT version_num FROM alembic_version")"
pol_a="$(db "SELECT count(*) FROM pg_policies")"; pol_b="$(rdb "SELECT count(*) FROM pg_policies")"
rls_b="$(rdb "SELECT count(*) FROM pg_class WHERE relrowsecurity AND relforcerowsecurity")"
echo "    tables: $(db "$tables" | wc -w), revision $rev_a -> $rev_b, policies $pol_a -> $pol_b, forced RLS tables $rls_b"
[ "$rev_a" = "$rev_b" ] && [ "$pol_a" = "$pol_b" ] || fail=1

echo "4/4 result"
if [ "$fail" = 0 ]; then echo "    RESTORE OK"; else echo "    RESTORE FAILED"; exit 1; fi
