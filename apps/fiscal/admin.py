from django.contrib import admin
from .models import CertificadoDigital, LoteNFe, NFe, NFeItem, NFePagamento, NFeEvento


class NFeItemInline(admin.TabularInline):
    model = NFeItem
    extra = 0
    readonly_fields = ['numero_item', 'codigo_produto', 'nome', 'ncm', 'cfop',
                       'quantidade', 'valor_unitario', 'valor_total']
    can_delete = False


class NFePagamentoInline(admin.TabularInline):
    model = NFePagamento
    extra = 0
    readonly_fields = ['forma_pagamento', 'valor']


class NFeEventoInline(admin.TabularInline):
    model = NFeEvento
    extra = 0
    readonly_fields = ['tipo', 'data_evento', 'protocolo', 'justificativa']


@admin.register(CertificadoDigital)
class CertificadoDigitalAdmin(admin.ModelAdmin):
    list_display = ['empresa', 'cnpj', 'tipo', 'validade_inicio', 'validade_fim', 'ativo']
    list_filter = ['tipo', 'ativo']
    search_fields = ['cnpj', 'empresa__nome_fantasia']


@admin.register(LoteNFe)
class LoteNFeAdmin(admin.ModelAdmin):
    list_display = ['numero_lote', 'empresa', 'status', 'data_criacao', 'protocolo']
    list_filter = ['status']
    search_fields = ['numero_lote', 'protocolo']


@admin.register(NFe)
class NFeAdmin(admin.ModelAdmin):
    list_display = ['numero', 'serie', 'destinatario', 'modelo', 'status',
                    'valor_total', 'data_emissao', 'protocolo']
    list_filter = ['status', 'modelo', 'tipo_emissao']
    search_fields = ['chave_acesso', 'numero', 'destinatario__nome', 'protocolo']
    date_hierarchy = 'data_emissao'
    inlines = [NFeItemInline, NFePagamentoInline, NFeEventoInline]
    readonly_fields = ['chave_acesso', 'protocolo', 'data_emissao', 'data_envio',
                       'data_autorizacao', 'xml_enviado', 'xml_retorno']

    fieldsets = (
        ('Identificação', {
            'fields': ('empresa', 'movimentacao', 'destinatario', 'modelo',
                       'serie', 'numero', 'chave_acesso', 'status')
        }),
        ('Configuração', {
            'fields': ('tipo_emissao', 'natureza_operacao', 'finalidade',
                       'consumo_final', 'presenca_comprador')
        }),
        ('Valores', {
            'fields': ('valor_total', 'valor_total_produtos', 'valor_frete',
                       'valor_seguro', 'valor_desconto', 'valor_outras_despesas',
                       'valor_base_calculo_icms', 'valor_icms',
                       'valor_base_calculo_icms_st', 'valor_icms_st',
                       'valor_ipi', 'valor_pis', 'valor_cofins')
        }),
        ('SEFAZ', {
            'fields': ('protocolo', 'mensagem_retorno', 'codigo_erro',
                       'data_envio', 'data_autorizacao', 'xml_enviado', 'xml_retorno')
        }),
        ('Cancelamento', {
            'fields': ('data_cancelamento', 'justificativa_cancelamento')
        }),
        ('Informações', {
            'fields': ('informacoes_adicionais',)
        }),
    )
