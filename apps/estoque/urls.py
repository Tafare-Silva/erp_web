from django.urls import path
from . import views

app_name = 'estoque'

urlpatterns = [
    # Locais de Estoque
    path('locais/', views.LocalEstoqueListView.as_view(), name='local_estoque_list'),
    path('locais/novo/', views.LocalEstoqueCreateView.as_view(), name='local_estoque_create'),
    path('locais/<str:local>/editar/', views.LocalEstoqueUpdateView.as_view(), name='local_estoque_update'),
    path('locais/<str:local>/deletar/', views.LocalEstoqueDeleteView.as_view(), name='local_estoque_delete'),

    # Páginas principais
    path('movimentacao/', views.movimentacao_estoque_view, name='movimentacao_estoque'),
    
    path('', views.consulta_estoque, name='consulta_estoque'),
    #path('entrada/', views.entrada_manual_view, name='entrada_manual'),
    #path('saida/', views.saida_manual_view, name='saida_manual'),
    path('entrada/', views.entrada_manual_view, name='entrada_manual'),  # ✅ Aponta para v2
    path('saida/', views.saida_manual_view, name='saida_manual'),   
    path('transferencia/', views.transferencia_view, name='transferencia'),
    path('historico/', views.historico_view, name='historico'),
    path('produto/<int:produto_id>/', views.estoque_produto_view, name='estoque_produto'),

    # API
    path('api/buscar-produto/', views.api_buscar_produto, name='api_buscar_produto'),
    path('api/saldo-produto/', views.api_saldo_produto, name='api_saldo_produto'),
]