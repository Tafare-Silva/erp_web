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
4. roda `migrate`, `collectstatic` e `seed_tabelas_fiscais` (estados, cidades/IBGE, NCM, CFOP e CST);
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

## Tabelas fiscais e localidades

O comando `seed_tabelas_fiscais` popula, de forma idempotente:

- **Estados** (27) e **cidades** com código IBGE (5.571, base oficial do IBGE);
- **NCM** (~10.515 códigos de 8 dígitos) — `apps/cadastros/management/data/ncm.csv`;
- **CFOP** (619 códigos vigentes) — `apps/cadastros/management/data/cfop.csv`;
- **CST** de ICMS/CSOSN, PIS, COFINS e IPI.

Ele roda automaticamente no `novo_cliente.sh` e no `atualizar_todos.sh`. Para rodar manualmente:

```bash
cd /var/www/erp/app
sudo -u ubuntu bash -c 'set -a; source /var/www/clientes/<slug>/.env; set +a; \
  /var/www/erp/venv/bin/python manage.py seed_tabelas_fiscais'
```

Opções: `--skip-cidades`, `--skip-ncm`, `--skip-cfop`, `--skip-cst`.
Para atualizar as bases, substitua os arquivos em `apps/cadastros/management/data/`
(fontes públicas: IBGE e tabelasfiscais.com.br/Receita Federal/CONFAZ) e rode de novo.

> Para uma NCM específica fora da base, a tela de produto permite criar na hora (botão “+”).
> O comando `importar_ncms --arquivo <csv/xlsx>` continua disponível para cargas personalizadas.

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
