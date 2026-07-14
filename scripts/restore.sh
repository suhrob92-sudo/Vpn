#!/usr/bin/env bash
# Restore a backup produced by backup.sh: ./scripts/restore.sh backups/vpn_X.sql.gz
set -euo pipefail

if [ $# -ne 1 ] || [ ! -f "$1" ]; then
  echo "usage: $0 <backup-file.sql.gz>" >&2
  exit 1
fi

cd "$(dirname "$0")/.."
FILE="$1"

echo "⚠️  This will DROP and recreate the current database. Ctrl+C to abort."
read -r -p "Type 'restore' to continue: " confirm
[ "$confirm" = "restore" ] || exit 1

docker compose exec -T postgres sh -c \
  'dropdb -U "$POSTGRES_USER" --if-exists "$POSTGRES_DB" && createdb -U "$POSTGRES_USER" "$POSTGRES_DB"'

gunzip -c "$FILE" | docker compose exec -T postgres sh -c \
  'psql -q -U "$POSTGRES_USER" "$POSTGRES_DB"'

echo "restore complete from $FILE"
