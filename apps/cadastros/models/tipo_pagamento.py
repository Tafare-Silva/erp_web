from django.db import models
from .financeiro import ContaBancaria


class TipoPagamento(models.Model):
    SITUACAO_CHOICES = [
        ('AV', 'À Vista'),
        ('AP', 'À Prazo'),
        ('AM', 'Ambos'),
    ]
    
    TIPO_TITULO_CHOICES = [
        ('DU', 'Duplicata'),
        ('BO', 'Boleto'),
        ('CH', 'Cheque'),
        ('CR', 'Crediário'),
        ('CA', 'Cartão'),
        ('DP', 'Depósito'),
        ('PI', 'PIX'),
        ('DI', 'Dinheiro'),
        ('OU', 'Outros'),
    ]
    
    TIPO_PARCELAMENTO_CHOICES = [
        ('NP', 'Não Parcelado'),
        ('PP', 'Parcelado pelo Cliente'),
        ('PL', 'Parcelado pela Loja'),
    ]
    
    MODALIDADE_CHOICES = [
        ('CR', 'Crédito'),
        ('DE', 'Débito'),
        ('AM', 'Ambos'),
    ]

    pk_tipo_pagamento = models.AutoField(primary_key=True)
    
    # Campos básicos
    tipo_pagamento = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='Tipo de Pagamento'
    )
    nome = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name='Nome',
        help_text='Nome alternativo/simplificado'
    )
    
    # Situações e tipos permitidos
    situacoes_permitidas = models.CharField(
        max_length=100,
        choices=SITUACAO_CHOICES,
        default='AV',
        verbose_name='Situações Permitidas'
    )
    tipos_titulos_permitidos = models.CharField(
        max_length=2,
        choices=TIPO_TITULO_CHOICES,
        default='DU',
        verbose_name='Tipos de Títulos Permitidos'
    )
    tipos_parcelamentos_permitidos = models.CharField(
        max_length=2,
        choices=TIPO_PARCELAMENTO_CHOICES,
        default='NP',
        verbose_name='Tipos de Parcelamentos Permitidos'
    )
    
    # Configurações fiscais
    forma_pagamento_nfe = models.IntegerField(
        default=1,
        verbose_name='Forma Pagamento NF-e',
        help_text='Código conforme manual da NF-e: 01=Dinheiro, 02=Cheque, 03=Cartão Crédito, etc.'
    )
    indice_forma_pgto_ecf = models.CharField(
        max_length=2,
        null=True,
        blank=True,
        verbose_name='Índice Forma Pgto ECF/SAT'
    )
    
    # Configurações de controle
    controle_cheque = models.BooleanField(
        default=False,
        verbose_name='Controle de Cheque'
    )
    emite_boleto = models.BooleanField(
        default=False,
        verbose_name='Emite Boleto'
    )
    chamar_tef = models.BooleanField(
        default=False,
        verbose_name='Chamar TEF'
    )
    entrar_caixa_usuario = models.BooleanField(
        default=True,
        verbose_name='Entrar no Caixa do Usuário',
        help_text='Se deve registrar no fechamento de caixa'
    )
    exigir_conta_bancaria = models.BooleanField(
        default=False,
        verbose_name='Exigir Conta Bancária',
        help_text='Obriga informar conta bancária ao usar este tipo de pagamento'
    )
    
    # Configurações de cartão
    modalidade = models.CharField(
        max_length=2,
        choices=MODALIDADE_CHOICES,
        null=True,
        blank=True,
        verbose_name='Modalidade',
        help_text='Modalidade do cartão (Crédito/Débito)'
    )
    bandeira_cartao = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name='Bandeira do Cartão'
    )
    taxa_administracao = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name='Taxa de Administração (%)',
        help_text='Taxa percentual cobrada (ex: taxa do cartão)'
    )
    
    # Configurações de parcelamento
    prazo_padrao = models.IntegerField(
        default=0,
        verbose_name='Prazo Padrão (dias)',
        help_text='Prazo padrão em dias para vencimento'
    )
    qtd_parcelas_padrao = models.IntegerField(
        default=1,
        verbose_name='Quantidade de Parcelas Padrão',
        help_text='Número padrão de parcelas'
    )
    centavos_por_ultimo_nas_parcelas = models.BooleanField(
        default=True,
        verbose_name='Centavos por Último nas Parcelas',
        help_text='Ajusta centavos na última parcela'
    )
    
    # Conta bancária padrão
    conta_bancaria_padrao = models.ForeignKey(
        ContaBancaria,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tipos_pagamento',
        verbose_name='Conta Bancária Padrão'
    )
    
    # Status
    ativo = models.BooleanField(
        default=True,
        verbose_name='Ativo'
    )

    class Meta:
        db_table = 'tipos_pagamento'
        verbose_name = 'Tipo de Pagamento'
        verbose_name_plural = 'Tipos de Pagamento'
        ordering = ['tipo_pagamento']

    def __str__(self):
        return self.tipo_pagamento