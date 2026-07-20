"""
Views do Módulo de Estoque - 100% Django ORM
Estrutura: Consulta → Movimentações (Entrada/Saída/Transferência/Unificada) → Histórico → API
"""

import json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.db.models import Q, Sum, F, ExpressionWrapper, DecimalField
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView

from apps.cadastros.models import Produto
from .models import LocalEstoque, SaldoEstoque
from .services import EstoqueService
from .forms import LocalEstoqueForm


# ═══════════════════════════════════════════════════════════════
# 1️⃣ CONSULTA DE ESTOQUE
# ═══════════════════════════════════════════════════════════════

def consulta_estoque(request):
    """Consulta de estoque com filtros."""
    filtros = {
        'produto': request.GET.get('produto', ''),
        'local': request.GET.get('local', ''),
        'zerados': request.GET.get('zerados', ''),
    }

    estoque = EstoqueService.listar_estoque(filtros)
    locais = EstoqueService.obter_locais()

    totais_qs = estoque.aggregate(
        total_itens=Sum('quantidade'),
        total_valor=Sum(
            ExpressionWrapper(
                F('quantidade') * F('produto__preco_venda'),
                output_field=DecimalField()
            )
        )
    )

    total_produtos = estoque.values('produto').distinct().count()

    return render(request, 'estoque/consulta.html', {
        'estoque': estoque,
        'locais': locais,
        'filtros': filtros,
        'totais': {
            'produtos': total_produtos,
            'itens': totais_qs['total_itens'] or 0,
            'valor': totais_qs['total_valor'] or 0,
        }
    })


# ═══════════════════════════════════════════════════════════════
# 2️⃣ MOVIMENTAÇÕES INDIVIDUAIS (Suas views originais)
# ═══════════════════════════════════════════════════════════════

def entrada_manual_view(request):
    """Tela de entrada manual de estoque com múltiplos produtos."""
    if request.method == 'POST':
        try:
            produtos_json = request.POST.get('produtos_json', '[]')
            local_id = request.POST.get('local')
            motivo = request.POST.get('motivo', '').strip()
            
            produtos_data = json.loads(produtos_json)
            
            if not produtos_data or not local_id or not motivo:
                messages.error(request, '❌ Preencha todos os campos obrigatórios.')
                return redirect('estoque:entrada_manual')
            
            movimentacoes = []
            for produto_info in produtos_data:
                mov_id = EstoqueService.entrada_manual(
                    produto_id=int(produto_info['pk_chave']),
                    quantidade=float(produto_info['quantidade']),
                    local_id=int(local_id),
                    motivo=motivo,
                    usuario=request.user,
                )
                movimentacoes.append(mov_id)
            
            messages.success(
                request, 
                f'✅ Entrada registrada com sucesso! {len(movimentacoes)} produto(s) adicionado(s).'
            )
            return redirect('estoque:entrada_manual')
        
        except json.JSONDecodeError:
            messages.error(request, '❌ Erro ao processar produtos.')
        except Exception as e:
            messages.error(request, f'❌ {str(e)}')
    
    return render(request, 'estoque/entrada_manual_v2.html', {
        'locais': EstoqueService.obter_locais(),
    })


def saida_manual_view(request):
    """Tela de saída manual de estoque."""
    if request.method == 'POST':
        try:
            produtos_json = request.POST.get('produtos_json', '[]')
            local_id = request.POST.get('local')
            motivo = request.POST.get('motivo', '').strip()
            
            produtos_data = json.loads(produtos_json)
            
            if not produtos_data or not local_id or not motivo:
                messages.error(request, '❌ Preencha todos os campos obrigatórios.')
                return redirect('estoque:saida_manual')
            
            movimentacoes = []
            for produto_info in produtos_data:
                mov_id = EstoqueService.saida_manual(
                    produto_id=int(produto_info['pk_chave']),
                    quantidade=float(produto_info['quantidade']),
                    local_id=int(local_id),
                    motivo=motivo,
                    usuario=request.user,
                )
                movimentacoes.append(mov_id)
            
            messages.success(
                request, 
                f'✅ Saída registrada com sucesso! {len(movimentacoes)} produto(s) removido(s).'
            )
            return redirect('estoque:saida_manual')
        
        except json.JSONDecodeError:
            messages.error(request, '❌ Erro ao processar produtos.')
        except Exception as e:
            messages.error(request, f'❌ {str(e)}')

    return render(request, 'estoque/saida_manual.html', {
        'locais': EstoqueService.obter_locais(),
    })


