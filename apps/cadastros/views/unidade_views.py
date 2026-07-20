"""
Views para Unidades de Medida.
CRUD completo de unidades.
"""

from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages

from apps.cadastros.models import Unidade


class UnidadeListView(ListView):
    """Listagem de unidades com busca."""
    model = Unidade
    template_name = 'cadastros/unidades/list.html'
    context_object_name = 'unidades'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset()
        search = self.request.GET.get('q', '')
        if search:
            queryset = queryset.filter(nome__icontains=search)
        return queryset.order_by('nome')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search'] = self.request.GET.get('q', '')
        context['titulo'] = 'Unidades de Medida'
        return context


class UnidadeCreateView(CreateView):
    """Criação de nova unidade."""
    model = Unidade
    template_name = 'cadastros/unidades/form.html'
    fields = ['nome', 'simbolo']
    success_url = reverse_lazy('cadastros:unidade_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Nova Unidade'
        context['botao_texto'] = 'Salvar'
        return context
    
    def form_valid(self, form):
        messages.success(self.request, 'Unidade cadastrada com sucesso!')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Erro ao cadastrar unidade. Verifique os dados.')
        return super().form_invalid(form)


class UnidadeUpdateView(UpdateView):
    """Edição de unidade existente."""
    model = Unidade
    template_name = 'cadastros/unidades/form.html'
    fields = ['nome', 'simbolo']
    success_url = reverse_lazy('cadastros:unidade_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Unidade'
        context['botao_texto'] = 'Atualizar'
        return context
    
    def form_valid(self, form):
        messages.success(self.request, 'Unidade atualizada com sucesso!')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Erro ao atualizar unidade. Verifique os dados.')
        return super().form_invalid(form)


class UnidadeDeleteView(DeleteView):
    """Exclusão de unidade."""
    model = Unidade
    template_name = 'cadastros/unidades/confirm_delete.html'
    success_url = reverse_lazy('cadastros:unidade_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Excluir Unidade'
        return context
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Unidade excluída com sucesso!')
        return super().delete(request, *args, **kwargs)
