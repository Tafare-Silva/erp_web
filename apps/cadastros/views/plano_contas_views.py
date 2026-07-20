"""
Views para Plano de Contas.
"""

from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Q

from apps.cadastros.models import PlanoContas
from apps.cadastros.forms import PlanoContasForm


class PlanoContasListView(ListView):
    """Listagem de plano de contas."""
    model = PlanoContas
    template_name = 'cadastros/plano_contas/list.html'
    context_object_name = 'contas'
    paginate_by = 50
    
    def get_queryset(self):
        queryset = super().get_queryset()
        search = self.request.GET.get('q', '')
        tipo = self.request.GET.get('tipo', '')
        
        if search:
            queryset = queryset.filter(
                Q(codigo__icontains=search) |
                Q(nome__icontains=search)
            )
        
        if tipo:
            queryset = queryset.filter(tipo_conta=tipo)
        
        return queryset.order_by('codigo')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search'] = self.request.GET.get('q', '')
        context['tipo_filtro'] = self.request.GET.get('tipo', '')
        context['titulo'] = 'Plano de Contas'
        
        # Adicionar informações hierárquicas
        for conta in context['contas']:
            conta.nivel = conta.get_nivel()
            conta.indentacao = '—' * conta.nivel
        
        return context


class PlanoContasCreateView(CreateView):
    """Criação de nova conta."""
    model = PlanoContas
    form_class = PlanoContasForm
    template_name = 'cadastros/plano_contas/form.html'
    success_url = reverse_lazy('cadastros:plano_contas_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Nova Conta no Plano de Contas'
        context['botao_texto'] = 'Salvar'
        return context
    
    def form_valid(self, form):
        messages.success(self.request, 'Conta cadastrada com sucesso!')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Erro ao cadastrar conta. Verifique os dados.')
        return super().form_invalid(form)


class PlanoContasUpdateView(UpdateView):
    """Edição de conta existente."""
    model = PlanoContas
    form_class = PlanoContasForm
    template_name = 'cadastros/plano_contas/form.html'
    success_url = reverse_lazy('cadastros:plano_contas_list')
    pk_url_kwarg = 'pk'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Conta no Plano de Contas'
        context['botao_texto'] = 'Atualizar'
        return context
    
    def form_valid(self, form):
        messages.success(self.request, 'Conta atualizada com sucesso!')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Erro ao atualizar conta. Verifique os dados.')
        return super().form_invalid(form)


class PlanoContasDeleteView(DeleteView):
    """Exclusão de conta."""
    model = PlanoContas
    template_name = 'cadastros/plano_contas/confirm_delete.html'
    success_url = reverse_lazy('cadastros:plano_contas_list')
    pk_url_kwarg = 'pk'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Excluir Conta do Plano de Contas'
        return context
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Conta excluída com sucesso!')
        return super().delete(request, *args, **kwargs)
