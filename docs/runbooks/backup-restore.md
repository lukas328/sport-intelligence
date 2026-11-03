# Backup and restore

**Database.** Managed Postgres with point-in-time recovery (7 days) plus a nightly logical dump:
`DATABASE_URL=... BACKUP_DIR=... infra/scripts/backup.sh` → copy the `.dump` and `.sha256` to the
off-site bucket (versioning + object lock, other region, CH/EU). Retention: 35 daily, 12 monthly.

**Object storage.** Bucket versioning on `videos` and `artifacts`, lifecycle: noncurrent versions
kept 30 days. Originals are the expensive part to lose; derived HLS, proxies and analysis can be
regenerated (`reprocess`).

**Restore test (monthly, and before go-live).** `infra/scripts/restore-test.sh` dumps the database,
restores it into a fresh Postgres 16 and compares row counts per table, the migration revision and the
row-level-security policies. Result of the M9 run (local stack): 36 tables, revision 0012 → 0012,
31 → 31 policies, 30 tables with forced RLS, `RESTORE OK`. For production, run the same comparison
against the latest nightly dump in an isolated environment and record the result here.

**Real restore.**
1. Stop writers (scale API and workers to 0, maintenance page on the load balancer).
2. Point-in-time restore of the managed database to a new instance, or `pg_restore --no-owner` of the
   latest dump into an empty database (create role `handball_app` first).
3. Check revision, policies and row counts as in the restore test; switch `HB_DATABASE_URL`.
4. Start API and workers, verify like after a deploy, inform affected clubs (incident.md).
