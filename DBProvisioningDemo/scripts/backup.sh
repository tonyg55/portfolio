#!/usr/bin/env bash
# Create a pg_dump backup of a running PostgreSQL instance
set -euo pipefail

: "${PGHOST:=localhost}"
: "${PGPORT:=5432}"
: "${PGDATABASE:=appdb}"
: "${PGUSER:=appuser}"
: "${PGPASSWORD:=localpass}"
: "${BACKUP_DIR:=./backups}"

TIMESTAMP=$(date +%Y%m%d-%H%M%S)
FILENAME="${BACKUP_DIR}/${PGDATABASE}-${TIMESTAMP}.dump"

mkdir -p "$BACKUP_DIR"

echo "[backup] Starting pg_dump → ${FILENAME}"
PGPASSWORD="$PGPASSWORD" pg_dump \
  -h "$PGHOST" \
  -p "$PGPORT" \
  -U "$PGUSER" \
  -d "$PGDATABASE" \
  -F c \
  -f "$FILENAME"

SIZE=$(du -sh "$FILENAME" | cut -f1)
echo "[backup] Complete: ${FILENAME} (${SIZE})"

# Retain only last 7 backups
ls -t "${BACKUP_DIR}"/*.dump 2>/dev/null | tail -n +8 | xargs -r rm --
echo "[backup] Retention: kept last 7 backups."
