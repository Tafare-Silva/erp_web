from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.contrib import messages
from django.db.models import Q, Sum, DecimalField
from django.shortcuts import get_object_or_404
from django.db.models.functions import Coalesce
from django.http import JsonResponse, HttpResponseRedirect
from django.db import transaction
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from decimal import Decimal, InvalidOperation
from apps.cadastros.models import Produto, Marca, Divisao, Empresa, Unidade, NCM
from apps.cadastros.models.produto import LocalEstoque, SaldoEstoque
from apps.cadastros.models.reservados import DivisaoImpostosSaida, CST, CFOP
from apps.cadastros.forms import ProdutoForm, ConversaoUnidadeFormSet, ProdutoVariacaoFormSet, ProdutoCanalFormSet

class ProdutoListView(ListView):
    model = Produto
    template_name = 'cadastros/produtos/list.html'
    context_object_name = 'produtos'
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().select_related('marca', 'divisao')
        
        # O Coalesce garante que se for vazio (None), ele retorna 0
        try:
            qs = qs.annotate(estoque_total=Coalesce(Sum('saldos_estoque__quantidade'), 0, output_field=DecimalField()))
        except Exception:
            try:
                qs = qs.annotate(estoque_total=Coalesce(Sum('saldoestoque__quantidade'), 0, output_field=DecimalField()))
            except Exception:
                pass

        # 3. Filtros existentes
        q = self.request.GET.get('q')
        marca = self.request.GET.get('marca')
        divisao = self.request.GET.get('divisao')
        
        if q:
            qs = qs.filter(Q(nome__icontains=q) | Q(pk_chave__icontains=q) | Q(codigo__icontains=q) | Q(referencia__icontains=q))
        if marca:
            qs = qs.filter(marca__nome=marca) 
        if divisao:
            qs = qs.filter(divisao__nome=divisao)
            
        return qs.order_by('nome') # Ordenação alfabética padrão

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['marcas'] = Marca.objects.all()
        context['divisoes'] = Divisao.objects.all()
        return context

class ProdutoCreateView(CreateView):
    model = Produto
    form_class = ProdutoForm
    template_name = 'cadastros/produtos/form.html'
    success_url = '/cadastros/produtos/'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['formset_conversoes'] = ConversaoUnidadeFormSet(self.request.POST, instance=self.object, prefix='conversoes')
            context['formset_variacoes'] = ProdutoVariacaoFormSet(self.request.POST, instance=self.object, prefix='variacoes')
            context['formset_canais'] = ProdutoCanalFormSet(self.request.POST, instance=self.object, prefix='canais')
        else:
            context['formset_conversoes'] = ConversaoUnidadeFormSet(instance=self.object, prefix='conversoes')
            context['formset_variacoes'] = ProdutoVariacaoFormSet(instance=self.object, prefix='variacoes')
            context['formset_canais'] = ProdutoCanalFormSet(instance=self.object, prefix='canais')
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        formset_conversoes = context['formset_conversoes']
        formset_variacoes = context['formset_variacoes']
        formset_canais = context['formset_canais']
        if formset_conversoes.is_valid() and formset_variacoes.is_valid() and formset_canais.is_valid():
            with transaction.atomic():
                self.object = form.save()
                formset_conversoes.instance = self.object
                formset_conversoes.save()
                formset_variacoes.instance = self.object
                formset_variacoes.save()
                formset_canais.instance = self.object
                formset_canais.save()
                estoque_inicial = form.cleaned_data.get('estoque_inicial') or Decimal('0')
                if estoque_inicial > 0:
                    local = self.object.local_padrao
                    if not local:
                        empresa = Empresa.objects.first()
                        if empresa:
                            local = empresa.local_padrao or empresa.local_padrao_xml
                    if not local:
                        local = LocalEstoque.objects.first()
                    if local:
                        SaldoEstoque.objects.update_or_create(
                            produto=self.object,
                            local=local,
                            defaults={'quantidade': estoque_inicial},
                        )
            messages.success(self.request, f'Produto "{form.instance.nome}" criado com sucesso!')
            return HttpResponseRedirect(self.get_success_url())
        return self.form_invalid(form)

    def get_success_url(self):
        return f'/cadastros/produtos/?q={self.object.pk_chave}'


@login_required
def api_buscar_ncm(request):
    q = (request.GET.get('q') or '').strip()
    qs = NCM.objects.all()
    if q:
        qs = qs.filter(Q(ncm__icontains=q) | Q(descricao__icontains=q) | Q(nome__icontains=q))
    resultados = [
        {'ncm': n.ncm, 'descricao': n.descricao, 'nome': n.nome or ''}
        for n in qs.order_by('ncm')[:25]
    ]
    return JsonResponse({'resultados': resultados})


