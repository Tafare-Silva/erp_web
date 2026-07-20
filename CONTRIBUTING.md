# 🤝 Guia de Contribuição - ERP Web

Obrigado por considerar contribuir com o ERP Web! Este documento fornece diretrizes para contribuir com o projeto.

## Código de Conduta

- Seja respeitoso e profissional
- Aceite feedback construtivo
- Foque no que é melhor para o projeto
- Mostre empatia com outros contribuidores

## Como Contribuir

### Reportar Bugs

1. Verifique se o bug já não foi reportado nas Issues
2. Abra uma nova Issue incluindo:
   - Descrição clara do problema
   - Passos para reproduzir
   - Comportamento esperado vs atual
   - Screenshots se aplicável
   - Versão do Django e Python
   - Sistema operacional

### Sugerir Melhorias

1. Verifique se a sugestão já não existe
2. Abra uma Issue com:
   - Descrição clara da melhoria
   - Por que seria útil
   - Exemplos de uso, se possível

### Pull Requests

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## Padrões de Código

### Python / Django

#### PEP 8

Siga o guia de estilo PEP 8:

```python
# Bom
def calcular_total(items):
    """Calcula o total dos itens."""
    total = sum(item.preco for item in items)
    return total

# Ruim
def calc_tot(i):
    t=sum(x.p for x in i)
    return t
```

#### Docstrings

Use docstrings para documentar funções, classes e módulos:

```python
def criar_pedido(cliente_id, items):
    """
    Cria um novo pedido de venda.
    
    Args:
        cliente_id (int): ID do cliente
        items (list): Lista de itens do pedido
        
    Returns:
        Pedido: Instância do pedido criado
        
    Raises:
        ValueError: Se cliente_id for inválido
    """
    pass
```

#### Type Hints

Use type hints quando possível:

```python
from typing import List, Optional
from decimal import Decimal

def calcular_desconto(
    valor: Decimal,
    percentual: float
) -> Decimal:
    """Calcula desconto sobre um valor."""
    return valor * Decimal(str(percentual / 100))
```

### Django Specific

#### Models

```python
class Produto(models.Model):
    """Model para produtos do sistema."""
    
    codigo = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='Código'
    )
    descricao = models.CharField(
        max_length=255,
        verbose_name='Descrição'
    )
    
    class Meta:
        managed = False
        db_table = 'produtos'
        ordering = ['descricao']
        verbose_name = 'Produto'
        verbose_name_plural = 'Produtos'
    
    def __str__(self):
        return f"{self.codigo} - {self.descricao}"
```

#### Views

```python
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages

@login_required
def produto_create(request):
    """View para criar novo produto."""
    if request.method == 'POST':
        # Processar formulário
        messages.success(request, 'Produto criado com sucesso!')
        return redirect('cadastros:produto_list')
    
    return render(request, 'cadastros/produto_form.html')
```

#### URLs

```python
from django.urls import path
from . import views

app_name = 'cadastros'

urlpatterns = [
    path('produtos/', views.produto_list, name='produto_list'),
    path('produtos/<int:pk>/', views.produto_detail, name='produto_detail'),
    path('produtos/novo/', views.produto_create, name='produto_create'),
]
```

### Templates

#### Estrutura

```html
{% extends 'base.html' %}
{% load static %}

{% block title %}{{ title }} - ERP Web{% endblock %}

{% block content %}
<div class="container">
    <!-- Conteúdo -->
</div>
{% endblock %}
```

#### Tailwind CSS

Use classes utilitárias do Tailwind:

```html
<!-- Bom -->
<button class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md">
    Salvar
</button>

<!-- Evite CSS inline -->
<button style="background: blue; padding: 10px;">
    Salvar
</button>
```

#### HTMX

```html
<!-- Busca com HTMX -->
<input 
    type="text" 
    name="q"
    hx-get="{% url 'cadastros:produto_list' %}"
    hx-trigger="keyup changed delay:500ms"
    hx-target="#results"
    class="px-4 py-2 border rounded"
>
<div id="results">
    <!-- Resultados aparecem aqui -->
</div>
```

### JavaScript / Alpine.js

