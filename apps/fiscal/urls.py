from django.urls import path
from . import views

app_name = 'fiscal'

urlpatterns = [
    path('nfe/', views.NFeListView.as_view(), name='nfe_list'),
    path('nfe/novo/', views.nfe_create, name='nfe_create'),
    path('nfe/<int:pk>/', views.NFeDetailView.as_view(), name='nfe_detail'),
    path('nfe/<int:pk>/autorizar/', views.nfe_autorizar, name='nfe_autorizar'),
    path('nfe/<int:pk>/cancelar/', views.nfe_cancelar, name='nfe_cancelar'),
    path('nfe/<int:pk>/cce/', views.nfe_cce, name='nfe_cce'),
    path('nfe/<int:pk>/xml/', views.nfe_download_xml, name='nfe_download_xml'),
    path('nfe/<int:pk>/danfe/', views.nfe_danfe, name='nfe_danfe'),
    path('nfe/<int:pk>/simular-autorizar/', views.nfe_simular_autorizar, name='nfe_simular_autorizar'),
    path('api/buscar-clientes/', views.api_buscar_clientes, name='api_buscar_clientes'),
    path('nfe/enviar-lote/', views.nfe_enviar_lote, name='nfe_enviar_lote'),
    path('nfe/consultar/<int:pk>/', views.nfe_consultar_status, name='nfe_consultar_status'),
    path('nfe/<int:pk>/reabrir/', views.nfe_reabrir, name='nfe_reabrir'),
    path('nfe/testar-sefaz/', views.nfe_testar_sefaz, name='nfe_testar_sefaz'),

    path('certificados/', views.CertificadoListView.as_view(), name='certificado_list'),
    path('certificados/novo/', views.certificado_create, name='certificado_create'),
    path('certificados/<int:pk>/', views.certificado_detail, name='certificado_detail'),

    path('api/buscar-venda/', views.api_buscar_venda, name='api_buscar_venda'),
    path('api/emitir-nfe/', views.api_emitir_nfe, name='api_emitir_nfe'),
    path('api/parse-certificado/', views.api_parse_certificado, name='api_parse_certificado'),

    path('nfe/novo/manual/', views.nfe_create_manual, name='nfe_create_manual'),
]
