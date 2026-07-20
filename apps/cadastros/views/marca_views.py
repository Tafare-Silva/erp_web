"""
Views para Marcas.
CRUD completo de marcas de produtos.
"""

from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Q

from apps.cadastros.models import Marca


class MarcaListView(ListView):
    """
    Listagem de marcas com busca.
    """
    model = Marca
    template_name = 'cadastros/marcas/list.html'
    context_object_name = 'marcas'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Busca por nome
        search = self.request.GET.get('q', '')
        if search:
            queryset = queryset.filter(nome__icontains=search)
        
        return queryset.order_by('nome')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search'] = self.request.GET.get('q', '')
        context['titulo'] = 'Marcas'
        return context


class MarcaCreateView(CreateView):
    """
    Criação de nova marca.
    """
    model = Marca
    template_name = 'cadastros/marcas/form.html'
    fields = ['nome']
    success_url = reverse_lazy('cadastros:marca_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Nova Marca'
        context['botao_texto'] = 'Salvar'
        return context
    
    def form_valid(self, form):
        messages.success(self.request, 'Marca cadastrada com sucesso!')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Erro ao cadastrar marca. Verifique os dados.')
        return super().form_invalid(form)


class MarcaUpdateView(UpdateView):
    """
    Edição de marca existente.
    """
    model = Marca
    template_name = 'cadastros/marcas/form.html'
    fields = ['nome']
    success_url = reverse_lazy('cadastros:marca_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Marca'
        context['botao_texto'] = 'Atualizar'
        return context
    
    def form_valid(self, form):
        messages.success(self.request, 'Marca atualizada com sucesso!')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Erro ao atualizar marca. Verifique os dados.')
        return super().form_invalid(form)


class MarcaDeleteView(DeleteView):
    """
    Exclusão de marca.
    """
    model = Marca
    template_name = 'cadastros/marcas/confirm_delete.html'
    success_url = reverse_lazy('cadastros:marca_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Excluir Marca'
        return context
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Marca excluída com sucesso!')
        return super().delete(request, *args, **kwargs)
