"""
Views para Contas Bancárias.
CRUD completo de contas.
"""

from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404

from apps.cadastros.models import ContaBancaria
from apps.cadastros.forms import ContaBancariaForm


class ContaBancariaListView(ListView):
    """Listagem de contas com busca."""
    model = ContaBancaria
    template_name = 'cadastros/contas/list.html'
    context_object_name = 'contas'
    paginate_by = 20
    
    def get_queryset(self):
        from apps.cadastros.models import Banco
        
        # Query raw para evitar problema de PK composta
        search = self.request.GET.get('q', '')
        mostrar_inativas = self.request.GET.get('inativas', '') == '1'
        
        where_clauses = []
        params = []
        
        if search:
            where_clauses.append('(CAST(conta AS TEXT) LIKE %s OR descricao_propria ILIKE %s)')
            params.extend([f'%{search}%', f'%{search}%'])
        
        if not mostrar_inativas:
            where_clauses.append('inativo = false')
        
        where_sql = ' AND '.join(where_clauses) if where_clauses else '1=1'
        
        contas = ContaBancaria.objects.raw(f'''
            SELECT "fk_bancos$banco" as banco, 
                   "fk_agencias_bancarias$agencia" as agencia,
                   conta, digito, saldo_inicial, tipo_conta_bancaria,
                   inativo, descricao_propria
            FROM "cadastros"."contas_bancarias"
            WHERE {where_sql}
            ORDER BY "fk_bancos$banco", "fk_agencias_bancarias$agencia", conta
        ''', params)
        
        return list(contas)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search'] = self.request.GET.get('q', '')
        context['mostrar_inativas'] = self.request.GET.get('inativas', '') == '1'
        context['titulo'] = 'Contas Bancárias'
        
        # Adicionar banco_obj e pk_composto
        from apps.cadastros.models import Banco
        bancos_cache = {}
        
        for conta in context['contas']:
            conta.pk_composto = f"{conta.banco}-{conta.agencia}-{conta.conta}"
            
            # Cache de bancos
            if conta.banco not in bancos_cache:
                try:
                    bancos_cache[conta.banco] = Banco.objects.get(codigo_banco=conta.banco)
                except Banco.DoesNotExist:
                    bancos_cache[conta.banco] = None
            
            conta.banco_obj = bancos_cache[conta.banco]
        
        return context


