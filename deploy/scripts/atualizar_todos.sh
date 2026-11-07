#!/usr/bin/env bash
set -euo pipefail

# Atualiza o código compartilhado e todos os clientes gerenciados.
# Uso: sudo ./deploy/scripts/atualizar_todos.sh

APP_DIR="/var/www/erp/app"
VENV_DIR="/var/www/erp/venv"
CLIENTS_DIR="/var/www/clientes"
SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"

if [ "$EUID" -ne 0 ]; then
  echo "ERRO: execute como root (sudo)."
  exit 1
fi

# Atualiza o código e reexecuta a versão recém-baixada deste script, para que
# mudanças no próprio atualizar_todos.sh valham já nesta execução.
if [ -z "${ERP_UPDATE_REEXEC:-}" ]; then
  echo ">> Atualizando código em ${APP_DIR}..."
  if ! sudo -u ubuntu git -C "$APP_DIR" pull --ff-only; then
    echo "ERRO: git pull falhou. Verifique 'git -C ${APP_DIR} status' e rode novamente."
    exit 1
  fi
  export ERP_UPDATE_REEXEC=1
  exec "$SCRIPT_PATH" "$@"
fi

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
    '${VENV_DIR}/bin/python' manage.py seed_tabelas_fiscais || true
  "
  systemctl restart "${slug}.service" || echo "AVISO: falha ao reiniciar ${slug}.service"
done

echo ">> Concluído."
