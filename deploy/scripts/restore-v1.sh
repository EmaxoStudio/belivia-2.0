#!/usr/bin/env bash
# restore-v1.sh — Belivia V1 safe database restore
#
# Usage:
#   bash restore-v1.sh /srv/belivia/ops/backups/belivia-YYYYMMDD-HHMMSS.sqlite
#
# Must be run as beliviaadmin (needs sudo for service control and install).
# Does NOT perform a live restore automatically — always review output before confirming.

set -euo pipefail

BACKUP_FILE="${1:-}"
DB_TARGET="/srv/belivia/data/belivia.sqlite"
SAFETY_COPY="${DB_TARGET}.before-restore"

# --- Argument check ---
if [[ -z "$BACKUP_FILE" ]]; then
  echo "ERROR: No backup file specified."
  echo "Usage: bash restore-v1.sh /srv/belivia/ops/backups/belivia-YYYYMMDD-HHMMSS.sqlite"
  exit 1
fi

if [[ ! -f "$BACKUP_FILE" ]]; then
  echo "ERROR: Backup file not found: $BACKUP_FILE"
  exit 1
fi

# --- Pre-restore: integrity check ---
echo "=== PRE-RESTORE: Integrity check ==="
INTEGRITY=$(sqlite3 "$BACKUP_FILE" "PRAGMA integrity_check;" 2>&1)
if [[ "$INTEGRITY" != "ok" ]]; then
  echo "ERROR: Backup file failed integrity check:"
  echo "$INTEGRITY"
  echo "Aborting restore. Do not use this backup."
  exit 1
fi
echo "Backup integrity: ok"

# --- Pre-restore: table spot-check ---
echo ""
echo "=== PRE-RESTORE: Backup contents ==="
sqlite3 "$BACKUP_FILE" ".tables"
echo ""

# --- Confirm before proceeding ---
echo "Backup file: $BACKUP_FILE"
echo "Target:      $DB_TARGET"
echo ""
echo "This will:"
echo "  1. Stop belivia-api"
echo "  2. Copy current DB to ${SAFETY_COPY}"
echo "  3. Install backup as live DB"
echo "  4. Start belivia-api"
echo ""
read -r -p "Proceed with restore? [yes/no] " CONFIRM
if [[ "$CONFIRM" != "yes" ]]; then
  echo "Aborted. No changes made."
  exit 0
fi

# --- Stop service ---
echo ""
echo "=== Stopping belivia-api ==="
sudo systemctl stop belivia-api
echo "Service stopped."

# --- Safety copy of current DB ---
echo ""
echo "=== Creating safety copy ==="
cp "$DB_TARGET" "$SAFETY_COPY"
echo "Safety copy: $SAFETY_COPY"

# --- Restore backup ---
echo ""
echo "=== Restoring backup ==="
sudo install -o beliviaapp -g beliviaapp -m 644 "$BACKUP_FILE" "$DB_TARGET"
echo "Backup installed."

# --- Start service ---
echo ""
echo "=== Starting belivia-api ==="
sudo systemctl start belivia-api
sleep 1

# --- Post-restore verification ---
echo ""
echo "=== POST-RESTORE: Verification ==="

echo "Service status:"
systemctl is-active belivia-api

echo ""
echo "Health check:"
curl -sS http://127.0.0.1:8000/api/health
echo ""

echo ""
echo "DB table check (restored DB):"
sqlite3 "$DB_TARGET" ".tables"

echo ""
echo "=== Restore complete ==="
echo ""
echo "IMPORTANT:"
echo "  - Safety copy remains at: $SAFETY_COPY"
echo "  - Remove it once the restore is confirmed: rm $SAFETY_COPY"
echo "  - If something is wrong: stop service, restore safety copy, start service"
