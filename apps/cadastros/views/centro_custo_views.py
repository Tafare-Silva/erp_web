"""
Views para Centro de Custos.
"""

from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Q

from apps.cadastros.models import CentroCusto
from apps.cadastros.forms import CentroCustoForm


class CentroCustoListView(ListView):
    """Listagem de centros de custos."""
    model = CentroCusto
    template_name = 'cadastros/centros_custos/list.html'
    context_object_name = 'centros_custos'
    paginate_by = 50
    
    def get_queryset(self):
        queryset = super().get_queryset()
        search = self.request.GET.get('q', '')
        if search:
            queryset = queryset.filter(
                Q(codigo__icontains=search) |
                Q(nome__icontains=search)
            )
        return queryset.order_by('codigo')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search'] = self.request.GET.get('q', '')
        context['titulo'] = 'Centros de Custos'
        
        # Adicionar informações hierárquicas
        for cc in context['centros_custos']:
            cc.nivel = cc.get_nivel()
            cc.indentacao = '—' * cc.nivel
        
        return context


class CentroCustoCreateView(CreateView):
    """Criação de novo centro de custo."""
    model = CentroCusto
    form_class = CentroCustoForm
    template_name = 'cadastros/centros_custos/form.html'
    success_url = reverse_lazy('cadastros:centro_custo_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Novo Centro de Custo'
        context['botao_texto'] = 'Salvar'
        return context
    
    def form_valid(self, form):
        messages.success(self.request, 'Centro de custo cadastrado com sucesso!')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Erro ao cadastrar centro de custo. Verifique os dados.')
        return super().form_invalid(form)


class CentroCustoUpdateView(UpdateView):
    """Edição de centro de custo existente."""
    model = CentroCusto
    form_class = CentroCustoForm
    template_name = 'cadastros/centros_custos/form.html'
    success_url = reverse_lazy('cadastros:centro_custo_list')
    pk_url_kwarg = 'pk'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Centro de Custo'
        context['botao_texto'] = 'Atualizar'
        return context
    
    def form_valid(self, form):
        messages.success(self.request, 'Centro de custo atualizado com sucesso!')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Erro ao atualizar centro de custo. Verifique os dados.')
        return super().form_invalid(form)


class CentroCustoDeleteView(DeleteView):
    """Exclusão de centro de custo."""
    model = CentroCusto
    template_name = 'cadastros/centros_custos/confirm_delete.html'
    success_url = reverse_lazy('cadastros:centro_custo_list')
    pk_url_kwarg = 'pk'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Excluir Centro de Custo'
        return context
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Centro de custo excluído com sucesso!')
        return super().delete(request, *args, **kwargs)
