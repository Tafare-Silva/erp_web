"""
Views para Divisões.
CRUD completo de divisões de produtos.
"""

from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages

from apps.cadastros.models import Divisao
from apps.cadastros.forms import DivisaoForm


class DivisaoListView(ListView):
    """Listagem de divisões com busca."""
    model = Divisao
    template_name = 'cadastros/divisoes/list.html'
    context_object_name = 'divisoes'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset()
        search = self.request.GET.get('q', '')
        if search:
            queryset = queryset.filter(nome__icontains=search)
        return queryset.order_by('codigo', 'nome')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search'] = self.request.GET.get('q', '')
        context['titulo'] = 'Divisões'
        return context


class DivisaoCreateView(CreateView):
    """Criação de nova divisão."""
    model = Divisao
    form_class = DivisaoForm
    template_name = 'cadastros/divisoes/form.html'
    success_url = reverse_lazy('cadastros:divisao_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Nova Divisão'
        context['botao_texto'] = 'Salvar'
        return context
    
    def form_valid(self, form):
        messages.success(self.request, 'Divisão cadastrada com sucesso!')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Erro ao cadastrar divisão. Verifique os dados.')
        return super().form_invalid(form)


class DivisaoUpdateView(UpdateView):
    """Edição de divisão existente."""
    model = Divisao
    form_class = DivisaoForm
    template_name = 'cadastros/divisoes/form.html'
    success_url = reverse_lazy('cadastros:divisao_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Divisão'
        context['botao_texto'] = 'Atualizar'
        return context
    
    def form_valid(self, form):
        messages.success(self.request, 'Divisão atualizada com sucesso!')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Erro ao atualizar divisão. Verifique os dados.')
        return super().form_invalid(form)


class DivisaoDeleteView(DeleteView):
    """Exclusão de divisão."""
    model = Divisao
    template_name = 'cadastros/divisoes/confirm_delete.html'
    success_url = reverse_lazy('cadastros:divisao_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Excluir Divisão'
        return context
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Divisão excluída com sucesso!')
        return super().delete(request, *args, **kwargs)
