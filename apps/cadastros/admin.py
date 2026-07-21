"""
Configuração do Django Admin para o módulo de Cadastros.
"""

from django.contrib import admin
from .models import (
    Marca, Divisao, Unidade, Banco, Cidade, NCM,
    AgenciaBancaria, ContaBancaria,
    Pessoa, PessoaFisica, Cliente, Fornecedor, Funcionario,
    EnderecoPessoa, EnderecoPrincipalPessoa,
    Produto, CodigoBarras, ImagemProduto, LocalEstoque,
    Empresa, TituloFinanceiro, Caixa, MovimentacaoCaixa,
    CentroCusto, PlanoContas,
)


# Empresa / Configurações
@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ['pessoa', 'nome_fantasia', 'telefone_principal', 'uf_web_service_nfe']
    search_fields = ['nome_fantasia', 'pessoa__nome']
    
    fieldsets = (
        ('Identificação', {
            'fields': ('pessoa', 'nome_fantasia', 'telefone_principal', 'nome_esquema', 'logo_fundo')
        }),
        ('Financeiro Padrão', {
            'fields': ('plano_contas_receita_venda', 'centro_custo_venda', 'centro_custo_compra', 'plano_contas_receita_compra')
        }),
        ('Juros e Multas', {
            'fields': ('juros_mes', 'multa_por_atraso')
        }),
        ('Vendas e Orçamentos', {
            'fields': ('dias_vencimento_padrao_orcamento', 'valor_frete_padrao', 'nao_alterar_valor_frete_padrao')
        }),
        ('Fiscal / NF-e', {
            'fields': ('ncm_padrao', 'cnae_fiscal', 'uf_web_service_nfe', 'ambiente_destino', 'crt_nfe', 'regime_tributacao_federal', 'serie_nfe', 'serie_nfce', 'caminho_arquivos_xml')
        }),
        ('Certificado Digital & CSC', {
            'fields': ('certificado_digital', 'csc', 'csc_id')
        }),
        ('Responsável Técnico NF-e', {
            'fields': ('resp_tec_cnpj', 'resp_tec_contato', 'resp_tec_email', 'resp_tec_fone', 'resp_tec_csrt', 'resp_tec_csrt_id')
        }),
        ('Sede', {
            'fields': ('cidade_sede',)
        }),
        ('Padrões PDV', {
            'fields': ('cliente_padrao', 'vendedor_padrao', 'consumidor_final')
        }),
        ('Estoque Padrões', {
            'fields': ('configuracao_estoque_negativo', 'local_padrao')
        }),
        ('Importação XML Padrões', {
            'fields': ('marca_padrao_xml', 'divisao_padrao_xml', 'unidade_venda_padrao_xml', 'local_padrao_xml')
        }),
    )


@admin.register(LocalEstoque)
class LocalEstoqueAdmin(admin.ModelAdmin):
    list_display = ['local', 'ativo']
    search_fields = ['local']
    ordering = ['local']


# Financeiro Novo
@admin.register(TituloFinanceiro)
class TituloFinanceiroAdmin(admin.ModelAdmin):
    list_display = ['numero_documento', 'pessoa', 'data_vencimento', 'valor_documento', 'valor_saldo', 'situacao', 'tipo']
    list_filter = ['tipo', 'situacao', 'data_vencimento']
    search_fields = ['numero_documento', 'pessoa__nome']
    date_hierarchy = 'data_vencimento'


class MovimentacaoCaixaInline(admin.TabularInline):
    model = MovimentacaoCaixa
    extra = 0
    readonly_fields = ['data_movimento']


@admin.register(Caixa)
class CaixaAdmin(admin.ModelAdmin):
    list_display = ['pk_chave', 'usuario', 'data_abertura', 'data_fechamento', 'valor_abertura', 'valor_fechamento', 'aberto']
    list_filter = ['aberto', 'usuario']
    inlines = [MovimentacaoCaixaInline]


@admin.register(MovimentacaoCaixa)
class MovimentacaoCaixaAdmin(admin.ModelAdmin):
    list_display = ['data_movimento', 'caixa', 'tipo_operacao', 'valor', 'tipo_pagamento', 'historico']
    list_filter = ['tipo_operacao', 'tipo_pagamento']
    search_fields = ['historico']


@admin.register(CentroCusto)
class CentroCustoAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nome', 'pai']
    search_fields = ['codigo', 'nome']
    ordering = ['codigo']


@admin.register(PlanoContas)
class PlanoContasAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nome', 'tipo', 'pai']
    list_filter = ['tipo']
    search_fields = ['codigo', 'nome']
    ordering = ['codigo']


# Auxiliares
@admin.register(Marca)
class MarcaAdmin(admin.ModelAdmin):
    list_display = ['nome']
    search_fields = ['nome']
    ordering = ['nome']


@admin.register(Divisao)
class DivisaoAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nome', 'pai', 'controla_lote']
    search_fields = ['nome', 'codigo']
    list_filter = ['controla_lote', 'permitir_estoque_negativo']
    ordering = ['nome']


