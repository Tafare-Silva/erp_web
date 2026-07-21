"""Views de Vendas/Movimentações."""
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView
from django.contrib import messages
from django.db.models import Q, Sum
from apps.cadastros.models import MovimentacaoEstoque, ItemMovimentacaoEstoque, Pessoa
from decimal import Decimal


class VendaListView(ListView):
    """Lista de vendas."""
    model = MovimentacaoEstoque
    template_name = 'cadastros/vendas/list.html'
    context_object_name = 'vendas'
    paginate_by = 50
    
    def get_queryset(self):
        qs = MovimentacaoEstoque.objects.filter(
            tipo_movimento__in=['VE', 'PV']
        ).select_related('pessoa', 'vendedor')
        
        data_ini = self.request.GET.get('data_ini')
        data_fim = self.request.GET.get('data_fim')
        cliente = self.request.GET.get('cliente')
        vendedor = self.request.GET.get('vendedor')
        
        if data_ini:
            qs = qs.filter(data__gte=data_ini)
        if data_fim:
            qs = qs.filter(data__lte=data_fim)
        if cliente:
            qs = qs.filter(pessoa__nome__icontains=cliente)
        if vendedor:
            qs = qs.filter(vendedor_id=vendedor)
        
        return qs.order_by('-pk_chave')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        qs_total = self.get_queryset()
        from django.db.models import Sum
        total_vendas = qs_total.aggregate(total=Sum('vr_total_liquido'))['total'] or 0
        total_vendas = abs(total_vendas)
        
        context['total_vendas'] = total_vendas
        context['quantidade_vendas'] = qs_total.count()
        
        context['filtros'] = {
            'data_ini': self.request.GET.get('data_ini', ''),
            'data_fim': self.request.GET.get('data_fim', ''),
            'cliente': self.request.GET.get('cliente', ''),
            'vendedor': self.request.GET.get('vendedor', ''),
        }
        
        context['vendedores'] = Pessoa.objects.filter(
            Q(vendedor=True) | Q(funcionario=True)
        ).distinct().order_by('nome')[:100]
        
        return context


class VendaDetailView(DetailView):
    """Detalhes da venda."""
    model = MovimentacaoEstoque
    template_name = 'cadastros/vendas/detail.html'
    context_object_name = 'venda'
    pk_url_kwarg = 'pk'
    
    def get_object(self, queryset=None):
        return get_object_or_404(
            MovimentacaoEstoque.objects.select_related('pessoa', 'vendedor'),
            pk_chave=self.kwargs['pk']
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        venda = self.object
        context['itens'] = venda.itens.select_related('produto').all()
        context['total'] = abs(venda.calcular_total())
        return context


def cupom_venda(request, pk):
    """Cupom térmico da venda."""
    venda = get_object_or_404(MovimentacaoEstoque.objects.select_related('pessoa', 'vendedor'), pk_chave=pk)
    itens = venda.itens.select_related('produto').all()
    
    from apps.cadastros.models import Empresa
    empresa = Empresa.objects.first()
    emit = empresa.pessoa if empresa else None
    
    subtotal = sum(abs(item.calcular_total()) for item in itens)
    
    pagamentos = venda.titulos_financeiros.select_related('tipo_pagamento').all()
    pagamentos_info = [{'tipo': t.tipo_pagamento.tipo_pagamento if t.tipo_pagamento else '—', 'valor': t.valor_pago or t.valor_documento} for t in pagamentos]
    
    context = {
        'venda': venda,
        'itens': itens,
        'subtotal': subtotal,
        'total': subtotal,
        'empresa': empresa,
        'emit': emit,
        'pagamentos': pagamentos_info,
    }
    
    return render(request, 'cadastros/vendas/cupom.html', context)


def excluir_venda(request, pk):
    """Excluir/excluir venda."""
    venda = get_object_or_404(MovimentacaoEstoque, pk_chave=pk)
    
    if venda.pre_venda and venda.pre_venda.efetivada:
        pass
    
    if request.method == 'POST':
        venda.delete()
        messages.success(request, f'Venda #{pk} excluída com sucesso.')
        return redirect('cadastros:venda_list')
    
    return render(request, 'cadastros/vendas/confirm_delete.html', {
        'venda': venda,
    })
