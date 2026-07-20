from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.db.models import Sum
from apps.cadastros.models import Produto, ItemMovimentacaoEstoque, Empresa

class HomeView(LoginRequiredMixin, TemplateView):
    """Página inicial do sistema com resumos."""
    template_name = 'core/home.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        total_produtos = Produto.objects.filter(inativo=False).count()
        
        total_estoque_itens = ItemMovimentacaoEstoque.objects.aggregate(
            total=Sum('quantidade')
        )['total'] or 0
        
        ultimas_movimentacoes = ItemMovimentacaoEstoque.objects.select_related(
            'movimentacao', 'produto', 'local'
        ).order_by('-movimentacao__data_criacao')[:10]
        
        try:
            empresa = Empresa.objects.select_related('pessoa').first()
        except:
            empresa = None
        
        context.update({
            'titulo': 'Dashboard - ERP Web',
            'total_produtos': total_produtos,
            'total_estoque_itens': int(total_estoque_itens) if total_estoque_itens else 0,
            'ultimas_movimentacoes': ultimas_movimentacoes,
            'empresa': empresa,
        })
        
        return context