def transferencia_view(request):
    """Tela de transferência entre locais."""
    if request.method == 'POST':
        try:
            produtos_json = request.POST.get('produtos_json', '[]')
            local_origem_id = request.POST.get('local_origem')
            local_destino_id = request.POST.get('local_destino')
            motivo = request.POST.get('motivo', '').strip()
            
            produtos_data = json.loads(produtos_json)
            
            if not produtos_data or not local_origem_id or not local_destino_id or not motivo:
                messages.error(request, '❌ Preencha todos os campos obrigatórios.')
                return redirect('estoque:transferencia')
            
            movimentacoes = []
            for produto_info in produtos_data:
                saida_id, entrada_id = EstoqueService.transferir(
                    produto_id=int(produto_info['pk_chave']),
                    quantidade=float(produto_info['quantidade']),
                    local_origem_id=int(local_origem_id),
                    local_destino_id=int(local_destino_id),
                    motivo=motivo,
                    usuario=request.user,
                )
                movimentacoes.append((saida_id, entrada_id))
            
            messages.success(
                request,
                f'✅ Transferência realizada! {len(movimentacoes)} produto(s) transferido(s).'
            )
            return redirect('estoque:transferencia')

        except json.JSONDecodeError:
            messages.error(request, '❌ Erro ao processar produtos.')
        except Exception as e:
            messages.error(request, f'❌ {str(e)}')

    return render(request, 'estoque/transferencia.html', {
        'locais': EstoqueService.obter_locais(),
    })


# ═══════════════════════════════════════════════════════════════
# 2️⃣-PLUS MOVIMENTAÇÃO UNIFICADA (Nova opção)
# ═══════════════════════════════════════════════════════════════

def movimentacao_estoque_view(request):
    """✨ Tela unificada de movimentação (entrada, saída, transferência)."""
    if request.method == 'POST':
        try:
            tipo_movimento = request.POST.get('tipo_movimento')
            local_origem_id = request.POST.get('local_origem')
            local_destino_id = request.POST.get('local_destino')
            motivo = request.POST.get('motivo', '').strip()
            produtos_json = request.POST.get('produtos_json', '[]')
            
            if not all([tipo_movimento, motivo]):
                messages.error(request, '❌ Preencha todos os campos obrigatórios.')
                return redirect('estoque:movimentacao_estoque')
            
            if tipo_movimento == 'TRANSFERENCIA' and not (local_origem_id and local_destino_id):
                messages.error(request, '❌ Selecione local de origem e destino.')
                return redirect('estoque:movimentacao_estoque')
            
            if not (local_origem_id or local_destino_id):
                messages.error(request, '❌ Selecione um local.')
                return redirect('estoque:movimentacao_estoque')
            
            produtos_data = json.loads(produtos_json)
            if not produtos_data:
                messages.error(request, '❌ Adicione pelo menos um produto.')
                return redirect('estoque:movimentacao_estoque')
            
            total_processado = 0
            for produto_info in produtos_data:
                produto_id = int(produto_info['pk_chave'])
                quantidade = float(produto_info['quantidade'])
                
                if tipo_movimento == 'ENTRADA':
                    EstoqueService.entrada_manual(
                        produto_id=produto_id,
                        quantidade=quantidade,
                        local_id=int(local_origem_id),
                        motivo=motivo,
                        usuario=request.user,
                    )
                elif tipo_movimento == 'SAIDA':
                    EstoqueService.saida_manual(
                        produto_id=produto_id,
                        quantidade=quantidade,
                        local_id=int(local_origem_id),
                        motivo=motivo,
                        usuario=request.user,
                    )
                elif tipo_movimento == 'TRANSFERENCIA':
                    EstoqueService.transferir(
                        produto_id=produto_id,
                        quantidade=quantidade,
                        local_origem_id=int(local_origem_id),
                        local_destino_id=int(local_destino_id),
                        motivo=motivo,
                        usuario=request.user,
                    )
                total_processado += 1
            
            emoji_tipo = {'ENTRADA': '📥', 'SAIDA': '📤', 'TRANSFERENCIA': '🔄'}
            messages.success(
                request, 
                f'{emoji_tipo.get(tipo_movimento, "")} {total_processado} produto(s) processado(s)!'
            )
            return redirect('estoque:movimentacao_estoque')
        
        except json.JSONDecodeError:
            messages.error(request, '❌ Erro ao processar produtos.')
        except Exception as e:
            messages.error(request, f'❌ {str(e)}')
    
    return render(request, 'estoque/movimentacao_estoque.html', {
        'locais': EstoqueService.obter_locais(),
        'tipos_movimento': [
            ('ENTRADA', '📥 Entrada', 'Adicionar produtos ao estoque'),
            ('SAIDA', '📤 Saída', 'Remover produtos do estoque'),
            ('TRANSFERENCIA', '🔄 Transferência', 'Mover entre locais'),
        ]
    })


# ═══════════════════════════════════════════════════════════════
# 3️⃣ HISTÓRICO
# ═══════════════════════════════════════════════════════════════

