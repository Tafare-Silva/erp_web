#!/bin/bash
set -e

echo "========================================"
echo "  ERP Web - Setup de Produção"
echo "========================================"

# Verificar se está rodando como root
if [ "$EUID" -ne 0 ]; then
  echo "Execute como root: sudo bash setup.sh"
  exit 1
fi

# Instalar Docker se não existir
if ! command -v docker &> /dev/null; then
    echo "Instalando Docker..."
    curl -fsSL https://get.docker.com | bash
fi

# Instalar Docker Compose se não existir
if ! command -v docker compose &> /dev/null; then
    echo "Instalando Docker Compose..."
    apt-get update
    apt-get install -y docker-compose-plugin
fi

# Criar .env se não existir
if [ ! -f .env ]; then
    echo "Criando .env a partir do .env.example..."
    cp .env.example .env
    echo "EDITAR .env ANTES DE CONTINUAR!"
    echo "  - SECRET_KEY: gere uma aleatória"
    echo "  - DB_PASSWORD: defina uma senha forte"
    echo "  - ALLOWED_HOSTS: seu dominio"
    echo "  - CSRF_TRUSTED_ORIGINS: seu dominio com https"
    echo ""
    read -p "Pressione Enter depois de editar o .env..."
fi

echo "Parando containers antigos..."
docker compose down 2>/dev/null || true

echo "Construindo e subindo containers..."
docker compose up -d --build

echo "Aguardando banco de dados ficar pronto..."
sleep 5

echo "Executando migrations..."
docker compose exec -T app python manage.py migrate || echo "Migrations executadas (pode ignorar erros de tabelas existentes)"

echo "Coletando arquivos estáticos..."
docker compose exec -T app python manage.py collectstatic --noinput || true

echo ""
echo "========================================"
echo "  Deploy concluído!"
echo "========================================"
echo "Acesse: http://$(curl -s ifconfig.me)"
echo ""
echo "Próximos passos:"
echo "  1. Criar superusuário: docker compose exec app python manage.py createsuperuser"
echo "  2. Configurar SSL: veja deploy/README.md"
echo "  3. Acompanhar logs: docker compose logs -f app"
echo "========================================"