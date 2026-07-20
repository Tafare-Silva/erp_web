from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal
from .pessoa import Pessoa
from .financeiro import PlanoContas, CentroCusto, ContaBancaria
from .tipo_pagamento import TipoPagamento

class TituloFinanceiro(models.Model):
    """
    Modelo base para Contas a Pagar e Contas a Receber.
    """
    TIPO_CHOICES = [
        ('P', 'A Pagar'),
        ('R', 'A Receber'),
    ]
    
    SITUACAO_CHOICES = [
        ('ABERTO', 'Aberto'),
        ('PAGO', 'Pago/Liquidado'),
        ('CANCELADO', 'Cancelado'),
        ('ATRASADO', 'Atrasado'),
        ('PARCIAL', 'Pago Parcial'),
    ]

    pk_chave = models.AutoField(primary_key=True)
    tipo = models.CharField(max_length=1, choices=TIPO_CHOICES, verbose_name='Tipo')
    pessoa = models.ForeignKey(
        Pessoa, on_delete=models.PROTECT, 
        related_name='titulos_financeiros',
        verbose_name='Pessoa (Cliente/Fornecedor)'
    )
    
    data_operacao = models.DateField(auto_now_add=True, verbose_name='Data de Operação')
    data_vencimento = models.DateField(verbose_name='Data de Vencimento')
    data_pagamento = models.DateField(null=True, blank=True, verbose_name='Data de Pagamento')
    
    numero_documento = models.CharField(max_length=50, verbose_name='Número do Documento')
    parcela = models.IntegerField(default=1, verbose_name='Parcela')
    total_parcelas = models.IntegerField(default=1, verbose_name='Total de Parcelas')
    
    valor_documento = models.DecimalField(max_digits=14, decimal_places=2, verbose_name='Valor do Documento')
    valor_pago = models.DecimalField(max_digits=14, decimal_places=2, default=0, verbose_name='Valor Pago')
    valor_saldo = models.DecimalField(max_digits=14, decimal_places=2, verbose_name='Saldo')
    
    situacao = models.CharField(max_length=20, choices=SITUACAO_CHOICES, default='ABERTO', verbose_name='Situação')
    
    tipo_pagamento = models.ForeignKey(
        TipoPagamento, on_delete=models.PROTECT, 
        null=True, blank=True,
        verbose_name='Tipo de Pagamento'
    )
    plano_contas = models.ForeignKey(
        PlanoContas, on_delete=models.PROTECT,
        verbose_name='Plano de Contas'
    )
    centro_custo = models.ForeignKey(
        CentroCusto, on_delete=models.PROTECT,
        verbose_name='Centro de Custo'
    )
    conta_bancaria = models.ForeignKey(
        ContaBancaria, on_delete=models.PROTECT,
        null=True, blank=True,
        verbose_name='Conta Bancária'
    )
    
    movimentacao_estoque = models.ForeignKey(
        'cadastros.MovimentacaoEstoque', 
        on_delete=models.SET_NULL, 
        null=True, blank=True,
        related_name='titulos_financeiros',
        verbose_name='Movimentação de Origem'
    )
    
    historico = models.TextField(null=True, blank=True, verbose_name='Histórico/Observação')
    
    usuario_criacao = models.ForeignKey(
        User, on_delete=models.PROTECT,
        null=True, blank=True,
        verbose_name='Usuário'
    )

    class Meta:
        db_table = 'titulos_financeiros'
        verbose_name = 'Título Financeiro'
        verbose_name_plural = 'Títulos Financeiros'
        ordering = ['data_vencimento', 'pk_chave']

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.numero_documento} ({self.parcela}/{self.total_parcelas}) - {self.pessoa.nome}"

    def save(self, *args, **kwargs):
        if not self.valor_saldo:
            self.valor_saldo = self.valor_documento - self.valor_pago
        super().save(*args, **kwargs)


class Caixa(models.Model):
    """
    Controle de abertura e fechamento de caixa.
    """
    pk_chave = models.AutoField(primary_key=True)
    data_abertura = models.DateTimeField(auto_now_add=True, verbose_name='Data de Abertura')
    data_fechamento = models.DateTimeField(null=True, blank=True, verbose_name='Data de Fechamento')
    
    valor_abertura = models.DecimalField(max_digits=14, decimal_places=2, default=0, verbose_name='Valor de Abertura')
    valor_fechamento = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True, verbose_name='Valor de Fechamento')
    
    usuario = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name='Usuário')
    aberto = models.BooleanField(default=True, verbose_name='Caixa Aberto')

    class Meta:
        db_table = 'caixas'
        verbose_name = 'Caixa'
        verbose_name_plural = 'Caixas'
        ordering = ['-data_abertura']

    def __str__(self):
        status = "Aberto" if self.aberto else "Fechado"
        return f"Caixa #{self.pk_chave} - {self.usuario.username} ({status})"


class MovimentacaoCaixa(models.Model):
    """
    Registros individuais de entradas e saídas no caixa.
    """
    TIPO_OPERACAO = [
        ('E', 'Entrada'),
        ('S', 'Saída'),
    ]

    pk_chave = models.AutoField(primary_key=True)
    caixa = models.ForeignKey(Caixa, on_delete=models.CASCADE, related_name='movimentacoes', verbose_name='Caixa')
    data_movimento = models.DateTimeField(auto_now_add=True, verbose_name='Data')
    
    tipo_operacao = models.CharField(max_length=1, choices=TIPO_OPERACAO, verbose_name='Tipo Operação')
    valor = models.DecimalField(max_digits=14, decimal_places=2, verbose_name='Valor')
    
    tipo_pagamento = models.ForeignKey(TipoPagamento, on_delete=models.PROTECT, verbose_name='Tipo de Pagamento')
    titulo_financeiro = models.ForeignKey(
        TituloFinanceiro, on_delete=models.SET_NULL, 
        null=True, blank=True,
        verbose_name='Título Relacionado'
    )
    
    historico = models.CharField(max_length=255, verbose_name='Histórico')

    class Meta:
        db_table = 'movimentacoes_caixa'
        verbose_name = 'Movimentação de Caixa'
        verbose_name_plural = 'Movimentações de Caixa'
        ordering = ['data_movimento']
