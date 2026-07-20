# Deploy na DigitalOcean

## Pré-requisitos

- Docker e Docker Compose instalados no droplet
- Domínio apontado para o IP do droplet
- PostgreSQL gerenciado pela DigitalOcean (opcional, usar container)

## 1. Gerar SECRET_KEY

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

## 2. Configurar variáveis de ambiente

```bash
cp .env.example .env.production
# Editar SECRET_KEY, DB_PASSWORD, ALLOWED_HOSTS, CSRF_TRUSTED_ORIGINS
```

## 3. Deploy com Docker Compose (recomendado)

```bash
# Enviar arquivos para o servidor
rsync -avz --exclude 'venv/' --exclude '.git/' --exclude '__pycache__/' --exclude 'media/' --exclude 'staticfiles/' ./ usuario@servidor:~/erp_web/

# Acessar o servidor e deploy
ssh usuario@servidor
cd ~/erp_web

# Criar .env a partir do exemplo
cp .env.example .env
nano .env   # Ajustar credenciais

# Subir tudo
docker compose up -d --build
```

## 4. Migrations e primeiro acesso

```bash
# Executar migrations
docker compose exec app python manage.py migrate

# Criar superusuário
docker compose exec app python manage.py createsuperuser
```

## 5. Nginx + SSL (Let's Encrypt)

```bash
docker compose exec nginx apk add certbot certbot-nginx
docker compose exec nginx certbot --nginx -d seudominio.com.br -d www.seudominio.com.br
```

## Comandos úteis

```bash
# Ver logs
docker compose logs -f app

# Reiniciar app
docker compose restart app

# Shell no Django
docker compose exec app python manage.py shell

# Backup do banco
docker compose exec db pg_dump -U postgres erp_db > backup_$(date +%Y%m%d).sql
```