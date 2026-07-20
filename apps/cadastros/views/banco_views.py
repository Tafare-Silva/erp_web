"""
Views para Bancos.
CRUD completo de bancos.
"""

from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Q

from apps.cadastros.models import Banco


class BancoListView(ListView):
    """Listagem de bancos com busca."""
    model = Banco
    template_name = 'cadastros/bancos/list.html'
    context_object_name = 'bancos'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset()
        search = self.request.GET.get('q', '')
        if search:
            queryset = queryset.filter(
                Q(codigo_banco__icontains=search) |
                Q(nome__icontains=search)
            )
        return queryset.order_by('codigo_banco')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search'] = self.request.GET.get('q', '')
        context['titulo'] = 'Bancos'
        return context


class BancoCreateView(CreateView):
    """Criação de novo banco."""
    model = Banco
    template_name = 'cadastros/bancos/form.html'
    fields = ['codigo_banco', 'nome', 'taxa_cobranca_simples', 'banco_boleto', 
              'orientacoes_banco', 'local_pagamento_boleto']
    success_url = reverse_lazy('cadastros:banco_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Novo Banco'
        context['botao_texto'] = 'Salvar'
        return context
    
    def form_valid(self, form):
        messages.success(self.request, 'Banco cadastrado com sucesso!')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Erro ao cadastrar banco. Verifique os dados.')
        return super().form_invalid(form)


class BancoUpdateView(UpdateView):
    """Edição de banco existente."""
    model = Banco
    template_name = 'cadastros/bancos/form.html'
    fields = ['codigo_banco', 'nome', 'taxa_cobranca_simples', 'banco_boleto',
              'orientacoes_banco', 'local_pagamento_boleto']
    success_url = reverse_lazy('cadastros:banco_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Banco'
        context['botao_texto'] = 'Atualizar'
        return context
    
    def form_valid(self, form):
        messages.success(self.request, 'Banco atualizado com sucesso!')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Erro ao atualizar banco. Verifique os dados.')
        return super().form_invalid(form)


class BancoDeleteView(DeleteView):
    """Exclusão de banco."""
    model = Banco
    template_name = 'cadastros/bancos/confirm_delete.html'
    success_url = reverse_lazy('cadastros:banco_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Excluir Banco'
        return context
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Banco excluído com sucesso!')
        return super().delete(request, *args, **kwargs)
