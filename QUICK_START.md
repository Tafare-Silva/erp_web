# 🚀 Quick Start - ERP Web

## Início Rápido em 5 Minutos

### 1. Extrair o Projeto

Se você baixou o arquivo compactado:

```bash
tar -xzf erp_web.tar.gz
cd erp_web
```

### 2. Configurar Ambiente

```bash
# Executar script de setup automático (Linux/Mac)
chmod +x setup.sh
./setup.sh
```

**OU manualmente:**

```bash
# Criar ambiente virtual
python3 -m venv venv

# Ativar ambiente virtual
# Linux/Mac:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# Instalar dependências
pip install -r requirements.txt
```

### 3. Configurar Banco de Dados

Copie `.env.example` para `.env` e configure:

```bash
cp .env.example .env
nano .env  # ou use seu editor preferido
```

**Configure as variáveis:**

```env
DB_NAME=seu_banco_de_dados
DB_USER=seu_usuario
DB_PASSWORD=sua_senha
DB_HOST=localhost
DB_PORT=5432
```

### 4. Executar Migrações

```bash
python manage.py migrate
```

**IMPORTANTE:** Como usamos `managed=False` nos models, as migrações só criam tabelas internas do Django (auth, sessions, etc). Suas tabelas existentes do PostgreSQL não serão alteradas.

### 5. Criar Superusuário

```bash
python manage.py createsuperuser
```

### 6. Iniciar Servidor

```bash
python manage.py runserver
```

Acesse: **http://localhost:8000**

## ✅ Checklist de Verificação

- [ ] Python 3.10+ instalado
- [ ] PostgreSQL rodando
- [ ] Banco de dados configurado
- [ ] Arquivo .env criado e configurado
- [ ] Dependências instaladas
- [ ] Migrações executadas
- [ ] Superusuário criado
- [ ] Servidor rodando

## 🎯 Primeiros Passos

### 1. Fazer Login

Acesse `http://localhost:8000` e faça login com o superusuário criado.

### 2. Explorar o Sistema

- **Dashboard:** Página inicial com resumo
- **Cadastros → Pessoas:** Lista de todas as pessoas
- **Cadastros → Clientes:** Lista de clientes
- **Cadastros → Fornecedores:** Lista de fornecedores
- **Cadastros → Produtos:** Lista de produtos

### 3. Admin do Django

Acesse `http://localhost:8000/admin` para usar a interface administrativa do Django.

## 📚 Documentação

Consulte os seguintes documentos:

- **README.md** - Visão geral e instalação completa
- **ARCHITECTURE.md** - Arquitetura e decisões técnicas
- **ROADMAP.md** - Funcionalidades atuais e futuras
- **COMMANDS.md** - Comandos úteis do Django
- **CONTRIBUTING.md** - Guia de contribuição

## 🔧 Comandos Rápidos

```bash
# Iniciar servidor
python manage.py runserver

# Acessar shell Django
python manage.py shell

# Executar testes
python manage.py test

# Criar nova migração
python manage.py makemigrations

# Aplicar migrações
python manage.py migrate
```

## 🐛 Problemas Comuns

### Erro de conexão com banco de dados

**Problema:** `FATAL: password authentication failed`

**Solução:** Verifique as credenciais no arquivo `.env`

### Porta 8000 em uso

**Problema:** `Error: That port is already in use`

**Solução:** Use outra porta ou mate o processo:
```bash
# Linux/Mac
lsof -ti:8000 | xargs kill -9

# Ou use outra porta
python manage.py runserver 8080
```

### Módulo não encontrado

**Problema:** `ModuleNotFoundError: No module named 'django'`

**Solução:** Ative o ambiente virtual:
```bash
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

### Tabelas não aparecem

**Problema:** Views retornam vazio

**Solução:** 
1. Verifique se o banco está configurado corretamente
2. Verifique se os schemas `cadastros` e `marilia` existem
3. Teste a conexão no shell:
```python
python manage.py shell
>>> from apps.cadastros.models import Pessoa
>>> Pessoa.objects.count()
```

## 🎨 Estrutura Atual

```
erp_web/
├── apps/
│   ├── core/          # Dashboard e autenticação
│   └── cadastros/     # Pessoas, Clientes, Fornecedores, Produtos
├── config/            # Configurações Django
├── templates/         # Templates HTML
└── manage.py
```

## 📦 Próximos Módulos

Veja `ROADMAP.md` para lista completa, mas os próximos são:

1. **Formulários de CRUD** - Criar/Editar cadastros
2. **Vendas** - Pedidos de venda
3. **Financeiro** - Contas a pagar/receber
4. **Estoque** - Controle de estoque
5. **Fiscal** - NFe e NFCe

## 💡 Dicas

1. **Desenvolvimento:** Use `DEBUG=True` no `.env`
2. **Produção:** Nunca use `DEBUG=True` em produção!
3. **Backup:** Faça backup regular do banco de dados
4. **Git:** Não commite o arquivo `.env`
5. **Logs:** Cheque os logs se algo não funcionar

## 🆘 Precisa de Ajuda?

1. Leia a documentação no projeto
2. Verifique os logs de erro
3. Use `python manage.py check` para verificar problemas
4. Consulte a documentação oficial do Django: https://docs.djangoproject.com

## 🎉 Tudo Pronto!

Agora você pode começar a desenvolver! 

Explore o código, faça modificações, adicione funcionalidades e customize conforme necessário.

**Boa sorte! 🚀**