@login_required
@require_POST
def api_cadastro_rapido(request):
    tipo = (request.POST.get('tipo') or '').strip()
    nome = (request.POST.get('nome') or '').strip()
    try:
        if tipo == 'marca':
            if not nome:
                return JsonResponse({'ok': False, 'erro': 'Informe o nome da marca.'}, status=400)
            obj, _ = Marca.objects.get_or_create(nome=nome)
            return JsonResponse({'ok': True, 'value': obj.pk, 'label': obj.nome})

        if tipo == 'divisao':
            if not nome:
                return JsonResponse({'ok': False, 'erro': 'Informe o nome da divisão.'}, status=400)
            codigo = (request.POST.get('codigo') or '').strip() or nome[:20]
            obj, _ = Divisao.objects.get_or_create(nome=nome, defaults={'codigo': codigo})
            return JsonResponse({'ok': True, 'value': obj.pk, 'label': obj.nome})

        if tipo == 'unidade':
            if not nome:
                return JsonResponse({'ok': False, 'erro': 'Informe o nome da unidade.'}, status=400)
            simbolo = (request.POST.get('simbolo') or '').strip().upper()[:3]
            if not simbolo:
                return JsonResponse({'ok': False, 'erro': 'Informe o símbolo (ex: UN, KG).'}, status=400)
            obj, _ = Unidade.objects.get_or_create(nome=nome, defaults={'simbolo': simbolo})
            return JsonResponse({'ok': True, 'value': obj.pk, 'label': str(obj)})

        if tipo == 'ncm':
            codigo = ''.join(filter(str.isdigit, request.POST.get('ncm') or ''))
            descricao = (request.POST.get('descricao') or '').strip()
            if len(codigo) != 8:
                return JsonResponse({'ok': False, 'erro': 'O NCM deve ter 8 dígitos.'}, status=400)
            if not descricao:
                return JsonResponse({'ok': False, 'erro': 'Informe a descrição do NCM.'}, status=400)
            obj, _ = NCM.objects.update_or_create(
                ncm=codigo,
                defaults={'descricao': descricao, 'nome': descricao[:100]},
            )
            return JsonResponse({'ok': True, 'value': obj.pk, 'label': f'{obj.ncm} - {obj.descricao[:60]}'})

        if tipo == 'divisao_impostos':
            codigo = (request.POST.get('codigo') or '').strip()[:5]
            descricao = (request.POST.get('descricao') or '').strip() or nome
            if not codigo or not descricao:
                return JsonResponse({'ok': False, 'erro': 'Informe o código e a descrição da regra.'}, status=400)
            cst_icms = CST.objects.filter(tipo_imposto='ICMS').first()
            cst_pis = CST.objects.filter(tipo_imposto='PIS').first()
            cst_cofins = CST.objects.filter(tipo_imposto='COFINS').first()
            cfop_estadual = CFOP.objects.filter(cfop__startswith='5').first() or CFOP.objects.first()
            cfop_interestadual = CFOP.objects.filter(cfop__startswith='6').first() or CFOP.objects.first()
            if not all([cst_icms, cst_pis, cst_cofins, cfop_estadual, cfop_interestadual]):
                return JsonResponse({
                    'ok': False,
                    'erro': 'Cadastre CST/CFOP antes, ou crie a regra pela tela completa de Divisão de Impostos.'
                }, status=400)
            obj, _ = DivisaoImpostosSaida.objects.get_or_create(
                divisao=codigo,
                defaults={
                    'nome': nome or descricao,
                    'descricao': descricao,
                    'cst_icms': cst_icms,
                    'cst_pis': cst_pis,
                    'cst_cofins': cst_cofins,
                    'cfop_dentro_estado': cfop_estadual,
                    'cfop_fora_estado': cfop_interestadual,
                },
            )
            return JsonResponse({'ok': True, 'value': obj.pk, 'label': str(obj)})

        return JsonResponse({'ok': False, 'erro': 'Tipo de cadastro inválido.'}, status=400)
    except (ValueError, InvalidOperation, TypeError) as exc:
        return JsonResponse({'ok': False, 'erro': str(exc)}, status=400)

class ProdutoUpdateView(UpdateView):
    model = Produto
    form_class = ProdutoForm
    template_name = 'cadastros/produtos/form.html'
    pk_url_kwarg = 'pk'
    success_url = '/cadastros/produtos/'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['formset_conversoes'] = ConversaoUnidadeFormSet(self.request.POST, instance=self.object, prefix='conversoes')
            context['formset_variacoes'] = ProdutoVariacaoFormSet(self.request.POST, instance=self.object, prefix='variacoes')
            context['formset_canais'] = ProdutoCanalFormSet(self.request.POST, instance=self.object, prefix='canais')
        else:
            context['formset_conversoes'] = ConversaoUnidadeFormSet(instance=self.object, prefix='conversoes')
            context['formset_variacoes'] = ProdutoVariacaoFormSet(instance=self.object, prefix='variacoes')
            context['formset_canais'] = ProdutoCanalFormSet(instance=self.object, prefix='canais')
        if self.object and hasattr(self.object, 'saldos_estoque'):
            saldo_total = self.object.saldos_estoque.aggregate(total=Sum('quantidade'))['total'] or 0
            context['saldos_estoque'] = self.object.saldos_estoque.select_related('local').all()
        else:
            saldo_total = 0
            context['saldos_estoque'] = []
        context['quantidade_estoque'] = saldo_total
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        formset_conversoes = context['formset_conversoes']
        formset_variacoes = context['formset_variacoes']
        formset_canais = context['formset_canais']
        if formset_conversoes.is_valid() and formset_variacoes.is_valid() and formset_canais.is_valid():
            with transaction.atomic():
                self.object = form.save()
                formset_conversoes.instance = self.object
                formset_conversoes.save()
                formset_variacoes.instance = self.object
                formset_variacoes.save()
                formset_canais.instance = self.object
                formset_canais.save()
            messages.success(self.request, f'Produto "{form.instance.nome}" atualizado com sucesso!')
            return HttpResponseRedirect(self.get_success_url())
        return self.form_invalid(form)

    def get_success_url(self):
        return f'/cadastros/produtos/?q={self.object.pk_chave}' # Mudei para buscar pela PK, é mais seguro que o nome

