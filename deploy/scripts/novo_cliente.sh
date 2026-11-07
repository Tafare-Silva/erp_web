#!/usr/bin/env bash
set -euo pipefail

# ==========================================================================
# Provisiona um novo cliente do ERP (padrão systemd + gunicorn + unix socket)
#
# Uso:
#   sudo ./deploy/scripts/novo_cliente.sh <slug> [dominio]
#
# Exemplo:
#   sudo ./deploy/scripts/novo_cliente.sh cliente1 cliente1.blanjos.com.br
#
# Pré-requisitos (executar uma vez): deploy/scripts/preparar_servidor.sh
# ==========================================================================

SLUG="${1:-}"
DOMAIN="${2:-}"
if [ -z "$SLUG" ]; then
  echo "Uso: sudo $0 <slug> [dominio]"
  exit 1
fi
DOMAIN="${DOMAIN:-${SLUG}.blanjos.com.br}"

if ! [[ "$SLUG" =~ ^[a-z0-9_]+$ ]]; then
  echo "ERRO: slug inválido (use apenas minúsculas, números e underscore)."
  exit 1
fi

APP_DIR="/var/www/erp/app"
VENV_DIR="/var/www/erp/venv"
CLIENT_ROOT="/var/www/clientes/${SLUG}"
DB_NAME="${SLUG}_db"
DB_USER="${SLUG}_user"
SERVICE_FILE="/etc/systemd/system/${SLUG}.service"
NGINX_SITE="/etc/nginx/sites-enabled/${SLUG}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
CERTBOT_EMAIL="${CERTBOT_EMAIL:-}"

if [ "$EUID" -ne 0 ]; then
  echo "ERRO: execute como root (sudo)."
  exit 1
fi

if [ ! -d "$APP_DIR" ]; then
  echo "ERRO: $APP_DIR não existe. Rode antes: sudo deploy/scripts/preparar_servidor.sh"
  exit 1
fi
if [ ! -x "$VENV_DIR/bin/python" ]; then
  echo "ERRO: venv compartilhado não encontrado em $VENV_DIR."
  exit 1
fi

psql_su() { ( cd /tmp && sudo -u postgres psql "$@" ); }

ENV_FILE="${CLIENT_ROOT}/.env"

# --------------------------------------------------------------------------
# 1. Diretórios + senha (reaproveita a do .env em reexecuções)
# --------------------------------------------------------------------------
echo ">> Criando diretórios em ${CLIENT_ROOT}..."
mkdir -p "${CLIENT_ROOT}/staticfiles" "${CLIENT_ROOT}/media"

if [ -f "$ENV_FILE" ]; then
  DB_PASS="$(grep -E '^DB_PASSWORD=' "$ENV_FILE" | cut -d= -f2- | head -n1 || true)"
fi
DB_PASS="${DB_PASS:-$(openssl rand -hex 16)}"

# --------------------------------------------------------------------------
# 2. Banco de dados
# --------------------------------------------------------------------------
echo ">> Criando role/database ${DB_NAME}..."
if ! psql_su -tAc "SELECT 1 FROM pg_roles WHERE rolname='${DB_USER}'" | grep -q 1; then
  psql_su -c "CREATE ROLE ${DB_USER} LOGIN PASSWORD '${DB_PASS}';"
else
  psql_su -c "ALTER ROLE ${DB_USER} WITH LOGIN PASSWORD '${DB_PASS}';"
fi

if ! psql_su -tAc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" | grep -q 1; then
  ( cd /tmp && sudo -u postgres createdb -O "${DB_USER}" "${DB_NAME}" )
fi

# --------------------------------------------------------------------------
# 3. Arquivo .env (não sobrescreve se já existir)
# --------------------------------------------------------------------------
if [ -f "$ENV_FILE" ]; then
  echo ">> .env já existe, mantendo o atual."
else
  echo ">> Gerando ${ENV_FILE}..."
  SECRET_KEY="$(openssl rand -hex 50)"
  # Branding do cliente (Blanjos Sistemas por padrão; use Dator Sistemas se preferir).
  # Pode ser sobrescrito por variáveis de ambiente ao rodar o script.
  BRAND_NAME="${BRAND_NAME:-Blanjos Sistemas}"
  BRAND_SHORT_NAME="${BRAND_SHORT_NAME:-Blanjos}"
  BRAND_TAGLINE="${BRAND_TAGLINE:-Gestão Inteligente}"
  BRAND_LOGO_URL="${BRAND_LOGO_URL:-}"
  cat > "$ENV_FILE" <<EOF
SECRET_KEY=${SECRET_KEY}
DEBUG=False
ALLOWED_HOSTS=${DOMAIN}
CSRF_TRUSTED_ORIGINS=https://${DOMAIN}

