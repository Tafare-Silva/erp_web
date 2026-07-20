"""
Views para Tipo de Pagamento.
"""

from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Q

from apps.cadastros.models import TipoPagamento
from apps.cadastros.forms import TipoPagamentoForm


class TipoPagamentoListView(ListView):
    """Listagem de tipos de pagamento."""
    model = TipoPagamento
    template_name = 'cadastros/tipos_pagamento/list.html'
    context_object_name = 'tipos_pagamento'
    paginate_by = 50
    
    def get_queryset(self):
        queryset = super().get_queryset()
        search = self.request.GET.get('q', '')
        if search:
            queryset = queryset.filter(nome__icontains=search)
        return queryset.order_by('nome')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search'] = self.request.GET.get('q', '')
        context['titulo'] = 'Tipos de Pagamento'
        return context


class TipoPagamentoCreateView(CreateView):
    """Criação de novo tipo de pagamento."""
    model = TipoPagamento
    form_class = TipoPagamentoForm
    template_name = 'cadastros/tipos_pagamento/form.html'
    success_url = reverse_lazy('cadastros:tipo_pagamento_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Novo Tipo de Pagamento'
        context['botao_texto'] = 'Salvar'
        return context
    
    def form_valid(self, form):
        messages.success(self.request, 'Tipo de pagamento cadastrado com sucesso!')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Erro ao cadastrar tipo de pagamento. Verifique os dados.')
        return super().form_invalid(form)


class TipoPagamentoUpdateView(UpdateView):
    """Edição de tipo de pagamento existente."""
    model = TipoPagamento
    form_class = TipoPagamentoForm
    template_name = 'cadastros/tipos_pagamento/form.html'
    success_url = reverse_lazy('cadastros:tipo_pagamento_list')
    pk_url_kwarg = 'nome'
    
    def get_object(self, queryset=None):
        """Busca por nome ao invés de pk numérico."""
        nome = self.kwargs.get('nome')
        return self.model.objects.get(nome=nome)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Tipo de Pagamento'
        context['botao_texto'] = 'Atualizar'
        return context
    
    def form_valid(self, form):
        messages.success(self.request, 'Tipo de pagamento atualizado com sucesso!')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Erro ao atualizar tipo de pagamento. Verifique os dados.')
        return super().form_invalid(form)


class TipoPagamentoDeleteView(DeleteView):
    """Exclusão de tipo de pagamento."""
    model = TipoPagamento
    template_name = 'cadastros/tipos_pagamento/confirm_delete.html'
    success_url = reverse_lazy('cadastros:tipo_pagamento_list')
    pk_url_kwarg = 'nome'
    
    def get_object(self, queryset=None):
        """Busca por nome ao invés de pk numérico."""
        nome = self.kwargs.get('nome')
        return self.model.objects.get(nome=nome)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Excluir Tipo de Pagamento'
        return context
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Tipo de pagamento excluído com sucesso!')
        return super().delete(request, *args, **kwargs)
