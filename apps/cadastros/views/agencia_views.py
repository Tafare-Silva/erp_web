"""
Views para Agências Bancárias.
CRUD completo de agências.
"""

from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.views.generic.detail import SingleObjectMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.http import Http404
from django import forms

from apps.cadastros.models import AgenciaBancaria
from apps.cadastros.forms import AgenciaBancariaForm


class AgenciaBancariaListView(ListView):
    """Listagem de agências com busca."""
    model = AgenciaBancaria
    template_name = 'cadastros/agencias/list.html'
    context_object_name = 'agencias'
    paginate_by = 20
    
    def get_queryset(self):
        from apps.cadastros.models import Banco
        
        # Query raw para evitar problema de PK composta
        search = self.request.GET.get('q', '')
        
        if search:
            agencias = AgenciaBancaria.objects.raw('''
                SELECT "fk_bancos$banco" as banco, agencia, telefone, nome_gerente, digito,
                       valor_juros, valor_multa_por_atraso, dias_para_protesto,
                       carteira, codigo_cedente, convenio, especie_documento,
                       layout_remessa, nosso_numero_boleto_bancario,
                       numero_remessa_boleto_bancario, codigo_transmissao, modalidade
                FROM "cadastros"."agencias_bancarias"
                WHERE CAST(agencia AS TEXT) LIKE %s
                   OR CAST("fk_bancos$banco" AS TEXT) LIKE %s
                   OR nome_gerente ILIKE %s
                ORDER BY "fk_bancos$banco", agencia
            ''', [f'%{search}%', f'%{search}%', f'%{search}%'])
        else:
            agencias = AgenciaBancaria.objects.raw('''
                SELECT "fk_bancos$banco" as banco, agencia, telefone, nome_gerente, digito,
                       valor_juros, valor_multa_por_atraso, dias_para_protesto,
                       carteira, codigo_cedente, convenio, especie_documento,
                       layout_remessa, nosso_numero_boleto_bancario,
                       numero_remessa_boleto_bancario, codigo_transmissao, modalidade
                FROM "cadastros"."agencias_bancarias"
                ORDER BY "fk_bancos$banco", agencia
            ''')
        
        return list(agencias)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search'] = self.request.GET.get('q', '')
        context['titulo'] = 'Agências Bancárias'
        
        # Adicionar pk_composto e banco_obj para cada agência
        from apps.cadastros.models import Banco
        bancos_cache = {}
        
        for agencia in context['agencias']:
            agencia.pk_composto = f"{agencia.banco}-{agencia.agencia}"
            
            # Cache de bancos para evitar múltiplas queries
            if agencia.banco not in bancos_cache:
                try:
                    bancos_cache[agencia.banco] = Banco.objects.get(codigo_banco=agencia.banco)
                except Banco.DoesNotExist:
                    bancos_cache[agencia.banco] = None
            
            agencia.banco_obj = bancos_cache[agencia.banco]
        
        return context


class AgenciaBancariaCreateView(CreateView):
    """Criação de nova agência."""
    model = AgenciaBancaria
    template_name = 'cadastros/agencias/form.html'
    fields = ['banco', 'agencia', 'digito', 'telefone', 'nome_gerente',
              'valor_juros', 'valor_multa_por_atraso', 'dias_para_protesto',
              'carteira', 'codigo_cedente', 'convenio', 'especie_documento',
              'layout_remessa', 'codigo_transmissao', 'modalidade']
    success_url = reverse_lazy('cadastros:agencia_list')
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Transformar campo banco em select
        from apps.cadastros.models import Banco
        form.fields['banco'].widget = forms.Select(choices=[(b.codigo_banco, f"{b.codigo_banco} - {b.nome}") for b in Banco.objects.all()])
        return form
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Nova Agência Bancária'
        context['botao_texto'] = 'Salvar'
        return context
    
    def form_valid(self, form):
        messages.success(self.request, 'Agência cadastrada com sucesso!')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Erro ao cadastrar agência. Verifique os dados.')
        return super().form_invalid(form)


class AgenciaBancariaUpdateView(UpdateView):
    """Edição de agência existente."""
    model = AgenciaBancaria
    template_name = 'cadastros/agencias/form.html'
    fields = ['banco', 'agencia', 'digito', 'telefone', 'nome_gerente',
              'valor_juros', 'valor_multa_por_atraso', 'dias_para_protesto',
              'carteira', 'codigo_cedente', 'convenio', 'especie_documento',
              'layout_remessa', 'codigo_transmissao', 'modalidade']
    success_url = reverse_lazy('cadastros:agencia_list')
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Transformar campo banco em select
        from apps.cadastros.models import Banco
        form.fields['banco'].widget = forms.Select(choices=[(b.codigo_banco, f"{b.codigo_banco} - {b.nome}") for b in Banco.objects.all()])
        return form
    
    def get_object(self, queryset=None):
        """Busca agência por banco+agencia ao invés de pk único."""
        pk_str = self.kwargs.get('pk')
        if '-' in pk_str:
            banco_cod, agencia_num = pk_str.split('-', 1)
            return get_object_or_404(
                AgenciaBancaria,
                banco=int(banco_cod),
                agencia=int(agencia_num)
            )
        raise Http404("Agência não encontrada")
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Agência Bancária'
        context['botao_texto'] = 'Atualizar'
        return context
    
    def form_valid(self, form):
        messages.success(self.request, 'Agência atualizada com sucesso!')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Erro ao atualizar agência. Verifique os dados.')
        return super().form_invalid(form)


class AgenciaBancariaDeleteView(DeleteView):
    """Exclusão de agência."""
    model = AgenciaBancaria
    template_name = 'cadastros/agencias/confirm_delete.html'
    success_url = reverse_lazy('cadastros:agencia_list')
    
    def get_object(self, queryset=None):
        """Busca agência por banco+agencia ao invés de pk único."""
        pk_str = self.kwargs.get('pk')
        if '-' in pk_str:
            banco_cod, agencia_num = pk_str.split('-', 1)
            return get_object_or_404(
                AgenciaBancaria,
                banco=int(banco_cod),
                agencia=int(agencia_num)
            )
        raise Http404("Agência não encontrada")
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Excluir Agência Bancária'
        return context
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Agência excluída com sucesso!')
        return super().delete(request, *args, **kwargs)
