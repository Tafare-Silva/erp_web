"""Views de Vendas/Movimentações."""
from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView, DetailView
from apps.cadastros.models import MovimentacaoEstoque


class VendaListView(ListView):
    """Lista de vendas."""
    model = MovimentacaoEstoque
    template_name = 'cadastros/vendas/list.html'
    context_object_name = 'vendas'
    paginate_by = 50
    
    def get_queryset(self):
        qs = MovimentacaoEstoque.objects.filter(
            tipo_movimento__in=['VE', 'PV']
        ).select_related('pessoa')
        
        # Filtros
        data_ini = self.request.GET.get('data_ini')
        data_fim = self.request.GET.get('data_fim')
        cliente = self.request.GET.get('cliente')
        
        if data_ini:
            qs = qs.filter(data__gte=data_ini)
        if data_fim:
            qs = qs.filter(data__lte=data_fim)
        if cliente:
            qs = qs.filter(pessoa_id=cliente)
        
        return qs.order_by('-pk_chave')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Totalizadores
        vendas = context['vendas']
        total_vendas = sum(v.calcular_total() for v in vendas)
        
        context['total_vendas'] = total_vendas
        context['quantidade_vendas'] = vendas.count() if hasattr(vendas, 'count') else len(vendas)
        
        # Filtros atuais
        context['filtros'] = {
            'data_ini': self.request.GET.get('data_ini', ''),
            'data_fim': self.request.GET.get('data_fim', ''),
            'cliente': self.request.GET.get('cliente', ''),
        }
        
        return context


class VendaDetailView(DetailView):
    """Detalhes da venda."""
    model = MovimentacaoEstoque
    template_name = 'cadastros/vendas/detail.html'
    context_object_name = 'venda'
    pk_url_kwarg = 'pk'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        venda = self.object
        
        # Buscar itens
        context['itens'] = venda.itens.select_related('produto').all()
        context['total'] = venda.calcular_total()
        
        return context


def cupom_venda(request, pk):
    """Cupom térmico da venda."""
    venda = get_object_or_404(MovimentacaoEstoque, pk_chave=pk)
    itens = venda.itens.select_related('produto').all()
    
    from apps.cadastros.models import Empresa
    empresa = Empresa.objects.first()
    emit = empresa.pessoa if empresa else None
    
    subtotal = sum(item.calcular_total() for item in itens)
    
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
