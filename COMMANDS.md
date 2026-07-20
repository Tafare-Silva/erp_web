# 📝 Comandos Úteis - Django

## Comandos Básicos

### Servidor de Desenvolvimento

```bash
# Iniciar servidor
python manage.py runserver

# Iniciar em porta específica
python manage.py runserver 8080

# Iniciar acessível na rede
python manage.py runserver 0.0.0.0:8000
```

### Migrações

```bash
# Criar migrações
python manage.py makemigrations

# Aplicar migrações
python manage.py migrate

# Ver SQL das migrações
python manage.py sqlmigrate app_name migration_name

# Mostrar migrações
python manage.py showmigrations

# Reverter migração
python manage.py migrate app_name migration_name
```

### Shell Interativo

```bash
# Shell Python com contexto Django
python manage.py shell

# Shell com IPython (se instalado)
python manage.py shell -i ipython

# Shell com BPython (se instalado)
python manage.py shell -i bpython
```

### Usuários

```bash
# Criar superusuário
python manage.py createsuperuser

# Alterar senha de usuário
python manage.py changepassword username
```

## Banco de Dados

### Inspecionar Banco Existente

```bash
# Gerar models a partir do banco de dados
python manage.py inspectdb > apps/cadastros/models_generated.py

# Gerar apenas algumas tabelas
python manage.py inspectdb pessoas produtos > models.py

# Gerar de um schema específico
python manage.py inspectdb --database=default --schema=cadastros
```

### Console do Banco

```bash
# Abrir console do banco de dados
python manage.py dbshell
```

### Backup e Restore

```bash
# Backup do banco PostgreSQL
pg_dump -U usuario -d nome_banco > backup_$(date +%Y%m%d).sql

# Backup com compressão
pg_dump -U usuario -d nome_banco | gzip > backup_$(date +%Y%m%d).sql.gz

# Restore
psql -U usuario -d nome_banco < backup.sql

# Restore com gzip
gunzip -c backup.sql.gz | psql -U usuario -d nome_banco
```

## Desenvolvimento

### Arquivos Estáticos

```bash
# Coletar arquivos estáticos
python manage.py collectstatic

# Sem confirmação
python manage.py collectstatic --noinput

# Limpar arquivos antigos
python manage.py collectstatic --clear
```

### Cache

```bash
# Limpar cache
python manage.py shell
>>> from django.core.cache import cache
>>> cache.clear()
```

### Testes

```bash
# Executar todos os testes
python manage.py test

# Executar testes de um app
python manage.py test apps.cadastros

# Executar teste específico
python manage.py test apps.cadastros.tests.test_models

# Executar com verbosidade
python manage.py test --verbosity=2

# Manter banco de testes
python manage.py test --keepdb
```

### Debug

```bash
# Verificar problemas no projeto
python manage.py check

# Verificar problemas de deploy
python manage.py check --deploy

# Verificar se há migrações pendentes
python manage.py showmigrations
```

## Manipulação de Dados

### Shell Django - Exemplos

```python
# Abrir shell
python manage.py shell

# Importar models
from apps.cadastros.models import Pessoa, Cliente, Produto

# Listar todas as pessoas
pessoas = Pessoa.objects.all()

# Contar registros
Pessoa.objects.count()

# Filtrar
clientes_ativos = Cliente.objects.filter(fk_pessoas__inativo=False)

# Buscar um registro
pessoa = Pessoa.objects.get(chave=1)

# Criar registro
pessoa = Pessoa.objects.create(
    cpf_cnpj='12345678901',
    razao_social='Teste'
)

# Atualizar
pessoa.razao_social = 'Novo Nome'
pessoa.save()

# Deletar
pessoa.delete()

# Raw SQL
from django.db import connection
cursor = connection.cursor()
cursor.execute("SELECT * FROM cadastros.pessoas LIMIT 10")
rows = cursor.fetchall()
```

### Importar dados de CSV

```python
import csv
from apps.cadastros.models import Pessoa

with open('pessoas.csv') as f:
    reader = csv.DictReader(f)
    for row in reader:
        Pessoa.objects.create(
            cpf_cnpj=row['cpf_cnpj'],
            razao_social=row['razao_social'],
            # ... outros campos
        )
```

## Produção