@admin.register(Unidade)
class UnidadeAdmin(admin.ModelAdmin):
    list_display = ['nome', 'simbolo']
    search_fields = ['nome', 'simbolo']
    ordering = ['nome']


@admin.register(Banco)
class BancoAdmin(admin.ModelAdmin):
    list_display = ['codigo_banco', 'nome', 'taxa_cobranca_simples', 'banco_boleto']
    search_fields = ['codigo_banco', 'nome']
    ordering = ['codigo_banco']


@admin.register(AgenciaBancaria)
class AgenciaBancariaAdmin(admin.ModelAdmin):
    list_display = ['banco', 'agencia', 'digito', 'nome_gerente', 'telefone']
    search_fields = ['agencia', 'nome_gerente', 'banco__nome']
    list_filter = ['banco']
    ordering = ['banco', 'agencia']


@admin.register(ContaBancaria)
class ContaBancariaAdmin(admin.ModelAdmin):
    list_display = ['get_banco', 'get_agencia', 'conta', 'digito', 'tipo_conta_bancaria', 'nome_conta']
    list_filter = ['tipo_conta_bancaria', 'agencia__banco']
    search_fields = ['conta', 'nome_conta', 'agencia__banco__nome', 'agencia__agencia']
    ordering = ['agencia__banco__nome', 'agencia__agencia', 'conta']
    
    fieldsets = (
        ('Identificação', {
            'fields': ('agencia', 'conta', 'digito', 'tipo_conta_bancaria', 'nome_conta')
        }),
        ('Boleto', {
            'fields': ('carteira', 'convenio', 'ultimo_nosso_numero'),
            'classes': ('collapse',)
        }),
        ('Saldos', {
            'fields': ('saldo_inicial', 'saldo_atual'),
            'classes': ('collapse',)
        }),
    )
    
    def get_banco(self, obj):
        return obj.agencia.banco.nome if obj.agencia and obj.agencia.banco else '-'
    get_banco.short_description = 'Banco'
    get_banco.admin_order_field = 'agencia__banco__nome'
    
    def get_agencia(self, obj):
        return obj.agencia.agencia_formatada() if obj.agencia else '-'
    get_agencia.short_description = 'Agência'
    get_agencia.admin_order_field = 'agencia__agencia'


@admin.register(Cidade)
class CidadeAdmin(admin.ModelAdmin):
    list_display = ['codigo_ibge', 'nome', 'get_uf']
    list_filter = ['estado']
    search_fields = ['nome', 'codigo_ibge', 'estado__uf', 'estado__nome']
    ordering = ['estado__uf', 'nome']
    
    def get_uf(self, obj):
        return obj.estado.uf
    get_uf.short_description = 'UF'
    get_uf.admin_order_field = 'estado__uf'

@admin.register(NCM)
class NCMAdmin(admin.ModelAdmin):
    list_display = ['ncm', 'nome']
    search_fields = ['ncm', 'nome']
    ordering = ['ncm']


# Pessoas
@admin.register(Pessoa)
class PessoaAdmin(admin.ModelAdmin):
    list_display = ['chave', 'nome', 'cpf_cnpj', 'email', 'cliente', 'fornecedor', 'inativo']
    search_fields = ['nome', 'cpf_cnpj', 'email']
    list_filter = ['cliente', 'fornecedor', 'funcionario', 'usuario', 'inativo']
    ordering = ['nome']
    date_hierarchy = 'data_cadastro'


@admin.register(PessoaFisica)
class PessoaFisicaAdmin(admin.ModelAdmin):
    list_display = ['pessoa', 'data_nascimento', 'estado_civil']
    search_fields = ['pessoa__nome']
    ordering = ['pessoa__nome']


# Cliente, Fornecedor e Funcionario são aliases de Pessoa, não precisam registro separado


# Endereços
@admin.register(EnderecoPessoa)
class EnderecoPessoaAdmin(admin.ModelAdmin):
    list_display = ['pessoa', 'tipo_endereco', 'logradouro', 'numero', 'cidade']
    search_fields = ['pessoa__nome', 'logradouro', 'bairro']
    list_filter = ['tipo_endereco']
    ordering = ['pessoa__nome']


# Produtos
@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = ['pk_chave', 'nome', 'marca', 'divisao', 'preco_venda', 'inativo']
    search_fields = ['nome', 'referencia_fabrica']
    list_filter = ['marca', 'divisao', 'tipo_produto', 'inativo']
    ordering = ['nome']
    date_hierarchy = 'data_cadastramento'


@admin.register(CodigoBarras)
class CodigoBarrasAdmin(admin.ModelAdmin):
    list_display = ['codigo_barras', 'produto']
    search_fields = ['codigo_barras', 'produto__nome']
    ordering = ['produto__nome']


@admin.register(ImagemProduto)
class ImagemProdutoAdmin(admin.ModelAdmin):
    list_display = ['pk_chave', 'produto']
    search_fields = ['produto__nome']
    ordering = ['produto__nome']
