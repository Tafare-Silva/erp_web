# Guia de Continuação do Desenvolvimento

## 🎯 Onde Estamos

Você tem agora um projeto Django funcional com:

1. ✅ Estrutura base do projeto configurada
2. ✅ Models criados para todo o módulo de cadastros
3. ✅ CRUD completo de Marcas implementado (exemplo funcionando)
4. ✅ Interface moderna com Tailwind CSS + HTMX + Alpine.js
5. ✅ Templates base prontos para reutilização

## 📋 Próximos Passos Recomendados

### Sprint 1: Cadastro de Pessoas (2-3 semanas)

#### 1. Criar Views de Pessoa

Arquivo: `apps/cadastros/views/pessoa_views.py`

```python
from django.views.generic import ListView, CreateView, UpdateView, DetailView
from apps.cadastros.models import Pessoa, PessoaFisica, Cliente

class PessoaListView(ListView):
    # Similar ao MarcaListView
    # Adicionar filtros por tipo (cliente, fornecedor, etc)
    pass

class PessoaCreateView(CreateView):
    # Criar form com abas para dados PF/PJ
    pass

class PessoaUpdateView(UpdateView):
    pass

class PessoaDetailView(DetailView):
    # Mostrar todos os dados: endereços, etc
    pass
```

#### 2. Criar Forms de Pessoa

Arquivo: `apps/cadastros/forms/pessoa_forms.py`

```python
from django import forms
from apps.cadastros.models import Pessoa, PessoaFisica

class PessoaForm(forms.ModelForm):
    class Meta:
        model = Pessoa
        fields = ['nome', 'cpf_cnpj', 'rg_ie', 'email', ...]
        
class PessoaFisicaForm(forms.ModelForm):
    class Meta:
        model = PessoaFisica
        fields = ['data_nascimento', 'estado_civil', ...]
```

#### 3. Criar Templates

- `cadastros/pessoas/list.html` (baseado em marcas/list.html)
- `cadastros/pessoas/form.html` (com abas para PF/PJ)
- `cadastros/pessoas/detail.html` (visão completa)

#### 4. Adicionar URLs

Arquivo: `apps/cadastros/urls.py`

```python
# Pessoas
path('pessoas/', pessoa_views.PessoaListView.as_view(), name='pessoa_list'),
path('pessoas/novo/', pessoa_views.PessoaCreateView.as_view(), name='pessoa_create'),
path('pessoas/<int:pk>/', pessoa_views.PessoaDetailView.as_view(), name='pessoa_detail'),
path('pessoas/<int:pk>/editar/', pessoa_views.PessoaUpdateView.as_view(), name='pessoa_update'),
```

### Sprint 2: Cadastro de Produtos (2-3 semanas)

Similar ao processo de Pessoas, mas focado em Produtos.

Pontos de atenção:
- Upload de imagens
- Múltiplos códigos de barras
- Relacionamento com fornecedores
- Cálculo de preços e margens

### Sprint 3: Outras Tabelas Auxiliares (1-2 semanas)

Implementar CRUDs simples para:
- Divisões (hierárquica - usar biblioteca django-mptt)
- Unidades
- NCM
- Cidades

### Sprint 4: Melhorias e Funcionalidades Extras (2 semanas)

- Sistema de permissões
- Logs de auditoria
- Exportação para Excel/PDF
- Filtros avançados
- Dashboard com métricas reais

## 🎨 Padrões de Código Estabelecidos

### 1. Estrutura de Views

Sempre use Class-Based Views:
- ListView para listagens
- CreateView para criação
- UpdateView para edição
- DeleteView para exclusão
- DetailView para visualização

### 2. Estrutura de Templates

Sempre estenda o `base.html`:

```django
{% extends 'base.html' %}
{% block title %}Título{% endblock %}
{% block page_title %}Título da Página{% endblock %}
{% block content %}
    <!-- Seu conteúdo aqui -->
{% endblock %}
```

### 3. Mensagens Flash

Use sempre após ações:

```python
from django.contrib import messages

messages.success(request, 'Operação realizada com sucesso!')
messages.error(request, 'Erro ao realizar operação.')
messages.warning(request, 'Atenção!')
messages.info(request, 'Informação importante.')
```

### 4. Nomenclatura

- **Models:** Singular, PascalCase (ex: Pessoa, Produto)
- **Views:** Nome + Ação + View (ex: PessoaListView)
- **URLs:** snake_case (ex: pessoa_list, produto_create)
- **Templates:** snake_case (ex: pessoa_list.html)

## 🔧 Ferramentas Úteis

### Django Extensions

```bash
pip install django-extensions
```

Adicione em INSTALLED_APPS:
```python
'django_extensions',
```

Comandos úteis:
```bash
python manage.py show_urls  # Lista todas as URLs
python manage.py shell_plus  # Shell com imports automáticos
```

### Django Debug Toolbar

```bash
pip install django-debug-toolbar
```

Excelente para debug de queries SQL.

## 📚 Recursos de Aprendizado

- Documentação Django: https://docs.djangoproject.com/
- Tailwind CSS: https://tailwindcss.com/docs
- HTMX: https://htmx.org/docs/
- Alpine.js: https://alpinejs.dev/start-here

## 🐛 Debugging

### Problema comum 1: Erro ao conectar ao banco

Solução:
1. Verifique credenciais em `config/settings.py`
2. Teste conexão: `python manage.py dbshell`
3. Verifique se o PostgreSQL está rodando

### Problema comum 2: Tabela não encontrada

Solução:
- Verifique o `db_table` no Meta do model
- Confirme que a tabela existe no schema correto

### Problema comum 3: Erro de foreign key

Solução:
- Para FKs com nomes como `fk_marcas$marca`, use:
  ```python
  db_column='fk_marcas$marca'
  to_field='nome'  # Se a FK aponta para nome, não para pk
  ```

## 🚀 Dicas de Produtividade

1. **Use o shell do Django para testar:**
   ```bash
   python manage.py shell
   >>> from apps.cadastros.models import Pessoa
   >>> Pessoa.objects.all()
   ```

2. **Crie fixtures para dados de teste:**
   ```bash
   python manage.py dumpdata cadastros.Marca > marcas.json
   python manage.py loaddata marcas.json
   ```

3. **Use atalhos do Django:**
   - `get_object_or_404()` ao invés de try/except
   - `reverse_lazy()` para URLs em views
   - `@login_required` para proteger views

## 📞 Suporte

Para dúvidas sobre o projeto:
1. Consulte a documentação do Django
2. Use o Django Debug Toolbar
3. Verifique os logs em tempo real com `python manage.py runserver`

---

**Boa sorte no desenvolvimento! 🚀**
