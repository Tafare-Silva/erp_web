#!/usr/bin/env bash
set -euo pipefail

# Atualiza o código compartilhado e todos os clientes gerenciados.
# Uso: sudo ./deploy/scripts/atualizar_todos.sh

APP_DIR="/var/www/erp/app"
VENV_DIR="/var/www/erp/venv"
CLIENTS_DIR="/var/www/clientes"

if [ "$EUID" -ne 0 ]; then
  echo "ERRO: execute como root (sudo)."
  exit 1
fi

echo ">> Atualizando código em ${APP_DIR}..."
sudo -u ubuntu git -C "$APP_DIR" pull --ff-only

echo ">> Instalando dependências..."
"$VENV_DIR/bin/pip" install --upgrade -r "${APP_DIR}/requirements.txt"

for marker in "$CLIENTS_DIR"/*/.erp_managed; do
  [ -e "$marker" ] || continue
  client_dir="$(dirname "$marker")"
  slug="$(basename "$client_dir")"
  env_file="${client_dir}/.env"

  echo ">> Atualizando cliente ${slug}..."
  sudo -u ubuntu bash -c "
    set -a; source '${env_file}'; set +a
    cd '${APP_DIR}'
    '${VENV_DIR}/bin/python' manage.py migrate --noinput
    '${VENV_DIR}/bin/python' manage.py collectstatic --noinput
  "
  systemctl restart "${slug}.service" || echo "AVISO: falha ao reiniciar ${slug}.service"
done

echo ">> Concluído."
