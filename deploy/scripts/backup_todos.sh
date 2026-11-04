#!/usr/bin/env bash
set -euo pipefail

# Faz backup (banco + media) de todos os clientes gerenciados.
# Uso: sudo ./deploy/scripts/backup_todos.sh
# Variável opcional: BACKUP_DIR (padrão /var/backups/erp)

BACKUP_DIR="${BACKUP_DIR:-/var/backups/erp}"
CLIENTS_DIR="/var/www/clientes"
DATE="$(date +%Y%m%d_%H%M%S)"

if [ "$EUID" -ne 0 ]; then
  echo "ERRO: execute como root (sudo)."
  exit 1
fi

mkdir -p "$BACKUP_DIR"

for marker in "$CLIENTS_DIR"/*/.erp_managed; do
  [ -e "$marker" ] || continue
  client_dir="$(dirname "$marker")"
  slug="$(basename "$client_dir")"
  env_file="${client_dir}/.env"

  DB_NAME="$(grep -E '^DB_NAME=' "$env_file" | cut -d= -f2-)"
  MEDIA_ROOT="$(grep -E '^MEDIA_ROOT=' "$env_file" | cut -d= -f2-)"

  echo ">> Backup ${slug} (${DB_NAME})..."
  ( cd /tmp && sudo -u postgres pg_dump "$DB_NAME" ) | gzip > "${BACKUP_DIR}/${slug}_db_${DATE}.sql.gz"

  if [ -n "$MEDIA_ROOT" ] && [ -d "$MEDIA_ROOT" ]; then
    tar czf "${BACKUP_DIR}/${slug}_media_${DATE}.tar.gz" -C "$MEDIA_ROOT" . || true
  fi
done

# Retenção de 30 dias
find "$BACKUP_DIR" -type f -name '*.gz' -mtime +30 -delete || true

echo ">> Backups em ${BACKUP_DIR}"