```html
<!-- Componente com Alpine -->
<div x-data="{ open: false }">
    <button @click="open = !open">
        Toggle
    </button>
    <div x-show="open" x-cloak>
        Conteúdo
    </div>
</div>
```

## Convenções de Nomenclatura

### Python

- **Classes:** PascalCase (`class PedidoVenda`)
- **Funções/Métodos:** snake_case (`def calcular_total()`)
- **Constantes:** UPPER_SNAKE_CASE (`MAX_ITEMS = 100`)
- **Variáveis:** snake_case (`total_pedido = 0`)

### Templates

- **Arquivos:** snake_case (`produto_list.html`)
- **IDs:** kebab-case (`id="btn-salvar"`)
- **Classes CSS:** kebab-case (`class="btn-primary"`)

### URLs

- **Patterns:** kebab-case (`path('novo-produto/', ...)`)
- **Names:** snake_case (`name='produto_create'`)

## Estrutura de Commits

### Mensagens de Commit

Use o padrão conventional commits:

```
tipo(escopo): descrição curta

Descrição detalhada (opcional)

Closes #123
```

**Tipos:**
- `feat`: Nova funcionalidade
- `fix`: Correção de bug
- `docs`: Documentação
- `style`: Formatação (não afeta código)
- `refactor`: Refatoração
- `test`: Testes
- `chore`: Manutenção

**Exemplos:**

```bash
feat(cadastros): adicionar formulário de criação de produtos
fix(vendas): corrigir cálculo de desconto
docs(readme): atualizar instruções de instalação
style(templates): formatar código HTML
refactor(models): simplificar query de produtos
test(cadastros): adicionar testes para Pessoa model
chore(deps): atualizar Django para 5.0.1
```

## Testes

### Escrever Testes

Todo código novo deve incluir testes:

```python
from django.test import TestCase
from apps.cadastros.models import Pessoa

class PessoaModelTest(TestCase):
    """Testes para o model Pessoa."""
    
    def setUp(self):
        """Configuração inicial dos testes."""
        self.pessoa = Pessoa.objects.create(
            cpf_cnpj='12345678901',
            razao_social='Teste LTDA'
        )
    
    def test_str_representation(self):
        """Testa representação string do model."""
        self.assertEqual(str(self.pessoa), 'Teste LTDA')
    
    def test_cpf_cnpj_unique(self):
        """Testa unicidade do CPF/CNPJ."""
        with self.assertRaises(Exception):
            Pessoa.objects.create(
                cpf_cnpj='12345678901',
                razao_social='Outro'
            )
```

### Executar Testes

```bash
# Todos os testes
python manage.py test

# App específico
python manage.py test apps.cadastros

# Com cobertura (coverage deve estar instalado)
coverage run --source='.' manage.py test
coverage report
```

## Documentação

### Código

- Docstrings em todas as funções, classes e módulos
- Comentários para lógica complexa
- Type hints quando possível

### Projeto

Ao adicionar funcionalidades significativas, atualize:

- `README.md` - Se mudar instalação ou uso básico
- `ROADMAP.md` - Marcar features implementadas
- `ARCHITECTURE.md` - Se mudar arquitetura
- `COMMANDS.md` - Se adicionar comandos úteis

## Code Review

### Para Revisores

- Seja construtivo e educado
- Sugira melhorias, não apenas critique
- Explique o "porquê" das sugestões
- Aprove quando estiver satisfeito

### Para Autores

- Responda todos os comentários
- Faça as mudanças solicitadas
- Não leve críticas para o pessoal
- Agradeça o feedback

## Checklist de PR

Antes de submeter um PR, verifique:

- [ ] Código segue os padrões do projeto
- [ ] Testes foram adicionados/atualizados
- [ ] Testes estão passando
- [ ] Documentação foi atualizada
- [ ] Commits seguem o padrão
- [ ] Branch está atualizada com main
- [ ] Não há conflitos
- [ ] Não há arquivos desnecessários (*.pyc, __pycache__, etc)

## Dúvidas?

Se tiver dúvidas sobre como contribuir:

1. Verifique a documentação existente
2. Abra uma Issue perguntando
3. Entre em contato com os mantenedores

## Licença

Ao contribuir, você concorda que suas contribuições serão licenciadas sob a mesma licença do projeto.

---

**Obrigado por contribuir! 🎉**
