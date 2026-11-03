#!/usr/bin/env bash
# Logical backup of the database (custom format) next to the managed provider's PITR.
# Usage: DATABASE_URL=postgresql://... BACKUP_DIR=/backups ./backup.sh
# Production: run nightly from the scheduler, then copy the file to the off-site bucket (versioned,
# object lock, other region). Keep 35 daily and 12 monthly copies (docs/runbooks/backup-restore.md).
set -euo pipefail
: "${DATABASE_URL:?set DATABASE_URL}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
mkdir -p "$BACKUP_DIR"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
file="$BACKUP_DIR/handball-$stamp.dump"
pg_dump --format=custom --no-owner --no-privileges --file="$file" "$DATABASE_URL"
sha256sum "$file" > "$file.sha256"
echo "$file"