def historico_view(request):
    """Histórico de movimentações com filtros."""
    produto_id = request.GET.get('produto_id')
    local_id = request.GET.get('local')
    limite = int(request.GET.get('limite', 100))

    historico = EstoqueService.obter_historico(
        produto_id=produto_id,
        local_id=local_id,
        limite=limite,
    )

    return render(request, 'estoque/historico.html', {
        'historico': historico,
        'locais': EstoqueService.obter_locais(),
        'produto_id': produto_id,
        'local_id': local_id,
        'limite': limite,
    })


def estoque_produto_view(request, produto_id):
    """Detalhe do estoque de um produto específico."""
    produto = get_object_or_404(Produto, pk=produto_id)

    saldos = SaldoEstoque.objects.filter(
        produto=produto
    ).select_related('local').order_by('local__local')

    saldo_total = saldos.aggregate(
        total=Sum('quantidade')
    )['total'] or 0

    historico = EstoqueService.obter_historico(
        produto_id=produto_id, limite=50
    )

    return render(request, 'estoque/estoque_produto.html', {
        'produto': produto,
        'saldos': saldos,
        'saldo_total': saldo_total,
        'historico': historico,
    })


# ═══════════════════════════════════════════════════════════════
# 4️⃣ GERENCIAMENTO DE LOCAIS (Class-based views)
# ═══════════════════════════════════════════════════════════════

class LocalEstoqueListView(ListView):
    """Lista todos os locais de estoque."""
    model = LocalEstoque
    template_name = 'estoque/local_estoque_list.html'
    context_object_name = 'locais'
    paginate_by = 20

    def get_queryset(self):
        return LocalEstoque.objects.all().order_by('local')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Locais de Estoque'
        return context


class LocalEstoqueCreateView(CreateView):
    """Criar novo local de estoque."""
    model = LocalEstoque
    form_class = LocalEstoqueForm
    template_name = 'estoque/local_estoque_form.html'
    success_url = reverse_lazy('estoque:local_estoque_list')

    def form_valid(self, form):
        messages.success(self.request, f'✅ Local "{form.cleaned_data["local"]}" criado com sucesso!')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Novo Local de Estoque'
        context['botao_texto'] = 'Criar'
        return context


class LocalEstoqueUpdateView(UpdateView):
    """Editar local de estoque."""
    model = LocalEstoque
    form_class = LocalEstoqueForm
    template_name = 'estoque/local_estoque_form.html'
    success_url = reverse_lazy('estoque:local_estoque_list')
    pk_url_kwarg = 'local'

    def get_object(self):
        return LocalEstoque.objects.get(local=self.kwargs['local'])

    def form_valid(self, form):
        messages.success(self.request, f'✅ Local "{form.cleaned_data["local"]}" atualizado com sucesso!')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Local de Estoque'
        context['botao_texto'] = 'Atualizar'
        return context


class LocalEstoqueDeleteView(DeleteView):
    """Deletar local de estoque."""
    model = LocalEstoque
    template_name = 'estoque/local_estoque_confirm_delete.html'
    success_url = reverse_lazy('estoque:local_estoque_list')
    pk_url_kwarg = 'local'

    def get_object(self):
        return LocalEstoque.objects.get(local=self.kwargs['local'])

    def delete(self, request, *args, **kwargs):
        local_nome = self.get_object().local
        messages.success(request, f'✅ Local "{local_nome}" deletado com sucesso!')
        return super().delete(request, *args, **kwargs)


# ═══════════════════════════════════════════════════════════════
# 5️⃣ API ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@require_http_methods(["GET"])
def api_buscar_produto(request):
    """API: Buscar produto por nome ou referência."""
    termo = request.GET.get('q', '').strip()

    if len(termo) < 2:
        return JsonResponse({'produtos': []})

    produtos = Produto.objects.filter(
        Q(nome__icontains=termo) |
        Q(referencia_fabrica__icontains=termo),
        inativo=False,
    ).values(
        'pk_chave', 'nome', 'preco_venda', 'custo_referencia', 'referencia_fabrica'
    ).order_by('nome')[:20]

    return JsonResponse({'produtos': list(produtos)})


@require_http_methods(["GET"])
def api_saldo_produto(request):
    """API: Retorna saldo de um produto."""
    produto_id = request.GET.get('produto_id')
    local_id = request.GET.get('local')

    if not produto_id:
        return JsonResponse({'erro': 'produto_id obrigatório'}, status=400)

    try:
        saldo = EstoqueService.obter_saldo_produto(
            produto_id=int(produto_id),
            local_id=int(local_id) if local_id else None,
        )
        return JsonResponse({
            'produto_id': produto_id,
            'local_id': local_id or 'GERAL',
            'saldo': float(saldo),
        })
    except Exception as e:
        return JsonResponse({'erro': str(e)}, status=500)