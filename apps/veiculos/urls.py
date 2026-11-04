from django.urls import path

from . import views

app_name = 'veiculos'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('veiculos/', views.veiculo_list, name='veiculo_list'),
    path('veiculos/novo/', views.veiculo_create, name='veiculo_create'),
    path('veiculos/<int:pk>/editar/', views.veiculo_update, name='veiculo_update'),
    path('veiculos/<int:pk>/excluir/', views.veiculo_delete, name='veiculo_delete'),

    path('marcas/', views.marca_list, name='marca_list'),
    path('marcas/importar/', views.marca_importar, name='marca_importar'),
    path('marcas/nova/', views.marca_create, name='marca_create'),
    path('marcas/<int:pk>/editar/', views.marca_update, name='marca_update'),
    path('marcas/<int:pk>/excluir/', views.marca_delete, name='marca_delete'),

    path('modelos/', views.modelo_list, name='modelo_list'),
    path('modelos/marca/<int:marca_id>/', views.modelo_list, name='modelo_list_por_marca'),
    path('modelos/marca/<int:marca_id>/importar/', views.modelo_importar, name='modelo_importar_por_marca'),
    path('modelos/novo/', views.modelo_create, name='modelo_create'),
    path('modelos/marca/<int:marca_id>/novo/', views.modelo_create, name='modelo_create_por_marca'),
    path('modelos/<int:pk>/editar/', views.modelo_update, name='modelo_update'),
    path('modelos/<int:pk>/excluir/', views.modelo_delete, name='modelo_delete'),

    path('api/marcas/', views.api_marcas, name='api_marcas'),
    path('api/marcas/<int:marca_id>/modelos/', views.api_modelos_por_marca, name='api_modelos_por_marca'),
    path('api/fipe/', views.api_fipe, name='api_fipe'),
    path('api/consulta-placa/', views.api_consulta_placa, name='api_consulta_placa'),
    path('api/pessoas/', views.api_pessoas, name='api_pessoas'),
    path('api/tipos-pagamento/', views.api_tipos_pagamento, name='api_tipos_pagamento'),
    path('api/veiculos-entrada/', views.api_veiculos_entrada, name='api_veiculos_entrada'),
    path('veiculos/<int:pk>/vender/', views.veiculo_vender_api, name='veiculo_vender'),
    path('veiculos/<int:pk>/emitir-compra/', views.veiculo_emitir_compra, name='veiculo_emitir_compra'),
]