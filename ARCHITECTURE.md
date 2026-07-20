# 🏗️ Arquitetura do ERP Web

## Visão Geral

Este documento descreve a arquitetura técnica do sistema ERP Web, desenvolvido para migrar um sistema legado em Delphi para uma plataforma web moderna.

## Stack Tecnológica

### Backend

- **Django 5.0:** Framework web Python maduro e robusto
- **PostgreSQL:** Banco de dados relacional (reaproveitando estrutura existente)
- **Python 3.10+:** Linguagem de programação

### Frontend

- **Django Templates:** Sistema de templates nativo do Django
- **Tailwind CSS:** Framework CSS utility-first para UI moderna
- **HTMX:** Biblioteca para AJAX sem JavaScript complexo
- **Alpine.js:** Framework JavaScript minimalista para interatividade

### Por que essa stack?

1. **Django Templates vs SPA (React/Vue/Angular):**
   - Menor curva de aprendizado
   - Menos complexidade no deploy
   - SSR (Server-Side Rendering) nativo
   - SEO-friendly
   - Melhor para aplicações CRUD tradicionais
   - Time pequeno ou desenvolvedor solo

2. **HTMX + Alpine.js:**
   - Interatividade sem frameworks pesados
   - Mantém simplicidade do backend
   - Progressive Enhancement
   - Menor bundle size
   - Menos JavaScript para manter

3. **Tailwind CSS:**
   - Desenvolvimento rápido
   - Consistência visual
   - Responsivo por padrão
   - Fácil customização

## Estrutura do Projeto

```
erp_web/
├── apps/                   # Aplicações Django
│   ├── core/              # App central (auth, dashboard)
│   ├── cadastros/         # Cadastros mestres
│   ├── vendas/           # [Futuro] Pedidos e vendas
│   ├── financeiro/       # [Futuro] Contas a pagar/receber
│   ├── estoque/          # [Futuro] Controle de estoque
│   └── fiscal/           # [Futuro] NFe, NFCe
├── config/                # Configurações Django
├── templates/            # Templates globais
├── static/              # CSS, JS, imagens
├── media/               # Uploads de usuários
└── manage.py
```

### Organização por Apps

Cada módulo do ERP é um app Django separado:

- **Separação de responsabilidades**
- **Fácil manutenção**
- **Possibilidade de reutilização**
- **Deploy incremental**

## Banco de Dados

### Estratégia: Database-First

O projeto usa uma abordagem **database-first**, onde o banco de dados já existe e o Django apenas mapeia as tabelas existentes.

#### Models com `managed = False`

```python
class Pessoa(models.Model):
    # ... campos ...
    
    class Meta:
        managed = False  # Django NÃO gerencia esta tabela
        db_table = 'pessoas'  # Nome real da tabela
```

**Vantagens:**
- Reutiliza estrutura existente
- Sistema Delphi e Django podem coexistir
- Migração gradual possível
- Dados preservados

**Desvantagens:**
- Não pode usar migrations para alterar schema
- Alterações de estrutura devem ser feitas manualmente no banco

### Schemas PostgreSQL

O banco usa múltiplos schemas:

```
├── cadastros/    # Tabelas de cadastros
├── marilia/      # Movimentações e transações
├── app/          # Dados do app mobile
└── audit/        # Logs de auditoria
```

**Configuração no Django:**
```python
DATABASES = {
    'default': {
        # ...
        'OPTIONS': {
            'options': '-c search_path=cadastros,marilia,public'
        }
    }
}
```

### Relacionamentos

Os relacionamentos seguem a convenção do banco existente:

```python
# FK usando convenção do banco legado
fk_cidades_cidade = models.ForeignKey(
    'Cidade',
    db_column='fk_cidades$cidade',  # Nome real no banco
    on_delete=models.PROTECT
)
```

## Padrões de Código

### Views

Usando Function-Based Views (FBV) para simplicidade:

```python
@login_required
def pessoa_list(request):
    # Lógica da view
    return render(request, 'template.html', context)
```

**Por que FBV e não CBV?**
- Mais explícitas e fáceis de entender
- Menos "mágica" do Django
- Melhor para iniciantes
- Suficiente para 90% dos casos

### Templates

Estrutura de herança:

```
base.html
├── core/dashboard.html
├── cadastros/pessoa_list.html
├── cadastros/pessoa_detail.html
└── ...
```

**Componentes reutilizáveis:**
- Navbar
- Mensagens
- Formulários
- Tabelas

### Formulários

Usando `widget_tweaks` para customizar forms no template:

```html
{% load widget_tweaks %}
{{ form.campo|add_class:"classe-tailwind" }}
```

## Frontend

### Tailwind CSS

Usando via CDN para desenvolvimento:

```html
<script src="https://cdn.tailwindcss.com"></script>
```

