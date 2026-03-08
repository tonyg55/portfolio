#!/usr/bin/env bash
# Restore a pg_dump backup file into a running PostgreSQL instance
set -euo pipefail

: "${PGHOST:=localhost}"
: "${PGPORT:=5432}"
: "${PGDATABASE:=appdb}"
: "${PGUSER:=appuser}"
: "${PGPASSWORD:=localpass}"

BACKUP_FILE="${1:-}"
if [ -z "$BACKUP_FILE" ]; then
  echo "Usage: $0 <backup.dump>"
  exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
  echo "Backup file not found: $BACKUP_FILE"
  exit 1
fi

echo "[restore] Dropping and recreating database: ${PGDATABASE}"
PGPASSWORD="$PGPASSWORD" psql \
  -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d postgres \
  -c "DROP DATABASE IF EXISTS ${PGDATABASE};" \
  -c "CREATE DATABASE ${PGDATABASE} OWNER ${PGUSER};"

echo "[restore] Restoring from: ${BACKUP_FILE}"
PGPASSWORD="$PGPASSWORD" pg_restore \
  -h "$PGHOST" \
  -p "$PGPORT" \
  -U "$PGUSER" \
  -d "$PGDATABASE" \
  --no-owner \
  --role="$PGUSER" \
  "$BACKUP_FILE"

echo "[restore] Restore complete."
