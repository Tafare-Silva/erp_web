# Deploy do ERP Web — multi-cliente (systemd + Gunicorn)

Este diretório define o padrão de implantação **um cliente por instância** (single-tenant),
seguindo o modelo já usado no servidor DigitalOcean (systemd + Gunicorn + socket Unix + Nginx).
**Não usamos Docker em produção.** Os `Dockerfile`/`docker-compose.yml` ficam apenas para
desenvolvimento local.

## Arquitetura

```
/var/www/erp/
├── app/                     # código compartilhado (clone do repositório)
└── venv/                    # virtualenv compartilhado

/var/www/clientes/<slug>/
├── .env                     # configuração exclusiva do cliente
├── .erp_managed             # marcador: cliente gerenciado pelos scripts
├── staticfiles/             # collectstatic deste cliente
├── media/                   # uploads deste cliente
└── <slug>.sock              # socket do Gunicorn
```

Cada cliente tem: banco próprio (`<slug>_db`), role própria (`<slug>_user`),
serviço systemd (`<slug>.service`) e site Nginx (`<slug>` em `sites-enabled`).

## Preparação única do servidor

```bash
# na raiz do repositório clonado temporariamente no servidor
sudo ./deploy/scripts/preparar_servidor.sh
```

O script:
1. cria swap de 2 GB (`/swapfile`, persistido no `/etc/fstab`) — obrigatório, o droplet tem ~2 GB de RAM;
2. instala `git`, `certbot`/`python3-certbot-nginx` e `python3-venv` se faltarem;
3. clona o repositório em `/var/www/erp/app`;
4. cria o venv em `/var/www/erp/venv` e instala `requirements.txt`.

Variáveis opcionais: `REPO_URL`, `BRANCH` (padrão `master`), `SWAP_SIZE` (padrão `2G`).

> Se o repositório for privado, configure a credencial do usuário `ubuntu`
> (`sudo -u ubuntu git config --global credential.helper store` + clone uma vez) antes de rodar.

## Provisionar um cliente

```bash
sudo ./deploy/scripts/novo_cliente.sh <slug> [dominio]
# exemplo:
sudo ./deploy/scripts/novo_cliente.sh cliente1 cliente1.blanjos.com.br
```

O `slug` deve conter apenas `a-z`, `0-9` e `_`. O domínio padrão é `<slug>.blanjos.com.br`.

O script executa, em ordem:
1. cria role e banco no PostgreSQL (`<slug>_user` / `<slug>_db`);
2. cria `/var/www/clientes/<slug>/` com `staticfiles/` e `media/`;
3. gera o `.env` (não sobrescreve se já existir);
4. roda `migrate`, `collectstatic` e importa os NCMs básicos (e a tabela completa se `data/ncm.csv` existir);
5. instala e sobe o serviço systemd (`gunicorn`, 2 workers, socket Unix);
6. cria o site Nginx (HTTP) e recarrega o Nginx;
7. emite o certificado SSL via Certbot (`--redirect`);
8. opcionalmente cria o superusuário.

Variáveis de ambiente úteis:
```bash
CERTBOT_EMAIL=admin@blanjos.com.br \
DJANGO_SUPERUSER_EMAIL=admin@cliente.com \
DJANGO_SUPERUSER_PASSWORD='SenhaForte' \
DJANGO_SUPERUSER_USERNAME=admin \
sudo -E ./deploy/scripts/novo_cliente.sh cliente1
```

> Antes de rodar, crie o registro **DNS A** `<slug>.blanjos.com.br` apontando para o IP do droplet.
> Sem DNS propagado o Certbot falha (o restante do provisionamento continua; rode o Certbot depois).

## Branding por cliente

A marca exibida (login, título e sidebar) vem do `.env` do cliente. Padrão **Blanjos Sistemas**;
para usar **Dator Sistemas**, sobrescreva ao provisionar:

```bash
BRAND_NAME='Dator Sistemas' BRAND_SHORT_NAME='Dator' \
  sudo -E ./deploy/scripts/novo_cliente.sh cliente1
```

Variáveis: `BRAND_NAME`, `BRAND_SHORT_NAME`, `BRAND_TAGLINE`, `BRAND_LOGO_URL`
(URL absoluta ou caminho em `/static/`; vazio usa o ícone padrão).
Em cliente já existente, basta editar o `.env` e reiniciar o serviço.

## Tabela completa de NCM

O sistema já permite pesquisar/criar NCM na tela de produto. Para carregar a tabela oficial
completa (~10 mil itens), coloque o arquivo em `data/ncm.csv` (ou `.xlsx`) no servidor e rode:

```bash
cd /var/www/erp/app
sudo -u ubuntu bash -c 'set -a; source /var/www/clientes/<slug>/.env; set +a; \
  /var/www/erp/venv/bin/python manage.py importar_ncms --arquivo data/ncm.csv'
```

O importador aceita CSV (`;` ou `,`) e XLSX, de arquivo local (`--arquivo`) ou URL (`--url`),
com cabeçalho flexível (colunas de código e descrição). Se o arquivo estiver em `data/ncm.csv`,
o `novo_cliente.sh` já o importa automaticamente no provisionamento.

## Atualizar todos os clientes

```bash
sudo ./deploy/scripts/atualizar_todos.sh
```

Faz `git pull --ff-only` no código compartilhado, atualiza dependências, roda
`migrate` + `collectstatic` e reinicia cada serviço marcado com `.erp_managed`.
O cliente legado `erp_web` (demo) **não** possui o marcador e é ignorado.

## Backup

```bash
sudo ./deploy/scripts/backup_todos.sh
```

Gera, em `/var/backups/erp` (ou `BACKUP_DIR`), um dump `.sql.gz` e um `.tar.gz` de `media`
por cliente. Retenção automática de 30 dias.

Sugestão de cron diário (03:00):
```cron
0 3 * * * root /var/www/erp/app/deploy/scripts/backup_todos.sh >> /var/log/erp_backup.log 2>&1
```

## Onboarding do cliente após o provisionamento

No admin do ERP (`https://<dominio>/admin/`), na ordem:
1. **Empresa** + endereço principal;
2. **IE / CRT / `uf_web_service_nfe` / `cidade_sede`**, séries e numeração;
3. `ambiente_destino = H` (homologação);
4. certificado **A1 (.pfx)** + senha;
5. **CSC** apenas se for emitir NFC-e — **CSRT deixar vazio**.

## Variáveis de configuração relevantes

`config/settings.py` lê do `.env`:
- `DB_SEARCH_PATH` — padrão `cadastros,marilia,public` (bancos legados); novos clientes usam `public`.
- `STATIC_ROOT` / `MEDIA_ROOT` — por cliente (ver `.env` gerado).
- `SESSION_COOKIE_SECURE` / `CSRF_COOKIE_SECURE` — `True` em produção.

## Observações

- **RAM:** ~2 GB no droplet. Com swap de 2 GB cabem 1–2 clientes confortavelmente;
  para mais, faça resize do droplet.
- **Static/Media** são servidos pelo Nginx via `alias` (sem WhiteNoise).
- O deploy da demo antiga (`/var/www/clientes/erp_web`) permanece intocado.
