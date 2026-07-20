from django.db import models
from .pessoa import Pessoa
from .financeiro import PlanoContas, CentroCusto
from .reservados import NCM, Cidade
from .auxiliares import Marca, Divisao, Unidade
from .produto import LocalEstoque

class Empresa(models.Model):
    """
    Configurações e parâmetros da empresa licenciada.
    """
    # Relacionamento principal
    pessoa = models.OneToOneField(
        Pessoa,
        on_delete=models.PROTECT,
        primary_key=True,
        related_name='empresa_config',
        verbose_name='Pessoa/Empresa'
    )
    nome_fantasia = models.CharField(max_length=255, null=True, blank=True)
    telefone_principal = models.CharField(max_length=20, null=True, blank=True)
    nome_esquema = models.CharField(max_length=20, null=True, blank=True, help_text='Ex: marilia, bauru')
    
    # Imagem
    logo_fundo = models.ImageField(upload_to='empresa/logos/', null=True, blank=True)

    # Financeiro Padrão
    plano_contas_receita_venda = models.ForeignKey(
        PlanoContas, on_delete=models.PROTECT,
        related_name='empresas_receita_venda',
        verbose_name='Plano de Contas (Receita Venda)',
        null=True, blank=True
    )
    centro_custo_venda = models.ForeignKey(
        CentroCusto, on_delete=models.PROTECT,
        related_name='empresas_cc_venda',
        default=1, # No SQL era 127, mas depende do que existe no DB
        verbose_name='Centro de Custo Venda'
    )
    centro_custo_compra = models.ForeignKey(
        CentroCusto, on_delete=models.PROTECT,
        related_name='empresas_cc_compra',
        default=1,
        verbose_name='Centro de Custo Compra'
    )
    plano_contas_receita_compra = models.ForeignKey(
        PlanoContas, on_delete=models.PROTECT,
        related_name='empresas_receita_compra',
        default=1,
        verbose_name='Plano de Contas (Receita Compra)'
    )
    
    # Juros e Multas
    juros_mes = models.DecimalField(max_digits=14, decimal_places=4, default=0)
    multa_por_atraso = models.DecimalField(max_digits=14, decimal_places=4, default=0)
    
    # Vendas
    dias_vencimento_padrao_orcamento = models.IntegerField(default=0)
    valor_frete_padrao = models.DecimalField(max_digits=14, decimal_places=4, default=0)
    nao_alterar_valor_frete_padrao = models.BooleanField(default=False)
    
    # NFe / Fiscais
    ncm_padrao = models.ForeignKey(
        NCM, on_delete=models.PROTECT, null=True, blank=True,
        verbose_name='NCM Padrão'
    )
    numero_serie_certificado_nfe = models.CharField(max_length=255, null=True, blank=True)
    senha_certificado_digital = models.CharField(max_length=255, null=True, blank=True)
    caminho_arquivos_xml = models.CharField(max_length=255, null=True, blank=True)
    uf_web_service_nfe = models.CharField(max_length=2, default='SP')
    ambiente_destino = models.CharField(
        max_length=1, 
        choices=[('H', 'Homologação'), ('P', 'Produção')],
        default='H'
    )
    crt_nfe = models.SmallIntegerField(
        choices=[(1, 'Simples Nacional'), (2, 'Simples Nacional - Excesso'), (3, 'Regime Normal')],
        null=True, blank=True
    )
    regime_tributacao_federal = models.IntegerField(
        choices=[(0, 'Simples Nacional'), (1, 'Lucro Presumido'), (2, 'Lucro Real')],
        default=0
    )

    # Certificado Digital vinculado
    certificado_digital = models.ForeignKey(
        'fiscal.CertificadoDigital', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='empresa_vinculada',
        verbose_name='Certificado Digital Ativo'
    )

    # NFC-e (CSC)
    csc = models.CharField(
        max_length=36, blank=True,
        verbose_name='CSC (Código de Segurança do Contribuinte)',
        help_text='Código de Segurança do Contribuinte para emissão de NFC-e (fornecido pela SEFAZ)'
    )
    csc_id = models.CharField(
        max_length=6, blank=True,
        verbose_name='ID do CSC',
        help_text='Identificador do CSC para NFC-e'
    )

    # Série e numeração
    serie_nfe = models.IntegerField(default=1, verbose_name='Série NF-e')
    serie_nfce = models.IntegerField(default=1, verbose_name='Série NFC-e')
    ultimo_numero_nfe = models.IntegerField(default=0, verbose_name='Último Nº NF-e')
    ultimo_numero_nfce = models.IntegerField(default=0, verbose_name='Último Nº NFC-e')

    # CNAE
    cnae_fiscal = models.CharField(
        max_length=7, blank=True,
        verbose_name='CNAE Fiscal',
        help_text='Classificação Nacional de Atividades Econômicas (7 dígitos)'
    )

    # Cidade sede (para o emit da NF-e)
    cidade_sede = models.ForeignKey(
        Cidade, on_delete=models.PROTECT,
        null=True, blank=True,
        verbose_name='Município da Sede',
        help_text='Município da sede da empresa (para identificação do emitente na NF-e)'
    )
    
    # Configurações de PDV
    cliente_padrao = models.ForeignKey(
        Pessoa, on_delete=models.PROTECT,
        related_name='empresas_cliente_padrao',
        null=True, blank=True,
        verbose_name='Cliente Padrão (PDV)'
    )
    vendedor_padrao = models.ForeignKey(
        Pessoa, on_delete=models.PROTECT,
        related_name='empresas_vendedor_padrao',
        null=True, blank=True,
        verbose_name='Vendedor Padrão'
    )
    consumidor_final = models.ForeignKey(
        Pessoa, on_delete=models.PROTECT,
        related_name='empresas_consumidor_final',
        null=True, blank=True,
        verbose_name='Pessoa Consumidor Final'
    )

    # Responsável Técnico (NF-e)
    resp_tec_cnpj = models.CharField(
        max_length=18, blank=True,
        verbose_name='CNPJ do Responsável Técnico',
        help_text='CNPJ da empresa de software (desenvolvedora do sistema)'
    )
    resp_tec_contato = models.CharField(
        max_length=60, blank=True,
        verbose_name='Contato do Responsável Técnico',
        help_text='Nome da pessoa de contato'
    )
    resp_tec_email = models.EmailField(
        max_length=60, blank=True,
        verbose_name='Email do Responsável Técnico'
    )
    resp_tec_fone = models.CharField(
        max_length=20, blank=True,
        verbose_name='Telefone do Responsável Técnico'
    )
    resp_tec_csrt = models.CharField(
        max_length=32, blank=True,
        verbose_name='CSRT',
        help_text='Código de Segurança do Responsável Técnico (32 caracteres hexadecimais)'
    )
    resp_tec_csrt_id = models.CharField(
        max_length=6, blank=True,
        verbose_name='ID do CSRT',
        help_text='Identificador do CSRT'
    )
    
    # Estoque
    configuracao_estoque_negativo = models.SmallIntegerField(
        choices=[(1, 'Permitir'), (2, 'Bloquear'), (3, 'Controlar por Divisão')],
        default=1
    )
    local_padrao = models.ForeignKey(
        LocalEstoque, on_delete=models.PROTECT,
        null=True, blank=True,
        verbose_name='Local de Estoque Padrão'
    )
    
    # XML Importação Padrões
    marca_padrao_xml = models.ForeignKey(Marca, on_delete=models.PROTECT, null=True, blank=True)
    divisao_padrao_xml = models.ForeignKey(Divisao, on_delete=models.PROTECT, null=True, blank=True)
    unidade_venda_padrao_xml = models.ForeignKey(Unidade, on_delete=models.PROTECT, null=True, blank=True)
    local_padrao_xml = models.ForeignKey(LocalEstoque, on_delete=models.PROTECT, null=True, blank=True, related_name='empresas_local_xml')

    class Meta:
        db_table = 'empresas'
        verbose_name = 'Empresa'
        verbose_name_plural = 'Empresa'

    def __str__(self):
        return self.nome_fantasia or self.pessoa.nome
