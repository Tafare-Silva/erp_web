#!/usr/bin/env bash
set -euo pipefail

# ==========================================================================
# Preparação única do servidor:
#   - swap (evita OOM com os outros serviços)
#   - código compartilhado em /var/www/erp/app
#   - virtualenv compartilhado em /var/www/erp/venv
#
# Uso: sudo ./deploy/scripts/preparar_servidor.sh
# ==========================================================================

REPO_URL="${REPO_URL:-https://github.com/Tafare-Silva/erp_web.git}"
BRANCH="${BRANCH:-master}"
APP_DIR="/var/www/erp/app"
VENV_DIR="/var/www/erp/venv"
SWAP_SIZE="${SWAP_SIZE:-2G}"

if [ "$EUID" -ne 0 ]; then
  echo "ERRO: execute como root (sudo)."
  exit 1
fi

# 1. Swap
if ! swapon --show | grep -q '/swapfile'; then
  echo ">> Criando swap de ${SWAP_SIZE}..."
  fallocate -l "$SWAP_SIZE" /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  grep -q '^/swapfile ' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
else
  echo ">> Swap já ativo."
fi

# 2. Dependências de sistema
command -v git >/dev/null || apt-get install -y git
command -v certbot >/dev/null || apt-get install -y certbot python3-certbot-nginx
dpkg -s python3-venv >/dev/null 2>&1 || apt-get install -y python3-venv

# 3. Código compartilhado
mkdir -p /var/www/erp
chown -R ubuntu:www-data /var/www/erp
if [ ! -d "$APP_DIR/.git" ]; then
  echo ">> Clonando repositório em ${APP_DIR}..."
  sudo -u ubuntu git clone -b "$BRANCH" "$REPO_URL" "$APP_DIR"
else
  echo ">> Atualizando repositório existente..."
  sudo -u ubuntu git -C "$APP_DIR" pull --ff-only
fi

# 4. Virtualenv
if [ ! -x "$VENV_DIR/bin/python" ]; then
  echo ">> Criando virtualenv em ${VENV_DIR}..."
  sudo -u ubuntu python3 -m venv "$VENV_DIR"
fi
sudo -u ubuntu "$VENV_DIR/bin/pip" install --upgrade pip
sudo -u ubuntu "$VENV_DIR/bin/pip" install -r "${APP_DIR}/requirements.txt"

chown -R ubuntu:www-data /var/www/erp

echo ">> Servidor preparado. Próximo passo: sudo deploy/scripts/novo_cliente.sh <slug>"
