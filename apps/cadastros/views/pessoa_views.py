from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from apps.cadastros.models import Pessoa, PessoaFisica, FuncionarioDetalhes, Cidade, EnderecoPessoa, EnderecoPrincipalPessoa
from apps.cadastros.forms import PessoaForm, PessoaFisicaForm, FuncionarioDetalhesForm


class PessoaListView(ListView):
    model = Pessoa
    template_name = 'cadastros/pessoas/list.html'
    context_object_name = 'pessoas'
    paginate_by = 50
    
    def get_queryset(self):
        qs = super().get_queryset()
        search = self.request.GET.get('q', '')
        tipo = self.request.GET.get('tipo', '')
        
        if search:
            qs = qs.filter(Q(nome__icontains=search) | Q(cpf_cnpj__icontains=search))
        if tipo == 'cliente':
            qs = qs.filter(cliente=True)
        elif tipo == 'fornecedor':
            qs = qs.filter(fornecedor=True)
        elif tipo == 'vendedor':
            qs = qs.filter(vendedor=True)
        elif tipo == 'funcionario':
            qs = qs.filter(funcionario=True)
        
        return qs.order_by('nome')
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['search'] = self.request.GET.get('q', '')
        ctx['tipo_filtro'] = self.request.GET.get('tipo', '')
        return ctx


def _salvar_endereco(pessoa, request):
    logradouro = request.POST.get('logradouro', '').strip()
    cidade_id = request.POST.get('cidade', '').strip()
    if not logradouro or not cidade_id:
        return
    try:
        cidade = Cidade.objects.get(codigo_ibge=int(cidade_id))
    except (Cidade.DoesNotExist, ValueError, TypeError):
        return
    cep = request.POST.get('cep', '').strip()[:9]
    endereco, created = EnderecoPessoa.objects.update_or_create(
        pessoa=pessoa,
        tipo_endereco=request.POST.get('tipo_endereco', 'RESIDENCIAL'),
        defaults={
            'cep': cep,
            'logradouro': logradouro,
            'numero': request.POST.get('numero', 'S/N')[:10],
            'complemento': request.POST.get('complemento', '').strip() or None,
            'bairro': request.POST.get('bairro', '').strip(),
            'cidade': cidade,
        }
    )
    EnderecoPrincipalPessoa.objects.update_or_create(
        pessoa=pessoa,
        defaults={'endereco': endereco},
    )


class PessoaCreateView(CreateView):
    model = Pessoa
    form_class = PessoaForm
    template_name = 'cadastros/pessoas/form.html'
    success_url = reverse_lazy('cadastros:pessoa_list')
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['titulo'] = 'Nova Pessoa'
        ctx['botao_texto'] = 'Salvar'
        ctx['endereco'] = None
        if self.request.POST:
            ctx['form_pf'] = PessoaFisicaForm(self.request.POST, prefix='pf')
            ctx['form_funcionario'] = FuncionarioDetalhesForm(self.request.POST, prefix='func')
        else:
            ctx['form_pf'] = PessoaFisicaForm(prefix='pf')
            ctx['form_funcionario'] = FuncionarioDetalhesForm(prefix='func')
        return ctx
    
    def form_valid(self, form):
        response = super().form_valid(form)
        # Salvar PF se for pessoa física
        if self.object.is_pf() and 'pf_data_nascimento' in self.request.POST:
            form_pf = PessoaFisicaForm(self.request.POST, prefix='pf')
            if form_pf.is_valid():
                pf = form_pf.save(commit=False)
                pf.pessoa = self.object
                pf.save()
        
        # Salvar detalhes funcionário se for funcionário
        if self.object.funcionario:
            form_func = FuncionarioDetalhesForm(self.request.POST, prefix='func')
            if form_func.is_valid():
                func = form_func.save(commit=False)
                func.pessoa = self.object
                func.save()
                
                # Se marcou como vendedor nos detalhes, garantir que Pessoa.vendedor também esteja True
                if func.e_vendedor:
                    self.object.vendedor = True
                    self.object.save(update_fields=['vendedor'])
                    
        _salvar_endereco(self.object, self.request)
        messages.success(self.request, 'Pessoa cadastrada!')
        return response