**Para produção:** Compilar Tailwind localmente para reduzir tamanho.

### HTMX

Trocas parciais de conteúdo:

```html
<div hx-get="/endpoint" hx-trigger="click">
    Clique aqui
</div>
```

**Casos de uso:**
- Filtros dinâmicos
- Busca em tempo real
- Paginação infinita
- Modais
- Validação inline

### Alpine.js

Interatividade simples:

```html
<div x-data="{ open: false }">
    <button @click="open = !open">Toggle</button>
    <div x-show="open">Conteúdo</div>
</div>
```

**Casos de uso:**
- Dropdowns
- Tabs
- Tooltips
- Validação básica

## Segurança

### Autenticação

Usando sistema nativo do Django:

```python
from django.contrib.auth.decorators import login_required

@login_required
def view(request):
    # ...
```

### Proteção CSRF

Nativa do Django, habilitada por padrão:

```html
<form method="post">
    {% csrf_token %}
    <!-- campos -->
</form>
```

### Permissões

Sistema de permissões do Django:

```python
# Futuro
@permission_required('app.permission')
def view(request):
    # ...
```

## Performance

### Otimizações de Query

```python
# Evitar N+1 queries
clientes = Cliente.objects.select_related('fk_pessoas')

# Prefetch related
produtos = Produto.objects.prefetch_related('movimentacoes')
```

### Cache

```python
# Futuro: Cache com Redis
from django.core.cache import cache

data = cache.get('key')
if not data:
    data = compute_expensive_data()
    cache.set('key', data, 3600)
```

### Paginação

```python
from django.core.paginator import Paginator

paginator = Paginator(lista, 25)
page = paginator.get_page(numero)
```

## Deploy

### Desenvolvimento

```bash
python manage.py runserver
```

### Produção

```bash
gunicorn config.wsgi:application
```

**Servidor Web:** Nginx como proxy reverso

**Arquivos Estáticos:** Servidos pelo Nginx

**Arquivos de Mídia:** Nginx ou S3

### Docker (Futuro)

```dockerfile
FROM python:3.10
# ... configurações ...
CMD ["gunicorn", "config.wsgi:application"]
```

## Testes

### Estrutura de Testes

```
app/
├── tests/
│   ├── test_models.py
│   ├── test_views.py
│   └── test_forms.py
```

### Executar Testes

```bash
python manage.py test
```

## Monitoramento

### Logs

```python
import logging
logger = logging.getLogger(__name__)

logger.info("Mensagem")
logger.error("Erro", exc_info=True)
```

### Métricas (Futuro)

- Sentry: Tracking de erros
- Prometheus: Métricas
- Grafana: Dashboards

## Escalabilidade

### Tarefas Assíncronas (Futuro)

```python
# Celery para tarefas pesadas
@shared_task
def gerar_relatorio(id):
    # Processar em background
    pass
```

### Load Balancing (Futuro)

- Múltiplas instâncias do Django
- Nginx fazendo load balancing
- Redis para sessões compartilhadas

## Backup

### Banco de Dados

```bash
# Backup diário
pg_dump dbname > backup.sql

# Restaurar
psql dbname < backup.sql
```

### Arquivos de Mídia

- Backup para S3 ou similar
- Versionamento de arquivos

## Integração Contínua (Futuro)

```yaml
# .github/workflows/test.yml
name: Tests
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run tests
        run: python manage.py test
```

## Decisões Arquiteturais

### Por que não usar REST API + React?

1. **Complexidade:** Dois projetos para manter
2. **Deploy:** Mais complexo
3. **Time:** Pequeno ou solo
4. **Necessidade:** Não há necessidade de API no momento
5. **Custo:** Mais caro de desenvolver e manter

**Quando considerar:** Se surgir necessidade de app mobile nativo ou múltiplos frontends.

### Por que Django Templates + HTMX?

1. **Simplicidade:** Tudo em um lugar
2. **Produtividade:** Desenvolvimento mais rápido
3. **SSR:** Melhor performance inicial
4. **SEO:** Natural para SSR
5. **Interatividade:** HTMX fornece o necessário

### Por que não usar ORM completo do Django?

1. **Banco existente:** Estrutura já definida
2. **Migração gradual:** Sistema legado ainda em uso
3. **Risco:** Menor risco de quebrar dados
4. **Compatibilidade:** Sistema Delphi coexiste

## Próximas Decisões

1. **API REST:** Criar quando necessário (app mobile)
2. **Cache:** Redis quando tráfego aumentar
3. **Queue:** Celery para tarefas assíncronas
4. **Testes:** Aumentar cobertura de testes
5. **CI/CD:** Automatizar deploy

---

Este documento é vivo e deve ser atualizado conforme o projeto evolui.
