#!/bin/bash
# Belivia v1 – manual backup script
# Backs up the live SQLite database to /srv/belivia/ops/backups/
# Run as beliviaadmin (DB is world-readable; backup dir is writable by beliviaadmin)
# Keeps the last 7 backups, removes older ones.
#
# Usage:
#   bash /srv/belivia/ops/scripts/backup-v1.sh

set -euo pipefail

DB_SOURCE="/srv/belivia/data/belivia.sqlite"
BACKUP_DIR="/srv/belivia/ops/backups"
TIMESTAMP=$(date +"%Y%m%d-%H%M%S")
BACKUP_FILE="$BACKUP_DIR/belivia-${TIMESTAMP}.sqlite"
KEEP=7

if [ ! -f "$DB_SOURCE" ]; then
  echo "ERROR: database not found at $DB_SOURCE" >&2
  exit 1
fi

mkdir -p "$BACKUP_DIR"

cp "$DB_SOURCE" "$BACKUP_FILE"

echo "Backup written: $BACKUP_FILE"

# Prune old backups – keep newest $KEEP, remove the rest
PRUNED=$(ls -1t "$BACKUP_DIR"/belivia-*.sqlite 2>/dev/null | tail -n +$((KEEP + 1)))
if [ -n "$PRUNED" ]; then
  echo "$PRUNED" | xargs rm --
  echo "Pruned old backups (kept last $KEEP)."
fi

echo "Done."
