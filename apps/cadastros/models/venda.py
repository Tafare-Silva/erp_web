from django.db import models
from django.core.exceptions import ValidationError
from .pessoa import Pessoa
from .produto import Produto, LocalEstoque
from decimal import Decimal

class TipoMovimentacao(models.Model):
    """
    Tipos de movimentação de estoque.
    Ex: Venda, Compra, Devolução, Transferência, etc.
    """
    OPERACAO_CHOICES = [
        ('E', 'Entrada'),
        ('S', 'Saída'),
        ('T', 'Transferência'),
    ]

    tipo_movimentacao = models.CharField(
        max_length=100,
        primary_key=True,
        verbose_name='Tipo de Movimentação'
    )
    nome = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name='Nome',
        help_text='Nome alternativo/simplificado'
    )
    operacao = models.CharField(
        max_length=1,
        choices=OPERACAO_CHOICES,
        default='S',
        verbose_name='Operação',
        help_text='E=Entrada, S=Saída, T=Transferência'
    )
    movimenta_estoque = models.BooleanField(
        default=True,
        verbose_name='Movimenta Estoque',
        help_text='Se movimenta fisicamente o estoque'
    )
    movimenta_financeiro = models.BooleanField(
        default=True,
        verbose_name='Movimenta Financeiro',
        help_text='Se gera lançamento financeiro'
    )
    gera_custo = models.BooleanField(
        default=False,
        verbose_name='Gera Custo',
        help_text='Se atualiza o custo do produto'
    )
    ativo = models.BooleanField(
        default=True,
        verbose_name='Ativo'
    )

    class Meta:
        db_table = 'tipos_movimentacao'
        verbose_name = 'Tipo de Movimentação'
        verbose_name_plural = 'Tipos de Movimentação'
        ordering = ['tipo_movimentacao']

    def __str__(self):
        if self.nome:
            return self.nome
        return self.tipo_movimentacao

class MovimentacaoEstoque(models.Model):
    TIPO_MOVIMENTO_CHOICES = [
        ('VE', 'Venda'),
        ('CO', 'Compra'),
        ('DV', 'Devolução de Venda'),
        ('DC', 'Devolução de Compra'),
        ('TR', 'Transferência'),
        ('AJ', 'Ajuste'),
        ('PV', 'Pré-Venda'),
    ]

    pk_chave = models.AutoField(primary_key=True)
    data = models.DateField(auto_now_add=True, verbose_name='Data')
    pessoa = models.ForeignKey(
        Pessoa,
        on_delete=models.PROTECT,
        related_name='movimentacoes',
        verbose_name='Pessoa (Cliente/Fornecedor)'
    )
    tipo_movimento = models.CharField(
        max_length=2,
        choices=TIPO_MOVIMENTO_CHOICES,
        verbose_name='Tipo de Movimento'
    )
    observacao = models.TextField(null=True, blank=True, verbose_name='Observação')
    
    vr_total_bruto = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        verbose_name='Valor Total Bruto'
    )
    vr_desconto = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        verbose_name='Valor Desconto'
    )
    vr_acrescimo = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        verbose_name='Valor Acréscimo'
    )
    vr_total_liquido = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        verbose_name='Valor Total Líquido'
    )
    
    usuario_criacao = models.ForeignKey(
        'auth.User',
        on_delete=models.PROTECT,
        related_name='movimentacoes_criadas',
        verbose_name='Usuário que Criou',
        null=True,
        blank=True
    )
    vendedor = models.ForeignKey(
        Pessoa,
        on_delete=models.PROTECT,
        related_name='vendas_realizadas',
        verbose_name='Vendedor',
        null=True,
        blank=True
    )
    emitir_nfe = models.BooleanField(default=False, verbose_name='Emitir NF-e/NFC-e')
    tipo_documento_fiscal = models.CharField(
        max_length=2, blank=True, default='',
        choices=[('', 'Nenhum'), ('55', 'NF-e'), ('65', 'NFC-e')],
        verbose_name='Tipo Documento Fiscal'
    )
    chave_nfe = models.CharField(max_length=44, blank=True, null=True, verbose_name='Chave da NF-e')
    nro_documento = models.CharField(max_length=50, blank=True, null=True, verbose_name='Número do Documento')
    serie = models.CharField(max_length=10, blank=True, null=True, verbose_name='Série')
    cfop = models.CharField(max_length=5, blank=True, null=True, verbose_name='CFOP')
    local = models.ForeignKey(
        'cadastros.LocalEstoque', # Ajuste o caminho se necessário
        on_delete=models.PROTECT, 
        blank=True, 
        null=True, 
        verbose_name='Local de Estoque'
    )
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name='Data de Criação')
    data_alteracao = models.DateTimeField(auto_now=True, verbose_name='Data de Alteração')

    class Meta:
        db_table = 'movimentacoes_estoque'
        verbose_name = 'Movimentação de Estoque'
        verbose_name_plural = 'Movimentações de Estoque'
        ordering = ['-data', '-pk_chave']

    def __str__(self):
        return f"{self.get_tipo_movimento_display()} #{self.pk_chave} - {self.pessoa.nome}"

    def recalcular_totais(self):
        itens = self.itens.all()
        self.vr_total_bruto = sum(item.vr_total_bruto for item in itens)
        self.vr_total_liquido = self.vr_total_bruto - self.vr_desconto + self.vr_acrescimo
        self.save(update_fields=['vr_total_bruto', 'vr_total_liquido'])

    def calcular_total(self):
        """Retorna o valor total líquido da movimentação."""
        return self.vr_total_liquido