class ContaBancariaCreateView(CreateView):
    """Criação de nova conta."""
    model = ContaBancaria
    form_class = ContaBancariaForm
    template_name = 'cadastros/contas/form.html'
    success_url = reverse_lazy('cadastros:conta_list')
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Transformar campo banco em select
        from apps.cadastros.models import Banco, AgenciaBancaria
        from django import forms as django_forms
        
        # Buscar apenas bancos que têm agências cadastradas
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT DISTINCT "fk_bancos$banco"
                FROM "cadastros"."agencias_bancarias"
                ORDER BY "fk_bancos$banco"
            """)
            bancos_com_agencias = [row[0] for row in cursor.fetchall()]
        
        # Filtrar bancos e criar choices
        bancos_choices = [('', '--- Selecione um banco ---')]
        for b in Banco.objects.filter(codigo_banco__in=bancos_com_agencias).order_by('codigo_banco'):
            bancos_choices.append((b.codigo_banco, f"{b.codigo_banco} - {b.nome}"))
        
        form.fields['banco'].widget = django_forms.Select(
            choices=bancos_choices,
            attrs={'class': 'form-control', 'id': 'id_banco'}
        )
        
        # Buscar agências usando raw query
        agencias_choices = [('', '--- Selecione o banco primeiro ---')]
        
        try:
            agencias_raw = AgenciaBancaria.objects.raw('''
            SELECT "fk_bancos$banco" as banco, agencia, digito
            FROM "cadastros"."agencias_bancarias"
            ORDER BY "fk_bancos$banco", agencia
        ''')
        
            # Converter para lista
            agencias_list = list(agencias_raw)
            
            for ag in agencias_list:
                # Usar valor composto para evitar duplicatas
                valor = f"{ag.banco}-{ag.agencia}"
                texto = f"Ag {ag.agencia}{'-' + ag.digito if ag.digito else ''} (Banco {ag.banco})"
                agencias_choices.append((valor, texto))
            
            print(f"DEBUG: {len(agencias_list)} agências carregadas")
            
        except Exception as e:
            print(f"ERRO ao carregar agências: {e}")
            agencias_choices.append(('', f'--- Erro: {str(e)[:50]} ---'))
        
        form.fields['agencia'].widget = django_forms.Select(
            choices=agencias_choices,
            attrs={'class': 'form-control', 'id': 'id_agencia'}
        )
        
        return form
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Nova Conta Bancária'
        context['botao_texto'] = 'Salvar'
        return context
    
    def form_valid(self, form):
        messages.success(self.request, 'Conta cadastrada com sucesso!')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Erro ao cadastrar conta. Verifique os dados.')
        return super().form_invalid(form)


class ContaBancariaUpdateView(UpdateView):
    """Edição de conta existente."""
    model = ContaBancaria
    form_class = ContaBancariaForm
    template_name = 'cadastros/contas/form.html'
    success_url = reverse_lazy('cadastros:conta_list')
    
    def get_object(self, queryset=None):
        """Busca conta por banco+agencia+conta ao invés de pk único."""
        from django.http import Http404
        pk_str = self.kwargs.get('pk')
        if '-' in pk_str:
            parts = pk_str.split('-')
            if len(parts) == 3:
                banco_cod, agencia_num, conta_num = parts
                return get_object_or_404(
                    ContaBancaria,
                    banco=int(banco_cod),
                    agencia=int(agencia_num),
                    conta=int(conta_num)
                )
        raise Http404("Conta não encontrada")
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Transformar campo banco em select
        from apps.cadastros.models import Banco, AgenciaBancaria
        from django import forms as django_forms
        
        # Buscar apenas bancos que têm agências cadastradas
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT DISTINCT "fk_bancos$banco"
                FROM "cadastros"."agencias_bancarias"
                ORDER BY "fk_bancos$banco"
            """)
            bancos_com_agencias = [row[0] for row in cursor.fetchall()]
        
        # Filtrar bancos e criar choices
        bancos_choices = [('', '--- Selecione um banco ---')]
        for b in Banco.objects.filter(codigo_banco__in=bancos_com_agencias).order_by('codigo_banco'):
            bancos_choices.append((b.codigo_banco, f"{b.codigo_banco} - {b.nome}"))
        
        form.fields['banco'].widget = django_forms.Select(
            choices=bancos_choices,
            attrs={'class': 'form-control', 'id': 'id_banco'}
        )
        
        # Buscar agências usando raw query
        agencias_choices = [('', '--- Selecione o banco primeiro ---')]
        
        try:
            agencias_raw = AgenciaBancaria.objects.raw('''
            SELECT "fk_bancos$banco" as banco, agencia, digito
            FROM "cadastros"."agencias_bancarias"
            ORDER BY "fk_bancos$banco", agencia
        ''')
        
            # Converter para lista
            agencias_list = list(agencias_raw)
            
            for ag in agencias_list:
                # Usar valor composto para evitar duplicatas
                valor = f"{ag.banco}-{ag.agencia}"
                texto = f"Ag {ag.agencia}{'-' + ag.digito if ag.digito else ''} (Banco {ag.banco})"
                agencias_choices.append((valor, texto))
            
            print(f"DEBUG: {len(agencias_list)} agências carregadas")
            
        except Exception as e:
            print(f"ERRO ao carregar agências: {e}")
            agencias_choices.append(('', f'--- Erro: {str(e)[:50]} ---'))
        
        form.fields['agencia'].widget = django_forms.Select(
            choices=agencias_choices,
            attrs={'class': 'form-control', 'id': 'id_agencia'}
        )
        
        return form
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Conta Bancária'
        context['botao_texto'] = 'Atualizar'
        return context
    
    def form_valid(self, form):
        messages.success(self.request, 'Conta atualizada com sucesso!')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Erro ao atualizar conta. Verifique os dados.')
        return super().form_invalid(form)


class ContaBancariaDeleteView(DeleteView):
    """Exclusão de conta."""
    model = ContaBancaria
    template_name = 'cadastros/contas/confirm_delete.html'
    success_url = reverse_lazy('cadastros:conta_list')
    
    def get_object(self, queryset=None):
        """Busca conta por banco+agencia+conta ao invés de pk único."""
        from django.http import Http404
        pk_str = self.kwargs.get('pk')
        if '-' in pk_str:
            parts = pk_str.split('-')
            if len(parts) == 3:
                banco_cod, agencia_num, conta_num = parts
                return get_object_or_404(
                    ContaBancaria,
                    banco=int(banco_cod),
                    agencia=int(agencia_num),
                    conta=int(conta_num)
                )
        raise Http404("Conta não encontrada")
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Excluir Conta Bancária'
        return context
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Conta excluída com sucesso!')
        return super().delete(request, *args, **kwargs)