### Gunicorn

```bash
# Instalar
pip install gunicorn

# Executar
gunicorn config.wsgi:application

# Com workers
gunicorn config.wsgi:application --workers 4

# Com bind
gunicorn config.wsgi:application --bind 0.0.0.0:8000

# Com log
gunicorn config.wsgi:application --access-logfile access.log --error-logfile error.log
```

### Systemd Service (Linux)

```bash
# Criar arquivo de serviço
sudo nano /etc/systemd/system/erp_web.service
```

```ini
[Unit]
Description=ERP Web
After=network.target

[Service]
User=seu_usuario
Group=www-data
WorkingDirectory=/caminho/do/projeto
ExecStart=/caminho/do/projeto/venv/bin/gunicorn --workers 3 --bind unix:/caminho/do/projeto/erp_web.sock config.wsgi:application

[Install]
WantedBy=multi-user.target
```

```bash
# Recarregar systemd
sudo systemctl daemon-reload

# Iniciar serviço
sudo systemctl start erp_web

# Habilitar na inicialização
sudo systemctl enable erp_web

# Ver status
sudo systemctl status erp_web

# Reiniciar
sudo systemctl restart erp_web

# Ver logs
sudo journalctl -u erp_web
```

## Git

### Comandos Úteis

```bash
# Iniciar repositório
git init

# Adicionar arquivos
git add .

# Commit
git commit -m "Mensagem"

# Adicionar remote
git remote add origin url_do_repositorio

# Push
git push -u origin main

# Pull
git pull origin main

# Ver status
git status

# Ver diferenças
git diff

# Ver histórico
git log --oneline
```

### .gitignore

Já criado no projeto, mas lembre-se de:

```bash
# Nunca commitar
.env
*.pyc
__pycache__/
db.sqlite3
/media/
/staticfiles/
```

## Manutenção

### Limpeza

```bash
# Remover arquivos .pyc
find . -type f -name '*.pyc' -delete

# Remover __pycache__
find . -type d -name '__pycache__' -delete

# Limpar migrations (cuidado!)
find . -path "*/migrations/*.py" -not -name "__init__.py" -delete
find . -path "*/migrations/*.pyc" -delete
```

### Atualizar Dependências

```bash
# Ver pacotes desatualizados
pip list --outdated

# Atualizar um pacote
pip install --upgrade nome_pacote

# Atualizar requirements.txt
pip freeze > requirements.txt
```

### Monitoramento

```bash
# Ver processos Python
ps aux | grep python

# Ver uso de memória
htop

# Ver logs em tempo real
tail -f /var/log/nginx/error.log
tail -f /var/log/gunicorn/error.log
```

## Atalhos Personalizados

### Criar aliases no .bashrc

```bash
# Editar .bashrc
nano ~/.bashrc

# Adicionar aliases
alias dj='python manage.py'
alias djrun='python manage.py runserver'
alias djmig='python manage.py migrate'
alias djmake='python manage.py makemigrations'
alias djshell='python manage.py shell'
alias djtest='python manage.py test'

# Recarregar
source ~/.bashrc
```

Agora você pode usar:
```bash
djrun  # ao invés de python manage.py runserver
djmig  # ao invés de python manage.py migrate
```

## Troubleshooting

### Erro de Importação

```bash
# Verificar PYTHONPATH
echo $PYTHONPATH

# Adicionar diretório ao PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:/caminho/do/projeto"
```

### Erro de Permissão

```bash
# Dar permissão ao manage.py
chmod +x manage.py

# Dar permissão aos scripts
chmod +x setup.sh
```

### Porta em Uso

```bash
# Ver processo usando porta 8000
lsof -i :8000

# Matar processo
kill -9 PID
```

### Resetar Banco de Dados

```bash
# CUIDADO: Isso apaga todos os dados!
python manage.py flush

# Ou manualmente no PostgreSQL
DROP DATABASE nome_banco;
CREATE DATABASE nome_banco;
python manage.py migrate
```

## Documentação

### Gerar Documentação

```bash
# Instalar sphinx
pip install sphinx

# Iniciar documentação
sphinx-quickstart docs

# Gerar HTML
cd docs
make html
```

---

**Dica:** Mantenha este arquivo aberto enquanto desenvolve para referência rápida!
