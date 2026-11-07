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

def _normalizar_texto(texto):
    import unicodedata
    return ''.join(
        c for c in unicodedata.normalize('NFKD', texto or '')
        if not unicodedata.combining(c)
    ).lower()


@require_GET
def api_buscar_cidades(request):
    q = request.GET.get('q', '').strip()
    if len(q) < 2:
        return JsonResponse({'results': []})
    cidades = list(
        Cidade.objects.filter(
            Q(nome__icontains=q) | Q(estado__uf__icontains=q)
        ).select_related('estado')[:20]
    )
    if not cidades:
        # Busca sem acentos (ex.: "Sao Paulo" encontra "São Paulo"), priorizando
        # correspondências exatas e prefixos.
        qn = _normalizar_texto(q)
        candidatos = []
        for cidade in Cidade.objects.select_related('estado').all():
            nome_n = _normalizar_texto(cidade.nome)
            uf = cidade.estado.uf.lower()
            if qn == nome_n:
                score = 0
            elif nome_n.startswith(qn) or qn == uf:
                score = 1
            elif qn in nome_n:
                score = 2
            else:
                continue
            candidatos.append((score, len(cidade.nome), cidade.nome, cidade))
        candidatos.sort(key=lambda item: (item[0], item[1], item[2]))
        cidades = [item[3] for item in candidatos[:20]]
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


@require_GET
def api_consultar_cnpj(request, cnpj):
    """Consulta CNPJ nas APIs públicas (BrasilAPI com fallback para ReceitaWS) e associa cidade local."""
    import json
    import urllib.request
    import urllib.error

    cnpj_limpo = ''.join(filter(str.isdigit, str(cnpj)))
    if len(cnpj_limpo) != 14:
        return JsonResponse({'erro': 'CNPJ deve conter exatamente 14 dígitos.'}, status=400)

    # 1. Tenta BrasilAPI
    try:
        req = urllib.request.Request(
            f'https://brasilapi.com.br/api/cnpj/v1/{cnpj_limpo}',
            headers={'User-Agent': 'ERP-Blanjos/1.0'}
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode('utf-8'))
                ibge = data.get('codigo_ibge') or data.get('codigo_municipio_ibge')
                cidade_obj = None
                if ibge:
                    try:
                        cidade_obj = Cidade.objects.filter(codigo_ibge=int(ibge)).first()
                    except:
                        pass
                if not cidade_obj and data.get('municipio') and data.get('uf'):
                    cidade_obj = Cidade.objects.filter(
                        nome__iexact=data.get('municipio'),
                        estado__uf__iexact=data.get('uf')
                    ).first()

                telefone = data.get('ddd_telefone_1', '')
                if not telefone and data.get('telefone'):
                    telefone = data.get('telefone')

                return JsonResponse({
                    'sucesso': True,
                    'razao_social': data.get('razao_social') or '',
                    'nome_fantasia': data.get('nome_fantasia') or '',
                    'cnpj': cnpj_limpo,
                    'cep': data.get('cep') or '',
                    'logradouro': data.get('logradouro') or '',
                    'numero': data.get('numero') or '',
                    'complemento': data.get('complemento') or '',
                    'bairro': data.get('bairro') or '',
                    'municipio': data.get('municipio') or '',
                    'uf': data.get('uf') or '',
                    'cidade_id': cidade_obj.codigo_ibge if cidade_obj else (ibge or ''),
                    'cidade_nome': f"{cidade_obj.nome}/{cidade_obj.estado.uf}" if cidade_obj else (f"{data.get('municipio')}/{data.get('uf')}" if data.get('municipio') else ''),
                    'telefone': telefone,
                    'email': data.get('email') or '',
                    'situacao_cadastral': data.get('descricao_situacao_cadastral') or '',
                })
    except Exception:
        pass

    # 2. Fallback para ReceitaWS
    try:
        req = urllib.request.Request(
            f'https://receitaws.com.br/v1/cnpj/{cnpj_limpo}',
            headers={'User-Agent': 'ERP-Blanjos/1.0'}
        )
        with urllib.request.urlopen(req, timeout=6) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode('utf-8'))
                if data.get('status') == 'ERROR':
                    return JsonResponse({'erro': data.get('message', 'Erro na consulta')}, status=400)

                ibge = data.get('ibge')
                cidade_obj = None
                if ibge:
                    try:
                        cidade_obj = Cidade.objects.filter(codigo_ibge=int(ibge)).first()
                    except:
                        pass
                if not cidade_obj and data.get('municipio') and data.get('uf'):
                    cidade_obj = Cidade.objects.filter(
                        nome__iexact=data.get('municipio'),
                        estado__uf__iexact=data.get('uf')
                    ).first()

                return JsonResponse({
                    'sucesso': True,
                    'razao_social': data.get('nome') or '',
                    'nome_fantasia': data.get('fantasia') or '',
                    'cnpj': cnpj_limpo,
                    'cep': (data.get('cep') or '').replace('.', '').replace('-', ''),
                    'logradouro': data.get('logradouro') or '',
                    'numero': data.get('numero') or '',
                    'complemento': data.get('complemento') or '',
                    'bairro': data.get('bairro') or '',
                    'municipio': data.get('municipio') or '',
                    'uf': data.get('uf') or '',
                    'cidade_id': cidade_obj.codigo_ibge if cidade_obj else (ibge or ''),
                    'cidade_nome': f"{cidade_obj.nome}/{cidade_obj.estado.uf}" if cidade_obj else (f"{data.get('municipio')}/{data.get('uf')}" if data.get('municipio') else ''),
                    'telefone': data.get('telefone') or '',
                    'email': data.get('email') or '',
                    'situacao_cadastral': data.get('situacao') or '',
                })
    except Exception as e:
        return JsonResponse({'erro': f'Falha ao consultar CNPJ: {str(e)}'}, status=500)
