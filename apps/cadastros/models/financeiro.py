from django.db import models
from .auxiliares import Banco
from .pessoa import Pessoa


class AgenciaBancaria(models.Model):
    id = models.AutoField(primary_key=True)
    banco = models.ForeignKey(
        Banco,
        on_delete=models.PROTECT,
        related_name='agencias',
        verbose_name='Banco'
    )
    agencia = models.IntegerField(verbose_name='Agência')
    digito = models.CharField(max_length=1, null=True, blank=True, verbose_name='Dígito')
    nome_agencia = models.CharField(max_length=100, null=True, blank=True, verbose_name='Nome da Agência')
    endereco = models.CharField(max_length=255, null=True, blank=True, verbose_name='Endereço')
    telefone = models.CharField(max_length=20, null=True, blank=True, verbose_name='Telefone')
    nome_gerente = models.CharField(max_length=100, null=True, blank=True, verbose_name='Nome do Gerente')
    
    multa_padrao = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name='Multa Padrão (%)',
        help_text='Percentual de multa para atraso'
    )
    juros_padrao = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name='Juros Padrão (% ao mês)',
        help_text='Percentual de juros ao mês'
    )

    class Meta:
        db_table = 'agencias_bancarias'
        verbose_name = 'Agência Bancária'
        verbose_name_plural = 'Agências Bancárias'
        unique_together = [['banco', 'agencia']]
        ordering = ['banco__nome', 'agencia']

    def __str__(self):
        return f"{self.banco.nome} - Ag {self.agencia}-{self.digito or ''}"

    def agencia_formatada(self):
        if self.digito:
            return f"{self.agencia}-{self.digito}"
        return str(self.agencia)


class ContaBancaria(models.Model):
    TIPO_CONTA_CHOICES = [
        ('CC', 'Conta Corrente'),
        ('CP', 'Conta Poupança'),
        ('CI', 'Conta Investimento'),
        ('CS', 'Conta Salário'),
    ]

    id = models.AutoField(primary_key=True)
    agencia = models.ForeignKey(
        AgenciaBancaria,
        on_delete=models.PROTECT,
        related_name='contas',
        verbose_name='Agência'
    )
    conta = models.IntegerField(verbose_name='Conta')
    digito = models.CharField(max_length=2, null=True, blank=True, verbose_name='Dígito')
    tipo_conta_bancaria = models.CharField(
        max_length=2,
        choices=TIPO_CONTA_CHOICES,
        default='CC',
        verbose_name='Tipo de Conta'
    )
    nome_conta = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name='Nome/Descrição da Conta'
    )

    inativo = models.BooleanField(
        default=False,
        verbose_name='Inativo',
        help_text='Conta desativada'
    )
    descricao_propria = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name='Descrição Própria',
        help_text='Descrição personalizada da conta'
    )
    
    carteira = models.CharField(
        max_length=3,
        null=True,
        blank=True,
        verbose_name='Carteira (Boleto)',
        help_text='Código da carteira para emissão de boletos'
    )
    convenio = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name='Convênio',
        help_text='Número do convênio bancário'
    )
    ultimo_nosso_numero = models.BigIntegerField(
        default=0,
        verbose_name='Último Nosso Número',
        help_text='Controle sequencial para nosso número do boleto'
    )
    
    saldo_inicial = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        verbose_name='Saldo Inicial'
    )
    saldo_atual = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        verbose_name='Saldo Atual'
    )

    class Meta:
        db_table = 'contas_bancarias'
        verbose_name = 'Conta Bancária'
        verbose_name_plural = 'Contas Bancárias'
        unique_together = [['agencia', 'conta']]
        ordering = ['agencia__banco__nome', 'agencia__agencia', 'conta']

    def __str__(self):
        return f"{self.agencia.banco.nome} - Ag {self.agencia.agencia} - Cc {self.conta_formatada()}"

    def conta_formatada(self):
        if self.digito:
            return f"{self.conta}-{self.digito}"
        return str(self.conta)

    def get_banco(self):
        return self.agencia.banco

    def get_proximo_nosso_numero(self):
        self.ultimo_nosso_numero += 1
        self.save(update_fields=['ultimo_nosso_numero'])
        return self.ultimo_nosso_numero