class ProdutoDeleteView(DeleteView):
    model = Produto
    template_name = 'cadastros/produtos/confirm_delete.html' # CORREÇÃO: Faltava o 'cadastros/'
    pk_url_kwarg = 'pk'
    success_url = '/cadastros/produtos/'

    def delete(self, request, *args, **kwargs):
        produto = self.get_object()
        # Tratamento de erro elegante caso tente excluir um produto que já tem movimentação!
        try:
            response = super().delete(request, *args, **kwargs)
            messages.success(self.request, f'Produto "{produto.nome}" excluído com sucesso!')
            return response
        except Exception as e:
            messages.error(self.request, f'Não é possível excluir o produto "{produto.nome}" porque ele já possui vínculos no sistema (ex: histórico de estoque).')
            from django.shortcuts import redirect
            return redirect('cadastros:produto_list')
        
@transaction.atomic
def ajustar_estoque_produto(request, pk):
    """API: Ajuste direto de estoque a partir do cadastro do produto."""
    if request.method != 'POST':
        return JsonResponse({'erro': 'Método inválido'}, status=400)

    try:
        import json
        produto = get_object_or_404(Produto, pk_chave=pk)

        if request.content_type == 'application/json':
            dados = json.loads(request.body)
        else:
            dados = request.POST.dict()

        local_nome = dados.get('local')
        nova_qtd = Decimal(str(dados.get('quantidade', 0)))
        motivo = dados.get('motivo', 'Ajuste manual via cadastro de produto')

        local = LocalEstoque.objects.filter(local=local_nome).first()
        if not local:
            local = LocalEstoque.objects.first()
        if not local:
            return JsonResponse({'erro': 'Nenhum Local de Estoque cadastrado.'}, status=400)

        saldo, _ = SaldoEstoque.objects.get_or_create(
            produto=produto, local=local, defaults={'quantidade': 0}
        )
        saldo_anterior = saldo.quantidade
        saldo.quantidade = nova_qtd
        saldo.save()

        return JsonResponse({
            'sucesso': True,
            'saldo_anterior': float(saldo_anterior),
            'saldo_novo': float(nova_qtd),
        })
    except Exception as e:
        return JsonResponse({'erro': str(e)}, status=500)


from django.shortcuts import render

def pagina_ajuste_estoque(request):
    """Página dedicada para ajuste de estoque."""
    produtos = Produto.objects.filter(inativo=False).order_by('nome')
    locais = LocalEstoque.objects.all().order_by('local')
    return render(request, 'cadastros/estoque/ajuste.html', {
        'produtos': produtos,
        'locais': locais,
    })


class ProdutoDetailView(DetailView):
    model = Produto
    template_name = 'cadastros/produtos/detail.html' # CORREÇÃO: Faltava o 'cadastros/'
    context_object_name = 'produto'
    pk_url_kwarg = 'pk'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # BUSCA DE TABELAS FILHAS (ForeignKeys) VIA ORM
        # O Django cria automaticamente o sufixo "_set" para buscar os filhos, a menos que você tenha usado "related_name" no model.
        
        # 1. Códigos de Barras
        if hasattr(self.object, 'codigos_barras'):
            context['codigos_barras'] = self.object.codigos_barras.all()
        else:
            context['codigos_barras'] = self.object.codigobarras_set.all() if hasattr(self.object, 'codigobarras_set') else []
            
        # 2. Imagens
        if hasattr(self.object, 'imagens'):
            context['imagens'] = self.object.imagens.all()
        else:
            context['imagens'] = self.object.imagemproduto_set.all() if hasattr(self.object, 'imagemproduto_set') else []
            
        # 3. Saldos de Estoque (trazendo o nome do Local junto com select_related para não pesar o banco)
        if hasattr(self.object, 'saldos_estoque'):
            context['saldos'] = self.object.saldos_estoque.select_related('local').all()
        elif hasattr(self.object, 'saldoestoque_set'):
            context['saldos'] = self.object.saldoestoque_set.select_related('local').all()
        else:
            context['saldos'] = []
            
        return context