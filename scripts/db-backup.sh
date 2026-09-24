#!/bin/bash
# Backup giornaliero DB OmniState con rotazione 7 giorni
# Usa DATA_HOST_DIR da .env (default ./data)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/../.env"

if [[ -f "$ENV_FILE" ]]; then
  DATA_HOST_DIR=$(grep '^DATA_HOST_DIR=' "$ENV_FILE" | cut -d= -f2- | tr -d '[:space:]' || true)
fi
DATA_HOST_DIR="${DATA_HOST_DIR:-${SCRIPT_DIR}/../data}"
DB_FILE="$DATA_HOST_DIR/index.db"
BACKUP_DIR="$DATA_HOST_DIR/backups"

if [[ ! -f "$DB_FILE" ]]; then
  echo "DB non trovato: $DB_FILE" >&2
  exit 1
fi

mkdir -p "$BACKUP_DIR"
DATE=$(date +%F)
BACKUP_FILE="$BACKUP_DIR/index_$DATE.db"

cp -v "$DB_FILE" "$BACKUP_FILE"

# Rotazione: mantieni ultimi 7
ls -t "$BACKUP_DIR"/index_*.db | tail -n +8 | xargs -r rm -v

echo "Backup completato: $BACKUP_FILE ($(ls -t $BACKUP_DIR/index_*.db 2>/dev/null | wc -l) file mantenuti, max 7)"
