#!/bin/bash
# Backup giornaliero DB OmniState con rotazione 7 giorni
# Usa DATA_HOST_DIR da .env (default ./data)
set -euo pipefail
umask 077

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
chmod 700 "$BACKUP_DIR" 2>/dev/null || true
DATE=$(date +%F)
BACKUP_FILE="$BACKUP_DIR/index_$DATE.db"

# Consistent, WAL-safe backup when sqlite3 is available; fallback to cp.
if command -v sqlite3 >/dev/null 2>&1; then
  sqlite3 "$DB_FILE" ".backup '$BACKUP_FILE'"
else
  cp -v "$DB_FILE" "$BACKUP_FILE"
fi
chmod 600 "$BACKUP_FILE" 2>/dev/null || true
sha256sum "$BACKUP_FILE" > "$BACKUP_FILE.sha256"
chmod 600 "$BACKUP_FILE.sha256" 2>/dev/null || true

# Rotazione: mantieni ultimi 7 + relative checksum (no xargs/rm pipeline)
while IFS= read -r f; do
  [ -n "$f" ] && rm -v -- "$f"
done < <(ls -t "$BACKUP_DIR"/index_*.db 2>/dev/null | tail -n +8 || true)
while IFS= read -r f; do
  [ -n "$f" ] && rm -v -- "$f"
done < <(ls -t "$BACKUP_DIR"/index_*.db.sha256 2>/dev/null | tail -n +8 || true)

kept=$(ls -t "$BACKUP_DIR"/index_*.db 2>/dev/null | wc -l | tr -d ' ')
echo "Backup completato: $BACKUP_FILE (${kept} file mantenuti, max 7)"
