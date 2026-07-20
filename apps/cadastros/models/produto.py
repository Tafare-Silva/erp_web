from django.db import models
from .auxiliares import Marca, Divisao, Unidade
from .reservados import NCM, DivisaoImpostosSaida
from .pessoa import Pessoa


class LocalEstoque(models.Model):
    local = models.CharField(
        max_length=255,
        primary_key=True,
        verbose_name='Local de Estoque',
        help_text='Nome do local de estoque (ex: Loja Principal, Depósito)'
    )
    descricao = models.TextField(
        null=True,
        blank=True,
        verbose_name='Descrição'
    )
    ativo = models.BooleanField(  
        default=True,
        verbose_name='Ativo'
    )

    class Meta:
        db_table = 'local_estoque'
        verbose_name = 'Local de Estoque'
        verbose_name_plural = 'Locais de Estoque'
        ordering = ['local']

    def __str__(self):
        return self.local


class Produto(models.Model):
    TIPO_CHOICES = [
        ('PRODUTO ACABADO', 'Produto Acabado'),
        ('MATERIA PRIMA', 'Matéria Prima'),
        ('PRODUTO INTERMEDIARIO', 'Produto Intermediário'),
        ('USO E CONSUMO', 'Uso e Consumo'),
        ('SERVICO', 'Serviço'),
    ]

    ORIGEM_CHOICES = [
        ('0', '0 - Nacional'),
        ('1', '1 - Estrangeira - Importação direta'),
        ('2', '2 - Estrangeira - Adquirida no mercado interno'),
        ('3', '3 - Nacional - Conteúdo de Importação > 40%'),
        ('4', '4 - Nacional - Processos Produtivos Básicos'),
        ('5', '5 - Nacional - Conteúdo de Importação ≤ 40%'),
        ('6', '6 - Estrangeira - Importação direta, sem similar nacional'),
        ('7', '7 - Estrangeira - Merc. interno, sem similar nacional'),
        ('8', '8 - Nacional - Conteúdo de Importação > 70%'),
    ]

    pk_chave = models.AutoField(primary_key=True, verbose_name='Código')
    nome = models.CharField(max_length=255, verbose_name='Nome do Produto')
    
    marca = models.ForeignKey(
        Marca,
        on_delete=models.PROTECT,
        to_field='nome',
        related_name='produtos',
        verbose_name='Marca'
    )
    divisao = models.ForeignKey(
        Divisao,
        on_delete=models.PROTECT,
        to_field='nome',
        related_name='produtos',
        verbose_name='Divisão'
    )
    ncm = models.ForeignKey(
        NCM,
        on_delete=models.PROTECT,
        to_field='ncm',
        related_name='produtos',
        verbose_name='NCM'
    )
    unidade_venda = models.ForeignKey(
        Unidade,
        on_delete=models.PROTECT,
        to_field='nome',
        related_name='produtos',
        verbose_name='Unidade Venda'
    )
    
    preco_venda = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        default=0,
        verbose_name='Preço Venda'
    )
    custo_referencia = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        default=0,
        verbose_name='Custo Referência'
    )
    pode_alterar_preco_venda = models.BooleanField(
        default=False,
        verbose_name='Pode Alterar Preço'
    )
    
    inativo = models.BooleanField(default=False, verbose_name='Inativo')
    data_cadastramento = models.DateField(auto_now_add=True, verbose_name='Data Cadastro')
    tipo_produto = models.CharField(
        max_length=21,
        choices=TIPO_CHOICES,
        default='PRODUTO ACABADO',
        verbose_name='Tipo de Produto'
    )
    
    referencia_fabrica = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name='Referência Fábrica'
    )
    
    divisao_impostos_saida = models.ForeignKey(
        DivisaoImpostosSaida,
        on_delete=models.SET_NULL,
        to_field='divisao',
        related_name='produtos',
        blank=True,
        null=True,
        verbose_name='Divisão Impostos Saída'
    )
    cest = models.CharField(max_length=7, default='0000000', verbose_name='CEST')
    
    estoque_minimo = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        default=0,
        verbose_name='Estoque Mínimo'
    )
    permitir_estoque_negativo = models.BooleanField(
        default=False,
        verbose_name='Permitir Estoque Negativo'
    )
    local_padrao = models.ForeignKey(
        LocalEstoque,
        on_delete=models.SET_NULL,
        to_field='local',
        related_name='produtos',
        blank=True,
        null=True,
        verbose_name='Local Estoque Padrão'
    )
    
    fornecedor_principal = models.ForeignKey(
        Pessoa,
        on_delete=models.SET_NULL,
        limit_choices_to={'fornecedor': True},
        related_name='produtos_fornecidos',
        blank=True,
        null=True,
        verbose_name='Fornecedor Principal'
    )
    
    imagem_principal = models.ForeignKey(
        'ImagemProduto',
        on_delete=models.SET_NULL,
        related_name='+',
        blank=True,
        null=True,
        verbose_name='Imagem Principal'
    )
    
    aplicacao = models.TextField(blank=True, null=True, verbose_name='Aplicação')
    tamanho = models.CharField(max_length=50, blank=True, null=True, verbose_name='Tamanho')
    cor = models.CharField(max_length=50, blank=True, null=True, verbose_name='Cor')
    genero = models.CharField(max_length=100, blank=True, null=True, verbose_name='Gênero')
    colecao = models.CharField(max_length=100, blank=True, null=True, verbose_name='Coleção')
    categoria = models.CharField(max_length=200, blank=True, null=True, verbose_name='Categoria')

    # =========================================================
    # CAMPOS FISCAIS (NF-e / NFC-e)
    # =========================================================
    origem = models.CharField(
        max_length=1, choices=ORIGEM_CHOICES, default='0',
        verbose_name='Origem da Mercadoria'
    )

    # ICMS
    cst_icms = models.CharField(
        max_length=3, blank=True, default='',
        verbose_name='CST/CSOSN ICMS',
        help_text='Régime Normal: 00,10,20,30,40,41,50,60,70,90 | Simples: 101,102,103,201,202,203,300,400,500,900'
    )
    cfop_venda_estadual = models.CharField(
        max_length=4, blank=True, default='',
        verbose_name='CFOP Venda Estadual',
        help_text='Ex: 5102, 5405'
    )
    cfop_venda_interestadual = models.CharField(
        max_length=4, blank=True, default='',
        verbose_name='CFOP Venda Interestadual',
        help_text='Ex: 6102, 6404'
    )
    aliquota_icms = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        verbose_name='Alíquota ICMS (%)'
    )
    reducao_bc_icms = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        verbose_name='Redução BC ICMS (%)'
    )
    modalidade_bc_icms = models.IntegerField(
        default=3,
        verbose_name='Modalidade BC ICMS',
        help_text='0=MVA | 1=Pauta | 2=Preço Tabelado | 3=Valor da Operação'
    )

    # ICMS-ST (Substituição Tributária)
    aliquota_icms_st = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        verbose_name='Alíquota ICMS-ST (%)'
    )
    aliquota_mva = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        verbose_name='MVA (%)',
        help_text='Margem de Valor Agregado para ICMS-ST'
    )
    reducao_bc_icms_st = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        verbose_name='Redução BC ICMS-ST (%)'
    )

    # PIS
    cst_pis = models.CharField(
        max_length=2, blank=True, default='',
        verbose_name='CST PIS',
        help_text='Ex: 01=Alíquota básica | 07=Operação isenta | 49=Outras operações | 99=Outras'
    )
    aliquota_pis = models.DecimalField(
        max_digits=5, decimal_places=4, default=0,
        verbose_name='Alíquota PIS (%)'
    )

    # COFINS
    cst_cofins = models.CharField(
        max_length=2, blank=True, default='',
        verbose_name='CST COFINS',
        help_text='Ex: 01=Alíquota básica | 07=Operação isenta | 49=Outras operações | 99=Outras'
    )
    aliquota_cofins = models.DecimalField(
        max_digits=5, decimal_places=4, default=0,
        verbose_name='Alíquota COFINS (%)'
    )

    # IPI
    cst_ipi = models.CharField(
        max_length=2, blank=True, null=True,
        verbose_name='CST IPI',
        help_text='Ex: 50=Saída tributada | 99=Outras saídas'
    )
    aliquota_ipi = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        verbose_name='Alíquota IPI (%)'
    )

    class Meta:
        db_table = 'produtos'
        verbose_name = 'Produto'
        verbose_name_plural = 'Produtos'
        ordering = ['nome']

    def __str__(self):
        return f"{self.pk_chave} - {self.nome}"