class ItemMovimentacaoEstoque(models.Model):
    id = models.AutoField(primary_key=True)
    movimentacao = models.ForeignKey(
        MovimentacaoEstoque,
        on_delete=models.CASCADE,
        related_name='itens',
        verbose_name='Movimentação'
    )
    produto = models.ForeignKey(
        Produto,
        on_delete=models.PROTECT,
        related_name='itens_movimentacao',
        verbose_name='Produto'
    )
    local = models.ForeignKey(
        LocalEstoque,
        on_delete=models.PROTECT,
        related_name='itens_movimentacao',
        verbose_name='Local Estoque'
    )
    
    quantidade = models.DecimalField(
        max_digits=14,
        decimal_places=6,
        verbose_name='Quantidade'
    )
    quantidade_fiscal = models.DecimalField(
        max_digits=14,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name='Quantidade Fiscal',
        help_text='Quantidade convertida para unidade fiscal (ex: caixa → unidades)'
    )
    
    vr_unitario_bruto = models.DecimalField(
        max_digits=14,
        decimal_places=6,
        verbose_name='Valor Unitário Bruto'
    )
    vr_unitario_liquido = models.DecimalField(
        max_digits=14,
        decimal_places=6,
        verbose_name='Valor Unitário Líquido'
    )
    vr_unitario_liquido_fiscal = models.DecimalField(
        max_digits=14,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name='Valor Unitário Líquido Fiscal'
    )
    
    vr_desconto_total = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        verbose_name='Valor Desconto Total'
    )
    vr_acrescimo_total = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        verbose_name='Valor Acréscimo Total'
    )
    vr_total_bruto = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        verbose_name='Valor Total Bruto'
    )
    vr_total_liquido = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        verbose_name='Valor Total Líquido'
    )
    
    vr_comissao = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        verbose_name='Valor Comissão'
    )
    
    observacao = models.TextField(null=True, blank=True, verbose_name='Observação')

    class Meta:
        db_table = 'itens_movimentacao_estoque'
        verbose_name = 'Item de Movimentação'
        verbose_name_plural = 'Itens de Movimentação'
        ordering = ['movimentacao', 'id']

    def __str__(self):
        return f"{self.produto.nome} - Qtd: {self.quantidade}"

    def calcular_total(self):
        """Retorna o valor total líquido do item."""
        return self.vr_total_liquido

    def save(self, *args, **kwargs):
        self.vr_total_bruto = self.quantidade * self.vr_unitario_bruto
        self.vr_total_liquido = self.vr_total_bruto - self.vr_desconto_total + self.vr_acrescimo_total
        self.vr_unitario_liquido = self.vr_total_liquido / self.quantidade if self.quantidade else Decimal('0')
        super().save(*args, **kwargs)


class PreVenda(models.Model):
    CONDICAO_PAGAMENTO_CHOICES = [
        ('AV', 'À Vista'),
        ('AP', 'À Prazo'),
    ]

    pk_chave = models.AutoField(primary_key=True)
    movimentacao = models.OneToOneField(
        MovimentacaoEstoque,
        on_delete=models.CASCADE,
        related_name='pre_venda',
        verbose_name='Movimentação'
    )
    vendedor = models.ForeignKey(
        Pessoa,
        on_delete=models.PROTECT,
        limit_choices_to={'vendedor': True},
        related_name='pre_vendas',
        verbose_name='Vendedor'
    )
    efetivada = models.BooleanField(default=False, verbose_name='Efetivada')
    condicao_pagamento = models.CharField(
        max_length=2,
        choices=CONDICAO_PAGAMENTO_CHOICES,
        default='AV',
        verbose_name='Condição de Pagamento'
    )
    data_entrega = models.DateField(null=True, blank=True, verbose_name='Data de Entrega')
    endereco_entrega = models.TextField(null=True, blank=True, verbose_name='Endereço de Entrega')

    class Meta:
        db_table = 'pre_vendas'
        verbose_name = 'Pré-Venda'
        verbose_name_plural = 'Pré-Vendas'
        ordering = ['-pk_chave']

    def __str__(self):
        return f"Pré-Venda #{self.pk_chave} - {self.movimentacao.pessoa.nome}"

    def efetivar(self):
        if self.efetivada:
            raise ValidationError('Esta pré-venda já foi efetivada.')
        self.efetivada = True
        self.movimentacao.tipo_movimento = 'VE'
        self.movimentacao.save(update_fields=['tipo_movimento'])
        self.save(update_fields=['efetivada'])


class ItemPreVenda(models.Model):
    id = models.AutoField(primary_key=True)
    pre_venda = models.ForeignKey(
        PreVenda,
        on_delete=models.CASCADE,
        related_name='itens',
        verbose_name='Pré-Venda'
    )
    item_movimentacao = models.OneToOneField(
        ItemMovimentacaoEstoque,
        on_delete=models.CASCADE,
        related_name='item_pre_venda',
        verbose_name='Item Movimentação'
    )
    vendedor = models.ForeignKey(
        Pessoa,
        on_delete=models.PROTECT,
        limit_choices_to={'vendedor': True},
        related_name='itens_pre_venda',
        verbose_name='Vendedor'
    )
    quantidade_devolvida = models.DecimalField(
        max_digits=14,
        decimal_places=6,
        default=0,
        verbose_name='Quantidade Devolvida'
    )

    class Meta:
        db_table = 'itens_pre_venda'
        verbose_name = 'Item de Pré-Venda'
        verbose_name_plural = 'Itens de Pré-Venda'
        ordering = ['pre_venda', 'id']

    def __str__(self):
        return f"{self.item_movimentacao.produto.nome} - Pré-Venda #{self.pre_venda.pk_chave}"