DB_NAME=${DB_NAME}
DB_USER=${DB_USER}
DB_PASSWORD=${DB_PASS}
DB_HOST=127.0.0.1
DB_PORT=5432
DB_SEARCH_PATH=public

STATIC_ROOT=${CLIENT_ROOT}/staticfiles
MEDIA_ROOT=${CLIENT_ROOT}/media

SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True

BRAND_NAME=${BRAND_NAME}
BRAND_SHORT_NAME=${BRAND_SHORT_NAME}
BRAND_TAGLINE=${BRAND_TAGLINE}
BRAND_LOGO_URL=${BRAND_LOGO_URL}
EOF
fi

# marcador que identifica clientes gerenciados por estes scripts
touch "${CLIENT_ROOT}/.erp_managed"

chown -R ubuntu:www-data "${CLIENT_ROOT}"
chmod 640 "$ENV_FILE"

# --------------------------------------------------------------------------
# 4. Migrations + static
# --------------------------------------------------------------------------
echo ">> Rodando migrate e collectstatic..."
sudo -u ubuntu bash -c "
  set -a
  source '${ENV_FILE}'
  set +a
  cd '${APP_DIR}'
  '${VENV_DIR}/bin/python' manage.py migrate --noinput
  '${VENV_DIR}/bin/python' manage.py collectstatic --noinput
  # Tabelas fiscais e de localidades (estados, cidades/IBGE, NCM, CFOP, CST)
  '${VENV_DIR}/bin/python' manage.py seed_tabelas_fiscais || true
"

# --------------------------------------------------------------------------
# 5. Serviço systemd
# --------------------------------------------------------------------------
echo ">> Instalando serviço systemd ${SLUG}.service..."
sed "s/__SLUG__/${SLUG}/g" "${TEMPLATE_DIR}/systemd/cliente.service.template" > "$SERVICE_FILE"
systemctl daemon-reload
systemctl enable --now "${SLUG}.service"

# --------------------------------------------------------------------------
# 6. Nginx
# --------------------------------------------------------------------------
echo ">> Criando site Nginx para ${DOMAIN}..."
if [ ! -f "$NGINX_SITE" ]; then
  sed -e "s/__SLUG__/${SLUG}/g" -e "s/__DOMAIN__/${DOMAIN}/g" \
    "${TEMPLATE_DIR}/nginx/cliente.conf.template" > "$NGINX_SITE"
fi
nginx -t
systemctl reload nginx

# --------------------------------------------------------------------------
# 7. Certificado SSL
# --------------------------------------------------------------------------
echo ">> Emitindo certificado SSL para ${DOMAIN}..."
if [ -n "$CERTBOT_EMAIL" ]; then
  certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos -m "$CERTBOT_EMAIL" --redirect || \
    echo "AVISO: falha ao emitir SSL. Verifique o DNS e rode o certbot manualmente."
else
  certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos \
    --register-unsafely-without-email --redirect || \
    echo "AVISO: SSL não emitido. Defina CERTBOT_EMAIL e rode novamente."
fi

# --------------------------------------------------------------------------
# 8. Superusuário
# --------------------------------------------------------------------------
if [ -n "${DJANGO_SUPERUSER_PASSWORD:-}" ] && [ -n "${DJANGO_SUPERUSER_EMAIL:-}" ]; then
  echo ">> Criando superusuário..."
  sudo -u ubuntu bash -c "
    set -a; source '${ENV_FILE}'; set +a
    cd '${APP_DIR}'
    DJANGO_SUPERUSER_PASSWORD='${DJANGO_SUPERUSER_PASSWORD}' \
    '${VENV_DIR}/bin/python' manage.py createsuperuser --noinput \
      --username '${DJANGO_SUPERUSER_USERNAME:-admin}' \
      --email '${DJANGO_SUPERUSER_EMAIL}'
  "
else
  echo ">> Crie o superusuário manualmente:"
  echo "   sudo -u ubuntu bash -c 'set -a; source ${ENV_FILE}; set +a; cd ${APP_DIR}; ${VENV_DIR}/bin/python manage.py createsuperuser'"
fi

echo ""
echo "=========================================================="
echo " Cliente ${SLUG} provisionado!"
echo " URL: https://${DOMAIN}"
echo " Marca: ${BRAND_NAME:-Blanjos Sistemas}"
echo " Banco: ${DB_NAME} (role ${DB_USER})"
echo " Serviço: systemctl status ${SLUG}.service"
echo "=========================================================="
echo "Checklist de onboarding no ERP:"
echo "  1. Cadastrar Empresa + endereço principal"
echo "  2. IE/CRT/uf_web_service_nfe/cidade_sede, séries e numeração"
echo "  3. ambiente_destino = H (homologação)"
echo "  4. Subir certificado A1 (.pfx) + senha"
echo "  5. CSC apenas se NFC-e; CSRT deixar vazio"
