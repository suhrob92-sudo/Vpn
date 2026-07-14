#!/usr/bin/env bash
# Daily PostgreSQL backup. Keeps RETENTION_DAYS days locally; sync ./backups
# to object storage (rclone/S3) from cron so backups leave the machine.
set -euo pipefail

cd "$(dirname "$0")/.."
BACKUP_DIR="${BACKUP_DIR:-./backups}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
STAMP="$(date +%Y-%m-%d_%H%M)"

mkdir -p "$BACKUP_DIR"

docker compose exec -T postgres sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' \
  | gzip > "$BACKUP_DIR/vpn_${STAMP}.sql.gz"

find "$BACKUP_DIR" -name 'vpn_*.sql.gz' -mtime +"$RETENTION_DAYS" -delete

echo "backup written: $BACKUP_DIR/vpn_${STAMP}.sql.gz"
