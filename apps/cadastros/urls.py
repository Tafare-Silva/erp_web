"""
URLs do módulo de Cadastros.
"""

from django.urls import path, re_path
from .views import (
    marca_views, unidade_views, divisao_views, banco_views,
    agencia_views, conta_views, pessoa_views, debug_views, 
    centro_custo_views, plano_contas_views, tipo_pagamento_views, 
    ncm_views, cfop_views, divisao_impostos_views, codigo_barras_views, imagem_produto_views, pdv_views, venda_views,
    condicional_views, financeiro_views
)
from .views.pessoa_views import api_cidade_por_ibge, api_buscar_cidades
from .views.empresa_views import empresa_config
from .views.produto import ProdutoListView, ProdutoCreateView, ProdutoUpdateView, ProdutoDeleteView, ProdutoDetailView, ajustar_estoque_produto, pagina_ajuste_estoque
from .views.entrada_views import (
    entrada_nf, 
    buscar_produto_entrada,
    finalizar_entrada_nf, 
    listar_entradas,
    detalhe_entrada,
    upload_xml_nfe,
    cadastrar_produtos_xml,
    editar_entrada,
    atualizar_entrada,
    excluir_entrada
    
)

app_name = 'cadastros'

urlpatterns = [
    # Marcas
    path('marcas/', marca_views.MarcaListView.as_view(), name='marca_list'),
    path('marcas/novo/', marca_views.MarcaCreateView.as_view(), name='marca_create'),
    path('marcas/<str:pk>/editar/', marca_views.MarcaUpdateView.as_view(), name='marca_update'),
    path('marcas/<str:pk>/excluir/', marca_views.MarcaDeleteView.as_view(), name='marca_delete'),
    
    # Unidades
    path('unidades/', unidade_views.UnidadeListView.as_view(), name='unidade_list'),
    path('unidades/novo/', unidade_views.UnidadeCreateView.as_view(), name='unidade_create'),
    path('unidades/<str:pk>/editar/', unidade_views.UnidadeUpdateView.as_view(), name='unidade_update'),
    path('unidades/<str:pk>/excluir/', unidade_views.UnidadeDeleteView.as_view(), name='unidade_delete'),
    
    # Divisões
    path('divisoes/', divisao_views.DivisaoListView.as_view(), name='divisao_list'),
    path('divisoes/novo/', divisao_views.DivisaoCreateView.as_view(), name='divisao_create'),
    path('divisoes/<str:pk>/editar/', divisao_views.DivisaoUpdateView.as_view(), name='divisao_update'),
    path('divisoes/<str:pk>/excluir/', divisao_views.DivisaoDeleteView.as_view(), name='divisao_delete'),
    
    # Bancos
    path('bancos/', banco_views.BancoListView.as_view(), name='banco_list'),
    path('bancos/novo/', banco_views.BancoCreateView.as_view(), name='banco_create'),
    path('bancos/<int:pk>/editar/', banco_views.BancoUpdateView.as_view(), name='banco_update'),
    path('bancos/<int:pk>/excluir/', banco_views.BancoDeleteView.as_view(), name='banco_delete'),
    
    # Agências Bancárias
    path('agencias/', agencia_views.AgenciaBancariaListView.as_view(), name='agencia_list'),
    path('agencias/novo/', agencia_views.AgenciaBancariaCreateView.as_view(), name='agencia_create'),
    re_path(r'^agencias/(?P<pk>[\w-]+)/editar/$', agencia_views.AgenciaBancariaUpdateView.as_view(), name='agencia_update'),
    re_path(r'^agencias/(?P<pk>[\w-]+)/excluir/$', agencia_views.AgenciaBancariaDeleteView.as_view(), name='agencia_delete'),
    
    # Contas Bancárias
    path('contas/', conta_views.ContaBancariaListView.as_view(), name='conta_list'),
    path('contas/novo/', conta_views.ContaBancariaCreateView.as_view(), name='conta_create'),
    re_path(r'^contas/(?P<pk>[\w-]+)/editar/$', conta_views.ContaBancariaUpdateView.as_view(), name='conta_update'),
    re_path(r'^contas/(?P<pk>[\w-]+)/excluir/$', conta_views.ContaBancariaDeleteView.as_view(), name='conta_delete'),
    
    # Centros de Custos
    path('centros-custos/', centro_custo_views.CentroCustoListView.as_view(), name='centro_custo_list'),
    path('centros-custos/novo/', centro_custo_views.CentroCustoCreateView.as_view(), name='centro_custo_create'),
    path('centros-custos/<int:pk>/editar/', centro_custo_views.CentroCustoUpdateView.as_view(), name='centro_custo_update'),
    path('centros-custos/<int:pk>/excluir/', centro_custo_views.CentroCustoDeleteView.as_view(), name='centro_custo_delete'),
    
    # Plano de Contas
    path('plano-contas/', plano_contas_views.PlanoContasListView.as_view(), name='plano_contas_list'),
    path('plano-contas/novo/', plano_contas_views.PlanoContasCreateView.as_view(), name='plano_contas_create'),
    path('plano-contas/<int:pk>/editar/', plano_contas_views.PlanoContasUpdateView.as_view(), name='plano_contas_update'),
    path('plano-contas/<int:pk>/excluir/', plano_contas_views.PlanoContasDeleteView.as_view(), name='plano_contas_delete'),
    
    # Tipos de Pagamento
    path('tipos-pagamento/', tipo_pagamento_views.TipoPagamentoListView.as_view(), name='tipo_pagamento_list'),
    path('tipos-pagamento/novo/', tipo_pagamento_views.TipoPagamentoCreateView.as_view(), name='tipo_pagamento_create'),
    path('tipos-pagamento/<str:nome>/editar/', tipo_pagamento_views.TipoPagamentoUpdateView.as_view(), name='tipo_pagamento_update'),
    path('tipos-pagamento/<str:nome>/excluir/', tipo_pagamento_views.TipoPagamentoDeleteView.as_view(), name='tipo_pagamento_delete'),
    
    # Pessoas
    path('pessoas/', pessoa_views.PessoaListView.as_view(), name='pessoa_list'),
    path('pessoas/novo/', pessoa_views.PessoaCreateView.as_view(), name='pessoa_create'),
    path('pessoas/<int:pk>/', pessoa_views.PessoaDetailView.as_view(), name='pessoa_detail'),
    path('pessoas/<int:pk>/editar/', pessoa_views.PessoaUpdateView.as_view(), name='pessoa_update'),
    path('pessoas/<int:pk>/excluir/', pessoa_views.PessoaDeleteView.as_view(), name='pessoa_delete'),
    
    # Produtos
    path('produtos/', ProdutoListView.as_view(), name='produto_list'),
    path('produtos/novo/', ProdutoCreateView.as_view(), name='produto_create'),
    path('produtos/<int:pk>/', ProdutoDetailView.as_view(), name='produto_detail'),
    path('produtos/<int:pk>/editar/', ProdutoUpdateView.as_view(), name='produto_update'),
    path('produtos/<int:pk>/excluir/', ProdutoDeleteView.as_view(), name='produto_delete'),
    path('produtos/<int:pk>/ajustar-estoque/', ajustar_estoque_produto, name='produto_ajustar_estoque'),
    path('estoque/ajustar/', pagina_ajuste_estoque, name='pagina_ajuste_estoque'),

    # Códigos de Barras
    path('produtos/<int:produto_id>/codigos-barras/', codigo_barras_views.codigo_barras_list, name='codigo_barras_list'),
    path('produtos/<int:produto_id>/codigos-barras/novo/', codigo_barras_views.codigo_barras_create, name='codigo_barras_create'),
    path('produtos/<int:produto_id>/codigos-barras/<str:codigo>/excluir/', codigo_barras_views.codigo_barras_delete, name='codigo_barras_delete'),
    
    # Imagens de Produtos
    path('produtos/<int:produto_id>/imagens/', imagem_produto_views.imagem_list, name='imagem_list'),
    path('produtos/<int:produto_id>/imagens/nova/', imagem_produto_views.imagem_create, name='imagem_create'),
    path('produtos/<int:produto_id>/imagens/<int:pk_imagem>/excluir/', imagem_produto_views.imagem_delete, name='imagem_delete'),
    path('imagens/<int:pk_imagem>/view/', imagem_produto_views.imagem_view, name='imagem_view'),
    
    # Cadastros Reservados - NCM
    path('ncm/', ncm_views.NCMListView.as_view(), name='ncm_list'),
    path('ncm/novo/', ncm_views.NCMCreateView.as_view(), name='ncm_create'),
    path('ncm/<str:ncm>/editar/', ncm_views.NCMUpdateView.as_view(), name='ncm_update'),
    path('ncm/<str:ncm>/excluir/', ncm_views.NCMDeleteView.as_view(), name='ncm_delete'),
    
    # Cadastros Reservados - CFOP
    path('cfop/', cfop_views.CFOPListView.as_view(), name='cfop_list'),
    path('cfop/novo/', cfop_views.CFOPCreateView.as_view(), name='cfop_create'),
    path('cfop/<str:cfop>/editar/', cfop_views.CFOPUpdateView.as_view(), name='cfop_update'),
    path('cfop/<str:cfop>/excluir/', cfop_views.CFOPDeleteView.as_view(), name='cfop_delete'),
    
    # Cadastros Reservados - Divisão de Impostos
    path('divisao-impostos/', divisao_impostos_views.DivisaoImpostosListView.as_view(), name='divisao_impostos_list'),
    path('divisao-impostos/novo/', divisao_impostos_views.DivisaoImpostosCreateView.as_view(), name='divisao_impostos_create'),
    path('divisao-impostos/<str:nome>/editar/', divisao_impostos_views.DivisaoImpostosUpdateView.as_view(), name='divisao_impostos_update'),
    path('divisao-impostos/<str:nome>/excluir/', divisao_impostos_views.DivisaoImpostosDeleteView.as_view(), name='divisao_impostos_delete'),
    path('api/divisao-impostos/<str:pk>/', divisao_impostos_views.api_divisao_impostos_detalhe, name='api_divisao_impostos_detalhe'),
    
    # PDV Rápido
    path('pdv/', pdv_views.pdv_index, name='pdv_index'),
    path('pdv/buscar/', pdv_views.pdv_buscar_produto, name='pdv_buscar'),
    path('pdv/finalizar/', pdv_views.pdv_finalizar, name='pdv_finalizar'),
    path('api/pessoas/', pdv_views.api_buscar_pessoas, name='api_pessoas'),
    path('api/pessoas/criar/', pdv_views.api_criar_cliente_rapido, name='api_criar_cliente'),
    
    # Vendas
    path('vendas/', venda_views.VendaListView.as_view(), name='venda_list'),
    path('vendas/<int:pk>/', venda_views.VendaDetailView.as_view(), name='venda_detail'),
    path('vendas/<int:pk>/cupom/', venda_views.cupom_venda, name='venda_cupom'),
    path('vendas/<int:pk>/excluir/', venda_views.excluir_venda, name='venda_excluir'),
    
    # Condicionais
    path('condicionais/', condicional_views.listar_condicionais, name='condicional_list'),
    path('condicionais/criar/', condicional_views.criar_condicional, name='condicional_criar'),
    path('condicionais/buscar/', condicional_views.buscar_condicionais_api, name='condicional_buscar'),
    path('condicionais/<int:pk>/cupom/', condicional_views.cupom_condicional, name='condicional_cupom'),
    path('condicionais/devolucao/', condicional_views.tela_devolucao_multipla, name='condicional_devolucao_multipla'),
    path('condicionais/<int:pk>/devolucao/', condicional_views.tela_devolucao, name='condicional_devolucao'),
    path('condicionais/processar-devolucao/', condicional_views.processar_devolucao_multiplo, name='condicional_processar_multiplo'),
    path('condicionais/<int:pk>/processar-devolucao/', condicional_views.processar_devolucao, name='condicional_processar'),
    path('condicionais/<int:pk>/dados-pdv/', condicional_views.dados_pdv, name='condicional_dados_pdv'),
    path('condicionais/dados-pdv-multiplo/', condicional_views.dados_pdv_multiplo, name='condicional_dados_pdv_multiplo'),
    path('entradas/cadastrar-produtos/', cadastrar_produtos_xml, name='cadastrar_produtos_xml'),

    # ========== ENTRADAS DE NOTA FISCAL ==========
    path('entradas/', listar_entradas, name='listar_entradas'),
    path('entradas/nova/', entrada_nf, name='entrada_nf'),
    path('entradas/buscar-produto/', buscar_produto_entrada, name='buscar_produto_entrada'),
    path('entradas/upload-xml/', upload_xml_nfe, name='upload_xml_nfe'),
    path('entradas/finalizar/', finalizar_entrada_nf, name='finalizar_entrada_nf'),
    path('entradas/<int:pk>/', detalhe_entrada, name='detalhe_entrada'),
    path('entradas/<int:pk>/editar/', editar_entrada, name='editar_entrada'),
    path('entradas/<int:pk>/atualizar/', atualizar_entrada, name='atualizar_entrada'),
    path('entradas/<int:pk>/excluir/', excluir_entrada, name='excluir_entrada'),
    
    # API - Cidade por IBGE (usado pelo ViaCEP frontend)
    path('api/cidade-ibge/<str:ibge>/', api_cidade_por_ibge, name='api_cidade_ibge'),
    path('api/cidades/', api_buscar_cidades, name='api_buscar_cidades'),

    # Empresa (Configurações)
    path('empresa/', empresa_config, name='empresa_config'),

    # Debug
    path('debug-agencias/', debug_views.debug_agencias, name='debug_agencias'),

    # ========== FINANCEIRO E CAIXA ==========
    path('financeiro/contas-pagar/', financeiro_views.listar_titulos, {'tipo': 'P'}, name='contas_pagar'),
    path('financeiro/contas-receber/', financeiro_views.listar_titulos, {'tipo': 'R'}, name='contas_receber'),
    path('financeiro/salvar-titulo/', financeiro_views.salvar_titulo_manual, name='salvar_titulo_manual'),
    path('caixa/status/', financeiro_views.caixa_status, name='caixa_status'),
    path('caixa/abrir/', financeiro_views.caixa_abrir, name='caixa_abrir'),
    path('caixa/fechar/', financeiro_views.caixa_fechar, name='caixa_fechar'),
    path('caixa/operacao/', financeiro_views.caixa_operacao, name='caixa_operacao'),
    path('caixa/', financeiro_views.caixa_controle, name='caixa_controle'),
]