class CodigoBarras(models.Model):
    produto = models.ForeignKey(
        Produto,
        on_delete=models.CASCADE,
        related_name='codigos_barras',
        verbose_name='Produto'
    )
    codigo_barras = models.CharField(
        max_length=13,
        verbose_name='Código de Barras',
        help_text='Código EAN-13 (até 13 dígitos)'
    )

    class Meta:
        db_table = 'codigo_barras'
        verbose_name = 'Código de Barras'
        verbose_name_plural = 'Códigos de Barras'
        unique_together = [['produto', 'codigo_barras']]

    def __str__(self):
        return f"{self.codigo_barras} - {self.produto.nome}"


class ImagemProduto(models.Model):
    pk_chave = models.AutoField(primary_key=True, verbose_name='Código')
    produto = models.ForeignKey(
        Produto,
        on_delete=models.CASCADE,
        related_name='imagens',
        verbose_name='Produto'
    )
    imagem = models.BinaryField(verbose_name='Imagem (Binário)')

    class Meta:
        db_table = 'imagem_produto'
        verbose_name = 'Imagem de Produto'
        verbose_name_plural = 'Imagens de Produtos'

    def __str__(self):
        return f"Imagem {self.pk_chave} - {self.produto.nome}"

class SaldoEstoque(models.Model):
    """
    Saldo atual de um produto em um local de estoque.
    Atualizado automaticamente a cada movimentação.
    """
    produto = models.ForeignKey(
        Produto,
        on_delete=models.PROTECT,
        related_name='saldos_estoque',
        verbose_name='Produto'
    )
    local = models.ForeignKey(
        LocalEstoque,
        on_delete=models.PROTECT,
        related_name='saldos',
        verbose_name='Local'
    )
    quantidade = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        default=0,
        verbose_name='Quantidade'
    )
    ultima_atualizacao = models.DateTimeField(
        auto_now=True,
        verbose_name='Última Atualização'
    )

    class Meta:
        db_table = 'estoque_saldo'
        verbose_name = 'Saldo de Estoque'
        verbose_name_plural = 'Saldos de Estoque'
        unique_together = [['produto', 'local']]
        ordering = ['produto__nome']

    def __str__(self):
        return f"{self.produto.nome} | {self.local.local}: {self.quantidade}"
