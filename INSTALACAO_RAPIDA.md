# 🚀 Guia Rápido de Instalação - ERP Web

## ⚡ Instalação Rápida (5 minutos)

### 1. Descompacte o Projeto
```bash
unzip erp_web_projeto_completo.zip
cd erp_web
```

### 2. Crie o Ambiente Virtual
```bash
# Linux/Mac
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

### 3. Instale as Dependências
```bash
pip install -r requirements.txt
```

**OU** instalação mínima (mais rápido):
```bash
pip install Django==5.0.1 psycopg2-binary Pillow
```

### 4. Configure o Banco de Dados

**Opção A: Editar diretamente o settings.py**

Abra `config/settings.py` e altere:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'seu_banco',        # ← ALTERE AQUI
        'USER': 'seu_usuario',      # ← ALTERE AQUI
        'PASSWORD': 'sua_senha',    # ← ALTERE AQUI
        'HOST': 'localhost',
        'PORT': '5432',
        'OPTIONS': {
            'options': '-c search_path=cadastros,marilia,public'
        }
    }
}
```

**Opção B: Usar arquivo .env (recomendado para produção)**

1. Copie o arquivo de exemplo:
```bash
cp .env.example .env
```

2. Edite o `.env`:
```
DB_NAME=seu_banco
DB_USER=seu_usuario
DB_PASSWORD=sua_senha
DB_HOST=localhost
DB_PORT=5432
```

3. Renomeie o settings alternativo:
```bash
mv config/settings.py config/settings_original.py
mv config/settings_com_env.py config/settings.py
```

### 5. Teste a Conexão
```bash
python manage.py check
```

Se aparecer **"System check identified no issues (0 silenced)"**, está tudo OK! ✅

### 6. Rode o Servidor
```bash
python manage.py runserver
```

### 7. Acesse o Sistema
Abra seu navegador em: **http://localhost:8000**

- Dashboard: http://localhost:8000
- Marcas: http://localhost:8000/cadastros/marcas/
- Admin: http://localhost:8000/admin (precisa criar superuser)

## 🎯 Primeira Utilização

### Testando o CRUD de Marcas

1. Acesse: http://localhost:8000/cadastros/marcas/
2. Clique em "Nova Marca"
3. Digite um nome (ex: "Nike")
4. Salve

Pronto! Você acabou de criar seu primeiro registro no sistema web! 🎉

### Criando um Superusuário (opcional)

Para acessar o Admin do Django:

```bash
python manage.py createsuperuser
```

Preencha os dados solicitados e acesse: http://localhost:8000/admin

## ⚠️ Solução de Problemas

### Erro: "no module named 'django'"
**Solução:** Ative o ambiente virtual
```bash
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

### Erro: "could not connect to server"
**Solução:** Verifique se o PostgreSQL está rodando e as credenciais estão corretas.

### Erro: "relation does not exist"
**Solução:** Verifique se a tabela existe no schema correto do banco de dados.

### Porta 8000 já em uso
**Solução:** Use outra porta
```bash
python manage.py runserver 8080
```

## 📦 Estrutura de Arquivos Principais

```
erp_web/
├── config/
│   └── settings.py          ← Configure aqui o banco
├── apps/
│   └── cadastros/
│       ├── models/          ← Models já criados
│       ├── views/           ← Views (Marcas pronto)
│       └── templates/       ← Templates HTML
├── templates/
│   └── base.html           ← Template base
├── manage.py               ← Script principal
├── requirements.txt        ← Dependências
└── .env.example           ← Exemplo de configuração
```

## 🎓 Próximos Passos

Depois de testar o CRUD de Marcas:

1. **Estude o código** de `apps/cadastros/views/marca_views.py`
2. **Copie o padrão** para criar CRUD de Pessoas
3. **Leia** o arquivo `GUIA_CONTINUACAO.md`
4. **Implemente** novos módulos seguindo o mesmo padrão

## 💡 Dicas

- Use `python manage.py shell` para testar queries
- Consulte `README.md` para documentação completa
- Veja `PLANEJAMENTO_PROJETO.md` para entender a arquitetura

## 📞 Comandos Úteis

```bash
# Ver todas as URLs do projeto
python manage.py show_urls  # (requer django-extensions)

# Acessar shell do Django
python manage.py shell

# Verificar problemas
python manage.py check

# Rodar na rede local
python manage.py runserver 0.0.0.0:8000
```

## ✅ Checklist de Instalação

- [ ] Ambiente virtual criado e ativado
- [ ] Dependências instaladas
- [ ] Banco de dados configurado
- [ ] `python manage.py check` sem erros
- [ ] Servidor rodando
- [ ] Acesso ao sistema pelo navegador
- [ ] CRUD de Marcas funcionando

---

**Pronto! Seu ERP Web está rodando! 🚀**

Em caso de dúvida, consulte os outros documentos de guia fornecidos.
