# ERP Web - Sistema de Gestão Empresarial

Sistema ERP desenvolvido em Django para migração de aplicação legada Delphi + PostgreSQL para Web.

## 🚀 Tecnologias

- **Backend:** Django 5.0
- **Banco de Dados:** PostgreSQL (banco existente)
- **Frontend:** Django Templates + Tailwind CSS + HTMX + Alpine.js
- **Python:** 3.10+

## 📋 Pré-requisitos

- Python 3.10 ou superior
- PostgreSQL 12 ou superior
- pip (gerenciador de pacotes Python)
- Acesso ao banco de dados PostgreSQL existente

## 🔧 Instalação

### 1. Clone o repositório (ou use os arquivos fornecidos)

```bash
cd erp_web
```

### 2. Crie um ambiente virtual

```bash
python -m venv venv

# Linux/Mac
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 3. Instale as dependências

```bash
pip install Django==5.0.1
pip install psycopg2-binary
pip install Pillow
pip install python-decouple
pip install validate-docbr
```

### 4. Configure o banco de dados

Edite o arquivo `config/settings.py` e configure a conexão com seu PostgreSQL:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'seu_banco_de_dados',    # Nome do seu banco
        'USER': 'seu_usuario',            # Usuário PostgreSQL
        'PASSWORD': 'sua_senha',          # Senha
        'HOST': 'localhost',              # Host (ou IP do servidor)
        'PORT': '5432',                   # Porta
        'OPTIONS': {
            'options': '-c search_path=cadastros,marilia,public'
        }
    }
}
```

### 5. Teste a conexão

```bash
python manage.py check
```

### 6. Inicie o servidor

```bash
python manage.py runserver
```

Acesse: http://localhost:8000

## 📂 Estrutura do Projeto

```
erp_web/
├── config/                 # Configurações do Django
├── apps/
│   ├── cadastros/         # App de cadastros
│   │   ├── models/        # Models organizados
│   │   ├── views/         # Views
│   │   └── templates/     # Templates
│   └── core/              # Funcionalidades compartilhadas
├── templates/             # Templates globais
├── static/               # Arquivos estáticos
└── manage.py
```

## 🎯 Funcionalidades Implementadas

### ✅ Módulo de Cadastros

- ✅ CRUD completo de Marcas
- ✅ Interface moderna com Tailwind CSS
- ✅ Busca e paginação
- ✅ Models prontos para Pessoas, Produtos, etc

## 🛠️ Comandos Úteis

```bash
python manage.py runserver     # Iniciar servidor
python manage.py check         # Verificar configuração
python manage.py createsuperuser  # Criar admin
```

## 📝 Próximos Passos

1. Implementar CRUD de Pessoas
2. Implementar CRUD de Produtos
3. Adicionar módulo de Vendas
4. Adicionar módulo de Estoque

---

**Desenvolvido com Django + Tailwind CSS + HTMX**