class PessoaUpdateView(UpdateView):
    model = Pessoa
    form_class = PessoaForm
    template_name = 'cadastros/pessoas/form.html'
    success_url = reverse_lazy('cadastros:pessoa_list')
    pk_url_kwarg = 'pk'
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['titulo'] = 'Editar Pessoa'
        ctx['botao_texto'] = 'Atualizar'
        endereco_rel = getattr(self.object, 'endereco_principal_rel', None)
        ctx['endereco'] = endereco_rel.endereco if endereco_rel else None
        
        # Pessoa Física
        try:
            pf = self.object.dados_pf
            ctx['form_pf'] = PessoaFisicaForm(instance=pf, prefix='pf')
        except:
            ctx['form_pf'] = PessoaFisicaForm(prefix='pf')
            
        # Funcionário
        try:
            func = self.object.detalhes_funcionario
            ctx['form_funcionario'] = FuncionarioDetalhesForm(instance=func, prefix='func')
        except:
            ctx['form_funcionario'] = FuncionarioDetalhesForm(prefix='func')
            
        return ctx
    
    def form_valid(self, form):
        response = super().form_valid(form)
        # Pessoa Física
        if self.object.is_pf():
            try:
                pf = self.object.dados_pf
                form_pf = PessoaFisicaForm(self.request.POST, instance=pf, prefix='pf')
            except:
                form_pf = PessoaFisicaForm(self.request.POST, prefix='pf')
            
            if form_pf.is_valid():
                pf = form_pf.save(commit=False)
                pf.pessoa = self.object
                pf.save()
        
        # Funcionário
        if self.object.funcionario:
            try:
                func = self.object.detalhes_funcionario
                form_func = FuncionarioDetalhesForm(self.request.POST, instance=func, prefix='func')
            except:
                form_func = FuncionarioDetalhesForm(self.request.POST, prefix='func')
            
            if form_func.is_valid():
                func = form_func.save(commit=False)
                func.pessoa = self.object
                func.save()
                
                # Se marcou como vendedor nos detalhes, garantir que Pessoa.vendedor também esteja True
                if func.e_vendedor:
                    self.object.vendedor = True
                    self.object.save(update_fields=['vendedor'])
        
        _salvar_endereco(self.object, self.request)
        messages.success(self.request, 'Pessoa atualizada!')
        return response


class PessoaDeleteView(DeleteView):
    model = Pessoa
    template_name = 'cadastros/pessoas/confirm_delete.html'
    success_url = reverse_lazy('cadastros:pessoa_list')
    pk_url_kwarg = 'pk'
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Pessoa excluída!')
        return super().delete(request, *args, **kwargs)


class PessoaDetailView(DetailView):
    model = Pessoa
    template_name = 'cadastros/pessoas/detail.html'
    context_object_name = 'pessoa'
    pk_url_kwarg = 'pk'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        try:
            ctx['dados_pf'] = self.object.dados_pf
        except:
            ctx['dados_pf'] = None
        ctx['endereco'] = getattr(self.object, 'endereco_principal_rel', None)
        ctx['ultimas_vendas'] = self.object.movimentacoes.filter(
            tipo_movimento__in=['VE', 'PV']
        ).order_by('-pk_chave')[:10]
        return ctx


from django.views.decorators.http import require_GET

@require_GET
def api_buscar_cidades(request):
    q = request.GET.get('q', '').strip()
    if len(q) < 2:
        return JsonResponse({'results': []})
    cidades = Cidade.objects.filter(
        Q(nome__icontains=q) | Q(estado__uf__icontains=q)
    ).select_related('estado')[:20]
    results = [{
        'id': c.codigo_ibge,
        'text': f'{c.nome}/{c.estado.uf}',
        'estado_uf': c.estado.uf,
    } for c in cidades]
    return JsonResponse({'results': results})

@require_GET
def api_cidade_por_ibge(request, ibge):
    try:
        cidade = Cidade.objects.get(codigo_ibge=int(ibge))
        return JsonResponse({
            'id': cidade.codigo_ibge,
            'nome': cidade.nome,
            'estado_id': cidade.estado_id,
            'estado_uf': cidade.estado.uf,
        })
    except (Cidade.DoesNotExist, ValueError):
        return JsonResponse({'erro': 'Cidade não encontrada'}, status=404)
