import json
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.views.generic import TemplateView
from django.db.models import Sum

from apps.cadastros.models import (
    Produto, ItemMovimentacaoEstoque, Empresa, MovimentacaoEstoque, TituloFinanceiro,
)


class HomeView(LoginRequiredMixin, TemplateView):
    """Página inicial do sistema com resumos."""
    template_name = 'core/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        hoje = timezone.localdate()
        inicio_mes = hoje.replace(day=1)

        total_produtos = Produto.objects.filter(inativo=False).count()

        # Vendas no mês
        vendas_mes_qs = MovimentacaoEstoque.objects.filter(
            tipo_movimento='VE',
            data__gte=inicio_mes,
            data__lte=hoje,
        )
        total_vendas_mes = abs(vendas_mes_qs.aggregate(t=Sum('vr_total_liquido'))['t'] or Decimal('0'))
        qtd_vendas_mes = vendas_mes_qs.count()
        ticket_medio = (total_vendas_mes / qtd_vendas_mes) if qtd_vendas_mes else Decimal('0')

        # Vendas hoje
        vendas_hoje = abs(MovimentacaoEstoque.objects.filter(
            tipo_movimento='VE', data=hoje,
        ).aggregate(t=Sum('vr_total_liquido'))['t'] or Decimal('0'))

        # Títulos a receber / pagar em aberto
        a_receber = TituloFinanceiro.objects.filter(
            tipo='R', situacao__in=['ABERTO', 'ATRASADO', 'PARCIAL'],
        ).aggregate(t=Sum('valor_saldo'))['t'] or Decimal('0')

        a_pagar = TituloFinanceiro.objects.filter(
            tipo='P', situacao__in=['ABERTO', 'ATRASADO', 'PARCIAL'],
        ).aggregate(t=Sum('valor_saldo'))['t'] or Decimal('0')

        # Inadimplência (a receber vencido)
        inadimplencia = TituloFinanceiro.objects.filter(
            tipo='R', situacao__in=['ABERTO', 'ATRASADO', 'PARCIAL'],
            data_vencimento__lt=hoje,
        ).aggregate(t=Sum('valor_saldo'))['t'] or Decimal('0')

        # Itens em estoque
        total_estoque_itens = ItemMovimentacaoEstoque.objects.aggregate(
            total=Sum('quantidade')
        )['total'] or 0

        # Gráfico: vendas dos últimos 14 dias
        inicio_graf = hoje - timedelta(days=13)
        vendas_por_dia = (
            MovimentacaoEstoque.objects
            .filter(tipo_movimento='VE', data__gte=inicio_graf, data__lte=hoje)
            .values('data')
            .annotate(total=Sum('vr_total_liquido'))
            .order_by('data')
        )
        mapa = {v['data']: abs(v['total'] or 0) for v in vendas_por_dia}
        labels, valores = [], []
        for i in range(14):
            d = inicio_graf + timedelta(days=i)
            labels.append(d.strftime('%d/%m'))
            valores.append(float(mapa.get(d, 0)))

        chart_vendas = json.dumps({
            'labels': labels,
            'valores': valores,
        })

        ultimas_movimentacoes = ItemMovimentacaoEstoque.objects.select_related(
            'movimentacao', 'produto', 'local'
        ).order_by('-movimentacao__data_criacao')[:8]

        try:
            empresa = Empresa.objects.select_related('pessoa').first()
        except Exception:
            empresa = None

        context.update({
            'titulo': 'Dashboard - ERP Web',
            'hoje': hoje,
            'total_produtos': total_produtos,
            'total_estoque_itens': int(total_estoque_itens) if total_estoque_itens else 0,
            'total_vendas_mes': total_vendas_mes,
            'qtd_vendas_mes': qtd_vendas_mes,
            'ticket_medio': ticket_medio,
            'vendas_hoje': vendas_hoje,
            'a_receber': a_receber,
            'a_pagar': a_pagar,
            'inadimplencia': inadimplencia,
            'chart_vendas': chart_vendas,
            'ultimas_movimentacoes': ultimas_movimentacoes,
            'empresa': empresa,
        })

        return context