class CentroCusto(models.Model):
    chave = models.AutoField(
        primary_key=True,
        verbose_name='Chave',
        help_text='Chave primária'
    )
    codigo = models.CharField(
        max_length=20,
        verbose_name='Código',
        help_text='Código do centro de custos. Ex: 1.1, 2.5.6'
    )
    nome = models.CharField(
        max_length=255,
        unique=True,
        verbose_name='Nome',
        help_text='Descrição do centro de custos'
    )
    pai = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name='Centro de Custo Pai',
        help_text='Centro de custo superior na hierarquia'
    )

    class Meta:
        db_table = 'centro_custos'
        verbose_name = 'Centro de Custo'
        verbose_name_plural = 'Centros de Custos'
        ordering = ['codigo']

    def __str__(self):
        return f"{self.codigo} - {self.nome}"

    def get_nivel(self):
        nivel = 0
        pai_atual = self.pai
        while pai_atual:
            nivel += 1
            pai_atual = pai_atual.pai
        return nivel

    def get_caminho_completo(self):
        caminho = [self.nome]
        pai_atual = self.pai
        while pai_atual:
            caminho.insert(0, pai_atual.nome)
            pai_atual = pai_atual.pai
        return ' > '.join(caminho)


class PlanoContas(models.Model):
    TIPO_CHOICES = [
        ('R', 'Receita'),
        ('D', 'Despesa'),
        ('A', 'Ambas (Receita e Despesa)'),
    ]

    chave = models.AutoField(
        primary_key=True,
        verbose_name='Chave',
        help_text='Chave primária'
    )
    codigo = models.CharField(
        max_length=20,
        verbose_name='Código',
        help_text='Código da conta. Ex: 1.1, 2.5.6'
    )
    nome = models.CharField(
        max_length=255,
        verbose_name='Nome',
        help_text='Descrição da conta no plano de contas'
    )
    pai = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name='Conta Pai',
        help_text='Conta superior na hierarquia'
    )
    tipo_conta = models.CharField(
        max_length=1,
        choices=TIPO_CHOICES,
        verbose_name='Tipo de Conta',
        help_text='Receita, Despesa ou Ambas'
    )
    observacoes = models.TextField(
        blank=True,
        default='',
        verbose_name='Observações',
        help_text='Observações ou explicações relacionadas à conta'
    )
    fixo = models.BooleanField(
        default=False,
        verbose_name='Despesa/Receita Fixa',
        help_text='Indica se é uma despesa ou receita fixa (ex: aluguel, salário)'
    )
    
    pessoa_padrao = models.ForeignKey(
        Pessoa,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='planos_contas',
        verbose_name='Pessoa Padrão',
        help_text='Favorecido/cliente padrão'
    )
    documento = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name='Documento Padrão',
        help_text='Número do documento padrão'
    )
    dia_do_lancamento = models.SmallIntegerField(
        null=True,
        blank=True,
        verbose_name='Dia do Lançamento',
        help_text='Dia do mês para lançamento automático (1-31)'
    )
    tipo_pagamento_nome = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name='Tipo de Pagamento Padrão',
        help_text='Tipo de pagamento padrão do título'
    )
    obs_padrao = models.TextField(
        blank=True,
        null=True,
        verbose_name='Observação Padrão',
        help_text='Observação padrão para o título'
    )
    valor_padrao = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        verbose_name='Valor Padrão',
        help_text='Valor padrão para o título'
    )
    situacao_titulo_padrao = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name='Situação Padrão',
        help_text='Situação cadastral padrão do título'
    )
    apenas_previsao = models.BooleanField(
        default=False,
        verbose_name='Apenas Previsão',
        help_text='Não gera lançamento, apenas previsão no fluxo de caixa'
    )
    
    conta_bancaria_padrao = models.ForeignKey(
        ContaBancaria,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='planos_contas',
        verbose_name='Conta Bancária Padrão'
    )
    
    centro_custo_padrao = models.ForeignKey(
        CentroCusto,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='planos_contas',
        verbose_name='Centro de Custo Padrão',
        help_text='Centro de custos padrão para esta conta'
    )

    class Meta:
        db_table = 'plano_contas'
        verbose_name = 'Plano de Contas'
        verbose_name_plural = 'Plano de Contas'
        ordering = ['codigo']

    def __str__(self):
        return f"{self.codigo} - {self.nome}"

    def get_tipo_display_icon(self):
        icons = {
            'R': 'fa-arrow-up text-green-600',
            'D': 'fa-arrow-down text-red-600',
            'A': 'fa-exchange-alt text-blue-600',
        }
        return icons.get(self.tipo_conta, '')

    def get_nivel(self):
        nivel = 0
        pai_atual = self.pai
        while pai_atual:
            nivel += 1
            pai_atual = pai_atual.pai
        return nivel

    def get_caminho_completo(self):
        caminho = [self.nome]
        pai_atual = self.pai
        while pai_atual:
            caminho.insert(0, pai_atual.nome)
            pai_atual = pai_atual.pai
        return ' > '.join(caminho)